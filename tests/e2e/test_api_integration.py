"""API integration tests for all dashboard endpoints.

모든 대시보드 API 엔드포인트의 통합 테스트를 수행한다.
HTTP 상태 코드, 응답 형식, 에러 핸들링을 검증한다.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# 테스트에서 rate limiting 비활성화
os.environ["RATE_LIMIT_PER_MINUTE"] = "10000"


@pytest.fixture
def api_client() -> TestClient:
    """API 테스트용 TestClient를 생성한다."""
    from reddit_insight.dashboard.app import app

    return TestClient(app)


# =============================================================================
# DASHBOARD MAIN ENDPOINTS
# =============================================================================


class TestDashboardEndpoints:
    """대시보드 메인 엔드포인트 테스트."""

    def test_get_dashboard_home(self, api_client: TestClient) -> None:
        """GET /dashboard/ - 홈 페이지 반환."""
        response = api_client.get("/dashboard/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_get_dashboard_summary(self, api_client: TestClient) -> None:
        """GET /dashboard/summary - 요약 partial 반환."""
        response = api_client.get("/dashboard/summary")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_get_analyze_page(self, api_client: TestClient) -> None:
        """GET /dashboard/analyze - 분석 시작 페이지 반환."""
        response = api_client.get("/dashboard/analyze")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_get_analysis_detail_with_valid_id(self, api_client: TestClient) -> None:
        """GET /dashboard/analysis/{id} - 유효한 ID로 분석 상세 조회."""
        with patch("reddit_insight.dashboard.data_store.load_analysis_by_id") as mock:
            mock_data = MagicMock()
            mock_data.subreddit = "test"
            mock_data.keywords = []
            mock_data.demands = {}
            mock_data.insights = []
            mock.return_value = mock_data

            response = api_client.get("/dashboard/analysis/1")
            assert response.status_code == 200

    def test_get_analysis_detail_with_invalid_id(self, api_client: TestClient) -> None:
        """GET /dashboard/analysis/{id} - 잘못된 ID로 404 반환."""
        with patch("reddit_insight.dashboard.data_store.load_analysis_by_id") as mock:
            mock.return_value = None

            response = api_client.get("/dashboard/analysis/9999")
            assert response.status_code == 404


# =============================================================================
# TRENDS ENDPOINTS
# =============================================================================


class TestTrendsEndpoints:
    """트렌드 엔드포인트 테스트."""

    def test_get_trends_home(self, api_client: TestClient) -> None:
        """GET /dashboard/trends/ - 트렌드 홈 페이지 반환."""
        response = api_client.get("/dashboard/trends/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_get_trends_with_filters(self, api_client: TestClient) -> None:
        """GET /dashboard/trends/ - 필터 파라미터 적용."""
        response = api_client.get("/dashboard/trends/?subreddit=SaaS&days=14&limit=30")
        assert response.status_code == 200

    def test_get_trends_keywords_partial(self, api_client: TestClient) -> None:
        """GET /dashboard/trends/keywords - 키워드 목록 partial."""
        response = api_client.get("/dashboard/trends/keywords")
        assert response.status_code == 200

    def test_get_trends_rising_partial(self, api_client: TestClient) -> None:
        """GET /dashboard/trends/rising - Rising 키워드 partial."""
        response = api_client.get("/dashboard/trends/rising")
        assert response.status_code == 200

    def test_get_trends_chart_data(self, api_client: TestClient) -> None:
        """GET /dashboard/trends/chart-data - 차트 데이터 JSON 반환."""
        response = api_client.get("/dashboard/trends/chart-data?keyword=test")
        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]

    def test_get_top_keywords_chart_data(self, api_client: TestClient) -> None:
        """GET /dashboard/trends/top-keywords-chart - 상위 키워드 차트 데이터."""
        response = api_client.get("/dashboard/trends/top-keywords-chart")
        assert response.status_code == 200
        data = response.json()
        assert "labels" in data
        assert "datasets" in data


# =============================================================================
# PREDICTION ENDPOINTS
# =============================================================================


class TestPredictionEndpoints:
    """예측 엔드포인트 테스트."""

    def test_get_prediction_for_keyword(self, api_client: TestClient) -> None:
        """GET /dashboard/trends/predict/{keyword} - 키워드 예측."""
        with patch(
            "reddit_insight.dashboard.services.prediction_service.get_prediction_service"
        ) as mock_service:
            mock_result = MagicMock()
            mock_result.to_chart_data.return_value = {
                "labels": [],
                "datasets": [],
                "metadata": {},
            }
            mock_service.return_value.predict_keyword_trend.return_value = mock_result

            response = api_client.get("/dashboard/trends/predict/test_keyword")
            assert response.status_code == 200
            assert "application/json" in response.headers["content-type"]

    def test_get_prediction_with_custom_params(self, api_client: TestClient) -> None:
        """GET /dashboard/trends/predict/{keyword} - 커스텀 파라미터."""
        with patch(
            "reddit_insight.dashboard.services.prediction_service.get_prediction_service"
        ) as mock_service:
            mock_result = MagicMock()
            mock_result.to_chart_data.return_value = {"labels": [], "datasets": []}
            mock_service.return_value.predict_keyword_trend.return_value = mock_result

            response = api_client.get(
                "/dashboard/trends/predict/test?days=10&historical_days=20&confidence=0.9"
            )
            assert response.status_code == 200

    def test_get_prediction_partial(self, api_client: TestClient) -> None:
        """GET /dashboard/trends/predict-partial/{keyword} - 예측 HTML partial."""
        with patch(
            "reddit_insight.dashboard.routers.trends.get_prediction_service"
        ) as mock_service:
            # PredictionView 데이터클래스를 사용하여 실제 객체 생성
            from reddit_insight.dashboard.services.prediction_service import PredictionView

            mock_result = PredictionView(
                keyword="test",
                historical_dates=["2024-01-01", "2024-01-02"],
                historical_values=[10.0, 12.0],
                forecast_dates=["2024-01-03", "2024-01-04"],
                forecast_values=[14.0, 16.0],
                confidence_lower=[12.0, 14.0],
                confidence_upper=[16.0, 18.0],
                model_name="TestModel",
                metrics={"MAE": 1.0, "RMSE": 1.5, "MAPE": 5.0},
                confidence_level=0.95,
            )
            mock_service.return_value.predict_keyword_trend.return_value = mock_result

            response = api_client.get("/dashboard/trends/predict-partial/test")
            assert response.status_code == 200
            assert "text/html" in response.headers["content-type"]


# =============================================================================
# ANOMALY DETECTION ENDPOINTS
# =============================================================================


class TestAnomalyEndpoints:
    """이상 탐지 엔드포인트 테스트."""

    def test_get_anomalies_for_keyword(self, api_client: TestClient) -> None:
        """GET /dashboard/trends/anomalies/{keyword} - 이상 탐지."""
        with patch(
            "reddit_insight.dashboard.services.anomaly_service.get_anomaly_service"
        ) as mock_service:
            mock_result = MagicMock()
            mock_result.to_chart_data.return_value = {
                "labels": [],
                "datasets": [],
                "anomaly_count": 0,
            }
            mock_service.return_value.detect_anomalies.return_value = mock_result

            response = api_client.get("/dashboard/trends/anomalies/test_keyword")
            assert response.status_code == 200
            assert "application/json" in response.headers["content-type"]

    def test_get_anomalies_with_params(self, api_client: TestClient) -> None:
        """GET /dashboard/trends/anomalies/{keyword} - 파라미터 적용."""
        with patch(
            "reddit_insight.dashboard.services.anomaly_service.get_anomaly_service"
        ) as mock_service:
            mock_result = MagicMock()
            mock_result.to_chart_data.return_value = {"labels": [], "datasets": []}
            mock_service.return_value.detect_anomalies.return_value = mock_result

            response = api_client.get(
                "/dashboard/trends/anomalies/test?days=60&method=zscore&threshold=2.5"
            )
            assert response.status_code == 200

    def test_get_anomalies_partial(self, api_client: TestClient) -> None:
        """GET /dashboard/trends/anomalies-partial/{keyword} - 이상 탐지 partial."""
        with patch(
            "reddit_insight.dashboard.services.anomaly_service.get_anomaly_service"
        ) as mock_service:
            mock_result = MagicMock()
            mock_result.anomalies = []
            mock_result.anomaly_count = 0
            mock_service.return_value.detect_anomalies.return_value = mock_result

            response = api_client.get("/dashboard/trends/anomalies-partial/test")
            assert response.status_code == 200
            assert "text/html" in response.headers["content-type"]


# =============================================================================
# DEMANDS ENDPOINTS
# =============================================================================


class TestDemandsEndpoints:
    """수요 분석 엔드포인트 테스트."""

    def test_get_demands_home(self, api_client: TestClient) -> None:
        """GET /dashboard/demands/ - 수요 분석 홈 페이지."""
        response = api_client.get("/dashboard/demands/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_get_demands_list_partial(self, api_client: TestClient) -> None:
        """GET /dashboard/demands/list - 수요 목록 partial."""
        response = api_client.get("/dashboard/demands/list")
        assert response.status_code == 200

    def test_get_demands_list_with_filters(self, api_client: TestClient) -> None:
        """GET /dashboard/demands/list - 필터 적용."""
        response = api_client.get(
            "/dashboard/demands/list?category=feature_request&min_priority=50&limit=10"
        )
        assert response.status_code == 200

    def test_get_demand_detail(self, api_client: TestClient) -> None:
        """GET /dashboard/demands/{demand_id} - 수요 상세 페이지."""
        with patch("reddit_insight.dashboard.routers.demands.get_current_data") as mock:
            mock_data = MagicMock()
            mock_data.demands = {
                "top_opportunities": [
                    {
                        "representative": "Test demand",
                        "priority_score": 80,
                        "size": 10,
                        "business_potential": "high",
                    }
                ]
            }
            mock.return_value = mock_data

            response = api_client.get("/dashboard/demands/demand_000")
            assert response.status_code == 200

    def test_get_category_stats(self, api_client: TestClient) -> None:
        """GET /dashboard/demands/categories/stats - 카테고리 통계."""
        response = api_client.get("/dashboard/demands/categories/stats")
        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]


# =============================================================================
# COMPETITION ENDPOINTS
# =============================================================================


class TestCompetitionEndpoints:
    """경쟁 분석 엔드포인트 테스트."""

    def test_get_competition_home(self, api_client: TestClient) -> None:
        """GET /dashboard/competition/ - 경쟁 분석 홈 페이지."""
        response = api_client.get("/dashboard/competition/")
        assert response.status_code == 200


# =============================================================================
# INSIGHTS ENDPOINTS
# =============================================================================


class TestInsightsEndpoints:
    """인사이트 엔드포인트 테스트."""

    def test_get_insights_home(self, api_client: TestClient) -> None:
        """GET /dashboard/insights/ - 인사이트 홈 페이지."""
        response = api_client.get("/dashboard/insights/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_get_insights_with_filters(self, api_client: TestClient) -> None:
        """GET /dashboard/insights/ - 필터 적용."""
        response = api_client.get(
            "/dashboard/insights/?insight_type=opportunity&min_confidence=0.5&limit=10"
        )
        assert response.status_code == 200

    def test_get_insights_list_partial(self, api_client: TestClient) -> None:
        """GET /dashboard/insights/list - 인사이트 목록 partial."""
        response = api_client.get("/dashboard/insights/list")
        assert response.status_code == 200

    def test_get_recommendations_partial(self, api_client: TestClient) -> None:
        """GET /dashboard/insights/recommendations - 추천 목록 partial."""
        response = api_client.get("/dashboard/insights/recommendations")
        assert response.status_code == 200

    def test_get_opportunities_partial(self, api_client: TestClient) -> None:
        """GET /dashboard/insights/opportunities - 기회 랭킹 partial."""
        response = api_client.get("/dashboard/insights/opportunities")
        assert response.status_code == 200

    def test_get_insight_detail_with_valid_id(self, api_client: TestClient) -> None:
        """GET /dashboard/insights/{id} - 유효한 ID로 상세 조회."""
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

            response = api_client.get("/dashboard/insights/insight_000")
            assert response.status_code == 200

    def test_get_insight_detail_with_invalid_id(self, api_client: TestClient) -> None:
        """GET /dashboard/insights/{id} - 잘못된 ID로 404 반환."""
        with patch(
            "reddit_insight.dashboard.services.insight_service.get_insight_service"
        ) as mock_service:
            mock_service.return_value.get_insight_detail.return_value = None

            response = api_client.get("/dashboard/insights/nonexistent")
            assert response.status_code == 404

    def test_get_score_breakdown_chart(self, api_client: TestClient) -> None:
        """GET /dashboard/insights/chart/score-breakdown/{id} - 스코어 차트."""
        with patch(
            "reddit_insight.dashboard.services.insight_service.get_current_data"
        ) as mock_data:
            # get_current_data가 인사이트가 있는 데이터를 반환하도록 mock
            mock_data.return_value = MagicMock(
                insights=[
                    {
                        "type": "opportunity",
                        "title": "Test Insight",
                        "confidence": 0.85,
                    }
                ]
            )

            response = api_client.get("/dashboard/insights/chart/score-breakdown/insight_000")
            assert response.status_code == 200

    def test_get_grade_distribution_chart(self, api_client: TestClient) -> None:
        """GET /dashboard/insights/chart/grade-distribution - 등급 분포 차트."""
        response = api_client.get("/dashboard/insights/chart/grade-distribution")
        assert response.status_code == 200
        data = response.json()
        assert "labels" in data
        assert "datasets" in data


# =============================================================================
# TOPICS ENDPOINTS
# =============================================================================


class TestTopicsEndpoints:
    """토픽 모델링 엔드포인트 테스트."""

    def test_get_topics_home(self, api_client: TestClient) -> None:
        """GET /dashboard/topics/ - 토픽 분석 홈 페이지."""
        response = api_client.get("/dashboard/topics/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_get_topics_analyze(self, api_client: TestClient) -> None:
        """GET /dashboard/topics/analyze - 토픽 분석 실행."""
        with patch(
            "reddit_insight.dashboard.services.topic_service.get_topic_service"
        ) as mock_service:
            mock_result = MagicMock()
            mock_result.to_chart_data.return_value = {"topics": [], "n_topics": 0}
            mock_service.return_value.analyze_topics.return_value = mock_result

            response = api_client.get("/dashboard/topics/analyze")
            assert response.status_code == 200
            assert "application/json" in response.headers["content-type"]

    def test_get_topics_analyze_with_params(self, api_client: TestClient) -> None:
        """GET /dashboard/topics/analyze - 파라미터 적용."""
        with patch(
            "reddit_insight.dashboard.services.topic_service.get_topic_service"
        ) as mock_service:
            mock_result = MagicMock()
            mock_result.to_chart_data.return_value = {"topics": [], "n_topics": 5}
            mock_service.return_value.analyze_topics.return_value = mock_result

            response = api_client.get("/dashboard/topics/analyze?n_topics=8&method=nmf")
            assert response.status_code == 200

    def test_get_topics_distribution(self, api_client: TestClient) -> None:
        """GET /dashboard/topics/distribution - 토픽 분포 데이터."""
        with patch(
            "reddit_insight.dashboard.services.topic_service.get_topic_service"
        ) as mock_service:
            mock_result = MagicMock()
            mock_result.topics = []
            mock_result.topic_distribution = []
            mock_result.n_topics = 0
            mock_result.method = "lda"
            mock_service.return_value.analyze_topics.return_value = mock_result

            response = api_client.get("/dashboard/topics/distribution")
            assert response.status_code == 200

    def test_get_topics_keywords_partial(self, api_client: TestClient) -> None:
        """GET /dashboard/topics/keywords-partial - 키워드 카드 partial."""
        with patch(
            "reddit_insight.dashboard.services.topic_service.get_topic_service"
        ) as mock_service:
            mock_result = MagicMock()
            mock_result.topics = []
            mock_result.overall_coherence = 0.5
            mock_result.method = "lda"
            mock_result.document_count = 100
            mock_service.return_value.analyze_topics.return_value = mock_result

            response = api_client.get("/dashboard/topics/keywords-partial")
            assert response.status_code == 200

    def test_get_topics_document_count(self, api_client: TestClient) -> None:
        """GET /dashboard/topics/document-count - 문서 수 조회."""
        response = api_client.get("/dashboard/topics/document-count")
        assert response.status_code == 200
        data = response.json()
        assert "document_count" in data
        assert "has_sufficient_data" in data


# =============================================================================
# CLUSTERS ENDPOINTS
# =============================================================================


class TestClustersEndpoints:
    """클러스터링 엔드포인트 테스트."""

    def test_get_clusters_home(self, api_client: TestClient) -> None:
        """GET /dashboard/clusters/ - 클러스터링 홈 페이지."""
        response = api_client.get("/dashboard/clusters/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_get_clusters_analyze(self, api_client: TestClient) -> None:
        """GET /dashboard/clusters/analyze - 클러스터링 분석 실행."""
        with patch(
            "reddit_insight.dashboard.services.cluster_service.get_cluster_service"
        ) as mock_service:
            mock_result = MagicMock()
            mock_result.to_chart_data.return_value = {"clusters": [], "n_clusters": 0}
            mock_service.return_value.cluster_documents.return_value = mock_result

            response = api_client.get("/dashboard/clusters/analyze")
            assert response.status_code == 200
            assert "application/json" in response.headers["content-type"]

    def test_get_clusters_analyze_with_params(self, api_client: TestClient) -> None:
        """GET /dashboard/clusters/analyze - 파라미터 적용."""
        with patch(
            "reddit_insight.dashboard.services.cluster_service.get_cluster_service"
        ) as mock_service:
            mock_result = MagicMock()
            mock_result.to_chart_data.return_value = {"clusters": [], "n_clusters": 5}
            mock_service.return_value.cluster_documents.return_value = mock_result

            response = api_client.get("/dashboard/clusters/analyze?n_clusters=5&method=kmeans")
            assert response.status_code == 200

    def test_get_clusters_distribution(self, api_client: TestClient) -> None:
        """GET /dashboard/clusters/distribution - 클러스터 분포 데이터."""
        with patch(
            "reddit_insight.dashboard.services.cluster_service.get_cluster_service"
        ) as mock_service:
            mock_result = MagicMock()
            mock_result.clusters = []
            mock_result.cluster_sizes = []
            mock_result.n_clusters = 0
            mock_result.method = "kmeans"
            mock_result.silhouette_score = 0.5
            mock_service.return_value.cluster_documents.return_value = mock_result

            response = api_client.get("/dashboard/clusters/distribution")
            assert response.status_code == 200

    def test_get_cluster_detail(self, api_client: TestClient) -> None:
        """GET /dashboard/clusters/cluster/{id} - 클러스터 상세."""
        with patch(
            "reddit_insight.dashboard.services.cluster_service.get_cluster_service"
        ) as mock_service:
            mock_cluster = MagicMock()
            mock_cluster.id = 0
            mock_service.return_value.get_cluster_by_id.return_value = mock_cluster
            mock_service.return_value.get_cluster_documents.return_value = []

            response = api_client.get("/dashboard/clusters/cluster/0")
            assert response.status_code == 200

    def test_get_cluster_documents(self, api_client: TestClient) -> None:
        """GET /dashboard/clusters/cluster/{id}/documents - 클러스터 문서 목록."""
        with patch(
            "reddit_insight.dashboard.services.cluster_service.get_cluster_service"
        ) as mock_service:
            mock_service.return_value.get_cluster_documents.return_value = [
                {"text": "doc1"},
                {"text": "doc2"},
            ]

            response = api_client.get("/dashboard/clusters/cluster/0/documents")
            assert response.status_code == 200
            data = response.json()
            assert "documents" in data
            assert "total_count" in data

    def test_get_cluster_documents_with_pagination(self, api_client: TestClient) -> None:
        """GET /dashboard/clusters/cluster/{id}/documents - 페이지네이션."""
        with patch(
            "reddit_insight.dashboard.services.cluster_service.get_cluster_service"
        ) as mock_service:
            mock_service.return_value.get_cluster_documents.return_value = [
                {"text": f"doc{i}"} for i in range(50)
            ]

            response = api_client.get("/dashboard/clusters/cluster/0/documents?page=2&page_size=10")
            assert response.status_code == 200
            data = response.json()
            assert data["page"] == 2
            assert data["page_size"] == 10

    def test_get_cluster_cards_partial(self, api_client: TestClient) -> None:
        """GET /dashboard/clusters/cards-partial - 클러스터 카드 partial."""
        with patch(
            "reddit_insight.dashboard.services.cluster_service.get_cluster_service"
        ) as mock_service:
            mock_result = MagicMock()
            mock_result.clusters = []
            mock_result.silhouette_score = 0.5
            mock_result.method = "kmeans"
            mock_result.document_count = 100
            mock_service.return_value.cluster_documents.return_value = mock_result

            response = api_client.get("/dashboard/clusters/cards-partial")
            assert response.status_code == 200

    def test_get_clusters_document_count(self, api_client: TestClient) -> None:
        """GET /dashboard/clusters/document-count - 문서 수 조회."""
        response = api_client.get("/dashboard/clusters/document-count")
        assert response.status_code == 200
        data = response.json()
        assert "document_count" in data


# =============================================================================
# REPORT ENDPOINTS
# =============================================================================


class TestReportEndpoints:
    """보고서 생성 엔드포인트 테스트."""

    def test_get_report_page(self, api_client: TestClient) -> None:
        """GET /dashboard/insights/report/generate - 보고서 생성 페이지."""
        response = api_client.get("/dashboard/insights/report/generate")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_get_report_preview(self, api_client: TestClient) -> None:
        """GET /dashboard/insights/report/preview - 보고서 미리보기."""
        response = api_client.get("/dashboard/insights/report/preview")
        assert response.status_code == 200

    def test_get_report_json(self, api_client: TestClient) -> None:
        """GET /dashboard/insights/report/json - 보고서 JSON 데이터."""
        with patch(
            "reddit_insight.dashboard.services.report_service.get_report_service"
        ) as mock_service:
            mock_report = MagicMock()
            mock_report.subreddit = "test"
            mock_report.generated_at = MagicMock()
            mock_report.generated_at.isoformat.return_value = "2024-01-01T00:00:00"
            mock_report.analysis_period = "7 days"
            mock_report.total_posts_analyzed = 100
            mock_report.total_keywords = 50
            mock_report.total_insights = 10
            mock_report.executive_summary = "Summary"
            mock_report.market_overview = "Overview"
            mock_report.business_items = []
            mock_report.trend_analysis = {}
            mock_report.demand_analysis = {}
            mock_report.competition_analysis = {}
            mock_report.recommendations = []
            mock_report.risk_factors = []
            mock_report.conclusion = "Conclusion"
            mock_service.return_value.generate_report.return_value = mock_report

            response = api_client.get("/dashboard/insights/report/json")
            assert response.status_code == 200

    def test_download_report(self, api_client: TestClient) -> None:
        """GET /dashboard/insights/report/download - 마크다운 보고서 다운로드."""
        with patch(
            "reddit_insight.dashboard.services.report_service.get_report_service"
        ) as mock_service:
            mock_service.return_value.generate_markdown_report.return_value = (
                "# Report\n\nContent here"
            )

            response = api_client.get("/dashboard/insights/report/download")
            assert response.status_code == 200
            assert "text/markdown" in response.headers["content-type"]
            assert "attachment" in response.headers.get("content-disposition", "")

    def test_download_report_no_data(self, api_client: TestClient) -> None:
        """GET /dashboard/insights/report/download - 데이터 없을 때 404."""
        with patch(
            "reddit_insight.dashboard.services.report_service.get_current_data"
        ) as mock_data:
            # get_current_data가 None을 반환하면 generate_report가 None을 반환하고
            # 결과적으로 generate_markdown_report도 None을 반환하여 404
            mock_data.return_value = None

            response = api_client.get("/dashboard/insights/report/download")
            assert response.status_code == 404


# =============================================================================
# QUERY PARAMETER VALIDATION TESTS
# =============================================================================


class TestQueryParameterValidation:
    """쿼리 파라미터 검증 테스트."""

    def test_trends_days_validation(self, api_client: TestClient) -> None:
        """days 파라미터 범위 검증 (1-30)."""
        # 유효한 범위
        response = api_client.get("/dashboard/trends/?days=15")
        assert response.status_code == 200

        # 범위 초과
        response = api_client.get("/dashboard/trends/?days=100")
        assert response.status_code == 422  # Validation error

    def test_trends_limit_validation(self, api_client: TestClient) -> None:
        """limit 파라미터 범위 검증 (1-100)."""
        response = api_client.get("/dashboard/trends/?limit=0")
        assert response.status_code == 422

        response = api_client.get("/dashboard/trends/?limit=200")
        assert response.status_code == 422

    def test_prediction_confidence_validation(self, api_client: TestClient) -> None:
        """confidence 파라미터 범위 검증 (0.5-0.99)."""
        with patch(
            "reddit_insight.dashboard.services.prediction_service.get_prediction_service"
        ) as mock_service:
            mock_result = MagicMock()
            mock_result.to_chart_data.return_value = {"labels": [], "datasets": []}
            mock_service.return_value.predict_keyword_trend.return_value = mock_result

            # 유효한 범위
            response = api_client.get("/dashboard/trends/predict/test?confidence=0.95")
            assert response.status_code == 200

        # 범위 초과
        response = api_client.get("/dashboard/trends/predict/test?confidence=1.5")
        assert response.status_code == 422

    def test_anomaly_threshold_validation(self, api_client: TestClient) -> None:
        """threshold 파라미터 범위 검증 (1.0-5.0)."""
        with patch(
            "reddit_insight.dashboard.services.anomaly_service.get_anomaly_service"
        ) as mock_service:
            mock_result = MagicMock()
            mock_result.to_chart_data.return_value = {"labels": [], "datasets": []}
            mock_service.return_value.detect_anomalies.return_value = mock_result

            # 유효한 범위
            response = api_client.get("/dashboard/trends/anomalies/test?threshold=3.0")
            assert response.status_code == 200

        # 범위 초과
        response = api_client.get("/dashboard/trends/anomalies/test?threshold=10.0")
        assert response.status_code == 422

    def test_topics_n_topics_validation(self, api_client: TestClient) -> None:
        """n_topics 파라미터 범위 검증 (2-10)."""
        with patch(
            "reddit_insight.dashboard.services.topic_service.get_topic_service"
        ) as mock_service:
            mock_result = MagicMock()
            mock_result.to_chart_data.return_value = {"topics": []}
            mock_service.return_value.analyze_topics.return_value = mock_result

            # 유효한 범위
            response = api_client.get("/dashboard/topics/analyze?n_topics=5")
            assert response.status_code == 200

        # 범위 미달
        response = api_client.get("/dashboard/topics/analyze?n_topics=1")
        assert response.status_code == 422

        # 범위 초과
        response = api_client.get("/dashboard/topics/analyze?n_topics=20")
        assert response.status_code == 422

    def test_clusters_n_clusters_validation(self, api_client: TestClient) -> None:
        """n_clusters 파라미터 범위 검증 (2-10)."""
        with patch(
            "reddit_insight.dashboard.services.cluster_service.get_cluster_service"
        ) as mock_service:
            mock_result = MagicMock()
            mock_result.to_chart_data.return_value = {"clusters": []}
            mock_service.return_value.cluster_documents.return_value = mock_result

            # 유효한 범위
            response = api_client.get("/dashboard/clusters/analyze?n_clusters=5")
            assert response.status_code == 200

        # 범위 미달
        response = api_client.get("/dashboard/clusters/analyze?n_clusters=1")
        assert response.status_code == 422

    def test_pagination_validation(self, api_client: TestClient) -> None:
        """페이지네이션 파라미터 검증."""
        with patch(
            "reddit_insight.dashboard.services.cluster_service.get_cluster_service"
        ) as mock_service:
            mock_service.return_value.get_cluster_documents.return_value = []

            # 유효한 파라미터
            response = api_client.get("/dashboard/clusters/cluster/0/documents?page=1&page_size=20")
            assert response.status_code == 200

        # page 0은 허용되지 않음
        response = api_client.get("/dashboard/clusters/cluster/0/documents?page=0")
        assert response.status_code == 422

        # page_size 범위 초과
        response = api_client.get("/dashboard/clusters/cluster/0/documents?page_size=200")
        assert response.status_code == 422
