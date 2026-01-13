"""Repository 패턴 구현.

데이터베이스 접근을 추상화하여 도메인 로직과 영속성 계층을 분리한다.
각 Repository는 AsyncSession을 주입받아 트랜잭션 관리를 유연하게 처리한다.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Generic, TypeVar

from sqlalchemy import select, update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from reddit_insight.storage.models import CommentModel, PostModel, SubredditModel

if TYPE_CHECKING:
    from reddit_insight.reddit.models import Comment, Post, SubredditInfo


ModelT = TypeVar("ModelT", bound=SubredditModel | PostModel | CommentModel)


class BaseRepository(Generic[ModelT]):
    """Repository 기본 클래스.

    모든 Repository의 공통 기능을 제공한다.
    세션 주입 패턴을 사용하여 트랜잭션 범위를 호출자가 제어할 수 있다.

    Attributes:
        _session: SQLAlchemy AsyncSession 인스턴스
    """

    def __init__(self, session: AsyncSession) -> None:
        """Repository 초기화.

        Args:
            session: SQLAlchemy AsyncSession 인스턴스
        """
        self._session = session


class SubredditRepository(BaseRepository[SubredditModel]):
    """서브레딧 Repository.

    서브레딧 정보의 CRUD 연산을 제공한다.
    """

    async def get_by_name(self, name: str) -> SubredditModel | None:
        """이름으로 서브레딧 조회.

        Args:
            name: 서브레딧 이름 (대소문자 무관)

        Returns:
            SubredditModel 또는 None (존재하지 않는 경우)
        """
        stmt = select(SubredditModel).where(SubredditModel.name == name.lower())
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_or_create(self, info: SubredditInfo) -> SubredditModel:
        """서브레딧 조회 또는 생성.

        이미 존재하면 업데이트하고, 없으면 새로 생성한다.

        Args:
            info: SubredditInfo Pydantic 모델

        Returns:
            SubredditModel: 조회되거나 생성된 서브레딧 모델
        """
        existing = await self.get_by_name(info.name)

        if existing is not None:
            # 기존 레코드 업데이트
            existing.display_name = info.display_name
            existing.title = info.title or None
            existing.description = info.description or None
            existing.subscribers = info.subscribers
            existing.over18 = info.over18
            existing.fetched_at = datetime.now(UTC)
            await self._session.flush()
            return existing

        # 새 레코드 생성
        model = SubredditModel.from_pydantic(info)
        self._session.add(model)
        await self._session.flush()
        return model

    async def update_metrics(
        self,
        name: str,
        subscribers: int | None = None,
        **extra_fields: object,
    ) -> SubredditModel | None:
        """서브레딧 메트릭 업데이트.

        Args:
            name: 서브레딧 이름
            subscribers: 구독자 수 (업데이트할 경우)
            **extra_fields: 추가 필드 (title, description 등)

        Returns:
            업데이트된 SubredditModel 또는 None
        """
        subreddit = await self.get_by_name(name)
        if subreddit is None:
            return None

        if subscribers is not None:
            subreddit.subscribers = subscribers

        for field, value in extra_fields.items():
            if hasattr(subreddit, field):
                setattr(subreddit, field, value)

        subreddit.fetched_at = datetime.now(UTC)
        await self._session.flush()
        return subreddit

    async def list_all(self, limit: int = 100) -> list[SubredditModel]:
        """모든 서브레딧 조회.

        Args:
            limit: 최대 조회 개수

        Returns:
            서브레딧 모델 목록
        """
        stmt = (
            select(SubredditModel)
            .order_by(SubredditModel.subscribers.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())


class PostRepository(BaseRepository[PostModel]):
    """게시물 Repository.

    게시물 데이터의 CRUD 및 bulk 연산을 제공한다.
    """

    async def get_by_reddit_id(self, reddit_id: str) -> PostModel | None:
        """Reddit ID로 게시물 조회.

        Args:
            reddit_id: Reddit 게시물 ID

        Returns:
            PostModel 또는 None
        """
        stmt = select(PostModel).where(PostModel.reddit_id == reddit_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def save(self, post: Post, subreddit_id: int) -> PostModel:
        """단일 게시물 저장.

        이미 존재하면 업데이트하고, 없으면 새로 생성한다.

        Args:
            post: Post Pydantic 모델
            subreddit_id: 연결할 서브레딧 ID

        Returns:
            저장된 PostModel
        """
        existing = await self.get_by_reddit_id(post.id)

        if existing is not None:
            # 기존 레코드 업데이트 (score, num_comments는 변할 수 있음)
            existing.score = post.score
            existing.num_comments = post.num_comments
            existing.fetched_at = datetime.now(UTC)
            await self._session.flush()
            return existing

        # 새 레코드 생성
        model = PostModel.from_pydantic(post, subreddit_id)
        self._session.add(model)
        await self._session.flush()
        return model

    async def save_many(
        self,
        posts: list[Post],
        subreddit_id: int,
    ) -> list[PostModel]:
        """여러 게시물 bulk 저장.

        SQLite의 ON CONFLICT DO UPDATE를 사용하여 upsert 수행.
        중복 게시물은 업데이트된다.

        Args:
            posts: Post Pydantic 모델 목록
            subreddit_id: 연결할 서브레딧 ID

        Returns:
            저장된 PostModel 목록
        """
        if not posts:
            return []

        now = datetime.now(UTC)
        values = [
            {
                "reddit_id": post.id,
                "subreddit_id": subreddit_id,
                "title": post.title,
                "selftext": post.selftext or None,
                "author": post.author,
                "score": post.score,
                "num_comments": post.num_comments,
                "url": post.url,
                "permalink": post.permalink,
                "is_self": post.is_self,
                "reddit_created_utc": post.created_utc,
                "fetched_at": now,
                "created_at": now,
                "updated_at": now,
            }
            for post in posts
        ]

        # SQLite INSERT ... ON CONFLICT DO UPDATE
        stmt = sqlite_insert(PostModel).values(values)
        stmt = stmt.on_conflict_do_update(
            index_elements=["reddit_id"],
            set_={
                "score": stmt.excluded.score,
                "num_comments": stmt.excluded.num_comments,
                "fetched_at": stmt.excluded.fetched_at,
                "updated_at": stmt.excluded.updated_at,
            },
        )
        await self._session.execute(stmt)
        await self._session.flush()

        # 저장된 레코드 조회하여 반환
        reddit_ids = [post.id for post in posts]
        select_stmt = select(PostModel).where(PostModel.reddit_id.in_(reddit_ids))
        result = await self._session.execute(select_stmt)
        return list(result.scalars().all())

    async def get_by_subreddit(
        self,
        subreddit_id: int,
        limit: int = 100,
    ) -> list[PostModel]:
        """서브레딧의 게시물 조회.

        Args:
            subreddit_id: 서브레딧 ID
            limit: 최대 조회 개수

        Returns:
            게시물 모델 목록 (최신순 정렬)
        """
        stmt = (
            select(PostModel)
            .where(PostModel.subreddit_id == subreddit_id)
            .order_by(PostModel.reddit_created_utc.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_recent(
        self,
        hours: int = 24,
        limit: int = 100,
    ) -> list[PostModel]:
        """최근 게시물 조회.

        Args:
            hours: 기준 시간 (기본 24시간)
            limit: 최대 조회 개수

        Returns:
            게시물 모델 목록 (최신순 정렬)
        """
        cutoff = datetime.now(UTC) - timedelta(hours=hours)
        stmt = (
            select(PostModel)
            .where(PostModel.reddit_created_utc >= cutoff)
            .order_by(PostModel.reddit_created_utc.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())


class CommentRepository(BaseRepository[CommentModel]):
    """댓글 Repository.

    댓글 데이터의 CRUD 및 bulk 연산을 제공한다.
    """

    async def get_by_reddit_id(self, reddit_id: str) -> CommentModel | None:
        """Reddit ID로 댓글 조회.

        Args:
            reddit_id: Reddit 댓글 ID

        Returns:
            CommentModel 또는 None
        """
        stmt = select(CommentModel).where(CommentModel.reddit_id == reddit_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def save(self, comment: Comment, post_id: int) -> CommentModel:
        """단일 댓글 저장.

        이미 존재하면 업데이트하고, 없으면 새로 생성한다.

        Args:
            comment: Comment Pydantic 모델
            post_id: 연결할 게시물 ID

        Returns:
            저장된 CommentModel
        """
        existing = await self.get_by_reddit_id(comment.id)

        if existing is not None:
            # 기존 레코드 업데이트 (score는 변할 수 있음)
            existing.score = comment.score
            existing.fetched_at = datetime.now(UTC)
            await self._session.flush()
            return existing

        # 새 레코드 생성
        model = CommentModel.from_pydantic(comment, post_id)
        self._session.add(model)
        await self._session.flush()
        return model

    async def save_many(
        self,
        comments: list[Comment],
        post_id: int,
    ) -> list[CommentModel]:
        """여러 댓글 bulk 저장.

        SQLite의 ON CONFLICT DO UPDATE를 사용하여 upsert 수행.

        Args:
            comments: Comment Pydantic 모델 목록
            post_id: 연결할 게시물 ID

        Returns:
            저장된 CommentModel 목록
        """
        if not comments:
            return []

        now = datetime.now(UTC)
        values = [
            {
                "reddit_id": comment.id,
                "post_id": post_id,
                "parent_reddit_id": comment.parent_id or None,
                "body": comment.body,
                "author": comment.author,
                "score": comment.score,
                "reddit_created_utc": comment.created_utc,
                "fetched_at": now,
                "created_at": now,
                "updated_at": now,
            }
            for comment in comments
        ]

        # SQLite INSERT ... ON CONFLICT DO UPDATE
        stmt = sqlite_insert(CommentModel).values(values)
        stmt = stmt.on_conflict_do_update(
            index_elements=["reddit_id"],
            set_={
                "score": stmt.excluded.score,
                "fetched_at": stmt.excluded.fetched_at,
                "updated_at": stmt.excluded.updated_at,
            },
        )
        await self._session.execute(stmt)
        await self._session.flush()

        # 저장된 레코드 조회하여 반환
        reddit_ids = [comment.id for comment in comments]
        select_stmt = select(CommentModel).where(
            CommentModel.reddit_id.in_(reddit_ids)
        )
        result = await self._session.execute(select_stmt)
        return list(result.scalars().all())

    async def get_by_post(self, post_id: int) -> list[CommentModel]:
        """게시물의 모든 댓글 조회.

        Args:
            post_id: 게시물 ID

        Returns:
            댓글 모델 목록 (최신순 정렬)
        """
        stmt = (
            select(CommentModel)
            .where(CommentModel.post_id == post_id)
            .order_by(CommentModel.reddit_created_utc.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
