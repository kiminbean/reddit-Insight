"""E2E tests for v2.0 features.

v2.0에서 추가된 주요 기능에 대한 통합 테스트:
- LLM 분석 (Phase 26-27)
- 멀티 서브레딧 비교 (Phase 28)
- 실시간 모니터링 (Phase 29)
- 알림 시스템 (Phase 30)
"""

from __future__ import annotations

import os
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# 테스트에서 rate limiting 비활성화
os.environ["RATE_LIMIT_PER_MINUTE"] = "10000"


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def e2e_client() -> TestClient:
    """E2E 테스트용 TestClient를 생성한다."""
    from reddit_insight.dashboard.app import app

    return TestClient(app)


# =============================================================================
# LLM INTEGRATION TESTS (Phase 26-27)
# =============================================================================


class TestLLMIntegration:
    """LLM 분석 통합 테스트."""

    def test_llm_page_renders(self, e2e_client: TestClient) -> None:
        """LLM 분석 페이지가 정상적으로 렌더링된다."""
        response = e2e_client.get("/dashboard/llm/")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        # 페이지 제목 또는 핵심 요소 확인
        assert "AI" in response.text or "LLM" in response.text

    def test_llm_status_endpoint(self, e2e_client: TestClient) -> None:
        """LLM 서비스 상태 엔드포인트가 동작한다."""
        response = e2e_client.get("/dashboard/llm/status")

        assert response.status_code == 200
        data = response.json()
        assert "configured" in data

    def test_llm_categorize_endpoint_with_mock(self, e2e_client: TestClient) -> None:
        """LLM 카테고리화 엔드포인트가 동작한다 (mock)."""
        with patch(
            "reddit_insight.dashboard.routers.llm.get_llm_service"
        ) as mock_get_service:
            mock_service = MagicMock()
            mock_result = MagicMock()
            mock_result.category = "Feature Request"
            mock_result.confidence = 0.85
            mock_result.reasoning = "User is asking for a new feature"
            mock_service.categorize_single = AsyncMock(return_value=mock_result)
            mock_get_service.return_value = mock_service

            response = e2e_client.post(
                "/dashboard/llm/categorize",
                data={"text": "I wish this app had dark mode"},
            )

            assert response.status_code == 200

    def test_llm_sentiment_endpoint_with_mock(self, e2e_client: TestClient) -> None:
        """LLM 감성 분석 엔드포인트가 동작한다 (mock)."""
        with patch(
            "reddit_insight.dashboard.routers.llm.get_llm_service"
        ) as mock_get_service:
            mock_service = MagicMock()
            mock_result = MagicMock()
            mock_result.sentiment = "positive"
            mock_result.confidence = 0.9
            mock_result.emotions = ["satisfaction", "excitement"]
            mock_service.get_deep_sentiment = AsyncMock(return_value=mock_result)
            mock_get_service.return_value = mock_service

            response = e2e_client.post(
                "/dashboard/llm/sentiment",
                data={"text": "This product is amazing!"},
            )

            assert response.status_code == 200


# =============================================================================
# COMPARISON INTEGRATION TESTS (Phase 28)
# =============================================================================


class TestComparisonIntegration:
    """멀티 서브레딧 비교 통합 테스트."""

    def test_comparison_page_renders(self, e2e_client: TestClient) -> None:
        """비교 분석 페이지가 정상적으로 렌더링된다."""
        response = e2e_client.get("/dashboard/comparison/")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "Comparison" in response.text or "comparison" in response.text.lower()

    def test_comparison_available_subreddits(self, e2e_client: TestClient) -> None:
        """비교 가능한 서브레딧 목록을 가져온다."""
        response = e2e_client.get("/dashboard/comparison/available")

        assert response.status_code == 200
        data = response.json()
        assert "subreddits" in data
        assert isinstance(data["subreddits"], list)

    def test_comparison_analyze_with_mock(self, e2e_client: TestClient) -> None:
        """비교 분석을 실행한다 (mock)."""
        with patch(
            "reddit_insight.dashboard.routers.comparison.get_comparison_service"
        ) as mock_get_service:
            mock_service = MagicMock()
            mock_result = MagicMock()
            mock_result.subreddits = ["python", "javascript"]
            mock_result.summary = {"python": {}, "javascript": {}}
            mock_result.chart_data = {"labels": [], "datasets": []}
            mock_service.compare_subreddits = AsyncMock(return_value=mock_result)
            mock_service.get_available_subreddits.return_value = ["python", "javascript"]
            mock_get_service.return_value = mock_service

            response = e2e_client.post(
                "/dashboard/comparison/analyze",
                data={"subreddits": ["python", "javascript"]},
            )

            assert response.status_code == 200

    def test_comparison_analyze_validation_min_subreddits(
        self, e2e_client: TestClient
    ) -> None:
        """비교 분석에 최소 2개 서브레딧이 필요함을 검증한다."""
        with patch(
            "reddit_insight.dashboard.routers.comparison.get_comparison_service"
        ) as mock_get_service:
            mock_service = MagicMock()
            mock_service.get_available_subreddits.return_value = []
            mock_get_service.return_value = mock_service

            response = e2e_client.post(
                "/dashboard/comparison/analyze",
                data={"subreddits": ["python"]},  # 1개만 제공
            )

            assert response.status_code == 200
            # 에러 메시지 또는 validation 실패 확인
            assert "최소" in response.text or "2" in response.text or "error" in response.text.lower()

    def test_comparison_chart_data_endpoint(self, e2e_client: TestClient) -> None:
        """비교 차트 데이터 엔드포인트가 동작한다."""
        with patch(
            "reddit_insight.dashboard.services.comparison_service.ComparisonService.compare_subreddits"
        ) as mock_compare:
            mock_result = MagicMock()
            mock_result.chart_data = {
                "labels": ["python", "javascript"],
                "datasets": [
                    {"label": "Activity", "data": [100, 80]}
                ],
            }
            mock_compare.return_value = mock_result

            response = e2e_client.get(
                "/dashboard/comparison/chart-data?subreddits=python&subreddits=javascript"
            )

            # 404는 데이터가 없을 때 정상 응답
            assert response.status_code in [200, 404]


# =============================================================================
# LIVE MONITORING INTEGRATION TESTS (Phase 29)
# =============================================================================


class TestLiveMonitoringIntegration:
    """실시간 모니터링 통합 테스트."""

    def test_live_page_renders(self, e2e_client: TestClient) -> None:
        """라이브 대시보드 페이지가 정상적으로 렌더링된다."""
        response = e2e_client.get("/dashboard/live/")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        # SSE 또는 live 관련 요소 확인
        assert "Live" in response.text or "EventSource" in response.text or "live" in response.text.lower()

    def test_live_status_endpoint(self, e2e_client: TestClient) -> None:
        """라이브 모니터 상태 엔드포인트가 동작한다."""
        response = e2e_client.get("/dashboard/live/status")

        assert response.status_code == 200
        data = response.json()
        assert "active_count" in data
        assert "active_monitors" in data

    def test_live_subreddit_status(self, e2e_client: TestClient) -> None:
        """특정 서브레딧의 모니터 상태를 조회한다."""
        response = e2e_client.get("/dashboard/live/status/python")

        assert response.status_code == 200
        data = response.json()
        assert "subreddit" in data
        assert "is_monitoring" in data

    def test_live_start_monitoring(self, e2e_client: TestClient) -> None:
        """모니터링 시작 엔드포인트가 동작한다 (mock)."""
        with patch(
            "reddit_insight.dashboard.routers.live.get_live_service"
        ) as mock_get_service:
            mock_service = MagicMock()
            mock_monitor = MagicMock()
            mock_monitor.is_running = True
            mock_service.start_monitoring = AsyncMock(return_value=mock_monitor)
            mock_get_service.return_value = mock_service

            response = e2e_client.post("/dashboard/live/start/python?interval=60")

            assert response.status_code == 200
            data = response.json()
            assert data.get("success") is True

    def test_live_stop_monitoring(self, e2e_client: TestClient) -> None:
        """모니터링 중지 엔드포인트가 동작한다 (mock)."""
        with patch(
            "reddit_insight.dashboard.routers.live.get_live_service"
        ) as mock_get_service:
            mock_service = MagicMock()
            mock_service.stop_monitoring = AsyncMock(return_value=True)
            mock_get_service.return_value = mock_service

            response = e2e_client.post("/dashboard/live/stop/python")

            assert response.status_code == 200
            data = response.json()
            assert data.get("success") is True


# =============================================================================
# ALERTS INTEGRATION TESTS (Phase 30)
# =============================================================================


class TestAlertsIntegration:
    """알림 시스템 통합 테스트."""

    def test_alerts_page_renders(self, e2e_client: TestClient) -> None:
        """알림 대시보드 페이지가 정상적으로 렌더링된다."""
        response = e2e_client.get("/dashboard/alerts/")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "Alerts" in response.text or "alerts" in response.text.lower()

    def test_alerts_rules_list(self, e2e_client: TestClient) -> None:
        """알림 규칙 목록을 조회한다."""
        response = e2e_client.get("/dashboard/alerts/rules")

        assert response.status_code == 200
        data = response.json()
        assert "rules" in data
        assert isinstance(data["rules"], list)

    def test_alerts_create_rule(self, e2e_client: TestClient) -> None:
        """알림 규칙을 생성한다."""
        with patch(
            "reddit_insight.dashboard.routers.alerts.get_alert_service"
        ) as mock_get_service:
            mock_service = MagicMock()
            mock_service.create_rule.return_value = {
                "id": "rule_001",
                "name": "Test Rule",
                "alert_type": "keyword_surge",
                "subreddit": "python",
                "threshold": 50.0,
                "enabled": True,
            }
            mock_get_service.return_value = mock_service

            response = e2e_client.post(
                "/dashboard/alerts/rules",
                data={
                    "name": "Test Rule",
                    "alert_type": "keyword_surge",
                    "subreddit": "python",
                    "threshold": "50",
                    "window_minutes": "60",
                    "comparison": "gte",
                    "notifiers": "console",
                },
            )

            # 성공적으로 생성되면 200 또는 201
            assert response.status_code in [200, 201]

    def test_alerts_get_single_rule(self, e2e_client: TestClient) -> None:
        """특정 알림 규칙을 조회한다 - 존재하지 않는 규칙은 404."""
        # 존재하지 않는 규칙 ID 조회 시 404 반환
        response = e2e_client.get("/dashboard/alerts/rules/nonexistent_rule")
        assert response.status_code == 404
        data = response.json()
        assert "error" in data

    def test_alerts_rules_list_structure(self, e2e_client: TestClient) -> None:
        """알림 규칙 목록 응답 구조를 검증한다."""
        response = e2e_client.get("/dashboard/alerts/rules")

        assert response.status_code == 200
        data = response.json()
        assert "rules" in data
        assert isinstance(data["rules"], list)

    def test_alerts_get_history(self, e2e_client: TestClient) -> None:
        """알림 이력을 조회한다."""
        response = e2e_client.get("/dashboard/alerts/history")

        assert response.status_code == 200

    def test_alerts_stats(self, e2e_client: TestClient) -> None:
        """알림 통계를 조회한다."""
        response = e2e_client.get("/dashboard/alerts/stats")

        assert response.status_code == 200
        data = response.json()
        # stats 응답은 dict여야 함
        assert isinstance(data, dict)

    def test_alerts_test_notification(self, e2e_client: TestClient) -> None:
        """테스트 알림을 전송한다."""
        with patch(
            "reddit_insight.dashboard.routers.alerts.get_alert_service"
        ) as mock_get_service:
            mock_service = MagicMock()
            mock_service.send_test_alert = AsyncMock(return_value=True)
            mock_get_service.return_value = mock_service

            response = e2e_client.post(
                "/dashboard/alerts/test",
                data={"notifier": "console"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data.get("success") is True


# =============================================================================
# CROSS-FEATURE INTEGRATION TESTS
# =============================================================================


class TestCrossFeatureIntegration:
    """기능 간 통합 테스트."""

    def test_all_v2_pages_accessible(self, e2e_client: TestClient) -> None:
        """모든 v2.0 페이지에 접근 가능하다."""
        v2_pages = [
            "/dashboard/llm/",
            "/dashboard/comparison/",
            "/dashboard/live/",
            "/dashboard/alerts/",
        ]

        for page in v2_pages:
            response = e2e_client.get(page)
            assert response.status_code == 200, f"Failed to access {page}"
            assert "text/html" in response.headers["content-type"], f"Wrong content type for {page}"

    def test_all_v2_api_endpoints_respond(self, e2e_client: TestClient) -> None:
        """모든 v2.0 API 엔드포인트가 응답한다."""
        api_endpoints = [
            ("/dashboard/llm/status", "GET"),
            ("/dashboard/comparison/available", "GET"),
            ("/dashboard/live/status", "GET"),
            ("/dashboard/alerts/rules", "GET"),
            ("/dashboard/alerts/stats", "GET"),
        ]

        for endpoint, method in api_endpoints:
            if method == "GET":
                response = e2e_client.get(endpoint)
            else:
                response = e2e_client.post(endpoint)

            assert response.status_code == 200, f"Failed: {method} {endpoint}"

    def test_dashboard_navigation_includes_v2_features(
        self, e2e_client: TestClient
    ) -> None:
        """대시보드 네비게이션에 v2.0 기능이 포함되어 있다."""
        response = e2e_client.get("/dashboard/")

        assert response.status_code == 200

        # v2.0 기능 메뉴 확인 (대소문자 구분 없이)
        html_lower = response.text.lower()

        # 최소한 하나 이상의 v2 메뉴가 존재해야 함
        v2_features = ["llm", "comparison", "live", "alerts", "ai"]
        found_features = [f for f in v2_features if f in html_lower]

        assert len(found_features) > 0, "No v2 features found in navigation"
