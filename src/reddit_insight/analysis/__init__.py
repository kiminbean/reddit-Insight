"""
Reddit Insight Analysis Module.

텍스트 분석, 토큰화, 키워드 추출을 위한 모듈.

Example:
    >>> from reddit_insight.analysis import RedditTokenizer, StopwordManager
    >>> tokenizer = RedditTokenizer()
    >>> tokens = tokenizer.tokenize("This is a sample Reddit post!")
    >>> print(tokens)
    ['sample']

    >>> from reddit_insight.analysis import UnifiedKeywordExtractor
    >>> extractor = UnifiedKeywordExtractor()
    >>> result = extractor.extract_keywords(["Python is great for ML"])
    >>> print(result.keywords[0].keyword)
"""

from reddit_insight.analysis.keywords import (
    Keyword,
    KeywordExtractorConfig,
    KeywordMethod,
    KeywordResult,
    UnifiedKeywordExtractor,
    YAKEExtractor,
)
from reddit_insight.analysis.stopwords import (
    StopwordManager,
    ensure_nltk_data,
    get_default_stopwords,
)
from reddit_insight.analysis.tfidf import TFIDFAnalyzer, TFIDFConfig
from reddit_insight.analysis.time_series import (
    TimeGranularity,
    TimePoint,
    TimeSeries,
    bucket_timestamp,
    get_time_delta,
)
from reddit_insight.analysis.tokenizer import RedditTokenizer, TokenizerConfig
from reddit_insight.analysis.trends import (
    KeywordTrendAnalyzer,
    KeywordTrendResult,
    TrendCalculator,
    TrendDirection,
    TrendMetrics,
)
from reddit_insight.analysis.rising import (
    RisingConfig,
    RisingKeywordDetector,
    RisingScore,
    RisingScoreCalculator,
    TrendReport,
    TrendReporter,
)
from reddit_insight.analysis.demand_patterns import (
    DemandCategory,
    DemandMatch,
    DemandPattern,
    DemandPatternLibrary,
    ENGLISH_PATTERNS,
    KOREAN_PATTERNS,
)
from reddit_insight.analysis.demand_detector import (
    DemandDetector,
    DemandDetectorConfig,
    DemandSummary,
)
from reddit_insight.analysis.demand_analyzer import (
    DemandAnalyzer,
    DemandCluster,
    DemandClusterer,
    DemandReport,
    PrioritizedDemand,
    PriorityCalculator,
    PriorityConfig,
    PriorityScore,
)

__all__ = [
    # Tokenizer
    "RedditTokenizer",
    "TokenizerConfig",
    # Stopwords
    "StopwordManager",
    "get_default_stopwords",
    "ensure_nltk_data",
    # Keywords - Data Classes
    "Keyword",
    "KeywordResult",
    "KeywordExtractorConfig",
    "KeywordMethod",
    # Keywords - Extractors
    "YAKEExtractor",
    "UnifiedKeywordExtractor",
    # TF-IDF
    "TFIDFAnalyzer",
    "TFIDFConfig",
    # Time Series
    "TimeSeries",
    "TimePoint",
    "TimeGranularity",
    "bucket_timestamp",
    "get_time_delta",
    # Trends
    "TrendCalculator",
    "TrendDirection",
    "TrendMetrics",
    "KeywordTrendAnalyzer",
    "KeywordTrendResult",
    # Rising Keywords
    "RisingScore",
    "RisingConfig",
    "RisingScoreCalculator",
    "RisingKeywordDetector",
    "TrendReport",
    "TrendReporter",
    # Demand Patterns
    "DemandCategory",
    "DemandPattern",
    "DemandMatch",
    "DemandPatternLibrary",
    "ENGLISH_PATTERNS",
    "KOREAN_PATTERNS",
    # Demand Detector
    "DemandDetector",
    "DemandDetectorConfig",
    "DemandSummary",
    # Demand Analyzer
    "DemandCluster",
    "DemandClusterer",
    "PriorityScore",
    "PriorityConfig",
    "PriorityCalculator",
    "PrioritizedDemand",
    "DemandReport",
    "DemandAnalyzer",
]
