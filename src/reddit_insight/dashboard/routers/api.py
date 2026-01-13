"""API 라우터.

인증이 필요한 API 엔드포인트를 제공한다.
"""

from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel

from reddit_insight.dashboard.auth import (
    APIKey,
    create_api_key,
    deactivate_api_key,
    delete_api_key,
    get_api_keys,
    get_api_key_required,
    get_current_auth,
)
from reddit_insight.dashboard.data_store import (
    get_all_subreddits,
    get_analysis_history,
    get_current_data,
)

router = APIRouter(prefix="/api/v1", tags=["api"])


# ============================================================================
# Request/Response Models
# ============================================================================


class CreateAPIKeyRequest(BaseModel):
    """API 키 생성 요청."""

    name: str
    rate_limit: int = 100


class CreateAPIKeyResponse(BaseModel):
    """API 키 생성 응답."""

    id: int
    name: str
    api_key: str
    rate_limit: int
    message: str


class APIKeyInfo(BaseModel):
    """API 키 정보."""

    id: int
    name: str
    created_at: str | None
    last_used_at: str | None
    is_active: bool
    rate_limit: int


class AnalysisHistoryItem(BaseModel):
    """분석 이력 항목."""

    id: int
    subreddit: str
    analyzed_at: str
    post_count: int
    keyword_count: int
    insight_count: int


class SubredditDataResponse(BaseModel):
    """서브레딧 데이터 응답."""

    subreddit: str
    analyzed_at: str
    post_count: int
    keyword_count: int
    trend_count: int
    demand_count: int
    insight_count: int
    keywords: list[dict[str, Any]]
    trends: list[dict[str, Any]]


# ============================================================================
# Public Endpoints (No Auth Required)
# ============================================================================


@router.get("/status")
async def api_status() -> dict[str, Any]:
    """API 상태를 반환한다."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "auth_required": True,
    }


# ============================================================================
# Protected Endpoints (Auth Required)
# ============================================================================


@router.get("/subreddits", response_model=list[str])
async def list_subreddits(
    auth: Annotated[APIKey, Depends(get_api_key_required)],
) -> list[str]:
    """분석된 서브레딧 목록을 반환한다."""
    return get_all_subreddits()


@router.get("/analysis/history", response_model=list[AnalysisHistoryItem])
async def list_analysis_history(
    auth: Annotated[APIKey, Depends(get_api_key_required)],
    subreddit: str | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """분석 이력을 반환한다."""
    return get_analysis_history(subreddit, limit)


@router.get("/analysis/{subreddit}")
async def get_subreddit_analysis(
    subreddit: str,
    auth: Annotated[APIKey, Depends(get_api_key_required)],
) -> dict[str, Any]:
    """특정 서브레딧의 최신 분석 데이터를 반환한다."""
    data = get_current_data(subreddit)

    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No analysis data found for r/{subreddit}",
        )

    return {
        "subreddit": data.subreddit,
        "analyzed_at": data.analyzed_at,
        "post_count": data.post_count,
        "keyword_count": len(data.keywords),
        "trend_count": len(data.trends),
        "demand_count": data.demands.get("total_demands", 0) if data.demands else 0,
        "insight_count": len(data.insights),
        "keywords": data.keywords[:20],
        "trends": data.trends,
        "top_insights": data.insights[:10],
    }


@router.get("/keywords/{subreddit}")
async def get_subreddit_keywords(
    subreddit: str,
    auth: Annotated[APIKey, Depends(get_api_key_required)],
    limit: int = 50,
) -> dict[str, Any]:
    """서브레딧의 키워드 데이터를 반환한다."""
    data = get_current_data(subreddit)

    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No analysis data found for r/{subreddit}",
        )

    return {
        "subreddit": data.subreddit,
        "analyzed_at": data.analyzed_at,
        "total_keywords": len(data.keywords),
        "keywords": data.keywords[:limit],
    }


@router.get("/trends/{subreddit}")
async def get_subreddit_trends(
    subreddit: str,
    auth: Annotated[APIKey, Depends(get_api_key_required)],
) -> dict[str, Any]:
    """서브레딧의 트렌드 데이터를 반환한다."""
    data = get_current_data(subreddit)

    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No analysis data found for r/{subreddit}",
        )

    return {
        "subreddit": data.subreddit,
        "analyzed_at": data.analyzed_at,
        "trends": data.trends,
    }


@router.get("/insights/{subreddit}")
async def get_subreddit_insights(
    subreddit: str,
    auth: Annotated[APIKey, Depends(get_api_key_required)],
) -> dict[str, Any]:
    """서브레딧의 인사이트 데이터를 반환한다."""
    data = get_current_data(subreddit)

    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No analysis data found for r/{subreddit}",
        )

    return {
        "subreddit": data.subreddit,
        "analyzed_at": data.analyzed_at,
        "total_insights": len(data.insights),
        "insights": data.insights,
        "demands": data.demands,
        "competition": data.competition,
    }


# ============================================================================
# Admin Endpoints (Special Auth - Admin Key Required)
# ============================================================================


@router.post("/admin/api-keys", response_model=CreateAPIKeyResponse)
async def create_new_api_key(
    request: CreateAPIKeyRequest,
    auth: Annotated[APIKey, Depends(get_api_key_required)],
) -> CreateAPIKeyResponse:
    """새로운 API 키를 생성한다.

    관리자 권한 API 키로만 접근 가능.
    """
    # 실제 프로덕션에서는 관리자 권한 체크 필요
    raw_key, key_id = create_api_key(request.name, request.rate_limit)

    return CreateAPIKeyResponse(
        id=key_id,
        name=request.name,
        api_key=raw_key,
        rate_limit=request.rate_limit,
        message="API key created successfully. Save this key, it won't be shown again.",
    )


@router.get("/admin/api-keys", response_model=list[APIKeyInfo])
async def list_api_keys_admin(
    auth: Annotated[APIKey, Depends(get_api_key_required)],
) -> list[dict[str, Any]]:
    """모든 API 키 목록을 반환한다."""
    return get_api_keys()


@router.delete("/admin/api-keys/{key_id}")
async def delete_api_key_admin(
    key_id: int,
    auth: Annotated[APIKey, Depends(get_api_key_required)],
) -> dict[str, str]:
    """API 키를 삭제한다."""
    if delete_api_key(key_id):
        return {"message": f"API key {key_id} deleted successfully"}
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"API key {key_id} not found",
    )


@router.put("/admin/api-keys/{key_id}/deactivate")
async def deactivate_api_key_admin(
    key_id: int,
    auth: Annotated[APIKey, Depends(get_api_key_required)],
) -> dict[str, str]:
    """API 키를 비활성화한다."""
    if deactivate_api_key(key_id):
        return {"message": f"API key {key_id} deactivated successfully"}
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"API key {key_id} not found",
    )
