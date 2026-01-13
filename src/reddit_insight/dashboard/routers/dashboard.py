"""대시보드 메인 라우터.

대시보드 홈 페이지와 요약 데이터를 제공하는 라우터.
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def get_templates(request: Request) -> Jinja2Templates:
    """Request에서 템플릿 인스턴스를 가져온다."""
    return request.app.state.templates


@router.get("/", response_class=HTMLResponse)
async def dashboard_home(request: Request) -> HTMLResponse:
    """대시보드 홈 페이지를 렌더링한다.

    Args:
        request: FastAPI Request 객체

    Returns:
        HTMLResponse: 렌더링된 HTML 페이지
    """
    templates = get_templates(request)

    # 임시 요약 데이터 (추후 DashboardService에서 가져옴)
    context = {
        "request": request,
        "page_title": "Dashboard",
        "summary": {
            "total_posts_analyzed": 0,
            "trending_keywords_count": 0,
            "demands_found": 0,
            "insights_generated": 0,
        },
        "recent_analyses": [],
    }

    return templates.TemplateResponse("dashboard/home.html", context)


@router.get("/summary", response_class=HTMLResponse)
async def dashboard_summary(request: Request) -> HTMLResponse:
    """대시보드 요약 데이터를 HTMX partial로 반환한다.

    Args:
        request: FastAPI Request 객체

    Returns:
        HTMLResponse: 요약 카드 HTML 파셜
    """
    templates = get_templates(request)

    context = {
        "request": request,
        "summary": {
            "total_posts_analyzed": 0,
            "trending_keywords_count": 0,
            "demands_found": 0,
            "insights_generated": 0,
        },
    }

    return templates.TemplateResponse("dashboard/partials/summary.html", context)
