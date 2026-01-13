"""대시보드 서비스 패키지."""

# 기존 services.py에서 임포트 (하위 호환성 유지)
# 이상 탐지 서비스
from reddit_insight.dashboard.services.anomaly_service import (
    AnomalyPointView,
    AnomalyService,
    AnomalyView,
    get_anomaly_service,
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
]
