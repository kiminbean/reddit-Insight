"""트렌드 시각화 라우터.

키워드 트렌드와 Rising 키워드를 시각화하는 라우터.
"""

from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from reddit_insight.dashboard.trend_service import (
    TrendService,
    get_trend_service,
)

router = APIRouter(prefix="/dashboard/trends", tags=["trends"])


def get_templates(request: Request) -> Jinja2Templates:
    """Request에서 템플릿 인스턴스를 가져온다."""
    return request.app.state.templates


@router.get("/", response_class=HTMLResponse)
async def trends_home(
    request: Request,
    subreddit: str | None = Query(default=None, description="필터링할 서브레딧"),
    days: int = Query(default=7, ge=1, le=30, description="분석 기간(일)"),
    limit: int = Query(default=20, ge=1, le=100, description="표시할 키워드 수"),
    service: TrendService = Depends(get_trend_service),
) -> HTMLResponse:
    """트렌드 메인 페이지를 렌더링한다.

    Args:
        request: FastAPI Request 객체
        subreddit: 필터링할 서브레딧 (None이면 전체)
        days: 분석 기간
        limit: 표시할 키워드 수
        service: TrendService 인스턴스

    Returns:
        HTMLResponse: 렌더링된 HTML 페이지
    """
    templates = get_templates(request)

    top_keywords = service.get_top_keywords(subreddit=subreddit, days=days, limit=limit)
    rising_keywords = service.get_rising_keywords(subreddit=subreddit, limit=limit)

    context = {
        "request": request,
        "page_title": "Trends",
        "top_keywords": [kw.__dict__ for kw in top_keywords],
        "rising_keywords": [kw.__dict__ for kw in rising_keywords],
        "filters": {
            "subreddit": subreddit,
            "days": days,
            "limit": limit,
        },
    }

    return templates.TemplateResponse("trends/index.html", context)


@router.get("/keywords", response_class=HTMLResponse)
async def keywords_partial(
    request: Request,
    subreddit: str | None = Query(default=None, description="필터링할 서브레딧"),
    days: int = Query(default=7, ge=1, le=30, description="분석 기간(일)"),
    limit: int = Query(default=20, ge=1, le=100, description="표시할 키워드 수"),
    service: TrendService = Depends(get_trend_service),
) -> HTMLResponse:
    """키워드 목록을 HTMX partial로 반환한다.

    Args:
        request: FastAPI Request 객체
        subreddit: 필터링할 서브레딧
        days: 분석 기간
        limit: 표시할 키워드 수
        service: TrendService 인스턴스

    Returns:
        HTMLResponse: 키워드 목록 HTML 파셜
    """
    templates = get_templates(request)

    top_keywords = service.get_top_keywords(subreddit=subreddit, days=days, limit=limit)

    context = {
        "request": request,
        "top_keywords": [kw.__dict__ for kw in top_keywords],
    }

    return templates.TemplateResponse("trends/partials/keyword_list.html", context)


@router.get("/rising", response_class=HTMLResponse)
async def rising_partial(
    request: Request,
    subreddit: str | None = Query(default=None, description="필터링할 서브레딧"),
    limit: int = Query(default=20, ge=1, le=100, description="표시할 키워드 수"),
    service: TrendService = Depends(get_trend_service),
) -> HTMLResponse:
    """Rising 키워드를 HTMX partial로 반환한다.

    Args:
        request: FastAPI Request 객체
        subreddit: 필터링할 서브레딧
        limit: 표시할 키워드 수
        service: TrendService 인스턴스

    Returns:
        HTMLResponse: Rising 키워드 목록 HTML 파셜
    """
    templates = get_templates(request)

    rising_keywords = service.get_rising_keywords(subreddit=subreddit, limit=limit)

    context = {
        "request": request,
        "rising_keywords": [kw.__dict__ for kw in rising_keywords],
    }

    return templates.TemplateResponse("trends/partials/rising_list.html", context)


@router.get("/chart-data", response_class=JSONResponse)
async def chart_data(
    keyword: str = Query(description="타임라인을 조회할 키워드"),
    days: int = Query(default=7, ge=1, le=30, description="분석 기간(일)"),
    service: TrendService = Depends(get_trend_service),
) -> JSONResponse:
    """키워드 타임라인 차트 데이터를 JSON으로 반환한다.

    Args:
        keyword: 조회할 키워드
        days: 분석 기간
        service: TrendService 인스턴스

    Returns:
        JSONResponse: Chart.js 형식의 데이터
    """
    timeline = service.get_keyword_timeline(keyword=keyword, days=days)

    # Chart.js 형식으로 변환
    chart_data = {
        "labels": [str(point.date) for point in timeline],
        "datasets": [
            {
                "label": keyword,
                "data": [point.count for point in timeline],
                "borderColor": "rgb(59, 130, 246)",
                "backgroundColor": "rgba(59, 130, 246, 0.1)",
                "fill": True,
                "tension": 0.3,
            }
        ],
    }

    return JSONResponse(content=chart_data)


@router.get("/top-keywords-chart", response_class=JSONResponse)
async def top_keywords_chart_data(
    subreddit: str | None = Query(default=None, description="필터링할 서브레딧"),
    days: int = Query(default=7, ge=1, le=30, description="분석 기간(일)"),
    limit: int = Query(default=10, ge=1, le=20, description="표시할 키워드 수"),
    service: TrendService = Depends(get_trend_service),
) -> JSONResponse:
    """상위 키워드 바 차트 데이터를 JSON으로 반환한다.

    Args:
        subreddit: 필터링할 서브레딧
        days: 분석 기간
        limit: 표시할 키워드 수
        service: TrendService 인스턴스

    Returns:
        JSONResponse: Chart.js 형식의 바 차트 데이터
    """
    top_keywords = service.get_top_keywords(subreddit=subreddit, days=days, limit=limit)

    chart_data = {
        "labels": [kw.keyword for kw in top_keywords],
        "datasets": [
            {
                "label": "Frequency",
                "data": [kw.frequency for kw in top_keywords],
                "backgroundColor": [
                    "rgba(59, 130, 246, 0.8)" if kw.trend_direction == "up"
                    else "rgba(239, 68, 68, 0.8)" if kw.trend_direction == "down"
                    else "rgba(156, 163, 175, 0.8)"
                    for kw in top_keywords
                ],
                "borderColor": [
                    "rgb(59, 130, 246)" if kw.trend_direction == "up"
                    else "rgb(239, 68, 68)" if kw.trend_direction == "down"
                    else "rgb(156, 163, 175)"
                    for kw in top_keywords
                ],
                "borderWidth": 1,
            }
        ],
    }

    return JSONResponse(content=chart_data)
