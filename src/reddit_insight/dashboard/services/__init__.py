"""대시보드 서비스 패키지."""

# 기존 services.py에서 임포트 (하위 호환성 유지)
# 이상 탐지 서비스
from reddit_insight.dashboard.services.anomaly_service import (
    AnomalyPointView,
    AnomalyService,
    AnomalyView,
    get_anomaly_service,
)

# 클러스터링 서비스
from reddit_insight.dashboard.services.cluster_service import (
    ClusterAnalysisView,
    ClusterKeywordView,
    ClusterService,
    ClusterView,
    get_cluster_service,
)

# 새 인사이트 서비스
from reddit_insight.dashboard.services.insight_service import (
    InsightDetail,
    InsightService,
    InsightView,
    OpportunityView,
    RecommendationView,
    get_insight_service,
)

# 예측 서비스
from reddit_insight.dashboard.services.prediction_service import (
    PredictionService,
    PredictionView,
    get_prediction_service,
)

# 토픽 모델링 서비스
from reddit_insight.dashboard.services.topic_service import (
    TopicAnalysisView,
    TopicKeywordView,
    TopicService,
    TopicView,
    get_topic_service,
)
from reddit_insight.dashboard.services_module import (
    AnalysisRecord,
    DashboardService,
    DashboardSummary,
    get_dashboard_service,
)

__all__ = [
    # Dashboard service
    "DashboardService",
    "DashboardSummary",
    "AnalysisRecord",
    "get_dashboard_service",
    # Anomaly service
    "AnomalyService",
    "AnomalyView",
    "AnomalyPointView",
    "get_anomaly_service",
    # Cluster service
    "ClusterService",
    "ClusterAnalysisView",
    "ClusterView",
    "ClusterKeywordView",
    "get_cluster_service",
    # Insight service
    "InsightService",
    "InsightView",
    "InsightDetail",
    "RecommendationView",
    "OpportunityView",
    "get_insight_service",
    # Prediction service
    "PredictionService",
    "PredictionView",
    "get_prediction_service",
    # Topic service
    "TopicService",
    "TopicAnalysisView",
    "TopicView",
    "TopicKeywordView",
    "get_topic_service",
]
