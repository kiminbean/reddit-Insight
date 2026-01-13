# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-13)

**Core value:** 관심사를 비즈니스 모델로 연결하는 실행 가능한 인사이트
**Current focus:** Phase 9 — Web Dashboard

## Current Position

Phase: 9 of 10 (Web Dashboard)
Plan: Not started
Status: Ready to plan
Last activity: 2026-01-13 — Phase 8 completed

Progress: ████████░░ 80%

## Performance Metrics

**Velocity:**
- Total plans completed: 28
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
| 7. Competitive Analysis | 3 | — | — |
| 8. Business Insights | 3 | — | — |

**Recent Trend:**
- Last 5 plans: 07-02, 07-03, 08-01, 08-02, 08-03
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
- 패턴 기반 엔티티 인식 (제품/서비스/브랜드/기술)
- 규칙 기반 감성 분석 (96 positive, 107 negative words + Reddit slang)
- 불만 추출 (7가지 유형) + 대안 비교 추출 (5가지 유형)
- CompetitiveAnalyzer로 엔티티별 인사이트 리포트
- 규칙 기반 인사이트 생성 (5가지 InsightType)
- 비즈니스 기회 스코어링 (5차원: 시장규모, 경쟁, 긴급성, 트렌드, 실현가능성)
- 실행 가능성 분석 (5요소: 기술복잡도, 리소스, 시장장벽, 시간가치, 경쟁리스크)
- InsightReportGenerator로 마크다운 리포트 생성

### Deferred Issues

None yet.

### Blockers/Concerns

None yet.

## Session Continuity

Last session: 2026-01-13
Stopped at: Phase 8 완료, Phase 9 준비
Resume file: None
