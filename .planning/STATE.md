# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-13)

**Core value:** 관심사를 비즈니스 모델로 연결하는 실행 가능한 인사이트
**Current focus:** Phase 7 — Competitive Analysis

## Current Position

Phase: 7 of 10 (Competitive Analysis)
Plan: Not started
Status: Ready to plan
Last activity: 2026-01-13 — Phase 6 completed

Progress: ██████░░░░ 60%

## Performance Metrics

**Velocity:**
- Total plans completed: 22
- Average duration: —
- Total execution time: —

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1. Foundation | 2 | — | — |
| 2. Reddit API | 3 | — | — |
| 3. Web Scraping | 3 | — | — |
| 4. Data Pipeline | 3 | — | — |
| 5. Trend Analysis | 4 | — | — |
| 6. Demand Discovery | 3 | — | — |

**Recent Trend:**
- Last 5 plans: 05-03, 05-04, 06-01, 06-02, 06-03
- Trend: —

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- src layout 선택 (editable install 호환성)
- pydantic-settings로 환경변수 관리
- rich.logging.RichHandler로 터미널 로깅
- PRAW 라이브러리로 Reddit API 연동
- Pydantic 모델로 데이터 구조화 (Post, Comment, SubredditInfo)
- old.reddit.com JSON API로 스크래핑
- UnifiedDataSource로 API/스크래핑 자동 전환
- SQLAlchemy 2.0 + aiosqlite로 데이터베이스 (async)
- Repository 패턴으로 데이터 접근 추상화
- CLI 진입점: reddit-insight
- YAKE + TF-IDF 키워드 추출 (lightweight, 학습 불필요)
- 시계열 트렌드 분석 (이동 평균, 변화율, 기울기)
- Rising Score 0-100 (새 키워드 보너스)
- 정규식 기반 수요 패턴 탐지 (20개 영어 패턴)
- 5가지 수요 카테고리 (FEATURE_REQUEST, PAIN_POINT, SEARCH_QUERY, WILLINGNESS_TO_PAY, ALTERNATIVE_SEEKING)
- 우선순위 점수 = 빈도(30%) + 구매의향(30%) + 긴급도(20%) + 최신성(20%)

### Deferred Issues

None yet.

### Blockers/Concerns

None yet.

## Session Continuity

Last session: 2026-01-13
Stopped at: Phase 6 완료, Phase 7 준비
Resume file: None
