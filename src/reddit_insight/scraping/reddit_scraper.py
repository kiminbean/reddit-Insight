"""Reddit 스크래퍼.

old.reddit.com의 JSON 엔드포인트를 사용하여 Reddit 데이터를 수집합니다.
API 제한 시 백업 수단으로 사용됩니다.

URL 패턴:
- https://old.reddit.com/r/{subreddit}/hot.json
- https://old.reddit.com/r/{subreddit}/new.json
- https://old.reddit.com/r/{subreddit}/top.json?t={time}
- https://old.reddit.com/comments/{post_id}.json
"""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlencode

from reddit_insight.reddit.models import Comment, Post, SubredditInfo
from reddit_insight.scraping.http_client import ScrapingClient
from reddit_insight.scraping.parser import (
    RedditJSONParser,
    extract_comments_from_response,
    extract_posts_from_response,
)

logger = logging.getLogger(__name__)


class RedditScraper:
    """Reddit JSON 엔드포인트를 사용한 데이터 수집기.

    old.reddit.com의 비공식 JSON API를 사용하여 게시물, 댓글,
    서브레딧 정보를 수집합니다.

    Attributes:
        BASE_URL: Reddit 베이스 URL (old.reddit.com)

    Example:
        >>> async with ScrapingClient() as client:
        ...     scraper = RedditScraper(client)
        ...     posts = await scraper.get_hot("python", limit=50)
        ...     for post in posts:
        ...         print(post.title)
    """

    BASE_URL = "https://old.reddit.com"
    MAX_PER_REQUEST = 100  # Reddit API 한 요청당 최대 개수

    def __init__(self, client: ScrapingClient | None = None) -> None:
        """RedditScraper 초기화.

        Args:
            client: HTTP 클라이언트 (없으면 새로 생성)
        """
        self._client = client or ScrapingClient()
        self._parser = RedditJSONParser()
        self._owns_client = client is None  # 클라이언트 소유 여부 (cleanup용)

    async def close(self) -> None:
        """리소스 정리.

        자체 생성한 클라이언트만 닫습니다.
        """
        if self._owns_client:
            await self._client.close()

    async def __aenter__(self) -> "RedditScraper":
        """비동기 컨텍스트 매니저 진입."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """비동기 컨텍스트 매니저 종료."""
        await self.close()

    def _build_subreddit_url(
        self, subreddit: str, sort: str, params: dict[str, Any] | None = None
    ) -> str:
        """서브레딧 URL 생성.

        Args:
            subreddit: 서브레딧 이름
            sort: 정렬 방식 (hot, new, top, rising)
            params: 추가 쿼리 파라미터

        Returns:
            완성된 URL 문자열
        """
        base = f"{self.BASE_URL}/r/{subreddit}/{sort}.json"
        if params:
            return f"{base}?{urlencode(params)}"
        return base

    async def _fetch_posts(self, url: str, limit: int) -> list[Post]:
        """URL에서 게시물 수집.

        limit가 100을 초과하면 여러 요청으로 페이지네이션 처리합니다.

        Args:
            url: 요청 URL (기본 파라미터 제외)
            limit: 수집할 게시물 수

        Returns:
            Post 모델 리스트
        """
        posts: list[Post] = []
        after: str | None = None

        while len(posts) < limit:
            # 이번 요청에서 가져올 개수 계산
            remaining = limit - len(posts)
            fetch_count = min(remaining, self.MAX_PER_REQUEST)

            # 파라미터 구성
            params: dict[str, Any] = {"limit": fetch_count}
            if after:
                params["after"] = after

            # URL 구성 (기존 파라미터 유지)
            if "?" in url:
                request_url = f"{url}&{urlencode(params)}"
            else:
                request_url = f"{url}?{urlencode(params)}"

            logger.debug(f"Fetching posts: {request_url}")

            try:
                response = await self._client.get_json(request_url)
            except Exception as e:
                logger.error(f"Failed to fetch posts: {e}")
                break

            # 게시물 추출
            new_posts = extract_posts_from_response(response)
            posts.extend(new_posts)

            # 다음 페이지 토큰 확인
            after = self._parser.get_after_token(response)
            if not after:
                # 더 이상 페이지 없음
                break

            # 빈 응답 방어
            if not new_posts:
                logger.debug("No more posts available")
                break

        return posts[:limit]  # 정확한 limit 반환

    async def get_hot(self, subreddit: str, limit: int = 100) -> list[Post]:
        """Hot 게시물 수집.

        Args:
            subreddit: 서브레딧 이름
            limit: 수집할 게시물 수 (기본: 100)

        Returns:
            Post 모델 리스트
        """
        url = self._build_subreddit_url(subreddit, "hot")
        return await self._fetch_posts(url, limit)

    async def get_new(self, subreddit: str, limit: int = 100) -> list[Post]:
        """New 게시물 수집.

        Args:
            subreddit: 서브레딧 이름
            limit: 수집할 게시물 수 (기본: 100)

        Returns:
            Post 모델 리스트
        """
        url = self._build_subreddit_url(subreddit, "new")
        return await self._fetch_posts(url, limit)

    async def get_top(
        self,
        subreddit: str,
        time_filter: str = "week",
        limit: int = 100,
    ) -> list[Post]:
        """Top 게시물 수집.

        Args:
            subreddit: 서브레딧 이름
            time_filter: 기간 필터 (hour, day, week, month, year, all)
            limit: 수집할 게시물 수 (기본: 100)

        Returns:
            Post 모델 리스트
        """
        url = self._build_subreddit_url(subreddit, "top", {"t": time_filter})
        return await self._fetch_posts(url, limit)

    async def get_rising(self, subreddit: str, limit: int = 100) -> list[Post]:
        """Rising 게시물 수집.

        Args:
            subreddit: 서브레딧 이름
            limit: 수집할 게시물 수 (기본: 100)

        Returns:
            Post 모델 리스트
        """
        url = self._build_subreddit_url(subreddit, "rising")
        return await self._fetch_posts(url, limit)

    # ========== 댓글 수집 메서드 ==========

    async def get_post_comments(
        self, post_id: str, limit: int = 500
    ) -> list[Comment]:
        """게시물의 댓글 수집.

        /comments/{post_id}.json 엔드포인트를 사용합니다.
        응답 구조는 [post_listing, comments_listing] 형태입니다.

        Args:
            post_id: 게시물 ID
            limit: 수집할 댓글 수 (기본: 500, 최대: 500)

        Returns:
            Comment 모델 리스트 (중첩 구조가 평탄화됨)
        """
        # Reddit은 댓글 limit 최대 500 지원
        effective_limit = min(limit, 500)

        url = f"{self.BASE_URL}/comments/{post_id}.json?limit={effective_limit}"
        logger.debug(f"Fetching comments: {url}")

        try:
            response = await self._client.get_json(url)
        except Exception as e:
            logger.error(f"Failed to fetch comments for post {post_id}: {e}")
            return []

        # 응답이 리스트 형태인지 확인
        if not isinstance(response, list):
            logger.warning(f"Unexpected response format for comments: {type(response)}")
            return []

        # 댓글 추출 및 평탄화
        comments = extract_comments_from_response(response)
        return comments[:limit]

    async def get_subreddit_comments(
        self, subreddit: str, limit: int = 100
    ) -> list[Comment]:
        """서브레딧의 최근 댓글 스트림 수집.

        /r/{subreddit}/comments.json 엔드포인트를 사용합니다.
        서브레딧에서 작성된 최근 댓글들을 가져옵니다.

        Args:
            subreddit: 서브레딧 이름
            limit: 수집할 댓글 수 (기본: 100)

        Returns:
            Comment 모델 리스트
        """
        comments: list[Comment] = []
        after: str | None = None

        while len(comments) < limit:
            # 이번 요청에서 가져올 개수 계산
            remaining = limit - len(comments)
            fetch_count = min(remaining, self.MAX_PER_REQUEST)

            # 파라미터 구성
            params: dict[str, Any] = {"limit": fetch_count}
            if after:
                params["after"] = after

            url = f"{self.BASE_URL}/r/{subreddit}/comments.json?{urlencode(params)}"
            logger.debug(f"Fetching subreddit comments: {url}")

            try:
                response = await self._client.get_json(url)
            except Exception as e:
                logger.error(f"Failed to fetch comments for r/{subreddit}: {e}")
                break

            # 댓글 추출
            children = self._parser.parse_listing(response)
            for child in children:
                comment = self._parser.parse_comment(child)
                if comment is not None:
                    comments.append(comment)

            # 다음 페이지 토큰 확인
            after = self._parser.get_after_token(response)
            if not after:
                break

            # 빈 응답 방어
            if not children:
                logger.debug("No more comments available")
                break

        return comments[:limit]

    def _flatten_comment_tree(
        self, children: list[dict[str, Any]]
    ) -> list[Comment]:
        """중첩된 댓글 트리를 평탄화.

        Args:
            children: 댓글 children 리스트

        Returns:
            평탄화된 Comment 리스트
        """
        comments: list[Comment] = []

        for child in children:
            kind = child.get("kind")

            # "more" 타입은 스킵
            if kind == RedditJSONParser.KIND_MORE:
                continue

            # 댓글 파싱
            comment = self._parser.parse_comment(child)
            if comment is not None:
                comments.append(comment)

            # replies 처리
            child_data = child.get("data", {})
            replies = child_data.get("replies")

            if replies and isinstance(replies, dict):
                nested_children = self._parser.parse_listing(replies)
                nested_comments = self._flatten_comment_tree(nested_children)
                comments.extend(nested_comments)

        return comments

    # ========== 서브레딧 정보 수집 메서드 ==========

    async def get_subreddit_info(self, name: str) -> SubredditInfo | None:
        """서브레딧 정보 수집.

        /r/{name}/about.json 엔드포인트를 사용합니다.

        Args:
            name: 서브레딧 이름

        Returns:
            SubredditInfo 모델 또는 None (존재하지 않는 경우)
        """
        url = f"{self.BASE_URL}/r/{name}/about.json"
        logger.debug(f"Fetching subreddit info: {url}")

        try:
            response = await self._client.get_json(url)
        except Exception as e:
            logger.error(f"Failed to fetch subreddit info for r/{name}: {e}")
            return None

        return self._parser.parse_subreddit(response)

    async def search_subreddits(
        self, query: str, limit: int = 25
    ) -> list[SubredditInfo]:
        """서브레딧 검색.

        /subreddits/search.json 엔드포인트를 사용합니다.

        Args:
            query: 검색어
            limit: 수집할 결과 수 (기본: 25)

        Returns:
            SubredditInfo 모델 리스트
        """
        subreddits: list[SubredditInfo] = []
        after: str | None = None

        while len(subreddits) < limit:
            # 이번 요청에서 가져올 개수 계산
            remaining = limit - len(subreddits)
            fetch_count = min(remaining, self.MAX_PER_REQUEST)

            # 파라미터 구성
            params: dict[str, Any] = {
                "q": query,
                "limit": fetch_count,
            }
            if after:
                params["after"] = after

            url = f"{self.BASE_URL}/subreddits/search.json?{urlencode(params)}"
            logger.debug(f"Searching subreddits: {url}")

            try:
                response = await self._client.get_json(url)
            except Exception as e:
                logger.error(f"Failed to search subreddits for '{query}': {e}")
                break

            # 서브레딧 추출
            children = self._parser.parse_listing(response)
            for child in children:
                subreddit = self._parser.parse_subreddit(child)
                if subreddit is not None:
                    subreddits.append(subreddit)

            # 다음 페이지 토큰 확인
            after = self._parser.get_after_token(response)
            if not after:
                break

            # 빈 응답 방어
            if not children:
                logger.debug("No more subreddits available")
                break

        return subreddits[:limit]
