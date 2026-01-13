"""데이터 파이프라인.

수집 -> 전처리 -> 저장의 전체 워크플로우를 관리한다.
중복 필터링, 삭제 콘텐츠 처리, 배치 저장 등을 처리한다.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from reddit_insight.data_source import DataSourceStrategy, UnifiedDataSource
from reddit_insight.pipeline.preprocessor import TextPreprocessor
from reddit_insight.storage.models import SubredditModel
from reddit_insight.storage.repository import (
    CommentRepository,
    PostRepository,
    SubredditRepository,
)

if TYPE_CHECKING:
    from reddit_insight.reddit.models import Comment, Post, SubredditInfo
    from reddit_insight.storage.database import Database

logger = logging.getLogger(__name__)


@dataclass
class ProcessingResult:
    """처리 결과 통계.

    파이프라인 처리 후 결과 통계를 담는 데이터 클래스.

    Attributes:
        total: 전체 입력 개수
        new: 새로 저장된 개수
        duplicates: 중복으로 업데이트된 개수
        filtered: 필터링된 개수 (삭제된 콘텐츠 등)
        errors: 처리 오류 개수
    """

    total: int = 0
    new: int = 0
    duplicates: int = 0
    filtered: int = 0
    errors: int = 0

    def __add__(self, other: ProcessingResult) -> ProcessingResult:
        """두 ProcessingResult를 합산."""
        return ProcessingResult(
            total=self.total + other.total,
            new=self.new + other.new,
            duplicates=self.duplicates + other.duplicates,
            filtered=self.filtered + other.filtered,
            errors=self.errors + other.errors,
        )

    def to_dict(self) -> dict[str, int]:
        """딕셔너리로 변환."""
        return {
            "total": self.total,
            "new": self.new,
            "duplicates": self.duplicates,
            "filtered": self.filtered,
            "errors": self.errors,
        }


@dataclass
class CollectionResult:
    """전체 수집 결과.

    collect_and_store 메서드의 결과를 담는다.

    Attributes:
        subreddit: 서브레딧 이름
        posts: 게시물 처리 결과
        comments: 댓글 처리 결과 (수집한 경우)
    """

    subreddit: str
    posts: ProcessingResult = field(default_factory=ProcessingResult)
    comments: ProcessingResult | None = None

    def to_dict(self) -> dict:
        """딕셔너리로 변환."""
        result = {
            "subreddit": self.subreddit,
            "posts": self.posts.to_dict(),
        }
        if self.comments is not None:
            result["comments"] = self.comments.to_dict()
        return result


class DataPipeline:
    """데이터 파이프라인.

    Reddit 데이터 수집 -> 전처리 -> 저장의 전체 워크플로우를 관리한다.

    Example:
        >>> async with Database() as db:
        ...     pipeline = DataPipeline(db)
        ...     result = await pipeline.collect_and_store(
        ...         subreddit="python",
        ...         sort="hot",
        ...         limit=100,
        ...         include_comments=True,
        ...     )
        ...     print(f"새 게시물: {result.posts.new}")
    """

    def __init__(self, database: Database) -> None:
        """DataPipeline 초기화.

        Args:
            database: Database 인스턴스 (연결 상태여야 함)
        """
        self._db = database
        self._preprocessor = TextPreprocessor()

    @property
    def preprocessor(self) -> TextPreprocessor:
        """텍스트 전처리기."""
        return self._preprocessor

    async def process_posts(
        self,
        posts: list[Post],
        subreddit_name: str,
    ) -> ProcessingResult:
        """게시물 처리 및 저장.

        중복 필터링, 텍스트 전처리를 수행하고 데이터베이스에 저장한다.

        Args:
            posts: Post Pydantic 모델 목록
            subreddit_name: 서브레딧 이름

        Returns:
            ProcessingResult: 처리 결과 통계
        """
        result = ProcessingResult(total=len(posts))

        if not posts:
            return result

        # 삭제된 게시물 필터링
        valid_posts: list[Post] = []
        for post in posts:
            if self._preprocessor.is_deleted_content(post.title):
                result.filtered += 1
                continue
            if post.is_self and self._preprocessor.is_deleted_content(post.selftext):
                result.filtered += 1
                continue
            valid_posts.append(post)

        if not valid_posts:
            return result

        try:
            async with self._db.session() as session:
                # 서브레딧 확보
                subreddit_repo = SubredditRepository(session)
                subreddit = await subreddit_repo.get_by_name(subreddit_name)

                if subreddit is None:
                    # 서브레딧이 없으면 기본 정보로 생성
                    from datetime import UTC, datetime

                    from reddit_insight.reddit.models import SubredditInfo

                    # 첫 번째 게시물에서 서브레딧 정보 추출
                    default_info = SubredditInfo(
                        name=subreddit_name.lower(),
                        display_name=valid_posts[0].subreddit
                        if valid_posts
                        else subreddit_name,
                        title="",
                        description="",
                        subscribers=0,
                        created_utc=datetime.now(UTC),
                        over18=False,
                    )
                    subreddit = await subreddit_repo.get_or_create(default_info)

                # 기존 게시물 ID 조회 (중복 체크용)
                post_repo = PostRepository(session)
                existing_ids: set[str] = set()
                for post in valid_posts:
                    existing = await post_repo.get_by_reddit_id(post.id)
                    if existing is not None:
                        existing_ids.add(post.id)

                # 새 게시물과 기존 게시물 분리
                new_posts = [p for p in valid_posts if p.id not in existing_ids]
                duplicate_posts = [p for p in valid_posts if p.id in existing_ids]

                # bulk 저장
                saved_models = await post_repo.save_many(valid_posts, subreddit.id)

                result.new = len(new_posts)
                result.duplicates = len(duplicate_posts)

                await session.commit()

                logger.info(
                    f"r/{subreddit_name} 게시물 처리 완료: "
                    f"total={result.total}, new={result.new}, "
                    f"duplicates={result.duplicates}, filtered={result.filtered}"
                )

        except Exception as e:
            result.errors = len(valid_posts)
            logger.error(f"게시물 처리 중 오류: {e}")
            raise

        return result

    async def process_comments(
        self,
        comments: list[Comment],
        post_reddit_id: str,
    ) -> ProcessingResult:
        """댓글 처리 및 저장.

        삭제된 댓글 필터링, 텍스트 전처리를 수행하고 데이터베이스에 저장한다.

        Args:
            comments: Comment Pydantic 모델 목록
            post_reddit_id: 연결할 게시물의 Reddit ID

        Returns:
            ProcessingResult: 처리 결과 통계
        """
        result = ProcessingResult(total=len(comments))

        if not comments:
            return result

        # 삭제된 댓글 필터링
        valid_comments: list[Comment] = []
        for comment in comments:
            if self._preprocessor.is_deleted_content(comment.body):
                result.filtered += 1
                continue
            # 작성자 정규화 후 삭제 여부 체크
            if self._preprocessor.normalize_author(comment.author) is None:
                # 삭제된 작성자의 댓글은 본문이 있으면 유지
                if not comment.body or comment.body.strip() == "":
                    result.filtered += 1
                    continue
            valid_comments.append(comment)

        if not valid_comments:
            return result

        try:
            async with self._db.session() as session:
                # 게시물 조회
                post_repo = PostRepository(session)
                post = await post_repo.get_by_reddit_id(post_reddit_id)

                if post is None:
                    logger.warning(
                        f"게시물을 찾을 수 없음: {post_reddit_id}, 댓글 저장 건너뜀"
                    )
                    result.errors = len(valid_comments)
                    return result

                # 기존 댓글 ID 조회 (중복 체크용)
                comment_repo = CommentRepository(session)
                existing_ids: set[str] = set()
                for comment in valid_comments:
                    existing = await comment_repo.get_by_reddit_id(comment.id)
                    if existing is not None:
                        existing_ids.add(comment.id)

                # 새 댓글과 기존 댓글 분리
                new_comments = [c for c in valid_comments if c.id not in existing_ids]
                duplicate_comments = [
                    c for c in valid_comments if c.id in existing_ids
                ]

                # bulk 저장
                saved_models = await comment_repo.save_many(valid_comments, post.id)

                result.new = len(new_comments)
                result.duplicates = len(duplicate_comments)

                await session.commit()

                logger.info(
                    f"post/{post_reddit_id} 댓글 처리 완료: "
                    f"total={result.total}, new={result.new}, "
                    f"duplicates={result.duplicates}, filtered={result.filtered}"
                )

        except Exception as e:
            result.errors = len(valid_comments)
            logger.error(f"댓글 처리 중 오류: {e}")
            raise

        return result

    async def ensure_subreddit(
        self,
        info: SubredditInfo,
    ) -> SubredditModel:
        """서브레딧 정보 저장 또는 업데이트.

        Args:
            info: SubredditInfo Pydantic 모델

        Returns:
            SubredditModel: 저장된 서브레딧 모델
        """
        async with self._db.session() as session:
            repo = SubredditRepository(session)
            model = await repo.get_or_create(info)
            await session.commit()
            return model

    async def collect_and_store(
        self,
        subreddit: str,
        sort: str = "hot",
        limit: int = 100,
        include_comments: bool = False,
        time_filter: str = "week",
        strategy: DataSourceStrategy = DataSourceStrategy.API_FIRST,
    ) -> CollectionResult:
        """데이터 수집 및 저장 워크플로우.

        UnifiedDataSource로 데이터를 수집하고 파이프라인으로 처리하여 저장한다.

        Args:
            subreddit: 서브레딧 이름
            sort: 정렬 방식 (hot, new, top)
            limit: 수집할 게시물 수
            include_comments: 댓글 수집 여부
            time_filter: top 정렬 시 기간 필터 (hour, day, week, month, year, all)
            strategy: 데이터 소스 전략

        Returns:
            CollectionResult: 수집 및 저장 결과

        Example:
            >>> result = await pipeline.collect_and_store(
            ...     subreddit="python",
            ...     sort="hot",
            ...     limit=100,
            ...     include_comments=True,
            ... )
            >>> print(f"새 게시물: {result.posts.new}")
            >>> if result.comments:
            ...     print(f"새 댓글: {result.comments.new}")
        """
        result = CollectionResult(subreddit=subreddit)

        async with UnifiedDataSource(strategy=strategy) as data_source:
            # 1. 서브레딧 정보 수집 및 저장
            try:
                subreddit_info = await data_source.get_subreddit_info(subreddit)
                if subreddit_info is not None:
                    await self.ensure_subreddit(subreddit_info)
                    logger.info(f"r/{subreddit} 정보 저장 완료")
            except Exception as e:
                logger.warning(f"서브레딧 정보 수집 실패: {e}")

            # 2. 게시물 수집
            try:
                if sort == "hot":
                    posts = await data_source.get_hot_posts(subreddit, limit=limit)
                elif sort == "new":
                    posts = await data_source.get_new_posts(subreddit, limit=limit)
                elif sort == "top":
                    posts = await data_source.get_top_posts(
                        subreddit, time_filter=time_filter, limit=limit
                    )
                else:
                    logger.warning(f"알 수 없는 정렬 방식: {sort}, hot으로 대체")
                    posts = await data_source.get_hot_posts(subreddit, limit=limit)

                logger.info(f"r/{subreddit} {sort} 게시물 {len(posts)}개 수집 완료")
            except Exception as e:
                logger.error(f"게시물 수집 실패: {e}")
                raise

            # 3. 게시물 처리 및 저장
            result.posts = await self.process_posts(posts, subreddit)

            # 4. 댓글 수집 (옵션)
            if include_comments and posts:
                result.comments = ProcessingResult()

                for post in posts:
                    try:
                        comments = await data_source.get_post_comments(post.id)
                        comment_result = await self.process_comments(comments, post.id)
                        result.comments = result.comments + comment_result
                    except Exception as e:
                        logger.warning(f"post/{post.id} 댓글 수집 실패: {e}")
                        result.comments.errors += 1

                logger.info(
                    f"r/{subreddit} 댓글 수집 완료: "
                    f"new={result.comments.new}, "
                    f"duplicates={result.comments.duplicates}"
                )

        logger.info(f"r/{subreddit} 전체 수집 완료: {result.to_dict()}")
        return result
