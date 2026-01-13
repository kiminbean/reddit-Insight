"""Reddit 데이터 모델.

PRAW 객체를 Pydantic 모델로 변환하기 위한 데이터 클래스들.
모든 모델은 불변(frozen=True)으로 설정되어 안전한 데이터 전달을 보장한다.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    import praw.models


class Post(BaseModel):
    """Reddit 게시물(Submission) 모델.

    Attributes:
        id: 게시물 고유 ID
        title: 게시물 제목
        selftext: 게시물 본문 (텍스트 게시물인 경우)
        author: 작성자 이름
        subreddit: 서브레딧 이름
        score: 점수 (업보트 - 다운보트)
        num_comments: 댓글 수
        created_utc: 작성 시간 (UTC)
        url: 게시물 URL (외부 링크 또는 미디어 URL)
        permalink: Reddit 내부 링크
        is_self: 텍스트 게시물 여부
    """

    model_config = ConfigDict(frozen=True)

    id: str = Field(description="게시물 고유 ID")
    title: str = Field(description="게시물 제목")
    selftext: str = Field(default="", description="게시물 본문")
    author: str = Field(description="작성자 이름")
    subreddit: str = Field(description="서브레딧 이름")
    score: int = Field(default=0, description="점수")
    num_comments: int = Field(default=0, description="댓글 수")
    created_utc: datetime = Field(description="작성 시간 (UTC)")
    url: str = Field(description="게시물 URL")
    permalink: str = Field(description="Reddit 내부 링크")
    is_self: bool = Field(default=True, description="텍스트 게시물 여부")

    @classmethod
    def from_praw(cls, submission: praw.models.Submission) -> Post:
        """PRAW Submission 객체에서 Post 모델 생성.

        Args:
            submission: PRAW Submission 객체

        Returns:
            Post: 변환된 Post 모델
        """
        # author가 삭제된 경우 "[deleted]" 반환
        author_name = "[deleted]"
        if submission.author is not None:
            author_name = submission.author.name

        return cls(
            id=submission.id,
            title=submission.title,
            selftext=submission.selftext or "",
            author=author_name,
            subreddit=submission.subreddit.display_name,
            score=submission.score,
            num_comments=submission.num_comments,
            created_utc=datetime.fromtimestamp(submission.created_utc, tz=UTC),
            url=submission.url,
            permalink=f"https://reddit.com{submission.permalink}",
            is_self=submission.is_self,
        )


class Comment(BaseModel):
    """Reddit 댓글 모델.

    Attributes:
        id: 댓글 고유 ID
        body: 댓글 본문
        author: 작성자 이름
        subreddit: 서브레딧 이름
        score: 점수
        created_utc: 작성 시간 (UTC)
        parent_id: 부모 ID (게시물 또는 상위 댓글)
        post_id: 소속 게시물 ID
    """

    model_config = ConfigDict(frozen=True)

    id: str = Field(description="댓글 고유 ID")
    body: str = Field(description="댓글 본문")
    author: str = Field(description="작성자 이름")
    subreddit: str = Field(description="서브레딧 이름")
    score: int = Field(default=0, description="점수")
    created_utc: datetime = Field(description="작성 시간 (UTC)")
    parent_id: str = Field(description="부모 ID")
    post_id: str = Field(description="소속 게시물 ID")

    @classmethod
    def from_praw(cls, comment: praw.models.Comment) -> Comment:
        """PRAW Comment 객체에서 Comment 모델 생성.

        Args:
            comment: PRAW Comment 객체

        Returns:
            Comment: 변환된 Comment 모델
        """
        author_name = "[deleted]"
        if comment.author is not None:
            author_name = comment.author.name

        # link_id는 't3_xxxxx' 형식, 'xxxxx' 부분만 추출
        post_id = comment.link_id
        if post_id.startswith("t3_"):
            post_id = post_id[3:]

        return cls(
            id=comment.id,
            body=comment.body,
            author=author_name,
            subreddit=comment.subreddit.display_name,
            score=comment.score,
            created_utc=datetime.fromtimestamp(comment.created_utc, tz=UTC),
            parent_id=comment.parent_id,
            post_id=post_id,
        )


class SubredditInfo(BaseModel):
    """서브레딧 정보 모델.

    Attributes:
        name: 서브레딧 이름 (소문자)
        display_name: 표시 이름
        title: 서브레딧 제목
        description: 서브레딧 설명
        subscribers: 구독자 수
        created_utc: 생성 시간 (UTC)
        over18: 성인 전용 여부
    """

    model_config = ConfigDict(frozen=True)

    name: str = Field(description="서브레딧 이름")
    display_name: str = Field(description="표시 이름")
    title: str = Field(default="", description="서브레딧 제목")
    description: str = Field(default="", description="서브레딧 설명")
    subscribers: int = Field(default=0, description="구독자 수")
    created_utc: datetime = Field(description="생성 시간 (UTC)")
    over18: bool = Field(default=False, description="성인 전용 여부")

    @classmethod
    def from_praw(cls, subreddit: praw.models.Subreddit) -> SubredditInfo:
        """PRAW Subreddit 객체에서 SubredditInfo 모델 생성.

        Args:
            subreddit: PRAW Subreddit 객체

        Returns:
            SubredditInfo: 변환된 SubredditInfo 모델
        """
        return cls(
            name=subreddit.name,
            display_name=subreddit.display_name,
            title=subreddit.title or "",
            description=subreddit.public_description or "",
            subscribers=subreddit.subscribers or 0,
            created_utc=datetime.fromtimestamp(subreddit.created_utc, tz=UTC),
            over18=subreddit.over18,
        )
