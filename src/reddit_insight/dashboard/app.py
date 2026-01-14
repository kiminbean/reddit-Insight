"""FastAPI 기반 웹 대시보드 애플리케이션.

Reddit Insight 분석 결과를 시각화하는 웹 대시보드를 제공한다.
서버 사이드 렌더링(Jinja2)과 HTMX를 활용하여 최소한의 JavaScript로 동적 UI를 구현한다.
"""

import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# 로깅 설정
logger = logging.getLogger(__name__)

# 패키지 내부 경로 설정
PACKAGE_DIR = Path(__file__).parent
TEMPLATES_DIR = PACKAGE_DIR / "templates"
STATIC_DIR = PACKAGE_DIR / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 수명 주기 관리.

    Startup: 리소스 초기화
    Shutdown: 리소스 정리
    """
    # Startup
    logger.info("Starting Reddit Insight Dashboard...")

    # 데이터베이스 초기화
    from reddit_insight.dashboard.database import init_db
    init_db()
    logger.info("Database initialized")

    # 디렉토리 존재 확인
    if not TEMPLATES_DIR.exists():
        logger.warning(f"Templates directory not found: {TEMPLATES_DIR}")
    if not STATIC_DIR.exists():
        logger.warning(f"Static directory not found: {STATIC_DIR}")

    # 스케줄러 시작
    from reddit_insight.dashboard.scheduler import start_scheduler, stop_scheduler
    start_scheduler()
    logger.info("Scheduler started")

    logger.info("Dashboard startup complete")

    yield

    # Shutdown
    logger.info("Shutting down Reddit Insight Dashboard...")
    stop_scheduler()
    logger.info("Dashboard shutdown complete")


def create_app() -> FastAPI:
    """FastAPI 애플리케이션 인스턴스를 생성한다.

    Returns:
        FastAPI: 설정이 완료된 FastAPI 앱 인스턴스
    """
    application = FastAPI(
        title="Reddit Insight Dashboard",
        description="Reddit 데이터 분석 인사이트 대시보드",
        version="0.1.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        lifespan=lifespan,
    )

    # CORS 미들웨어 설정
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 프로덕션에서는 특정 도메인으로 제한
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 요청 로깅 미들웨어 (DB에 기록)
    from reddit_insight.dashboard.monitoring import RequestLoggingMiddleware
    application.add_middleware(RequestLoggingMiddleware)

    # Rate Limiting 미들웨어
    from reddit_insight.dashboard.rate_limit import RateLimitMiddleware
    application.add_middleware(RateLimitMiddleware)

    # 글로벌 예외 핸들러
    @application.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """처리되지 않은 예외를 처리한다."""
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "detail": str(exc) if application.debug else "An unexpected error occurred",
            },
        )

    # 요청 로깅 미들웨어
    @application.middleware("http")
    async def log_requests(request: Request, call_next):
        """모든 HTTP 요청을 로깅한다."""
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time

        logger.info(
            f"{request.method} {request.url.path} "
            f"- Status: {response.status_code} "
            f"- Time: {process_time:.3f}s"
        )
        return response

    # 정적 파일 마운트
    application.mount(
        "/static",
        StaticFiles(directory=str(STATIC_DIR)),
        name="static",
    )

    # 템플릿 설정
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
    application.state.templates = templates

    # 기본 라우트 등록
    @application.get("/", include_in_schema=False)
    async def root() -> RedirectResponse:
        """루트 경로에서 대시보드로 리다이렉트한다."""
        return RedirectResponse(url="/dashboard", status_code=302)

    @application.get("/health", tags=["system"])
    async def health_check() -> dict[str, Any]:
        """헬스체크 엔드포인트.

        Returns:
            dict: 서비스 상태 정보
        """
        return {
            "status": "healthy",
            "service": "reddit-insight-dashboard",
            "version": "0.1.0",
        }

    # 라우터 등록 (지연 임포트로 순환 참조 방지)
    from reddit_insight.dashboard.routers import (
        alerts,
        api,
        clusters,
        comparison,
        competition,
        dashboard,
        demands,
        insights,
        live,
        llm,
        search,
        topics,
        trends,
    )

    application.include_router(dashboard.router)
    application.include_router(trends.router)
    application.include_router(demands.router)
    application.include_router(competition.router)
    application.include_router(insights.router)
    application.include_router(topics.router)
    application.include_router(clusters.router)
    application.include_router(comparison.router)
    application.include_router(llm.router)
    application.include_router(live.router)
    application.include_router(alerts.router)
    application.include_router(search.router)
    application.include_router(api.router)

    return application


# 기본 앱 인스턴스 생성
app = create_app()
