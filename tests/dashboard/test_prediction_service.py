"""PredictionService 단위 테스트.

TrendPredictor ML 모듈을 래핑하는 예측 서비스의 동작을 검증한다.
"""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest

from reddit_insight.dashboard.services.prediction_service import (
    PredictionService,
    PredictionView,
    get_prediction_service,
)
from reddit_insight.dashboard.trend_service import TimelinePoint


# =============================================================================
# TEST FIXTURES
# =============================================================================


@pytest.fixture
def mock_timeline() -> list[TimelinePoint]:
    """테스트용 타임라인 데이터를 생성한다."""
    today = date.today()
    return [
        TimelinePoint(date=today - timedelta(days=i), count=100 + i * 5)
        for i in range(14, -1, -1)  # 15일치 데이터
    ]


@pytest.fixture
def mock_trend_service(mock_timeline: list[TimelinePoint]):
    """Mock TrendService를 생성한다."""
    service = MagicMock()
    service.get_keyword_timeline.return_value = mock_timeline
    service.get_top_keywords.return_value = [
        MagicMock(keyword="python"),
        MagicMock(keyword="javascript"),
    ]
    return service


@pytest.fixture
def prediction_service(mock_trend_service) -> PredictionService:
    """테스트용 PredictionService를 생성한다."""
    return PredictionService(trend_service=mock_trend_service)


# =============================================================================
# PREDICTION VIEW TESTS
# =============================================================================


class TestPredictionView:
    """PredictionView 데이터 클래스 테스트."""

    def test_basic_properties(self):
        """기본 속성이 올바르게 작동한다."""
        # Given
        view = PredictionView(
            keyword="test",
            historical_dates=["2024-01-01", "2024-01-02"],
            historical_values=[100.0, 110.0],
            forecast_dates=["2024-01-03", "2024-01-04"],
            forecast_values=[120.0, 130.0],
            confidence_lower=[115.0, 120.0],
            confidence_upper=[125.0, 140.0],
            model_name="TestModel",
            metrics={"MAE": 5.0, "RMSE": 6.0, "MAPE": 3.5},
            confidence_level=0.95,
        )

        # Then
        assert view.mae == 5.0
        assert view.rmse == 6.0
        assert view.mape == 3.5
        assert view.confidence_percent == 95

    def test_to_chart_data_structure(self):
        """to_chart_data()가 올바른 구조의 데이터를 반환한다."""
        # Given
        view = PredictionView(
            keyword="test",
            historical_dates=["2024-01-01", "2024-01-02"],
            historical_values=[100.0, 110.0],
            forecast_dates=["2024-01-03"],
            forecast_values=[120.0],
            confidence_lower=[115.0],
            confidence_upper=[125.0],
            model_name="TestModel",
            metrics={"MAE": 5.0, "RMSE": 6.0, "MAPE": 3.5},
            confidence_level=0.95,
        )

        # When
        chart_data = view.to_chart_data()

        # Then
        assert "labels" in chart_data
        assert "datasets" in chart_data
        assert "metadata" in chart_data
        assert len(chart_data["labels"]) == 3  # 2 historical + 1 forecast
        assert len(chart_data["datasets"]) == 4  # historical, forecast, lower, upper

    def test_to_chart_data_metadata(self):
        """to_chart_data()가 올바른 메타데이터를 포함한다."""
        # Given
        view = PredictionView(
            keyword="python",
            historical_dates=["2024-01-01"],
            historical_values=[100.0],
            forecast_dates=["2024-01-02"],
            forecast_values=[110.0],
            confidence_lower=[105.0],
            confidence_upper=[115.0],
            model_name="SimpleExponentialSmoothing",
            metrics={"MAE": 5.0, "RMSE": 6.0, "MAPE": 3.5},
            confidence_level=0.95,
        )

        # When
        chart_data = view.to_chart_data()

        # Then
        metadata = chart_data["metadata"]
        assert metadata["keyword"] == "python"
        assert metadata["model"] == "SimpleExponentialSmoothing"
        assert metadata["confidence_level"] == 95
        assert metadata["metrics"]["MAE"] == 5.0


# =============================================================================
# PREDICTION SERVICE TESTS
# =============================================================================


class TestPredictionService:
    """PredictionService 테스트."""

    def test_predict_keyword_trend_returns_prediction_view(
        self, prediction_service: PredictionService
    ):
        """predict_keyword_trend()가 PredictionView를 반환한다."""
        # When
        result = prediction_service.predict_keyword_trend("test_keyword")

        # Then
        assert isinstance(result, PredictionView)
        assert result.keyword == "test_keyword"
        assert len(result.historical_dates) > 0
        assert len(result.forecast_dates) > 0

    def test_predict_keyword_trend_forecast_days_parameter(
        self, prediction_service: PredictionService
    ):
        """forecast_days 파라미터가 예측 기간을 결정한다."""
        # When
        result_7 = prediction_service.predict_keyword_trend("test", forecast_days=7)
        result_14 = prediction_service.predict_keyword_trend("test", forecast_days=14)

        # Then
        assert len(result_7.forecast_dates) == 7
        assert len(result_14.forecast_dates) == 14

    def test_predict_keyword_trend_with_insufficient_data(
        self, mock_trend_service
    ):
        """데이터가 부족할 때 fallback 예측을 반환한다."""
        # Given: 5일치 데이터만 제공
        short_timeline = [
            TimelinePoint(date=date.today() - timedelta(days=i), count=100)
            for i in range(5)
        ]
        mock_trend_service.get_keyword_timeline.return_value = short_timeline
        service = PredictionService(trend_service=mock_trend_service)

        # When
        result = service.predict_keyword_trend("test_keyword")

        # Then
        assert isinstance(result, PredictionView)
        assert "Fallback" in result.model_name or "MovingAverage" in result.model_name

    def test_predict_keyword_trend_confidence_bounds(
        self, prediction_service: PredictionService
    ):
        """신뢰구간 경계가 유효하다."""
        # When
        result = prediction_service.predict_keyword_trend("test")

        # Then
        for i, forecast_val in enumerate(result.forecast_values):
            lower = result.confidence_lower[i]
            upper = result.confidence_upper[i]
            assert lower <= forecast_val <= upper

    def test_get_available_keywords(self, prediction_service: PredictionService):
        """get_available_keywords()가 키워드 목록을 반환한다."""
        # When
        keywords = prediction_service.get_available_keywords()

        # Then
        assert isinstance(keywords, list)
        assert len(keywords) == 2
        assert "python" in keywords
        assert "javascript" in keywords


# =============================================================================
# SINGLETON TESTS
# =============================================================================


class TestPredictionServiceSingleton:
    """PredictionService 싱글톤 테스트."""

    def test_get_prediction_service_returns_singleton(self):
        """get_prediction_service()가 싱글톤 인스턴스를 반환한다."""
        # When
        service1 = get_prediction_service()
        service2 = get_prediction_service()

        # Then
        assert service1 is service2


# =============================================================================
# EDGE CASE TESTS
# =============================================================================


class TestPredictionServiceEdgeCases:
    """PredictionService 엣지 케이스 테스트."""

    def test_empty_timeline(self):
        """빈 타임라인을 처리한다."""
        # Given
        mock_service = MagicMock()
        mock_service.get_keyword_timeline.return_value = []
        service = PredictionService(trend_service=mock_service)

        # When
        result = service.predict_keyword_trend("test")

        # Then
        assert isinstance(result, PredictionView)
        # 빈 데이터에서도 예측 구조가 유효해야 함
        assert result.keyword == "test"

    def test_forecast_days_boundary_values(self, prediction_service: PredictionService):
        """예측 기간 경계값을 처리한다."""
        # When: 최소값 테스트
        result_min = prediction_service.predict_keyword_trend("test", forecast_days=1)
        assert len(result_min.forecast_dates) == 1

        # When: 최대값 테스트
        result_max = prediction_service.predict_keyword_trend("test", forecast_days=14)
        assert len(result_max.forecast_dates) == 14

        # When: 범위 초과 테스트 (자동으로 14로 제한)
        result_over = prediction_service.predict_keyword_trend("test", forecast_days=100)
        assert len(result_over.forecast_dates) == 14

    def test_special_characters_in_keyword(self, prediction_service: PredictionService):
        """특수 문자가 포함된 키워드를 처리한다."""
        # When
        result = prediction_service.predict_keyword_trend("c++")

        # Then
        assert result.keyword == "c++"

    def test_confidence_level_boundary(self, prediction_service: PredictionService):
        """신뢰수준 경계값을 처리한다."""
        # When: 유효 범위 내
        result_normal = prediction_service.predict_keyword_trend(
            "test", confidence_level=0.95
        )
        assert result_normal.confidence_level == 0.95

        # When: 최소값 미만 (0.5로 제한)
        result_low = prediction_service.predict_keyword_trend(
            "test", confidence_level=0.1
        )
        assert result_low.confidence_level >= 0.5

        # When: 최대값 초과 (0.99로 제한)
        result_high = prediction_service.predict_keyword_trend(
            "test", confidence_level=1.0
        )
        assert result_high.confidence_level <= 0.99
