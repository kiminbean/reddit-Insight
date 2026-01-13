"""
Trend analysis for keyword time series.

Provides tools for calculating trend metrics, detecting trend direction,
and analyzing keyword frequency changes over time.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING

from reddit_insight.analysis.time_series import (
    TimeGranularity,
    TimePoint,
    TimeSeries,
    bucket_timestamp,
)

if TYPE_CHECKING:
    from collections import defaultdict

    from reddit_insight.analysis.keywords import UnifiedKeywordExtractor
    from reddit_insight.reddit.models import Post


# Threshold constants for trend classification
RISING_THRESHOLD = 0.1  # 10% increase considered rising
FALLING_THRESHOLD = -0.1  # 10% decrease considered falling
VOLATILITY_THRESHOLD = 0.3  # 30% volatility considered high


class TrendDirection(Enum):
    """
    Direction of a trend.

    Attributes:
        RISING: Upward trend (positive change rate)
        FALLING: Downward trend (negative change rate)
        STABLE: No significant change
        VOLATILE: High variance, unclear direction
    """

    RISING = "rising"
    FALLING = "falling"
    STABLE = "stable"
    VOLATILE = "volatile"


@dataclass
class TrendMetrics:
    """
    Metrics describing a trend.

    Attributes:
        direction: Overall trend direction
        change_rate: Percentage change over the period (0.1 = 10%)
        slope: Linear regression slope
        volatility: Standard deviation of values (coefficient of variation)
        momentum: Recent change intensity (last period vs average)
    """

    direction: TrendDirection
    change_rate: float
    slope: float
    volatility: float
    momentum: float = 0.0

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "direction": self.direction.value,
            "change_rate": self.change_rate,
            "slope": self.slope,
            "volatility": self.volatility,
            "momentum": self.momentum,
        }

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"TrendMetrics(direction={self.direction.value}, "
            f"change_rate={self.change_rate:.2%}, "
            f"slope={self.slope:.4f}, "
            f"volatility={self.volatility:.2f})"
        )


@dataclass
class TrendCalculator:
    """
    Calculator for trend metrics from time series data.

    Provides methods to calculate various trend indicators including
    slope, change rate, volatility, and momentum.

    Attributes:
        smoothing_window: Window size for moving average smoothing

    Example:
        >>> calculator = TrendCalculator(smoothing_window=3)
        >>> metrics = calculator.calculate_trend(series)
        >>> print(metrics.direction)
        TrendDirection.RISING
    """

    smoothing_window: int = 3
    _rising_threshold: float = field(default=RISING_THRESHOLD, repr=False)
    _falling_threshold: float = field(default=FALLING_THRESHOLD, repr=False)
    _volatility_threshold: float = field(default=VOLATILITY_THRESHOLD, repr=False)

    def calculate_trend(self, series: TimeSeries) -> TrendMetrics:
        """
        Calculate comprehensive trend metrics for a time series.

        Args:
            series: Time series to analyze

        Returns:
            TrendMetrics with all calculated indicators
        """
        values = series.get_values()

        if len(values) < 2:
            return TrendMetrics(
                direction=TrendDirection.STABLE,
                change_rate=0.0,
                slope=0.0,
                volatility=0.0,
                momentum=0.0,
            )

        # Calculate individual metrics
        change_rate = self.get_change_rate(series)
        slope = self.get_slope(series)
        volatility = self._calculate_volatility(values)
        momentum = self._calculate_momentum(values)

        # Determine direction based on metrics
        direction = self._classify_direction(change_rate, slope, volatility)

        return TrendMetrics(
            direction=direction,
            change_rate=change_rate,
            slope=slope,
            volatility=volatility,
            momentum=momentum,
        )

    def get_moving_average(self, series: TimeSeries, window: int | None = None) -> list[float]:
        """
        Calculate moving average of the time series.

        Args:
            series: Time series to smooth
            window: Window size (defaults to smoothing_window)

        Returns:
            List of smoothed values (shorter than original by window-1)
        """
        if window is None:
            window = self.smoothing_window

        values = series.get_values()

        if len(values) < window:
            return values.copy()

        result = []
        for i in range(len(values) - window + 1):
            window_values = values[i:i + window]
            avg = sum(window_values) / window
            result.append(avg)

        return result

    def get_change_rate(self, series: TimeSeries, periods: int = 1) -> float:
        """
        Calculate percentage change rate.

        Compares the average of the last `periods` values to the
        average of the first `periods` values.

        Args:
            series: Time series to analyze
            periods: Number of periods to average at each end

        Returns:
            Change rate as a decimal (0.1 = 10% increase)
        """
        values = series.get_values()

        if len(values) < 2:
            return 0.0

        # Adjust periods if series is too short
        periods = min(periods, len(values) // 2)
        if periods < 1:
            periods = 1

        # Calculate averages of first and last periods
        first_avg = sum(values[:periods]) / periods
        last_avg = sum(values[-periods:]) / periods

        # Avoid division by zero
        if first_avg == 0:
            if last_avg == 0:
                return 0.0
            return 1.0  # 100% increase from zero

        return (last_avg - first_avg) / first_avg

    def get_slope(self, series: TimeSeries) -> float:
        """
        Calculate linear regression slope.

        Uses simple linear regression to find the best-fit line
        slope, indicating the average rate of change per time unit.

        Args:
            series: Time series to analyze

        Returns:
            Slope of the linear regression line
        """
        values = series.get_values()
        n = len(values)

        if n < 2:
            return 0.0

        # Simple linear regression using least squares
        # x = [0, 1, 2, ..., n-1]
        # y = values
        x_mean = (n - 1) / 2
        y_mean = sum(values) / n

        numerator = 0.0
        denominator = 0.0

        for i, y in enumerate(values):
            numerator += (i - x_mean) * (y - y_mean)
            denominator += (i - x_mean) ** 2

        if denominator == 0:
            return 0.0

        return numerator / denominator

    def _calculate_volatility(self, values: list[float]) -> float:
        """
        Calculate volatility as coefficient of variation.

        Volatility is measured as standard deviation divided by mean,
        giving a normalized measure of variability.

        Args:
            values: List of numeric values

        Returns:
            Coefficient of variation (0 = no variation, 1 = high variation)
        """
        if len(values) < 2:
            return 0.0

        mean = sum(values) / len(values)
        if mean == 0:
            return 0.0

        # Calculate standard deviation
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std_dev = variance ** 0.5

        # Coefficient of variation
        return std_dev / abs(mean)

    def _calculate_momentum(self, values: list[float]) -> float:
        """
        Calculate momentum as recent change vs average change.

        Momentum measures how the most recent change compares to
        the average change, indicating acceleration or deceleration.

        Args:
            values: List of numeric values

        Returns:
            Momentum value (>1 = accelerating, <1 = decelerating)
        """
        if len(values) < 3:
            return 0.0

        # Recent change (last value vs second-to-last)
        recent_change = values[-1] - values[-2]

        # Average change across all periods
        total_change = values[-1] - values[0]
        avg_change = total_change / (len(values) - 1)

        if avg_change == 0:
            if recent_change == 0:
                return 0.0
            return 1.0 if recent_change > 0 else -1.0

        return recent_change / avg_change

    def _classify_direction(
        self,
        change_rate: float,
        slope: float,
        volatility: float,
    ) -> TrendDirection:
        """
        Classify trend direction based on metrics.

        Uses thresholds to determine if the trend is rising, falling,
        stable, or volatile.

        Args:
            change_rate: Percentage change rate
            slope: Linear regression slope
            volatility: Volatility measure

        Returns:
            TrendDirection classification
        """
        # High volatility takes precedence
        if volatility > self._volatility_threshold:
            # But still check if there's a clear trend despite volatility
            if change_rate > self._rising_threshold * 2:
                return TrendDirection.RISING
            elif change_rate < self._falling_threshold * 2:
                return TrendDirection.FALLING
            return TrendDirection.VOLATILE

        # Classify based on change rate
        if change_rate > self._rising_threshold:
            return TrendDirection.RISING
        elif change_rate < self._falling_threshold:
            return TrendDirection.FALLING
        else:
            return TrendDirection.STABLE

    def classify_direction(self, metrics: TrendMetrics) -> TrendDirection:
        """
        Classify direction from existing metrics.

        Convenience method to re-classify a metrics object.

        Args:
            metrics: TrendMetrics object

        Returns:
            TrendDirection classification
        """
        return self._classify_direction(
            metrics.change_rate,
            metrics.slope,
            metrics.volatility,
        )


@dataclass
class KeywordTrendResult:
    """
    Result of keyword trend analysis.

    Attributes:
        keyword: The analyzed keyword
        series: Time series data for the keyword
        metrics: Trend metrics calculated from the series
        analyzed_at: Timestamp when analysis was performed
    """

    keyword: str
    series: TimeSeries
    metrics: TrendMetrics
    analyzed_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "keyword": self.keyword,
            "series": self.series.to_dict(),
            "metrics": self.metrics.to_dict(),
            "analyzed_at": self.analyzed_at.isoformat(),
        }

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"KeywordTrendResult(keyword='{self.keyword}', "
            f"direction={self.metrics.direction.value}, "
            f"points={len(self.series)})"
        )


@dataclass
class KeywordTrendAnalyzer:
    """
    Analyzer for keyword trends in Reddit posts.

    Combines keyword extraction with time series analysis to track
    how keyword frequencies change over time.

    Attributes:
        keyword_extractor: Extractor for identifying keywords in text
        trend_calculator: Calculator for trend metrics

    Example:
        >>> analyzer = KeywordTrendAnalyzer()
        >>> result = analyzer.analyze_keyword_trend(posts, "python")
        >>> print(result.metrics.direction)
        TrendDirection.RISING
    """

    keyword_extractor: "UnifiedKeywordExtractor | None" = None
    trend_calculator: TrendCalculator | None = None

    def __post_init__(self) -> None:
        """Initialize default components if not provided."""
        if self.trend_calculator is None:
            self.trend_calculator = TrendCalculator()

    def _get_extractor(self) -> "UnifiedKeywordExtractor":
        """Lazy initialization of keyword extractor."""
        if self.keyword_extractor is None:
            from reddit_insight.analysis.keywords import UnifiedKeywordExtractor

            self.keyword_extractor = UnifiedKeywordExtractor()
        return self.keyword_extractor

    def _count_keyword_in_text(self, text: str, keyword: str) -> int:
        """
        Count occurrences of a keyword in text.

        Case-insensitive counting of keyword occurrences.

        Args:
            text: Text to search in
            keyword: Keyword to count

        Returns:
            Number of occurrences
        """
        if not text or not keyword:
            return 0

        # Simple case-insensitive word boundary matching
        text_lower = text.lower()
        keyword_lower = keyword.lower()

        # Count occurrences
        count = 0
        start = 0
        while True:
            pos = text_lower.find(keyword_lower, start)
            if pos == -1:
                break
            count += 1
            start = pos + 1

        return count

    def build_keyword_timeseries(
        self,
        posts: list["Post"],
        keyword: str,
        granularity: TimeGranularity = TimeGranularity.DAY,
    ) -> TimeSeries:
        """
        Build a time series for a specific keyword.

        Counts keyword occurrences in posts and aggregates them
        by the specified time granularity.

        Args:
            posts: List of Post objects to analyze
            keyword: Keyword to track
            granularity: Time unit for aggregation

        Returns:
            TimeSeries with keyword frequency over time
        """
        if not posts:
            return TimeSeries(
                keyword=keyword,
                granularity=granularity,
                points=[],
            )

        # Import defaultdict here to avoid circular imports
        from collections import defaultdict

        # Group posts by time bucket and count keyword occurrences
        bucket_counts: dict[datetime, list[int]] = defaultdict(list)

        for post in posts:
            # Use created_utc for timestamp
            bucket = bucket_timestamp(post.created_utc, granularity)

            # Combine title and selftext for search
            text = post.title
            if post.selftext:
                text = f"{text} {post.selftext}"

            count = self._count_keyword_in_text(text, keyword)
            bucket_counts[bucket].append(count)

        # Convert to time points
        points = []
        for timestamp in sorted(bucket_counts.keys()):
            counts = bucket_counts[timestamp]
            total_count = sum(counts)
            points.append(
                TimePoint(
                    timestamp=timestamp,
                    value=float(total_count),
                    count=len(counts),  # Number of posts in this bucket
                )
            )

        return TimeSeries(
            keyword=keyword,
            granularity=granularity,
            points=points,
        )

    def build_multiple_timeseries(
        self,
        posts: list["Post"],
        keywords: list[str],
        granularity: TimeGranularity = TimeGranularity.DAY,
    ) -> dict[str, TimeSeries]:
        """
        Build time series for multiple keywords.

        Args:
            posts: List of Post objects to analyze
            keywords: List of keywords to track
            granularity: Time unit for aggregation

        Returns:
            Dictionary mapping keywords to their time series
        """
        result = {}
        for keyword in keywords:
            result[keyword] = self.build_keyword_timeseries(
                posts, keyword, granularity
            )
        return result

    def analyze_keyword_trend(
        self,
        posts: list["Post"],
        keyword: str,
        granularity: TimeGranularity = TimeGranularity.DAY,
    ) -> KeywordTrendResult:
        """
        Analyze the trend for a specific keyword.

        Builds a time series and calculates trend metrics for
        the specified keyword.

        Args:
            posts: List of Post objects to analyze
            keyword: Keyword to analyze
            granularity: Time unit for aggregation

        Returns:
            KeywordTrendResult with series and metrics
        """
        # Build time series
        series = self.build_keyword_timeseries(posts, keyword, granularity)

        # Calculate trend metrics
        metrics = self.trend_calculator.calculate_trend(series)

        return KeywordTrendResult(
            keyword=keyword,
            series=series,
            metrics=metrics,
        )

    def analyze_multiple_keywords(
        self,
        posts: list["Post"],
        keywords: list[str],
        granularity: TimeGranularity = TimeGranularity.DAY,
    ) -> list[KeywordTrendResult]:
        """
        Analyze trends for multiple keywords.

        Args:
            posts: List of Post objects to analyze
            keywords: List of keywords to analyze
            granularity: Time unit for aggregation

        Returns:
            List of KeywordTrendResult objects
        """
        results = []
        for keyword in keywords:
            result = self.analyze_keyword_trend(posts, keyword, granularity)
            results.append(result)
        return results

    def find_trending_keywords(
        self,
        posts: list["Post"],
        num_keywords: int = 10,
        granularity: TimeGranularity = TimeGranularity.DAY,
    ) -> list[KeywordTrendResult]:
        """
        Find and analyze the top trending keywords.

        Extracts keywords from posts and analyzes their trends,
        returning results sorted by trend strength.

        Args:
            posts: List of Post objects to analyze
            num_keywords: Number of top keywords to analyze
            granularity: Time unit for aggregation

        Returns:
            List of KeywordTrendResult sorted by change rate
        """
        if not posts:
            return []

        # Extract keywords from all posts
        extractor = self._get_extractor()
        keyword_result = extractor.extract_from_posts(posts, num_keywords=num_keywords * 2)

        # Get top keyword strings
        keywords = [kw.keyword for kw in keyword_result.keywords[:num_keywords * 2]]

        # Analyze each keyword
        results = self.analyze_multiple_keywords(posts, keywords, granularity)

        # Sort by absolute change rate (trending up or down)
        results.sort(key=lambda r: abs(r.metrics.change_rate), reverse=True)

        return results[:num_keywords]
