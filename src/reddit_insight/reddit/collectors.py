"""Reddit 게시물 및 댓글 수집기.

Subreddit에서 게시물과 댓글을 체계적으로 수집하는 Collector 클래스들.
PRAW 객체를 Pydantic 모델로 변환하여 반환한다.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from reddit_insight.reddit.models import Comment, Post

if TYPE_CHECKING:
    from praw.models.comment_forest import CommentForest

    from reddit_insight.reddit.client import RedditClient

logger = logging.getLogger(__name__)


class PostCollector:
    """Reddit 게시물 수집기.

    다양한 정렬 방식(hot, new, top, rising)으로 게시물을 수집하고
    검색 기능을 제공한다.

    Attributes:
        client: RedditClient 인스턴스

    Example:
        >>> collector = PostCollector(client)
        >>> posts = collector.get_hot("python", limit=10)
        >>> for post in posts:
        ...     print(post.title)
    """

    def __init__(self, client: RedditClient) -> None:
        """PostCollector 초기화.

        Args:
            client: RedditClient 인스턴스
        """
        self._client = client

    def get_hot(self, subreddit: str, limit: int = 100) -> list[Post]:
        """Hot 게시물 수집.

        인기도와 최신성을 조합한 정렬로 게시물을 가져온다.

        Args:
            subreddit: 서브레딧 이름
            limit: 최대 수집 개수 (기본: 100, 최대: Reddit API 제한)

        Returns:
            list[Post]: 수집된 게시물 목록
        """
        logger.debug("r/%s에서 hot 게시물 %d개 수집", subreddit, limit)
        sub = self._client.get_subreddit(subreddit)
        return [self._convert_submission(s) for s in sub.hot(limit=limit)]

    def get_new(self, subreddit: str, limit: int = 100) -> list[Post]:
        """최신 게시물 수집.

        작성 시간 순으로 정렬된 게시물을 가져온다.

        Args:
            subreddit: 서브레딧 이름
            limit: 최대 수집 개수 (기본: 100)

        Returns:
            list[Post]: 수집된 게시물 목록
        """
        logger.debug("r/%s에서 new 게시물 %d개 수집", subreddit, limit)
        sub = self._client.get_subreddit(subreddit)
        return [self._convert_submission(s) for s in sub.new(limit=limit)]

    def get_top(
        self,
        subreddit: str,
        time_filter: str = "week",
        limit: int = 100,
    ) -> list[Post]:
        """Top 게시물 수집.

        지정된 기간 내 최고 점수 게시물을 가져온다.

        Args:
            subreddit: 서브레딧 이름
            time_filter: 기간 필터. "hour", "day", "week", "month", "year", "all" 중 하나
            limit: 최대 수집 개수 (기본: 100)

        Returns:
            list[Post]: 수집된 게시물 목록

        Raises:
            ValueError: time_filter가 유효하지 않은 경우
        """
        valid_filters = {"hour", "day", "week", "month", "year", "all"}
        if time_filter not in valid_filters:
            raise ValueError(
                f"Invalid time_filter: {time_filter}. Must be one of {valid_filters}"
            )

        logger.debug(
            "r/%s에서 top 게시물 %d개 수집 (time_filter=%s)",
            subreddit,
            limit,
            time_filter,
        )
        sub = self._client.get_subreddit(subreddit)
        return [
            self._convert_submission(s)
            for s in sub.top(time_filter=time_filter, limit=limit)
        ]

    def get_rising(self, subreddit: str, limit: int = 100) -> list[Post]:
        """Rising 게시물 수집.

        빠르게 인기를 얻고 있는 게시물을 가져온다.

        Args:
            subreddit: 서브레딧 이름
            limit: 최대 수집 개수 (기본: 100)

        Returns:
            list[Post]: 수집된 게시물 목록
        """
        logger.debug("r/%s에서 rising 게시물 %d개 수집", subreddit, limit)
        sub = self._client.get_subreddit(subreddit)
        return [self._convert_submission(s) for s in sub.rising(limit=limit)]

    def search(
        self,
        subreddit: str,
        query: str,
        sort: str = "relevance",
        limit: int = 100,
    ) -> list[Post]:
        """게시물 검색.

        서브레딧 내에서 키워드로 게시물을 검색한다.

        Args:
            subreddit: 서브레딧 이름
            query: 검색어
            sort: 정렬 방식. "relevance", "hot", "top", "new", "comments" 중 하나
            limit: 최대 수집 개수 (기본: 100)

        Returns:
            list[Post]: 검색된 게시물 목록

        Raises:
            ValueError: sort가 유효하지 않은 경우
        """
        valid_sorts = {"relevance", "hot", "top", "new", "comments"}
        if sort not in valid_sorts:
            raise ValueError(f"Invalid sort: {sort}. Must be one of {valid_sorts}")

        logger.debug(
            "r/%s에서 '%s' 검색 (sort=%s, limit=%d)",
            subreddit,
            query,
            sort,
            limit,
        )
        sub = self._client.get_subreddit(subreddit)
        return [
            self._convert_submission(s)
            for s in sub.search(query=query, sort=sort, limit=limit)
        ]

    def _convert_submission(self, submission) -> Post:
        """PRAW Submission을 Post 모델로 변환.

        Args:
            submission: PRAW Submission 객체

        Returns:
            Post: 변환된 Post 모델
        """
        return Post.from_praw(submission)


class CommentCollector:
    """Reddit 댓글 수집기.

    게시물별 또는 서브레딧별로 댓글을 수집한다.
    댓글 트리를 평탄화하여 반환할 수 있다.

    Attributes:
        client: RedditClient 인스턴스

    Example:
        >>> collector = CommentCollector(client)
        >>> comments = collector.get_post_comments("abc123", limit=50)
        >>> for comment in comments:
        ...     print(comment.body[:50])
    """

    def __init__(self, client: RedditClient) -> None:
        """CommentCollector 초기화.

        Args:
            client: RedditClient 인스턴스
        """
        self._client = client

    def get_post_comments(
        self,
        post_id: str,
        limit: int | None = None,
        *,
        replace_more_limit: int = 0,
    ) -> list[Comment]:
        """게시물의 댓글 수집.

        게시물에 달린 댓글을 수집하고 평탄화하여 반환한다.

        Args:
            post_id: 게시물 ID
            limit: 최대 수집 개수. None이면 모든 댓글 수집
            replace_more_limit: "more comments" 확장 개수.
                               0이면 확장하지 않음, None이면 모두 확장

        Returns:
            list[Comment]: 수집된 댓글 목록

        Note:
            replace_more_limit이 클수록 API 호출이 많아지므로 주의.
            대규모 댓글 수집 시 replace_more_limit=0 권장.
        """
        logger.debug(
            "게시물 %s의 댓글 수집 (limit=%s, replace_more=%d)",
            post_id,
            limit,
            replace_more_limit,
        )

        reddit = self._client._ensure_connected()
        submission = reddit.submission(id=post_id)

        # "more comments" 확장
        submission.comments.replace_more(limit=replace_more_limit)

        # 댓글 트리 평탄화
        all_comments = self._flatten_comment_tree(submission.comments)

        # limit 적용
        if limit is not None:
            all_comments = all_comments[:limit]

        return [self._convert_comment(c) for c in all_comments]

    def get_subreddit_comments(
        self,
        subreddit: str,
        limit: int = 100,
    ) -> list[Comment]:
        """서브레딧의 최근 댓글 수집.

        서브레딧에 올라온 최근 댓글 스트림을 가져온다.

        Args:
            subreddit: 서브레딧 이름
            limit: 최대 수집 개수 (기본: 100)

        Returns:
            list[Comment]: 수집된 댓글 목록
        """
        logger.debug("r/%s의 최근 댓글 %d개 수집", subreddit, limit)
        sub = self._client.get_subreddit(subreddit)
        return [self._convert_comment(c) for c in sub.comments(limit=limit)]

    def _convert_comment(self, comment) -> Comment:
        """PRAW Comment를 Comment 모델로 변환.

        Args:
            comment: PRAW Comment 객체

        Returns:
            Comment: 변환된 Comment 모델
        """
        return Comment.from_praw(comment)

    def _flatten_comment_tree(
        self,
        comments: CommentForest,
    ) -> list:
        """댓글 트리를 평탄화.

        중첩된 댓글 구조를 1차원 리스트로 변환한다.
        MoreComments 객체는 제외한다.

        Args:
            comments: PRAW CommentForest 객체

        Returns:
            list: 평탄화된 PRAW Comment 객체 리스트
        """
        # list() 호출로 이미 평탄화된 모든 댓글 반환
        # PRAW의 CommentForest.list()는 BFS로 모든 댓글 반환
        flattened = list(comments)

        # MoreComments 객체 필터링
        result = []
        for item in flattened:
            # MoreComments는 제외
            if hasattr(item, "body"):
                result.append(item)

        return result
