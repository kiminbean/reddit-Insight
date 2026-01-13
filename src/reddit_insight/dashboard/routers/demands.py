"""수요 분석 라우터.

수요 발견 및 우선순위 분석 결과를 시각화하는 라우터.
"""

from dataclasses import dataclass
from hashlib import md5
from typing import Any, Optional

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from reddit_insight.analysis.demand_analyzer import (
    DemandAnalyzer,
    DemandCluster,
    DemandReport,
    PrioritizedDemand,
)
from reddit_insight.analysis.demand_patterns import DemandCategory

router = APIRouter(prefix="/dashboard/demands", tags=["demands"])


# =============================================================================
# VIEW MODELS
# =============================================================================


@dataclass
class DemandView:
    """수요 뷰 모델.

    Attributes:
        id: 고유 식별자
        category: 수요 카테고리 (feature_request, pain_point 등)
        text: 대표 텍스트
        priority_score: 우선순위 점수 (0-100)
        source_count: 소스 수 (매칭된 문장 수)
        business_potential: 비즈니스 잠재력 (high/medium/low)
        keywords: 관련 키워드 목록
    """

    id: str
    category: str
    text: str
    priority_score: float
    source_count: int
    business_potential: str = "medium"
    keywords: list[str] | None = None


@dataclass
class DemandDetail:
    """수요 상세 뷰 모델.

    Attributes:
        demand: 기본 수요 정보
        frequency_score: 빈도 점수
        payment_intent_score: 구매 의향 점수
        urgency_score: 긴급성 점수
        recency_score: 최신성 점수
        sample_texts: 샘플 텍스트 목록
    """

    demand: DemandView
    frequency_score: float
    payment_intent_score: float
    urgency_score: float
    recency_score: float
    sample_texts: list[str]


# =============================================================================
# DEMAND SERVICE
# =============================================================================


class DemandService:
    """수요 분석 서비스.

    DemandAnalyzer를 래핑하여 대시보드에 필요한 데이터 형태로 변환한다.
    """

    def __init__(self, analyzer: DemandAnalyzer | None = None) -> None:
        """DemandService를 초기화한다.

        Args:
            analyzer: 수요 분석기 (None이면 기본 인스턴스 생성)
        """
        self._analyzer = analyzer or DemandAnalyzer()
        self._cached_report: DemandReport | None = None
        self._sample_texts: list[str] = []

    def _generate_demand_id(self, cluster: DemandCluster) -> str:
        """클러스터에서 고유 ID를 생성한다."""
        # 대표 텍스트 기반으로 해시 생성
        content = f"{cluster.representative}_{cluster.cluster_id}"
        return md5(content.encode()).hexdigest()[:12]

    def _prioritized_to_view(self, prioritized: PrioritizedDemand) -> DemandView:
        """PrioritizedDemand를 DemandView로 변환한다."""
        cluster = prioritized.cluster
        primary_cat = cluster.primary_category

        return DemandView(
            id=self._generate_demand_id(cluster),
            category=primary_cat.value if primary_cat else "unknown",
            text=cluster.representative,
            priority_score=prioritized.priority.total_score,
            source_count=cluster.frequency,
            business_potential=prioritized.business_potential,
            keywords=cluster.keywords[:5] if cluster.keywords else None,
        )

    def _prioritized_to_detail(
        self, prioritized: PrioritizedDemand
    ) -> DemandDetail:
        """PrioritizedDemand를 DemandDetail로 변환한다."""
        view = self._prioritized_to_view(prioritized)
        priority = prioritized.priority

        # 샘플 텍스트 추출 (매칭된 컨텍스트에서)
        sample_texts = []
        for match in prioritized.cluster.matches[:5]:
            if match.context and match.context not in sample_texts:
                sample_texts.append(match.context)

        return DemandDetail(
            demand=view,
            frequency_score=priority.frequency_score,
            payment_intent_score=priority.payment_intent_score,
            urgency_score=priority.urgency_score,
            recency_score=priority.recency_score,
            sample_texts=sample_texts,
        )

    def analyze_texts(self, texts: list[str], top_n: int = 20) -> None:
        """텍스트 목록을 분석하고 결과를 캐시한다.

        Args:
            texts: 분석할 텍스트 목록
            top_n: 상위 기회 수
        """
        self._sample_texts = texts
        self._cached_report = self._analyzer.analyze_texts(texts, top_n=top_n)

    def get_demands(
        self,
        category: DemandCategory | str | None = None,
        min_priority: float = 0.0,
        limit: int = 20,
    ) -> list[DemandView]:
        """수요 목록을 반환한다.

        Args:
            category: 필터링할 카테고리 (None이면 전체)
            min_priority: 최소 우선순위 점수
            limit: 최대 반환 수

        Returns:
            DemandView 목록
        """
        if self._cached_report is None:
            # 데모 데이터로 분석 실행
            self._run_demo_analysis()

        if self._cached_report is None:
            return []

        result: list[DemandView] = []

        for prioritized in self._cached_report.top_opportunities:
            # 최소 우선순위 필터링
            if prioritized.priority.total_score < min_priority:
                continue

            # 카테고리 필터링
            if category is not None:
                cat_value = category.value if isinstance(category, DemandCategory) else category
                primary_cat = prioritized.cluster.primary_category
                if primary_cat is None or primary_cat.value != cat_value:
                    continue

            result.append(self._prioritized_to_view(prioritized))

            if len(result) >= limit:
                break

        return result

    def get_demand_detail(self, demand_id: str) -> DemandDetail | None:
        """수요 상세 정보를 반환한다.

        Args:
            demand_id: 수요 ID

        Returns:
            DemandDetail 또는 None (찾지 못한 경우)
        """
        if self._cached_report is None:
            self._run_demo_analysis()

        if self._cached_report is None:
            return None

        for prioritized in self._cached_report.top_opportunities:
            if self._generate_demand_id(prioritized.cluster) == demand_id:
                return self._prioritized_to_detail(prioritized)

        return None

    def get_category_stats(self) -> dict[str, int]:
        """카테고리별 수요 수를 반환한다.

        Returns:
            카테고리별 수요 수 딕셔너리
        """
        if self._cached_report is None:
            self._run_demo_analysis()

        if self._cached_report is None:
            return {}

        return {
            cat.value: count
            for cat, count in self._cached_report.by_category.items()
        }

    def get_recommendations(self) -> list[str]:
        """분석 권장사항을 반환한다.

        Returns:
            권장사항 목록
        """
        if self._cached_report is None:
            return []

        return self._cached_report.recommendations

    def _run_demo_analysis(self) -> None:
        """데모 데이터로 분석을 실행한다."""
        demo_texts = [
            "I wish there was a better way to organize my notes across devices.",
            "Looking for a good project management tool that's not too expensive.",
            "So frustrated with this app's constant crashes. Anyone have alternatives?",
            "I'd pay good money for a tool that actually syncs properly.",
            "Does anyone know of a free alternative to Notion?",
            "Really annoying that there's no dark mode option.",
            "We need something like Slack but for smaller teams.",
            "Is there a tool that can automatically categorize emails?",
            "Frustrated when the app takes forever to load.",
            "Would be great to have offline support.",
            "Looking for suggestions on budgeting apps.",
            "Any recommendations for a password manager?",
            "Why isn't there an option to export data?",
            "I'm willing to pay for a premium version with these features.",
            "Something similar to Figma but open source?",
        ]
        self.analyze_texts(demo_texts, top_n=20)


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_demand_service: DemandService | None = None


def get_demand_service() -> DemandService:
    """DemandService 싱글톤 인스턴스를 반환한다."""
    global _demand_service
    if _demand_service is None:
        _demand_service = DemandService()
    return _demand_service


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def get_templates(request: Request) -> Jinja2Templates:
    """Request에서 템플릿 인스턴스를 가져온다."""
    return request.app.state.templates


def demand_view_to_dict(view: DemandView) -> dict[str, Any]:
    """DemandView를 딕셔너리로 변환한다."""
    return {
        "id": view.id,
        "category": view.category,
        "text": view.text,
        "priority_score": view.priority_score,
        "source_count": view.source_count,
        "business_potential": view.business_potential,
        "keywords": view.keywords or [],
    }


def demand_detail_to_dict(detail: DemandDetail) -> dict[str, Any]:
    """DemandDetail을 딕셔너리로 변환한다."""
    return {
        "demand": demand_view_to_dict(detail.demand),
        "frequency_score": detail.frequency_score,
        "payment_intent_score": detail.payment_intent_score,
        "urgency_score": detail.urgency_score,
        "recency_score": detail.recency_score,
        "sample_texts": detail.sample_texts,
    }


# =============================================================================
# ROUTES
# =============================================================================


@router.get("/", response_class=HTMLResponse)
async def demands_index(
    request: Request,
    service: DemandService = Depends(get_demand_service),
) -> HTMLResponse:
    """수요 분석 메인 페이지를 렌더링한다.

    Args:
        request: FastAPI Request 객체
        service: DemandService 인스턴스

    Returns:
        HTMLResponse: 렌더링된 HTML 페이지
    """
    templates = get_templates(request)

    demands = service.get_demands(limit=20)
    category_stats = service.get_category_stats()
    recommendations = service.get_recommendations()

    # 카테고리 목록 생성
    categories = [
        {"value": cat.value, "label": cat.value.replace("_", " ").title()}
        for cat in DemandCategory
    ]

    context = {
        "request": request,
        "page_title": "Demands",
        "demands": [demand_view_to_dict(d) for d in demands],
        "category_stats": category_stats,
        "categories": categories,
        "recommendations": recommendations,
        "total_demands": sum(category_stats.values()) if category_stats else 0,
    }

    return templates.TemplateResponse(request, "demands/index.html", context)


@router.get("/list", response_class=HTMLResponse)
async def demands_list(
    request: Request,
    category: Optional[str] = Query(None, description="카테고리 필터"),
    min_priority: float = Query(0.0, ge=0.0, le=100.0, description="최소 우선순위"),
    limit: int = Query(20, ge=1, le=100, description="최대 반환 수"),
    service: DemandService = Depends(get_demand_service),
) -> HTMLResponse:
    """수요 목록을 HTMX partial로 반환한다.

    Args:
        request: FastAPI Request 객체
        category: 카테고리 필터
        min_priority: 최소 우선순위 점수
        limit: 최대 반환 수
        service: DemandService 인스턴스

    Returns:
        HTMLResponse: 수요 목록 HTML partial
    """
    templates = get_templates(request)

    demands = service.get_demands(
        category=category,
        min_priority=min_priority,
        limit=limit,
    )

    context = {
        "request": request,
        "demands": [demand_view_to_dict(d) for d in demands],
    }

    return templates.TemplateResponse(request, "demands/partials/demand_list.html", context)


@router.get("/{demand_id}", response_class=HTMLResponse)
async def demand_detail(
    request: Request,
    demand_id: str,
    service: DemandService = Depends(get_demand_service),
) -> HTMLResponse:
    """수요 상세 페이지를 렌더링한다.

    Args:
        request: FastAPI Request 객체
        demand_id: 수요 ID
        service: DemandService 인스턴스

    Returns:
        HTMLResponse: 수요 상세 HTML 페이지
    """
    templates = get_templates(request)

    detail = service.get_demand_detail(demand_id)

    if detail is None:
        context = {
            "request": request,
            "page_title": "Demand Not Found",
            "error": f"Demand with ID '{demand_id}' not found.",
        }
        return templates.TemplateResponse("demands/detail.html", context, status_code=404)

    context = {
        "request": request,
        "page_title": f"Demand: {detail.demand.text[:30]}...",
        "detail": demand_detail_to_dict(detail),
    }

    return templates.TemplateResponse(request, "demands/detail.html", context)


@router.get("/categories/stats", response_class=JSONResponse)
async def category_stats(
    service: DemandService = Depends(get_demand_service),
) -> JSONResponse:
    """카테고리별 분포를 JSON으로 반환한다.

    Args:
        service: DemandService 인스턴스

    Returns:
        JSONResponse: 카테고리별 수요 수
    """
    stats = service.get_category_stats()
    return JSONResponse(content=stats)
