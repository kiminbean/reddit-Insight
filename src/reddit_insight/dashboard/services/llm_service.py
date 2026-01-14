"""LLM 대시보드 서비스.

LLM 기반 분석 기능을 대시보드에 제공하는 서비스 레이어.
캐싱을 적용하여 API 비용을 최적화한다.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

from reddit_insight.llm import (
    CategoryResult,
    DeepSentimentResult,
    Insight,
    LLMAnalyzer,
    LLMError,
)
from reddit_insight.dashboard.services.cache_service import (
    CacheService,
    get_cache_service,
)

if TYPE_CHECKING:
    from reddit_insight.llm import LLMClient

logger = logging.getLogger(__name__)


# =============================================================================
# DATA CLASSES FOR VIEW MODELS
# =============================================================================


@dataclass
class LLMSummaryView:
    """LLM 요약 결과 뷰 모델.

    Attributes:
        summary: 요약 텍스트 (마크다운)
        generated_at: 생성 시각
        post_count: 분석된 게시물 수
        subreddit: 분석 대상 서브레딧
        cached: 캐시된 결과 여부
    """

    summary: str
    generated_at: str
    post_count: int = 0
    subreddit: str = ""
    cached: bool = False


@dataclass
class LLMCategoryView:
    """LLM 카테고리화 결과 뷰 모델.

    Attributes:
        text: 원본 텍스트 (축약)
        category: 분류된 카테고리
        confidence: 신뢰도 (0-100)
        reason: 분류 이유
        secondary: 2순위 카테고리 목록
    """

    text: str
    category: str
    confidence: float
    reason: str = ""
    secondary: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_result(cls, result: CategoryResult) -> "LLMCategoryView":
        """CategoryResult에서 LLMCategoryView를 생성한다."""
        return cls(
            text=result.text,
            category=result.category,
            confidence=result.confidence,
            reason=result.reason,
            secondary=result.secondary_categories,
        )


@dataclass
class LLMSentimentView:
    """LLM 심층 감성 분석 결과 뷰 모델.

    Attributes:
        sentiment: 전체 감성 (positive/neutral/negative)
        score: 감성 점수 (-1.0 ~ +1.0)
        factors: 감성 세부 요인 목록
        emotions: 감지된 감정 목록
        is_opinion: 의견인지 사실인지 여부
        user_needs: 사용자 니즈 목록
        pain_points: 불만 사항 목록
    """

    sentiment: str
    score: float
    factors: list[dict[str, Any]] = field(default_factory=list)
    emotions: list[str] = field(default_factory=list)
    is_opinion: bool = True
    user_needs: list[str] = field(default_factory=list)
    pain_points: list[str] = field(default_factory=list)

    @classmethod
    def from_result(cls, result: DeepSentimentResult) -> "LLMSentimentView":
        """DeepSentimentResult에서 LLMSentimentView를 생성한다."""
        return cls(
            sentiment=result.overall_sentiment,
            score=result.sentiment_score,
            factors=[
                {"aspect": f.aspect, "sentiment": f.sentiment, "reason": f.reason}
                for f in result.factors
            ],
            emotions=result.emotions,
            is_opinion=result.is_opinion,
            user_needs=result.user_needs,
            pain_points=result.pain_points,
        )


@dataclass
class LLMInsightView:
    """LLM 인사이트 뷰 모델.

    Attributes:
        title: 인사이트 제목
        finding: 발견 내용
        meaning: 비즈니스적 의미
        recommendation: 권장 조치
        priority: 우선순위 (high/medium/low)
    """

    title: str
    finding: str
    meaning: str
    recommendation: str
    priority: str

    @classmethod
    def from_result(cls, insight: Insight) -> "LLMInsightView":
        """Insight에서 LLMInsightView를 생성한다."""
        return cls(
            title=insight.title,
            finding=insight.finding,
            meaning=insight.meaning,
            recommendation=insight.recommendation,
            priority=insight.priority,
        )


# =============================================================================
# LLM SERVICE
# =============================================================================


class LLMService:
    """LLM 대시보드 서비스.

    LLMAnalyzer를 래핑하여 대시보드에 필요한 기능을 제공한다.
    캐싱을 적용하여 API 호출 비용을 최적화한다.

    Attributes:
        analyzer: LLMAnalyzer 인스턴스
        cache: CacheService 인스턴스
        is_configured: LLM API가 설정되었는지 여부
    """

    # 캐시 TTL (초)
    SUMMARY_CACHE_TTL = 3600  # 1시간
    CATEGORY_CACHE_TTL = 86400  # 24시간
    SENTIMENT_CACHE_TTL = 86400  # 24시간
    INSIGHTS_CACHE_TTL = 1800  # 30분

    def __init__(
        self,
        analyzer: LLMAnalyzer | None = None,
        cache: CacheService | None = None,
    ) -> None:
        """LLMService를 초기화한다.

        Args:
            analyzer: LLMAnalyzer 인스턴스 (None이면 비활성화 상태)
            cache: CacheService 인스턴스 (None이면 기본 캐시 사용)
        """
        self.analyzer = analyzer
        self.cache = cache or get_cache_service()
        self.is_configured = analyzer is not None

    # =========================================================================
    # SUMMARY
    # =========================================================================

    async def get_summary(
        self,
        subreddit: str,
        posts: list[dict[str, Any]],
        use_cache: bool = True,
    ) -> LLMSummaryView:
        """서브레딧 분석 요약을 가져온다.

        Args:
            subreddit: 서브레딧 이름
            posts: 분석할 게시물 목록
            use_cache: 캐시 사용 여부

        Returns:
            LLMSummaryView

        Raises:
            LLMError: LLM API 호출 실패 시
        """
        if not self.is_configured:
            return LLMSummaryView(
                summary="LLM API가 설정되지 않았습니다. 환경변수를 확인하세요.",
                generated_at=datetime.now().isoformat(),
                subreddit=subreddit,
            )

        cache_key = f"llm:summary:{subreddit.lower()}"

        # 캐시 확인
        if use_cache:
            cached = self.cache.get(cache_key)
            if cached:
                logger.debug("LLM 요약 캐시 히트: %s", subreddit)
                cached["cached"] = True
                return LLMSummaryView(**cached)

        # LLM 호출
        if not posts:
            return LLMSummaryView(
                summary="분석할 게시물이 없습니다.",
                generated_at=datetime.now().isoformat(),
                subreddit=subreddit,
            )

        summary = await self.analyzer.summarize_posts(posts)  # type: ignore[union-attr]

        result = LLMSummaryView(
            summary=summary,
            generated_at=datetime.now().isoformat(),
            post_count=len(posts),
            subreddit=subreddit,
            cached=False,
        )

        # 캐시 저장
        if use_cache:
            cache_data = asdict(result)
            del cache_data["cached"]
            self.cache.set(cache_key, cache_data, ttl=self.SUMMARY_CACHE_TTL)

        logger.info("LLM 요약 생성 완료: %s (%d 게시물)", subreddit, len(posts))
        return result

    # =========================================================================
    # CATEGORIZATION
    # =========================================================================

    async def get_ai_categorization(
        self,
        texts: list[str],
        categories: list[str] | None = None,
    ) -> list[LLMCategoryView]:
        """AI 카테고리화 결과를 가져온다.

        Args:
            texts: 분류할 텍스트 목록
            categories: 사용할 카테고리 목록 (None이면 기본 카테고리)

        Returns:
            LLMCategoryView 목록

        Raises:
            LLMError: LLM API 호출 실패 시
        """
        if not self.is_configured:
            return [
                LLMCategoryView(
                    text=text[:100],
                    category="Uncategorized",
                    confidence=0,
                    reason="LLM API가 설정되지 않았습니다.",
                )
                for text in texts
            ]

        if not texts:
            return []

        results = await self.analyzer.categorize_content(texts, categories)  # type: ignore[union-attr]
        return [LLMCategoryView.from_result(r) for r in results]

    async def categorize_single(
        self,
        text: str,
        categories: list[str] | None = None,
    ) -> LLMCategoryView:
        """단일 텍스트를 카테고리화한다.

        Args:
            text: 분류할 텍스트
            categories: 사용할 카테고리 목록

        Returns:
            LLMCategoryView
        """
        results = await self.get_ai_categorization([text], categories)
        return results[0] if results else LLMCategoryView(
            text=text[:100],
            category="Uncategorized",
            confidence=0,
        )

    # =========================================================================
    # SENTIMENT ANALYSIS
    # =========================================================================

    async def get_deep_sentiment(self, text: str) -> LLMSentimentView:
        """심층 감성 분석 결과를 가져온다.

        Args:
            text: 분석할 텍스트

        Returns:
            LLMSentimentView

        Raises:
            LLMError: LLM API 호출 실패 시
        """
        if not self.is_configured:
            return LLMSentimentView(
                sentiment="unknown",
                score=0.0,
            )

        if not text.strip():
            return LLMSentimentView(
                sentiment="neutral",
                score=0.0,
            )

        result = await self.analyzer.analyze_sentiment_deep(text)  # type: ignore[union-attr]
        return LLMSentimentView.from_result(result)

    # =========================================================================
    # INSIGHTS
    # =========================================================================

    async def get_insights(
        self,
        analysis_data: dict[str, Any],
        subreddit: str = "",
        use_cache: bool = True,
    ) -> list[LLMInsightView]:
        """분석 결과에서 비즈니스 인사이트를 생성한다.

        Args:
            analysis_data: 분석 결과 데이터
            subreddit: 분석 대상 서브레딧
            use_cache: 캐시 사용 여부

        Returns:
            LLMInsightView 목록

        Raises:
            LLMError: LLM API 호출 실패 시
        """
        if not self.is_configured:
            return []

        if not analysis_data:
            return []

        cache_key = f"llm:insights:{subreddit.lower()}"

        # 캐시 확인
        if use_cache:
            cached = self.cache.get(cache_key)
            if cached:
                logger.debug("LLM 인사이트 캐시 히트: %s", subreddit)
                return [LLMInsightView(**item) for item in cached]

        # LLM 호출
        insights = await self.analyzer.generate_insights(  # type: ignore[union-attr]
            analysis_data,
            subreddit=subreddit,
        )

        views = [LLMInsightView.from_result(i) for i in insights]

        # 캐시 저장
        if use_cache and views:
            cache_data = [asdict(v) for v in views]
            self.cache.set(cache_key, cache_data, ttl=self.INSIGHTS_CACHE_TTL)

        logger.info("LLM 인사이트 생성 완료: %s (%d개)", subreddit, len(views))
        return views

    # =========================================================================
    # TREND INTERPRETATION
    # =========================================================================

    async def interpret_trends(
        self,
        trend_data: dict[str, Any],
        rising_keywords: list[str],
        declining_keywords: list[str],
        target: str = "subreddit",
    ) -> str:
        """트렌드 데이터를 해석한다.

        Args:
            trend_data: 트렌드 데이터
            rising_keywords: 상승 키워드 목록
            declining_keywords: 하락 키워드 목록
            target: 분석 대상

        Returns:
            트렌드 해석 텍스트 (마크다운)
        """
        if not self.is_configured:
            return "LLM API가 설정되지 않았습니다."

        return await self.analyzer.interpret_trends(  # type: ignore[union-attr]
            trend_data=trend_data,
            rising_keywords=rising_keywords,
            declining_keywords=declining_keywords,
            target=target,
        )

    # =========================================================================
    # STATUS
    # =========================================================================

    def get_status(self) -> dict[str, Any]:
        """LLM 서비스 상태를 반환한다.

        Returns:
            상태 정보 딕셔너리
        """
        return {
            "configured": self.is_configured,
            "cache_stats": self.cache.stats() if self.cache else {},
        }


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_llm_service: LLMService | None = None


def get_llm_service() -> LLMService:
    """LLMService 싱글톤 인스턴스를 반환한다.

    환경변수에서 API 키를 확인하여 LLMAnalyzer를 초기화한다.
    API 키가 없으면 비활성화 상태의 서비스를 반환한다.

    Returns:
        LLMService 인스턴스
    """
    global _llm_service

    if _llm_service is None:
        _llm_service = _create_llm_service()

    return _llm_service


def _create_llm_service() -> LLMService:
    """LLMService 인스턴스를 생성한다."""
    try:
        from reddit_insight.config import get_settings
        from reddit_insight.llm import get_llm_client

        settings = get_settings()

        # API 키 확인 (Claude 또는 OpenAI)
        if settings.anthropic_api_key:
            client = get_llm_client(provider="claude")
            analyzer = LLMAnalyzer(client=client)
            logger.info("LLMService 초기화 완료 (Claude)")
            return LLMService(analyzer=analyzer)
        elif settings.openai_api_key:
            client = get_llm_client(provider="openai")
            analyzer = LLMAnalyzer(client=client)
            logger.info("LLMService 초기화 완료 (OpenAI)")
            return LLMService(analyzer=analyzer)
        else:
            logger.warning("LLM API 키가 설정되지 않음, 비활성화 상태로 시작")
            return LLMService(analyzer=None)

    except Exception as e:
        logger.error("LLMService 초기화 실패: %s", e)
        return LLMService(analyzer=None)


def reset_llm_service() -> None:
    """LLMService 싱글톤을 리셋한다 (테스트용)."""
    global _llm_service
    _llm_service = None
