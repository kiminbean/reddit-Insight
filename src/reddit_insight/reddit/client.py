"""Reddit API 클라이언트.

PRAW 기반 Reddit API 클라이언트를 제공한다.
OAuth2 인증을 지원하며, 자격증명이 없는 경우 read-only 모드로 동작한다.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import TYPE_CHECKING

import praw

from reddit_insight.config import Settings, get_settings
from reddit_insight.reddit.auth import (
    DEFAULT_USER_AGENT,
    AuthenticationError,
    RedditAuth,
)

if TYPE_CHECKING:
    from praw.models import Subreddit

logger = logging.getLogger(__name__)


class RedditClient:
    """Reddit API 클라이언트.

    PRAW를 래핑하여 Reddit API 접근을 제공한다.
    자격증명이 없는 경우 read-only 모드로 동작하여
    공개 데이터에 대한 읽기 접근만 가능하다.

    Attributes:
        settings: 애플리케이션 설정
        auth: 인증 정보

    Example:
        >>> client = RedditClient()
        >>> client.connect()
        >>> subreddit = client.get_subreddit("python")
        >>> print(subreddit.display_name)
        Python
    """

    def __init__(self, settings: Settings | None = None) -> None:
        """RedditClient 초기화.

        Args:
            settings: 애플리케이션 설정. None이면 get_settings() 사용.
        """
        self._settings = settings or get_settings()
        self._praw: praw.Reddit | None = None
        self._auth = RedditAuth(
            client_id=self._settings.reddit_client_id,
            client_secret=self._settings.reddit_client_secret,
            user_agent=self._settings.reddit_user_agent or DEFAULT_USER_AGENT,
        )

    @property
    def is_connected(self) -> bool:
        """PRAW 인스턴스 연결 여부.

        Returns:
            bool: 연결되어 있으면 True
        """
        return self._praw is not None

    @property
    def is_read_only(self) -> bool:
        """Read-only 모드 여부.

        Returns:
            bool: 인증되지 않은 read-only 모드면 True
        """
        if self._praw is None:
            return True
        return self._praw.read_only

    @property
    def settings(self) -> Settings:
        """설정 객체 반환."""
        return self._settings

    @property
    def auth(self) -> RedditAuth:
        """인증 정보 반환."""
        return self._auth

    def connect(self, *, read_only: bool | None = None) -> None:
        """Reddit API에 연결.

        자격증명이 설정되어 있으면 OAuth2 인증으로 연결하고,
        그렇지 않으면 read-only 모드로 연결한다.

        Args:
            read_only: True면 강제로 read-only 모드로 연결.
                      None이면 자격증명 유무에 따라 자동 결정.

        Raises:
            AuthenticationError: 인증에 실패한 경우
        """
        if self._praw is not None:
            logger.debug("이미 연결되어 있습니다")
            return

        # read-only 모드 결정
        use_read_only = read_only
        if use_read_only is None:
            use_read_only = not self._auth.is_configured

        try:
            if use_read_only:
                # Read-only 모드: 인증 없이 공개 데이터 접근
                logger.info("Reddit API에 read-only 모드로 연결합니다")
                self._praw = praw.Reddit(
                    client_id=self._auth.client_id or "reddit_insight_readonly",
                    client_secret=self._auth.client_secret or "",
                    user_agent=self._auth.user_agent,
                )
                # 명시적으로 read_only 설정
                self._praw.read_only = True
            else:
                # OAuth2 인증 모드
                self._auth.validate()
                logger.info("Reddit API에 OAuth2로 연결합니다")
                self._praw = praw.Reddit(
                    client_id=self._auth.client_id,
                    client_secret=self._auth.client_secret,
                    user_agent=self._auth.user_agent,
                )

            logger.info(
                "Reddit API 연결 성공 (read_only=%s)", self._praw.read_only
            )

        except Exception as e:
            logger.error("Reddit API 연결 실패: %s", e)
            raise AuthenticationError(f"Reddit API 연결 실패: {e}") from e

    def _ensure_connected(self) -> praw.Reddit:
        """연결 확인 및 PRAW 인스턴스 반환.

        연결되어 있지 않으면 자동으로 연결을 시도한다.

        Returns:
            praw.Reddit: PRAW 인스턴스

        Raises:
            AuthenticationError: 연결에 실패한 경우
        """
        if self._praw is None:
            self.connect()
        # connect() 이후에도 None일 수 없지만 타입 체커를 위해 검사
        if self._praw is None:
            raise AuthenticationError("Reddit API에 연결되지 않았습니다")
        return self._praw

    def get_subreddit(self, name: str) -> Subreddit:
        """서브레딧 객체 반환.

        Args:
            name: 서브레딧 이름 (예: "python", "datascience")

        Returns:
            Subreddit: PRAW Subreddit 객체
        """
        reddit = self._ensure_connected()
        return reddit.subreddit(name)

    def search_subreddits(
        self,
        query: str,
        *,
        limit: int = 10,
    ) -> list[Subreddit]:
        """서브레딧 검색.

        Args:
            query: 검색어
            limit: 최대 결과 수 (기본: 10)

        Returns:
            list[Subreddit]: 검색된 서브레딧 목록
        """
        reddit = self._ensure_connected()
        return list(reddit.subreddits.search(query, limit=limit))

    def close(self) -> None:
        """연결 종료.

        PRAW는 명시적인 연결 종료가 필요하지 않지만,
        리소스 정리를 위해 호출할 수 있다.
        """
        self._praw = None
        logger.info("Reddit API 연결이 종료되었습니다")

    def __repr__(self) -> str:
        """문자열 표현."""
        status = "connected" if self.is_connected else "disconnected"
        mode = "read_only" if self.is_read_only else "authenticated"
        return f"RedditClient(status={status}, mode={mode})"


@lru_cache(maxsize=1)
def get_reddit_client(settings: Settings | None = None) -> RedditClient:
    """RedditClient 싱글톤 인스턴스 반환.

    동일한 설정으로 여러 번 호출해도 같은 인스턴스를 반환한다.

    Args:
        settings: 애플리케이션 설정. None이면 get_settings() 사용.

    Returns:
        RedditClient: RedditClient 싱글톤 인스턴스

    Note:
        lru_cache는 hashable한 인자만 캐싱하므로,
        settings=None으로 호출해야 싱글톤이 보장된다.
    """
    return RedditClient(settings)
