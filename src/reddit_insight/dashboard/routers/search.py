"""검색 라우터.

글로벌 검색 기능을 제공하는 라우터.
키워드, 엔티티, 인사이트, 수요를 통합 검색한다.
"""


from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from reddit_insight.dashboard.services.search_service import (
    SearchService,
    get_search_service,
)

router = APIRouter(prefix="/search", tags=["search"])


def get_templates(request: Request) -> Jinja2Templates:
    """Request에서 템플릿 인스턴스를 가져온다."""
    return request.app.state.templates


@router.get("/", response_class=HTMLResponse)
async def search_home(
    request: Request,
    q: str = Query(default="", description="검색어"),
    type: str | None = Query(default=None, description="검색 유형 (keywords/entities/insights/demands)"),
    limit: int = Query(default=20, ge=1, le=100, description="결과 수"),
    service: SearchService = Depends(get_search_service),
) -> HTMLResponse:
    """검색 결과 페이지를 렌더링한다.

    Args:
        request: FastAPI Request 객체
        q: 검색어
        type: 검색 유형 필터
        limit: 결과 수 제한
        service: SearchService 인스턴스

    Returns:
        HTMLResponse: 렌더링된 HTML 페이지
    """
    templates = get_templates(request)

    # 검색어가 있으면 검색 수행
    results = None
    if q:
        results = service.search(query=q, search_type=type, limit=limit)

    context = {
        "request": request,
        "page_title": "Search",
        "query": q,
        "search_type": type,
        "limit": limit,
        "results": results,
        "search_types": [
            {"value": "", "label": "All"},
            {"value": "keywords", "label": "Keywords"},
            {"value": "entities", "label": "Entities"},
            {"value": "insights", "label": "Insights"},
            {"value": "demands", "label": "Demands"},
        ],
    }

    return templates.TemplateResponse(request, "search/index.html", context)


@router.get("/suggestions", response_class=HTMLResponse)
async def search_suggestions(
    request: Request,
    q: str = Query(default="", description="검색어"),
    limit: int = Query(default=5, ge=1, le=10, description="제안 수"),
    service: SearchService = Depends(get_search_service),
) -> HTMLResponse:
    """자동완성 제안을 HTMX partial로 반환한다.

    Args:
        request: FastAPI Request 객체
        q: 검색어
        limit: 제안 수 제한
        service: SearchService 인스턴스

    Returns:
        HTMLResponse: 제안 목록 HTML 파셜
    """
    templates = get_templates(request)

    suggestions = []
    if q and len(q) >= 2:
        suggestions = service.get_suggestions(query=q, limit=limit)

    context = {
        "request": request,
        "suggestions": suggestions,
        "query": q,
    }

    return templates.TemplateResponse(request, "search/partials/suggestions.html", context)


@router.get("/results", response_class=HTMLResponse)
async def search_results_partial(
    request: Request,
    q: str = Query(default="", description="검색어"),
    type: str | None = Query(default=None, description="검색 유형"),
    limit: int = Query(default=20, ge=1, le=100, description="결과 수"),
    service: SearchService = Depends(get_search_service),
) -> HTMLResponse:
    """검색 결과를 HTMX partial로 반환한다.

    Args:
        request: FastAPI Request 객체
        q: 검색어
        type: 검색 유형 필터
        limit: 결과 수 제한
        service: SearchService 인스턴스

    Returns:
        HTMLResponse: 검색 결과 HTML 파셜
    """
    templates = get_templates(request)

    results = None
    if q:
        results = service.search(query=q, search_type=type, limit=limit)

    context = {
        "request": request,
        "query": q,
        "results": results,
    }

    return templates.TemplateResponse(request, "search/partials/results.html", context)
