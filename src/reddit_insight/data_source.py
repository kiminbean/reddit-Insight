"""통합 데이터 소스.

API와 스크래핑 간 자동 전환 로직을 제공합니다.
API 실패/제한 시 자동으로 스크래핑으로 폴백합니다.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable, TypeVar

if TYPE_CHECKING:
    from reddit_insight.reddit.client import RedditClient
    from reddit_insight.reddit.models import Comment, Post, SubredditInfo
    from reddit_insight.scraping.reddit_scraper import RedditScraper

logger = logging.getLogger(__name__)


# ========== 전략 열거형 ==========


class DataSourceStrategy(Enum):
    """데이터 소스 전략.

    어떤 데이터 소스를 우선 사용할지 결정합니다.

    Values:
        API_ONLY: API만 사용 (실패 시 에러 발생)
        SCRAPING_ONLY: 스크래핑만 사용 (실패 시 에러 발생)
        API_FIRST: API 우선, 실패 시 스크래핑으로 폴백 (기본값)
        SCRAPING_FIRST: 스크래핑 우선, 실패 시 API로 폴백
    """

    API_ONLY = "api_only"
    SCRAPING_ONLY = "scraping_only"
    API_FIRST = "api_first"
    SCRAPING_FIRST = "scraping_first"


# ========== 예외 클래스 ==========


class DataSourceError(Exception):
    """모든 데이터 소스 실패 시 발생하는 예외.

    API와 스크래핑 모두 실패한 경우 발생합니다.
    """

    pass


class APIUnavailableError(DataSourceError):
    """API 사용 불가 예외.

    API 연결 실패, 인증 오류, rate limit 등의 경우 발생합니다.
    """

    pass


class ScrapingUnavailableError(DataSourceError):
    """스크래핑 사용 불가 예외.

    스크래핑 요청 실패, 파싱 오류 등의 경우 발생합니다.
    """

    pass


# ========== 상태 추적 ==========


@dataclass
class SourceStatus:
    """데이터 소스 상태 추적.

    각 데이터 소스의 가용성 및 실패 이력을 추적합니다.
    연속 실패 횟수를 기반으로 일시적 비활성화를 결정합니다.

    Attributes:
        api_available: API 사용 가능 여부
        scraping_available: 스크래핑 사용 가능 여부
        last_api_error: 마지막 API 에러 메시지
        last_scraping_error: 마지막 스크래핑 에러 메시지
        api_failure_count: API 연속 실패 횟수
        scraping_failure_count: 스크래핑 연속 실패 횟수
    """

    api_available: bool = True
    scraping_available: bool = True
    last_api_error: str | None = None
    last_scraping_error: str | None = None
    api_failure_count: int = 0
    scraping_failure_count: int = 0

    # 연속 실패 횟수 임계값 (이상이면 일시적 비활성화)
    FAILURE_THRESHOLD: int = field(default=5, repr=False)

    def is_api_temporarily_disabled(self) -> bool:
        """API가 일시적으로 비활성화되었는지 확인."""
        return self.api_failure_count >= self.FAILURE_THRESHOLD

    def is_scraping_temporarily_disabled(self) -> bool:
        """스크래핑이 일시적으로 비활성화되었는지 확인."""
        return self.scraping_failure_count >= self.FAILURE_THRESHOLD

    def reset_api_failures(self) -> None:
        """API 실패 카운트 리셋."""
        self.api_failure_count = 0
        self.last_api_error = None

    def reset_scraping_failures(self) -> None:
        """스크래핑 실패 카운트 리셋."""
        self.scraping_failure_count = 0
        self.last_scraping_error = None


# ========== 통합 데이터 소스 ==========


class UnifiedDataSource:
    """통합 데이터 소스.

    API와 스크래핑을 투명하게 전환하며 데이터를 수집합니다.
    사용자는 데이터 소스를 신경 쓰지 않고 데이터를 수집할 수 있습니다.

    Attributes:
        strategy: 데이터 소스 전략

    Example:
        >>> ds = UnifiedDataSource(strategy=DataSourceStrategy.API_FIRST)
        >>> posts = await ds.get_hot_posts("python", limit=50)
        >>> for post in posts:
        ...     print(post.title)
    """

    # 폴백을 트리거하는 예외 패턴
    # rate limit, 인증 실패, 네트워크 오류 등
    FALLBACK_EXCEPTIONS = (
        "rate limit",
        "too many requests",
        "429",
        "401",
        "403",
        "authentication",
        "unauthorized",
        "forbidden",
        "connection",
        "timeout",
        "network",
    )

    def __init__(
        self,
        strategy: DataSourceStrategy = DataSourceStrategy.API_FIRST,
    ) -> None:
        """UnifiedDataSource 초기화.

        Args:
            strategy: 데이터 소스 전략 (기본: API_FIRST)
        """
        self._strategy = strategy
        self._status = SourceStatus()

        # Lazy initialization
        self._api_client: RedditClient | None = None
        self._scraper: RedditScraper | None = None

    @property
    def strategy(self) -> DataSourceStrategy:
        """현재 데이터 소스 전략."""
        return self._strategy

    @strategy.setter
    def strategy(self, value: DataSourceStrategy) -> None:
        """데이터 소스 전략 변경."""
        self._strategy = value

    def get_status(self) -> SourceStatus:
        """현재 데이터 소스 상태 반환."""
        return self._status

    def _get_api_client(self) -> "RedditClient":
        """API 클라이언트 반환 (lazy initialization).

        Returns:
            RedditClient: Reddit API 클라이언트

        Raises:
            APIUnavailableError: API 클라이언트 생성 실패
        """
        if self._api_client is None:
            try:
                from reddit_insight.reddit.client import RedditClient

                self._api_client = RedditClient()
                self._api_client.connect()
                logger.info("API 클라이언트 초기화 완료")
            except Exception as e:
                logger.error(f"API 클라이언트 초기화 실패: {e}")
                self._status.api_available = False
                self._status.last_api_error = str(e)
                raise APIUnavailableError(f"API 클라이언트 초기화 실패: {e}") from e

        return self._api_client

    def _get_scraper(self) -> "RedditScraper":
        """스크래퍼 반환 (lazy initialization).

        Returns:
            RedditScraper: Reddit 스크래퍼

        Raises:
            ScrapingUnavailableError: 스크래퍼 생성 실패
        """
        if self._scraper is None:
            try:
                from reddit_insight.scraping.reddit_scraper import RedditScraper

                self._scraper = RedditScraper()
                logger.info("스크래퍼 초기화 완료")
            except Exception as e:
                logger.error(f"스크래퍼 초기화 실패: {e}")
                self._status.scraping_available = False
                self._status.last_scraping_error = str(e)
                raise ScrapingUnavailableError(f"스크래퍼 초기화 실패: {e}") from e

        return self._scraper

    def _should_use_api(self) -> bool:
        """API를 사용해야 하는지 결정.

        전략과 현재 상태를 기반으로 API 사용 여부를 결정합니다.

        Returns:
            bool: API를 사용해야 하면 True
        """
        # API_ONLY 또는 API_FIRST 전략
        if self._strategy in (
            DataSourceStrategy.API_ONLY,
            DataSourceStrategy.API_FIRST,
        ):
            # API가 일시적으로 비활성화되지 않았는지 확인
            if not self._status.is_api_temporarily_disabled():
                return True

        # SCRAPING_FIRST 전략에서 스크래핑이 비활성화된 경우
        if self._strategy == DataSourceStrategy.SCRAPING_FIRST:
            if self._status.is_scraping_temporarily_disabled():
                return True

        return False

    def _should_use_scraping(self) -> bool:
        """스크래핑을 사용해야 하는지 결정.

        전략과 현재 상태를 기반으로 스크래핑 사용 여부를 결정합니다.

        Returns:
            bool: 스크래핑을 사용해야 하면 True
        """
        # SCRAPING_ONLY 또는 SCRAPING_FIRST 전략
        if self._strategy in (
            DataSourceStrategy.SCRAPING_ONLY,
            DataSourceStrategy.SCRAPING_FIRST,
        ):
            # 스크래핑이 일시적으로 비활성화되지 않았는지 확인
            if not self._status.is_scraping_temporarily_disabled():
                return True

        # API_FIRST 전략에서 API가 비활성화된 경우
        if self._strategy == DataSourceStrategy.API_FIRST:
            if self._status.is_api_temporarily_disabled():
                return True

        return False

    def _should_fallback_to_scraping(self, error: Exception) -> bool:
        """스크래핑으로 폴백해야 하는지 결정.

        에러 메시지를 분석하여 스크래핑으로 폴백해야 하는지 결정합니다.

        Args:
            error: 발생한 예외

        Returns:
            bool: 스크래핑으로 폴백해야 하면 True
        """
        # API_ONLY 전략이면 폴백하지 않음
        if self._strategy == DataSourceStrategy.API_ONLY:
            return False

        # SCRAPING_ONLY 전략이면 이미 스크래핑 사용 중
        if self._strategy == DataSourceStrategy.SCRAPING_ONLY:
            return False

        # 에러 메시지 확인
        error_msg = str(error).lower()
        for pattern in self.FALLBACK_EXCEPTIONS:
            if pattern in error_msg:
                logger.info(f"폴백 트리거 감지: {pattern}")
                return True

        # 그 외의 경우도 폴백 시도 (안전하게)
        return True

    def _should_fallback_to_api(self, error: Exception) -> bool:
        """API로 폴백해야 하는지 결정.

        에러 메시지를 분석하여 API로 폴백해야 하는지 결정합니다.

        Args:
            error: 발생한 예외

        Returns:
            bool: API로 폴백해야 하면 True
        """
        # SCRAPING_ONLY 전략이면 폴백하지 않음
        if self._strategy == DataSourceStrategy.SCRAPING_ONLY:
            return False

        # API_ONLY 전략이면 이미 API 사용 중
        if self._strategy == DataSourceStrategy.API_ONLY:
            return False

        return True

    def _record_api_failure(self, error: Exception) -> None:
        """API 실패 기록.

        Args:
            error: 발생한 예외
        """
        self._status.api_failure_count += 1
        self._status.last_api_error = str(error)
        logger.warning(
            f"API 실패 ({self._status.api_failure_count}회): {error}"
        )

        if self._status.is_api_temporarily_disabled():
            logger.warning(
                f"API 일시적 비활성화 "
                f"({self._status.FAILURE_THRESHOLD}회 연속 실패)"
            )

    def _record_scraping_failure(self, error: Exception) -> None:
        """스크래핑 실패 기록.

        Args:
            error: 발생한 예외
        """
        self._status.scraping_failure_count += 1
        self._status.last_scraping_error = str(error)
        logger.warning(
            f"스크래핑 실패 ({self._status.scraping_failure_count}회): {error}"
        )

        if self._status.is_scraping_temporarily_disabled():
            logger.warning(
                f"스크래핑 일시적 비활성화 "
                f"({self._status.FAILURE_THRESHOLD}회 연속 실패)"
            )

    def _record_api_success(self) -> None:
        """API 성공 기록."""
        if self._status.api_failure_count > 0:
            logger.info("API 성공 - 실패 카운트 리셋")
        self._status.reset_api_failures()
        self._status.api_available = True

    def _record_scraping_success(self) -> None:
        """스크래핑 성공 기록."""
        if self._status.scraping_failure_count > 0:
            logger.info("스크래핑 성공 - 실패 카운트 리셋")
        self._status.reset_scraping_failures()
        self._status.scraping_available = True

    async def close(self) -> None:
        """리소스 정리."""
        if self._api_client is not None:
            self._api_client.close()
            self._api_client = None

        if self._scraper is not None:
            await self._scraper.close()
            self._scraper = None

        logger.info("UnifiedDataSource 리소스 정리 완료")

    async def __aenter__(self) -> "UnifiedDataSource":
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

    def __repr__(self) -> str:
        """문자열 표현."""
        return (
            f"UnifiedDataSource("
            f"strategy={self._strategy.value}, "
            f"api_failures={self._status.api_failure_count}, "
            f"scraping_failures={self._status.scraping_failure_count})"
        )
