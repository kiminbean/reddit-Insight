"""요청 속도 제어를 위한 Rate Limiter.

Reddit 스크래핑 시 차단을 방지하기 위해 요청 속도를 제어합니다.
슬라이딩 윈도우 기반으로 분당 요청 수를 제한하고,
최소 요청 간격을 보장합니다.
"""

from __future__ import annotations

import asyncio
import time
from typing import Self


class RateLimiter:
    """슬라이딩 윈도우 기반 Rate Limiter.

    Reddit 스크래핑은 보수적으로 30 req/min을 기본값으로 사용합니다.
    (공식 API 60 req/min보다 느리게 설정)

    Attributes:
        requests_per_minute: 분당 최대 요청 수
        min_delay: 요청 간 최소 대기 시간 (초)

    Example:
        >>> limiter = RateLimiter(requests_per_minute=30, min_delay=1.0)
        >>> async with limiter:
        ...     # 요청 실행
        ...     pass
    """

    def __init__(
        self,
        requests_per_minute: int = 30,
        min_delay: float = 1.0,
    ) -> None:
        """Rate Limiter 초기화.

        Args:
            requests_per_minute: 분당 최대 요청 수 (기본: 30)
            min_delay: 요청 간 최소 대기 시간 초 (기본: 1.0)
        """
        self.requests_per_minute = requests_per_minute
        self.min_delay = min_delay

        # 슬라이딩 윈도우 상태
        self._window_start: float = time.monotonic()
        self._request_count: int = 0
        self._last_request_time: float = 0.0

        # 동기화를 위한 락
        self._lock = asyncio.Lock()

    async def wait(self) -> None:
        """다음 요청까지 필요한 시간만큼 대기.

        1. 최소 요청 간격 확인
        2. 슬라이딩 윈도우 내 요청 수 확인
        3. 필요시 대기
        """
        async with self._lock:
            current_time = time.monotonic()

            # 최소 요청 간격 대기
            if self._last_request_time > 0:
                elapsed_since_last = current_time - self._last_request_time
                if elapsed_since_last < self.min_delay:
                    await asyncio.sleep(self.min_delay - elapsed_since_last)
                    current_time = time.monotonic()

            # 슬라이딩 윈도우 체크 (60초 윈도우)
            window_elapsed = current_time - self._window_start
            if window_elapsed >= 60.0:
                # 윈도우 리셋
                self._window_start = current_time
                self._request_count = 0
            elif self._request_count >= self.requests_per_minute:
                # 분당 요청 수 초과 - 윈도우가 끝날 때까지 대기
                wait_time = 60.0 - window_elapsed
                await asyncio.sleep(wait_time)
                # 윈도우 리셋
                self._window_start = time.monotonic()
                self._request_count = 0

            # 요청 기록
            self._request_count += 1
            self._last_request_time = time.monotonic()

    async def __aenter__(self) -> Self:
        """컨텍스트 매니저 진입 시 자동 대기."""
        await self.wait()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """컨텍스트 매니저 종료."""
        pass

    @property
    def request_count(self) -> int:
        """현재 윈도우 내 요청 수."""
        return self._request_count

    def reset(self) -> None:
        """Rate Limiter 상태 초기화."""
        self._window_start = time.monotonic()
        self._request_count = 0
        self._last_request_time = 0.0
