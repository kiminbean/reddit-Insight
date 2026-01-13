"""
ML Analysis result data models.

Provides specific data models for different types of ML analysis results:
- PredictionResult: Time series prediction results
- AnomalyResult: Anomaly detection results
- ClusterResult: Clustering analysis results
- TopicResult: Topic modeling results

Example:
    >>> from reddit_insight.analysis.ml.models import PredictionResult
    >>> result = PredictionResult(
    ...     timestamps=[datetime.now()],
    ...     values=[1.0],
    ...     model_name="ARIMA"
    ... )
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class PredictionResult:
    """
    Result of time series prediction.

    Contains predicted values with confidence intervals and model metrics.

    Attributes:
        timestamps: List of prediction timestamps
        values: Predicted values at each timestamp
        lower_bound: Lower confidence interval bound
        upper_bound: Upper confidence interval bound
        confidence_level: Confidence level for intervals (e.g., 0.95 for 95%)
        model_name: Name of the model used (e.g., "ARIMA", "ExponentialSmoothing")
        metrics: Model performance metrics (MAE, RMSE, MAPE, etc.)
        fitted_values: Values fitted to training data (if available)
        residuals: Model residuals (if available)

    Example:
        >>> result = PredictionResult(
        ...     timestamps=[datetime(2024, 1, 1), datetime(2024, 1, 2)],
        ...     values=[10.5, 12.3],
        ...     lower_bound=[8.0, 10.0],
        ...     upper_bound=[13.0, 14.6],
        ...     confidence_level=0.95,
        ...     model_name="ARIMA(1,1,1)"
        ... )
    """

    timestamps: list[datetime]
    values: list[float]
    lower_bound: list[float] = field(default_factory=list)
    upper_bound: list[float] = field(default_factory=list)
    confidence_level: float = 0.95
    model_name: str = "Unknown"
    metrics: dict[str, float] = field(default_factory=dict)
    fitted_values: list[float] = field(default_factory=list)
    residuals: list[float] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate prediction result."""
        if len(self.timestamps) != len(self.values):
            raise ValueError(
                f"timestamps ({len(self.timestamps)}) and values ({len(self.values)}) "
                "must have the same length"
            )

        if self.lower_bound and len(self.lower_bound) != len(self.values):
            raise ValueError("lower_bound must have same length as values")

        if self.upper_bound and len(self.upper_bound) != len(self.values):
            raise ValueError("upper_bound must have same length as values")

    @property
    def n_predictions(self) -> int:
        """Number of predictions."""
        return len(self.values)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "timestamps": [ts.isoformat() for ts in self.timestamps],
            "values": self.values,
            "lower_bound": self.lower_bound,
            "upper_bound": self.upper_bound,
            "confidence_level": self.confidence_level,
            "model_name": self.model_name,
            "metrics": self.metrics,
            "n_predictions": self.n_predictions,
        }


@dataclass
class AnomalyPoint:
    """
    A single point that may be an anomaly.

    Attributes:
        timestamp: When the data point occurred
        value: The observed value
        anomaly_score: Score indicating anomaly likelihood (higher = more anomalous)
        is_anomaly: Whether this point is classified as an anomaly
        expected_value: Expected normal value (if available)
        deviation: Deviation from expected value
    """

    timestamp: datetime
    value: float
    anomaly_score: float
    is_anomaly: bool
    expected_value: float | None = None
    deviation: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "value": self.value,
            "anomaly_score": self.anomaly_score,
            "is_anomaly": self.is_anomaly,
            "expected_value": self.expected_value,
            "deviation": self.deviation,
        }


@dataclass
class AnomalyResult:
    """
    Result of anomaly detection analysis.

    Contains identified anomalies and detection metadata.

    Attributes:
        anomalies: List of anomaly points with scores
        threshold: Score threshold used for classification
        method: Detection method used (e.g., "isolation_forest", "zscore", "iqr")
        total_points: Total number of data points analyzed
        anomaly_count: Number of points classified as anomalies
        contamination: Expected proportion of anomalies (if applicable)
        parameters: Additional method-specific parameters

    Example:
        >>> result = AnomalyResult(
        ...     anomalies=[AnomalyPoint(datetime.now(), 100.0, 0.9, True)],
        ...     threshold=0.5,
        ...     method="isolation_forest",
        ...     total_points=1000,
        ...     anomaly_count=5
        ... )
    """

    anomalies: list[AnomalyPoint]
    threshold: float
    method: str
    total_points: int
    anomaly_count: int
    contamination: float = 0.01
    parameters: dict[str, Any] = field(default_factory=dict)

    @property
    def anomaly_rate(self) -> float:
        """Calculate anomaly rate as percentage."""
        if self.total_points == 0:
            return 0.0
        return self.anomaly_count / self.total_points

    @property
    def detected_anomalies(self) -> list[AnomalyPoint]:
        """Get only points classified as anomalies."""
        return [a for a in self.anomalies if a.is_anomaly]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "anomalies": [a.to_dict() for a in self.anomalies],
            "threshold": self.threshold,
            "method": self.method,
            "total_points": self.total_points,
            "anomaly_count": self.anomaly_count,
            "anomaly_rate": self.anomaly_rate,
            "contamination": self.contamination,
            "parameters": self.parameters,
        }


@dataclass
class Cluster:
    """
    A single cluster from clustering analysis.

    Attributes:
        id: Unique cluster identifier
        label: Human-readable cluster label
        size: Number of items in the cluster
        centroid: Cluster center coordinates (if applicable)
        keywords: Representative keywords for the cluster
        representative_items: Sample items from the cluster
    """

    id: int
    label: str
    size: int
    centroid: list[float] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    representative_items: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "label": self.label,
            "size": self.size,
            "centroid": self.centroid,
            "keywords": self.keywords,
            "representative_items": self.representative_items,
        }


@dataclass
class ClusterResult:
    """
    Result of clustering analysis.

    Contains cluster assignments and quality metrics.

    Attributes:
        clusters: List of identified clusters
        n_clusters: Number of clusters
        silhouette_score: Silhouette coefficient (-1 to 1, higher is better)
        method: Clustering method used (e.g., "kmeans", "dbscan", "hdbscan")
        inertia: Within-cluster sum of squares (for k-means)
        labels: Cluster assignment for each input item
        parameters: Method-specific parameters

    Example:
        >>> result = ClusterResult(
        ...     clusters=[Cluster(0, "Tech", 100), Cluster(1, "Sports", 50)],
        ...     n_clusters=2,
        ...     silhouette_score=0.65,
        ...     method="kmeans"
        ... )
    """

    clusters: list[Cluster]
    n_clusters: int
    silhouette_score: float
    method: str
    inertia: float | None = None
    labels: list[int] = field(default_factory=list)
    parameters: dict[str, Any] = field(default_factory=dict)

    @property
    def total_items(self) -> int:
        """Total number of items across all clusters."""
        return sum(c.size for c in self.clusters)

    @property
    def largest_cluster(self) -> Cluster | None:
        """Get the largest cluster by size."""
        if not self.clusters:
            return None
        return max(self.clusters, key=lambda c: c.size)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "clusters": [c.to_dict() for c in self.clusters],
            "n_clusters": self.n_clusters,
            "silhouette_score": self.silhouette_score,
            "method": self.method,
            "inertia": self.inertia,
            "total_items": self.total_items,
            "parameters": self.parameters,
        }


@dataclass
class Topic:
    """
    A single topic from topic modeling.

    Attributes:
        id: Unique topic identifier
        keywords: Top keywords representing the topic
        weights: Weight of each keyword in the topic
        representative_docs: Sample documents highly associated with the topic
        coherence: Topic coherence score (if available)
    """

    id: int
    keywords: list[str]
    weights: list[float] = field(default_factory=list)
    representative_docs: list[str] = field(default_factory=list)
    coherence: float | None = None

    def __post_init__(self) -> None:
        """Validate topic data."""
        if self.weights and len(self.weights) != len(self.keywords):
            raise ValueError("weights must have same length as keywords")

    @property
    def label(self) -> str:
        """Generate a label from top keywords."""
        return "_".join(self.keywords[:3]) if self.keywords else f"topic_{self.id}"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "label": self.label,
            "keywords": self.keywords,
            "weights": self.weights,
            "representative_docs": self.representative_docs,
            "coherence": self.coherence,
        }


@dataclass
class TopicResult:
    """
    Result of topic modeling analysis.

    Contains discovered topics and model quality metrics.

    Attributes:
        topics: List of discovered topics
        n_topics: Number of topics
        coherence_score: Overall model coherence score
        method: Topic modeling method (e.g., "lda", "nmf", "bertopic")
        perplexity: Model perplexity (for probabilistic models)
        document_topic_distribution: Topic weights for each document
        parameters: Method-specific parameters

    Example:
        >>> result = TopicResult(
        ...     topics=[Topic(0, ["python", "code", "programming"])],
        ...     n_topics=5,
        ...     coherence_score=0.45,
        ...     method="lda"
        ... )
    """

    topics: list[Topic]
    n_topics: int
    coherence_score: float
    method: str
    perplexity: float | None = None
    document_topic_distribution: list[list[float]] = field(default_factory=list)
    parameters: dict[str, Any] = field(default_factory=dict)

    @property
    def avg_topic_coherence(self) -> float:
        """Calculate average coherence across all topics."""
        coherences = [t.coherence for t in self.topics if t.coherence is not None]
        if not coherences:
            return self.coherence_score
        return sum(coherences) / len(coherences)

    def get_topic_by_id(self, topic_id: int) -> Topic | None:
        """Get a topic by its ID."""
        for topic in self.topics:
            if topic.id == topic_id:
                return topic
        return None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "topics": [t.to_dict() for t in self.topics],
            "n_topics": self.n_topics,
            "coherence_score": self.coherence_score,
            "avg_topic_coherence": self.avg_topic_coherence,
            "method": self.method,
            "perplexity": self.perplexity,
            "parameters": self.parameters,
        }
