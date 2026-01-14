"""LLM 분석 라우터.

LLM 기반 분석 기능을 제공하는 라우터:
- AI 요약: 게시물 핵심 내용 추출
- 카테고리화: 텍스트 자동 분류
- 심층 감성 분석: 뉘앙스 있는 감성 분석
- 인사이트 생성: 비즈니스 기회 해석
"""

import logging
from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from reddit_insight.dashboard.services.llm_service import (
    LLMService,
    get_llm_service,
)
from reddit_insight.dashboard.services_module import (
    DashboardService,
    get_dashboard_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard/llm", tags=["llm"])


def get_templates(request: Request) -> Jinja2Templates:
    """Request에서 템플릿 인스턴스를 가져온다."""
    return request.app.state.templates


# =============================================================================
# REQUEST MODELS
# =============================================================================


class CategorizeRequest(BaseModel):
    """카테고리화 요청 모델."""

    text: str = Field(..., min_length=1, max_length=5000)
    categories: list[str] | None = Field(default=None)


class SentimentRequest(BaseModel):
    """감성 분석 요청 모델."""

    text: str = Field(..., min_length=1, max_length=5000)


# =============================================================================
# PAGE ROUTES
# =============================================================================


@router.get("/", response_class=HTMLResponse)
async def llm_home(
    request: Request,
    llm_service: LLMService = Depends(get_llm_service),
    dashboard_service: DashboardService = Depends(get_dashboard_service),
) -> HTMLResponse:
    """LLM 분석 메인 페이지를 렌더링한다.

    Args:
        request: FastAPI Request 객체
        llm_service: LLMService 인스턴스
        dashboard_service: DashboardService 인스턴스

    Returns:
        HTMLResponse: 렌더링된 HTML 페이지
    """
    templates = get_templates(request)

    # LLM 서비스 상태 확인
    status = llm_service.get_status()

    # 최근 분석 목록 가져오기
    recent_analyses = dashboard_service.get_recent_analyses(limit=5)

    context = {
        "request": request,
        "page_title": "AI Analysis",
        "is_configured": status["configured"],
        "recent_analyses": [asdict(a) for a in recent_analyses],
        "default_categories": [
            "Feature Request",
            "Bug Report",
            "Question",
            "Discussion",
            "Review",
            "Complaint",
            "Suggestion",
            "Comparison",
        ],
    }

    return templates.TemplateResponse(request, "llm/index.html", context)


# =============================================================================
# SUMMARY ENDPOINTS
# =============================================================================


@router.get("/summary", response_class=HTMLResponse)
async def get_summary_partial(
    request: Request,
    subreddit: str = Query(..., description="서브레딧 이름"),
    llm_service: LLMService = Depends(get_llm_service),
    dashboard_service: DashboardService = Depends(get_dashboard_service),
) -> HTMLResponse:
    """AI 요약을 HTMX partial로 반환한다.

    Args:
        request: FastAPI Request 객체
        subreddit: 분석할 서브레딧
        llm_service: LLMService 인스턴스
        dashboard_service: DashboardService 인스턴스

    Returns:
        HTMLResponse: 요약 HTML 파셜
    """
    templates = get_templates(request)

    # 분석 데이터에서 게시물 가져오기
    analysis = dashboard_service.get_analysis_by_subreddit(subreddit)

    if not analysis or not analysis.get("raw_data"):
        context = {
            "request": request,
            "error": f"'{subreddit}' 서브레딧의 분석 데이터가 없습니다.",
        }
        return templates.TemplateResponse(request, "llm/partials/summary.html", context)

    posts = analysis["raw_data"].get("posts", [])

    try:
        summary = await llm_service.get_summary(subreddit, posts)
        context = {
            "request": request,
            "summary": asdict(summary),
            "subreddit": subreddit,
        }
    except Exception as e:
        logger.error("요약 생성 실패: %s", e)
        context = {
            "request": request,
            "error": f"요약 생성 중 오류가 발생했습니다: {e}",
        }

    return templates.TemplateResponse(request, "llm/partials/summary.html", context)


@router.get("/summary/json", response_class=JSONResponse)
async def get_summary_json(
    subreddit: str = Query(..., description="서브레딧 이름"),
    llm_service: LLMService = Depends(get_llm_service),
    dashboard_service: DashboardService = Depends(get_dashboard_service),
) -> JSONResponse:
    """AI 요약을 JSON으로 반환한다.

    Args:
        subreddit: 분석할 서브레딧
        llm_service: LLMService 인스턴스
        dashboard_service: DashboardService 인스턴스

    Returns:
        JSONResponse: 요약 데이터
    """
    analysis = dashboard_service.get_analysis_by_subreddit(subreddit)

    if not analysis or not analysis.get("raw_data"):
        return JSONResponse(
            content={"error": f"'{subreddit}' 서브레딧의 분석 데이터가 없습니다."},
            status_code=404,
        )

    posts = analysis["raw_data"].get("posts", [])

    try:
        summary = await llm_service.get_summary(subreddit, posts)
        return JSONResponse(content=asdict(summary))
    except Exception as e:
        logger.error("요약 생성 실패: %s", e)
        return JSONResponse(
            content={"error": f"요약 생성 실패: {e}"},
            status_code=500,
        )


# =============================================================================
# CATEGORIZATION ENDPOINTS
# =============================================================================


@router.post("/categorize", response_class=HTMLResponse)
async def categorize_text_partial(
    request: Request,
    text: str = Form(...),
    categories: str = Form(default=""),
    llm_service: LLMService = Depends(get_llm_service),
) -> HTMLResponse:
    """텍스트를 카테고리화하고 결과를 HTMX partial로 반환한다.

    Args:
        request: FastAPI Request 객체
        text: 분류할 텍스트
        categories: 카테고리 목록 (쉼표 구분, 선택)
        llm_service: LLMService 인스턴스

    Returns:
        HTMLResponse: 카테고리화 결과 HTML 파셜
    """
    templates = get_templates(request)

    # 카테고리 파싱
    category_list = None
    if categories.strip():
        category_list = [c.strip() for c in categories.split(",") if c.strip()]

    try:
        result = await llm_service.categorize_single(text, category_list)
        context = {
            "request": request,
            "result": asdict(result),
            "text_preview": text[:200] + "..." if len(text) > 200 else text,
        }
    except Exception as e:
        logger.error("카테고리화 실패: %s", e)
        context = {
            "request": request,
            "error": f"카테고리화 중 오류가 발생했습니다: {e}",
        }

    return templates.TemplateResponse(request, "llm/partials/category_result.html", context)


@router.post("/categorize/json", response_class=JSONResponse)
async def categorize_text_json(
    body: CategorizeRequest,
    llm_service: LLMService = Depends(get_llm_service),
) -> JSONResponse:
    """텍스트를 카테고리화하고 결과를 JSON으로 반환한다.

    Args:
        body: CategorizeRequest
        llm_service: LLMService 인스턴스

    Returns:
        JSONResponse: 카테고리화 결과
    """
    try:
        result = await llm_service.categorize_single(body.text, body.categories)
        return JSONResponse(content=asdict(result))
    except Exception as e:
        logger.error("카테고리화 실패: %s", e)
        return JSONResponse(
            content={"error": f"카테고리화 실패: {e}"},
            status_code=500,
        )


# =============================================================================
# SENTIMENT ENDPOINTS
# =============================================================================


@router.post("/sentiment", response_class=HTMLResponse)
async def analyze_sentiment_partial(
    request: Request,
    text: str = Form(...),
    llm_service: LLMService = Depends(get_llm_service),
) -> HTMLResponse:
    """심층 감성 분석 결과를 HTMX partial로 반환한다.

    Args:
        request: FastAPI Request 객체
        text: 분석할 텍스트
        llm_service: LLMService 인스턴스

    Returns:
        HTMLResponse: 감성 분석 결과 HTML 파셜
    """
    templates = get_templates(request)

    try:
        result = await llm_service.get_deep_sentiment(text)
        context = {
            "request": request,
            "result": asdict(result),
            "text_preview": text[:200] + "..." if len(text) > 200 else text,
        }
    except Exception as e:
        logger.error("감성 분석 실패: %s", e)
        context = {
            "request": request,
            "error": f"감성 분석 중 오류가 발생했습니다: {e}",
        }

    return templates.TemplateResponse(request, "llm/partials/sentiment_result.html", context)


@router.post("/sentiment/json", response_class=JSONResponse)
async def analyze_sentiment_json(
    body: SentimentRequest,
    llm_service: LLMService = Depends(get_llm_service),
) -> JSONResponse:
    """심층 감성 분석 결과를 JSON으로 반환한다.

    Args:
        body: SentimentRequest
        llm_service: LLMService 인스턴스

    Returns:
        JSONResponse: 감성 분석 결과
    """
    try:
        result = await llm_service.get_deep_sentiment(body.text)
        return JSONResponse(content=asdict(result))
    except Exception as e:
        logger.error("감성 분석 실패: %s", e)
        return JSONResponse(
            content={"error": f"감성 분석 실패: {e}"},
            status_code=500,
        )


# =============================================================================
# INSIGHTS ENDPOINTS
# =============================================================================


@router.get("/insights", response_class=HTMLResponse)
async def get_insights_partial(
    request: Request,
    subreddit: str = Query(..., description="서브레딧 이름"),
    llm_service: LLMService = Depends(get_llm_service),
    dashboard_service: DashboardService = Depends(get_dashboard_service),
) -> HTMLResponse:
    """AI 인사이트를 HTMX partial로 반환한다.

    Args:
        request: FastAPI Request 객체
        subreddit: 분석할 서브레딧
        llm_service: LLMService 인스턴스
        dashboard_service: DashboardService 인스턴스

    Returns:
        HTMLResponse: 인사이트 HTML 파셜
    """
    templates = get_templates(request)

    # 분석 데이터 가져오기
    analysis = dashboard_service.get_analysis_by_subreddit(subreddit)

    if not analysis:
        context = {
            "request": request,
            "error": f"'{subreddit}' 서브레딧의 분석 데이터가 없습니다.",
        }
        return templates.TemplateResponse(request, "llm/partials/insights.html", context)

    try:
        # 분석 데이터 준비
        analysis_data = {
            "trends": analysis.get("trends", {}),
            "demands": analysis.get("demands", {}),
            "sentiment": analysis.get("sentiment", {}),
            "competition": analysis.get("competition", {}),
        }

        insights = await llm_service.get_insights(analysis_data, subreddit)
        context = {
            "request": request,
            "insights": [asdict(i) for i in insights],
            "subreddit": subreddit,
        }
    except Exception as e:
        logger.error("인사이트 생성 실패: %s", e)
        context = {
            "request": request,
            "error": f"인사이트 생성 중 오류가 발생했습니다: {e}",
        }

    return templates.TemplateResponse(request, "llm/partials/insights.html", context)


@router.get("/insights/json", response_class=JSONResponse)
async def get_insights_json(
    subreddit: str = Query(..., description="서브레딧 이름"),
    llm_service: LLMService = Depends(get_llm_service),
    dashboard_service: DashboardService = Depends(get_dashboard_service),
) -> JSONResponse:
    """AI 인사이트를 JSON으로 반환한다.

    Args:
        subreddit: 분석할 서브레딧
        llm_service: LLMService 인스턴스
        dashboard_service: DashboardService 인스턴스

    Returns:
        JSONResponse: 인사이트 목록
    """
    analysis = dashboard_service.get_analysis_by_subreddit(subreddit)

    if not analysis:
        return JSONResponse(
            content={"error": f"'{subreddit}' 서브레딧의 분석 데이터가 없습니다."},
            status_code=404,
        )

    try:
        analysis_data = {
            "trends": analysis.get("trends", {}),
            "demands": analysis.get("demands", {}),
            "sentiment": analysis.get("sentiment", {}),
            "competition": analysis.get("competition", {}),
        }

        insights = await llm_service.get_insights(analysis_data, subreddit)
        return JSONResponse(content={"insights": [asdict(i) for i in insights]})
    except Exception as e:
        logger.error("인사이트 생성 실패: %s", e)
        return JSONResponse(
            content={"error": f"인사이트 생성 실패: {e}"},
            status_code=500,
        )


# =============================================================================
# STATUS ENDPOINT
# =============================================================================


@router.get("/status", response_class=JSONResponse)
async def get_status(
    llm_service: LLMService = Depends(get_llm_service),
) -> JSONResponse:
    """LLM 서비스 상태를 반환한다.

    Args:
        llm_service: LLMService 인스턴스

    Returns:
        JSONResponse: 서비스 상태
    """
    return JSONResponse(content=llm_service.get_status())
