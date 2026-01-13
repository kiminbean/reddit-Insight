---
phase: 09-web-dashboard
plan: 03
status: completed
completed_at: 2026-01-13
---

# 09-03 Summary: Demands and Competition Views

## Objective
수요 및 경쟁 분석 뷰를 구현하여 분석 결과를 시각화한다.

## Tasks Completed

### Task 1: Demands Router with DemandService
- **File**: `src/reddit_insight/dashboard/routers/demands.py`
- **Components**:
  - `DemandView`: 수요 뷰 모델 (id, category, text, priority_score, source_count, business_potential, keywords)
  - `DemandDetail`: 수요 상세 뷰 모델 (frequency_score, payment_intent_score, urgency_score, recency_score, sample_texts)
  - `DemandService`: DemandAnalyzer를 래핑하여 대시보드용 데이터 제공
- **Routes**:
  - `GET /dashboard/demands/`: 메인 페이지
  - `GET /dashboard/demands/list`: 수요 목록 HTMX partial (필터 지원)
  - `GET /dashboard/demands/{demand_id}`: 수요 상세
  - `GET /dashboard/demands/categories/stats`: 카테고리별 통계 JSON

### Task 2: Competition Router with CompetitionService
- **File**: `src/reddit_insight/dashboard/routers/competition.py`
- **Components**:
  - `EntityView`: 엔티티 뷰 모델 (name, entity_type, mention_count, sentiment_score, sentiment_label, complaint_count)
  - `EntityDetail`: 엔티티 상세 뷰 모델 (top_complaints, switch_to, switch_from, alternatives_mentioned)
  - `ComplaintView`: 불만 뷰 모델 (entity_name, complaint_type, text, severity, keywords)
  - `CompetitionService`: CompetitiveAnalyzer를 래핑하여 대시보드용 데이터 제공
- **Routes**:
  - `GET /dashboard/competition/`: 메인 페이지
  - `GET /dashboard/competition/entities`: 엔티티 목록 HTMX partial
  - `GET /dashboard/competition/entity/{name}`: 엔티티 상세
  - `GET /dashboard/competition/sentiment-chart`: 감성 분포 Chart.js JSON
  - `GET /dashboard/competition/complaints`: 불만 목록 HTMX partial
  - `GET /dashboard/competition/switches`: 인기 제품 전환 JSON

### Task 3: Templates
- **Demands Templates**:
  - `demands/index.html`: 메인 페이지 (카테고리 필터, 우선순위 슬라이더, 수요 카드 그리드)
  - `demands/detail.html`: 수요 상세 (점수 분석, 샘플 텍스트)
  - `demands/partials/demand_list.html`: HTMX partial 수요 목록
  - `demands/partials/demand_card.html`: 개별 수요 카드 컴포넌트
- **Competition Templates**:
  - `competition/index.html`: 메인 페이지 (엔티티 테이블, 감성 차트, 제품 전환 표)
  - `competition/entity_detail.html`: 엔티티 상세 (전환 현황, 불만 목록)
  - `competition/partials/entity_list.html`: HTMX partial 엔티티 테이블
  - `competition/partials/complaint_list.html`: HTMX partial 불만 목록

### Task 4: Router Registration
- **Files Modified**:
  - `src/reddit_insight/dashboard/app.py`: demands, competition 라우터 등록
  - `src/reddit_insight/dashboard/routers/__init__.py`: 새 라우터 export

## Features Implemented

### Demands Page
- Category filtering (Feature Request, Pain Point, Search Query, Willingness to Pay, Alternative Seeking)
- Priority score slider (0-100)
- Business potential badges (High/Medium/Low)
- Priority score breakdown visualization
- Keywords display
- Sample text quotes

### Competition Page
- Entity tracking table with sentiment indicators
- Sentiment distribution doughnut chart (Chart.js)
- Popular product switches visualization
- Top complaints list with severity indicators
- Entity detail with switch-to/switch-from tracking
- Complaint type categorization

### Common Components
- Sentiment badges (Positive/Neutral/Negative with colors)
- Priority bars with gradient coloring
- Category badges with distinct colors
- HTMX-powered dynamic filtering

## Verification

```bash
# All verifications passed:
python -c "from reddit_insight.dashboard.routers.demands import router; print('OK')"
python -c "from reddit_insight.dashboard.routers.competition import router; print('OK')"
python -c "from reddit_insight.dashboard.app import app; print('OK')"
ls src/reddit_insight/dashboard/templates/demands/index.html
ls src/reddit_insight/dashboard/templates/competition/index.html
```

## Commits
1. `feat(09-03): add demands router with DemandService` (already in 09-02)
2. `feat(09-03): add competition router with CompetitionService`
3. `feat(09-03): add demands and competition templates`
4. `feat(09-03): register demands and competition routers`

## Dependencies
- `reddit_insight.analysis.demand_analyzer.DemandAnalyzer`
- `reddit_insight.analysis.competitive.CompetitiveAnalyzer`
- `reddit_insight.analysis.demand_patterns.DemandCategory`
- Chart.js (CDN)
- HTMX (CDN)

## Next Steps
- 09-04: Insights 통합 뷰 구현
- 실제 분석 데이터 연동
- 사용자 분석 실행 인터페이스
