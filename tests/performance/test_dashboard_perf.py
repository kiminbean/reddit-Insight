"""Performance tests for dashboard.

대시보드의 성능을 측정하고 최적화 목표를 검증한다.
응답 시간, 메모리 사용량, 처리량을 측정한다.
"""

from __future__ import annotations

import gc
import os
import time
import tracemalloc
from typing import Any
from unittest.mock import MagicMock, patch

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

    def __enter__(self) -> PerformanceTimer:
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, *args: Any) -> None:
        self.end_time = time.perf_counter()
        self.elapsed_ms = (self.end_time - self.start_time) * 1000


class MemoryTracker:
    """메모리 사용량 측정을 위한 컨텍스트 매니저."""

    def __init__(self) -> None:
        self.peak_memory_mb: float = 0.0
        self.current_memory_mb: float = 0.0

    def __enter__(self) -> MemoryTracker:
        gc.collect()
        tracemalloc.start()
        return self

    def __exit__(self, *args: Any) -> None:
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        self.current_memory_mb = current / 1024 / 1024
        self.peak_memory_mb = peak / 1024 / 1024


def measure_response_time(client: TestClient, url: str, iterations: int = 10) -> dict[str, float]:
    """응답 시간을 측정한다.

    Args:
        client: TestClient 인스턴스
        url: 테스트할 URL
        iterations: 반복 횟수

    Returns:
        평균, 최소, 최대 응답 시간 (ms)
    """
    times: list[float] = []

    # 워밍업
    client.get(url)

    for _ in range(iterations):
        with PerformanceTimer() as timer:
            client.get(url)
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


@pytest.fixture
def large_mock_data() -> dict[str, Any]:
    """대용량 mock 데이터를 생성한다."""
    return {
        "keywords": [
            {"keyword": f"keyword_{i}", "count": 100 - i, "trend": "up"} for i in range(100)
        ],
        "posts": [
            {
                "id": f"post_{i}",
                "title": f"Sample post title {i}",
                "content": f"Sample content for post {i}" * 10,
            }
            for i in range(1000)
        ],
        "demands": {
            "top_opportunities": [
                {
                    "representative": f"Demand {i}: Need for better solution",
                    "priority_score": 100 - i,
                    "size": 50 - i // 2,
                    "business_potential": "high" if i < 10 else "medium",
                }
                for i in range(50)
            ],
        },
        "insights": [
            {
                "id": f"insight_{i}",
                "type": "opportunity",
                "title": f"Insight {i}",
                "description": f"Description for insight {i}",
                "confidence": 0.9 - i * 0.01,
                "priority": 10 - i // 5,
            }
            for i in range(50)
        ],
    }


# =============================================================================
# PAGE LOAD PERFORMANCE TESTS
# =============================================================================


class TestPageLoadPerformance:
    """페이지 로드 성능 테스트.

    목표: 모든 페이지 로드 시간 < 500ms
    """

    # 목표 응답 시간 (ms)
    TARGET_RESPONSE_TIME_MS = 500

    def test_dashboard_home_load_time(self, perf_client: TestClient) -> None:
        """대시보드 홈 페이지 로드 시간 측정."""
        metrics = measure_response_time(perf_client, "/dashboard/")

        assert metrics["avg_ms"] < self.TARGET_RESPONSE_TIME_MS, (
            f"Dashboard home avg load time {metrics['avg_ms']:.2f}ms "
            f"exceeds target {self.TARGET_RESPONSE_TIME_MS}ms"
        )

    def test_trends_page_load_time(self, perf_client: TestClient) -> None:
        """트렌드 페이지 로드 시간 측정."""
        metrics = measure_response_time(perf_client, "/dashboard/trends/")

        assert metrics["avg_ms"] < self.TARGET_RESPONSE_TIME_MS, (
            f"Trends page avg load time {metrics['avg_ms']:.2f}ms "
            f"exceeds target {self.TARGET_RESPONSE_TIME_MS}ms"
        )

    def test_demands_page_load_time(self, perf_client: TestClient) -> None:
        """수요 페이지 로드 시간 측정."""
        metrics = measure_response_time(perf_client, "/dashboard/demands/")

        assert metrics["avg_ms"] < self.TARGET_RESPONSE_TIME_MS, (
            f"Demands page avg load time {metrics['avg_ms']:.2f}ms "
            f"exceeds target {self.TARGET_RESPONSE_TIME_MS}ms"
        )

    def test_insights_page_load_time(self, perf_client: TestClient) -> None:
        """인사이트 페이지 로드 시간 측정."""
        metrics = measure_response_time(perf_client, "/dashboard/insights/")

        assert metrics["avg_ms"] < self.TARGET_RESPONSE_TIME_MS, (
            f"Insights page avg load time {metrics['avg_ms']:.2f}ms "
            f"exceeds target {self.TARGET_RESPONSE_TIME_MS}ms"
        )

    def test_topics_page_load_time(self, perf_client: TestClient) -> None:
        """토픽 분석 페이지 로드 시간 측정."""
        metrics = measure_response_time(perf_client, "/dashboard/topics/")

        assert metrics["avg_ms"] < self.TARGET_RESPONSE_TIME_MS, (
            f"Topics page avg load time {metrics['avg_ms']:.2f}ms "
            f"exceeds target {self.TARGET_RESPONSE_TIME_MS}ms"
        )

    def test_clusters_page_load_time(self, perf_client: TestClient) -> None:
        """클러스터링 페이지 로드 시간 측정."""
        metrics = measure_response_time(perf_client, "/dashboard/clusters/")

        assert metrics["avg_ms"] < self.TARGET_RESPONSE_TIME_MS, (
            f"Clusters page avg load time {metrics['avg_ms']:.2f}ms "
            f"exceeds target {self.TARGET_RESPONSE_TIME_MS}ms"
        )


# =============================================================================
# API ENDPOINT PERFORMANCE TESTS
# =============================================================================


class TestAPIEndpointPerformance:
    """API 엔드포인트 성능 테스트."""

    # JSON API 목표 응답 시간 (ms)
    TARGET_API_RESPONSE_TIME_MS = 200

    def test_chart_data_api_performance(self, perf_client: TestClient) -> None:
        """차트 데이터 API 응답 시간 측정."""
        metrics = measure_response_time(perf_client, "/dashboard/trends/chart-data?keyword=test")

        assert metrics["avg_ms"] < self.TARGET_API_RESPONSE_TIME_MS, (
            f"Chart data API avg response time {metrics['avg_ms']:.2f}ms "
            f"exceeds target {self.TARGET_API_RESPONSE_TIME_MS}ms"
        )

    def test_top_keywords_chart_api_performance(self, perf_client: TestClient) -> None:
        """상위 키워드 차트 API 응답 시간 측정."""
        metrics = measure_response_time(perf_client, "/dashboard/trends/top-keywords-chart")

        assert metrics["avg_ms"] < self.TARGET_API_RESPONSE_TIME_MS, (
            f"Top keywords chart API avg response time {metrics['avg_ms']:.2f}ms "
            f"exceeds target {self.TARGET_API_RESPONSE_TIME_MS}ms"
        )

    def test_category_stats_api_performance(self, perf_client: TestClient) -> None:
        """카테고리 통계 API 응답 시간 측정."""
        metrics = measure_response_time(perf_client, "/dashboard/demands/categories/stats")

        assert metrics["avg_ms"] < self.TARGET_API_RESPONSE_TIME_MS, (
            f"Category stats API avg response time {metrics['avg_ms']:.2f}ms "
            f"exceeds target {self.TARGET_API_RESPONSE_TIME_MS}ms"
        )

    def test_grade_distribution_api_performance(self, perf_client: TestClient) -> None:
        """등급 분포 API 응답 시간 측정."""
        metrics = measure_response_time(perf_client, "/dashboard/insights/chart/grade-distribution")

        assert metrics["avg_ms"] < self.TARGET_API_RESPONSE_TIME_MS, (
            f"Grade distribution API avg response time {metrics['avg_ms']:.2f}ms "
            f"exceeds target {self.TARGET_API_RESPONSE_TIME_MS}ms"
        )


# =============================================================================
# ML ANALYSIS PERFORMANCE TESTS
# =============================================================================


class TestMLAnalysisPerformance:
    """ML 분석 성능 테스트.

    ML 분석은 더 긴 시간이 허용되지만, 적절한 타임아웃이 필요하다.
    """

    # ML 분석 목표 응답 시간 (ms)
    TARGET_ML_RESPONSE_TIME_MS = 5000  # 5초

    def test_prediction_api_performance(self, perf_client: TestClient) -> None:
        """예측 API 성능 측정."""
        with patch(
            "reddit_insight.dashboard.services.prediction_service.get_prediction_service"
        ) as mock_service:
            mock_result = MagicMock()
            mock_result.to_chart_data.return_value = {"labels": [], "datasets": []}
            mock_service.return_value.predict_keyword_trend.return_value = mock_result

            metrics = measure_response_time(
                perf_client, "/dashboard/trends/predict/test", iterations=5
            )

            assert metrics["avg_ms"] < self.TARGET_ML_RESPONSE_TIME_MS, (
                f"Prediction API avg response time {metrics['avg_ms']:.2f}ms "
                f"exceeds target {self.TARGET_ML_RESPONSE_TIME_MS}ms"
            )

    def test_anomaly_detection_api_performance(self, perf_client: TestClient) -> None:
        """이상 탐지 API 성능 측정."""
        with patch(
            "reddit_insight.dashboard.services.anomaly_service.get_anomaly_service"
        ) as mock_service:
            mock_result = MagicMock()
            mock_result.to_chart_data.return_value = {"labels": [], "datasets": []}
            mock_service.return_value.detect_anomalies.return_value = mock_result

            metrics = measure_response_time(
                perf_client, "/dashboard/trends/anomalies/test", iterations=5
            )

            assert metrics["avg_ms"] < self.TARGET_ML_RESPONSE_TIME_MS, (
                f"Anomaly detection API avg response time {metrics['avg_ms']:.2f}ms "
                f"exceeds target {self.TARGET_ML_RESPONSE_TIME_MS}ms"
            )

    def test_topic_analysis_api_performance(self, perf_client: TestClient) -> None:
        """토픽 분석 API 성능 측정."""
        with patch(
            "reddit_insight.dashboard.services.topic_service.get_topic_service"
        ) as mock_service:
            mock_result = MagicMock()
            mock_result.to_chart_data.return_value = {"topics": []}
            mock_service.return_value.analyze_topics.return_value = mock_result

            metrics = measure_response_time(perf_client, "/dashboard/topics/analyze", iterations=5)

            assert metrics["avg_ms"] < self.TARGET_ML_RESPONSE_TIME_MS, (
                f"Topic analysis API avg response time {metrics['avg_ms']:.2f}ms "
                f"exceeds target {self.TARGET_ML_RESPONSE_TIME_MS}ms"
            )

    def test_cluster_analysis_api_performance(self, perf_client: TestClient) -> None:
        """클러스터링 API 성능 측정."""
        with patch(
            "reddit_insight.dashboard.services.cluster_service.get_cluster_service"
        ) as mock_service:
            mock_result = MagicMock()
            mock_result.to_chart_data.return_value = {"clusters": []}
            mock_service.return_value.cluster_documents.return_value = mock_result

            metrics = measure_response_time(
                perf_client, "/dashboard/clusters/analyze", iterations=5
            )

            assert metrics["avg_ms"] < self.TARGET_ML_RESPONSE_TIME_MS, (
                f"Cluster analysis API avg response time {metrics['avg_ms']:.2f}ms "
                f"exceeds target {self.TARGET_ML_RESPONSE_TIME_MS}ms"
            )


# =============================================================================
# MEMORY USAGE TESTS
# =============================================================================


class TestMemoryUsage:
    """메모리 사용량 테스트."""

    # 피크 메모리 목표 (MB)
    TARGET_PEAK_MEMORY_MB = 100

    def test_dashboard_home_memory_usage(self, perf_client: TestClient) -> None:
        """대시보드 홈 페이지 메모리 사용량 측정."""
        with MemoryTracker() as tracker:
            for _ in range(10):
                perf_client.get("/dashboard/")

        # 피크 메모리가 목표 이하인지 확인
        assert tracker.peak_memory_mb < self.TARGET_PEAK_MEMORY_MB, (
            f"Peak memory {tracker.peak_memory_mb:.2f}MB "
            f"exceeds target {self.TARGET_PEAK_MEMORY_MB}MB"
        )

    def test_large_data_memory_usage(
        self, perf_client: TestClient, large_mock_data: dict[str, Any]
    ) -> None:
        """대용량 데이터 처리 시 메모리 사용량 측정."""
        with patch("reddit_insight.dashboard.data_store.get_current_data") as mock_get:
            mock_data = MagicMock()
            mock_data.keywords = large_mock_data["keywords"]
            mock_data.demands = large_mock_data["demands"]
            mock_data.insights = large_mock_data["insights"]
            mock_get.return_value = mock_data

            with MemoryTracker() as tracker:
                for _ in range(5):
                    perf_client.get("/dashboard/")
                    perf_client.get("/dashboard/trends/")
                    perf_client.get("/dashboard/demands/")

            # 대용량 데이터에도 메모리 사용량이 합리적인지 확인
            assert tracker.peak_memory_mb < self.TARGET_PEAK_MEMORY_MB * 2, (
                f"Peak memory with large data {tracker.peak_memory_mb:.2f}MB "
                f"exceeds target {self.TARGET_PEAK_MEMORY_MB * 2}MB"
            )


# =============================================================================
# CONCURRENT REQUEST TESTS
# =============================================================================


class TestConcurrentRequests:
    """동시 요청 처리 테스트."""

    def test_sequential_requests_stability(self, perf_client: TestClient) -> None:
        """연속 요청 처리 안정성 테스트."""
        endpoints = [
            "/dashboard/",
            "/dashboard/trends/",
            "/dashboard/demands/",
            "/dashboard/insights/",
            "/dashboard/topics/",
            "/dashboard/clusters/",
        ]

        # 50회 연속 요청
        for _ in range(50):
            for endpoint in endpoints:
                response = perf_client.get(endpoint)
                assert response.status_code == 200, f"Failed request to {endpoint}"

    def test_repeated_api_calls_stability(self, perf_client: TestClient) -> None:
        """반복 API 호출 안정성 테스트."""
        api_endpoints = [
            "/dashboard/trends/chart-data?keyword=test",
            "/dashboard/trends/top-keywords-chart",
            "/dashboard/demands/categories/stats",
            "/dashboard/insights/chart/grade-distribution",
        ]

        # 100회 반복
        for _ in range(100):
            for endpoint in api_endpoints:
                response = perf_client.get(endpoint)
                assert response.status_code == 200, f"Failed API call to {endpoint}"


# =============================================================================
# PAGINATION PERFORMANCE TESTS
# =============================================================================


class TestPaginationPerformance:
    """페이지네이션 성능 테스트."""

    def test_pagination_response_time(self, perf_client: TestClient) -> None:
        """페이지네이션 응답 시간 측정."""
        with patch(
            "reddit_insight.dashboard.services.cluster_service.get_cluster_service"
        ) as mock_service:
            # 1000개 문서 시뮬레이션
            mock_service.return_value.get_cluster_documents.return_value = [
                {"text": f"Document {i}", "score": 0.9 - i * 0.001} for i in range(1000)
            ]

            # 첫 페이지
            with PerformanceTimer() as timer:
                response = perf_client.get(
                    "/dashboard/clusters/cluster/0/documents?page=1&page_size=20"
                )
            first_page_ms = timer.elapsed_ms

            # 마지막 페이지
            with PerformanceTimer() as timer:
                response = perf_client.get(
                    "/dashboard/clusters/cluster/0/documents?page=50&page_size=20"
                )
            last_page_ms = timer.elapsed_ms

            assert response.status_code == 200

            # 페이지 위치에 관계없이 비슷한 응답 시간이어야 함
            time_diff = abs(first_page_ms - last_page_ms)
            assert time_diff < 100, f"Pagination time difference {time_diff:.2f}ms is too large"


# =============================================================================
# PERFORMANCE BENCHMARK REPORT
# =============================================================================


class TestPerformanceBenchmark:
    """성능 벤치마크 종합 테스트."""

    def test_generate_performance_report(self, perf_client: TestClient) -> None:
        """전체 성능 벤치마크 리포트를 생성한다."""
        endpoints = {
            "Dashboard Home": "/dashboard/",
            "Trends": "/dashboard/trends/",
            "Demands": "/dashboard/demands/",
            "Insights": "/dashboard/insights/",
            "Topics": "/dashboard/topics/",
            "Clusters": "/dashboard/clusters/",
            "Chart Data API": "/dashboard/trends/chart-data?keyword=test",
            "Top Keywords API": "/dashboard/trends/top-keywords-chart",
        }

        results: dict[str, dict[str, float]] = {}

        for name, url in endpoints.items():
            metrics = measure_response_time(perf_client, url, iterations=10)
            results[name] = metrics

        # 모든 엔드포인트가 목표 시간 내에 응답하는지 확인
        target_ms = 500
        slow_endpoints = [
            name for name, metrics in results.items() if metrics["avg_ms"] > target_ms
        ]

        # 성능 리포트 출력 (테스트 디버깅용)
        print("\n=== Performance Benchmark Report ===")
        for name, metrics in results.items():
            status = "OK" if metrics["avg_ms"] <= target_ms else "SLOW"
            print(
                f"{name}: avg={metrics['avg_ms']:.1f}ms, "
                f"min={metrics['min_ms']:.1f}ms, "
                f"max={metrics['max_ms']:.1f}ms [{status}]"
            )

        assert len(slow_endpoints) == 0, f"Slow endpoints detected: {slow_endpoints}"
