"""비교 분석 라우터.

여러 서브레딧의 비교 분석 기능을 제공하는 라우터:
- 크로스 서브레딧 트렌드 비교
- 벤치마킹 (키워드, 감성, 활동량)
- 유사도 분석
"""

import logging
from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from reddit_insight.dashboard.services.comparison_service import (
    ComparisonService,
    ComparisonView,
    get_comparison_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard/comparison", tags=["comparison"])


def get_templates(request: Request) -> Jinja2Templates:
    """Request에서 템플릿 인스턴스를 가져온다."""
    return request.app.state.templates


# =============================================================================
# REQUEST MODELS
# =============================================================================


class CompareRequest(BaseModel):
    """비교 분석 요청 모델."""

    subreddits: list[str] = Field(
        ...,
        min_length=2,
        max_length=5,
        description="비교할 서브레딧 목록 (2-5개)",
    )


# =============================================================================
# PAGE ROUTES
# =============================================================================


@router.get("/", response_class=HTMLResponse)
async def comparison_home(
    request: Request,
    comparison_service: ComparisonService = Depends(get_comparison_service),
) -> HTMLResponse:
    """비교 분석 메인 페이지를 렌더링한다.

    Args:
        request: FastAPI Request 객체
        comparison_service: ComparisonService 인스턴스

    Returns:
        HTMLResponse: 렌더링된 HTML 페이지
    """
    templates = get_templates(request)

    # 비교 가능한 서브레딧 목록 가져오기
    available_subreddits = comparison_service.get_available_subreddits()

    context = {
        "request": request,
        "page_title": "Subreddit Comparison",
        "available_subreddits": available_subreddits,
        "min_subreddits": 2,
        "max_subreddits": 5,
    }

    return templates.TemplateResponse(request, "comparison/index.html", context)


# =============================================================================
# ANALYSIS ENDPOINTS
# =============================================================================


@router.post("/analyze", response_class=HTMLResponse)
async def analyze_comparison(
    request: Request,
    comparison_service: ComparisonService = Depends(get_comparison_service),
) -> HTMLResponse:
    """비교 분석을 실행하고 결과를 HTMX partial로 반환한다.

    Args:
        request: FastAPI Request 객체
        comparison_service: ComparisonService 인스턴스

    Returns:
        HTMLResponse: 분석 결과 HTML 파셜
    """
    templates = get_templates(request)

    # Form 데이터에서 서브레딧 목록 추출
    form_data = await request.form()
    subreddits = form_data.getlist("subreddits")

    if not subreddits:
        # 쉼표로 구분된 경우 처리
        subreddits_str = form_data.get("subreddits_str", "")
        if subreddits_str:
            subreddits = [s.strip() for s in str(subreddits_str).split(",") if s.strip()]

    # 유효성 검사
    if len(subreddits) < 2:
        context = {
            "request": request,
            "error": "비교 분석에는 최소 2개의 서브레딧이 필요합니다.",
        }
        return templates.TemplateResponse(request, "comparison/partials/results.html", context)

    if len(subreddits) > 5:
        context = {
            "request": request,
            "error": "비교 분석은 최대 5개의 서브레딧까지만 지원합니다.",
        }
        return templates.TemplateResponse(request, "comparison/partials/results.html", context)

    try:
        result = await comparison_service.compare_subreddits(subreddits)

        if result is None:
            context = {
                "request": request,
                "error": "선택한 서브레딧의 분석 데이터가 없습니다. 먼저 분석을 실행하세요.",
            }
            return templates.TemplateResponse(request, "comparison/partials/results.html", context)

        context = {
            "request": request,
            "result": asdict(result),
            "subreddits": result.subreddits,
        }
    except ValueError as e:
        context = {
            "request": request,
            "error": str(e),
        }
    except Exception as e:
        logger.error("비교 분석 실패: %s", e)
        context = {
            "request": request,
            "error": f"비교 분석 중 오류가 발생했습니다: {e}",
        }

    return templates.TemplateResponse(request, "comparison/partials/results.html", context)


@router.get("/analyze/json", response_class=JSONResponse)
async def analyze_comparison_json(
    subreddits: list[str] = Query(..., description="비교할 서브레딧 목록"),
    comparison_service: ComparisonService = Depends(get_comparison_service),
) -> JSONResponse:
    """비교 분석 결과를 JSON으로 반환한다.

    Args:
        subreddits: 비교할 서브레딧 목록
        comparison_service: ComparisonService 인스턴스

    Returns:
        JSONResponse: 비교 분석 결과
    """
    try:
        result = await comparison_service.compare_subreddits(subreddits)

        if result is None:
            return JSONResponse(
                content={"error": "선택한 서브레딧의 분석 데이터가 없습니다."},
                status_code=404,
            )

        return JSONResponse(content=asdict(result))

    except ValueError as e:
        return JSONResponse(
            content={"error": str(e)},
            status_code=400,
        )
    except Exception as e:
        logger.error("비교 분석 실패: %s", e)
        return JSONResponse(
            content={"error": f"비교 분석 실패: {e}"},
            status_code=500,
        )


@router.get("/chart-data", response_class=JSONResponse)
async def get_chart_data(
    subreddits: list[str] = Query(..., description="비교할 서브레딧 목록"),
    comparison_service: ComparisonService = Depends(get_comparison_service),
) -> JSONResponse:
    """비교 차트 데이터를 JSON으로 반환한다.

    Args:
        subreddits: 비교할 서브레딧 목록
        comparison_service: ComparisonService 인스턴스

    Returns:
        JSONResponse: 차트 데이터
    """
    try:
        result = await comparison_service.compare_subreddits(subreddits)

        if result is None:
            return JSONResponse(
                content={"error": "선택한 서브레딧의 분석 데이터가 없습니다."},
                status_code=404,
            )

        return JSONResponse(content=result.chart_data)

    except ValueError as e:
        return JSONResponse(
            content={"error": str(e)},
            status_code=400,
        )
    except Exception as e:
        logger.error("차트 데이터 생성 실패: %s", e)
        return JSONResponse(
            content={"error": f"차트 데이터 생성 실패: {e}"},
            status_code=500,
        )


@router.get("/available", response_class=JSONResponse)
async def get_available_subreddits(
    comparison_service: ComparisonService = Depends(get_comparison_service),
) -> JSONResponse:
    """비교 가능한 서브레딧 목록을 반환한다.

    Args:
        comparison_service: ComparisonService 인스턴스

    Returns:
        JSONResponse: 서브레딧 목록
    """
    subreddits = comparison_service.get_available_subreddits()
    return JSONResponse(content={"subreddits": subreddits})
