"""토픽 모델링 시각화 라우터.

TopicModeler ML 모듈의 토픽 분석 결과를 시각화하는 라우터.
토픽별 키워드, 문서 분포, coherence score를 표시한다.
"""

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from reddit_insight.dashboard.services.topic_service import (
    TopicService,
    get_topic_service,
)

router = APIRouter(prefix="/dashboard/topics", tags=["topics"])


def get_templates(request: Request) -> Jinja2Templates:
    """Request에서 템플릿 인스턴스를 가져온다."""
    return request.app.state.templates


@router.get("/", response_class=HTMLResponse)
async def topics_home(
    request: Request,
    service: TopicService = Depends(get_topic_service),
) -> HTMLResponse:
    """토픽 분석 메인 페이지를 렌더링한다.

    Args:
        request: FastAPI Request 객체
        service: TopicService 인스턴스

    Returns:
        HTMLResponse: 렌더링된 HTML 페이지
    """
    templates = get_templates(request)

    # 분석 가능한 문서 수 확인
    document_count = service.get_available_document_count()

    context = {
        "request": request,
        "page_title": "Topics",
        "document_count": document_count,
        "has_data": document_count >= 2,
    }

    return templates.TemplateResponse(request, "topics/index.html", context)


@router.get("/analyze", response_class=JSONResponse)
async def analyze_topics(
    n_topics: int = Query(default=5, ge=2, le=10, description="추출할 토픽 수"),
    method: str = Query(default="auto", description="토픽 모델링 방법 (auto, lda, nmf)"),
    service: TopicService = Depends(get_topic_service),
) -> JSONResponse:
    """토픽 분석을 실행하고 결과를 JSON으로 반환한다.

    Args:
        n_topics: 추출할 토픽 수 (2-10)
        method: 토픽 모델링 방법
        service: TopicService 인스턴스

    Returns:
        JSONResponse: 토픽 분석 결과 (Chart.js 형식)
    """
    result = service.analyze_topics(n_topics=n_topics, method=method)
    return JSONResponse(content=result.to_chart_data())


@router.get("/distribution", response_class=JSONResponse)
async def topic_distribution(
    n_topics: int = Query(default=5, ge=2, le=10, description="추출할 토픽 수"),
    service: TopicService = Depends(get_topic_service),
) -> JSONResponse:
    """토픽별 문서 분포 데이터를 JSON으로 반환한다.

    파이 차트 표시용 데이터를 반환한다.

    Args:
        n_topics: 토픽 수
        service: TopicService 인스턴스

    Returns:
        JSONResponse: 토픽 분포 데이터
    """
    result = service.analyze_topics(n_topics=n_topics)

    # 파이 차트용 데이터만 반환
    return JSONResponse(
        content={
            "labels": [f"Topic {t.id}: {t.label}" for t in result.topics],
            "data": result.topic_distribution,
            "n_topics": result.n_topics,
            "method": result.method,
        }
    )


@router.get("/keywords-partial", response_class=HTMLResponse)
async def keywords_partial(
    request: Request,
    n_topics: int = Query(default=5, ge=2, le=10, description="추출할 토픽 수"),
    method: str = Query(default="auto", description="토픽 모델링 방법"),
    service: TopicService = Depends(get_topic_service),
) -> HTMLResponse:
    """토픽별 키워드 카드를 HTMX partial로 반환한다.

    Args:
        request: FastAPI Request 객체
        n_topics: 추출할 토픽 수
        method: 토픽 모델링 방법
        service: TopicService 인스턴스

    Returns:
        HTMLResponse: 토픽 키워드 카드 HTML 파셜
    """
    templates = get_templates(request)

    result = service.analyze_topics(n_topics=n_topics, method=method)

    context = {
        "request": request,
        "topics": result.topics,
        "overall_coherence": result.overall_coherence,
        "method": result.method,
        "document_count": result.document_count,
    }

    return templates.TemplateResponse(
        request, "topics/partials/topic_cards.html", context
    )


@router.get("/document-count", response_class=JSONResponse)
async def get_document_count(
    service: TopicService = Depends(get_topic_service),
) -> JSONResponse:
    """분석 가능한 문서 수를 반환한다.

    Args:
        service: TopicService 인스턴스

    Returns:
        JSONResponse: 문서 수 정보
    """
    count = service.get_available_document_count()
    return JSONResponse(
        content={
            "document_count": count,
            "has_sufficient_data": count >= 2,
        }
    )
