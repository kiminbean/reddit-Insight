---
phase: 03-web-scraping
plan: 02
status: completed
completed_at: 2025-01-13
commits: ["741e8a3", "e7f70bd", "26cdfe8", "0fe79aa"]
---

# 03-02 Summary: Reddit 페이지 파서 구현

## Objective Achieved
old.reddit.com의 JSON 엔드포인트를 사용하여 Reddit 데이터를 수집하는 RedditScraper와 JSON 파서를 구현했습니다.

## What Was Built

### 1. JSON 파서 (`src/reddit_insight/scraping/parser.py`)
- **RedditJSONParser 클래스**
  - `parse_listing(data)`: Listing 응답에서 children 추출
  - `parse_post(data)`: JSON -> Post 모델 변환
  - `parse_comment(data)`: JSON -> Comment 모델 변환
  - `parse_subreddit(data)`: JSON -> SubredditInfo 모델 변환
  - `get_after_token(data)`: 페이지네이션 토큰 추출

- **유틸리티 함수**
  - `extract_posts_from_response(response)`: Listing에서 Post 리스트 추출
  - `extract_comments_from_response(response)`: 댓글 응답에서 Comment 리스트 추출
  - `_flatten_comment_tree(parser, children)`: 중첩 댓글 트리 평탄화

### 2. RedditScraper (`src/reddit_insight/scraping/reddit_scraper.py`)
- **게시물 수집 메서드**
  - `get_hot(subreddit, limit=100)`: Hot 게시물
  - `get_new(subreddit, limit=100)`: New 게시물
  - `get_top(subreddit, time_filter="week", limit=100)`: Top 게시물
  - `get_rising(subreddit, limit=100)`: Rising 게시물
  - `_fetch_posts(url, limit)`: 페이지네이션 지원 내부 메서드

- **댓글 수집 메서드**
  - `get_post_comments(post_id, limit=500)`: 게시물 댓글 (트리 평탄화)
  - `get_subreddit_comments(subreddit, limit=100)`: 서브레딧 댓글 스트림
  - `_flatten_comment_tree(children)`: 중첩 댓글 평탄화

- **서브레딧 정보 수집 메서드**
  - `get_subreddit_info(name)`: 서브레딧 정보 (/about.json)
  - `search_subreddits(query, limit=25)`: 서브레딧 검색

### 3. 모듈 구조 업데이트 (`src/reddit_insight/scraping/`)
```
scraping/
├── __init__.py       # +RedditScraper, RedditJSONParser export
├── http_client.py    # (기존)
├── rate_limiter.py   # (기존)
├── parser.py         # NEW: JSON 파서
└── reddit_scraper.py # NEW: Reddit 스크래퍼
```

## Key Implementation Details

### JSON 응답 구조 처리
- Reddit JSON 응답: `{"kind": "Listing", "data": {"children": [...]}}`
- Post: `{"kind": "t3", "data": {...}}`
- Comment: `{"kind": "t1", "data": {...}}`
- More: `{"kind": "more", ...}` (추가 댓글 표시, 스킵)

### 페이지네이션 지원
- `after` 파라미터로 다음 페이지 요청
- limit > 100인 경우 자동으로 여러 요청 수행
- 한 요청당 최대 100개 (Reddit API 제한)

### 댓글 트리 평탄화
- 중첩된 `replies` 필드 재귀적 처리
- `kind: "more"` 노드 스킵 (로드 더 보기)
- 삭제/제거된 댓글 ([deleted], [removed]) 필터링

### 데이터 모델 재사용
- `Post`, `Comment`, `SubredditInfo` 모델 사용 (`reddit_insight.reddit.models`)
- API와 스크래핑 모두 동일한 데이터 구조 반환

## Usage Example

```python
from reddit_insight.scraping import RedditScraper, ScrapingClient

# 컨텍스트 매니저로 사용
async with RedditScraper() as scraper:
    # 게시물 수집
    hot_posts = await scraper.get_hot("python", limit=50)
    top_posts = await scraper.get_top("python", time_filter="month", limit=100)

    # 댓글 수집
    comments = await scraper.get_post_comments("abc123", limit=200)
    recent = await scraper.get_subreddit_comments("python", limit=100)

    # 서브레딧 정보
    info = await scraper.get_subreddit_info("python")
    results = await scraper.search_subreddits("machine learning", limit=10)

# 외부 클라이언트 사용
async with ScrapingClient() as client:
    scraper = RedditScraper(client)
    posts = await scraper.get_new("datascience")
```

## Verification Results
- [x] JSON 파서가 Post, Comment, SubredditInfo 변환 지원
- [x] RedditScraper가 hot/new/top 게시물 수집 가능
- [x] 댓글 수집 및 트리 평탄화 동작
- [x] 서브레딧 정보 및 검색 가능

## Files Modified
- `src/reddit_insight/scraping/parser.py` (NEW): JSON 파서 구현
- `src/reddit_insight/scraping/reddit_scraper.py` (NEW): Reddit 스크래퍼 구현
- `src/reddit_insight/scraping/__init__.py`: export 업데이트

## Next Steps
- **03-03**: 스크래핑 테스트 및 API fallback 통합
- **Phase 04**: 데이터 저장소 구현
