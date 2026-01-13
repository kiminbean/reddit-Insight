"""
Anomaly detection for time series data.

Provides multiple methods for detecting anomalies in keyword trend data:
- Z-score: Statistical method using standard deviations from mean
- IQR: Interquartile range method for robust outlier detection
- Isolation Forest: Machine learning method for complex patterns

Example:
    >>> from reddit_insight.analysis.ml.anomaly_detector import (
    ...     AnomalyDetector, AnomalyDetectorConfig
    ... )
    >>> from reddit_insight.analysis.time_series import TimeSeries, TimePoint
    >>> from datetime import datetime, timedelta
    >>>
    >>> points = [TimePoint(datetime.now() - timedelta(days=i), 10.0) for i in range(20)]
    >>> points[10] = TimePoint(points[10].timestamp, 100.0)  # Insert anomaly
    >>> ts = TimeSeries(keyword="test", points=points, granularity=TimeGranularity.DAY)
    >>> detector = AnomalyDetector()
    >>> result = detector.detect(ts)
    >>> print(f"Found {result.anomaly_count} anomalies")
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Literal

import numpy as np

from reddit_insight.analysis.ml.base import (
    AnalysisResult,
    MLAnalyzerBase,
    MLAnalyzerConfig,
)
from reddit_insight.analysis.ml.models import AnomalyPoint, AnomalyResult

if TYPE_CHECKING:
    from reddit_insight.analysis.time_series import TimeSeries


AnomalyMethod = Literal["zscore", "iqr", "isolation_forest", "auto"]


@dataclass
class AnomalyDetectorConfig(MLAnalyzerConfig):
    """
    Configuration for anomaly detection.

    Attributes:
        method: Detection method ("zscore", "iqr", "isolation_forest", "auto")
        threshold: Z-score threshold for zscore method (default: 3.0)
        contamination: Expected proportion of anomalies for Isolation Forest
        window_size: Rolling window size for statistics (0 = use all data)
        min_data_points: Minimum data points required for detection
        iqr_multiplier: Multiplier for IQR range (default: 1.5)

    Example:
        >>> config = AnomalyDetectorConfig(method="zscore", threshold=2.5)
        >>> detector = AnomalyDetector(config)
    """

    method: AnomalyMethod = "auto"
    threshold: float = 3.0
    contamination: float = 0.05
    window_size: int = 0  # 0 = use all data
    min_data_points: int = 10
    iqr_multiplier: float = 1.5
    name: str = "AnomalyDetector"
    version: str = "1.0.0"


class AnomalyDetector(MLAnalyzerBase):
    """
    Multi-method anomaly detector for time series data.

    Supports three detection methods:
    - Z-score: Best for normally distributed data, fast computation
    - IQR: Robust to non-normal distributions, good for small-medium datasets
    - Isolation Forest: ML-based, best for complex patterns and large datasets

    The "auto" method selects the best approach based on data size:
    - <30 points: zscore (simple and stable)
    - 30-100 points: iqr
    - >100 points: isolation_forest

    Attributes:
        config: Configuration for the detector

    Example:
        >>> detector = AnomalyDetector()
        >>> result = detector.detect(time_series)
        >>> for point in result.detected_anomalies:
        ...     print(f"Anomaly at {point.timestamp}: {point.value}")
    """

    def __init__(self, config: AnomalyDetectorConfig | None = None) -> None:
        """
        Initialize the anomaly detector.

        Args:
            config: Configuration for detection, uses defaults if None
        """
        super().__init__(config or AnomalyDetectorConfig())

    @property
    def detector_config(self) -> AnomalyDetectorConfig:
        """Get the detector configuration with correct type."""
        return self.config  # type: ignore[return-value]

    def analyze(self, data: TimeSeries) -> AnalysisResult:
        """
        Perform anomaly analysis on time series data.

        Implements the MLAnalyzerBase interface.

        Args:
            data: TimeSeries to analyze

        Returns:
            AnalysisResult containing AnomalyResult
        """
        start_time = time.time()
        result = self.detect(data)
        processing_time_ms = (time.time() - start_time) * 1000

        # Calculate confidence based on data quality
        confidence = self._calculate_confidence(len(data.points), result.anomaly_count)

        return AnalysisResult(
            result_type="anomaly",
            data=result.to_dict(),
            metadata=self._create_metadata(
                data_size=len(data.points),
                processing_time_ms=processing_time_ms,
                parameters={
                    "method": result.method,
                    "threshold": result.threshold,
                },
            ),
            confidence=confidence,
            success=True,
        )

    def detect(self, time_series: TimeSeries) -> AnomalyResult:
        """
        Detect anomalies in a time series.

        Args:
            time_series: TimeSeries object to analyze

        Returns:
            AnomalyResult with detected anomalies

        Raises:
            ValueError: If insufficient data points for detection
        """
        values = time_series.get_values()
        timestamps = time_series.get_timestamps()
        cfg = self.detector_config

        # Validate minimum data
        if len(values) < cfg.min_data_points:
            return AnomalyResult(
                anomalies=[],
                threshold=cfg.threshold,
                method="insufficient_data",
                total_points=len(values),
                anomaly_count=0,
                contamination=cfg.contamination,
                parameters={"min_required": cfg.min_data_points},
            )

        # Select method
        method = cfg.method
        if method == "auto":
            method = self._auto_select_method(values)

        # Perform detection based on method
        if method == "zscore":
            anomalies, threshold = self._detect_zscore(values, timestamps)
        elif method == "iqr":
            anomalies, threshold = self._detect_iqr(values, timestamps)
        elif method == "isolation_forest":
            anomalies, threshold = self._detect_isolation_forest(values, timestamps)
        else:
            raise ValueError(f"Unknown method: {method}")

        return AnomalyResult(
            anomalies=anomalies,
            threshold=threshold,
            method=method,
            total_points=len(values),
            anomaly_count=sum(1 for a in anomalies if a.is_anomaly),
            contamination=cfg.contamination,
            parameters={
                "window_size": cfg.window_size,
                "iqr_multiplier": cfg.iqr_multiplier,
            },
        )

    def _auto_select_method(self, values: list[float]) -> str:
        """
        Automatically select the best detection method based on data size.

        Selection criteria:
        - <30 points: zscore (simple, stable with small data)
        - 30-100 points: iqr (robust to outliers)
        - >100 points: isolation_forest (handles complex patterns)

        Args:
            values: List of values to analyze

        Returns:
            Selected method name
        """
        n = len(values)
        if n < 30:
            return "zscore"
        elif n <= 100:
            return "iqr"
        else:
            return "isolation_forest"

    def _detect_zscore(
        self,
        values: list[float],
        timestamps: list[datetime],
    ) -> tuple[list[AnomalyPoint], float]:
        """
        Detect anomalies using Z-score method.

        Z-score measures how many standard deviations a point is from the mean.
        Points with |z-score| > threshold are classified as anomalies.

        Args:
            values: List of values to analyze
            timestamps: Corresponding timestamps

        Returns:
            Tuple of (anomaly points, threshold used)
        """
        cfg = self.detector_config
        arr = np.array(values, dtype=np.float64)
        threshold = cfg.threshold

        if cfg.window_size > 0 and len(arr) > cfg.window_size:
            # Rolling statistics
            anomalies = self._detect_zscore_rolling(arr, timestamps, threshold)
        else:
            # Global statistics
            mean = float(np.mean(arr))
            std = float(np.std(arr))

            if std == 0:
                # No variation - no anomalies
                return [
                    AnomalyPoint(
                        timestamp=ts,
                        value=val,
                        anomaly_score=0.0,
                        is_anomaly=False,
                        expected_value=mean,
                        deviation=0.0,
                    )
                    for ts, val in zip(timestamps, values)
                ], threshold

            anomalies = []
            for ts, val in zip(timestamps, values):
                z_score = abs((val - mean) / std)
                is_anomaly = z_score > threshold
                deviation = val - mean

                anomalies.append(
                    AnomalyPoint(
                        timestamp=ts,
                        value=val,
                        anomaly_score=z_score,
                        is_anomaly=is_anomaly,
                        expected_value=mean,
                        deviation=deviation,
                    )
                )

        return anomalies, threshold

    def _detect_zscore_rolling(
        self,
        arr: np.ndarray,
        timestamps: list[datetime],
        threshold: float,
    ) -> list[AnomalyPoint]:
        """
        Detect anomalies using rolling Z-score.

        Uses a sliding window to compute local statistics, which helps
        detect anomalies in data with trends or seasonality.

        Args:
            arr: Numpy array of values
            timestamps: Corresponding timestamps
            threshold: Z-score threshold

        Returns:
            List of anomaly points
        """
        cfg = self.detector_config
        window = cfg.window_size
        anomalies = []

        for i, (ts, val) in enumerate(zip(timestamps, arr)):
            # Get window of values centered on current point
            start_idx = max(0, i - window // 2)
            end_idx = min(len(arr), i + window // 2 + 1)
            window_vals = arr[start_idx:end_idx]

            mean = float(np.mean(window_vals))
            std = float(np.std(window_vals))

            if std == 0:
                z_score = 0.0
            else:
                z_score = abs((float(val) - mean) / std)

            is_anomaly = z_score > threshold
            deviation = float(val) - mean

            anomalies.append(
                AnomalyPoint(
                    timestamp=ts,
                    value=float(val),
                    anomaly_score=z_score,
                    is_anomaly=is_anomaly,
                    expected_value=mean,
                    deviation=deviation,
                )
            )

        return anomalies

    def _detect_iqr(
        self,
        values: list[float],
        timestamps: list[datetime],
    ) -> tuple[list[AnomalyPoint], float]:
        """
        Detect anomalies using Interquartile Range (IQR) method.

        IQR is robust to outliers and doesn't assume normal distribution.
        Outliers are points outside [Q1 - k*IQR, Q3 + k*IQR] where k=1.5.

        Args:
            values: List of values to analyze
            timestamps: Corresponding timestamps

        Returns:
            Tuple of (anomaly points, threshold based on IQR)
        """
        cfg = self.detector_config
        arr = np.array(values, dtype=np.float64)
        k = cfg.iqr_multiplier

        q1 = float(np.percentile(arr, 25))
        q3 = float(np.percentile(arr, 75))
        iqr = q3 - q1

        lower_bound = q1 - k * iqr
        upper_bound = q3 + k * iqr

        median = float(np.median(arr))

        anomalies = []
        for ts, val in zip(timestamps, values):
            is_anomaly = val < lower_bound or val > upper_bound

            # Calculate anomaly score based on distance from bounds
            if val < lower_bound:
                distance = lower_bound - val
            elif val > upper_bound:
                distance = val - upper_bound
            else:
                distance = 0.0

            # Normalize score by IQR (if IQR is 0, use absolute distance)
            if iqr > 0:
                anomaly_score = distance / iqr
            else:
                anomaly_score = distance if distance > 0 else 0.0

            deviation = val - median

            anomalies.append(
                AnomalyPoint(
                    timestamp=ts,
                    value=val,
                    anomaly_score=anomaly_score,
                    is_anomaly=is_anomaly,
                    expected_value=median,
                    deviation=deviation,
                )
            )

        # Return threshold as the IQR multiplier used
        return anomalies, k

    def _detect_isolation_forest(
        self,
        values: list[float],
        timestamps: list[datetime],
    ) -> tuple[list[AnomalyPoint], float]:
        """
        Detect anomalies using Isolation Forest algorithm.

        Isolation Forest isolates observations by randomly selecting a feature
        and split value. Anomalies require fewer splits to isolate.

        Args:
            values: List of values to analyze
            timestamps: Corresponding timestamps

        Returns:
            Tuple of (anomaly points, contamination threshold)
        """
        try:
            from sklearn.ensemble import IsolationForest
        except ImportError as e:
            raise ImportError(
                "scikit-learn is required for Isolation Forest. "
                "Install with: pip install scikit-learn"
            ) from e

        cfg = self.detector_config
        arr = np.array(values, dtype=np.float64).reshape(-1, 1)
        contamination = cfg.contamination

        # Fit Isolation Forest
        model = IsolationForest(
            contamination=contamination,
            random_state=cfg.random_state,
            n_estimators=100,
        )
        predictions = model.fit_predict(arr)
        scores = -model.decision_function(arr)  # Higher = more anomalous

        # Calculate expected value as median
        median = float(np.median(arr))

        anomalies = []
        for i, (ts, val) in enumerate(zip(timestamps, values)):
            # prediction: -1 = anomaly, 1 = normal
            is_anomaly = predictions[i] == -1
            anomaly_score = float(scores[i])
            deviation = val - median

            anomalies.append(
                AnomalyPoint(
                    timestamp=ts,
                    value=val,
                    anomaly_score=anomaly_score,
                    is_anomaly=is_anomaly,
                    expected_value=median,
                    deviation=deviation,
                )
            )

        return anomalies, contamination

    def _calculate_confidence(self, data_size: int, anomaly_count: int) -> float:
        """
        Calculate confidence score for the detection result.

        Higher confidence with more data points and reasonable anomaly rates.

        Args:
            data_size: Number of data points analyzed
            anomaly_count: Number of anomalies detected

        Returns:
            Confidence score between 0 and 1
        """
        cfg = self.detector_config

        # Base confidence from data size
        if data_size < cfg.min_data_points:
            return 0.3
        elif data_size < 30:
            size_confidence = 0.6
        elif data_size < 100:
            size_confidence = 0.8
        else:
            size_confidence = 0.9

        # Adjust for anomaly rate (too many or too few anomalies reduce confidence)
        if data_size > 0:
            anomaly_rate = anomaly_count / data_size
            if anomaly_rate > 0.3:  # More than 30% anomalies is suspicious
                rate_confidence = 0.7
            elif anomaly_rate < 0.001 and data_size > 100:  # Too few in large dataset
                rate_confidence = 0.8
            else:
                rate_confidence = 1.0
        else:
            rate_confidence = 0.5

        return min(size_confidence * rate_confidence, 1.0)


def detect_anomalies_simple(
    values: list[float],
    timestamps: list[datetime] | None = None,
    method: AnomalyMethod = "auto",
    threshold: float = 3.0,
) -> list[tuple[int, float, float]]:
    """
    Simple function for quick anomaly detection without TimeSeries.

    Convenience function for detecting anomalies in a simple list of values.

    Args:
        values: List of numeric values to analyze
        timestamps: Optional timestamps (auto-generated if None)
        method: Detection method to use
        threshold: Threshold for anomaly classification

    Returns:
        List of (index, value, anomaly_score) tuples for detected anomalies

    Example:
        >>> values = [10, 11, 12, 100, 11, 10]  # 100 is anomaly
        >>> anomalies = detect_anomalies_simple(values)
        >>> for idx, val, score in anomalies:
        ...     print(f"Index {idx}: value={val}, score={score:.2f}")
    """
    from datetime import UTC, timedelta

    from reddit_insight.analysis.time_series import TimeGranularity, TimeSeries, TimePoint

    # Generate timestamps if not provided
    if timestamps is None:
        now = datetime.now(UTC)
        timestamps = [now - timedelta(hours=len(values) - i) for i in range(len(values))]

    # Create TimeSeries
    points = [
        TimePoint(timestamp=ts, value=val) for ts, val in zip(timestamps, values)
    ]
    ts = TimeSeries(
        keyword="analysis",
        granularity=TimeGranularity.HOUR,
        points=points,
    )

    # Detect anomalies
    config = AnomalyDetectorConfig(method=method, threshold=threshold)
    detector = AnomalyDetector(config)
    result = detector.detect(ts)

    # Return only anomalies
    anomalies = []
    for i, point in enumerate(result.anomalies):
        if point.is_anomaly:
            anomalies.append((i, point.value, point.anomaly_score))

    return anomalies
