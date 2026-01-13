"""
Tests for the AnomalyDetector class.

Tests cover all three anomaly detection methods (z-score, IQR, Isolation Forest),
automatic method selection, and integration with RisingKeywordDetector.
"""

from datetime import UTC, datetime, timedelta

import pytest

from reddit_insight.analysis.ml.anomaly_detector import (
    AnomalyDetector,
    AnomalyDetectorConfig,
    detect_anomalies_simple,
)
from reddit_insight.analysis.ml.models import AnomalyPoint, AnomalyResult
from reddit_insight.analysis.time_series import TimeGranularity, TimePoint, TimeSeries


# Test fixtures
@pytest.fixture
def normal_time_series() -> TimeSeries:
    """Create a time series with no anomalies."""
    now = datetime.now(UTC)
    points = [
        TimePoint(timestamp=now - timedelta(hours=i), value=10.0 + (i % 3))
        for i in range(20, 0, -1)
    ]
    return TimeSeries(
        keyword="normal",
        granularity=TimeGranularity.HOUR,
        points=points,
    )


@pytest.fixture
def anomaly_time_series() -> TimeSeries:
    """Create a time series with a clear anomaly."""
    now = datetime.now(UTC)
    values = [10.0] * 20
    values[10] = 200.0  # Clear anomaly
    points = [
        TimePoint(timestamp=now - timedelta(hours=20 - i), value=val)
        for i, val in enumerate(values)
    ]
    return TimeSeries(
        keyword="anomaly",
        granularity=TimeGranularity.HOUR,
        points=points,
    )


@pytest.fixture
def small_time_series() -> TimeSeries:
    """Create a small time series (< 30 points)."""
    now = datetime.now(UTC)
    values = [10.0, 11.0, 10.0, 12.0, 100.0, 10.0, 11.0, 10.0, 12.0, 10.0]
    points = [
        TimePoint(timestamp=now - timedelta(hours=len(values) - i), value=val)
        for i, val in enumerate(values)
    ]
    return TimeSeries(
        keyword="small",
        granularity=TimeGranularity.HOUR,
        points=points,
    )


@pytest.fixture
def medium_time_series() -> TimeSeries:
    """Create a medium time series (30-100 points)."""
    now = datetime.now(UTC)
    values = [10.0 + (i % 5) for i in range(50)]
    values[25] = 200.0  # Clear anomaly
    points = [
        TimePoint(timestamp=now - timedelta(hours=len(values) - i), value=val)
        for i, val in enumerate(values)
    ]
    return TimeSeries(
        keyword="medium",
        granularity=TimeGranularity.HOUR,
        points=points,
    )


@pytest.fixture
def large_time_series() -> TimeSeries:
    """Create a large time series (> 100 points)."""
    now = datetime.now(UTC)
    values = [10.0 + (i % 5) for i in range(150)]
    values[75] = 200.0  # Clear anomaly
    points = [
        TimePoint(timestamp=now - timedelta(hours=len(values) - i), value=val)
        for i, val in enumerate(values)
    ]
    return TimeSeries(
        keyword="large",
        granularity=TimeGranularity.HOUR,
        points=points,
    )


class TestAnomalyDetectorConfig:
    """Test suite for AnomalyDetectorConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = AnomalyDetectorConfig()
        assert config.method == "auto"
        assert config.threshold == 3.0
        assert config.contamination == 0.05
        assert config.window_size == 0
        assert config.min_data_points == 10
        assert config.iqr_multiplier == 1.5

    def test_custom_config(self):
        """Test custom configuration."""
        config = AnomalyDetectorConfig(
            method="zscore",
            threshold=2.5,
            min_data_points=5,
        )
        assert config.method == "zscore"
        assert config.threshold == 2.5
        assert config.min_data_points == 5


class TestAnomalyDetectorZscore:
    """Test suite for Z-score anomaly detection."""

    def test_detect_zscore_basic(self, anomaly_time_series):
        """Test basic z-score anomaly detection."""
        config = AnomalyDetectorConfig(method="zscore", threshold=2.5)
        detector = AnomalyDetector(config)
        result = detector.detect(anomaly_time_series)

        assert result.method == "zscore"
        assert result.total_points == 20
        assert result.anomaly_count >= 1

        # Check the anomaly was found
        anomaly_values = [a.value for a in result.detected_anomalies]
        assert 200.0 in anomaly_values

    def test_zscore_no_anomalies_in_normal_data(self, normal_time_series):
        """Test that z-score finds no anomalies in normal data."""
        config = AnomalyDetectorConfig(method="zscore", threshold=3.0)
        detector = AnomalyDetector(config)
        result = detector.detect(normal_time_series)

        assert result.method == "zscore"
        assert result.anomaly_count == 0
        assert len(result.detected_anomalies) == 0

    def test_zscore_threshold_sensitivity(self, anomaly_time_series):
        """Test that lower threshold detects more anomalies."""
        # High threshold - might not detect
        high_config = AnomalyDetectorConfig(method="zscore", threshold=5.0)
        high_detector = AnomalyDetector(high_config)
        high_result = high_detector.detect(anomaly_time_series)

        # Low threshold - should detect
        low_config = AnomalyDetectorConfig(method="zscore", threshold=2.0)
        low_detector = AnomalyDetector(low_config)
        low_result = low_detector.detect(anomaly_time_series)

        assert low_result.anomaly_count >= high_result.anomaly_count


class TestAnomalyDetectorIQR:
    """Test suite for IQR anomaly detection."""

    def test_detect_iqr_basic(self, anomaly_time_series):
        """Test basic IQR anomaly detection."""
        config = AnomalyDetectorConfig(method="iqr")
        detector = AnomalyDetector(config)
        result = detector.detect(anomaly_time_series)

        assert result.method == "iqr"
        assert result.total_points == 20
        assert result.anomaly_count >= 1

        # Check the anomaly was found
        anomaly_values = [a.value for a in result.detected_anomalies]
        assert 200.0 in anomaly_values

    def test_iqr_no_anomalies_in_normal_data(self, normal_time_series):
        """Test that IQR finds no anomalies in normal data."""
        config = AnomalyDetectorConfig(method="iqr")
        detector = AnomalyDetector(config)
        result = detector.detect(normal_time_series)

        assert result.method == "iqr"
        assert result.anomaly_count == 0

    def test_iqr_multiplier_sensitivity(self, anomaly_time_series):
        """Test that lower IQR multiplier detects more anomalies."""
        # High multiplier - less sensitive
        high_config = AnomalyDetectorConfig(method="iqr", iqr_multiplier=3.0)
        high_detector = AnomalyDetector(high_config)
        high_result = high_detector.detect(anomaly_time_series)

        # Low multiplier - more sensitive
        low_config = AnomalyDetectorConfig(method="iqr", iqr_multiplier=1.0)
        low_detector = AnomalyDetector(low_config)
        low_result = low_detector.detect(anomaly_time_series)

        assert low_result.anomaly_count >= high_result.anomaly_count


class TestAnomalyDetectorIsolationForest:
    """Test suite for Isolation Forest anomaly detection."""

    def test_detect_isolation_forest_basic(self, large_time_series):
        """Test basic Isolation Forest anomaly detection."""
        config = AnomalyDetectorConfig(method="isolation_forest", contamination=0.05)
        detector = AnomalyDetector(config)
        result = detector.detect(large_time_series)

        assert result.method == "isolation_forest"
        assert result.total_points == 150
        # Isolation Forest should find approximately 5% anomalies
        assert result.anomaly_count > 0

        # The clear anomaly at value 200 should be detected
        anomaly_values = [a.value for a in result.detected_anomalies]
        assert 200.0 in anomaly_values

    def test_isolation_forest_contamination(self, large_time_series):
        """Test that contamination affects number of anomalies."""
        # Low contamination
        low_config = AnomalyDetectorConfig(
            method="isolation_forest", contamination=0.01
        )
        low_detector = AnomalyDetector(low_config)
        low_result = low_detector.detect(large_time_series)

        # High contamination
        high_config = AnomalyDetectorConfig(
            method="isolation_forest", contamination=0.1
        )
        high_detector = AnomalyDetector(high_config)
        high_result = high_detector.detect(large_time_series)

        assert high_result.anomaly_count >= low_result.anomaly_count


class TestAutoMethodSelection:
    """Test suite for automatic method selection."""

    def test_auto_selects_zscore_for_small_data(self, small_time_series):
        """Test that auto selects z-score for small datasets (<30)."""
        config = AnomalyDetectorConfig(method="auto", threshold=2.5)
        detector = AnomalyDetector(config)
        result = detector.detect(small_time_series)

        assert result.method == "zscore"

    def test_auto_selects_iqr_for_medium_data(self, medium_time_series):
        """Test that auto selects IQR for medium datasets (30-100)."""
        config = AnomalyDetectorConfig(method="auto")
        detector = AnomalyDetector(config)
        result = detector.detect(medium_time_series)

        assert result.method == "iqr"

    def test_auto_selects_isolation_forest_for_large_data(self, large_time_series):
        """Test that auto selects Isolation Forest for large datasets (>100)."""
        config = AnomalyDetectorConfig(method="auto")
        detector = AnomalyDetector(config)
        result = detector.detect(large_time_series)

        assert result.method == "isolation_forest"


class TestAnomalyResultStructure:
    """Test suite for AnomalyResult structure validation."""

    def test_anomaly_result_fields(self, anomaly_time_series):
        """Test that AnomalyResult has all required fields."""
        config = AnomalyDetectorConfig(method="zscore", threshold=2.5)
        detector = AnomalyDetector(config)
        result = detector.detect(anomaly_time_series)

        assert isinstance(result, AnomalyResult)
        assert hasattr(result, "anomalies")
        assert hasattr(result, "threshold")
        assert hasattr(result, "method")
        assert hasattr(result, "total_points")
        assert hasattr(result, "anomaly_count")
        assert hasattr(result, "contamination")
        assert hasattr(result, "parameters")

    def test_anomaly_point_fields(self, anomaly_time_series):
        """Test that AnomalyPoint has all required fields."""
        config = AnomalyDetectorConfig(method="zscore", threshold=2.5)
        detector = AnomalyDetector(config)
        result = detector.detect(anomaly_time_series)

        assert len(result.anomalies) > 0
        point = result.anomalies[0]

        assert isinstance(point, AnomalyPoint)
        assert hasattr(point, "timestamp")
        assert hasattr(point, "value")
        assert hasattr(point, "anomaly_score")
        assert hasattr(point, "is_anomaly")
        assert hasattr(point, "expected_value")
        assert hasattr(point, "deviation")

    def test_anomaly_rate_calculation(self, anomaly_time_series):
        """Test that anomaly rate is correctly calculated."""
        config = AnomalyDetectorConfig(method="zscore", threshold=2.5)
        detector = AnomalyDetector(config)
        result = detector.detect(anomaly_time_series)

        expected_rate = result.anomaly_count / result.total_points
        assert result.anomaly_rate == expected_rate

    def test_detected_anomalies_property(self, anomaly_time_series):
        """Test that detected_anomalies returns only anomalies."""
        config = AnomalyDetectorConfig(method="zscore", threshold=2.5)
        detector = AnomalyDetector(config)
        result = detector.detect(anomaly_time_series)

        detected = result.detected_anomalies
        assert all(a.is_anomaly for a in detected)
        assert len(detected) == result.anomaly_count

    def test_to_dict_serialization(self, anomaly_time_series):
        """Test that to_dict produces valid dictionary."""
        config = AnomalyDetectorConfig(method="zscore", threshold=2.5)
        detector = AnomalyDetector(config)
        result = detector.detect(anomaly_time_series)

        data = result.to_dict()
        assert isinstance(data, dict)
        assert "anomalies" in data
        assert "method" in data
        assert "total_points" in data
        assert "anomaly_count" in data
        assert "anomaly_rate" in data


class TestEdgeCases:
    """Test suite for edge cases."""

    def test_insufficient_data(self):
        """Test handling of insufficient data points."""
        now = datetime.now(UTC)
        points = [
            TimePoint(timestamp=now - timedelta(hours=i), value=10.0)
            for i in range(5)
        ]
        ts = TimeSeries(
            keyword="tiny",
            granularity=TimeGranularity.HOUR,
            points=points,
        )

        config = AnomalyDetectorConfig(min_data_points=10)
        detector = AnomalyDetector(config)
        result = detector.detect(ts)

        assert result.method == "insufficient_data"
        assert result.anomaly_count == 0
        assert len(result.anomalies) == 0

    def test_constant_values(self):
        """Test handling of constant values (zero variance)."""
        now = datetime.now(UTC)
        points = [
            TimePoint(timestamp=now - timedelta(hours=i), value=10.0)
            for i in range(20)
        ]
        ts = TimeSeries(
            keyword="constant",
            granularity=TimeGranularity.HOUR,
            points=points,
        )

        config = AnomalyDetectorConfig(method="zscore")
        detector = AnomalyDetector(config)
        result = detector.detect(ts)

        # Zero variance - no anomalies should be detected
        assert result.anomaly_count == 0


class TestSimpleFunction:
    """Test suite for detect_anomalies_simple function."""

    def test_basic_detection(self):
        """Test basic anomaly detection with simple function."""
        values = [10.0, 10.0, 10.0, 10.0, 100.0, 10.0, 10.0, 10.0, 10.0, 10.0]
        anomalies = detect_anomalies_simple(values, threshold=2.5)

        assert len(anomalies) >= 1
        # Check format: (index, value, score)
        idx, val, score = anomalies[0]
        assert isinstance(idx, int)
        assert isinstance(val, (int, float))
        assert isinstance(score, float)
        assert val == 100.0

    def test_no_anomalies_in_normal_data(self):
        """Test that no anomalies are found in normal data."""
        values = [10, 11, 10, 11, 10, 11, 10, 11, 10, 11]
        anomalies = detect_anomalies_simple(values)

        assert len(anomalies) == 0

    def test_custom_timestamps(self):
        """Test detection with custom timestamps."""
        now = datetime.now(UTC)
        timestamps = [now - timedelta(hours=i) for i in range(10, 0, -1)]
        values = [10, 10, 10, 10, 100, 10, 10, 10, 10, 10]

        anomalies = detect_anomalies_simple(values, timestamps=timestamps, threshold=2.5)
        assert len(anomalies) >= 1


class TestAnalyzeMethod:
    """Test suite for the analyze() method (MLAnalyzerBase interface)."""

    def test_analyze_returns_analysis_result(self, anomaly_time_series):
        """Test that analyze() returns proper AnalysisResult."""
        from reddit_insight.analysis.ml.base import AnalysisResult

        config = AnomalyDetectorConfig(method="zscore", threshold=2.5)
        detector = AnomalyDetector(config)
        result = detector.analyze(anomaly_time_series)

        assert isinstance(result, AnalysisResult)
        assert result.result_type == "anomaly"
        assert result.success is True
        assert 0.0 <= result.confidence <= 1.0

    def test_analyze_metadata(self, anomaly_time_series):
        """Test that analyze() includes proper metadata."""
        config = AnomalyDetectorConfig(method="zscore", threshold=2.5)
        detector = AnomalyDetector(config)
        result = detector.analyze(anomaly_time_series)

        assert result.metadata.data_size == 20
        assert result.metadata.processing_time_ms >= 0
        assert result.metadata.analyzer_name == "AnomalyDetector"
