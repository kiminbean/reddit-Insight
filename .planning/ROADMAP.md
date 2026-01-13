# Roadmap: Reddit Insight

## Overview

Reddit 데이터 수집부터 비즈니스 인사이트 도출까지의 전체 파이프라인을 구축한다. 먼저 데이터 수집 인프라(API + 스크래핑)를 구축하고, 분석 엔진(트렌드, 수요, 경쟁)을 순차적으로 개발한 후, 이를 비즈니스 모델로 연결하는 인사이트 레이어를 추가한다. 최종적으로 웹 대시보드와 리포트 기능으로 결과를 제공한다.

## Milestones

- ✅ **v1.0 MVP** - Phases 1-11 (shipped 2026-01-14)
- ✅ **v1.1 Dashboard & ML Integration** - Phases 12-19 (shipped 2026-01-14)

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
- [x] **Phase 9: Web Dashboard** - 인사이트 시각화 대시보드
- [x] **Phase 10: Report Export & Polish** - 마크다운 리포트 생성, 통합 테스트
- [x] **Phase 11: Advanced Analytics** - 고급 분석 기능 (머신러닝 기반 예측)
- [x] **Phase 12: Dashboard Data Integration** - DemandService, CompetitionService 실제 데이터 연동
- [x] **Phase 13: Recent Analyses** - 대시보드 홈 분석 기록 표시
- [x] **Phase 14: Trend Prediction UI** - 시계열 예측 차트 시각화
- [x] **Phase 15: Anomaly Detection UI** - 이상 탐지 결과 시각화
- [x] **Phase 16: Topic Modeling UI** - 토픽 분석 결과 시각화
- [x] **Phase 17: Text Clustering UI** - 클러스터링 결과 시각화
- [x] **Phase 18: Dashboard Polish** - UI/UX 개선, 반응형 디자인
- [x] **Phase 19: Integration Testing** - E2E 테스트, 성능 최적화

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
- [x] 09-01: 대시보드 프레임워크 설정
- [x] 09-02: 트렌드 시각화 컴포넌트
- [x] 09-03: 수요/경쟁 분석 뷰
- [x] 09-04: 비즈니스 인사이트 뷰
- [x] 09-05: 필터 및 검색 기능

### Phase 10: Report Export & Polish
**Goal**: 마크다운 리포트 생성 및 전체 시스템 통합 테스트
**Depends on**: Phase 9
**Research**: Unlikely (established patterns)
**Plans**: TBD

Plans:
- [x] 10-01: 마크다운 리포트 템플릿
- [x] 10-02: 리포트 생성 엔진
- [x] 10-03: 엔드투엔드 테스트
- [x] 10-04: UX 개선 및 문서화

### Phase 11: Advanced Analytics
**Goal**: 머신러닝 기반 고급 분석 기능 구현 - 트렌드 예측, 이상 탐지, 클러스터링
**Depends on**: Phase 10
**Research**: Likely (ML algorithms, model selection)
**Research topics**: 시계열 예측 (statsmodels ETS/ARIMA), 이상 탐지 (Isolation Forest, z-score), 토픽 모델링 (LDA/NMF), 클러스터링 (K-means)
**Plans**: 4 plans

Plans:
- [x] 11-01: ML Infrastructure - 의존성, 기반 클래스, 데이터 모델
- [x] 11-02: Trend Prediction - 시계열 예측 엔진 (ETS/ARIMA)
- [x] 11-03: Anomaly Detection - 이상 탐지 엔진 (z-score, IQR, Isolation Forest)
- [x] 11-04: Topic Modeling & Clustering - 토픽 모델링 (LDA/NMF), 텍스트 클러스터링

---

### ✅ v1.1 Dashboard & ML Integration (Complete)

**Milestone Goal:** 대시보드의 실제 데이터 연동 완성 및 ML 분석 결과 시각화 통합
**Shipped:** 2026-01-14

#### Phase 12: Dashboard Data Integration
**Goal**: DemandService, CompetitionService에 실제 분석 데이터 연동
**Depends on**: Phase 11
**Research**: Unlikely (internal patterns, existing data_store.py)
**Plans**: 1 plan

Plans:
- [x] 12-01: Dashboard Data Integration Verification

#### Phase 13: Recent Analyses
**Goal**: 대시보드 홈에 최근 분석 기록 표시 기능 완성
**Depends on**: Phase 12
**Research**: Unlikely (existing DashboardService patterns)
**Plans**: 1 plan

Plans:
- [x] 13-01: Recent Analyses Display Enhancement

#### Phase 14: Trend Prediction UI
**Goal**: 시계열 예측 결과를 차트로 시각화 (예측값 + 신뢰구간)
**Depends on**: Phase 13
**Research**: Unlikely (Chart.js already integrated)
**Plans**: 1 plan

Plans:
- [x] 14-01: Trend Prediction UI

#### Phase 15: Anomaly Detection UI
**Goal**: 이상 탐지 결과 시각화 (이상 포인트 하이라이트)
**Depends on**: Phase 14
**Research**: Unlikely (existing chart patterns)
**Plans**: 1 plan

Plans:
- [x] 15-01: Anomaly Detection UI

#### Phase 16: Topic Modeling UI
**Goal**: 토픽 분석 결과 시각화 (토픽별 키워드, 문서 분포)
**Depends on**: Phase 15
**Research**: Unlikely (existing visualization patterns)
**Plans**: 1 plan

Plans:
- [x] 16-01: Topic Modeling UI

#### Phase 17: Text Clustering UI
**Goal**: 클러스터링 결과 시각화 (클러스터별 키워드, 대표 문서)
**Depends on**: Phase 16
**Research**: Unlikely (existing visualization patterns)
**Plans**: 1 plan

Plans:
- [x] 17-01: Text Clustering UI

#### Phase 18: Dashboard Polish
**Goal**: UI/UX 개선, 반응형 디자인, 사용성 향상
**Depends on**: Phase 17
**Research**: Unlikely (Tailwind/HTMX existing patterns)
**Plans**: 1 plan

Plans:
- [x] 18-01: Dashboard UI/UX Polish

#### Phase 19: Integration Testing
**Goal**: E2E 테스트 보강, 성능 최적화, 문서 업데이트
**Depends on**: Phase 18
**Research**: Unlikely (existing test patterns)
**Plans**: 1 plan

Plans:
- [x] 19-01: Integration Testing & Performance Optimization

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → ... → 11 (v1.0) → 12 → ... → 19 (v1.1)

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
| 9. Web Dashboard | 5/5 | Complete | 2026-01-13 |
| 10. Report Export & Polish | 4/4 | Complete | 2026-01-13 |
| 11. Advanced Analytics | 4/4 | Complete | 2026-01-14 |
| 12. Dashboard Data Integration | 1/1 | Complete | 2026-01-14 |
| 13. Recent Analyses | 1/1 | Complete | 2026-01-14 |
| 14. Trend Prediction UI | 1/1 | Complete | 2026-01-14 |
| 15. Anomaly Detection UI | 1/1 | Complete | 2026-01-14 |
| 16. Topic Modeling UI | 1/1 | Complete | 2026-01-14 |
| 17. Text Clustering UI | 1/1 | Complete | 2026-01-14 |
| 18. Dashboard Polish | 1/1 | Complete | 2026-01-14 |
| 19. Integration Testing | 1/1 | Complete | 2026-01-14 |
