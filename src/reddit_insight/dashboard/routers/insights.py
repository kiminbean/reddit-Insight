"""인사이트 시각화 라우터.

비즈니스 인사이트, 추천, 기회 랭킹을 시각화하는 라우터.
"""

from typing import Any

from fastapi import APIRouter, Depends, Path, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from reddit_insight.dashboard.services.insight_service import (
    InsightService,
    get_insight_service,
)

router = APIRouter(prefix="/dashboard/insights", tags=["insights"])


def get_templates(request: Request) -> Jinja2Templates:
    """Request에서 템플릿 인스턴스를 가져온다."""
    return request.app.state.templates


@router.get("/", response_class=HTMLResponse)
async def insights_home(
    request: Request,
    insight_type: str | None = Query(default=None, description="인사이트 유형 필터"),
    min_confidence: float = Query(default=0.0, ge=0.0, le=1.0, description="최소 신뢰도"),
    limit: int = Query(default=20, ge=1, le=100, description="표시할 인사이트 수"),
    service: InsightService = Depends(get_insight_service),
) -> HTMLResponse:
    """인사이트 메인 페이지를 렌더링한다.

    Args:
        request: FastAPI Request 객체
        insight_type: 필터링할 인사이트 유형 (None이면 전체)
        min_confidence: 최소 신뢰도 필터
        limit: 표시할 인사이트 수
        service: InsightService 인스턴스

    Returns:
        HTMLResponse: 렌더링된 HTML 페이지
    """
    templates = get_templates(request)

    insights = service.get_insights(
        insight_type=insight_type,
        min_confidence=min_confidence,
        limit=limit,
    )
    recommendations = service.get_recommendations(top_n=5)
    opportunities = service.get_opportunity_ranking(limit=10)

    # 인사이트 유형 목록 생성 (필터용)
    insight_types = service.get_insight_types()

    context = {
        "request": request,
        "page_title": "Insights",
        "insights": [i.__dict__ for i in insights],
        "recommendations": [r.__dict__ for r in recommendations],
        "opportunities": [o.__dict__ for o in opportunities],
        "insight_types": insight_types,
        "filters": {
            "insight_type": insight_type,
            "min_confidence": min_confidence,
            "limit": limit,
        },
    }

    return templates.TemplateResponse("insights/index.html", context)


@router.get("/list", response_class=HTMLResponse)
async def insights_list_partial(
    request: Request,
    insight_type: str | None = Query(default=None, description="인사이트 유형 필터"),
    min_confidence: float = Query(default=0.0, ge=0.0, le=1.0, description="최소 신뢰도"),
    limit: int = Query(default=20, ge=1, le=100, description="표시할 인사이트 수"),
    service: InsightService = Depends(get_insight_service),
) -> HTMLResponse:
    """인사이트 목록을 HTMX partial로 반환한다.

    Args:
        request: FastAPI Request 객체
        insight_type: 필터링할 인사이트 유형
        min_confidence: 최소 신뢰도 필터
        limit: 표시할 인사이트 수
        service: InsightService 인스턴스

    Returns:
        HTMLResponse: 인사이트 목록 HTML 파셜
    """
    templates = get_templates(request)

    insights = service.get_insights(
        insight_type=insight_type,
        min_confidence=min_confidence,
        limit=limit,
    )

    context = {
        "request": request,
        "insights": [i.__dict__ for i in insights],
    }

    return templates.TemplateResponse("insights/partials/insight_list.html", context)


@router.get("/recommendations", response_class=HTMLResponse)
async def recommendations_partial(
    request: Request,
    top_n: int = Query(default=10, ge=1, le=50, description="표시할 추천 수"),
    service: InsightService = Depends(get_insight_service),
) -> HTMLResponse:
    """추천 목록을 HTMX partial로 반환한다.

    Args:
        request: FastAPI Request 객체
        top_n: 표시할 추천 수
        service: InsightService 인스턴스

    Returns:
        HTMLResponse: 추천 목록 HTML 파셜
    """
    templates = get_templates(request)

    recommendations = service.get_recommendations(top_n=top_n)

    context = {
        "request": request,
        "recommendations": [r.__dict__ for r in recommendations],
    }

    return templates.TemplateResponse("insights/partials/recommendation_list.html", context)


@router.get("/opportunities", response_class=HTMLResponse)
async def opportunities_partial(
    request: Request,
    limit: int = Query(default=20, ge=1, le=100, description="표시할 기회 수"),
    service: InsightService = Depends(get_insight_service),
) -> HTMLResponse:
    """기회 랭킹을 HTMX partial로 반환한다.

    Args:
        request: FastAPI Request 객체
        limit: 표시할 기회 수
        service: InsightService 인스턴스

    Returns:
        HTMLResponse: 기회 랭킹 테이블 HTML 파셜
    """
    templates = get_templates(request)

    opportunities = service.get_opportunity_ranking(limit=limit)

    context = {
        "request": request,
        "opportunities": [o.__dict__ for o in opportunities],
    }

    return templates.TemplateResponse("insights/partials/opportunity_table.html", context)


@router.get("/{insight_id}", response_class=HTMLResponse)
async def insight_detail(
    request: Request,
    insight_id: str = Path(description="인사이트 ID"),
    service: InsightService = Depends(get_insight_service),
) -> HTMLResponse:
    """인사이트 상세 페이지를 렌더링한다.

    Args:
        request: FastAPI Request 객체
        insight_id: 인사이트 ID
        service: InsightService 인스턴스

    Returns:
        HTMLResponse: 렌더링된 HTML 페이지
    """
    templates = get_templates(request)

    insight = service.get_insight_detail(insight_id=insight_id)

    if insight is None:
        # 404 페이지 또는 에러 처리
        context = {
            "request": request,
            "page_title": "Insight Not Found",
            "error_message": f"Insight with ID '{insight_id}' not found.",
        }
        return templates.TemplateResponse("insights/detail.html", context, status_code=404)

    context = {
        "request": request,
        "page_title": f"Insight: {insight.title}",
        "insight": insight.__dict__,
    }

    return templates.TemplateResponse("insights/detail.html", context)


@router.get("/chart/score-breakdown/{insight_id}", response_class=JSONResponse)
async def insight_score_chart_data(
    insight_id: str = Path(description="인사이트 ID"),
    service: InsightService = Depends(get_insight_service),
) -> JSONResponse:
    """인사이트 스코어 breakdown 차트 데이터를 JSON으로 반환한다.

    Args:
        insight_id: 인사이트 ID
        service: InsightService 인스턴스

    Returns:
        JSONResponse: Chart.js 형식의 레이더 차트 데이터
    """
    score_data = service.get_insight_score_breakdown(insight_id=insight_id)

    if score_data is None:
        return JSONResponse(content={"error": "Insight not found"}, status_code=404)

    # Chart.js 레이더 차트 형식으로 변환
    chart_data = {
        "labels": score_data["labels"],
        "datasets": [
            {
                "label": "Score",
                "data": score_data["scores"],
                "backgroundColor": "rgba(59, 130, 246, 0.2)",
                "borderColor": "rgb(59, 130, 246)",
                "borderWidth": 2,
                "pointBackgroundColor": "rgb(59, 130, 246)",
            }
        ],
    }

    return JSONResponse(content=chart_data)


@router.get("/chart/grade-distribution", response_class=JSONResponse)
async def grade_distribution_chart_data(
    service: InsightService = Depends(get_insight_service),
) -> JSONResponse:
    """등급 분포 차트 데이터를 JSON으로 반환한다.

    Args:
        service: InsightService 인스턴스

    Returns:
        JSONResponse: Chart.js 형식의 도넛 차트 데이터
    """
    distribution = service.get_grade_distribution()

    # Chart.js 도넛 차트 형식으로 변환
    chart_data = {
        "labels": list(distribution.keys()),
        "datasets": [
            {
                "data": list(distribution.values()),
                "backgroundColor": [
                    "rgba(34, 197, 94, 0.8)",   # A - green
                    "rgba(59, 130, 246, 0.8)",  # B - blue
                    "rgba(234, 179, 8, 0.8)",   # C - yellow
                    "rgba(249, 115, 22, 0.8)",  # D - orange
                    "rgba(239, 68, 68, 0.8)",   # F - red
                ],
                "borderWidth": 1,
            }
        ],
    }

    return JSONResponse(content=chart_data)
