"""인사이트 시각화 라우터.

비즈니스 인사이트, 추천, 기회 랭킹을 시각화하는 라우터.
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Path, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.templating import Jinja2Templates

from reddit_insight.dashboard.pagination import paginate
from reddit_insight.dashboard.services.insight_service import (
    InsightService,
    get_insight_service,
)
from reddit_insight.dashboard.services.report_service import (
    ReportService,
    get_report_service,
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

    return templates.TemplateResponse(request, "insights/index.html", context)


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

    return templates.TemplateResponse(request, "insights/partials/insight_list.html", context)


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

    return templates.TemplateResponse(request, "insights/partials/recommendation_list.html", context)


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

    return templates.TemplateResponse(request, "insights/partials/opportunity_table.html", context)


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
        return templates.TemplateResponse(request, "insights/detail.html", context, status_code=404)

    context = {
        "request": request,
        "page_title": f"Insight: {insight.title}",
        "insight": insight.__dict__,
    }

    return templates.TemplateResponse(request, "insights/detail.html", context)


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


# =============================================================================
# REPORT GENERATION ENDPOINTS
# =============================================================================


@router.get("/report/generate", response_class=HTMLResponse)
async def report_page(
    request: Request,
    service: ReportService = Depends(get_report_service),
) -> HTMLResponse:
    """보고서 생성 페이지를 렌더링한다.

    Args:
        request: FastAPI Request 객체
        service: ReportService 인스턴스

    Returns:
        HTMLResponse: 보고서 생성 페이지
    """
    templates = get_templates(request)

    # 미리보기용 보고서 데이터 생성
    report = service.generate_report()

    context = {
        "request": request,
        "page_title": "Generate Report",
        "report": report,
        "has_data": report is not None,
    }

    return templates.TemplateResponse(request, "insights/report.html", context)


@router.get("/report/download")
async def download_report(
    subreddit: str | None = Query(default=None, description="서브레딧 이름"),
    service: ReportService = Depends(get_report_service),
) -> Response:
    """마크다운 보고서를 다운로드한다.

    Args:
        subreddit: 서브레딧 이름
        service: ReportService 인스턴스

    Returns:
        Response: 마크다운 파일 다운로드
    """
    markdown_content = service.generate_markdown_report(subreddit)

    if not markdown_content:
        return JSONResponse(
            content={"error": "No data available for report generation"},
            status_code=404,
        )

    # 파일명 생성
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    filename = f"business_report_{subreddit or 'all'}_{timestamp}.md"

    return Response(
        content=markdown_content,
        media_type="text/markdown",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
        },
    )


@router.get("/report/preview", response_class=HTMLResponse)
async def preview_report(
    request: Request,
    subreddit: str | None = Query(default=None, description="서브레딧 이름"),
    service: ReportService = Depends(get_report_service),
) -> HTMLResponse:
    """보고서 미리보기를 렌더링한다.

    Args:
        request: FastAPI Request 객체
        subreddit: 서브레딧 이름
        service: ReportService 인스턴스

    Returns:
        HTMLResponse: 보고서 미리보기 HTML
    """
    templates = get_templates(request)

    report = service.generate_report(subreddit)

    context = {
        "request": request,
        "page_title": "Report Preview",
        "report": report,
        "has_data": report is not None,
    }

    return templates.TemplateResponse(request, "insights/partials/report_preview.html", context)


@router.get("/report/json")
async def get_report_json(
    subreddit: str | None = Query(default=None, description="서브레딧 이름"),
    service: ReportService = Depends(get_report_service),
) -> JSONResponse:
    """보고서 데이터를 JSON으로 반환한다.

    Args:
        subreddit: 서브레딧 이름
        service: ReportService 인스턴스

    Returns:
        JSONResponse: 보고서 데이터
    """
    report = service.generate_report(subreddit)

    if not report:
        return JSONResponse(
            content={"error": "No data available for report generation"},
            status_code=404,
        )

    # dataclass를 dict로 변환
    report_dict = {
        "subreddit": report.subreddit,
        "generated_at": report.generated_at.isoformat(),
        "analysis_period": report.analysis_period,
        "total_posts_analyzed": report.total_posts_analyzed,
        "total_keywords": report.total_keywords,
        "total_insights": report.total_insights,
        "executive_summary": report.executive_summary,
        "market_overview": report.market_overview,
        "business_items": [
            {
                "rank": item.rank,
                "title": item.title,
                "category": item.category,
                "opportunity_score": item.opportunity_score,
                "market_potential": item.market_potential,
                "risk_level": item.risk_level,
                "description": item.description,
                "target_audience": item.target_audience,
                "key_features": item.key_features,
                "competitive_advantage": item.competitive_advantage,
                "next_steps": item.next_steps,
                "evidence": item.evidence,
            }
            for item in report.business_items
        ],
        "trend_analysis": report.trend_analysis,
        "demand_analysis": report.demand_analysis,
        "competition_analysis": report.competition_analysis,
        "recommendations": report.recommendations,
        "risk_factors": report.risk_factors,
        "conclusion": report.conclusion,
    }

    return JSONResponse(content=report_dict)


# =============================================================================
# PAGINATED API ENDPOINTS
# =============================================================================


@router.get("/api/list", response_class=JSONResponse)
async def get_insights_paginated(
    insight_type: str | None = Query(default=None, description="인사이트 유형 필터"),
    min_confidence: float = Query(default=0.0, ge=0.0, le=1.0, description="최소 신뢰도"),
    page: int = Query(default=1, ge=1, description="페이지 번호"),
    per_page: int = Query(default=20, ge=1, le=100, description="페이지당 항목 수"),
    service: InsightService = Depends(get_insight_service),
) -> JSONResponse:
    """페이지네이션된 인사이트 목록을 JSON으로 반환한다.

    Args:
        insight_type: 필터링할 인사이트 유형 (None이면 전체)
        min_confidence: 최소 신뢰도 필터
        page: 페이지 번호 (1-indexed)
        per_page: 페이지당 항목 수
        service: InsightService 인스턴스

    Returns:
        JSONResponse: 페이지네이션된 인사이트 목록
        {
            "items": [...],
            "meta": { "total": N, "page": 1, "per_page": 20, "pages": M }
        }
    """
    # 모든 인사이트 가져오기 (최대 200개)
    all_insights = service.get_insights(
        insight_type=insight_type,
        min_confidence=min_confidence,
        limit=200,
    )

    # 페이지네이션 적용
    paginated = paginate(all_insights, page=page, per_page=per_page)

    # 응답 생성
    return JSONResponse(content=paginated.to_dict(item_converter=lambda i: i.__dict__))


@router.get("/api/opportunities", response_class=JSONResponse)
async def get_opportunities_paginated(
    page: int = Query(default=1, ge=1, description="페이지 번호"),
    per_page: int = Query(default=20, ge=1, le=100, description="페이지당 항목 수"),
    service: InsightService = Depends(get_insight_service),
) -> JSONResponse:
    """페이지네이션된 기회 랭킹을 JSON으로 반환한다.

    Args:
        page: 페이지 번호 (1-indexed)
        per_page: 페이지당 항목 수
        service: InsightService 인스턴스

    Returns:
        JSONResponse: 페이지네이션된 기회 랭킹
    """
    # 모든 기회 가져오기 (최대 100개)
    all_opportunities = service.get_opportunity_ranking(limit=100)

    # 페이지네이션 적용
    paginated = paginate(all_opportunities, page=page, per_page=per_page)

    # 응답 생성
    return JSONResponse(content=paginated.to_dict(item_converter=lambda o: o.__dict__))
