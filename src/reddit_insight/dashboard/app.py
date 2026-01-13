"""FastAPI 기반 웹 대시보드 애플리케이션.

Reddit Insight 분석 결과를 시각화하는 웹 대시보드를 제공한다.
서버 사이드 렌더링(Jinja2)과 HTMX를 활용하여 최소한의 JavaScript로 동적 UI를 구현한다.
"""

from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# 패키지 내부 경로 설정
PACKAGE_DIR = Path(__file__).parent
TEMPLATES_DIR = PACKAGE_DIR / "templates"
STATIC_DIR = PACKAGE_DIR / "static"


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
    )

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
    from reddit_insight.dashboard.routers import dashboard, trends

    application.include_router(dashboard.router)
    application.include_router(trends.router)

    return application


# 기본 앱 인스턴스 생성
app = create_app()
