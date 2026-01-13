---
phase: 03-web-scraping
plan: 03
status: completed
started: 2026-01-13T00:00:00Z
completed: 2026-01-13T00:00:00Z
---

## Summary

API와 스크래핑 간 자동 전환 로직을 성공적으로 구현했습니다.

UnifiedDataSource 클래스를 통해:
- API 우선 시도, 실패 시 자동으로 스크래핑으로 폴백
- 4가지 전략 지원 (API_ONLY, SCRAPING_ONLY, API_FIRST, SCRAPING_FIRST)
- 연속 실패 추적 및 일시적 소스 비활성화
- 사용자는 데이터 소스를 신경 쓰지 않고 통합 인터페이스로 데이터 수집 가능

## Files Modified

| File | Action | Description |
|------|--------|-------------|
| `src/reddit_insight/data_source.py` | Created | UnifiedDataSource, DataSourceStrategy, SourceStatus, 예외 클래스 |
| `src/reddit_insight/__init__.py` | Modified | UnifiedDataSource, DataSourceStrategy 등 export |
| `tests/test_data_source.py` | Created | 32개 단위/통합 테스트 |
| `pyproject.toml` | Modified | asyncio marker 추가 |

## Verification Results

### 1. 열거형 및 예외 클래스
```
$ python -c "from reddit_insight.data_source import DataSourceStrategy, DataSourceError; print('OK')"
OK
```

### 2. UnifiedDataSource 기본 기능
```
$ python -c "from reddit_insight.data_source import UnifiedDataSource; ds = UnifiedDataSource(); print(ds)"
UnifiedDataSource(strategy=api_first, api_failures=0, scraping_failures=0)
```

### 3. 패키지 레벨 import
```
$ python -c "from reddit_insight import UnifiedDataSource, DataSourceStrategy; print('Package integration OK')"
Package integration OK
```

### 4. 테스트 결과
```
$ python -m pytest tests/test_data_source.py -v
======================== 32 passed, 2 warnings in 0.09s ========================
```

## API Summary

### UnifiedDataSource

```python
from reddit_insight import UnifiedDataSource, DataSourceStrategy

# 기본 사용 (API 우선, 실패 시 스크래핑)
ds = UnifiedDataSource()

# 전략 지정
ds = UnifiedDataSource(strategy=DataSourceStrategy.SCRAPING_ONLY)

# 비동기 데이터 수집
async def collect():
    # 게시물 수집
    posts = await ds.get_hot_posts("python", limit=50)
    posts = await ds.get_new_posts("python", limit=50)
    posts = await ds.get_top_posts("python", time_filter="week", limit=50)

    # 댓글 수집
    comments = await ds.get_post_comments("post_id", limit=100)

    # 서브레딧 정보
    info = await ds.get_subreddit_info("python")
    results = await ds.search_subreddits("data science", limit=25)

# 컨텍스트 매니저 사용
async with UnifiedDataSource() as ds:
    posts = await ds.get_hot_posts("python")

# 상태 확인
status = ds.get_status()
print(f"API 실패 횟수: {status.api_failure_count}")
print(f"스크래핑 실패 횟수: {status.scraping_failure_count}")
```

### DataSourceStrategy

| 전략 | 설명 |
|------|------|
| `API_ONLY` | API만 사용, 실패 시 에러 |
| `SCRAPING_ONLY` | 스크래핑만 사용, 실패 시 에러 |
| `API_FIRST` | API 우선, 실패 시 스크래핑 폴백 (기본값) |
| `SCRAPING_FIRST` | 스크래핑 우선, 실패 시 API 폴백 |

## Architecture

```
UnifiedDataSource
├── _strategy: DataSourceStrategy (전략)
├── _status: SourceStatus (상태 추적)
├── _api_client: RedditClient (lazy init)
└── _scraper: RedditScraper (lazy init)

Fallback Flow (API_FIRST):
1. API 시도 → 성공 → 반환
2. API 실패 → 실패 기록 → 스크래핑 시도
3. 스크래핑 성공 → 반환
4. 스크래핑 실패 → DataSourceError

연속 실패 처리:
- 5회 연속 실패 시 해당 소스 일시적 비활성화
- 성공 시 실패 카운트 리셋
```

## Notes

1. **비동기 처리**: API(PRAW)는 동기, 스크래핑은 비동기이므로 API 호출은 `asyncio.to_thread()`로 래핑됩니다.

2. **Lazy Initialization**: API 클라이언트와 스크래퍼는 실제 사용 시점에 초기화됩니다.

3. **폴백 트리거**: rate limit, 인증 오류, 네트워크 오류 등 다양한 에러 패턴을 감지하여 폴백을 트리거합니다.

4. **Phase 3 완료**: 이 계획으로 Phase 3 (Web Scraping)이 완료되었습니다.
   - 03-01: HTTP 클라이언트 및 Rate Limiter
   - 03-02: RedditScraper (JSON 파싱)
   - 03-03: UnifiedDataSource (API/스크래핑 통합)

5. **다음 단계**: Phase 4 (데이터 저장)에서 수집된 데이터를 영구 저장합니다.
