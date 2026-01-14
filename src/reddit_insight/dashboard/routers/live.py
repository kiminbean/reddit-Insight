"""라이브 대시보드 라우터.

Server-Sent Events(SSE) 기반 실시간 모니터링 엔드포인트.
서브레딧의 새 게시물, 활동량 변화를 실시간으로 스트리밍한다.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from reddit_insight.dashboard.services.live_service import (
    LiveService,
    get_live_service,
)

if TYPE_CHECKING:
    from reddit_insight.streaming.monitor import LiveUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard/live", tags=["live"])


def get_templates(request: Request) -> Jinja2Templates:
    """Request에서 템플릿 인스턴스를 가져온다."""
    return request.app.state.templates


# =============================================================================
# SSE Streaming Endpoints
# =============================================================================


@router.get("/stream/{subreddit}")
async def live_stream(
    subreddit: str,
    request: Request,
    service: LiveService = Depends(get_live_service),
) -> StreamingResponse:
    """서브레딧의 실시간 업데이트를 SSE로 스트리밍한다.

    Server-Sent Events 프로토콜을 사용하여 실시간 업데이트를 전송한다.
    클라이언트는 EventSource API를 통해 이 엔드포인트에 연결한다.

    Args:
        subreddit: 스트리밍할 서브레딧 이름
        request: FastAPI Request 객체
        service: LiveService 인스턴스

    Returns:
        StreamingResponse: SSE 스트림
    """
    logger.info("SSE connection request for r/%s", subreddit)

    async def event_generator():
        """SSE 이벤트 생성기."""
        queue = None
        try:
            # 구독 시작 (모니터링이 없으면 자동 시작)
            queue = await service.subscribe(subreddit)
            logger.info("SSE client connected for r/%s", subreddit)

            # 연결 확인 이벤트
            yield _format_sse(
                {
                    "type": "connected",
                    "message": f"Connected to r/{subreddit}",
                }
            )

            # 업데이트 스트리밍
            while True:
                # 클라이언트 연결 끊김 체크
                if await request.is_disconnected():
                    logger.info("SSE client disconnected from r/%s", subreddit)
                    break

                try:
                    # 타임아웃과 함께 업데이트 대기
                    update: LiveUpdate = await asyncio.wait_for(
                        queue.get(),
                        timeout=30.0,  # 30초마다 하트비트
                    )
                    yield _format_sse(update.to_dict())

                except asyncio.TimeoutError:
                    # 하트비트 전송 (연결 유지)
                    yield _format_sse(
                        {
                            "type": "heartbeat",
                            "message": "keep-alive",
                        }
                    )

        except asyncio.CancelledError:
            logger.info("SSE stream cancelled for r/%s", subreddit)
        except Exception as e:
            logger.error("SSE stream error for r/%s: %s", subreddit, e)
            yield _format_sse(
                {
                    "type": "error",
                    "message": str(e),
                }
            )
        finally:
            # 구독 해제
            if queue:
                service.unsubscribe(subreddit, queue)
                logger.info("SSE client unsubscribed from r/%s", subreddit)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Nginx 버퍼링 비활성화
        },
    )


def _format_sse(data: dict) -> str:
    """SSE 형식으로 데이터를 포맷팅한다.

    Args:
        data: 전송할 데이터

    Returns:
        SSE 형식 문자열
    """
    json_data = json.dumps(data)
    return f"data: {json_data}\n\n"


# =============================================================================
# Control Endpoints
# =============================================================================


@router.post("/start/{subreddit}")
async def start_monitoring(
    subreddit: str,
    interval: int = Query(default=30, ge=10, le=300, description="폴링 간격(초)"),
    service: LiveService = Depends(get_live_service),
) -> JSONResponse:
    """서브레딧 모니터링을 시작한다.

    Args:
        subreddit: 모니터링할 서브레딧 이름
        interval: 폴링 간격 (10-300초)
        service: LiveService 인스턴스

    Returns:
        JSONResponse: 시작 결과
    """
    try:
        monitor = await service.start_monitoring(subreddit, interval=interval)

        return JSONResponse(
            content={
                "success": True,
                "message": f"Started monitoring r/{subreddit}",
                "subreddit": subreddit,
                "interval": interval,
                "is_running": monitor.is_running,
            }
        )
    except Exception as e:
        logger.error("Failed to start monitoring r/%s: %s", subreddit, e)
        return JSONResponse(
            content={
                "success": False,
                "message": f"Failed to start monitoring: {e}",
                "subreddit": subreddit,
            },
            status_code=500,
        )


@router.post("/stop/{subreddit}")
async def stop_monitoring(
    subreddit: str,
    service: LiveService = Depends(get_live_service),
) -> JSONResponse:
    """서브레딧 모니터링을 중지한다.

    Args:
        subreddit: 중지할 서브레딧 이름
        service: LiveService 인스턴스

    Returns:
        JSONResponse: 중지 결과
    """
    try:
        success = await service.stop_monitoring(subreddit)

        if success:
            return JSONResponse(
                content={
                    "success": True,
                    "message": f"Stopped monitoring r/{subreddit}",
                    "subreddit": subreddit,
                }
            )
        else:
            return JSONResponse(
                content={
                    "success": False,
                    "message": f"r/{subreddit} was not being monitored",
                    "subreddit": subreddit,
                },
                status_code=404,
            )
    except Exception as e:
        logger.error("Failed to stop monitoring r/%s: %s", subreddit, e)
        return JSONResponse(
            content={
                "success": False,
                "message": f"Failed to stop monitoring: {e}",
                "subreddit": subreddit,
            },
            status_code=500,
        )


@router.get("/status")
async def get_status(
    service: LiveService = Depends(get_live_service),
) -> JSONResponse:
    """모든 모니터의 상태를 반환한다.

    Returns:
        JSONResponse: 모니터 상태 목록
    """
    active_monitors = service.get_active_monitors()
    stats = service.get_monitor_stats()

    return JSONResponse(
        content={
            "active_count": len(active_monitors),
            "active_monitors": active_monitors,
            "stats": stats,
        }
    )


@router.get("/status/{subreddit}")
async def get_subreddit_status(
    subreddit: str,
    service: LiveService = Depends(get_live_service),
) -> JSONResponse:
    """특정 서브레딧의 모니터 상태를 반환한다.

    Args:
        subreddit: 서브레딧 이름
        service: LiveService 인스턴스

    Returns:
        JSONResponse: 모니터 상태
    """
    monitor = service.get_monitor(subreddit)

    if monitor is None:
        return JSONResponse(
            content={
                "subreddit": subreddit,
                "is_monitoring": False,
            }
        )

    return JSONResponse(
        content={
            "subreddit": subreddit,
            "is_monitoring": True,
            "is_running": monitor.is_running,
            "subscriber_count": monitor.subscriber_count,
            "interval": monitor.interval,
        }
    )


# =============================================================================
# Dashboard Page
# =============================================================================


@router.get("/", response_class=HTMLResponse)
async def live_dashboard(
    request: Request,
    subreddit: str | None = Query(default=None, description="모니터링할 서브레딧"),
    service: LiveService = Depends(get_live_service),
) -> HTMLResponse:
    """라이브 대시보드 페이지를 렌더링한다.

    Args:
        request: FastAPI Request 객체
        subreddit: 기본 모니터링 서브레딧
        service: LiveService 인스턴스

    Returns:
        HTMLResponse: 렌더링된 HTML 페이지
    """
    templates = get_templates(request)

    # 활성 모니터 목록
    active_monitors = service.get_active_monitors()

    context = {
        "request": request,
        "page_title": "Live",
        "initial_subreddit": subreddit,
        "active_monitors": active_monitors,
    }

    return templates.TemplateResponse(request, "live/index.html", context)
