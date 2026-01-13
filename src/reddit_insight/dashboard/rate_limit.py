"""Rate Limiting 모듈.

IP 기반 및 API Key 기반 요청 제한을 구현한다.
"""

import logging
import os
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

# 환경 변수에서 설정 로드
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "100"))
RATE_LIMIT_WINDOW_SECONDS = 60


@dataclass
class RateLimitEntry:
    """Rate limit 추적 엔트리."""

    count: int = 0
    window_start: float = field(default_factory=time.time)


class RateLimiter:
    """메모리 기반 Rate Limiter.

    슬라이딩 윈도우 방식으로 요청 수를 추적한다.
    프로덕션에서는 Redis 사용 권장.
    """

    def __init__(
        self,
        max_requests: int = RATE_LIMIT_PER_MINUTE,
        window_seconds: int = RATE_LIMIT_WINDOW_SECONDS,
    ):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._entries: dict[str, RateLimitEntry] = defaultdict(RateLimitEntry)
        self._cleanup_interval = 300  # 5분마다 정리
        self._last_cleanup = time.time()

    def _cleanup_old_entries(self) -> None:
        """오래된 엔트리를 정리한다."""
        current_time = time.time()
        if current_time - self._last_cleanup < self._cleanup_interval:
            return

        expired_keys = []
        for key, entry in self._entries.items():
            if current_time - entry.window_start > self.window_seconds * 2:
                expired_keys.append(key)

        for key in expired_keys:
            del self._entries[key]

        self._last_cleanup = current_time
        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired rate limit entries")

    def is_allowed(self, key: str) -> tuple[bool, dict]:
        """요청이 허용되는지 확인한다.

        Args:
            key: Rate limit 키 (IP 주소 또는 API 키)

        Returns:
            (허용 여부, 메타데이터)
        """
        self._cleanup_old_entries()

        current_time = time.time()
        entry = self._entries[key]

        # 윈도우 리셋 확인
        if current_time - entry.window_start > self.window_seconds:
            entry.count = 0
            entry.window_start = current_time

        # 요청 카운트 증가
        entry.count += 1

        remaining = max(0, self.max_requests - entry.count)
        reset_time = int(entry.window_start + self.window_seconds)

        metadata = {
            "limit": self.max_requests,
            "remaining": remaining,
            "reset": reset_time,
        }

        if entry.count > self.max_requests:
            logger.warning(f"Rate limit exceeded for {key}: {entry.count}/{self.max_requests}")
            return False, metadata

        return True, metadata

    def get_stats(self) -> dict:
        """Rate limiter 통계를 반환한다."""
        current_time = time.time()
        active_entries = sum(
            1
            for entry in self._entries.values()
            if current_time - entry.window_start <= self.window_seconds
        )

        return {
            "total_tracked": len(self._entries),
            "active_entries": active_entries,
            "max_requests": self.max_requests,
            "window_seconds": self.window_seconds,
        }


# 전역 Rate Limiter 인스턴스
_rate_limiter = RateLimiter()


def get_rate_limiter() -> RateLimiter:
    """전역 Rate Limiter 인스턴스를 반환한다."""
    return _rate_limiter


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate Limiting 미들웨어.

    IP 기반 또는 API Key 기반으로 요청을 제한한다.
    """

    # Rate limiting에서 제외할 경로
    EXCLUDED_PATHS = {
        "/health",
        "/static",
        "/favicon.ico",
    }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """요청을 처리하고 rate limit을 적용한다."""
        # 제외 경로 확인
        path = request.url.path
        if any(path.startswith(excluded) for excluded in self.EXCLUDED_PATHS):
            return await call_next(request)

        # Rate limit 키 결정 (API Key 우선, 없으면 IP)
        api_key = request.headers.get("X-API-Key")
        if api_key:
            rate_key = f"api:{api_key[:16]}"  # API 키 앞부분만 사용
        else:
            client_ip = self._get_client_ip(request)
            rate_key = f"ip:{client_ip}"

        # Rate limit 확인
        limiter = get_rate_limiter()
        allowed, metadata = limiter.is_allowed(rate_key)

        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Too Many Requests",
                    "message": f"Rate limit exceeded. Max {metadata['limit']} requests per minute.",
                    "retry_after": metadata["reset"] - int(time.time()),
                },
                headers={
                    "X-RateLimit-Limit": str(metadata["limit"]),
                    "X-RateLimit-Remaining": str(metadata["remaining"]),
                    "X-RateLimit-Reset": str(metadata["reset"]),
                    "Retry-After": str(metadata["reset"] - int(time.time())),
                },
            )

        # 정상 처리
        response = await call_next(request)

        # Rate limit 헤더 추가
        response.headers["X-RateLimit-Limit"] = str(metadata["limit"])
        response.headers["X-RateLimit-Remaining"] = str(metadata["remaining"])
        response.headers["X-RateLimit-Reset"] = str(metadata["reset"])

        return response

    def _get_client_ip(self, request: Request) -> str:
        """클라이언트 IP 주소를 추출한다."""
        # 프록시 뒤에 있는 경우 X-Forwarded-For 헤더 확인
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()

        # 직접 연결된 클라이언트 IP
        if request.client:
            return request.client.host

        return "unknown"


# ============================================================================
# API Key별 커스텀 Rate Limit
# ============================================================================


class APIKeyRateLimiter:
    """API Key별 개별 Rate Limit 관리.

    각 API Key는 데이터베이스에 저장된 rate_limit 값을 가진다.
    """

    def __init__(self):
        self._limiters: dict[str, RateLimiter] = {}

    def get_limiter(self, api_key_id: int, rate_limit: int) -> RateLimiter:
        """API Key에 대한 Rate Limiter를 반환한다."""
        key = f"api_key:{api_key_id}"
        if key not in self._limiters:
            self._limiters[key] = RateLimiter(max_requests=rate_limit)
        return self._limiters[key]

    def is_allowed(self, api_key_id: int, rate_limit: int) -> tuple[bool, dict]:
        """API Key에 대한 요청이 허용되는지 확인한다."""
        limiter = self.get_limiter(api_key_id, rate_limit)
        return limiter.is_allowed(str(api_key_id))


# 전역 API Key Rate Limiter 인스턴스
_api_key_rate_limiter = APIKeyRateLimiter()


def get_api_key_rate_limiter() -> APIKeyRateLimiter:
    """전역 API Key Rate Limiter를 반환한다."""
    return _api_key_rate_limiter


# ============================================================================
# CLI
# ============================================================================


def cli_show_stats() -> None:
    """CLI에서 Rate Limiter 통계를 출력한다."""
    limiter = get_rate_limiter()
    stats = limiter.get_stats()

    print("\n=== Rate Limiter Statistics ===")
    print(f"Total Tracked: {stats['total_tracked']}")
    print(f"Active Entries: {stats['active_entries']}")
    print(f"Max Requests: {stats['max_requests']}/minute")
    print(f"Window: {stats['window_seconds']} seconds")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "stats":
        cli_show_stats()
    else:
        print("Usage:")
        print("  python -m reddit_insight.dashboard.rate_limit stats")
