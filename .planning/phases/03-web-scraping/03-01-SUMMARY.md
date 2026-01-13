---
phase: 03-web-scraping
plan: 01
status: completed
completed_at: 2025-01-13
commits: ["562c972", "435a7fc", "9839fc9", "c985b91"]
---

# 03-01 Summary: 웹 스크래핑 인프라 설정

## Objective Achieved
API 제한 시 백업으로 사용할 웹 스크래핑 인프라를 구축했습니다.

## What Was Built

### 1. 의존성 추가 (`pyproject.toml`)
- `beautifulsoup4>=4.12.0`: HTML 파싱
- `lxml>=5.0.0`: 빠른 XML/HTML 파서

### 2. Rate Limiter (`src/reddit_insight/scraping/rate_limiter.py`)
- **RateLimiter 클래스**
  - 슬라이딩 윈도우 기반 분당 요청 수 제한
  - 기본값: 30 req/min (API 60 req/min보다 보수적)
  - 최소 요청 간격 보장 (기본 1.0초)
  - async 컨텍스트 매니저 지원 (`async with limiter:`)
  - 동기화를 위한 asyncio.Lock 사용

### 3. HTTP 클라이언트 (`src/reddit_insight/scraping/http_client.py`)
- **ScrapingClient 클래스**
  - httpx.AsyncClient 기반 비동기 HTTP 요청
  - 12개 User-Agent 로테이션 (Chrome, Firefox, Safari, Edge)
  - 재시도 로직: exponential backoff (최대 3회)
  - 429 Rate Limit 응답 자동 처리 (Retry-After 헤더 존중)
  - 5xx 서버 오류 시 재시도
  - `get_json()` 메서드: Reddit .json URL 지원

- **ScrapingError 예외 클래스**
  - status_code 속성으로 HTTP 상태 코드 추적

### 4. 모듈 구조 (`src/reddit_insight/scraping/`)
```
scraping/
├── __init__.py      # ScrapingClient, ScrapingError, RateLimiter export
├── http_client.py   # HTTP 클라이언트 구현
└── rate_limiter.py  # 요청 속도 제어
```

## Key Implementation Details

### Anti-blocking 대책
1. **User-Agent 로테이션**: 12개 브라우저 UA 순환 + 20% 무작위
2. **Rate limiting**: 30 req/min (보수적 설정)
3. **최소 요청 간격**: 1초
4. **브라우저 모방 헤더**: Accept, DNT, Sec-Fetch-* 등

### 재시도 전략
- 429 응답: Retry-After 헤더 값만큼 대기
- 5xx 오류: exponential backoff (1s, 2s, 4s)
- 타임아웃: 동일 backoff 적용
- 최대 3회 재시도 후 ScrapingError 발생

## Usage Example

```python
from reddit_insight.scraping import ScrapingClient, RateLimiter

# 기본 사용
async with ScrapingClient() as client:
    response = await client.get("https://old.reddit.com/r/python")
    html = response.text

# JSON 응답 (Reddit 비공식 API)
async with ScrapingClient() as client:
    data = await client.get_json("https://old.reddit.com/r/python.json")
    posts = data["data"]["children"]

# 커스텀 Rate Limiter
limiter = RateLimiter(requests_per_minute=20, min_delay=2.0)
client = ScrapingClient(rate_limiter=limiter)
```

## Verification Results
- [x] beautifulsoup4, lxml 의존성 추가됨
- [x] RateLimiter가 요청 속도 제어 (30 req/min, 1.0s delay)
- [x] ScrapingClient가 User-Agent 로테이션 (12개) 및 재시도 지원
- [x] `from reddit_insight.scraping import ScrapingClient, RateLimiter` 가능

## Files Modified
- `pyproject.toml`: 스크래핑 의존성 추가
- `src/reddit_insight/scraping/__init__.py`: 모듈 초기화
- `src/reddit_insight/scraping/rate_limiter.py`: Rate Limiter 구현
- `src/reddit_insight/scraping/http_client.py`: HTTP 클라이언트 구현

## Next Steps
- **03-02**: RedditScraper 구현 (HTML 파싱, 게시물/댓글 추출)
- **03-03**: 스크래핑 결과를 Post/Comment 모델로 변환
