"""비교 분석 대시보드 서비스.

여러 서브레딧의 비교 분석을 대시보드에 제공하는 서비스 레이어.
캐싱을 적용하여 성능을 최적화한다.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Any

from reddit_insight.analysis.comparison import (
    ComparisonAnalyzer,
    ComparisonResult,
    SubredditMetrics,
)
from reddit_insight.dashboard.data_store import (
    AnalysisData,
    get_all_subreddits,
    load_from_database,
)
from reddit_insight.dashboard.services.cache_service import (
    CacheService,
    get_cache_service,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


# =============================================================================
# VIEW DATA CLASSES
# =============================================================================


@dataclass
class SubredditMetricsView:
    """서브레딧 메트릭 뷰 모델.

    Attributes:
        subreddit: 서브레딧 이름
        post_count: 게시물 수
        avg_score: 평균 점수
        avg_comments: 평균 댓글 수
        top_keywords: 상위 키워드
        sentiment: 감성 분포
    """

    subreddit: str
    post_count: int
    avg_score: float
    avg_comments: float
    top_keywords: list[str] = field(default_factory=list)
    sentiment: dict[str, float] = field(default_factory=dict)

    @classmethod
    def from_metrics(cls, metrics: SubredditMetrics) -> "SubredditMetricsView":
        """SubredditMetrics에서 SubredditMetricsView를 생성한다."""
        return cls(
            subreddit=metrics.subreddit,
            post_count=metrics.post_count,
            avg_score=metrics.avg_score,
            avg_comments=metrics.avg_comments,
            top_keywords=metrics.top_keywords[:10],  # 상위 10개
            sentiment=metrics.sentiment_distribution,
        )


@dataclass
class ComparisonView:
    """비교 분석 결과 뷰 모델.

    Attributes:
        subreddits: 비교 대상 서브레딧 목록
        metrics: 서브레딧별 메트릭
        common_keywords: 공통 키워드
        unique_keywords: 서브레딧별 고유 키워드
        overlap_matrix: 키워드 유사도 행렬
        sentiment_comparison: 감성 비교
        chart_data: 차트 데이터
    """

    subreddits: list[str]
    metrics: list[SubredditMetricsView]
    common_keywords: list[str]
    unique_keywords: dict[str, list[str]]
    overlap_matrix: list[list[float]]
    sentiment_comparison: dict[str, dict[str, float]]
    chart_data: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_result(
        cls, result: ComparisonResult, chart_data: dict[str, Any] | None = None
    ) -> "ComparisonView":
        """ComparisonResult에서 ComparisonView를 생성한다."""
        return cls(
            subreddits=result.subreddits,
            metrics=[SubredditMetricsView.from_metrics(m) for m in result.metrics],
            common_keywords=result.common_keywords[:20],  # 상위 20개
            unique_keywords={
                k: v[:10] for k, v in result.unique_keywords.items()  # 상위 10개씩
            },
            overlap_matrix=result.keyword_overlap_matrix,
            sentiment_comparison=result.sentiment_comparison,
            chart_data=chart_data or {},
        )


# =============================================================================
# COMPARISON SERVICE
# =============================================================================


class ComparisonService:
    """비교 분석 대시보드 서비스.

    여러 서브레딧의 분석 데이터를 비교하여 인사이트를 제공한다.
    캐싱을 통해 반복 분석 요청의 성능을 최적화한다.

    Attributes:
        cache: CacheService 인스턴스
    """

    # 캐시 TTL (초)
    COMPARISON_CACHE_TTL = 1800  # 30분

    def __init__(self, cache: CacheService | None = None) -> None:
        """ComparisonService를 초기화한다.

        Args:
            cache: CacheService 인스턴스 (None이면 기본 캐시 사용)
        """
        self.cache = cache or get_cache_service()

    async def compare_subreddits(
        self, subreddits: list[str], use_cache: bool = True
    ) -> ComparisonView | None:
        """여러 서브레딧을 비교 분석한다.

        1. 각 서브레딧의 분석 데이터 로드
        2. ComparisonAnalyzer로 비교
        3. 결과 캐싱 및 반환

        Args:
            subreddits: 비교할 서브레딧 목록 (2-5개)
            use_cache: 캐시 사용 여부

        Returns:
            ComparisonView 또는 None (데이터가 없는 경우)

        Raises:
            ValueError: 서브레딧 수가 2-5개 범위를 벗어나는 경우
        """
        if len(subreddits) < 2:
            raise ValueError("비교 분석에는 최소 2개의 서브레딧이 필요합니다.")
        if len(subreddits) > 5:
            raise ValueError("비교 분석은 최대 5개의 서브레딧까지만 지원합니다.")

        # 정규화 및 정렬
        normalized = sorted([s.lower().strip() for s in subreddits])
        cache_key = f"comparison:{':'.join(normalized)}"

        # 캐시 확인
        if use_cache:
            cached = self.cache.get(cache_key)
            if cached:
                logger.debug("비교 분석 캐시 히트: %s", normalized)
                return ComparisonView(**cached)

        # 데이터 로드
        data_sources: list[AnalysisData] = []
        for subreddit in normalized:
            data = await self.load_subreddit_data(subreddit)
            if data is None:
                logger.warning("서브레딧 '%s'의 분석 데이터가 없습니다.", subreddit)
                return None
            data_sources.append(data)

        # 비교 분석 실행
        try:
            analyzer = ComparisonAnalyzer(data_sources)
            result = analyzer.compare()
        except Exception as e:
            logger.error("비교 분석 실패: %s", e)
            return None

        # 차트 데이터 생성
        chart_data = self.get_comparison_chart_data(result)

        # View 생성
        view = ComparisonView.from_result(result, chart_data)

        # 캐시 저장
        if use_cache:
            self.cache.set(cache_key, asdict(view), ttl=self.COMPARISON_CACHE_TTL)
            logger.info("비교 분석 완료 및 캐시 저장: %s", normalized)

        return view

    async def load_subreddit_data(self, subreddit: str) -> AnalysisData | None:
        """서브레딧 분석 데이터를 로드한다.

        Args:
            subreddit: 서브레딧 이름

        Returns:
            AnalysisData 또는 None
        """
        # 데이터베이스에서 로드
        data = load_from_database(subreddit)
        if data:
            return data

        logger.debug("서브레딧 '%s' 데이터 없음", subreddit)
        return None

    def get_comparison_chart_data(self, result: ComparisonResult) -> dict[str, Any]:
        """Chart.js 형식의 비교 차트 데이터를 생성한다.

        Args:
            result: ComparisonResult

        Returns:
            차트 데이터 딕셔너리
        """
        subreddits = result.subreddits
        metrics = result.metrics

        # 색상 팔레트
        colors = [
            "rgba(99, 102, 241, 0.8)",   # Indigo
            "rgba(16, 185, 129, 0.8)",   # Emerald
            "rgba(245, 158, 11, 0.8)",   # Amber
            "rgba(239, 68, 68, 0.8)",    # Red
            "rgba(139, 92, 246, 0.8)",   # Violet
        ]
        border_colors = [
            "rgba(99, 102, 241, 1)",
            "rgba(16, 185, 129, 1)",
            "rgba(245, 158, 11, 1)",
            "rgba(239, 68, 68, 1)",
            "rgba(139, 92, 246, 1)",
        ]

        # 1. 활동량 비교 바 차트
        activity_chart = {
            "type": "bar",
            "data": {
                "labels": subreddits,
                "datasets": [
                    {
                        "label": "게시물 수",
                        "data": [m.post_count for m in metrics],
                        "backgroundColor": colors[: len(subreddits)],
                        "borderColor": border_colors[: len(subreddits)],
                        "borderWidth": 1,
                    }
                ],
            },
            "options": {
                "responsive": True,
                "plugins": {
                    "title": {
                        "display": True,
                        "text": "게시물 수 비교",
                    }
                },
            },
        }

        # 2. 감성 분포 스택 바 차트
        sentiment_chart = {
            "type": "bar",
            "data": {
                "labels": subreddits,
                "datasets": [
                    {
                        "label": "긍정",
                        "data": [
                            round(m.sentiment_distribution.get("positive", 0) * 100, 1)
                            for m in metrics
                        ],
                        "backgroundColor": "rgba(16, 185, 129, 0.8)",
                        "borderColor": "rgba(16, 185, 129, 1)",
                        "borderWidth": 1,
                    },
                    {
                        "label": "중립",
                        "data": [
                            round(m.sentiment_distribution.get("neutral", 0) * 100, 1)
                            for m in metrics
                        ],
                        "backgroundColor": "rgba(156, 163, 175, 0.8)",
                        "borderColor": "rgba(156, 163, 175, 1)",
                        "borderWidth": 1,
                    },
                    {
                        "label": "부정",
                        "data": [
                            round(m.sentiment_distribution.get("negative", 0) * 100, 1)
                            for m in metrics
                        ],
                        "backgroundColor": "rgba(239, 68, 68, 0.8)",
                        "borderColor": "rgba(239, 68, 68, 1)",
                        "borderWidth": 1,
                    },
                ],
            },
            "options": {
                "responsive": True,
                "scales": {"x": {"stacked": True}, "y": {"stacked": True}},
                "plugins": {
                    "title": {
                        "display": True,
                        "text": "감성 분포 비교 (%)",
                    }
                },
            },
        }

        # 3. 키워드 유사도 히트맵 데이터
        heatmap_data = {
            "labels": subreddits,
            "matrix": [
                [round(v * 100, 1) for v in row]
                for row in result.keyword_overlap_matrix
            ],
        }

        return {
            "activity": activity_chart,
            "sentiment": sentiment_chart,
            "heatmap": heatmap_data,
        }

    def get_available_subreddits(self) -> list[str]:
        """비교 가능한 서브레딧 목록을 반환한다.

        Returns:
            분석 데이터가 있는 서브레딧 목록
        """
        return get_all_subreddits()


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_comparison_service: ComparisonService | None = None


def get_comparison_service() -> ComparisonService:
    """ComparisonService 싱글톤 인스턴스를 반환한다.

    Returns:
        ComparisonService 인스턴스
    """
    global _comparison_service

    if _comparison_service is None:
        _comparison_service = ComparisonService()
        logger.info("ComparisonService 초기화 완료")

    return _comparison_service


def reset_comparison_service() -> None:
    """ComparisonService 싱글톤을 리셋한다 (테스트용)."""
    global _comparison_service
    _comparison_service = None
