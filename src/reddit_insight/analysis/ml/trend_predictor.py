"""
Trend Predictor for time series forecasting.

Provides time series prediction using exponential smoothing (ETS) and ARIMA models
with automatic model selection based on data characteristics.

Example:
    >>> from reddit_insight.analysis.ml.trend_predictor import TrendPredictor, TrendPredictorConfig
    >>> from reddit_insight.analysis.time_series import TimeSeries, TimePoint
    >>> predictor = TrendPredictor(TrendPredictorConfig(forecast_periods=7))
    >>> result = predictor.predict(time_series)
"""

from __future__ import annotations

import time
import warnings
from dataclasses import dataclass, field
from datetime import timedelta
from typing import TYPE_CHECKING, Any, Literal

import numpy as np

from reddit_insight.analysis.ml.base import (
    AnalysisResult,
    MLAnalyzerBase,
    MLAnalyzerConfig,
)
from reddit_insight.analysis.ml.models import PredictionResult
from reddit_insight.analysis.time_series import TimeSeries, get_time_delta

if TYPE_CHECKING:
    pass


@dataclass
class TrendPredictorConfig(MLAnalyzerConfig):
    """
    Configuration for TrendPredictor.

    Attributes:
        forecast_periods: Number of future periods to predict
        confidence_level: Confidence level for prediction intervals (e.g., 0.95 for 95%)
        min_data_points: Minimum number of data points required for prediction
        model_type: Model type to use ("auto", "ets", "arima")
        seasonal_period: Seasonal period for models (None for auto-detection)
        name: Analyzer name
        version: Analyzer version
    """

    forecast_periods: int = 7
    confidence_level: float = 0.95
    min_data_points: int = 10
    model_type: Literal["auto", "ets", "arima"] = "auto"
    seasonal_period: int | None = None
    name: str = "TrendPredictor"
    version: str = "1.0.0"


class TrendPredictor(MLAnalyzerBase):
    """
    Time series predictor using exponential smoothing and ARIMA.

    Automatically selects the appropriate model based on data characteristics:
    - 10-30 data points: Simple Exponential Smoothing
    - 30+ data points with trend: Holt's Linear
    - 30+ data points with seasonality: Holt-Winters

    Attributes:
        config: TrendPredictorConfig with prediction settings

    Example:
        >>> predictor = TrendPredictor(TrendPredictorConfig(forecast_periods=7))
        >>> result = predictor.predict(time_series)
        >>> print(f"Predicted {len(result.values)} future values")
    """

    def __init__(self, config: TrendPredictorConfig | None = None) -> None:
        """
        Initialize TrendPredictor.

        Args:
            config: Configuration for the predictor
        """
        self.config: TrendPredictorConfig = config or TrendPredictorConfig()
        super().__init__(self.config)
        self._model: Any = None

    def analyze(self, data: TimeSeries) -> AnalysisResult:
        """
        Analyze time series by predicting future values.

        Args:
            data: TimeSeries to analyze

        Returns:
            AnalysisResult containing PredictionResult
        """
        start_time = time.time()

        try:
            prediction = self.predict(data)
            processing_time_ms = (time.time() - start_time) * 1000

            return AnalysisResult(
                result_type="prediction",
                data=prediction.to_dict(),
                metadata=self._create_metadata(
                    data_size=len(data),
                    processing_time_ms=processing_time_ms,
                    parameters={
                        "forecast_periods": self.config.forecast_periods,
                        "confidence_level": self.config.confidence_level,
                        "model_type": self.config.model_type,
                    },
                ),
                confidence=self.config.confidence_level,
                success=True,
            )
        except Exception as e:
            return self._create_error_result("prediction", str(e))

    def predict(self, time_series: TimeSeries) -> PredictionResult:
        """
        Predict future values for the time series.

        Args:
            time_series: TimeSeries with historical data

        Returns:
            PredictionResult with predictions and confidence intervals

        Raises:
            ValueError: If insufficient data points
        """
        values = time_series.get_values()

        # Validate data
        if len(values) < self.config.min_data_points:
            raise ValueError(
                f"Insufficient data: {len(values)} points, "
                f"minimum required: {self.config.min_data_points}"
            )

        # Select and fit model
        if self.config.model_type == "arima":
            return self._predict_arima(time_series, values)
        elif self.config.model_type == "ets":
            return self._predict_ets(time_series, values)
        else:
            # Auto-select model based on data characteristics
            return self._predict_auto(time_series, values)

    def _predict_auto(
        self, time_series: TimeSeries, values: list[float]
    ) -> PredictionResult:
        """
        Automatically select and apply the best model.

        Selection logic:
        - 10-30 points: Simple Exponential Smoothing
        - 30+ points: Check for trend and seasonality
          - With trend: Holt's Linear
          - With seasonality: Holt-Winters
          - Otherwise: Simple ES or Holt's Linear

        Args:
            time_series: Original time series
            values: List of numeric values

        Returns:
            PredictionResult from the selected model
        """
        n = len(values)

        if n < 30:
            # Small dataset: Simple Exponential Smoothing
            return self._fit_simple_es(time_series, values)
        else:
            # Check for trend using simple linear regression
            has_trend = self._detect_trend(values)

            # Check for seasonality if period is specified or detected
            seasonal_period = self.config.seasonal_period
            has_seasonality = False

            if seasonal_period and n >= seasonal_period * 2:
                has_seasonality = self._detect_seasonality(values, seasonal_period)

            if has_seasonality and seasonal_period:
                return self._fit_holtwinters(time_series, values, seasonal_period)
            elif has_trend:
                return self._fit_holts_linear(time_series, values)
            else:
                return self._fit_simple_es(time_series, values)

    def _predict_ets(
        self, time_series: TimeSeries, values: list[float]
    ) -> PredictionResult:
        """
        Apply Exponential Smoothing model.

        Args:
            time_series: Original time series
            values: List of numeric values

        Returns:
            PredictionResult from ETS model
        """
        has_trend = self._detect_trend(values) if len(values) >= 30 else False

        if has_trend and len(values) >= 30:
            return self._fit_holts_linear(time_series, values)
        else:
            return self._fit_simple_es(time_series, values)

    def _predict_arima(
        self, time_series: TimeSeries, values: list[float]
    ) -> PredictionResult:
        """
        Apply ARIMA model.

        Args:
            time_series: Original time series
            values: List of numeric values

        Returns:
            PredictionResult from ARIMA model
        """
        return self._fit_arima(time_series, values)

    def _fit_simple_es(
        self, time_series: TimeSeries, values: list[float]
    ) -> PredictionResult:
        """
        Fit Simple Exponential Smoothing model.

        Args:
            time_series: Original time series
            values: List of numeric values

        Returns:
            PredictionResult with predictions
        """
        from statsmodels.tsa.holtwinters import SimpleExpSmoothing

        # Suppress convergence warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")

            # Ensure all values are positive for multiplicative models
            # Use additive model for simple ES
            model = SimpleExpSmoothing(
                np.array(values),
                initialization_method="estimated",
            )
            fitted = model.fit(optimized=True)

        # Generate forecast
        forecast = fitted.forecast(self.config.forecast_periods)

        # Calculate confidence intervals using residual standard error
        residuals = fitted.resid
        std_error = np.std(residuals)
        z_score = self._get_z_score(self.config.confidence_level)

        lower_bound = [float(v - z_score * std_error) for v in forecast]
        upper_bound = [float(v + z_score * std_error) for v in forecast]

        # Generate future timestamps
        timestamps = self._generate_future_timestamps(time_series)

        # Calculate metrics
        fitted_values = list(fitted.fittedvalues)
        metrics = self._calculate_metrics(values, fitted_values)

        return PredictionResult(
            timestamps=timestamps,
            values=[float(v) for v in forecast],
            lower_bound=lower_bound,
            upper_bound=upper_bound,
            confidence_level=self.config.confidence_level,
            model_name="SimpleExponentialSmoothing",
            metrics=metrics,
            fitted_values=fitted_values,
            residuals=[float(r) for r in residuals],
        )

    def _fit_holts_linear(
        self, time_series: TimeSeries, values: list[float]
    ) -> PredictionResult:
        """
        Fit Holt's Linear Trend model.

        Args:
            time_series: Original time series
            values: List of numeric values

        Returns:
            PredictionResult with predictions
        """
        from statsmodels.tsa.holtwinters import ExponentialSmoothing

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")

            model = ExponentialSmoothing(
                np.array(values),
                trend="add",
                seasonal=None,
                initialization_method="estimated",
            )
            fitted = model.fit(optimized=True)

        # Generate forecast
        forecast = fitted.forecast(self.config.forecast_periods)

        # Calculate confidence intervals
        residuals = fitted.resid
        std_error = np.std(residuals)
        z_score = self._get_z_score(self.config.confidence_level)

        # Widen intervals for further predictions
        lower_bound = []
        upper_bound = []
        for i, v in enumerate(forecast):
            interval_width = z_score * std_error * np.sqrt(1 + i / len(values))
            lower_bound.append(float(v - interval_width))
            upper_bound.append(float(v + interval_width))

        timestamps = self._generate_future_timestamps(time_series)
        fitted_values = list(fitted.fittedvalues)
        metrics = self._calculate_metrics(values, fitted_values)

        return PredictionResult(
            timestamps=timestamps,
            values=[float(v) for v in forecast],
            lower_bound=lower_bound,
            upper_bound=upper_bound,
            confidence_level=self.config.confidence_level,
            model_name="Holt's Linear",
            metrics=metrics,
            fitted_values=fitted_values,
            residuals=[float(r) for r in residuals],
        )

    def _fit_holtwinters(
        self, time_series: TimeSeries, values: list[float], seasonal_period: int
    ) -> PredictionResult:
        """
        Fit Holt-Winters model with seasonality.

        Args:
            time_series: Original time series
            values: List of numeric values
            seasonal_period: Seasonal period length

        Returns:
            PredictionResult with predictions
        """
        from statsmodels.tsa.holtwinters import ExponentialSmoothing

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")

            # Use additive seasonality by default (safer for various data)
            model = ExponentialSmoothing(
                np.array(values),
                trend="add",
                seasonal="add",
                seasonal_periods=seasonal_period,
                initialization_method="estimated",
            )
            fitted = model.fit(optimized=True)

        forecast = fitted.forecast(self.config.forecast_periods)

        # Calculate confidence intervals
        residuals = fitted.resid
        std_error = np.std(residuals)
        z_score = self._get_z_score(self.config.confidence_level)

        lower_bound = []
        upper_bound = []
        for i, v in enumerate(forecast):
            interval_width = z_score * std_error * np.sqrt(1 + i / len(values))
            lower_bound.append(float(v - interval_width))
            upper_bound.append(float(v + interval_width))

        timestamps = self._generate_future_timestamps(time_series)
        fitted_values = list(fitted.fittedvalues)
        metrics = self._calculate_metrics(values, fitted_values)

        return PredictionResult(
            timestamps=timestamps,
            values=[float(v) for v in forecast],
            lower_bound=lower_bound,
            upper_bound=upper_bound,
            confidence_level=self.config.confidence_level,
            model_name=f"Holt-Winters(seasonal={seasonal_period})",
            metrics=metrics,
            fitted_values=fitted_values,
            residuals=[float(r) for r in residuals],
        )

    def _fit_arima(
        self, time_series: TimeSeries, values: list[float]
    ) -> PredictionResult:
        """
        Fit ARIMA model with automatic order selection.

        Args:
            time_series: Original time series
            values: List of numeric values

        Returns:
            PredictionResult with predictions
        """
        from statsmodels.tsa.arima.model import ARIMA

        # Determine order based on data characteristics
        # Simple heuristic: ARIMA(1,1,1) for most cases
        order = self._select_arima_order(values)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")

            model = ARIMA(np.array(values), order=order)
            fitted = model.fit()

        # Get forecast with confidence intervals
        forecast_result = fitted.get_forecast(steps=self.config.forecast_periods)
        forecast = forecast_result.predicted_mean
        conf_int = forecast_result.conf_int(alpha=1 - self.config.confidence_level)

        timestamps = self._generate_future_timestamps(time_series)
        fitted_values = list(fitted.fittedvalues)
        residuals = list(fitted.resid)
        metrics = self._calculate_metrics(values[order[1]:], fitted_values)

        return PredictionResult(
            timestamps=timestamps,
            values=[float(v) for v in forecast],
            lower_bound=[float(v) for v in conf_int.iloc[:, 0]],
            upper_bound=[float(v) for v in conf_int.iloc[:, 1]],
            confidence_level=self.config.confidence_level,
            model_name=f"ARIMA{order}",
            metrics=metrics,
            fitted_values=fitted_values,
            residuals=residuals,
        )

    def _select_arima_order(self, values: list[float]) -> tuple[int, int, int]:
        """
        Select ARIMA order using simple heuristics.

        Uses ADF test to determine differencing order and simple rules for p, q.

        Args:
            values: List of numeric values

        Returns:
            Tuple of (p, d, q) order
        """
        from statsmodels.tsa.stattools import adfuller

        # Check stationarity to determine d
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                adf_result = adfuller(values, maxlag=min(10, len(values) // 4))
                p_value = adf_result[1]

            # If p-value > 0.05, series is non-stationary, use d=1
            d = 0 if p_value < 0.05 else 1
        except Exception:
            d = 1  # Default to differencing

        # Simple heuristics for p and q
        # For small datasets, use lower orders
        n = len(values)
        if n < 30:
            p, q = 1, 0
        elif n < 60:
            p, q = 1, 1
        else:
            p, q = 2, 1

        return (p, d, q)

    def _detect_trend(self, values: list[float]) -> bool:
        """
        Detect if there's a significant trend in the data.

        Uses simple linear regression slope significance test.

        Args:
            values: List of numeric values

        Returns:
            True if significant trend detected
        """
        n = len(values)
        if n < 5:
            return False

        # Simple linear regression
        x = np.arange(n)
        x_mean = np.mean(x)
        y_mean = np.mean(values)

        numerator = np.sum((x - x_mean) * (values - y_mean))
        denominator = np.sum((x - x_mean) ** 2)

        if denominator == 0:
            return False

        slope = numerator / denominator

        # Calculate R-squared
        y_pred = x_mean + slope * (x - x_mean)
        ss_res = np.sum((values - y_pred) ** 2)
        ss_tot = np.sum((values - y_mean) ** 2)

        if ss_tot == 0:
            return False

        r_squared = 1 - (ss_res / ss_tot)

        # Consider trend significant if R-squared > 0.3 and slope is meaningful
        relative_slope = abs(slope) / (y_mean if y_mean != 0 else 1)
        return r_squared > 0.3 and relative_slope > 0.01

    def _detect_seasonality(self, values: list[float], period: int) -> bool:
        """
        Detect if there's significant seasonality in the data.

        Uses autocorrelation at the seasonal lag.

        Args:
            values: List of numeric values
            period: Expected seasonal period

        Returns:
            True if significant seasonality detected
        """
        if len(values) < period * 2:
            return False

        # Calculate autocorrelation at seasonal lag
        arr = np.array(values)
        mean = np.mean(arr)
        var = np.var(arr)

        if var == 0:
            return False

        autocorr = np.correlate(arr - mean, arr - mean, mode="full")
        autocorr = autocorr[len(autocorr) // 2:]
        autocorr = autocorr / (var * len(arr))

        if period < len(autocorr):
            # Significant seasonality if autocorrelation at lag > 0.3
            return abs(autocorr[period]) > 0.3

        return False

    def _generate_future_timestamps(self, time_series: TimeSeries) -> list:
        """
        Generate timestamps for forecast periods.

        Args:
            time_series: Original time series

        Returns:
            List of future timestamps
        """
        from datetime import datetime

        if not time_series.points:
            # Return placeholder timestamps
            from datetime import UTC
            base = datetime.now(UTC)
            delta = timedelta(days=1)
            return [base + delta * (i + 1) for i in range(self.config.forecast_periods)]

        last_timestamp = time_series.points[-1].timestamp
        delta = get_time_delta(time_series.granularity)

        timestamps = []
        for i in range(self.config.forecast_periods):
            timestamps.append(last_timestamp + delta * (i + 1))

        return timestamps

    def _calculate_metrics(
        self, actual: list[float], predicted: list[float]
    ) -> dict[str, float]:
        """
        Calculate forecast accuracy metrics.

        Args:
            actual: Actual values
            predicted: Predicted/fitted values

        Returns:
            Dictionary with MAE, RMSE, and MAPE metrics
        """
        # Align lengths (predictions may have different length due to differencing)
        min_len = min(len(actual), len(predicted))
        if min_len == 0:
            return {"MAE": 0.0, "RMSE": 0.0, "MAPE": 0.0}

        actual_arr = np.array(actual[-min_len:])
        pred_arr = np.array(predicted[-min_len:])

        # Mean Absolute Error
        mae = float(np.mean(np.abs(actual_arr - pred_arr)))

        # Root Mean Square Error
        rmse = float(np.sqrt(np.mean((actual_arr - pred_arr) ** 2)))

        # Mean Absolute Percentage Error (avoid division by zero)
        non_zero_mask = actual_arr != 0
        if np.any(non_zero_mask):
            mape = float(
                np.mean(np.abs((actual_arr[non_zero_mask] - pred_arr[non_zero_mask]) / actual_arr[non_zero_mask])) * 100
            )
        else:
            mape = 0.0

        return {
            "MAE": round(mae, 4),
            "RMSE": round(rmse, 4),
            "MAPE": round(mape, 2),
        }

    def _get_z_score(self, confidence_level: float) -> float:
        """
        Get z-score for confidence interval.

        Args:
            confidence_level: Confidence level (e.g., 0.95)

        Returns:
            Z-score for the confidence level
        """
        from scipy.stats import norm

        return norm.ppf((1 + confidence_level) / 2)
