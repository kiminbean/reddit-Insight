"""
Tests for TrendPredictor time series forecasting.

Tests cover:
- Basic prediction with sufficient data
- Prediction with minimal data (10-30 points)
- Handling of insufficient data
- PredictionResult structure validation
- Metrics calculation (MAE, RMSE, MAPE)
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from reddit_insight.analysis.ml.models import PredictionResult
from reddit_insight.analysis.ml.trend_predictor import (
    TrendPredictor,
    TrendPredictorConfig,
)
from reddit_insight.analysis.time_series import (
    TimeGranularity,
    TimePoint,
    TimeSeries,
)


@pytest.fixture
def sufficient_data_series() -> TimeSeries:
    """Time series with 30+ data points showing an upward trend."""
    base_time = datetime.now(UTC)
    points = []
    for i in range(40):
        # Simulating upward trend with some noise
        value = 100.0 + i * 2.0 + (i % 7) * 3.0
        timestamp = base_time - timedelta(days=40 - i)
        points.append(TimePoint(timestamp=timestamp, value=value))

    return TimeSeries(
        keyword="test_keyword",
        granularity=TimeGranularity.DAY,
        points=points,
    )


@pytest.fixture
def minimal_data_series() -> TimeSeries:
    """Time series with 10-30 data points (minimal for prediction)."""
    base_time = datetime.now(UTC)
    points = []
    for i in range(20):
        value = 50.0 + i * 1.5
        timestamp = base_time - timedelta(days=20 - i)
        points.append(TimePoint(timestamp=timestamp, value=value))

    return TimeSeries(
        keyword="minimal_keyword",
        granularity=TimeGranularity.DAY,
        points=points,
    )


@pytest.fixture
def insufficient_data_series() -> TimeSeries:
    """Time series with less than 10 data points."""
    base_time = datetime.now(UTC)
    points = [
        TimePoint(timestamp=base_time - timedelta(days=i), value=10.0 + i)
        for i in range(5, 0, -1)
    ]

    return TimeSeries(
        keyword="insufficient",
        granularity=TimeGranularity.DAY,
        points=points,
    )


@pytest.fixture
def seasonal_data_series() -> TimeSeries:
    """Time series with 60+ data points and weekly seasonality."""
    base_time = datetime.now(UTC)
    import math
    points = []
    for i in range(70):
        # Add weekly seasonality (period=7)
        seasonal = 20.0 * math.sin(2 * math.pi * i / 7)
        value = 100.0 + i * 0.5 + seasonal
        timestamp = base_time - timedelta(days=70 - i)
        points.append(TimePoint(timestamp=timestamp, value=value))

    return TimeSeries(
        keyword="seasonal_keyword",
        granularity=TimeGranularity.DAY,
        points=points,
    )


class TestTrendPredictorConfig:
    """Tests for TrendPredictorConfig."""

    def test_default_config(self):
        """Default configuration should have sensible values."""
        config = TrendPredictorConfig()

        assert config.forecast_periods == 7
        assert config.confidence_level == 0.95
        assert config.min_data_points == 10
        assert config.model_type == "auto"
        assert config.seasonal_period is None
        assert config.name == "TrendPredictor"
        assert config.version == "1.0.0"

    def test_custom_config(self):
        """Custom configuration should override defaults."""
        config = TrendPredictorConfig(
            forecast_periods=14,
            confidence_level=0.90,
            min_data_points=20,
            model_type="arima",
            seasonal_period=7,
        )

        assert config.forecast_periods == 14
        assert config.confidence_level == 0.90
        assert config.min_data_points == 20
        assert config.model_type == "arima"
        assert config.seasonal_period == 7


class TestTrendPredictor:
    """Tests for TrendPredictor."""

    def test_predict_with_sufficient_data(self, sufficient_data_series: TimeSeries):
        """Prediction should succeed with 30+ data points."""
        predictor = TrendPredictor(TrendPredictorConfig(forecast_periods=7))
        result = predictor.predict(sufficient_data_series)

        # Should return correct number of predictions
        assert len(result.values) == 7
        assert len(result.timestamps) == 7

        # Confidence intervals should exist
        assert len(result.lower_bound) == 7
        assert len(result.upper_bound) == 7

        # Confidence level should match config
        assert result.confidence_level == 0.95

        # Model name should be set
        assert result.model_name != "Unknown"

    def test_predict_with_minimal_data(self, minimal_data_series: TimeSeries):
        """Prediction should work with 10-30 data points using Simple ES."""
        predictor = TrendPredictor(TrendPredictorConfig(forecast_periods=5))
        result = predictor.predict(minimal_data_series)

        assert len(result.values) == 5
        # With minimal data, should use Simple Exponential Smoothing
        assert "SimpleExponentialSmoothing" in result.model_name or "Simple" in result.model_name

    def test_predict_insufficient_data(self, insufficient_data_series: TimeSeries):
        """Prediction should raise ValueError with less than min_data_points."""
        predictor = TrendPredictor(TrendPredictorConfig(min_data_points=10))

        with pytest.raises(ValueError) as exc_info:
            predictor.predict(insufficient_data_series)

        assert "Insufficient data" in str(exc_info.value)
        assert "minimum required" in str(exc_info.value)

    def test_prediction_result_structure(self, sufficient_data_series: TimeSeries):
        """PredictionResult should have correct structure."""
        predictor = TrendPredictor(TrendPredictorConfig(forecast_periods=7))
        result = predictor.predict(sufficient_data_series)

        # Validate type
        assert isinstance(result, PredictionResult)

        # All arrays should have same length
        n = len(result.values)
        assert len(result.timestamps) == n
        assert len(result.lower_bound) == n
        assert len(result.upper_bound) == n

        # Values should be floats
        assert all(isinstance(v, float) for v in result.values)

        # Lower bound should be <= values <= upper bound
        for i in range(n):
            assert result.lower_bound[i] <= result.values[i] <= result.upper_bound[i]

    def test_metrics_calculation(self, sufficient_data_series: TimeSeries):
        """Prediction should include accuracy metrics."""
        predictor = TrendPredictor(TrendPredictorConfig(forecast_periods=7))
        result = predictor.predict(sufficient_data_series)

        # Metrics should exist
        assert "MAE" in result.metrics
        assert "RMSE" in result.metrics
        assert "MAPE" in result.metrics

        # Metrics should be non-negative
        assert result.metrics["MAE"] >= 0
        assert result.metrics["RMSE"] >= 0
        assert result.metrics["MAPE"] >= 0

    def test_arima_model(self, sufficient_data_series: TimeSeries):
        """ARIMA model should work when explicitly selected."""
        predictor = TrendPredictor(
            TrendPredictorConfig(forecast_periods=5, model_type="arima")
        )
        result = predictor.predict(sufficient_data_series)

        assert len(result.values) == 5
        assert "ARIMA" in result.model_name

    def test_ets_model(self, sufficient_data_series: TimeSeries):
        """ETS model should work when explicitly selected."""
        predictor = TrendPredictor(
            TrendPredictorConfig(forecast_periods=5, model_type="ets")
        )
        result = predictor.predict(sufficient_data_series)

        assert len(result.values) == 5
        # Should use Holt's or Simple ES
        assert any(name in result.model_name for name in ["Holt", "Exponential"])

    def test_different_confidence_levels(self, sufficient_data_series: TimeSeries):
        """Different confidence levels should produce different interval widths."""
        predictor_95 = TrendPredictor(
            TrendPredictorConfig(forecast_periods=5, confidence_level=0.95)
        )
        predictor_80 = TrendPredictor(
            TrendPredictorConfig(forecast_periods=5, confidence_level=0.80)
        )

        result_95 = predictor_95.predict(sufficient_data_series)
        result_80 = predictor_80.predict(sufficient_data_series)

        # 95% CI should be wider than 80% CI
        width_95 = sum(u - l for u, l in zip(result_95.upper_bound, result_95.lower_bound))
        width_80 = sum(u - l for u, l in zip(result_80.upper_bound, result_80.lower_bound))

        assert width_95 > width_80

    def test_future_timestamps(self, sufficient_data_series: TimeSeries):
        """Predicted timestamps should be in the future relative to data."""
        predictor = TrendPredictor(TrendPredictorConfig(forecast_periods=7))
        result = predictor.predict(sufficient_data_series)

        last_data_timestamp = sufficient_data_series.points[-1].timestamp

        # All prediction timestamps should be after the last data point
        for ts in result.timestamps:
            assert ts > last_data_timestamp

    def test_fitted_values_and_residuals(self, sufficient_data_series: TimeSeries):
        """Prediction should include fitted values and residuals."""
        predictor = TrendPredictor(TrendPredictorConfig(forecast_periods=7))
        result = predictor.predict(sufficient_data_series)

        # Fitted values should exist (for ETS models)
        assert len(result.fitted_values) > 0

        # Residuals should exist
        assert len(result.residuals) > 0

    def test_analyze_method(self, sufficient_data_series: TimeSeries):
        """analyze() method should return AnalysisResult."""
        from reddit_insight.analysis.ml.base import AnalysisResult

        predictor = TrendPredictor(TrendPredictorConfig(forecast_periods=7))
        result = predictor.analyze(sufficient_data_series)

        assert isinstance(result, AnalysisResult)
        assert result.result_type == "prediction"
        assert result.success is True
        assert result.confidence == 0.95

    def test_analyze_with_insufficient_data(self, insufficient_data_series: TimeSeries):
        """analyze() should return error result for insufficient data."""
        predictor = TrendPredictor(TrendPredictorConfig(min_data_points=10))
        result = predictor.analyze(insufficient_data_series)

        assert result.success is False
        assert result.error_message is not None
        assert "Insufficient data" in result.error_message


class TestTrendPredictorDetection:
    """Tests for trend and seasonality detection."""

    def test_trend_detection_upward(self, sufficient_data_series: TimeSeries):
        """Should detect upward trend in data."""
        predictor = TrendPredictor(TrendPredictorConfig())
        values = sufficient_data_series.get_values()

        has_trend = predictor._detect_trend(values)
        assert bool(has_trend) is True

    def test_trend_detection_flat(self):
        """Should not detect trend in flat data."""
        base_time = datetime.now(UTC)
        points = [
            TimePoint(timestamp=base_time - timedelta(days=i), value=100.0)
            for i in range(30, 0, -1)
        ]
        flat_series = TimeSeries(
            keyword="flat",
            granularity=TimeGranularity.DAY,
            points=points,
        )

        predictor = TrendPredictor(TrendPredictorConfig())
        has_trend = predictor._detect_trend(flat_series.get_values())
        assert has_trend is False

    def test_seasonality_detection(self, seasonal_data_series: TimeSeries):
        """Should detect seasonality when period is specified."""
        predictor = TrendPredictor(
            TrendPredictorConfig(seasonal_period=7, model_type="auto")
        )

        # Test seasonality detection
        values = seasonal_data_series.get_values()
        has_seasonality = predictor._detect_seasonality(values, 7)

        # Should detect the weekly pattern we added
        assert bool(has_seasonality) is True


class TestPredictionResultValidation:
    """Tests for PredictionResult to_dict serialization."""

    def test_to_dict(self, sufficient_data_series: TimeSeries):
        """PredictionResult should serialize to dictionary correctly."""
        predictor = TrendPredictor(TrendPredictorConfig(forecast_periods=5))
        result = predictor.predict(sufficient_data_series)

        result_dict = result.to_dict()

        assert "timestamps" in result_dict
        assert "values" in result_dict
        assert "lower_bound" in result_dict
        assert "upper_bound" in result_dict
        assert "confidence_level" in result_dict
        assert "model_name" in result_dict
        assert "metrics" in result_dict
        assert "n_predictions" in result_dict

        # Timestamps should be ISO format strings
        assert all(isinstance(ts, str) for ts in result_dict["timestamps"])
