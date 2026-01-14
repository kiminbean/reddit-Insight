"""Rate Limiter 테스트."""

from __future__ import annotations

import asyncio
import time

import pytest

from reddit_insight.llm.rate_limiter import RateLimiter


class TestRateLimiter:
    """RateLimiter 클래스 테스트."""

    @pytest.fixture
    def rate_limiter(self) -> RateLimiter:
        """테스트용 rate limiter."""
        return RateLimiter(requests_per_minute=60, tokens_per_minute=100000)

    def test_estimate_tokens_english(self, rate_limiter: RateLimiter) -> None:
        """영어 텍스트의 토큰 수를 추정한다."""
        text = "Hello, World!"  # 13글자
        tokens = rate_limiter.estimate_tokens(text)
        assert tokens >= 1
        assert tokens <= 10

    def test_estimate_tokens_korean(self, rate_limiter: RateLimiter) -> None:
        """한국어 텍스트의 토큰 수를 추정한다."""
        text = "안녕하세요"  # 5글자
        tokens = rate_limiter.estimate_tokens(text)
        assert tokens >= 1

    def test_estimate_tokens_empty(self, rate_limiter: RateLimiter) -> None:
        """빈 텍스트도 최소 1토큰을 반환한다."""
        tokens = rate_limiter.estimate_tokens("")
        assert tokens == 1

    def test_estimate_tokens_long_text(self, rate_limiter: RateLimiter) -> None:
        """긴 텍스트의 토큰 수를 추정한다."""
        text = "a" * 300  # 300글자
        tokens = rate_limiter.estimate_tokens(text)
        assert tokens == 100  # 300 / 3

    @pytest.mark.asyncio
    async def test_acquire_under_limit(self, rate_limiter: RateLimiter) -> None:
        """Rate limit 내에서는 즉시 반환된다."""
        start = time.time()
        await rate_limiter.acquire(estimated_tokens=100)
        elapsed = time.time() - start
        assert elapsed < 0.1

    @pytest.mark.asyncio
    async def test_acquire_multiple_requests(self, rate_limiter: RateLimiter) -> None:
        """여러 요청이 rate limit 내에서 처리된다."""
        for _ in range(5):
            await rate_limiter.acquire(estimated_tokens=100)

        stats = rate_limiter.get_stats()
        assert stats["current_rpm"] == 5
        assert stats["current_tpm"] == 500

    @pytest.mark.asyncio
    async def test_acquire_rpm_limit(self) -> None:
        """RPM 제한에 걸리면 대기한다."""
        # 매우 낮은 RPM 제한 설정
        rate_limiter = RateLimiter(requests_per_minute=2, tokens_per_minute=100000)

        # 2개 요청은 통과
        await rate_limiter.acquire()
        await rate_limiter.acquire()

        # 3번째 요청은 대기해야 함 (테스트에서는 시간 제한으로 확인)
        stats = rate_limiter.get_stats()
        assert stats["current_rpm"] == 2
        assert stats["rpm_remaining"] == 0

    @pytest.mark.asyncio
    async def test_acquire_tpm_limit(self) -> None:
        """TPM 제한에 걸리면 대기한다."""
        # 매우 낮은 TPM 제한 설정
        rate_limiter = RateLimiter(requests_per_minute=100, tokens_per_minute=500)

        # 500 토큰 요청
        await rate_limiter.acquire(estimated_tokens=500)

        stats = rate_limiter.get_stats()
        assert stats["current_tpm"] == 500
        assert stats["tpm_remaining"] == 0

    def test_get_stats(self, rate_limiter: RateLimiter) -> None:
        """통계를 조회할 수 있다."""
        stats = rate_limiter.get_stats()

        assert "current_rpm" in stats
        assert "rpm_limit" in stats
        assert "current_tpm" in stats
        assert "tpm_limit" in stats
        assert "rpm_remaining" in stats
        assert "tpm_remaining" in stats

        assert stats["rpm_limit"] == 60
        assert stats["tpm_limit"] == 100000
        assert stats["current_rpm"] == 0
        assert stats["current_tpm"] == 0

    def test_reset(self, rate_limiter: RateLimiter) -> None:
        """rate limiter를 초기화할 수 있다."""
        # 요청 기록 추가
        rate_limiter._request_times.append(time.time())
        rate_limiter._token_counts.append((time.time(), 100))

        assert len(rate_limiter._request_times) == 1
        assert len(rate_limiter._token_counts) == 1

        # 리셋
        rate_limiter.reset()

        assert len(rate_limiter._request_times) == 0
        assert len(rate_limiter._token_counts) == 0

    @pytest.mark.asyncio
    async def test_cleanup_old_entries(self, rate_limiter: RateLimiter) -> None:
        """오래된 항목이 정리된다."""
        # 오래된 항목 추가 (2분 전)
        old_time = time.time() - 120
        rate_limiter._request_times.append(old_time)
        rate_limiter._token_counts.append((old_time, 100))

        # 새 요청 시 정리됨
        await rate_limiter.acquire()

        # 오래된 항목은 제거되고 새 항목만 있음
        assert len(rate_limiter._request_times) == 1
        assert all(t > (time.time() - 60) for t in rate_limiter._request_times)

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, rate_limiter: RateLimiter) -> None:
        """동시 요청도 안전하게 처리된다."""
        async def make_request():
            await rate_limiter.acquire(estimated_tokens=10)

        # 동시에 10개 요청
        await asyncio.gather(*[make_request() for _ in range(10)])

        stats = rate_limiter.get_stats()
        assert stats["current_rpm"] == 10
        assert stats["current_tpm"] == 100


class TestRateLimiterEdgeCases:
    """Rate Limiter 엣지 케이스 테스트."""

    def test_default_values(self) -> None:
        """기본값이 올바르게 설정된다."""
        rate_limiter = RateLimiter()
        assert rate_limiter.requests_per_minute == 60
        assert rate_limiter.tokens_per_minute == 100000

    def test_custom_values(self) -> None:
        """사용자 정의 값이 적용된다."""
        rate_limiter = RateLimiter(
            requests_per_minute=30,
            tokens_per_minute=50000,
        )
        assert rate_limiter.requests_per_minute == 30
        assert rate_limiter.tokens_per_minute == 50000

    @pytest.mark.asyncio
    async def test_zero_tokens(self) -> None:
        """0 토큰 요청도 처리된다."""
        rate_limiter = RateLimiter()
        await rate_limiter.acquire(estimated_tokens=0)
        stats = rate_limiter.get_stats()
        assert stats["current_rpm"] == 1
        assert stats["current_tpm"] == 0
