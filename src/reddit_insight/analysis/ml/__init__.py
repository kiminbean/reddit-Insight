"""
ML Analysis Module for Reddit Insight.

Provides machine learning based analysis tools for advanced analytics including:
- Time series prediction (ARIMA, exponential smoothing)
- Anomaly detection (Isolation Forest, Z-score)
- Clustering (K-means, DBSCAN)
- Topic modeling (LDA, NMF)

Example:
    >>> from reddit_insight.analysis.ml import MLAnalyzerBase, AnalysisResult
    >>> from reddit_insight.analysis.ml.models import PredictionResult, AnomalyResult
"""

from reddit_insight.analysis.ml.base import (
    AnalysisMetadata,
    AnalysisResult,
    MLAnalyzerBase,
    MLAnalyzerConfig,
)
from reddit_insight.analysis.ml.models import (
    AnomalyPoint,
    AnomalyResult,
    Cluster,
    ClusterResult,
    PredictionResult,
    Topic,
    TopicResult,
)

__all__ = [
    # Base classes
    "MLAnalyzerBase",
    "MLAnalyzerConfig",
    # Result types
    "AnalysisResult",
    "AnalysisMetadata",
    # Prediction models
    "PredictionResult",
    # Anomaly detection models
    "AnomalyPoint",
    "AnomalyResult",
    # Clustering models
    "Cluster",
    "ClusterResult",
    # Topic modeling models
    "Topic",
    "TopicResult",
]
