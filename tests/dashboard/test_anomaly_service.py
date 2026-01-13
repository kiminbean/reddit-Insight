"""AnomalyService 단위 테스트.

AnomalyDetector ML 모듈을 래핑하는 이상 탐지 서비스의 동작을 검증한다.
"""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import MagicMock

import pytest

from reddit_insight.dashboard.services.anomaly_service import (
    AnomalyPointView,
    AnomalyService,
    AnomalyView,
    get_anomaly_service,
)
from reddit_insight.dashboard.trend_service import TimelinePoint


# =============================================================================
# TEST FIXTURES
# =============================================================================


@pytest.fixture
def mock_timeline() -> list[TimelinePoint]:
    """테스트용 타임라인 데이터를 생성한다."""
    today = date.today()
    # 정상 데이터 + 이상 포인트 (5번째 위치에 급증)
    counts = [100, 105, 102, 98, 500, 103, 101, 99, 104, 100, 102, 98, 101, 103, 100]
    return [
        TimelinePoint(date=today - timedelta(days=14 - i), count=counts[i])
        for i in range(15)
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
def anomaly_service(mock_trend_service) -> AnomalyService:
    """테스트용 AnomalyService를 생성한다."""
    return AnomalyService(trend_service=mock_trend_service)


# =============================================================================
# ANOMALY POINT VIEW TESTS
# =============================================================================


class TestAnomalyPointView:
    """AnomalyPointView 데이터 클래스 테스트."""

    def test_basic_creation(self):
        """기본 생성이 올바르게 작동한다."""
        # Given & When
        point = AnomalyPointView(
            date="2024-01-15",
            value=500.0,
            score=5.2,
            is_anomaly=True,
            expected_value=100.0,
            deviation=400.0,
        )

        # Then
        assert point.date == "2024-01-15"
        assert point.value == 500.0
        assert point.score == 5.2
        assert point.is_anomaly is True
        assert point.expected_value == 100.0
        assert point.deviation == 400.0


# =============================================================================
# ANOMALY VIEW TESTS
# =============================================================================


class TestAnomalyView:
    """AnomalyView 데이터 클래스 테스트."""

    def test_basic_properties(self):
        """기본 속성이 올바르게 작동한다."""
        # Given
        view = AnomalyView(
            keyword="test",
            dates=["2024-01-01", "2024-01-02", "2024-01-03"],
            values=[100.0, 500.0, 105.0],
            is_anomaly=[False, True, False],
            anomaly_points=[
                AnomalyPointView(
                    date="2024-01-02",
                    value=500.0,
                    score=5.2,
                    is_anomaly=True,
                )
            ],
            anomaly_count=1,
            total_points=3,
            method="zscore",
            threshold=3.0,
        )

        # Then
        assert view.anomaly_rate == 1 / 3
        assert view.anomaly_rate_percent == pytest.approx(33.3, rel=0.1)

    def test_to_chart_data_structure(self):
        """to_chart_data()가 올바른 구조의 데이터를 반환한다."""
        # Given
        view = AnomalyView(
            keyword="test",
            dates=["2024-01-01", "2024-01-02"],
            values=[100.0, 500.0],
            is_anomaly=[False, True],
            anomaly_points=[
                AnomalyPointView(
                    date="2024-01-02",
                    value=500.0,
                    score=5.2,
                    is_anomaly=True,
                )
            ],
            anomaly_count=1,
            total_points=2,
            method="zscore",
            threshold=3.0,
        )

        # When
        chart_data = view.to_chart_data()

        # Then
        assert "labels" in chart_data
        assert "datasets" in chart_data
        assert "metadata" in chart_data
        assert len(chart_data["labels"]) == 2
        assert len(chart_data["datasets"]) == 2  # normal, anomaly

    def test_to_chart_data_metadata(self):
        """to_chart_data()가 올바른 메타데이터를 포함한다."""
        # Given
        view = AnomalyView(
            keyword="python",
            dates=["2024-01-01"],
            values=[100.0],
            is_anomaly=[False],
            anomaly_points=[],
            anomaly_count=0,
            total_points=1,
            method="auto",
            threshold=3.0,
        )

        # When
        chart_data = view.to_chart_data()

        # Then
        metadata = chart_data["metadata"]
        assert metadata["keyword"] == "python"
        assert metadata["method"] == "auto"
        assert metadata["threshold"] == 3.0
        assert metadata["anomaly_count"] == 0
        assert metadata["total_points"] == 1

    def test_anomaly_data_separation(self):
        """이상 포인트와 정상 포인트가 올바르게 분리된다."""
        # Given
        view = AnomalyView(
            keyword="test",
            dates=["d1", "d2", "d3"],
            values=[100.0, 500.0, 105.0],
            is_anomaly=[False, True, False],
            anomaly_points=[],
            anomaly_count=1,
            total_points=3,
        )

        # When
        chart_data = view.to_chart_data()

        # Then
        normal_dataset = chart_data["datasets"][0]
        anomaly_dataset = chart_data["datasets"][1]

        # 정상 데이터: 이상 포인트는 None
        assert normal_dataset["data"][0] == 100.0
        assert normal_dataset["data"][1] is None
        assert normal_dataset["data"][2] == 105.0

        # 이상 데이터: 정상 포인트는 None
        assert anomaly_dataset["data"][0] is None
        assert anomaly_dataset["data"][1] == 500.0
        assert anomaly_dataset["data"][2] is None


# =============================================================================
# ANOMALY SERVICE TESTS
# =============================================================================


class TestAnomalyService:
    """AnomalyService 테스트."""

    def test_detect_anomalies_returns_anomaly_view(
        self, anomaly_service: AnomalyService
    ):
        """detect_anomalies()가 AnomalyView를 반환한다."""
        # When
        result = anomaly_service.detect_anomalies("test_keyword")

        # Then
        assert isinstance(result, AnomalyView)
        assert result.keyword == "test_keyword"
        assert len(result.dates) > 0
        assert len(result.values) > 0

    def test_detect_anomalies_days_parameter(
        self, anomaly_service: AnomalyService, mock_trend_service
    ):
        """days 파라미터가 분석 기간을 결정한다."""
        # When
        anomaly_service.detect_anomalies("test", days=30)

        # Then
        mock_trend_service.get_keyword_timeline.assert_called_with(
            keyword="test",
            days=30,
        )

    def test_detect_anomalies_finds_outliers(
        self, anomaly_service: AnomalyService
    ):
        """이상 포인트를 올바르게 탐지한다."""
        # When
        result = anomaly_service.detect_anomalies("test")

        # Then
        # mock_timeline에서 5번째 값(500)은 명백한 이상치
        assert result.anomaly_count >= 1
        assert any(ap.value == 500.0 for ap in result.anomaly_points)

    def test_detect_anomalies_with_insufficient_data(self, mock_trend_service):
        """데이터가 부족할 때 빈 결과를 반환한다."""
        # Given: 5일치 데이터만 제공
        short_timeline = [
            TimelinePoint(date=date.today() - timedelta(days=i), count=100)
            for i in range(5)
        ]
        mock_trend_service.get_keyword_timeline.return_value = short_timeline
        service = AnomalyService(trend_service=mock_trend_service)

        # When
        result = service.detect_anomalies("test_keyword")

        # Then
        assert isinstance(result, AnomalyView)
        assert result.anomaly_count == 0

    def test_get_available_keywords(self, anomaly_service: AnomalyService):
        """get_available_keywords()가 키워드 목록을 반환한다."""
        # When
        keywords = anomaly_service.get_available_keywords()

        # Then
        assert isinstance(keywords, list)
        assert len(keywords) == 2
        assert "python" in keywords
        assert "javascript" in keywords


# =============================================================================
# SINGLETON TESTS
# =============================================================================


class TestAnomalyServiceSingleton:
    """AnomalyService 싱글톤 테스트."""

    def test_get_anomaly_service_returns_singleton(self):
        """get_anomaly_service()가 싱글톤 인스턴스를 반환한다."""
        # When
        service1 = get_anomaly_service()
        service2 = get_anomaly_service()

        # Then
        assert service1 is service2


# =============================================================================
# EDGE CASE TESTS
# =============================================================================


class TestAnomalyServiceEdgeCases:
    """AnomalyService 엣지 케이스 테스트."""

    def test_empty_timeline(self):
        """빈 타임라인을 처리한다."""
        # Given
        mock_service = MagicMock()
        mock_service.get_keyword_timeline.return_value = []
        service = AnomalyService(trend_service=mock_service)

        # When
        result = service.detect_anomalies("test")

        # Then
        assert isinstance(result, AnomalyView)
        assert result.keyword == "test"
        assert result.total_points == 0
        assert result.anomaly_count == 0

    def test_days_boundary_values(self, anomaly_service: AnomalyService, mock_trend_service):
        """분석 기간 경계값을 처리한다."""
        # When: 최소값 테스트 (7일로 제한)
        anomaly_service.detect_anomalies("test", days=1)
        call_args = mock_trend_service.get_keyword_timeline.call_args
        assert call_args.kwargs["days"] == 7

        # When: 최대값 테스트 (90일로 제한)
        anomaly_service.detect_anomalies("test", days=200)
        call_args = mock_trend_service.get_keyword_timeline.call_args
        assert call_args.kwargs["days"] == 90

    def test_threshold_boundary_values(self, anomaly_service: AnomalyService):
        """임계값 경계값을 처리한다."""
        # When: 정상 범위
        result_normal = anomaly_service.detect_anomalies("test", threshold=3.0)
        assert result_normal.threshold == 3.0

        # When: 최소값 미만
        result_low = anomaly_service.detect_anomalies("test", threshold=0.5)
        assert result_low.threshold >= 1.0

        # When: 최대값 초과
        result_high = anomaly_service.detect_anomalies("test", threshold=10.0)
        assert result_high.threshold <= 5.0

    def test_special_characters_in_keyword(self, anomaly_service: AnomalyService):
        """특수 문자가 포함된 키워드를 처리한다."""
        # When
        result = anomaly_service.detect_anomalies("c++")

        # Then
        assert result.keyword == "c++"

    def test_all_zero_values(self):
        """모든 값이 0인 경우를 처리한다."""
        # Given
        mock_service = MagicMock()
        mock_service.get_keyword_timeline.return_value = [
            TimelinePoint(date=date.today() - timedelta(days=i), count=0)
            for i in range(15)
        ]
        service = AnomalyService(trend_service=mock_service)

        # When
        result = service.detect_anomalies("test")

        # Then
        assert isinstance(result, AnomalyView)
        # 모든 값이 동일하면 이상치 없음
        assert result.anomaly_count == 0

    def test_constant_values(self):
        """모든 값이 동일한 경우를 처리한다."""
        # Given
        mock_service = MagicMock()
        mock_service.get_keyword_timeline.return_value = [
            TimelinePoint(date=date.today() - timedelta(days=i), count=100)
            for i in range(15)
        ]
        service = AnomalyService(trend_service=mock_service)

        # When
        result = service.detect_anomalies("test")

        # Then
        # 표준편차가 0이면 이상치가 없어야 함
        assert result.anomaly_count == 0


# =============================================================================
# DETECTION METHOD TESTS
# =============================================================================


class TestAnomalyDetectionMethods:
    """이상 탐지 방법 테스트."""

    def test_method_parameter_passed_correctly(
        self, anomaly_service: AnomalyService
    ):
        """method 파라미터가 올바르게 전달된다."""
        # When
        result_auto = anomaly_service.detect_anomalies("test", method="auto")
        result_zscore = anomaly_service.detect_anomalies("test", method="zscore")
        result_iqr = anomaly_service.detect_anomalies("test", method="iqr")

        # Then
        # 메서드가 결과에 반영되어야 함
        assert result_auto.method in ["zscore", "iqr", "isolation_forest", "auto"]
        assert result_zscore.method in ["zscore", "auto"]
        assert result_iqr.method in ["iqr", "auto"]


# =============================================================================
# CHART DATA FORMAT TESTS
# =============================================================================


class TestChartDataFormat:
    """Chart.js 데이터 형식 테스트."""

    def test_chart_data_has_correct_colors(self):
        """차트 데이터가 올바른 색상을 가진다."""
        # Given
        view = AnomalyView(
            keyword="test",
            dates=["2024-01-01"],
            values=[100.0],
            is_anomaly=[True],
            anomaly_points=[],
            anomaly_count=1,
            total_points=1,
        )

        # When
        chart_data = view.to_chart_data()

        # Then
        anomaly_dataset = chart_data["datasets"][1]  # Anomaly dataset
        assert "rgb(239, 68, 68)" in anomaly_dataset["borderColor"]  # Red color

    def test_chart_data_anomaly_points_larger_radius(self):
        """이상 포인트는 더 큰 반지름을 가진다."""
        # Given
        view = AnomalyView(
            keyword="test",
            dates=["2024-01-01"],
            values=[100.0],
            is_anomaly=[True],
            anomaly_points=[],
            anomaly_count=1,
            total_points=1,
        )

        # When
        chart_data = view.to_chart_data()

        # Then
        normal_dataset = chart_data["datasets"][0]
        anomaly_dataset = chart_data["datasets"][1]
        # 이상 포인트는 정상 포인트보다 큰 반지름을 가져야 함
        assert anomaly_dataset["pointRadius"] > normal_dataset["pointRadius"]
