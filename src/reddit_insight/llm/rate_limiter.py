"""LLM API Rate Limiter 모듈.

API 호출 제한을 관리하여 rate limit 초과를 방지한다.
"""

from __future__ import annotations

import asyncio
import time
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class RateLimiter:
    """API 호출 rate limiting을 관리한다.

    RPM(Requests Per Minute)과 TPM(Tokens Per Minute) 제한을 적용한다.
    슬라이딩 윈도우 방식으로 동작한다.
    """

    requests_per_minute: int = 60
    tokens_per_minute: int = 100000
    _request_times: list[float] = field(default_factory=list)
    _token_counts: list[tuple[float, int]] = field(default_factory=list)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    def estimate_tokens(self, text: str) -> int:
        """텍스트의 토큰 수를 추정한다.

        대략 4글자 = 1토큰으로 계산한다. (영어 기준)
        한국어 등 비라틴 문자는 더 많은 토큰을 사용할 수 있다.

        Args:
            text: 토큰 수를 추정할 텍스트

        Returns:
            추정 토큰 수
        """
        # 간단한 휴리스틱: 영어는 약 4글자 = 1토큰, 한국어는 약 2글자 = 1토큰
        # 보수적으로 평균 3글자 = 1토큰으로 계산
        return max(1, len(text) // 3)

    def _cleanup_old_entries(self, current_time: float) -> None:
        """1분 이전의 오래된 항목을 제거한다.

        Args:
            current_time: 현재 시간 (epoch seconds)
        """
        cutoff = current_time - 60.0

        # 오래된 요청 시간 제거
        self._request_times = [t for t in self._request_times if t > cutoff]

        # 오래된 토큰 카운트 제거
        self._token_counts = [(t, c) for t, c in self._token_counts if t > cutoff]

    def _get_current_rpm(self) -> int:
        """현재 분당 요청 수를 반환한다."""
        return len(self._request_times)

    def _get_current_tpm(self) -> int:
        """현재 분당 토큰 수를 반환한다."""
        return sum(count for _, count in self._token_counts)

    async def acquire(self, estimated_tokens: int = 0) -> None:
        """Rate limit 확인 후 필요시 대기한다.

        Args:
            estimated_tokens: 이번 요청의 추정 토큰 수

        Note:
            이 메서드는 rate limit에 걸리면 대기한 후 반환한다.
            rate limit이 해소될 때까지 블로킹된다.
        """
        async with self._lock:
            while True:
                current_time = time.time()
                self._cleanup_old_entries(current_time)

                current_rpm = self._get_current_rpm()
                current_tpm = self._get_current_tpm()

                rpm_ok = current_rpm < self.requests_per_minute
                tpm_ok = (current_tpm + estimated_tokens) <= self.tokens_per_minute

                if rpm_ok and tpm_ok:
                    # Rate limit 내에 있음 - 현재 요청 기록
                    self._request_times.append(current_time)
                    if estimated_tokens > 0:
                        self._token_counts.append((current_time, estimated_tokens))

                    logger.debug(
                        "Rate limit check passed: RPM=%d/%d, TPM=%d/%d",
                        current_rpm + 1,
                        self.requests_per_minute,
                        current_tpm + estimated_tokens,
                        self.tokens_per_minute,
                    )
                    return

                # Rate limit 초과 - 대기 시간 계산
                if not rpm_ok:
                    oldest_request = min(self._request_times) if self._request_times else current_time
                    wait_time = max(0.1, 60.0 - (current_time - oldest_request))
                    logger.info(
                        "RPM limit reached (%d/%d), waiting %.1fs",
                        current_rpm,
                        self.requests_per_minute,
                        wait_time,
                    )
                elif not tpm_ok:
                    oldest_token = min(t for t, _ in self._token_counts) if self._token_counts else current_time
                    wait_time = max(0.1, 60.0 - (current_time - oldest_token))
                    logger.info(
                        "TPM limit reached (%d/%d), waiting %.1fs",
                        current_tpm,
                        self.tokens_per_minute,
                        wait_time,
                    )
                else:
                    wait_time = 1.0

                # Lock을 해제하고 대기
                await asyncio.sleep(wait_time)

    def get_stats(self) -> dict[str, int | float]:
        """현재 rate limiter 통계를 반환한다.

        Returns:
            통계 정보 딕셔너리
        """
        current_time = time.time()
        self._cleanup_old_entries(current_time)

        return {
            "current_rpm": self._get_current_rpm(),
            "rpm_limit": self.requests_per_minute,
            "current_tpm": self._get_current_tpm(),
            "tpm_limit": self.tokens_per_minute,
            "rpm_remaining": max(0, self.requests_per_minute - self._get_current_rpm()),
            "tpm_remaining": max(0, self.tokens_per_minute - self._get_current_tpm()),
        }

    def reset(self) -> None:
        """Rate limiter 상태를 초기화한다."""
        self._request_times.clear()
        self._token_counts.clear()
        logger.debug("Rate limiter reset")
