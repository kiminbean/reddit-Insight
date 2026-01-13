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
from reddit_insight.analysis.tokenizer import RedditTokenizer, TokenizerConfig

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
]
