"""LLM 통합 모듈.

LLM API 클라이언트, 프롬프트 템플릿, rate limiting 및 캐싱 시스템.
"""

from reddit_insight.llm.client import (
    ClaudeClient,
    LLMClient,
    LLMError,
    LLMRateLimitError,
    OpenAIClient,
    get_llm_client,
)
from reddit_insight.llm.rate_limiter import RateLimiter
from reddit_insight.llm.cache import LLMCache

__all__ = [
    # Client
    "LLMClient",
    "ClaudeClient",
    "OpenAIClient",
    "get_llm_client",
    "LLMError",
    "LLMRateLimitError",
    # Rate Limiting & Caching
    "RateLimiter",
    "LLMCache",
]


def __getattr__(name: str):
    """Lazy import for prompts module to avoid circular imports."""
    if name in (
        "PromptTemplate",
        "SUMMARIZE_POSTS",
        "CATEGORIZE_CONTENT",
        "EXTRACT_INSIGHTS",
        "SENTIMENT_ANALYSIS",
        "TREND_INTERPRETATION",
    ):
        from reddit_insight.llm import prompts

        return getattr(prompts, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
