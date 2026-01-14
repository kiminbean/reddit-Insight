"""Performance tests for v2.0 features.

v2.0에서 추가된 기능들의 성능을 측정한다:
- LLM 분석 (Phase 26-27)
- 멀티 서브레딧 비교 (Phase 28)
- 실시간 모니터링 (Phase 29)
- 알림 시스템 (Phase 30)
- 캐싱 시스템 (Phase 22)
"""

from __future__ import annotations

import gc
import os
import time
import tracemalloc
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# 테스트에서 rate limiting 비활성화
os.environ["RATE_LIMIT_PER_MINUTE"] = "10000"


# =============================================================================
# PERFORMANCE UTILITIES
# =============================================================================


class PerformanceTimer:
    """성능 측정을 위한 컨텍스트 매니저."""

    def __init__(self, name: str = "Operation") -> None:
        self.name = name
        self.start_time: float = 0.0
        self.end_time: float = 0.0
        self.elapsed_ms: float = 0.0

    def __enter__(self) -> "PerformanceTimer":
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, *args: Any) -> None:
        self.end_time = time.perf_counter()
        self.elapsed_ms = (self.end_time - self.start_time) * 1000


def measure_response_time(
    client: TestClient, url: str, iterations: int = 10, method: str = "GET", **kwargs
) -> dict[str, float]:
    """응답 시간을 측정한다.

    Args:
        client: TestClient 인스턴스
        url: 테스트할 URL
        iterations: 반복 횟수
        method: HTTP 메서드
        **kwargs: 추가 요청 파라미터

    Returns:
        평균, 최소, 최대 응답 시간 (ms)
    """
    times: list[float] = []

    # 워밍업
    if method == "GET":
        client.get(url)
    elif method == "POST":
        client.post(url, **kwargs)

    for _ in range(iterations):
        with PerformanceTimer() as timer:
            if method == "GET":
                client.get(url)
            elif method == "POST":
                client.post(url, **kwargs)
        times.append(timer.elapsed_ms)

    return {
        "avg_ms": sum(times) / len(times),
        "min_ms": min(times),
        "max_ms": max(times),
        "p95_ms": sorted(times)[int(len(times) * 0.95)] if len(times) >= 20 else max(times),
    }


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def perf_client() -> TestClient:
    """성능 테스트용 TestClient를 생성한다."""
    from reddit_insight.dashboard.app import app

    return TestClient(app)


# =============================================================================
# LLM PERFORMANCE TESTS
# =============================================================================


class TestLLMPerformance:
    """LLM 관련 기능 성능 테스트."""

    # LLM 페이지 목표 응답 시간 (ms)
    TARGET_PAGE_RESPONSE_MS = 500
    TARGET_API_RESPONSE_MS = 200

    def test_llm_page_load_time(self, perf_client: TestClient) -> None:
        """LLM 페이지 로드 시간 측정."""
        metrics = measure_response_time(perf_client, "/dashboard/llm/")

        assert metrics["avg_ms"] < self.TARGET_PAGE_RESPONSE_MS, (
            f"LLM page avg load time {metrics['avg_ms']:.2f}ms "
            f"exceeds target {self.TARGET_PAGE_RESPONSE_MS}ms"
        )

    def test_llm_status_api_performance(self, perf_client: TestClient) -> None:
        """LLM 상태 API 응답 시간 측정."""
        metrics = measure_response_time(perf_client, "/dashboard/llm/status")

        assert metrics["avg_ms"] < self.TARGET_API_RESPONSE_MS, (
            f"LLM status API avg response time {metrics['avg_ms']:.2f}ms "
            f"exceeds target {self.TARGET_API_RESPONSE_MS}ms"
        )

    def test_llm_categorize_performance_with_mock(self, perf_client: TestClient) -> None:
        """LLM 카테고리화 API 성능 측정 (mock)."""
        with patch(
            "reddit_insight.dashboard.services.llm_service.LLMService.categorize_single"
        ) as mock_categorize:
            mock_result = MagicMock()
            mock_result.category = "Feature Request"
            mock_result.confidence = 0.85
            mock_categorize.return_value = mock_result

            metrics = measure_response_time(
                perf_client,
                "/dashboard/llm/categorize",
                method="POST",
                data={"text": "I wish this app had dark mode"},
            )

            # Mock이므로 빠른 응답 기대
            assert metrics["avg_ms"] < self.TARGET_API_RESPONSE_MS * 2

    def test_llm_sentiment_performance_with_mock(self, perf_client: TestClient) -> None:
        """LLM 감성 분석 API 성능 측정 (mock)."""
        with patch(
            "reddit_insight.dashboard.services.llm_service.LLMService.get_deep_sentiment"
        ) as mock_sentiment:
            mock_result = MagicMock()
            mock_result.sentiment = "positive"
            mock_result.confidence = 0.9
            mock_sentiment.return_value = mock_result

            metrics = measure_response_time(
                perf_client,
                "/dashboard/llm/sentiment",
                method="POST",
                data={"text": "This product is amazing!"},
            )

            assert metrics["avg_ms"] < self.TARGET_API_RESPONSE_MS * 2


# =============================================================================
# COMPARISON PERFORMANCE TESTS
# =============================================================================


class TestComparisonPerformance:
    """멀티 서브레딧 비교 성능 테스트."""

    TARGET_PAGE_RESPONSE_MS = 500
    TARGET_API_RESPONSE_MS = 300

    def test_comparison_page_load_time(self, perf_client: TestClient) -> None:
        """비교 페이지 로드 시간 측정."""
        metrics = measure_response_time(perf_client, "/dashboard/comparison/")

        assert metrics["avg_ms"] < self.TARGET_PAGE_RESPONSE_MS, (
            f"Comparison page avg load time {metrics['avg_ms']:.2f}ms "
            f"exceeds target {self.TARGET_PAGE_RESPONSE_MS}ms"
        )

    def test_comparison_available_api_performance(self, perf_client: TestClient) -> None:
        """사용 가능한 서브레딧 목록 API 응답 시간 측정."""
        metrics = measure_response_time(perf_client, "/dashboard/comparison/available")

        assert metrics["avg_ms"] < self.TARGET_API_RESPONSE_MS, (
            f"Available subreddits API avg response time {metrics['avg_ms']:.2f}ms "
            f"exceeds target {self.TARGET_API_RESPONSE_MS}ms"
        )

    def test_comparison_analyze_performance_with_mock(
        self, perf_client: TestClient
    ) -> None:
        """비교 분석 API 성능 측정 (mock)."""
        with patch(
            "reddit_insight.dashboard.services.comparison_service.ComparisonService.compare_subreddits"
        ) as mock_compare:
            mock_result = MagicMock()
            mock_result.subreddits = ["python", "javascript"]
            mock_result.summary = {}
            mock_result.chart_data = {"labels": [], "datasets": []}
            mock_compare.return_value = mock_result

            metrics = measure_response_time(
                perf_client,
                "/dashboard/comparison/analyze",
                method="POST",
                data={"subreddits": ["python", "javascript"]},
            )

            # 비교 분석은 더 긴 시간 허용
            assert metrics["avg_ms"] < 1000


# =============================================================================
# LIVE MONITORING PERFORMANCE TESTS
# =============================================================================


class TestLiveMonitoringPerformance:
    """실시간 모니터링 성능 테스트."""

    TARGET_PAGE_RESPONSE_MS = 500
    TARGET_API_RESPONSE_MS = 200

    def test_live_page_load_time(self, perf_client: TestClient) -> None:
        """라이브 대시보드 페이지 로드 시간 측정."""
        metrics = measure_response_time(perf_client, "/dashboard/live/")

        assert metrics["avg_ms"] < self.TARGET_PAGE_RESPONSE_MS, (
            f"Live page avg load time {metrics['avg_ms']:.2f}ms "
            f"exceeds target {self.TARGET_PAGE_RESPONSE_MS}ms"
        )

    def test_live_status_api_performance(self, perf_client: TestClient) -> None:
        """모니터 상태 API 응답 시간 측정."""
        metrics = measure_response_time(perf_client, "/dashboard/live/status")

        assert metrics["avg_ms"] < self.TARGET_API_RESPONSE_MS, (
            f"Live status API avg response time {metrics['avg_ms']:.2f}ms "
            f"exceeds target {self.TARGET_API_RESPONSE_MS}ms"
        )

    def test_live_subreddit_status_performance(self, perf_client: TestClient) -> None:
        """서브레딧 모니터 상태 API 응답 시간 측정."""
        metrics = measure_response_time(
            perf_client, "/dashboard/live/status/python", iterations=20
        )

        assert metrics["avg_ms"] < self.TARGET_API_RESPONSE_MS, (
            f"Subreddit status API avg response time {metrics['avg_ms']:.2f}ms "
            f"exceeds target {self.TARGET_API_RESPONSE_MS}ms"
        )

    def test_live_start_monitoring_performance(self, perf_client: TestClient) -> None:
        """모니터링 시작 API 성능 측정 (mock)."""
        with patch(
            "reddit_insight.dashboard.services.live_service.LiveService.start_monitoring"
        ) as mock_start:
            mock_monitor = MagicMock()
            mock_monitor.is_running = True
            mock_start.return_value = mock_monitor

            metrics = measure_response_time(
                perf_client,
                "/dashboard/live/start/testsubreddit?interval=60",
                method="POST",
            )

            assert metrics["avg_ms"] < self.TARGET_API_RESPONSE_MS * 2


# =============================================================================
# ALERTS PERFORMANCE TESTS
# =============================================================================


class TestAlertsPerformance:
    """알림 시스템 성능 테스트."""

    TARGET_PAGE_RESPONSE_MS = 500
    TARGET_API_RESPONSE_MS = 200

    def test_alerts_page_load_time(self, perf_client: TestClient) -> None:
        """알림 대시보드 페이지 로드 시간 측정."""
        metrics = measure_response_time(perf_client, "/dashboard/alerts/")

        assert metrics["avg_ms"] < self.TARGET_PAGE_RESPONSE_MS, (
            f"Alerts page avg load time {metrics['avg_ms']:.2f}ms "
            f"exceeds target {self.TARGET_PAGE_RESPONSE_MS}ms"
        )

    def test_alerts_rules_api_performance(self, perf_client: TestClient) -> None:
        """알림 규칙 목록 API 응답 시간 측정."""
        metrics = measure_response_time(perf_client, "/dashboard/alerts/rules")

        assert metrics["avg_ms"] < self.TARGET_API_RESPONSE_MS, (
            f"Alert rules API avg response time {metrics['avg_ms']:.2f}ms "
            f"exceeds target {self.TARGET_API_RESPONSE_MS}ms"
        )

    def test_alerts_stats_api_performance(self, perf_client: TestClient) -> None:
        """알림 통계 API 응답 시간 측정."""
        metrics = measure_response_time(perf_client, "/dashboard/alerts/stats")

        assert metrics["avg_ms"] < self.TARGET_API_RESPONSE_MS, (
            f"Alert stats API avg response time {metrics['avg_ms']:.2f}ms "
            f"exceeds target {self.TARGET_API_RESPONSE_MS}ms"
        )

    def test_alerts_history_performance(self, perf_client: TestClient) -> None:
        """알림 이력 API 응답 시간 측정."""
        metrics = measure_response_time(perf_client, "/dashboard/alerts/history")

        assert metrics["avg_ms"] < self.TARGET_API_RESPONSE_MS, (
            f"Alert history avg response time {metrics['avg_ms']:.2f}ms "
            f"exceeds target {self.TARGET_API_RESPONSE_MS}ms"
        )


# =============================================================================
# CACHE PERFORMANCE TESTS
# =============================================================================


class TestCachePerformance:
    """캐싱 시스템 성능 테스트."""

    def test_cache_service_performance(self) -> None:
        """캐시 서비스 기본 성능 테스트."""
        from reddit_insight.dashboard.services.cache_service import CacheService

        cache = CacheService()

        # 캐시 쓰기 성능
        start = time.perf_counter()
        for i in range(1000):
            cache.set(f"test_key_{i}", {"data": f"value_{i}"}, ttl=60)
        write_elapsed = (time.perf_counter() - start) * 1000

        # 캐시 읽기 성능
        start = time.perf_counter()
        for i in range(1000):
            cache.get(f"test_key_{i}")
        read_elapsed = (time.perf_counter() - start) * 1000

        # 1000번 쓰기/읽기가 각각 100ms 이내
        assert write_elapsed < 100, f"Cache write too slow: {write_elapsed:.2f}ms for 1000 ops"
        assert read_elapsed < 100, f"Cache read too slow: {read_elapsed:.2f}ms for 1000 ops"

    def test_cache_hit_vs_miss_performance(self) -> None:
        """캐시 히트 vs 미스 성능 비교."""
        from reddit_insight.dashboard.services.cache_service import CacheService

        cache = CacheService()

        # 캐시 미스 시간 측정
        start = time.perf_counter()
        for i in range(100):
            cache.get(f"nonexistent_key_{i}")
        miss_elapsed = (time.perf_counter() - start) * 1000

        # 캐시에 데이터 저장
        for i in range(100):
            cache.set(f"existing_key_{i}", {"data": f"value_{i}"}, ttl=60)

        # 캐시 히트 시간 측정
        start = time.perf_counter()
        for i in range(100):
            cache.get(f"existing_key_{i}")
        hit_elapsed = (time.perf_counter() - start) * 1000

        # 캐시 히트가 더 빨라야 함 (또는 비슷)
        # 인메모리 캐시이므로 둘 다 매우 빠름
        assert hit_elapsed < 50, f"Cache hit too slow: {hit_elapsed:.2f}ms for 100 ops"
        assert miss_elapsed < 50, f"Cache miss too slow: {miss_elapsed:.2f}ms for 100 ops"


# =============================================================================
# V2.0 DASHBOARD RESPONSE TIME TESTS
# =============================================================================


class TestV2DashboardResponseTime:
    """v2.0 대시보드 전체 응답 시간 테스트."""

    TARGET_RESPONSE_MS = 500

    def test_all_v2_pages_response_time(self, perf_client: TestClient) -> None:
        """모든 v2.0 페이지 응답 시간을 측정한다."""
        v2_pages = [
            ("/dashboard/llm/", "LLM Analysis"),
            ("/dashboard/comparison/", "Comparison"),
            ("/dashboard/live/", "Live Monitoring"),
            ("/dashboard/alerts/", "Alerts"),
        ]

        slow_pages: list[str] = []

        for url, name in v2_pages:
            metrics = measure_response_time(perf_client, url, iterations=5)
            if metrics["avg_ms"] > self.TARGET_RESPONSE_MS:
                slow_pages.append(f"{name}: {metrics['avg_ms']:.2f}ms")

        assert len(slow_pages) == 0, f"Slow v2 pages detected: {slow_pages}"

    def test_all_v2_api_response_time(self, perf_client: TestClient) -> None:
        """모든 v2.0 API 엔드포인트 응답 시간을 측정한다."""
        TARGET_API_MS = 300

        v2_apis = [
            ("/dashboard/llm/status", "LLM Status"),
            ("/dashboard/comparison/available", "Available Subreddits"),
            ("/dashboard/live/status", "Live Status"),
            ("/dashboard/alerts/rules", "Alert Rules"),
            ("/dashboard/alerts/stats", "Alert Stats"),
        ]

        slow_apis: list[str] = []

        for url, name in v2_apis:
            metrics = measure_response_time(perf_client, url, iterations=10)
            if metrics["avg_ms"] > TARGET_API_MS:
                slow_apis.append(f"{name}: {metrics['avg_ms']:.2f}ms")

        assert len(slow_apis) == 0, f"Slow v2 APIs detected: {slow_apis}"


# =============================================================================
# V2.0 PERFORMANCE BENCHMARK
# =============================================================================


class TestV2PerformanceBenchmark:
    """v2.0 성능 벤치마크 종합 테스트."""

    def test_v2_performance_summary(self, perf_client: TestClient) -> None:
        """v2.0 기능 전체 성능 벤치마크 리포트를 생성한다."""
        endpoints = {
            # v2.0 Pages
            "LLM Page": "/dashboard/llm/",
            "Comparison Page": "/dashboard/comparison/",
            "Live Page": "/dashboard/live/",
            "Alerts Page": "/dashboard/alerts/",
            # v2.0 APIs
            "LLM Status API": "/dashboard/llm/status",
            "Comparison Available API": "/dashboard/comparison/available",
            "Live Status API": "/dashboard/live/status",
            "Alerts Rules API": "/dashboard/alerts/rules",
            "Alerts Stats API": "/dashboard/alerts/stats",
        }

        results: dict[str, dict[str, float]] = {}

        for name, url in endpoints.items():
            metrics = measure_response_time(perf_client, url, iterations=5)
            results[name] = metrics

        # 성능 리포트 출력
        print("\n=== v2.0 Performance Benchmark Report ===")
        target_page_ms = 500
        target_api_ms = 300

        slow_items: list[str] = []

        for name, metrics in results.items():
            is_page = "Page" in name
            target = target_page_ms if is_page else target_api_ms
            status = "OK" if metrics["avg_ms"] <= target else "SLOW"

            print(
                f"{name}: avg={metrics['avg_ms']:.1f}ms, "
                f"min={metrics['min_ms']:.1f}ms, "
                f"max={metrics['max_ms']:.1f}ms [{status}]"
            )

            if metrics["avg_ms"] > target:
                slow_items.append(f"{name} ({metrics['avg_ms']:.1f}ms > {target}ms)")

        print("=" * 45)

        assert len(slow_items) == 0, f"Performance issues detected: {slow_items}"


# =============================================================================
# RATE LIMITER PERFORMANCE TEST
# =============================================================================


class TestRateLimiterPerformance:
    """Rate Limiter 성능 테스트."""

    def test_rate_limiter_stats_overhead(self) -> None:
        """Rate limiter 통계 조회 오버헤드를 테스트한다."""
        try:
            from reddit_insight.llm.rate_limiter import RateLimiter

            limiter = RateLimiter(requests_per_minute=60, tokens_per_minute=100000)

            start = time.perf_counter()
            for _ in range(1000):
                limiter.get_stats()
            elapsed = (time.perf_counter() - start) * 1000

            # 1000번 통계 조회가 50ms 이내여야 함
            assert elapsed < 50, f"Rate limiter stats too slow: {elapsed:.2f}ms for 1000 checks"

        except ImportError:
            pytest.skip("RateLimiter not available")

    def test_rate_limiter_token_estimation(self) -> None:
        """Rate limiter 토큰 추정 성능을 테스트한다."""
        try:
            from reddit_insight.llm.rate_limiter import RateLimiter

            limiter = RateLimiter(requests_per_minute=1000, tokens_per_minute=1000000)

            # 다양한 길이의 텍스트로 토큰 추정 테스트
            test_texts = [
                "Short text",
                "Medium length text that has more content than the short one",
                "A much longer text " * 100,  # 긴 텍스트
            ]

            start = time.perf_counter()
            for _ in range(100):
                for text in test_texts:
                    limiter.estimate_tokens(text)
            elapsed = (time.perf_counter() - start) * 1000

            # 300번 토큰 추정이 10ms 이내여야 함
            assert elapsed < 10, f"Token estimation too slow: {elapsed:.2f}ms for 300 estimates"

        except ImportError:
            pytest.skip("RateLimiter not available")
