"""웹 스크래핑을 위한 HTTP 클라이언트.

User-Agent 로테이션과 재시도 로직을 포함한 HTTP 클라이언트입니다.
Reddit 스크래핑 시 차단을 방지하기 위한 기능들을 제공합니다.
"""

from __future__ import annotations

import asyncio
import logging
import random
from typing import Any, Self

import httpx

from reddit_insight.scraping.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


# 일반적인 브라우저 User-Agent 문자열 (로테이션용)
USER_AGENTS: list[str] = [
    # Chrome (Windows)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    # Chrome (macOS)
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    # Firefox (Windows)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    # Firefox (macOS)
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0",
    # Safari (macOS)
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    # Edge (Windows)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
]


class ScrapingError(Exception):
    """스크래핑 중 발생한 오류."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class ScrapingClient:
    """User-Agent 로테이션 및 재시도를 지원하는 HTTP 클라이언트.

    Reddit 스크래핑 시 차단을 방지하기 위한 기능들을 포함합니다:
    - User-Agent 로테이션
    - Rate limiting
    - 재시도 로직 (exponential backoff)

    Attributes:
        rate_limiter: 요청 속도 제어기
        max_retries: 최대 재시도 횟수
        base_delay: 재시도 시 기본 대기 시간

    Example:
        >>> async with ScrapingClient() as client:
        ...     response = await client.get("https://old.reddit.com/r/python")
        ...     html = response.text
    """

    def __init__(
        self,
        rate_limiter: RateLimiter | None = None,
        max_retries: int = 3,
        base_delay: float = 1.0,
        timeout: float = 30.0,
    ) -> None:
        """ScrapingClient 초기화.

        Args:
            rate_limiter: 요청 속도 제어기 (없으면 기본값 사용)
            max_retries: 최대 재시도 횟수 (기본: 3)
            base_delay: 재시도 시 기본 대기 시간 초 (기본: 1.0)
            timeout: 요청 타임아웃 초 (기본: 30.0)
        """
        self.rate_limiter = rate_limiter or RateLimiter()
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.timeout = timeout

        # User-Agent 로테이션 상태
        self._user_agents: list[str] = USER_AGENTS.copy()
        self._current_ua_index: int = 0

        # httpx 클라이언트 (lazy init)
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """httpx 클라이언트 반환 (lazy initialization)."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                follow_redirects=True,
            )
        return self._client

    def _rotate_user_agent(self) -> str:
        """User-Agent를 로테이션하여 반환.

        순차적 로테이션과 약간의 무작위성을 조합하여
        패턴 감지를 어렵게 합니다.
        """
        # 20% 확률로 무작위 선택
        if random.random() < 0.2:
            return random.choice(self._user_agents)

        # 순차 로테이션
        user_agent = self._user_agents[self._current_ua_index]
        self._current_ua_index = (self._current_ua_index + 1) % len(self._user_agents)
        return user_agent

    def _get_headers(self) -> dict[str, str]:
        """요청에 사용할 헤더 생성."""
        return {
            "User-Agent": self._rotate_user_agent(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
        }

    async def get(
        self,
        url: str,
        params: dict[str, Any] | None = None,
    ) -> httpx.Response:
        """GET 요청 수행.

        Rate limiting과 재시도 로직이 적용됩니다.

        Args:
            url: 요청 URL
            params: 쿼리 파라미터 (선택)

        Returns:
            httpx.Response 객체

        Raises:
            ScrapingError: 모든 재시도 실패 시
        """
        client = await self._get_client()
        last_error: Exception | None = None

        for attempt in range(self.max_retries):
            try:
                # Rate limiting 대기
                await self.rate_limiter.wait()

                # 요청 실행
                headers = self._get_headers()
                response = await client.get(url, params=params, headers=headers)

                # 429 (Too Many Requests) 처리
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    logger.warning(
                        f"Rate limited (429). Waiting {retry_after}s. Attempt {attempt + 1}/{self.max_retries}"
                    )
                    await asyncio.sleep(retry_after)
                    continue

                # 5xx 서버 오류는 재시도
                if response.status_code >= 500:
                    logger.warning(
                        f"Server error ({response.status_code}). Attempt {attempt + 1}/{self.max_retries}"
                    )
                    delay = self.base_delay * (2**attempt)  # Exponential backoff
                    await asyncio.sleep(delay)
                    continue

                # 성공 또는 클라이언트 오류 (재시도 불필요)
                return response

            except httpx.TimeoutException as e:
                last_error = e
                logger.warning(f"Request timeout. Attempt {attempt + 1}/{self.max_retries}")
                delay = self.base_delay * (2**attempt)
                await asyncio.sleep(delay)

            except httpx.RequestError as e:
                last_error = e
                logger.warning(f"Request error: {e}. Attempt {attempt + 1}/{self.max_retries}")
                delay = self.base_delay * (2**attempt)
                await asyncio.sleep(delay)

        # 모든 재시도 실패
        error_msg = f"Failed after {self.max_retries} attempts: {last_error}"
        raise ScrapingError(error_msg)

    async def get_json(self, url: str) -> dict[str, Any]:
        """JSON 응답을 요청하고 파싱.

        Reddit의 .json URL을 사용한 비공식 API 접근에 유용합니다.

        Args:
            url: 요청 URL (자동으로 .json이 추가되지 않음)

        Returns:
            파싱된 JSON 딕셔너리

        Raises:
            ScrapingError: 요청 실패 또는 JSON 파싱 실패 시
        """
        response = await self.get(url)

        if response.status_code != 200:
            raise ScrapingError(
                f"Request failed with status {response.status_code}",
                status_code=response.status_code,
            )

        try:
            return response.json()
        except Exception as e:
            raise ScrapingError(f"Failed to parse JSON: {e}") from e

    async def close(self) -> None:
        """HTTP 클라이언트 닫기."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> Self:
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
