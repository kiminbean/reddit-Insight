"""Reddit Insight - Reddit 데이터 수집 및 분석 도구.

사용자가 지정한 키워드에 대해 Reddit 게시물을 수집하고,
요약 및 인사이트를 추출하는 도구입니다.
"""

from reddit_insight.config import Settings, get_settings
from reddit_insight.data_source import (
    DataSourceError,
    DataSourceStrategy,
    SourceStatus,
    UnifiedDataSource,
)
from reddit_insight.logging import get_logger, setup_logging

__version__ = "0.1.0"
__all__ = [
    "__version__",
    # Config
    "Settings",
    "get_settings",
    # Logging
    "setup_logging",
    "get_logger",
    # Data Source
    "UnifiedDataSource",
    "DataSourceStrategy",
    "DataSourceError",
    "SourceStatus",
]
