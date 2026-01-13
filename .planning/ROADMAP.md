# Roadmap: Reddit Insight

## Overview

Reddit 데이터 수집부터 비즈니스 인사이트 도출까지의 전체 파이프라인을 구축한다. 먼저 데이터 수집 인프라(API + 스크래핑)를 구축하고, 분석 엔진(트렌드, 수요, 경쟁)을 순차적으로 개발한 후, 이를 비즈니스 모델로 연결하는 인사이트 레이어를 추가한다. 최종적으로 웹 대시보드와 리포트 기능으로 결과를 제공한다.

## Domain Expertise

None

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

- [x] **Phase 1: Foundation** - 프로젝트 셋업, 개발 환경 구성
- [x] **Phase 2: Reddit API Integration** - Reddit API 클라이언트, 인증, 데이터 수집
- [x] **Phase 3: Web Scraping Fallback** - API 제한 시 스크래핑 백업 시스템
- [x] **Phase 4: Data Storage & Pipeline** - 데이터베이스, 전처리 파이프라인
- [x] **Phase 5: Trend Analysis Engine** - 키워드 추출, 시계열 분석
- [x] **Phase 6: Demand Discovery** - "이거 있으면 좋겠다" 패턴 탐지
- [x] **Phase 7: Competitive Analysis** - 제품/서비스 반응 및 불만 분석
- [x] **Phase 8: Business Model Insights** - 인사이트 → 실행 가능한 기회 연결
- [ ] **Phase 9: Web Dashboard** - 인사이트 시각화 대시보드
- [ ] **Phase 10: Report Export & Polish** - 마크다운 리포트 생성, 통합 테스트

## Phase Details

### Phase 1: Foundation
**Goal**: 프로젝트 구조 설정, 개발 환경 구성, 기본 설정 파일 생성
**Depends on**: Nothing (first phase)
**Research**: Unlikely (established patterns)
**Plans**: TBD

Plans:
- [x] 01-01: 프로젝트 구조 및 의존성 설정
- [x] 01-02: 설정 관리 및 환경 변수 시스템

### Phase 2: Reddit API Integration
**Goal**: Reddit API를 통한 안정적인 데이터 수집 파이프라인 구축
**Depends on**: Phase 1
**Research**: Likely (external API)
**Research topics**: Reddit API 인증 방식 (OAuth2), rate limits, 데이터 구조 (posts, comments, subreddits)
**Plans**: TBD

Plans:
- [x] 02-01: Reddit API 클라이언트 및 인증
- [x] 02-02: 게시물 및 댓글 수집기
- [x] 02-03: Subreddit 탐색 및 메타데이터 수집

### Phase 3: Web Scraping Fallback
**Goal**: API 제한 시 백업으로 사용할 스크래핑 시스템 구축
**Depends on**: Phase 2
**Research**: Likely (scraping strategy)
**Research topics**: Reddit HTML 구조, anti-scraping 대응, 스크래핑 라이브러리 (BeautifulSoup, Playwright)
**Plans**: TBD

Plans:
- [x] 03-01: 스크래핑 인프라 설정
- [x] 03-02: Reddit 페이지 파서
- [x] 03-03: API/스크래핑 자동 전환 로직

### Phase 4: Data Storage & Pipeline
**Goal**: 수집된 데이터를 저장하고 분석을 위해 전처리하는 파이프라인 구축
**Depends on**: Phase 2, Phase 3
**Research**: Unlikely (standard patterns)
**Plans**: TBD

Plans:
- [x] 04-01: 데이터베이스 스키마 및 모델
- [x] 04-02: 데이터 전처리 파이프라인
- [x] 04-03: 데이터 수집 스케줄러

### Phase 5: Trend Analysis Engine
**Goal**: 키워드 추출 및 시계열 분석으로 트렌드 파악
**Depends on**: Phase 4
**Research**: Likely (NLP/분석 기법)
**Research topics**: 키워드 추출 알고리즘 (TF-IDF, KeyBERT), 시계열 분석, 오픈소스 NLP 도구
**Plans**: TBD

Plans:
- [x] 05-01: 텍스트 전처리 및 토큰화
- [x] 05-02: 키워드 추출 엔진
- [x] 05-03: 시계열 트렌드 분석
- [x] 05-04: 급상승 키워드 탐지

### Phase 6: Demand Discovery
**Goal**: "이거 있으면 좋겠다" 패턴을 자동 탐지하여 미충족 수요 발굴
**Depends on**: Phase 5
**Research**: Likely (패턴 인식 기법)
**Research topics**: 텍스트 분류, 의도 분석, 로컬 LLM 활용 (Ollama 등)
**Plans**: TBD

Plans:
- [x] 06-01: 수요 표현 패턴 정의
- [x] 06-02: 패턴 매칭 엔진
- [x] 06-03: 수요 분류 및 우선순위화

### Phase 7: Competitive Analysis
**Goal**: 제품/서비스에 대한 반응, 불만, 대안 요구 분석
**Depends on**: Phase 5
**Research**: Likely (감성 분석)
**Research topics**: 감성 분석 모델, 엔티티 인식, 오픈소스 도구 (VADER, transformers)
**Plans**: TBD

Plans:
- [x] 07-01: 제품/서비스 엔티티 인식
- [x] 07-02: 감성 분석 엔진
- [x] 07-03: 불만 및 대안 요구 추출

### Phase 8: Business Model Insights
**Goal**: 분석 결과를 비즈니스 기회로 연결하는 인사이트 생성
**Depends on**: Phase 6, Phase 7
**Research**: Unlikely (domain logic based on previous phases)
**Plans**: TBD

Plans:
- [x] 08-01: 인사이트 생성 규칙 엔진
- [x] 08-02: 비즈니스 기회 스코어링
- [x] 08-03: 실행 가능성 분석

### Phase 9: Web Dashboard
**Goal**: 모든 인사이트를 시각화하는 대시보드 구축
**Depends on**: Phase 8
**Research**: Unlikely (standard frontend patterns)
**Plans**: TBD

Plans:
- [ ] 09-01: 대시보드 프레임워크 설정
- [ ] 09-02: 트렌드 시각화 컴포넌트
- [ ] 09-03: 수요/경쟁 분석 뷰
- [ ] 09-04: 비즈니스 인사이트 뷰
- [ ] 09-05: 필터 및 검색 기능

### Phase 10: Report Export & Polish
**Goal**: 마크다운 리포트 생성 및 전체 시스템 통합 테스트
**Depends on**: Phase 9
**Research**: Unlikely (established patterns)
**Plans**: TBD

Plans:
- [ ] 10-01: 마크다운 리포트 템플릿
- [ ] 10-02: 리포트 생성 엔진
- [ ] 10-03: 엔드투엔드 테스트
- [ ] 10-04: UX 개선 및 문서화

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 2/2 | Complete | 2026-01-13 |
| 2. Reddit API Integration | 3/3 | Complete | 2026-01-13 |
| 3. Web Scraping Fallback | 3/3 | Complete | 2026-01-13 |
| 4. Data Storage & Pipeline | 3/3 | Complete | 2026-01-13 |
| 5. Trend Analysis Engine | 4/4 | Complete | 2026-01-13 |
| 6. Demand Discovery | 3/3 | Complete | 2026-01-13 |
| 7. Competitive Analysis | 3/3 | Complete | 2026-01-13 |
| 8. Business Model Insights | 3/3 | Complete | 2026-01-13 |
| 9. Web Dashboard | 0/5 | Not started | - |
| 10. Report Export & Polish | 0/4 | Not started | - |
