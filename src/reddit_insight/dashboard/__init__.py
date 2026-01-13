"""Reddit Insight 웹 대시보드 패키지.

FastAPI 기반 웹 대시보드를 제공한다.
- Jinja2 템플릿으로 서버 사이드 렌더링
- HTMX로 동적 UI 구현
- TailwindCSS로 스타일링 (CDN)
"""

from reddit_insight.dashboard.app import app, create_app

__all__ = ["app", "create_app"]
