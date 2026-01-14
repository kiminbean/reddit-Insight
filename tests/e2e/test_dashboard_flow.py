"""E2E tests for dashboard user flows.

대시보드의 주요 사용자 시나리오를 테스트한다.
분석 실행부터 대시보드 표시까지의 전체 흐름을 검증한다.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# 테스트에서 rate limiting 비활성화
os.environ["RATE_LIMIT_PER_MINUTE"] = "10000"


# =============================================================================
# TEST DATA FIXTURES
# =============================================================================


@pytest.fixture
def mock_analysis_data() -> dict[str, Any]:
    """분석 결과 mock 데이터를 생성한다."""
    return {
        "subreddit": "SaaS",
        "post_count": 100,
        "comment_count": 500,
        "analyzed_at": datetime.now(UTC),
        "keywords": [
            {"keyword": "pricing", "count": 50, "trend": "up"},
            {"keyword": "automation", "count": 45, "trend": "up"},
            {"keyword": "integration", "count": 40, "trend": "stable"},
            {"keyword": "api", "count": 35, "trend": "down"},
            {"keyword": "support", "count": 30, "trend": "stable"},
        ],
        "trends": {
            "top_keywords": ["pricing", "automation", "integration"],
            "rising_keywords": ["ai", "machine learning"],
            "growth_rate": {"pricing": 0.15, "automation": 0.12},
        },
        "demands": {
            "top_opportunities": [
                {
                    "representative": "Need better API documentation",
                    "priority_score": 85,
                    "size": 25,
                    "business_potential": "high",
                },
                {
                    "representative": "Integration with Slack",
                    "priority_score": 78,
                    "size": 20,
                    "business_potential": "medium",
                },
            ],
            "by_category": {
                "feature_request": 45,
                "unmet_need": 30,
                "willingness_to_pay": 15,
            },
            "recommendations": [
                "Focus on API improvements",
                "Prioritize Slack integration",
            ],
        },
        "competition": {
            "competitors": [
                {"name": "Competitor A", "mention_count": 25, "sentiment": 0.3},
                {"name": "Competitor B", "mention_count": 18, "sentiment": -0.2},
            ],
            "market_trends": ["Consolidation", "AI adoption"],
        },
        "insights": [
            {
                "id": "insight_001",
                "type": "opportunity",
                "title": "High demand for API documentation",
                "description": "Users frequently request better API docs",
                "confidence": 0.85,
                "priority": 9,
            },
            {
                "id": "insight_002",
                "type": "trend",
                "title": "Rising interest in automation",
                "description": "Automation-related discussions increased 20%",
                "confidence": 0.78,
                "priority": 8,
            },
        ],
    }


@pytest.fixture
def e2e_client() -> TestClient:
    """E2E 테스트용 TestClient를 생성한다."""
    from reddit_insight.dashboard.app import app

    return TestClient(app)


# =============================================================================
# DASHBOARD HOME FLOW TESTS
# =============================================================================


class TestDashboardHomeFlow:
    """대시보드 홈 페이지 흐름 테스트."""

    def test_dashboard_home_renders_successfully(self, e2e_client: TestClient) -> None:
        """대시보드 홈 페이지가 정상적으로 렌더링된다."""
        response = e2e_client.get("/dashboard/")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        # 페이지 제목 확인
        assert "Dashboard" in response.text

    def test_dashboard_home_shows_summary_section(self, e2e_client: TestClient) -> None:
        """대시보드 홈 페이지에 요약 섹션이 표시된다."""
        response = e2e_client.get("/dashboard/")

        assert response.status_code == 200
        # 요약 관련 요소들이 있는지 확인
        assert "total" in response.text.lower() or "summary" in response.text.lower()

    def test_dashboard_summary_partial_loads(self, e2e_client: TestClient) -> None:
        """대시보드 요약 partial이 정상적으로 로드된다."""
        response = e2e_client.get("/dashboard/summary")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]


# =============================================================================
# FULL ANALYSIS FLOW TESTS
# =============================================================================


class TestFullAnalysisFlow:
    """분석 실행부터 대시보드 표시까지 전체 흐름 테스트."""

    def test_full_analysis_to_dashboard_flow(
        self, e2e_client: TestClient, mock_analysis_data: dict[str, Any]
    ) -> None:
        """분석 실행 -> 대시보드 표시 전체 흐름을 테스트한다."""
        # 1. Mock 데이터로 분석 결과 시뮬레이션
        with patch("reddit_insight.dashboard.data_store.get_current_data") as mock_get:
            mock_data = MagicMock()
            mock_data.subreddit = mock_analysis_data["subreddit"]
            mock_data.post_count = mock_analysis_data["post_count"]
            mock_data.keywords = mock_analysis_data["keywords"]
            mock_data.trends = mock_analysis_data["trends"]
            mock_data.demands = mock_analysis_data["demands"]
            mock_data.insights = mock_analysis_data["insights"]
            mock_get.return_value = mock_data

            # 2. 대시보드 홈 접속
            response = e2e_client.get("/dashboard/")
            assert response.status_code == 200

            # 3. 트렌드 페이지 접속
            response = e2e_client.get("/dashboard/trends/")
            assert response.status_code == 200

            # 4. 수요 페이지 접속
            response = e2e_client.get("/dashboard/demands/")
            assert response.status_code == 200

            # 5. 인사이트 페이지 접속
            response = e2e_client.get("/dashboard/insights/")
            assert response.status_code == 200

    def test_analysis_detail_page_with_valid_id(
        self, e2e_client: TestClient, mock_analysis_data: dict[str, Any]
    ) -> None:
        """유효한 ID로 분석 상세 페이지에 접근한다."""
        # 라우터에서 import한 위치에서 패치해야 함
        with patch("reddit_insight.dashboard.routers.dashboard.load_analysis_by_id") as mock_load:
            mock_data = MagicMock()
            mock_data.subreddit = mock_analysis_data["subreddit"]
            mock_data.keywords = mock_analysis_data["keywords"]
            mock_data.demands = mock_analysis_data["demands"]
            mock_data.insights = mock_analysis_data["insights"]
            mock_load.return_value = mock_data

            response = e2e_client.get("/dashboard/analysis/1")
            assert response.status_code == 200
            assert "SaaS" in response.text

    def test_analysis_detail_page_with_invalid_id_returns_404(self, e2e_client: TestClient) -> None:
        """잘못된 ID로 분석 상세 페이지 접근 시 404 반환."""
        with patch("reddit_insight.dashboard.routers.dashboard.load_analysis_by_id") as mock_load:
            mock_load.return_value = None

            response = e2e_client.get("/dashboard/analysis/9999")
            assert response.status_code == 404


# =============================================================================
# ML PREDICTION FLOW TESTS
# =============================================================================


class TestMLPredictionFlow:
    """ML 예측 흐름 테스트."""

    def test_prediction_endpoint_returns_chart_data(self, e2e_client: TestClient) -> None:
        """예측 엔드포인트가 차트 데이터를 반환한다."""
        with patch(
            "reddit_insight.dashboard.routers.trends.get_prediction_service"
        ) as mock_service:
            mock_prediction = MagicMock()
            mock_prediction.to_chart_data.return_value = {
                "labels": ["2024-01-01", "2024-01-02", "2024-01-03"],
                "datasets": [
                    {
                        "label": "Historical",
                        "data": [10, 12, 15],
                    },
                    {
                        "label": "Predicted",
                        "data": [None, None, 18],
                    },
                ],
            }
            mock_service.return_value.predict_keyword_trend.return_value = mock_prediction

            response = e2e_client.get("/dashboard/trends/predict/pricing")
            assert response.status_code == 200
            data = response.json()
            assert "labels" in data
            assert "datasets" in data

    def test_prediction_with_custom_parameters(self, e2e_client: TestClient) -> None:
        """커스텀 파라미터로 예측을 실행한다."""
        with patch(
            "reddit_insight.dashboard.routers.trends.get_prediction_service"
        ) as mock_service:
            mock_prediction = MagicMock()
            mock_prediction.to_chart_data.return_value = {"labels": [], "datasets": []}
            mock_service.return_value.predict_keyword_trend.return_value = mock_prediction

            response = e2e_client.get(
                "/dashboard/trends/predict/test?days=14&historical_days=30&confidence=0.9"
            )
            assert response.status_code == 200


# =============================================================================
# TOPIC ANALYSIS FLOW TESTS
# =============================================================================


class TestTopicAnalysisFlow:
    """토픽 분석 흐름 테스트."""

    def test_topics_home_page_renders(self, e2e_client: TestClient) -> None:
        """토픽 분석 홈 페이지가 렌더링된다."""
        response = e2e_client.get("/dashboard/topics/")
        assert response.status_code == 200
        assert "Topics" in response.text

    def test_topic_analysis_endpoint_returns_data(self, e2e_client: TestClient) -> None:
        """토픽 분석 엔드포인트가 데이터를 반환한다."""
        with patch(
            "reddit_insight.dashboard.routers.topics.get_topic_service"
        ) as mock_service:
            mock_result = MagicMock()
            # to_chart_data()의 실제 반환 형식에 맞게 수정
            mock_result.to_chart_data.return_value = {
                "labels": ["Topic 0: word1", "Topic 1: word2"],
                "datasets": [{"label": "Document Distribution", "data": [0.6, 0.4]}],
                "metadata": {
                    "n_topics": 2,
                    "method": "lda",
                    "overall_coherence": 0.5,
                    "document_count": 100,
                    "topics": [
                        {"id": 0, "label": "word1", "keywords": [{"word": "word1", "weight": 0.5}]},
                        {"id": 1, "label": "word2", "keywords": [{"word": "word2", "weight": 0.5}]},
                    ],
                },
            }
            mock_service.return_value.analyze_topics.return_value = mock_result

            response = e2e_client.get("/dashboard/topics/analyze?n_topics=5")
            assert response.status_code == 200
            data = response.json()
            assert "labels" in data
            assert "metadata" in data

    def test_topic_distribution_endpoint(self, e2e_client: TestClient) -> None:
        """토픽 분포 엔드포인트가 파이 차트 데이터를 반환한다."""
        with patch(
            "reddit_insight.dashboard.routers.topics.get_topic_service"
        ) as mock_service:
            mock_result = MagicMock()
            mock_result.topics = [
                MagicMock(id=0, label="Topic 1"),
                MagicMock(id=1, label="Topic 2"),
            ]
            mock_result.topic_distribution = [0.6, 0.4]
            mock_result.n_topics = 2
            mock_result.method = "lda"
            mock_service.return_value.analyze_topics.return_value = mock_result

            response = e2e_client.get("/dashboard/topics/distribution")
            assert response.status_code == 200
            data = response.json()
            assert "labels" in data
            assert "data" in data


# =============================================================================
# CLUSTER ANALYSIS FLOW TESTS
# =============================================================================


class TestClusterAnalysisFlow:
    """클러스터링 흐름 테스트."""

    def test_clusters_home_page_renders(self, e2e_client: TestClient) -> None:
        """클러스터링 홈 페이지가 렌더링된다."""
        response = e2e_client.get("/dashboard/clusters/")
        assert response.status_code == 200
        assert "Clusters" in response.text

    def test_cluster_analysis_endpoint_returns_data(self, e2e_client: TestClient) -> None:
        """클러스터링 분석 엔드포인트가 데이터를 반환한다."""
        with patch(
            "reddit_insight.dashboard.routers.clusters.get_cluster_service"
        ) as mock_service:
            mock_result = MagicMock()
            # to_chart_data()의 실제 반환 형식에 맞게 수정
            mock_result.to_chart_data.return_value = {
                "labels": ["Cluster 0: API", "Cluster 1: Integration"],
                "datasets": [{"label": "Document Count", "data": [30, 25]}],
                "metadata": {
                    "n_clusters": 2,
                    "method": "kmeans",
                    "silhouette_score": 0.5,
                    "document_count": 55,
                    "clusters": [
                        {"id": 0, "label": "API", "size": 30, "keywords": []},
                        {"id": 1, "label": "Integration", "size": 25, "keywords": []},
                    ],
                },
            }
            mock_service.return_value.cluster_documents.return_value = mock_result

            response = e2e_client.get("/dashboard/clusters/analyze?n_clusters=5")
            assert response.status_code == 200
            data = response.json()
            assert "labels" in data
            assert "metadata" in data

    def test_cluster_detail_page_with_valid_id(self, e2e_client: TestClient) -> None:
        """유효한 클러스터 ID로 상세 페이지에 접근한다."""
        with patch(
            "reddit_insight.dashboard.routers.clusters.get_cluster_service"
        ) as mock_service:
            mock_cluster = MagicMock()
            mock_cluster.id = 0
            mock_cluster.label = "Test Cluster"
            mock_cluster.size = 30
            mock_service.return_value.get_cluster_by_id.return_value = mock_cluster
            mock_service.return_value.get_cluster_documents.return_value = [
                {"text": "Document 1"},
                {"text": "Document 2"},
            ]

            response = e2e_client.get("/dashboard/clusters/cluster/0")
            assert response.status_code == 200

    def test_cluster_detail_page_with_invalid_id(self, e2e_client: TestClient) -> None:
        """잘못된 클러스터 ID로 상세 페이지 접근 시 에러 표시."""
        with patch(
            "reddit_insight.dashboard.routers.clusters.get_cluster_service"
        ) as mock_service:
            mock_service.return_value.get_cluster_by_id.return_value = None
            mock_service.return_value.get_cluster_documents.return_value = []

            response = e2e_client.get("/dashboard/clusters/cluster/999")
            # 에러 메시지 표시 (404가 아닌 200 with error message)
            assert response.status_code == 200
            assert "not found" in response.text.lower()


# =============================================================================
# ANOMALY DETECTION FLOW TESTS
# =============================================================================


class TestAnomalyDetectionFlow:
    """이상 탐지 흐름 테스트."""

    def test_anomaly_detection_endpoint_returns_data(self, e2e_client: TestClient) -> None:
        """이상 탐지 엔드포인트가 데이터를 반환한다."""
        with patch(
            "reddit_insight.dashboard.routers.trends.get_anomaly_service"
        ) as mock_service:
            mock_result = MagicMock()
            mock_result.to_chart_data.return_value = {
                "labels": ["2024-01-01", "2024-01-02"],
                "datasets": [
                    {"label": "Values", "data": [10, 50]},
                    {"label": "Anomalies", "data": [None, 50]},
                ],
                "anomaly_count": 1,
            }
            mock_service.return_value.detect_anomalies.return_value = mock_result

            response = e2e_client.get("/dashboard/trends/anomalies/test_keyword")
            assert response.status_code == 200
            data = response.json()
            assert "labels" in data
            assert "datasets" in data


# =============================================================================
# INSIGHTS FLOW TESTS
# =============================================================================


class TestInsightsFlow:
    """인사이트 흐름 테스트."""

    def test_insights_home_page_renders(self, e2e_client: TestClient) -> None:
        """인사이트 홈 페이지가 렌더링된다."""
        response = e2e_client.get("/dashboard/insights/")
        assert response.status_code == 200
        assert "Insights" in response.text

    def test_insights_with_filters(self, e2e_client: TestClient) -> None:
        """필터가 적용된 인사이트 목록을 조회한다."""
        response = e2e_client.get(
            "/dashboard/insights/?insight_type=opportunity&min_confidence=0.5"
        )
        assert response.status_code == 200

    def test_insight_detail_page_with_valid_id(self, e2e_client: TestClient) -> None:
        """유효한 인사이트 ID로 상세 페이지에 접근한다."""
        with patch(
            "reddit_insight.dashboard.services.insight_service.get_current_data"
        ) as mock_data:
            # get_current_data가 인사이트가 있는 데이터를 반환하도록 mock
            mock_data.return_value = MagicMock(
                insights=[
                    {
                        "type": "opportunity",
                        "title": "Test Insight",
                        "description": "Test Description",
                        "confidence": 0.85,
                        "evidence": ["evidence1"],
                        "related_entities": [],
                        "related_demands": [],
                    }
                ]
            )

            response = e2e_client.get("/dashboard/insights/insight_000")
            assert response.status_code == 200

    def test_insight_detail_page_with_invalid_id_returns_404(self, e2e_client: TestClient) -> None:
        """잘못된 인사이트 ID로 상세 페이지 접근 시 404 반환."""
        with patch(
            "reddit_insight.dashboard.routers.insights.get_insight_service"
        ) as mock_service:
            mock_service.return_value.get_insight_detail.return_value = None

            response = e2e_client.get("/dashboard/insights/nonexistent")
            assert response.status_code == 404


# =============================================================================
# DEMANDS FLOW TESTS
# =============================================================================


class TestDemandsFlow:
    """수요 분석 흐름 테스트."""

    def test_demands_home_page_renders(self, e2e_client: TestClient) -> None:
        """수요 분석 홈 페이지가 렌더링된다."""
        response = e2e_client.get("/dashboard/demands/")
        assert response.status_code == 200
        assert "Demands" in response.text

    def test_demands_list_with_filters(self, e2e_client: TestClient) -> None:
        """필터가 적용된 수요 목록을 조회한다."""
        response = e2e_client.get(
            "/dashboard/demands/list?category=feature_request&min_priority=50"
        )
        assert response.status_code == 200

    def test_demand_detail_page_with_valid_id(
        self, e2e_client: TestClient, mock_analysis_data: dict[str, Any]
    ) -> None:
        """유효한 수요 ID로 상세 페이지에 접근한다."""
        with patch("reddit_insight.dashboard.routers.demands.get_current_data") as mock_get:
            mock_data = MagicMock()
            mock_data.demands = mock_analysis_data["demands"]
            mock_get.return_value = mock_data

            response = e2e_client.get("/dashboard/demands/demand_000")
            assert response.status_code == 200

    def test_demand_detail_page_with_invalid_id_returns_404(self, e2e_client: TestClient) -> None:
        """잘못된 수요 ID로 상세 페이지 접근 시 404 반환."""
        with patch("reddit_insight.dashboard.routers.demands.get_current_data") as mock_get:
            mock_get.return_value = None

            response = e2e_client.get("/dashboard/demands/nonexistent")
            assert response.status_code == 404


# =============================================================================
# COMPETITION FLOW TESTS
# =============================================================================


class TestCompetitionFlow:
    """경쟁 분석 흐름 테스트."""

    def test_competition_home_page_renders(self, e2e_client: TestClient) -> None:
        """경쟁 분석 홈 페이지가 렌더링된다."""
        response = e2e_client.get("/dashboard/competition/")
        assert response.status_code == 200


# =============================================================================
# REPORT GENERATION FLOW TESTS
# =============================================================================


class TestReportGenerationFlow:
    """보고서 생성 흐름 테스트."""

    def test_report_page_renders(self, e2e_client: TestClient) -> None:
        """보고서 생성 페이지가 렌더링된다."""
        response = e2e_client.get("/dashboard/insights/report/generate")
        assert response.status_code == 200

    def test_report_download_without_data_returns_404(self, e2e_client: TestClient) -> None:
        """데이터가 없을 때 보고서 다운로드 시 404 반환."""
        with patch(
            "reddit_insight.dashboard.services.report_service.get_current_data"
        ) as mock_data:
            # get_current_data가 None을 반환하면 generate_report가 None을 반환하고
            # 결과적으로 generate_markdown_report도 None을 반환하여 404
            mock_data.return_value = None

            response = e2e_client.get("/dashboard/insights/report/download")
            assert response.status_code == 404
