"""
Rising keyword detection and trend reporting.

Provides tools for detecting rapidly rising keywords,
calculating rising scores, and generating trend reports.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from reddit_insight.analysis.keywords import Keyword, UnifiedKeywordExtractor
    from reddit_insight.analysis.ml.models import AnomalyPoint
    from reddit_insight.reddit.models import Post
    from reddit_insight.storage.database import Database


@dataclass
class RisingScore:
    """
    Rising score for a keyword.

    Attributes:
        keyword: The keyword being scored
        score: Rising score (0-100, higher = more rising)
        growth_rate: Percentage growth rate
        recent_frequency: Count in recent period
        previous_frequency: Count in comparison period
        is_new: Whether this keyword is new (not seen in previous period)
    """

    keyword: str
    score: float
    growth_rate: float
    recent_frequency: int
    previous_frequency: int
    is_new: bool = False

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "keyword": self.keyword,
            "score": self.score,
            "growth_rate": self.growth_rate,
            "recent_frequency": self.recent_frequency,
            "previous_frequency": self.previous_frequency,
            "is_new": self.is_new,
        }

    def __repr__(self) -> str:
        """String representation for debugging."""
        new_marker = " [NEW]" if self.is_new else ""
        return (
            f"RisingScore('{self.keyword}', score={self.score:.1f}, "
            f"growth={self.growth_rate:.0%}{new_marker})"
        )


@dataclass
class RisingKeyword:
    """
    Rising keyword with optional anomaly detection results.

    Extends RisingScore with anomaly detection information for
    identifying unusual patterns in keyword frequency over time.

    Attributes:
        keyword: The keyword being analyzed
        score: Rising score (0-100, higher = more rising)
        growth_rate: Percentage growth rate
        recent_frequency: Count in recent period
        previous_frequency: Count in comparison period
        is_new: Whether this keyword is new (not seen in previous period)
        time_series_values: Historical frequency values (for anomaly detection)
        anomalies: List of detected anomaly points (None if not analyzed)
        has_anomaly: Whether any anomalies were detected

    Example:
        >>> detector = RisingKeywordDetector()
        >>> keywords = detector.detect_with_anomalies(keywords_over_time)
        >>> for kw in keywords:
        ...     if kw.has_anomaly:
        ...         print(f"{kw.keyword} has unusual activity!")
    """

    keyword: str
    score: float
    growth_rate: float
    recent_frequency: int
    previous_frequency: int
    is_new: bool = False
    time_series_values: list[float] = field(default_factory=list)
    anomalies: list[AnomalyPoint] | None = None
    has_anomaly: bool = False

    @classmethod
    def from_rising_score(
        cls,
        rising_score: RisingScore,
        time_series_values: list[float] | None = None,
        anomalies: list[AnomalyPoint] | None = None,
    ) -> RisingKeyword:
        """
        Create RisingKeyword from a RisingScore.

        Args:
            rising_score: Source RisingScore object
            time_series_values: Historical frequency values
            anomalies: List of detected anomaly points

        Returns:
            RisingKeyword with anomaly information
        """
        return cls(
            keyword=rising_score.keyword,
            score=rising_score.score,
            growth_rate=rising_score.growth_rate,
            recent_frequency=rising_score.recent_frequency,
            previous_frequency=rising_score.previous_frequency,
            is_new=rising_score.is_new,
            time_series_values=time_series_values or [],
            anomalies=anomalies,
            has_anomaly=bool(anomalies and len(anomalies) > 0),
        )

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        result = {
            "keyword": self.keyword,
            "score": self.score,
            "growth_rate": self.growth_rate,
            "recent_frequency": self.recent_frequency,
            "previous_frequency": self.previous_frequency,
            "is_new": self.is_new,
            "has_anomaly": self.has_anomaly,
        }
        if self.anomalies:
            result["anomalies"] = [a.to_dict() for a in self.anomalies]
        return result

    def __repr__(self) -> str:
        """String representation for debugging."""
        new_marker = " [NEW]" if self.is_new else ""
        anomaly_marker = " [ANOMALY]" if self.has_anomaly else ""
        return (
            f"RisingKeyword('{self.keyword}', score={self.score:.1f}, "
            f"growth={self.growth_rate:.0%}{new_marker}{anomaly_marker})"
        )


@dataclass
class RisingConfig:
    """
    Configuration for rising keyword detection.

    Attributes:
        recent_period_hours: Duration of the recent period in hours
        comparison_period_hours: Duration of the comparison period in hours
        min_recent_frequency: Minimum frequency in recent period to qualify
        min_growth_rate: Minimum growth rate to be considered rising (0.5 = 50%)
        new_keyword_bonus: Bonus points for new keywords (0-100 scale)
    """

    recent_period_hours: int = 24
    comparison_period_hours: int = 168  # 1 week
    min_recent_frequency: int = 3
    min_growth_rate: float = 0.5  # 50% increase minimum
    new_keyword_bonus: float = 20.0


@dataclass
class RisingScoreCalculator:
    """
    Calculator for rising keyword scores.

    Calculates a normalized score (0-100) indicating how rapidly
    a keyword is rising based on frequency changes over time.

    Attributes:
        config: Configuration for score calculation

    Example:
        >>> calc = RisingScoreCalculator()
        >>> score = calc.calculate_score(recent_freq=10, previous_freq=2)
        >>> print(f"Score: {score.score:.1f}, Growth: {score.growth_rate:.0%}")
    """

    config: RisingConfig = field(default_factory=RisingConfig)

    def _growth_rate(self, recent: int, previous: int) -> float:
        """
        Calculate growth rate between periods.

        Handles division by zero by treating previous=0 as a new keyword
        with maximum growth rate.

        Args:
            recent: Recent period frequency
            previous: Previous period frequency

        Returns:
            Growth rate as a decimal (1.0 = 100% increase)
        """
        if previous == 0:
            # New keyword - treat as 100% growth if recent > 0
            return 1.0 if recent > 0 else 0.0

        return (recent - previous) / previous

    def _normalize_score(self, growth_rate: float, frequency: int) -> float:
        """
        Normalize growth rate and frequency to a 0-100 score.

        The score is based on:
        - Growth rate (capped at 500% for normalization)
        - Absolute frequency (log-scaled to prevent outlier dominance)

        Args:
            growth_rate: Percentage growth rate (1.0 = 100%)
            frequency: Recent period frequency

        Returns:
            Normalized score between 0 and 100
        """
        import math

        # Cap growth rate for normalization (500% max)
        capped_growth = min(growth_rate, 5.0)

        # Growth component (0-50 points)
        # 100% growth = 10 points, 500% growth = 50 points
        growth_score = capped_growth * 10

        # Frequency component (0-50 points)
        # Log scale: freq 1 = ~0, freq 10 = ~23, freq 100 = ~46, freq 1000 = ~69
        # We cap at 50 points
        freq_score = min(math.log10(max(frequency, 1) + 1) * 23, 50)

        # Combined score
        raw_score = growth_score + freq_score

        # Normalize to 0-100
        return min(max(raw_score, 0), 100)

    def calculate_score(
        self,
        recent_freq: int,
        previous_freq: int,
        keyword: str = "",
        is_new: bool | None = None,
    ) -> RisingScore:
        """
        Calculate rising score for a keyword.

        Args:
            recent_freq: Frequency in recent period
            previous_freq: Frequency in comparison period
            keyword: The keyword string (optional, for labeling)
            is_new: Whether this is a new keyword (auto-detect if None)

        Returns:
            RisingScore with calculated metrics
        """
        # Determine if keyword is new
        if is_new is None:
            is_new = previous_freq == 0 and recent_freq > 0

        # Calculate growth rate
        growth_rate = self._growth_rate(recent_freq, previous_freq)

        # Calculate base score
        score = self._normalize_score(growth_rate, recent_freq)

        # Apply new keyword bonus
        if is_new and recent_freq >= self.config.min_recent_frequency:
            score = min(score + self.config.new_keyword_bonus, 100)

        return RisingScore(
            keyword=keyword,
            score=score,
            growth_rate=growth_rate,
            recent_frequency=recent_freq,
            previous_frequency=previous_freq,
            is_new=is_new,
        )


@dataclass
class RisingKeywordDetector:
    """
    Detector for rapidly rising keywords in Reddit posts.

    Analyzes posts over time to identify keywords that are
    showing significant growth in frequency.

    Attributes:
        keyword_extractor: Extractor for identifying keywords
        config: Configuration for rising detection

    Example:
        >>> detector = RisingKeywordDetector()
        >>> rising = detector.detect_rising(posts, top_n=10)
        >>> for score in rising:
        ...     print(f"{score.keyword}: {score.score:.1f}")
    """

    keyword_extractor: UnifiedKeywordExtractor | None = None
    config: RisingConfig = field(default_factory=RisingConfig)
    _calculator: RisingScoreCalculator = field(init=False, repr=False)

    def __post_init__(self) -> None:
        """Initialize calculator with config."""
        self._calculator = RisingScoreCalculator(config=self.config)

    def _get_extractor(self) -> UnifiedKeywordExtractor:
        """Lazy initialization of keyword extractor."""
        if self.keyword_extractor is None:
            from reddit_insight.analysis.keywords import UnifiedKeywordExtractor

            self.keyword_extractor = UnifiedKeywordExtractor()
        return self.keyword_extractor

    def _filter_by_time(
        self,
        posts: list[Post],
        start: datetime,
        end: datetime,
    ) -> list[Post]:
        """
        Filter posts by time range.

        Args:
            posts: List of posts to filter
            start: Start of time range (inclusive)
            end: End of time range (exclusive)

        Returns:
            Posts within the time range
        """
        filtered = []
        for post in posts:
            if start <= post.created_utc < end:
                filtered.append(post)
        return filtered

    def _count_keywords_in_period(
        self,
        posts: list[Post],
        start: datetime,
        end: datetime,
    ) -> dict[str, int]:
        """
        Count keyword frequencies in a time period.

        Extracts keywords from posts within the time range
        and counts their occurrences.

        Args:
            posts: List of posts to analyze
            start: Start of time range
            end: End of time range

        Returns:
            Dictionary mapping keywords to their frequency
        """
        # Filter posts to time period
        period_posts = self._filter_by_time(posts, start, end)

        if not period_posts:
            return {}

        # Extract keywords from posts
        extractor = self._get_extractor()
        result = extractor.extract_from_posts(
            period_posts,
            num_keywords=100,  # Get many keywords for comparison
        )

        # Count frequencies
        freq_map: dict[str, int] = {}
        for kw in result.keywords:
            # Use frequency if available, otherwise count as 1
            count = kw.frequency if kw.frequency is not None else 1
            freq_map[kw.keyword.lower()] = count

        return freq_map

    def _filter_rising(self, scores: list[RisingScore]) -> list[RisingScore]:
        """
        Filter scores by rising thresholds.

        Removes keywords that don't meet the minimum criteria
        for being considered "rising".

        Args:
            scores: List of rising scores to filter

        Returns:
            Filtered list meeting threshold requirements
        """
        filtered = []
        for score in scores:
            # Check minimum frequency
            if score.recent_frequency < self.config.min_recent_frequency:
                continue

            # Check minimum growth rate (except for new keywords)
            if not score.is_new and score.growth_rate < self.config.min_growth_rate:
                continue

            filtered.append(score)

        return filtered

    def detect_rising(
        self,
        posts: list[Post],
        top_n: int = 20,
        reference_time: datetime | None = None,
    ) -> list[RisingScore]:
        """
        Detect rising keywords from posts.

        Compares keyword frequencies between recent and
        comparison periods to identify rising keywords.

        Args:
            posts: List of posts to analyze
            top_n: Number of top rising keywords to return
            reference_time: Reference point for time periods (default: now)

        Returns:
            List of RisingScore objects sorted by score (highest first)
        """
        if not posts:
            return []

        # Use reference time or now
        if reference_time is None:
            reference_time = datetime.now(UTC)

        # Calculate time periods
        recent_end = reference_time
        recent_start = recent_end - timedelta(hours=self.config.recent_period_hours)
        comparison_end = recent_start
        comparison_start = comparison_end - timedelta(
            hours=self.config.comparison_period_hours
        )

        # Count keywords in each period
        recent_counts = self._count_keywords_in_period(posts, recent_start, recent_end)
        previous_counts = self._count_keywords_in_period(
            posts, comparison_start, comparison_end
        )

        # Calculate scores for all keywords
        all_keywords = set(recent_counts.keys()) | set(previous_counts.keys())
        scores = []

        for keyword in all_keywords:
            recent_freq = recent_counts.get(keyword, 0)
            previous_freq = previous_counts.get(keyword, 0)

            # Skip if not present in recent period
            if recent_freq == 0:
                continue

            score = self._calculator.calculate_score(
                recent_freq=recent_freq,
                previous_freq=previous_freq,
                keyword=keyword,
            )
            scores.append(score)

        # Filter by thresholds
        filtered = self._filter_rising(scores)

        # Sort by score (highest first)
        filtered.sort(key=lambda s: s.score, reverse=True)

        return filtered[:top_n]

    def detect_from_database(
        self,
        database: Database,
        subreddit: str | None = None,
        top_n: int = 20,
    ) -> list[RisingScore]:
        """
        Detect rising keywords directly from database.

        Queries the database for posts and analyzes them
        for rising keywords.

        Args:
            database: Database instance to query
            subreddit: Optional subreddit filter
            top_n: Number of top rising keywords to return

        Returns:
            List of RisingScore objects sorted by score
        """
        # Query posts from database
        # Calculate time window that covers both periods
        now = datetime.now(UTC)
        total_hours = self.config.recent_period_hours + self.config.comparison_period_hours
        start_time = now - timedelta(hours=total_hours)

        # Query posts - use database-specific query if available
        posts = database.get_posts(
            subreddit=subreddit,
            since=start_time,
        )

        return self.detect_rising(posts, top_n=top_n, reference_time=now)

    def detect_with_anomalies(
        self,
        keywords_over_time: dict[str, list[float]],
        top_n: int = 20,
    ) -> list[RisingKeyword]:
        """
        Detect rising keywords with anomaly analysis.

        Analyzes keyword frequency time series to identify both rising
        keywords and anomalous patterns (unusual spikes or drops).

        This method takes pre-computed keyword frequencies over time
        rather than raw posts, making it suitable for pre-aggregated data.

        Args:
            keywords_over_time: Dictionary mapping keyword to list of
                frequency values over time (oldest to newest)
            top_n: Number of top rising keywords to return

        Returns:
            List of RisingKeyword objects with anomaly information

        Example:
            >>> keywords_over_time = {
            ...     'python': [10, 12, 11, 13, 50, 14, 12],  # spike at index 4
            ...     'javascript': [5, 6, 5, 6, 5, 6, 5],     # stable
            ... }
            >>> results = detector.detect_with_anomalies(keywords_over_time)
            >>> for kw in results:
            ...     if kw.has_anomaly:
            ...         print(f"{kw.keyword}: anomalies detected!")
        """
        from reddit_insight.analysis.ml.anomaly_detector import (
            AnomalyDetector,
            AnomalyDetectorConfig,
        )
        from reddit_insight.analysis.time_series import (
            TimeGranularity,
            TimePoint,
            TimeSeries,
        )

        # Lazy initialize anomaly detector
        # Use threshold=2.5 for more sensitive anomaly detection
        # (default 3.0 is too strict for small time series)
        anomaly_detector = AnomalyDetector(
            AnomalyDetectorConfig(method="auto", min_data_points=5, threshold=2.5)
        )

        results: list[RisingKeyword] = []

        for keyword, values in keywords_over_time.items():
            if not values or len(values) < 2:
                continue

            # Calculate rising score from recent vs previous
            # Split time series: first half = previous, second half = recent
            mid_point = len(values) // 2
            previous_values = values[:mid_point]
            recent_values = values[mid_point:]

            previous_freq = int(sum(previous_values))
            recent_freq = int(sum(recent_values))

            # Calculate rising score
            rising_score = self._calculator.calculate_score(
                recent_freq=recent_freq,
                previous_freq=previous_freq,
                keyword=keyword,
            )

            # Detect anomalies if enough data
            detected_anomalies = None
            if len(values) >= 5:
                # Create TimeSeries for anomaly detection
                now = datetime.now(UTC)
                points = [
                    TimePoint(
                        timestamp=now - timedelta(hours=len(values) - i),
                        value=float(val),
                    )
                    for i, val in enumerate(values)
                ]
                ts = TimeSeries(
                    keyword=keyword,
                    granularity=TimeGranularity.HOUR,
                    points=points,
                )

                # Detect anomalies
                anomaly_result = anomaly_detector.detect(ts)
                detected_anomalies = anomaly_result.detected_anomalies

            # Create RisingKeyword with anomaly info
            rising_keyword = RisingKeyword.from_rising_score(
                rising_score=rising_score,
                time_series_values=values,
                anomalies=detected_anomalies if detected_anomalies else None,
            )
            results.append(rising_keyword)

        # Filter by thresholds (convert to RisingScore for filtering)
        filtered_scores = self._filter_rising([
            RisingScore(
                keyword=rk.keyword,
                score=rk.score,
                growth_rate=rk.growth_rate,
                recent_frequency=rk.recent_frequency,
                previous_frequency=rk.previous_frequency,
                is_new=rk.is_new,
            )
            for rk in results
        ])
        filtered_keywords = {rs.keyword for rs in filtered_scores}

        # Keep only filtered results
        results = [rk for rk in results if rk.keyword in filtered_keywords]

        # Sort by score (highest first)
        results.sort(key=lambda rk: rk.score, reverse=True)

        return results[:top_n]


@dataclass
class TrendReport:
    """
    Comprehensive trend report for a time period.

    Combines rising keywords with top keywords to provide
    a complete picture of trends.

    Attributes:
        generated_at: When the report was generated
        period_start: Start of the analysis period
        period_end: End of the analysis period
        subreddit: Subreddit filter (None = all)
        rising_keywords: List of rising keyword scores
        top_keywords: List of top keywords by frequency
        total_posts_analyzed: Number of posts included in analysis
    """

    generated_at: datetime
    period_start: datetime
    period_end: datetime
    subreddit: str | None
    rising_keywords: list[RisingScore]
    top_keywords: list[Keyword]
    total_posts_analyzed: int

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "generated_at": self.generated_at.isoformat(),
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "subreddit": self.subreddit,
            "rising_keywords": [rs.to_dict() for rs in self.rising_keywords],
            "top_keywords": [
                {"keyword": kw.keyword, "score": kw.score}
                for kw in self.top_keywords
            ],
            "total_posts_analyzed": self.total_posts_analyzed,
        }


@dataclass
class TrendReporter:
    """
    Generator for comprehensive trend reports.

    Combines rising keyword detection with top keyword extraction
    to create detailed trend reports.

    Attributes:
        rising_detector: Detector for rising keywords
        keyword_extractor: Extractor for top keywords

    Example:
        >>> reporter = TrendReporter()
        >>> report = reporter.generate_report(posts)
        >>> print(reporter.to_markdown(report))
    """

    rising_detector: RisingKeywordDetector | None = None
    keyword_extractor: UnifiedKeywordExtractor | None = None

    def _get_detector(self) -> RisingKeywordDetector:
        """Lazy initialization of rising detector."""
        if self.rising_detector is None:
            self.rising_detector = RisingKeywordDetector()
        return self.rising_detector

    def _get_extractor(self) -> UnifiedKeywordExtractor:
        """Lazy initialization of keyword extractor."""
        if self.keyword_extractor is None:
            from reddit_insight.analysis.keywords import UnifiedKeywordExtractor

            self.keyword_extractor = UnifiedKeywordExtractor()
        return self.keyword_extractor

    def generate_report(
        self,
        posts: list[Post],
        subreddit: str | None = None,
        num_rising: int = 10,
        num_top: int = 20,
    ) -> TrendReport:
        """
        Generate a comprehensive trend report.

        Analyzes posts to identify both rising and top keywords.

        Args:
            posts: List of posts to analyze
            subreddit: Subreddit name for labeling (None = all)
            num_rising: Number of rising keywords to include
            num_top: Number of top keywords to include

        Returns:
            TrendReport with analysis results
        """
        now = datetime.now(UTC)
        detector = self._get_detector()
        extractor = self._get_extractor()

        # Detect rising keywords
        rising = detector.detect_rising(posts, top_n=num_rising, reference_time=now)

        # Extract top keywords
        result = extractor.extract_from_posts(posts, num_keywords=num_top)
        top_keywords = result.keywords

        # Calculate period boundaries
        config = detector.config
        period_end = now
        period_start = now - timedelta(
            hours=config.recent_period_hours + config.comparison_period_hours
        )

        return TrendReport(
            generated_at=now,
            period_start=period_start,
            period_end=period_end,
            subreddit=subreddit,
            rising_keywords=rising,
            top_keywords=top_keywords,
            total_posts_analyzed=len(posts),
        )

    def to_dict(self, report: TrendReport) -> dict:
        """
        Convert report to JSON-serializable dictionary.

        Args:
            report: TrendReport to convert

        Returns:
            Dictionary representation
        """
        return report.to_dict()

    def to_markdown(self, report: TrendReport) -> str:
        """
        Convert report to markdown format.

        Creates a human-readable markdown document
        summarizing the trend report.

        Args:
            report: TrendReport to format

        Returns:
            Markdown-formatted string
        """
        lines = []

        # Header
        lines.append("# Trend Report")
        lines.append("")

        # Metadata
        lines.append("## Overview")
        lines.append("")
        lines.append(f"- **Generated**: {report.generated_at.strftime('%Y-%m-%d %H:%M UTC')}")
        lines.append(f"- **Period**: {report.period_start.strftime('%Y-%m-%d')} to {report.period_end.strftime('%Y-%m-%d')}")
        if report.subreddit:
            lines.append(f"- **Subreddit**: r/{report.subreddit}")
        lines.append(f"- **Posts Analyzed**: {report.total_posts_analyzed:,}")
        lines.append("")

        # Rising keywords
        lines.append("## Rising Keywords")
        lines.append("")
        if report.rising_keywords:
            lines.append("| Rank | Keyword | Score | Growth | Recent | Previous | New |")
            lines.append("|------|---------|-------|--------|--------|----------|-----|")
            for i, rs in enumerate(report.rising_keywords, 1):
                new_marker = "Yes" if rs.is_new else "No"
                growth_str = f"{rs.growth_rate:+.0%}" if not rs.is_new else "N/A"
                lines.append(
                    f"| {i} | {rs.keyword} | {rs.score:.1f} | "
                    f"{growth_str} | {rs.recent_frequency} | "
                    f"{rs.previous_frequency} | {new_marker} |"
                )
        else:
            lines.append("_No rising keywords detected._")
        lines.append("")

        # Top keywords
        lines.append("## Top Keywords")
        lines.append("")
        if report.top_keywords:
            lines.append("| Rank | Keyword | Score |")
            lines.append("|------|---------|-------|")
            for i, kw in enumerate(report.top_keywords[:10], 1):
                lines.append(f"| {i} | {kw.keyword} | {kw.score:.3f} |")
        else:
            lines.append("_No keywords extracted._")
        lines.append("")

        # Summary
        lines.append("## Summary")
        lines.append("")
        lines.append(self._summarize_trends(report))
        lines.append("")

        return "\n".join(lines)

    def _summarize_trends(self, report: TrendReport) -> str:
        """
        Generate a text summary of trends.

        Args:
            report: TrendReport to summarize

        Returns:
            Summary paragraph
        """
        parts = []

        # Rising keywords summary
        rising_count = len(report.rising_keywords)
        new_count = sum(1 for rs in report.rising_keywords if rs.is_new)

        if rising_count > 0:
            top_rising = report.rising_keywords[0].keyword if report.rising_keywords else None
            parts.append(
                f"Detected {rising_count} rising keywords"
                f"{f', including {new_count} new keywords' if new_count > 0 else ''}."
            )
            if top_rising:
                parts.append(f"The fastest rising keyword is '{top_rising}'.")
        else:
            parts.append("No significant rising trends detected in this period.")

        # Top keywords summary
        if report.top_keywords:
            top_kw = report.top_keywords[0].keyword
            parts.append(f"The most prominent keyword overall is '{top_kw}'.")

        return " ".join(parts)
