"""Reddit 웹 스크래핑 모듈.

API 제한 시 백업으로 사용할 웹 스크래핑 기능을 제공합니다.
- ScrapingClient: User-Agent 로테이션 및 재시도 지원 HTTP 클라이언트
- RateLimiter: 요청 속도 제어
- RedditScraper: Reddit JSON 엔드포인트를 사용한 데이터 수집
- RedditJSONParser: Reddit JSON 응답 파싱
"""

from reddit_insight.scraping.http_client import ScrapingClient, ScrapingError
from reddit_insight.scraping.parser import RedditJSONParser
from reddit_insight.scraping.rate_limiter import RateLimiter
from reddit_insight.scraping.reddit_scraper import RedditScraper

__all__ = [
    "ScrapingClient",
    "ScrapingError",
    "RateLimiter",
    "RedditScraper",
    "RedditJSONParser",
]
