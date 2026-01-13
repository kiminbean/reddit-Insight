"""
Time series data structures for trend analysis.

Provides data structures for representing and manipulating time-based
keyword frequency data with support for multiple time granularities.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


class TimeGranularity(Enum):
    """
    Time granularity for time series aggregation.

    Attributes:
        HOUR: Hourly aggregation
        DAY: Daily aggregation
        WEEK: Weekly aggregation
        MONTH: Monthly aggregation
    """

    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


@dataclass
class TimePoint:
    """
    A single point in a time series.

    Attributes:
        timestamp: The timestamp for this point
        value: The numeric value (e.g., frequency, score)
        count: Optional count of items aggregated
    """

    timestamp: datetime
    value: float
    count: int | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        result = {
            "timestamp": self.timestamp.isoformat(),
            "value": self.value,
        }
        if self.count is not None:
            result["count"] = self.count
        return result


@dataclass
class TimeSeries:
    """
    Time series data for a keyword.

    Represents the temporal evolution of a keyword's frequency
    or other metric over a specified time period.

    Attributes:
        keyword: The keyword being tracked
        granularity: Time unit for aggregation
        points: List of time points
        start_time: Start of the time range
        end_time: End of the time range

    Example:
        >>> from datetime import datetime, UTC
        >>> points = [
        ...     TimePoint(datetime(2024, 1, 1, tzinfo=UTC), 5.0, 5),
        ...     TimePoint(datetime(2024, 1, 2, tzinfo=UTC), 8.0, 8),
        ... ]
        >>> series = TimeSeries(
        ...     keyword="python",
        ...     granularity=TimeGranularity.DAY,
        ...     points=points,
        ...     start_time=datetime(2024, 1, 1, tzinfo=UTC),
        ...     end_time=datetime(2024, 1, 2, tzinfo=UTC),
        ... )
        >>> print(series.get_values())
        [5.0, 8.0]
    """

    keyword: str
    granularity: TimeGranularity
    points: list[TimePoint] = field(default_factory=list)
    start_time: datetime | None = None
    end_time: datetime | None = None

    def __post_init__(self) -> None:
        """Initialize start/end times from points if not provided."""
        if self.points and self.start_time is None:
            self.start_time = min(p.timestamp for p in self.points)
        if self.points and self.end_time is None:
            self.end_time = max(p.timestamp for p in self.points)

    def get_values(self) -> list[float]:
        """
        Get all values as a list.

        Returns:
            List of values in chronological order
        """
        return [p.value for p in self.points]

    def get_timestamps(self) -> list[datetime]:
        """
        Get all timestamps as a list.

        Returns:
            List of timestamps in chronological order
        """
        return [p.timestamp for p in self.points]

    def get_counts(self) -> list[int | None]:
        """
        Get all counts as a list.

        Returns:
            List of counts in chronological order
        """
        return [p.count for p in self.points]

    def to_dict(self) -> dict:
        """
        Convert to dictionary representation.

        Returns:
            Dictionary with all time series data
        """
        return {
            "keyword": self.keyword,
            "granularity": self.granularity.value,
            "points": [p.to_dict() for p in self.points],
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
        }

    def to_dataframe(self) -> "pd.DataFrame":
        """
        Convert to pandas DataFrame.

        Requires pandas to be installed.

        Returns:
            DataFrame with timestamp index and value/count columns

        Raises:
            ImportError: If pandas is not installed
        """
        try:
            import pandas as pd
        except ImportError as e:
            raise ImportError(
                "pandas is required for to_dataframe(). "
                "Install it with: pip install pandas"
            ) from e

        data = {
            "timestamp": self.get_timestamps(),
            "value": self.get_values(),
            "count": self.get_counts(),
        }
        df = pd.DataFrame(data)
        df.set_index("timestamp", inplace=True)
        return df

    def __len__(self) -> int:
        """Return the number of time points."""
        return len(self.points)

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"TimeSeries(keyword='{self.keyword}', "
            f"granularity={self.granularity.value}, "
            f"points={len(self.points)})"
        )


def bucket_timestamp(dt: datetime, granularity: TimeGranularity) -> datetime:
    """
    Bucket a timestamp to the start of its time period.

    Rounds down the timestamp to the beginning of the specified
    time unit for aggregation purposes.

    Args:
        dt: The datetime to bucket
        granularity: The time granularity to bucket to

    Returns:
        Datetime rounded down to the start of the period

    Example:
        >>> from datetime import datetime, UTC
        >>> dt = datetime(2024, 1, 15, 14, 30, 45, tzinfo=UTC)
        >>> bucket_timestamp(dt, TimeGranularity.HOUR)
        datetime.datetime(2024, 1, 15, 14, 0, tzinfo=datetime.timezone.utc)
        >>> bucket_timestamp(dt, TimeGranularity.DAY)
        datetime.datetime(2024, 1, 15, 0, 0, tzinfo=datetime.timezone.utc)
    """
    if granularity == TimeGranularity.HOUR:
        # Round down to the start of the hour
        return dt.replace(minute=0, second=0, microsecond=0)

    elif granularity == TimeGranularity.DAY:
        # Round down to the start of the day
        return dt.replace(hour=0, minute=0, second=0, microsecond=0)

    elif granularity == TimeGranularity.WEEK:
        # Round down to the start of the week (Monday)
        # weekday() returns 0 for Monday, 6 for Sunday
        days_since_monday = dt.weekday()
        week_start = dt - timedelta(days=days_since_monday)
        return week_start.replace(hour=0, minute=0, second=0, microsecond=0)

    elif granularity == TimeGranularity.MONTH:
        # Round down to the start of the month
        return dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    else:
        raise ValueError(f"Unknown granularity: {granularity}")


def get_time_delta(granularity: TimeGranularity) -> timedelta:
    """
    Get the timedelta for a given granularity.

    Note: MONTH returns 30 days as an approximation.

    Args:
        granularity: The time granularity

    Returns:
        Approximate timedelta for the granularity
    """
    if granularity == TimeGranularity.HOUR:
        return timedelta(hours=1)
    elif granularity == TimeGranularity.DAY:
        return timedelta(days=1)
    elif granularity == TimeGranularity.WEEK:
        return timedelta(weeks=1)
    elif granularity == TimeGranularity.MONTH:
        return timedelta(days=30)  # Approximation
    else:
        raise ValueError(f"Unknown granularity: {granularity}")
