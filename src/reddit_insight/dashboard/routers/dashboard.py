"""대시보드 메인 라우터.

대시보드 홈 페이지와 요약 데이터를 제공하는 라우터.
"""

from dataclasses import asdict

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

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

    return templates.TemplateResponse("dashboard/home.html", context)


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

    return templates.TemplateResponse("dashboard/partials/summary.html", context)
