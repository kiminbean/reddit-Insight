"""대시보드 메인 라우터.

대시보드 홈 페이지와 요약 데이터를 제공하는 라우터.
"""

from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from reddit_insight.dashboard.data_store import get_all_subreddits, load_analysis_by_id
from reddit_insight.dashboard.services import (
    DashboardService,
    get_dashboard_service,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def get_templates(request: Request) -> Jinja2Templates:
    """Request에서 템플릿 인스턴스를 가져온다."""
    return request.app.state.templates


@router.get("/", response_class=HTMLResponse)
async def dashboard_home(
    request: Request,
    service: DashboardService = Depends(get_dashboard_service),
) -> HTMLResponse:
    """대시보드 홈 페이지를 렌더링한다.

    Args:
        request: FastAPI Request 객체
        service: DashboardService 인스턴스

    Returns:
        HTMLResponse: 렌더링된 HTML 페이지
    """
    templates = get_templates(request)

    summary = service.get_summary()
    recent_analyses = service.get_recent_analyses(limit=5)

    context = {
        "request": request,
        "page_title": "Dashboard",
        "summary": asdict(summary),
        "recent_analyses": recent_analyses,
    }

    return templates.TemplateResponse(request, "dashboard/home.html", context)


@router.get("/summary", response_class=HTMLResponse)
async def dashboard_summary(
    request: Request,
    service: DashboardService = Depends(get_dashboard_service),
) -> HTMLResponse:
    """대시보드 요약 데이터를 HTMX partial로 반환한다.

    Args:
        request: FastAPI Request 객체
        service: DashboardService 인스턴스

    Returns:
        HTMLResponse: 요약 카드 HTML 파셜
    """
    templates = get_templates(request)

    summary = service.get_summary()

    context = {
        "request": request,
        "summary": asdict(summary),
    }

    return templates.TemplateResponse(request, "dashboard/partials/summary.html", context)


@router.get("/analyze", response_class=HTMLResponse)
async def analyze_page(
    request: Request,
    service: DashboardService = Depends(get_dashboard_service),
) -> HTMLResponse:
    """분석 시작 페이지를 렌더링한다.

    Args:
        request: FastAPI Request 객체
        service: DashboardService 인스턴스

    Returns:
        HTMLResponse: 렌더링된 HTML 페이지
    """
    templates = get_templates(request)

    # 이전에 분석된 서브레딧 목록
    analyzed_subreddits = get_all_subreddits()

    context = {
        "request": request,
        "page_title": "Start Analysis",
        "analyzed_subreddits": analyzed_subreddits,
    }

    return templates.TemplateResponse(request, "dashboard/analyze.html", context)


@router.get("/analysis/{analysis_id}", response_class=HTMLResponse)
async def analysis_detail(
    request: Request,
    analysis_id: int,
) -> HTMLResponse:
    """특정 분석 결과의 상세 페이지를 렌더링한다.

    Args:
        request: FastAPI Request 객체
        analysis_id: 조회할 분석 결과 ID

    Returns:
        HTMLResponse: 렌더링된 HTML 페이지
    """
    templates = get_templates(request)

    # DB에서 분석 결과 로드 (연결 오류 처리)
    try:
        analysis_data = load_analysis_by_id(analysis_id)
    except (ConnectionError, OSError) as e:
        # 데이터베이스 연결 오류 시 500 상태로 에러 페이지 렌더링
        context = {
            "request": request,
            "page_title": "Service Unavailable",
            "analysis": None,
            "analysis_id": analysis_id,
            "error_message": f"Unable to load analysis data. Please try again later. (Error: {type(e).__name__})",
        }
        return templates.TemplateResponse(
            request, "dashboard/analysis_detail.html", context, status_code=500
        )

    if analysis_data is None:
        # 404 상태로 에러 페이지 렌더링
        context = {
            "request": request,
            "page_title": "Analysis Not Found",
            "analysis": None,
            "analysis_id": analysis_id,
            "error_message": f"Analysis with ID {analysis_id} could not be found.",
        }
        return templates.TemplateResponse(
            request, "dashboard/analysis_detail.html", context, status_code=404
        )

    # 주요 키워드 Top 5 추출
    top_keywords = []
    if analysis_data.keywords:
        sorted_keywords = sorted(
            analysis_data.keywords,
            key=lambda x: x.get("count", 0),
            reverse=True,
        )
        top_keywords = sorted_keywords[:5]

    # 주요 수요 Top 3 추출
    top_demands = []
    if analysis_data.demands and "items" in analysis_data.demands:
        demand_items = analysis_data.demands.get("items", [])
        sorted_demands = sorted(
            demand_items,
            key=lambda x: x.get("urgency_score", 0),
            reverse=True,
        )
        top_demands = sorted_demands[:3]

    # 주요 인사이트 Top 3 추출
    top_insights = []
    if analysis_data.insights:
        sorted_insights = sorted(
            analysis_data.insights,
            key=lambda x: x.get("priority", 0),
            reverse=True,
        )
        top_insights = sorted_insights[:3]

    context = {
        "request": request,
        "page_title": f"Analysis: r/{analysis_data.subreddit}",
        "analysis": analysis_data,
        "analysis_id": analysis_id,
        "top_keywords": top_keywords,
        "top_demands": top_demands,
        "top_insights": top_insights,
    }

    return templates.TemplateResponse(request, "dashboard/analysis_detail.html", context)
