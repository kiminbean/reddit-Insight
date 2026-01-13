"""텍스트 클러스터링 시각화 라우터.

TextClusterer ML 모듈의 클러스터링 결과를 시각화하는 라우터.
클러스터별 키워드, 대표 문서, 클러스터 분포를 표시한다.
"""

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from reddit_insight.dashboard.services.cluster_service import (
    ClusterService,
    get_cluster_service,
)

router = APIRouter(prefix="/dashboard/clusters", tags=["clusters"])


def get_templates(request: Request) -> Jinja2Templates:
    """Request에서 템플릿 인스턴스를 가져온다."""
    return request.app.state.templates


@router.get("/", response_class=HTMLResponse)
async def clusters_home(
    request: Request,
    service: ClusterService = Depends(get_cluster_service),
) -> HTMLResponse:
    """클러스터링 메인 페이지를 렌더링한다.

    Args:
        request: FastAPI Request 객체
        service: ClusterService 인스턴스

    Returns:
        HTMLResponse: 렌더링된 HTML 페이지
    """
    templates = get_templates(request)

    document_count = service.get_available_document_count()

    context = {
        "request": request,
        "page_title": "Clusters",
        "document_count": document_count,
        "has_data": document_count >= 2,
    }

    return templates.TemplateResponse(request, "clusters/index.html", context)


@router.get("/analyze", response_class=JSONResponse)
async def analyze_clusters(
    n_clusters: int | None = Query(
        default=None, ge=2, le=10, description="클러스터 수 (None이면 자동 선택)"
    ),
    method: str = Query(
        default="auto", description="클러스터링 방법 (auto, kmeans, agglomerative)"
    ),
    service: ClusterService = Depends(get_cluster_service),
) -> JSONResponse:
    """클러스터링 분석을 실행하고 결과를 JSON으로 반환한다.

    Args:
        n_clusters: 클러스터 수 (2-10, None이면 자동 선택)
        method: 클러스터링 방법
        service: ClusterService 인스턴스

    Returns:
        JSONResponse: 클러스터링 분석 결과 (Chart.js 형식)
    """
    result = service.cluster_documents(n_clusters=n_clusters, method=method)
    return JSONResponse(content=result.to_chart_data())


@router.get("/distribution", response_class=JSONResponse)
async def cluster_distribution(
    n_clusters: int | None = Query(
        default=None, ge=2, le=10, description="클러스터 수"
    ),
    service: ClusterService = Depends(get_cluster_service),
) -> JSONResponse:
    """클러스터별 크기 분포 데이터를 JSON으로 반환한다.

    바 차트 표시용 데이터를 반환한다.

    Args:
        n_clusters: 클러스터 수
        service: ClusterService 인스턴스

    Returns:
        JSONResponse: 클러스터 분포 데이터
    """
    result = service.cluster_documents(n_clusters=n_clusters)

    return JSONResponse(
        content={
            "labels": [f"Cluster {c.id}: {c.label}" for c in result.clusters],
            "data": result.cluster_sizes,
            "percentages": [c.percentage for c in result.clusters],
            "n_clusters": result.n_clusters,
            "method": result.method,
            "silhouette_score": result.silhouette_score,
        }
    )


@router.get("/cluster/{cluster_id}", response_class=HTMLResponse)
async def cluster_detail(
    request: Request,
    cluster_id: int,
    service: ClusterService = Depends(get_cluster_service),
) -> HTMLResponse:
    """특정 클러스터의 상세 정보를 표시한다.

    Args:
        request: FastAPI Request 객체
        cluster_id: 클러스터 ID
        service: ClusterService 인스턴스

    Returns:
        HTMLResponse: 클러스터 상세 페이지
    """
    templates = get_templates(request)

    # 캐시된 클러스터 정보 조회
    cluster = service.get_cluster_by_id(cluster_id)
    documents = service.get_cluster_documents(cluster_id)

    if cluster is None:
        context = {
            "request": request,
            "page_title": "Clusters",
            "cluster": None,
            "documents": [],
            "error_message": f"Cluster {cluster_id} not found. Please run clustering analysis first.",
        }
    else:
        context = {
            "request": request,
            "page_title": "Clusters",
            "cluster": cluster,
            "documents": documents,
            "error_message": None,
        }

    return templates.TemplateResponse(request, "clusters/detail.html", context)


@router.get("/cluster/{cluster_id}/documents", response_class=JSONResponse)
async def cluster_documents(
    cluster_id: int,
    page: int = Query(default=1, ge=1, description="페이지 번호"),
    page_size: int = Query(default=20, ge=5, le=100, description="페이지당 항목 수"),
    service: ClusterService = Depends(get_cluster_service),
) -> JSONResponse:
    """특정 클러스터의 문서 목록을 JSON으로 반환한다.

    Args:
        cluster_id: 클러스터 ID
        page: 페이지 번호
        page_size: 페이지당 항목 수
        service: ClusterService 인스턴스

    Returns:
        JSONResponse: 클러스터 문서 목록
    """
    documents = service.get_cluster_documents(cluster_id)

    # 페이지네이션
    total_count = len(documents)
    total_pages = (total_count + page_size - 1) // page_size
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size

    paginated_docs = documents[start_idx:end_idx]

    return JSONResponse(
        content={
            "cluster_id": cluster_id,
            "documents": paginated_docs,
            "page": page,
            "page_size": page_size,
            "total_count": total_count,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
        }
    )


@router.get("/cards-partial", response_class=HTMLResponse)
async def cluster_cards_partial(
    request: Request,
    n_clusters: int | None = Query(
        default=None, ge=2, le=10, description="클러스터 수"
    ),
    method: str = Query(default="auto", description="클러스터링 방법"),
    service: ClusterService = Depends(get_cluster_service),
) -> HTMLResponse:
    """클러스터 카드를 HTMX partial로 반환한다.

    Args:
        request: FastAPI Request 객체
        n_clusters: 클러스터 수
        method: 클러스터링 방법
        service: ClusterService 인스턴스

    Returns:
        HTMLResponse: 클러스터 카드 HTML 파셜
    """
    templates = get_templates(request)

    result = service.cluster_documents(n_clusters=n_clusters, method=method)

    context = {
        "request": request,
        "clusters": result.clusters,
        "silhouette_score": result.silhouette_score,
        "method": result.method,
        "document_count": result.document_count,
    }

    return templates.TemplateResponse(
        request, "clusters/partials/cluster_cards.html", context
    )


@router.get("/document-count", response_class=JSONResponse)
async def get_document_count(
    service: ClusterService = Depends(get_cluster_service),
) -> JSONResponse:
    """분석 가능한 문서 수를 반환한다.

    Args:
        service: ClusterService 인스턴스

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
