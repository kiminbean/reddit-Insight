"""트렌드 시각화 라우터.

키워드 트렌드와 Rising 키워드를 시각화하는 라우터.
예측 기능과 이상 탐지 기능을 포함하여 ML 기반 트렌드 분석을 제공한다.
"""


from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from reddit_insight.dashboard.pagination import paginate
from reddit_insight.dashboard.services.anomaly_service import (
    AnomalyService,
    get_anomaly_service,
)
from reddit_insight.dashboard.services.prediction_service import (
    PredictionService,
    get_prediction_service,
)
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

    return templates.TemplateResponse(request, "trends/index.html", context)


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

    return templates.TemplateResponse(request, "trends/partials/keyword_list.html", context)


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

    return templates.TemplateResponse(request, "trends/partials/rising_list.html", context)


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


# =============================================================================
# PREDICTION ENDPOINTS
# =============================================================================


@router.get("/predict/{keyword}", response_class=JSONResponse)
async def predict_keyword(
    keyword: str,
    days: int = Query(default=7, ge=1, le=14, description="예측 기간(일)"),
    historical_days: int = Query(default=14, ge=10, le=30, description="과거 데이터 기간(일)"),
    confidence: float = Query(default=0.95, ge=0.5, le=0.99, description="신뢰수준"),
    service: PredictionService = Depends(get_prediction_service),
) -> JSONResponse:
    """키워드의 트렌드 예측 데이터를 반환한다.

    ML 기반 시계열 예측 모델(ETS/ARIMA)을 사용하여 키워드 트렌드를 예측한다.

    Args:
        keyword: 예측할 키워드
        days: 예측 기간 (1-14일)
        historical_days: 과거 데이터 기간 (10-30일)
        confidence: 신뢰수준 (0.5-0.99)
        service: PredictionService 인스턴스

    Returns:
        JSONResponse: Chart.js 형식의 예측 데이터 및 메타데이터
    """
    prediction = service.predict_keyword_trend(
        keyword=keyword,
        historical_days=historical_days,
        forecast_days=days,
        confidence_level=confidence,
    )

    return JSONResponse(content=prediction.to_chart_data())


@router.get("/predict-partial/{keyword}", response_class=HTMLResponse)
async def predict_partial(
    request: Request,
    keyword: str,
    days: int = Query(default=7, ge=1, le=14, description="예측 기간(일)"),
    service: PredictionService = Depends(get_prediction_service),
) -> HTMLResponse:
    """예측 차트 파셜 HTML을 반환한다.

    HTMX로 동적 로딩할 수 있는 예측 차트 컴포넌트를 반환한다.

    Args:
        request: FastAPI Request 객체
        keyword: 예측할 키워드
        days: 예측 기간
        service: PredictionService 인스턴스

    Returns:
        HTMLResponse: 예측 차트 HTML 파셜
    """
    templates = get_templates(request)

    prediction = service.predict_keyword_trend(
        keyword=keyword,
        forecast_days=days,
    )

    context = {
        "request": request,
        "keyword": keyword,
        "prediction": prediction,
        "forecast_days": days,
    }

    return templates.TemplateResponse(request, "trends/partials/prediction_chart.html", context)


# =============================================================================
# ANOMALY DETECTION ENDPOINTS
# =============================================================================


@router.get("/anomalies/{keyword}", response_class=JSONResponse)
async def detect_anomalies(
    keyword: str,
    days: int = Query(default=30, ge=7, le=90, description="분석 기간(일)"),
    method: str = Query(default="auto", description="탐지 방법 (auto, zscore, iqr, isolation_forest)"),
    threshold: float = Query(default=3.0, ge=1.0, le=5.0, description="이상 판정 임계값"),
    service: AnomalyService = Depends(get_anomaly_service),
) -> JSONResponse:
    """키워드의 이상 포인트를 탐지하여 반환한다.

    ML 기반 이상 탐지 알고리즘을 사용하여 키워드 트렌드에서 이상 포인트를 식별한다.

    Args:
        keyword: 분석할 키워드
        days: 분석 기간 (7-90일)
        method: 탐지 방법 ("auto", "zscore", "iqr", "isolation_forest")
        threshold: 이상 판정 임계값 (1.0-5.0)
        service: AnomalyService 인스턴스

    Returns:
        JSONResponse: Chart.js 형식의 이상 탐지 데이터 및 메타데이터
    """
    result = service.detect_anomalies(
        keyword=keyword,
        days=days,
        method=method,
        threshold=threshold,
    )

    return JSONResponse(content=result.to_chart_data())


@router.get("/anomalies-partial/{keyword}", response_class=HTMLResponse)
async def anomalies_partial(
    request: Request,
    keyword: str,
    days: int = Query(default=30, ge=7, le=90, description="분석 기간(일)"),
    service: AnomalyService = Depends(get_anomaly_service),
) -> HTMLResponse:
    """이상 탐지 차트 파셜 HTML을 반환한다.

    HTMX로 동적 로딩할 수 있는 이상 탐지 차트 컴포넌트를 반환한다.

    Args:
        request: FastAPI Request 객체
        keyword: 분석할 키워드
        days: 분석 기간
        service: AnomalyService 인스턴스

    Returns:
        HTMLResponse: 이상 탐지 차트 HTML 파셜
    """
    templates = get_templates(request)

    anomaly_result = service.detect_anomalies(
        keyword=keyword,
        days=days,
    )

    context = {
        "request": request,
        "keyword": keyword,
        "anomaly_result": anomaly_result,
        "analysis_days": days,
    }

    return templates.TemplateResponse(request, "trends/partials/anomaly_chart.html", context)


# =============================================================================
# PAGINATED API ENDPOINTS
# =============================================================================


@router.get("/api/keywords", response_class=JSONResponse)
async def get_keywords_paginated(
    subreddit: str | None = Query(default=None, description="필터링할 서브레딧"),
    days: int = Query(default=7, ge=1, le=30, description="분석 기간(일)"),
    page: int = Query(default=1, ge=1, description="페이지 번호"),
    per_page: int = Query(default=20, ge=1, le=100, description="페이지당 항목 수"),
    service: TrendService = Depends(get_trend_service),
) -> JSONResponse:
    """페이지네이션된 키워드 목록을 JSON으로 반환한다.

    Args:
        subreddit: 필터링할 서브레딧
        days: 분석 기간
        page: 페이지 번호 (1-indexed)
        per_page: 페이지당 항목 수
        service: TrendService 인스턴스

    Returns:
        JSONResponse: 페이지네이션된 키워드 목록
        {
            "items": [...],
            "meta": { "total": N, "page": 1, "per_page": 20, "pages": M }
        }
    """
    # 모든 키워드 가져오기 (최대 200개)
    all_keywords = service.get_top_keywords(subreddit=subreddit, days=days, limit=200)

    # 페이지네이션 적용
    paginated = paginate(all_keywords, page=page, per_page=per_page)

    # 응답 생성
    return JSONResponse(content=paginated.to_dict(item_converter=lambda kw: kw.__dict__))


@router.get("/chart/{keyword}", response_class=HTMLResponse)
async def keyword_chart_partial(
    request: Request,
    keyword: str,
    days: int = Query(default=7, ge=1, le=30, description="분석 기간(일)"),
    service: TrendService = Depends(get_trend_service),
) -> HTMLResponse:
    """키워드 차트를 HTMX partial로 반환한다.

    지연 로딩(lazy loading)을 위해 hx-trigger="revealed"와 함께 사용한다.

    Args:
        request: FastAPI Request 객체
        keyword: 차트를 표시할 키워드
        days: 분석 기간
        service: TrendService 인스턴스

    Returns:
        HTMLResponse: 차트 HTML partial
    """
    templates = get_templates(request)

    timeline = service.get_keyword_timeline(keyword=keyword, days=days)

    context = {
        "request": request,
        "keyword": keyword,
        "timeline": [{"date": str(p.date), "count": p.count} for p in timeline],
        "days": days,
    }

    return templates.TemplateResponse(request, "trends/partials/chart_lazy.html", context)


@router.get("/api/rising", response_class=JSONResponse)
async def get_rising_paginated(
    subreddit: str | None = Query(default=None, description="필터링할 서브레딧"),
    page: int = Query(default=1, ge=1, description="페이지 번호"),
    per_page: int = Query(default=20, ge=1, le=100, description="페이지당 항목 수"),
    service: TrendService = Depends(get_trend_service),
) -> JSONResponse:
    """페이지네이션된 급상승 키워드 목록을 JSON으로 반환한다.

    Args:
        subreddit: 필터링할 서브레딧
        page: 페이지 번호 (1-indexed)
        per_page: 페이지당 항목 수
        service: TrendService 인스턴스

    Returns:
        JSONResponse: 페이지네이션된 급상승 키워드 목록
    """
    # 모든 급상승 키워드 가져오기
    all_rising = service.get_rising_keywords(subreddit=subreddit, limit=100)

    # 페이지네이션 적용
    paginated = paginate(all_rising, page=page, per_page=per_page)

    # datetime 변환 함수
    def convert_rising(kw):
        data = kw.__dict__.copy()
        if data.get("first_seen"):
            data["first_seen"] = data["first_seen"].isoformat()
        return data

    return JSONResponse(content=paginated.to_dict(item_converter=convert_rising))
