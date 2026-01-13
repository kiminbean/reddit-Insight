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
