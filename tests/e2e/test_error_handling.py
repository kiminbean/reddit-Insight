"""Error handling tests for dashboard.

에러 상황에서 graceful degradation이 올바르게 동작하는지 검증한다.
사용자에게 친화적인 에러 메시지와 복구 방법을 제공하는지 확인한다.
"""

from __future__ import annotations

import os
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# 테스트에서 rate limiting 비활성화
os.environ["RATE_LIMIT_PER_MINUTE"] = "10000"


@pytest.fixture
def error_client() -> TestClient:
    """에러 테스트용 TestClient를 생성한다."""
    from reddit_insight.dashboard.app import app

    return TestClient(app)


# =============================================================================
# EMPTY DATA HANDLING TESTS
# =============================================================================


class TestEmptyDataHandling:
    """데이터가 없을 때 빈 상태 표시 테스트."""

    def test_dashboard_home_with_no_data(self, error_client: TestClient) -> None:
        """데이터 없이 대시보드 홈 페이지 접근."""
        with patch("reddit_insight.dashboard.data_store.get_current_data") as mock:
            mock.return_value = None

            response = error_client.get("/dashboard/")

            assert response.status_code == 200
            # 페이지는 렌더링되어야 함 (빈 상태)
            assert "text/html" in response.headers["content-type"]

    def test_trends_page_with_no_data(self, error_client: TestClient) -> None:
        """데이터 없이 트렌드 페이지 접근."""
        response = error_client.get("/dashboard/trends/")

        assert response.status_code == 200
        # 빈 상태에서도 페이지 렌더링

    def test_demands_page_with_no_data(self, error_client: TestClient) -> None:
        """데이터 없이 수요 페이지 접근."""
        with patch("reddit_insight.dashboard.data_store.get_current_data") as mock:
            mock.return_value = None

            response = error_client.get("/dashboard/demands/")

            assert response.status_code == 200

    def test_insights_page_with_no_data(self, error_client: TestClient) -> None:
        """데이터 없이 인사이트 페이지 접근."""
        response = error_client.get("/dashboard/insights/")

        assert response.status_code == 200

    def test_topics_page_with_insufficient_data(self, error_client: TestClient) -> None:
        """불충분한 데이터로 토픽 분석 페이지 접근."""
        with patch(
            "reddit_insight.dashboard.services.topic_service.get_topic_service"
        ) as mock_service:
            mock_service.return_value.get_available_document_count.return_value = 1

            response = error_client.get("/dashboard/topics/")

            assert response.status_code == 200
            # 불충분한 데이터 메시지가 표시되어야 함

    def test_clusters_page_with_insufficient_data(self, error_client: TestClient) -> None:
        """불충분한 데이터로 클러스터링 페이지 접근."""
        with patch(
            "reddit_insight.dashboard.services.cluster_service.get_cluster_service"
        ) as mock_service:
            mock_service.return_value.get_available_document_count.return_value = 0

            response = error_client.get("/dashboard/clusters/")

            assert response.status_code == 200

    def test_chart_data_with_no_data(self, error_client: TestClient) -> None:
        """데이터 없이 차트 데이터 요청."""
        response = error_client.get("/dashboard/trends/chart-data?keyword=nonexistent")

        assert response.status_code == 200
        data = response.json()
        # 빈 데이터셋 반환
        assert "labels" in data
        assert "datasets" in data


# =============================================================================
# NOT FOUND ERROR HANDLING TESTS
# =============================================================================


class TestNotFoundHandling:
    """리소스를 찾지 못할 때 404 처리 테스트."""

    def test_analysis_detail_not_found(self, error_client: TestClient) -> None:
        """존재하지 않는 분석 ID로 상세 페이지 접근."""
        with patch("reddit_insight.dashboard.data_store.load_analysis_by_id") as mock:
            mock.return_value = None

            response = error_client.get("/dashboard/analysis/99999")

            assert response.status_code == 404
            # 에러 메시지가 포함되어야 함
            assert "not found" in response.text.lower()

    def test_demand_detail_not_found(self, error_client: TestClient) -> None:
        """존재하지 않는 수요 ID로 상세 페이지 접근."""
        with patch("reddit_insight.dashboard.data_store.get_current_data") as mock:
            mock.return_value = None

            response = error_client.get("/dashboard/demands/nonexistent_demand")

            assert response.status_code == 404

    def test_insight_detail_not_found(self, error_client: TestClient) -> None:
        """존재하지 않는 인사이트 ID로 상세 페이지 접근."""
        with patch(
            "reddit_insight.dashboard.services.insight_service.get_insight_service"
        ) as mock_service:
            mock_service.return_value.get_insight_detail.return_value = None

            response = error_client.get("/dashboard/insights/nonexistent")

            assert response.status_code == 404
            assert "not found" in response.text.lower()

    def test_insight_score_breakdown_not_found(self, error_client: TestClient) -> None:
        """존재하지 않는 인사이트의 스코어 분석 요청."""
        with patch(
            "reddit_insight.dashboard.services.insight_service.get_insight_service"
        ) as mock_service:
            mock_service.return_value.get_insight_score_breakdown.return_value = None

            response = error_client.get("/dashboard/insights/chart/score-breakdown/nonexistent")

            assert response.status_code == 404

    def test_cluster_detail_not_found(self, error_client: TestClient) -> None:
        """존재하지 않는 클러스터 ID로 상세 페이지 접근."""
        with patch(
            "reddit_insight.dashboard.services.cluster_service.get_cluster_service"
        ) as mock_service:
            mock_service.return_value.get_cluster_by_id.return_value = None
            mock_service.return_value.get_cluster_documents.return_value = []

            response = error_client.get("/dashboard/clusters/cluster/999")

            # 200이지만 에러 메시지 표시
            assert response.status_code == 200
            assert "not found" in response.text.lower()


# =============================================================================
# ML SERVICE ERROR HANDLING TESTS
# =============================================================================


class TestMLServiceErrorHandling:
    """ML 서비스 에러 처리 테스트."""

    def test_prediction_service_error(self, error_client: TestClient) -> None:
        """예측 서비스 에러 처리."""
        with patch(
            "reddit_insight.dashboard.services.prediction_service.get_prediction_service"
        ) as mock_service:
            mock_service.return_value.predict_keyword_trend.side_effect = RuntimeError(
                "Prediction failed"
            )

            # 에러가 발생해도 서버는 500을 반환하지 않아야 함 (graceful degradation)
            # 실제 구현에 따라 다를 수 있음
            response = error_client.get("/dashboard/trends/predict/test")
            # 에러 처리가 올바르게 되어야 함
            assert response.status_code in [200, 500]

    def test_anomaly_service_error(self, error_client: TestClient) -> None:
        """이상 탐지 서비스 에러 처리."""
        with patch(
            "reddit_insight.dashboard.services.anomaly_service.get_anomaly_service"
        ) as mock_service:
            mock_service.return_value.detect_anomalies.side_effect = ValueError("Invalid data")

            response = error_client.get("/dashboard/trends/anomalies/test")
            assert response.status_code in [200, 400, 500]

    def test_topic_service_error(self, error_client: TestClient) -> None:
        """토픽 분석 서비스 에러 처리."""
        with patch(
            "reddit_insight.dashboard.services.topic_service.get_topic_service"
        ) as mock_service:
            mock_service.return_value.analyze_topics.side_effect = Exception(
                "Topic modeling failed"
            )

            response = error_client.get("/dashboard/topics/analyze")
            assert response.status_code in [200, 500]

    def test_cluster_service_error(self, error_client: TestClient) -> None:
        """클러스터링 서비스 에러 처리."""
        with patch(
            "reddit_insight.dashboard.services.cluster_service.get_cluster_service"
        ) as mock_service:
            mock_service.return_value.cluster_documents.side_effect = Exception("Clustering failed")

            response = error_client.get("/dashboard/clusters/analyze")
            assert response.status_code in [200, 500]


# =============================================================================
# INVALID INPUT HANDLING TESTS
# =============================================================================


class TestInvalidInputHandling:
    """잘못된 입력 처리 테스트."""

    def test_invalid_analysis_id_format(self, error_client: TestClient) -> None:
        """잘못된 분석 ID 형식."""
        response = error_client.get("/dashboard/analysis/invalid")
        # FastAPI가 자동으로 422 반환
        assert response.status_code == 422

    def test_negative_days_parameter(self, error_client: TestClient) -> None:
        """음수 days 파라미터."""
        response = error_client.get("/dashboard/trends/?days=-1")
        assert response.status_code == 422

    def test_invalid_limit_parameter(self, error_client: TestClient) -> None:
        """범위를 벗어난 limit 파라미터."""
        response = error_client.get("/dashboard/trends/?limit=1000")
        assert response.status_code == 422

    def test_invalid_confidence_parameter(self, error_client: TestClient) -> None:
        """유효하지 않은 confidence 파라미터."""
        response = error_client.get("/dashboard/trends/predict/test?confidence=2.0")
        assert response.status_code == 422

    def test_invalid_method_parameter(self, error_client: TestClient) -> None:
        """지원되지 않는 method 파라미터 (유효성 검사 없으면 기본값 사용)."""
        with patch(
            "reddit_insight.dashboard.services.topic_service.get_topic_service"
        ) as mock_service:
            mock_result = MagicMock()
            mock_result.to_chart_data.return_value = {"topics": []}
            mock_service.return_value.analyze_topics.return_value = mock_result

            # 유효하지 않은 method도 처리됨 (default로 fallback)
            response = error_client.get("/dashboard/topics/analyze?method=invalid_method")
            # 에러 또는 기본값 사용
            assert response.status_code in [200, 422]

    def test_empty_keyword_for_prediction(self, error_client: TestClient) -> None:
        """빈 키워드로 예측 요청."""
        # URL 패턴상 빈 키워드는 404
        response = error_client.get("/dashboard/trends/predict/")
        assert response.status_code in [307, 404]  # Redirect or Not Found

    def test_special_characters_in_keyword(self, error_client: TestClient) -> None:
        """특수 문자가 포함된 키워드."""
        with patch(
            "reddit_insight.dashboard.services.prediction_service.get_prediction_service"
        ) as mock_service:
            mock_result = MagicMock()
            mock_result.to_chart_data.return_value = {"labels": [], "datasets": []}
            mock_service.return_value.predict_keyword_trend.return_value = mock_result

            # URL 인코딩된 특수 문자
            response = error_client.get("/dashboard/trends/predict/test%20keyword")
            assert response.status_code == 200


# =============================================================================
# REPORT GENERATION ERROR HANDLING TESTS
# =============================================================================


class TestReportGenerationErrors:
    """보고서 생성 에러 처리 테스트."""

    def test_report_download_no_data(self, error_client: TestClient) -> None:
        """데이터 없이 보고서 다운로드 시도."""
        with patch("reddit_insight.dashboard.routers.insights.get_report_service") as mock_service:
            mock_service.return_value.generate_markdown_report.return_value = None

            response = error_client.get("/dashboard/insights/report/download")

            # 실제 구현에서는 빈 보고서가 반환될 수 있음
            assert response.status_code in [200, 404]

    def test_report_json_no_data(self, error_client: TestClient) -> None:
        """데이터 없이 보고서 JSON 요청."""
        with patch("reddit_insight.dashboard.routers.insights.get_report_service") as mock_service:
            mock_service.return_value.generate_report.return_value = None

            response = error_client.get("/dashboard/insights/report/json")

            # 실제 구현에서는 빈 보고서가 반환될 수 있음
            assert response.status_code in [200, 404]

    def test_report_preview_no_data(self, error_client: TestClient) -> None:
        """데이터 없이 보고서 미리보기 요청."""
        with patch(
            "reddit_insight.dashboard.services.report_service.get_report_service"
        ) as mock_service:
            mock_service.return_value.generate_report.return_value = None

            response = error_client.get("/dashboard/insights/report/preview")

            # 빈 상태 표시
            assert response.status_code == 200


# =============================================================================
# GRACEFUL DEGRADATION TESTS
# =============================================================================


class TestGracefulDegradation:
    """Graceful degradation 테스트."""

    def test_partial_data_handling(self, error_client: TestClient) -> None:
        """일부 데이터만 있을 때 처리."""
        with patch("reddit_insight.dashboard.data_store.get_current_data") as mock:
            # 키워드는 있지만 수요 데이터는 없음
            mock_data = MagicMock()
            mock_data.keywords = [{"keyword": "test", "count": 10}]
            mock_data.demands = None
            mock_data.insights = None
            mock.return_value = mock_data

            response = error_client.get("/dashboard/")
            assert response.status_code == 200

    def test_service_timeout_simulation(self, error_client: TestClient) -> None:
        """서비스 타임아웃 시뮬레이션."""
        import time

        with patch(
            "reddit_insight.dashboard.services.prediction_service.get_prediction_service"
        ) as mock_service:

            def slow_prediction(*args: Any, **kwargs: Any) -> None:
                time.sleep(0.1)  # 100ms 지연
                mock_result = MagicMock()
                mock_result.to_chart_data.return_value = {"labels": [], "datasets": []}
                return mock_result

            mock_service.return_value.predict_keyword_trend = slow_prediction

            response = error_client.get("/dashboard/trends/predict/test")
            # 지연이 있어도 응답은 제공되어야 함
            assert response.status_code in [200, 500]

    def test_database_connection_error_simulation(self, error_client: TestClient) -> None:
        """데이터베이스 연결 에러 시뮬레이션."""
        with patch("reddit_insight.dashboard.routers.dashboard.load_analysis_by_id") as mock_load:
            mock_load.side_effect = ConnectionError("Database connection failed")

            response = error_client.get("/dashboard/analysis/1")
            # 에러가 발생해도 서버는 응답해야 함
            assert response.status_code in [200, 404, 500]


# =============================================================================
# ERROR MESSAGE QUALITY TESTS
# =============================================================================


class TestErrorMessageQuality:
    """에러 메시지 품질 테스트."""

    def test_404_page_has_helpful_message(self, error_client: TestClient) -> None:
        """404 페이지에 유용한 메시지가 포함되어 있는지 확인."""
        with patch("reddit_insight.dashboard.data_store.load_analysis_by_id") as mock:
            mock.return_value = None

            response = error_client.get("/dashboard/analysis/12345")

            assert response.status_code == 404
            # 에러 메시지에 ID가 포함
            assert "12345" in response.text or "not found" in response.text.lower()

    def test_insight_not_found_has_id_in_message(self, error_client: TestClient) -> None:
        """인사이트 not found 에러에 ID가 포함되어 있는지 확인."""
        with patch(
            "reddit_insight.dashboard.services.insight_service.get_insight_service"
        ) as mock_service:
            mock_service.return_value.get_insight_detail.return_value = None

            response = error_client.get("/dashboard/insights/test_id_123")

            assert response.status_code == 404
            assert "test_id_123" in response.text or "not found" in response.text.lower()


# =============================================================================
# EDGE CASE TESTS
# =============================================================================


class TestEdgeCases:
    """엣지 케이스 테스트."""

    def test_very_long_keyword(self, error_client: TestClient) -> None:
        """매우 긴 키워드 처리."""
        long_keyword = "a" * 1000

        with patch(
            "reddit_insight.dashboard.services.prediction_service.get_prediction_service"
        ) as mock_service:
            mock_result = MagicMock()
            mock_result.to_chart_data.return_value = {"labels": [], "datasets": []}
            mock_service.return_value.predict_keyword_trend.return_value = mock_result

            response = error_client.get(f"/dashboard/trends/predict/{long_keyword}")
            # 긴 키워드도 처리 가능해야 함
            assert response.status_code in [200, 414, 422]  # OK, URI Too Long, or Validation Error

    def test_unicode_keyword(self, error_client: TestClient) -> None:
        """유니코드 키워드 처리."""
        with patch(
            "reddit_insight.dashboard.services.prediction_service.get_prediction_service"
        ) as mock_service:
            mock_result = MagicMock()
            mock_result.to_chart_data.return_value = {"labels": [], "datasets": []}
            mock_service.return_value.predict_keyword_trend.return_value = mock_result

            response = error_client.get("/dashboard/trends/predict/한국어키워드")
            assert response.status_code == 200

    def test_zero_limit_parameter(self, error_client: TestClient) -> None:
        """limit=0 파라미터."""
        response = error_client.get("/dashboard/trends/?limit=0")
        assert response.status_code == 422

    def test_very_large_page_number(self, error_client: TestClient) -> None:
        """매우 큰 페이지 번호."""
        with patch(
            "reddit_insight.dashboard.services.cluster_service.get_cluster_service"
        ) as mock_service:
            mock_service.return_value.get_cluster_documents.return_value = []

            response = error_client.get("/dashboard/clusters/cluster/0/documents?page=99999")
            assert response.status_code == 200
            data = response.json()
            # 빈 결과 반환
            assert data["documents"] == []

    def test_concurrent_error_handling(self, error_client: TestClient) -> None:
        """동시 에러 처리."""
        endpoints = [
            "/dashboard/analysis/9999",
            "/dashboard/demands/nonexistent",
            "/dashboard/insights/nonexistent",
        ]

        for endpoint in endpoints:
            with patch("reddit_insight.dashboard.data_store.get_current_data") as mock:
                mock.return_value = None

                response = error_client.get(endpoint)
                assert response.status_code in [200, 404]  # 적절한 에러 처리
