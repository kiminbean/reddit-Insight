"""대시보드 라우터 패키지."""

from reddit_insight.dashboard.routers import (
    competition,
    dashboard,
    demands,
    insights,
    search,
    topics,
    trends,
)

__all__ = [
    "competition",
    "dashboard",
    "demands",
    "insights",
    "search",
    "topics",
    "trends",
]
