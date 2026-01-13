"""Reddit 웹 스크래핑 모듈.

API 제한 시 백업으로 사용할 웹 스크래핑 기능을 제공합니다.
- ScrapingClient: User-Agent 로테이션 및 재시도 지원 HTTP 클라이언트
- RateLimiter: 요청 속도 제어
- RedditScraper: Reddit 페이지 파싱 (Phase 03-02에서 구현 예정)
"""

from reddit_insight.scraping.http_client import ScrapingClient, ScrapingError
from reddit_insight.scraping.rate_limiter import RateLimiter

__all__ = [
    "ScrapingClient",
    "ScrapingError",
    "RateLimiter",
    # "RedditScraper",  # Phase 03-02에서 구현 예정
]
