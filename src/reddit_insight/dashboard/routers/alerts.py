"""알림 대시보드 라우터.

알림 규칙 관리 및 알림 이력 조회 엔드포인트.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from reddit_insight.dashboard.services.alert_service import (
    AlertService,
    get_alert_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard/alerts", tags=["alerts"])


def get_templates(request: Request) -> Jinja2Templates:
    """Request에서 템플릿 인스턴스를 가져온다."""
    return request.app.state.templates


# =============================================================================
# Dashboard Page
# =============================================================================


@router.get("/", response_class=HTMLResponse)
async def alerts_dashboard(
    request: Request,
    service: AlertService = Depends(get_alert_service),
) -> HTMLResponse:
    """알림 대시보드 페이지를 렌더링한다.

    Args:
        request: FastAPI Request 객체
        service: AlertService 인스턴스

    Returns:
        HTMLResponse: 렌더링된 HTML 페이지
    """
    templates = get_templates(request)

    # 데이터 조회
    rules = service.get_rules()
    history = service.get_history(limit=20)
    stats = service.get_stats()
    alert_types = service.get_alert_types()
    notifiers = service.get_available_notifiers()

    context = {
        "request": request,
        "page_title": "Alerts",
        "rules": rules,
        "history": history,
        "stats": stats,
        "alert_types": alert_types,
        "notifiers": notifiers,
    }

    return templates.TemplateResponse(request, "alerts/index.html", context)


# =============================================================================
# Rule CRUD Endpoints
# =============================================================================


@router.get("/rules", response_class=JSONResponse)
async def get_rules(
    enabled_only: bool = Query(default=False, description="활성화된 규칙만"),
    service: AlertService = Depends(get_alert_service),
) -> JSONResponse:
    """모든 규칙을 조회한다.

    Args:
        enabled_only: 활성화된 규칙만 반환할지 여부
        service: AlertService 인스턴스

    Returns:
        JSONResponse: 규칙 목록
    """
    rules = service.get_rules(enabled_only=enabled_only)
    return JSONResponse(content={"rules": rules})


@router.get("/rules/{rule_id}", response_class=JSONResponse)
async def get_rule(
    rule_id: str,
    service: AlertService = Depends(get_alert_service),
) -> JSONResponse:
    """특정 규칙을 조회한다.

    Args:
        rule_id: 규칙 ID
        service: AlertService 인스턴스

    Returns:
        JSONResponse: 규칙 정보 또는 404
    """
    rule = service.get_rule(rule_id)
    if not rule:
        return JSONResponse(
            content={"error": "Rule not found"},
            status_code=404,
        )
    return JSONResponse(content={"rule": rule})


@router.post("/rules", response_class=HTMLResponse)
async def create_rule(
    request: Request,
    name: str = Form(...),
    alert_type: str = Form(...),
    subreddit: str = Form(default=""),
    threshold: float = Form(...),
    window_minutes: int = Form(default=60),
    comparison: str = Form(default="gte"),
    notifiers: list[str] = Form(default=["console"]),
    enabled: bool = Form(default=True),
    service: AlertService = Depends(get_alert_service),
) -> HTMLResponse:
    """새 규칙을 생성한다.

    Args:
        request: FastAPI Request 객체
        name: 규칙 이름
        alert_type: 알림 유형
        subreddit: 대상 서브레딧
        threshold: 임계값
        window_minutes: 시간 윈도우 (분)
        comparison: 비교 연산자
        notifiers: 알림 채널 목록
        enabled: 활성화 여부
        service: AlertService 인스턴스

    Returns:
        HTMLResponse: 생성된 규칙 카드 HTML (HTMX 부분 업데이트용)
    """
    templates = get_templates(request)

    try:
        rule = service.create_rule(
            name=name,
            alert_type=alert_type,
            subreddit=subreddit,
            threshold=threshold,
            window_minutes=window_minutes,
            comparison=comparison,
            notifiers=notifiers,
            enabled=enabled,
        )

        return templates.TemplateResponse(
            request,
            "alerts/partials/rule_card.html",
            {"request": request, "rule": rule},
        )

    except Exception as e:
        logger.exception("Failed to create rule: %s", e)
        return HTMLResponse(
            content=f'<div class="text-red-500">Error: {e}</div>',
            status_code=400,
        )


@router.put("/rules/{rule_id}", response_class=JSONResponse)
async def update_rule(
    rule_id: str,
    request: Request,
    service: AlertService = Depends(get_alert_service),
) -> JSONResponse:
    """규칙을 업데이트한다.

    Args:
        rule_id: 규칙 ID
        request: FastAPI Request 객체
        service: AlertService 인스턴스

    Returns:
        JSONResponse: 업데이트된 규칙 정보
    """
    try:
        body = await request.json()
        rule = service.update_rule(rule_id, **body)

        if not rule:
            return JSONResponse(
                content={"error": "Rule not found"},
                status_code=404,
            )

        return JSONResponse(content={"success": True, "rule": rule})

    except Exception as e:
        logger.exception("Failed to update rule: %s", e)
        return JSONResponse(
            content={"error": str(e)},
            status_code=400,
        )


@router.delete("/rules/{rule_id}", response_class=HTMLResponse)
async def delete_rule(
    rule_id: str,
    service: AlertService = Depends(get_alert_service),
) -> HTMLResponse:
    """규칙을 삭제한다.

    Args:
        rule_id: 규칙 ID
        service: AlertService 인스턴스

    Returns:
        HTMLResponse: 빈 응답 (HTMX swap용)
    """
    success = service.delete_rule(rule_id)

    if success:
        return HTMLResponse(content="", status_code=200)
    else:
        return HTMLResponse(
            content='<div class="text-red-500">Rule not found</div>',
            status_code=404,
        )


@router.post("/rules/{rule_id}/toggle", response_class=HTMLResponse)
async def toggle_rule(
    rule_id: str,
    request: Request,
    service: AlertService = Depends(get_alert_service),
) -> HTMLResponse:
    """규칙을 토글한다 (활성화/비활성화).

    Args:
        rule_id: 규칙 ID
        request: FastAPI Request 객체
        service: AlertService 인스턴스

    Returns:
        HTMLResponse: 업데이트된 규칙 카드 HTML
    """
    templates = get_templates(request)

    rule = service.toggle_rule(rule_id)
    if not rule:
        return HTMLResponse(
            content='<div class="text-red-500">Rule not found</div>',
            status_code=404,
        )

    return templates.TemplateResponse(
        request,
        "alerts/partials/rule_card.html",
        {"request": request, "rule": rule},
    )


# =============================================================================
# History Endpoints
# =============================================================================


@router.get("/history", response_class=HTMLResponse)
async def get_history(
    request: Request,
    limit: int = Query(default=50, ge=1, le=200),
    rule_id: str | None = Query(default=None),
    subreddit: str | None = Query(default=None),
    service: AlertService = Depends(get_alert_service),
) -> HTMLResponse:
    """알림 이력을 조회한다.

    Args:
        request: FastAPI Request 객체
        limit: 최대 개수
        rule_id: 규칙 ID 필터
        subreddit: 서브레딧 필터
        service: AlertService 인스턴스

    Returns:
        HTMLResponse: 알림 이력 테이블 HTML (HTMX 부분 업데이트용)
    """
    templates = get_templates(request)

    history = service.get_history(
        limit=limit,
        rule_id=rule_id,
        subreddit=subreddit,
    )

    return templates.TemplateResponse(
        request,
        "alerts/partials/history_table.html",
        {"request": request, "history": history},
    )


@router.delete("/history", response_class=JSONResponse)
async def clear_history(
    service: AlertService = Depends(get_alert_service),
) -> JSONResponse:
    """알림 이력을 삭제한다.

    Args:
        service: AlertService 인스턴스

    Returns:
        JSONResponse: 삭제 결과
    """
    count = service.clear_history()
    return JSONResponse(content={"success": True, "cleared": count})


# =============================================================================
# Test Alert Endpoint
# =============================================================================


@router.post("/test", response_class=JSONResponse)
async def send_test_alert(
    notifier: str = Form(default="console"),
    service: AlertService = Depends(get_alert_service),
) -> JSONResponse:
    """테스트 알림을 전송한다.

    Args:
        notifier: 알림 채널 이름
        service: AlertService 인스턴스

    Returns:
        JSONResponse: 전송 결과
    """
    try:
        success = await service.send_test_alert(notifier)
        return JSONResponse(
            content={
                "success": success,
                "message": f"Test alert {'sent' if success else 'failed'} via {notifier}",
            }
        )
    except Exception as e:
        logger.exception("Failed to send test alert: %s", e)
        return JSONResponse(
            content={"success": False, "message": str(e)},
            status_code=500,
        )


# =============================================================================
# Stats Endpoint
# =============================================================================


@router.get("/stats", response_class=JSONResponse)
async def get_stats(
    service: AlertService = Depends(get_alert_service),
) -> JSONResponse:
    """알림 통계를 조회한다.

    Args:
        service: AlertService 인스턴스

    Returns:
        JSONResponse: 알림 통계
    """
    stats = service.get_stats()
    return JSONResponse(content=stats)
