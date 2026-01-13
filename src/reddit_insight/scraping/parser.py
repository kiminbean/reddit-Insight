"""Reddit JSON 응답 파서.

old.reddit.com의 JSON 응답을 파싱하여 데이터 모델로 변환합니다.
Reddit JSON API는 다음과 같은 구조를 가집니다:
- Listing: {"kind": "Listing", "data": {"children": [...]}}
- Post: {"kind": "t3", "data": {...}}
- Comment: {"kind": "t1", "data": {...}}
- More: {"kind": "more", "data": {...}}
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from reddit_insight.reddit.models import Comment, Post, SubredditInfo

logger = logging.getLogger(__name__)


class RedditJSONParser:
    """Reddit JSON 응답을 파싱하여 데이터 모델로 변환.

    Reddit의 JSON 응답 구조를 이해하고 Post, Comment, SubredditInfo
    모델로 변환하는 기능을 제공합니다.

    Example:
        >>> parser = RedditJSONParser()
        >>> posts = parser.parse_listing(response)
        >>> for item in posts:
        ...     post = parser.parse_post(item)
    """

    # Reddit thing 타입 접두사
    KIND_POST = "t3"  # Link/Post
    KIND_COMMENT = "t1"  # Comment
    KIND_SUBREDDIT = "t5"  # Subreddit
    KIND_MORE = "more"  # More comments indicator
    KIND_LISTING = "Listing"  # Listing container

    def parse_listing(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """Listing 응답에서 children 추출.

        Args:
            data: Reddit Listing 응답 {"kind": "Listing", "data": {"children": [...]}}

        Returns:
            children 리스트 (각 항목은 {"kind": "...", "data": {...}} 구조)
        """
        if not isinstance(data, dict):
            logger.warning(f"Expected dict, got {type(data)}")
            return []

        kind = data.get("kind")
        if kind != self.KIND_LISTING:
            logger.warning(f"Expected Listing, got {kind}")
            return []

        inner_data = data.get("data", {})
        children = inner_data.get("children", [])
        return children

    def get_after_token(self, data: dict[str, Any]) -> str | None:
        """Listing 응답에서 페이지네이션 토큰 추출.

        Args:
            data: Reddit Listing 응답

        Returns:
            다음 페이지 토큰 또는 None
        """
        if not isinstance(data, dict):
            return None

        inner_data = data.get("data", {})
        return inner_data.get("after")

    def parse_post(self, data: dict[str, Any]) -> Post | None:
        """JSON 데이터를 Post 모델로 변환.

        Args:
            data: Post 데이터 {"kind": "t3", "data": {...}}

        Returns:
            Post 모델 또는 None (파싱 실패 시)
        """
        try:
            kind = data.get("kind")
            if kind != self.KIND_POST:
                logger.debug(f"Expected t3 (post), got {kind}")
                return None

            post_data = data.get("data", {})
            if not post_data:
                return None

            # 작성자 처리 (삭제된 경우 None 또는 "[deleted]")
            author = post_data.get("author", "[deleted]")
            if author is None:
                author = "[deleted]"

            # 생성 시간 처리
            created_utc = post_data.get("created_utc", 0)
            created_dt = datetime.fromtimestamp(created_utc, tz=UTC)

            # permalink 처리 (상대 경로인 경우 전체 URL로 변환)
            permalink = post_data.get("permalink", "")
            if permalink and not permalink.startswith("http"):
                permalink = f"https://reddit.com{permalink}"

            return Post(
                id=post_data.get("id", ""),
                title=post_data.get("title", ""),
                selftext=post_data.get("selftext") or "",
                author=author,
                subreddit=post_data.get("subreddit", ""),
                score=post_data.get("score", 0),
                num_comments=post_data.get("num_comments", 0),
                created_utc=created_dt,
                url=post_data.get("url", ""),
                permalink=permalink,
                is_self=post_data.get("is_self", False),
            )

        except Exception as e:
            logger.error(f"Failed to parse post: {e}")
            return None

    def parse_comment(self, data: dict[str, Any]) -> Comment | None:
        """JSON 데이터를 Comment 모델로 변환.

        Args:
            data: Comment 데이터 {"kind": "t1", "data": {...}}

        Returns:
            Comment 모델 또는 None (파싱 실패 시)
        """
        try:
            kind = data.get("kind")
            if kind != self.KIND_COMMENT:
                logger.debug(f"Expected t1 (comment), got {kind}")
                return None

            comment_data = data.get("data", {})
            if not comment_data:
                return None

            # 삭제된 댓글 스킵 ([deleted] body)
            body = comment_data.get("body", "")
            if body in ("[deleted]", "[removed]"):
                logger.debug(f"Skipping deleted/removed comment: {comment_data.get('id')}")
                return None

            # 작성자 처리
            author = comment_data.get("author", "[deleted]")
            if author is None:
                author = "[deleted]"

            # 생성 시간 처리
            created_utc = comment_data.get("created_utc", 0)
            created_dt = datetime.fromtimestamp(created_utc, tz=UTC)

            # post_id 추출 (link_id는 "t3_xxxxx" 형식)
            link_id = comment_data.get("link_id", "")
            post_id = link_id[3:] if link_id.startswith("t3_") else link_id

            return Comment(
                id=comment_data.get("id", ""),
                body=body,
                author=author,
                subreddit=comment_data.get("subreddit", ""),
                score=comment_data.get("score", 0),
                created_utc=created_dt,
                parent_id=comment_data.get("parent_id", ""),
                post_id=post_id,
            )

        except Exception as e:
            logger.error(f"Failed to parse comment: {e}")
            return None

    def parse_subreddit(self, data: dict[str, Any]) -> SubredditInfo | None:
        """JSON 데이터를 SubredditInfo 모델로 변환.

        Args:
            data: Subreddit 데이터 {"kind": "t5", "data": {...}} 또는 about 응답

        Returns:
            SubredditInfo 모델 또는 None (파싱 실패 시)
        """
        try:
            # about.json 응답 또는 검색 결과 처리
            kind = data.get("kind")
            if kind == self.KIND_SUBREDDIT:
                subreddit_data = data.get("data", {})
            elif kind == self.KIND_LISTING:
                # Listing 응답의 경우 첫 번째 항목 사용
                children = self.parse_listing(data)
                if children:
                    return self.parse_subreddit(children[0])
                return None
            else:
                # about 응답은 직접 data 필드 포함
                subreddit_data = data.get("data", data)

            if not subreddit_data:
                return None

            # 생성 시간 처리
            created_utc = subreddit_data.get("created_utc", 0)
            created_dt = datetime.fromtimestamp(created_utc, tz=UTC)

            return SubredditInfo(
                name=subreddit_data.get("name", ""),
                display_name=subreddit_data.get("display_name", ""),
                title=subreddit_data.get("title") or "",
                description=subreddit_data.get("public_description") or "",
                subscribers=subreddit_data.get("subscribers") or 0,
                created_utc=created_dt,
                over18=subreddit_data.get("over18", False),
            )

        except Exception as e:
            logger.error(f"Failed to parse subreddit: {e}")
            return None


def extract_posts_from_response(response: dict[str, Any]) -> list[Post]:
    """Listing 응답에서 모든 Post 추출.

    Args:
        response: Reddit Listing 응답

    Returns:
        Post 모델 리스트
    """
    parser = RedditJSONParser()
    children = parser.parse_listing(response)

    posts: list[Post] = []
    for child in children:
        post = parser.parse_post(child)
        if post is not None:
            posts.append(post)

    return posts


def extract_comments_from_response(response: list[Any]) -> list[Comment]:
    """댓글 응답에서 모든 Comment 추출.

    Reddit의 /comments/{post_id}.json 응답은 [post_listing, comments_listing] 형태입니다.
    댓글은 중첩된 트리 구조로 되어 있어 평탄화가 필요합니다.

    Args:
        response: Reddit comments 응답 리스트 [post_listing, comments_listing]

    Returns:
        Comment 모델 리스트 (평탄화됨)
    """
    if not isinstance(response, list) or len(response) < 2:
        logger.warning(f"Expected [post, comments] list, got {type(response)}")
        return []

    parser = RedditJSONParser()
    comments_listing = response[1]
    children = parser.parse_listing(comments_listing)

    return _flatten_comment_tree(parser, children)


def _flatten_comment_tree(
    parser: RedditJSONParser, children: list[dict[str, Any]]
) -> list[Comment]:
    """중첩된 댓글 트리를 평탄화.

    Args:
        parser: RedditJSONParser 인스턴스
        children: 댓글 children 리스트

    Returns:
        평탄화된 Comment 리스트
    """
    comments: list[Comment] = []

    for child in children:
        kind = child.get("kind")

        # "more" 타입은 스킵 (추가 댓글 로드 필요 표시)
        if kind == RedditJSONParser.KIND_MORE:
            continue

        # 댓글 파싱
        comment = parser.parse_comment(child)
        if comment is not None:
            comments.append(comment)

        # replies 처리 (재귀적으로 중첩 댓글 평탄화)
        child_data = child.get("data", {})
        replies = child_data.get("replies")

        # replies가 빈 문자열이거나 None인 경우 스킵
        if replies and isinstance(replies, dict):
            nested_children = parser.parse_listing(replies)
            nested_comments = _flatten_comment_tree(parser, nested_children)
            comments.extend(nested_comments)

    return comments
