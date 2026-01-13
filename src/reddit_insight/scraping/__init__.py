"""Reddit 웹 스크래핑 모듈.

API 제한 시 백업으로 사용할 웹 스크래핑 기능을 제공합니다.
- ScrapingClient: User-Agent 로테이션 및 재시도 지원 HTTP 클라이언트
- RateLimiter: 요청 속도 제어
- RedditScraper: Reddit 페이지 파싱 (추후 구현 예정)
"""

from reddit_insight.scraping.rate_limiter import RateLimiter

# ScrapingClient는 Task 3에서 구현 후 export
# from reddit_insight.scraping.http_client import ScrapingClient

__all__ = [
    # "ScrapingClient",  # Task 3에서 추가
    "RateLimiter",
    # "RedditScraper",  # Phase 03-02에서 구현 예정
]
