"""
ML Analyzer base classes for advanced analytics.

Provides abstract base classes and common data structures for machine learning
based analysis including time series prediction, anomaly detection, clustering,
and topic modeling.

Example:
    >>> from reddit_insight.analysis.ml import MLAnalyzerBase, AnalysisResult
    >>> class MyAnalyzer(MLAnalyzerBase):
    ...     def analyze(self, data):
    ...         return AnalysisResult(result_type="custom", data={"value": 1})
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    pass


ResultType = Literal["prediction", "anomaly", "cluster", "topic"]


@dataclass
class AnalysisMetadata:
    """
    Metadata for analysis results.

    Attributes:
        analyzed_at: Timestamp when analysis was performed
        data_size: Number of data points analyzed
        processing_time_ms: Time taken to process in milliseconds
        analyzer_name: Name of the analyzer that produced the result
        analyzer_version: Version of the analyzer
        parameters: Parameters used for the analysis
    """

    analyzed_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    data_size: int = 0
    processing_time_ms: float = 0.0
    analyzer_name: str = ""
    analyzer_version: str = "1.0.0"
    parameters: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "analyzed_at": self.analyzed_at.isoformat(),
            "data_size": self.data_size,
            "processing_time_ms": self.processing_time_ms,
            "analyzer_name": self.analyzer_name,
            "analyzer_version": self.analyzer_version,
            "parameters": self.parameters,
        }


@dataclass
class AnalysisResult:
    """
    Common structure for ML analysis results.

    Provides a unified interface for all types of ML analysis results,
    including predictions, anomaly detection, clustering, and topic modeling.

    Attributes:
        result_type: Type of analysis result (prediction, anomaly, cluster, topic)
        data: The actual result data, structure depends on result_type
        metadata: Analysis metadata (timing, parameters, etc.)
        confidence: Overall confidence score (0-1)
        success: Whether the analysis completed successfully
        error_message: Error message if analysis failed

    Example:
        >>> result = AnalysisResult(
        ...     result_type="prediction",
        ...     data={"values": [1.0, 2.0, 3.0]},
        ...     confidence=0.85
        ... )
        >>> print(result.confidence)
        0.85
    """

    result_type: ResultType
    data: dict[str, Any] = field(default_factory=dict)
    metadata: AnalysisMetadata = field(default_factory=AnalysisMetadata)
    confidence: float = 0.0
    success: bool = True
    error_message: str | None = None

    def __post_init__(self) -> None:
        """Validate result after initialization."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be between 0 and 1, got {self.confidence}")

        valid_types = {"prediction", "anomaly", "cluster", "topic"}
        if self.result_type not in valid_types:
            raise ValueError(f"result_type must be one of {valid_types}, got {self.result_type}")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "result_type": self.result_type,
            "data": self.data,
            "metadata": self.metadata.to_dict(),
            "confidence": self.confidence,
            "success": self.success,
            "error_message": self.error_message,
        }

    def is_successful(self) -> bool:
        """Check if analysis completed successfully."""
        return self.success and self.error_message is None


@dataclass
class MLAnalyzerConfig:
    """
    Base configuration for ML analyzers.

    Provides common configuration options that apply to all ML analyzers.
    Subclasses should extend this with analyzer-specific options.

    Attributes:
        name: Name of the analyzer
        version: Version string
        verbose: Whether to print progress information
        random_state: Random seed for reproducibility
    """

    name: str = "MLAnalyzer"
    version: str = "1.0.0"
    verbose: bool = False
    random_state: int | None = 42


class MLAnalyzerBase(ABC):
    """
    Abstract base class for all ML analyzers.

    Provides the common interface and shared functionality for machine learning
    based analysis tools. All concrete analyzers should inherit from this class.

    Attributes:
        config: Configuration for the analyzer

    Example:
        >>> class TimeSeriesPredictor(MLAnalyzerBase):
        ...     def analyze(self, data):
        ...         # Implement prediction logic
        ...         return AnalysisResult(result_type="prediction", data={})
        ...
        ...     def fit(self, data):
        ...         # Train model
        ...         pass
    """

    def __init__(self, config: MLAnalyzerConfig | None = None) -> None:
        """
        Initialize the analyzer.

        Args:
            config: Configuration for the analyzer, uses defaults if None
        """
        self.config = config or MLAnalyzerConfig()
        self._is_fitted: bool = False

    @abstractmethod
    def analyze(self, data: Any) -> AnalysisResult:
        """
        Perform analysis on the provided data.

        Args:
            data: Input data to analyze, format depends on analyzer type

        Returns:
            AnalysisResult containing the analysis output
        """
        pass

    def fit(self, data: Any) -> None:
        """
        Fit the analyzer to training data.

        Optional method for stateful analyzers that need to learn from data.
        By default, this is a no-op. Override for analyzers that need training.

        Args:
            data: Training data to fit on
        """
        self._is_fitted = True

    def fit_analyze(self, data: Any) -> AnalysisResult:
        """
        Fit and analyze in one step.

        Convenience method that calls fit() then analyze().

        Args:
            data: Data to fit and analyze

        Returns:
            AnalysisResult from the analysis
        """
        self.fit(data)
        return self.analyze(data)

    @property
    def is_fitted(self) -> bool:
        """Check if the analyzer has been fitted."""
        return self._is_fitted

    def _create_metadata(
        self,
        data_size: int,
        processing_time_ms: float,
        parameters: dict[str, Any] | None = None,
    ) -> AnalysisMetadata:
        """
        Create metadata for analysis results.

        Helper method to generate consistent metadata across all analyzers.

        Args:
            data_size: Number of data points analyzed
            processing_time_ms: Processing time in milliseconds
            parameters: Additional parameters to include

        Returns:
            AnalysisMetadata with filled values
        """
        return AnalysisMetadata(
            analyzed_at=datetime.now(UTC),
            data_size=data_size,
            processing_time_ms=processing_time_ms,
            analyzer_name=self.config.name,
            analyzer_version=self.config.version,
            parameters=parameters or {},
        )

    def _create_error_result(
        self,
        result_type: ResultType,
        error_message: str,
    ) -> AnalysisResult:
        """
        Create an error result for failed analysis.

        Helper method to generate consistent error responses.

        Args:
            result_type: Type of analysis that failed
            error_message: Description of what went wrong

        Returns:
            AnalysisResult with success=False and error details
        """
        return AnalysisResult(
            result_type=result_type,
            data={},
            metadata=self._create_metadata(0, 0.0),
            confidence=0.0,
            success=False,
            error_message=error_message,
        )
