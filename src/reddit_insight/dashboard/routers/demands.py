"""수요 분석 라우터.

수요 발견 및 우선순위 분석 결과를 시각화하는 라우터.
"""

from dataclasses import dataclass
from hashlib import md5
from typing import Any

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
from reddit_insight.dashboard.data_store import get_current_data
from reddit_insight.dashboard.pagination import paginate

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
        # 실제 데이터에서 수요 정보 가져오기
        data = get_current_data()
        if data and data.demands and data.demands.get("top_opportunities"):
            result: list[DemandView] = []
            for i, opp in enumerate(data.demands["top_opportunities"]):
                priority_score = opp.get("priority_score", 50)

                # 최소 우선순위 필터링
                if priority_score < min_priority:
                    continue

                # 카테고리는 실제 데이터에서 지정되지 않으므로 business_potential로 추론
                inferred_category = "unmet_need"
                if opp.get("business_potential") == "high":
                    inferred_category = "willingness_to_pay"
                elif opp.get("business_potential") == "low":
                    inferred_category = "feature_request"

                # 카테고리 필터링
                if category is not None:
                    cat_value = category.value if isinstance(category, DemandCategory) else category
                    if inferred_category != cat_value:
                        continue

                result.append(
                    DemandView(
                        id=f"demand_{i:03d}",
                        category=inferred_category,
                        text=opp.get("representative", "")[:100],
                        priority_score=priority_score,
                        source_count=opp.get("size", 1),
                        business_potential=opp.get("business_potential", "medium"),
                        keywords=None,
                    )
                )

                if len(result) >= limit:
                    break

            if result:
                return result

        # 실제 데이터가 없으면 빈 결과 반환 (mock 데이터 사용 금지)
        if self._cached_report is None:
            return []

        result = []

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
        # 실제 데이터에서 수요 상세 정보 가져오기
        data = get_current_data()
        if data and data.demands and data.demands.get("top_opportunities"):
            for i, opp in enumerate(data.demands["top_opportunities"]):
                opp_id = f"demand_{i:03d}"
                if opp_id == demand_id:
                    # 카테고리 추론
                    inferred_category = "unmet_need"
                    if opp.get("business_potential") == "high":
                        inferred_category = "willingness_to_pay"
                    elif opp.get("business_potential") == "low":
                        inferred_category = "feature_request"

                    view = DemandView(
                        id=opp_id,
                        category=inferred_category,
                        text=opp.get("representative", "")[:100],
                        priority_score=opp.get("priority_score", 50),
                        source_count=opp.get("size", 1),
                        business_potential=opp.get("business_potential", "medium"),
                        keywords=None,
                    )
                    return DemandDetail(
                        demand=view,
                        frequency_score=opp.get("priority_score", 50) * 0.3,
                        payment_intent_score=opp.get("priority_score", 50) * 0.25,
                        urgency_score=opp.get("priority_score", 50) * 0.25,
                        recency_score=opp.get("priority_score", 50) * 0.2,
                        sample_texts=opp.get("sample_texts", []),
                    )

        # 캐시된 리포트에서 검색
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
        # 실제 데이터에서 카테고리 통계 가져오기
        data = get_current_data()
        if data and data.demands and data.demands.get("by_category"):
            return data.demands["by_category"]

        # 캐시된 리포트에서 통계 반환
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
        # 실제 데이터에서 권장사항 가져오기
        data = get_current_data()
        if data and data.demands and data.demands.get("recommendations"):
            return data.demands["recommendations"]

        if self._cached_report is None:
            return []

        return self._cached_report.recommendations


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
    category: str | None = Query(None, description="카테고리 필터"),
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
        return templates.TemplateResponse(request, "demands/detail.html", context, status_code=404)

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


# =============================================================================
# PAGINATED API ENDPOINTS
# =============================================================================


@router.get("/api/list", response_class=JSONResponse)
async def get_demands_paginated(
    category: str | None = Query(None, description="카테고리 필터"),
    min_priority: float = Query(0.0, ge=0.0, le=100.0, description="최소 우선순위"),
    page: int = Query(default=1, ge=1, description="페이지 번호"),
    per_page: int = Query(default=20, ge=1, le=100, description="페이지당 항목 수"),
    service: DemandService = Depends(get_demand_service),
) -> JSONResponse:
    """페이지네이션된 수요 목록을 JSON으로 반환한다.

    Args:
        category: 카테고리 필터
        min_priority: 최소 우선순위 점수
        page: 페이지 번호 (1-indexed)
        per_page: 페이지당 항목 수
        service: DemandService 인스턴스

    Returns:
        JSONResponse: 페이지네이션된 수요 목록
        {
            "items": [...],
            "meta": { "total": N, "page": 1, "per_page": 20, "pages": M }
        }
    """
    # 모든 수요 가져오기 (최대 200개)
    all_demands = service.get_demands(
        category=category,
        min_priority=min_priority,
        limit=200,
    )

    # 페이지네이션 적용
    paginated = paginate(all_demands, page=page, per_page=per_page)

    # 응답 생성
    return JSONResponse(content=paginated.to_dict(item_converter=demand_view_to_dict))
