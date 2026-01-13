"""SQLAlchemy ORM 모델.

Reddit 데이터를 영구 저장하기 위한 데이터베이스 스키마 정의.
SQLAlchemy 2.0 스타일의 DeclarativeBase를 사용한다.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from reddit_insight.reddit.models import Comment, Post, SubredditInfo


class Base(DeclarativeBase):
    """SQLAlchemy ORM 기본 클래스.

    모든 ORM 모델의 기본 클래스로, 공통 컬럼과 메타데이터를 정의한다.
    """

    pass


class TimestampMixin:
    """타임스탬프 믹스인.

    레코드 생성/수정 시간을 자동으로 관리한다.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


class SubredditModel(Base, TimestampMixin):
    """서브레딧 ORM 모델.

    서브레딧 메타데이터를 저장한다.
    """

    __tablename__ = "subreddits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    subscribers: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    over18: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reddit_created_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Relationships
    posts: Mapped[list[PostModel]] = relationship(
        "PostModel", back_populates="subreddit", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<SubredditModel(name={self.name!r}, subscribers={self.subscribers})>"

    @classmethod
    def from_pydantic(cls, info: SubredditInfo) -> SubredditModel:
        """Pydantic SubredditInfo에서 ORM 모델 생성.

        Args:
            info: Pydantic SubredditInfo 객체

        Returns:
            SubredditModel: ORM 모델 인스턴스
        """
        return cls(
            name=info.name.lower(),
            display_name=info.display_name,
            title=info.title or None,
            description=info.description or None,
            subscribers=info.subscribers,
            over18=info.over18,
            reddit_created_utc=info.created_utc,
            fetched_at=datetime.now(UTC),
        )

    def to_pydantic(self) -> SubredditInfo:
        """ORM 모델을 Pydantic SubredditInfo로 변환.

        Returns:
            SubredditInfo: Pydantic 모델 인스턴스
        """
        from reddit_insight.reddit.models import SubredditInfo

        return SubredditInfo(
            name=self.name,
            display_name=self.display_name,
            title=self.title or "",
            description=self.description or "",
            subscribers=self.subscribers,
            created_utc=self.reddit_created_utc,
            over18=self.over18,
        )


class PostModel(Base, TimestampMixin):
    """게시물 ORM 모델.

    Reddit 게시물(Submission) 데이터를 저장한다.
    """

    __tablename__ = "posts"
    __table_args__ = (
        Index("ix_posts_fetched_at", "fetched_at"),
        Index("ix_posts_reddit_created_utc", "reddit_created_utc"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    reddit_id: Mapped[str] = mapped_column(String(16), unique=True, nullable=False, index=True)
    subreddit_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("subreddits.id"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    selftext: Mapped[str | None] = mapped_column(Text, nullable=True)
    author: Mapped[str] = mapped_column(String(64), nullable=False)
    score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    num_comments: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    permalink: Mapped[str] = mapped_column(String(512), nullable=False)
    is_self: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    reddit_created_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Relationships
    subreddit: Mapped[SubredditModel] = relationship("SubredditModel", back_populates="posts")
    comments: Mapped[list[CommentModel]] = relationship(
        "CommentModel", back_populates="post", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<PostModel(reddit_id={self.reddit_id!r}, title={self.title[:30]!r}...)>"

    @classmethod
    def from_pydantic(cls, post: Post, subreddit_id: int) -> PostModel:
        """Pydantic Post에서 ORM 모델 생성.

        Args:
            post: Pydantic Post 객체
            subreddit_id: 연결할 서브레딧 ID

        Returns:
            PostModel: ORM 모델 인스턴스
        """
        return cls(
            reddit_id=post.id,
            subreddit_id=subreddit_id,
            title=post.title,
            selftext=post.selftext or None,
            author=post.author,
            score=post.score,
            num_comments=post.num_comments,
            url=post.url,
            permalink=post.permalink,
            is_self=post.is_self,
            reddit_created_utc=post.created_utc,
            fetched_at=datetime.now(UTC),
        )

    def to_pydantic(self) -> Post:
        """ORM 모델을 Pydantic Post로 변환.

        Returns:
            Post: Pydantic 모델 인스턴스
        """
        from reddit_insight.reddit.models import Post

        return Post(
            id=self.reddit_id,
            title=self.title,
            selftext=self.selftext or "",
            author=self.author,
            subreddit=self.subreddit.display_name if self.subreddit else "",
            score=self.score,
            num_comments=self.num_comments,
            created_utc=self.reddit_created_utc,
            url=self.url,
            permalink=self.permalink,
            is_self=self.is_self,
        )


class CommentModel(Base, TimestampMixin):
    """댓글 ORM 모델.

    Reddit 댓글 데이터를 저장한다.
    """

    __tablename__ = "comments"
    __table_args__ = (
        Index("ix_comments_fetched_at", "fetched_at"),
        Index("ix_comments_reddit_created_utc", "reddit_created_utc"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    reddit_id: Mapped[str] = mapped_column(String(16), unique=True, nullable=False, index=True)
    post_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("posts.id"), nullable=False, index=True
    )
    parent_reddit_id: Mapped[str | None] = mapped_column(String(24), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    author: Mapped[str] = mapped_column(String(64), nullable=False)
    score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reddit_created_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Relationships
    post: Mapped[PostModel] = relationship("PostModel", back_populates="comments")

    def __repr__(self) -> str:
        body_preview = self.body[:30] if self.body else ""
        return f"<CommentModel(reddit_id={self.reddit_id!r}, body={body_preview!r}...)>"

    @classmethod
    def from_pydantic(cls, comment: Comment, post_id: int) -> CommentModel:
        """Pydantic Comment에서 ORM 모델 생성.

        Args:
            comment: Pydantic Comment 객체
            post_id: 연결할 게시물 ID

        Returns:
            CommentModel: ORM 모델 인스턴스
        """
        return cls(
            reddit_id=comment.id,
            post_id=post_id,
            parent_reddit_id=comment.parent_id,
            body=comment.body,
            author=comment.author,
            score=comment.score,
            reddit_created_utc=comment.created_utc,
            fetched_at=datetime.now(UTC),
        )

    def to_pydantic(self) -> Comment:
        """ORM 모델을 Pydantic Comment로 변환.

        Returns:
            Comment: Pydantic 모델 인스턴스
        """
        from reddit_insight.reddit.models import Comment

        return Comment(
            id=self.reddit_id,
            body=self.body,
            author=self.author,
            subreddit=self.post.subreddit.display_name if self.post and self.post.subreddit else "",
            score=self.score,
            created_utc=self.reddit_created_utc,
            parent_id=self.parent_reddit_id or "",
            post_id=self.post.reddit_id if self.post else "",
        )
