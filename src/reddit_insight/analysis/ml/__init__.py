"""
ML Analysis Module for Reddit Insight.

Provides machine learning based analysis tools for advanced analytics including:
- Time series prediction (ARIMA, exponential smoothing)
- Anomaly detection (Isolation Forest, Z-score, IQR)
- Clustering (K-means, Agglomerative)
- Topic modeling (LDA, NMF)

Example:
    >>> from reddit_insight.analysis.ml import MLAnalyzerBase, AnalysisResult
    >>> from reddit_insight.analysis.ml import TrendPredictor, TrendPredictorConfig
    >>> from reddit_insight.analysis.ml import AnomalyDetector, AnomalyDetectorConfig
    >>> from reddit_insight.analysis.ml import TopicModeler, TopicModelerConfig
    >>> from reddit_insight.analysis.ml import TextClusterer, TextClustererConfig
"""

from reddit_insight.analysis.ml.anomaly_detector import (
    AnomalyDetector,
    AnomalyDetectorConfig,
    detect_anomalies_simple,
)
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
from reddit_insight.analysis.ml.text_clusterer import (
    TextClusterer,
    TextClustererConfig,
)
from reddit_insight.analysis.ml.topic_modeler import (
    TopicModeler,
    TopicModelerConfig,
)
from reddit_insight.analysis.ml.trend_predictor import (
    TrendPredictor,
    TrendPredictorConfig,
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
    # Trend prediction
    "TrendPredictor",
    "TrendPredictorConfig",
    # Anomaly detection
    "AnomalyDetector",
    "AnomalyDetectorConfig",
    "detect_anomalies_simple",
    # Anomaly detection models
    "AnomalyPoint",
    "AnomalyResult",
    # Topic modeling
    "TopicModeler",
    "TopicModelerConfig",
    # Text clustering
    "TextClusterer",
    "TextClustererConfig",
    # Clustering models
    "Cluster",
    "ClusterResult",
    # Topic modeling models
    "Topic",
    "TopicResult",
]
