"""데이터 파이프라인 모듈.

Reddit 데이터 수집, 전처리, 저장을 위한 파이프라인을 제공한다.
"""

from reddit_insight.pipeline.collector import (
    CollectionResult as CollectorResult,
)
from reddit_insight.pipeline.collector import (
    Collector,
    CollectorConfig,
)
from reddit_insight.pipeline.data_pipeline import (
    CollectionResult,
    DataPipeline,
    ProcessingResult,
)
from reddit_insight.pipeline.preprocessor import TextPreprocessor
from reddit_insight.pipeline.scheduler import (
    ScheduleConfig,
    SchedulerState,
    SchedulerStatus,
    ScheduleRun,
    SimpleScheduler,
)

__all__ = [
    # Preprocessor
    "TextPreprocessor",
    # DataPipeline
    "DataPipeline",
    "ProcessingResult",
    "CollectionResult",
    # Collector
    "Collector",
    "CollectorConfig",
    "CollectorResult",
    # Scheduler
    "SimpleScheduler",
    "ScheduleConfig",
    "ScheduleRun",
    "SchedulerState",
    "SchedulerStatus",
]
