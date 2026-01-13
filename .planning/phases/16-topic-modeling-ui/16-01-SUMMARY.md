# Summary 16-01: Topic Modeling UI

## Outcome

**Status**: COMPLETE

TopicModeler ML 모듈의 토픽 분석 결과를 대시보드에 시각화하는 기능을 완성했다. 토픽별 키워드 카드, 토픽 분포 차트, coherence score를 표시한다.

## Changes Made

### New Files

| File | Purpose |
|------|---------|
| `src/reddit_insight/dashboard/services/topic_service.py` | TopicModeler 래퍼 서비스 |
| `src/reddit_insight/dashboard/routers/topics.py` | Topics 라우터 (페이지 및 API) |
| `src/reddit_insight/dashboard/templates/topics/index.html` | Topics 메인 페이지 템플릿 |
| `src/reddit_insight/dashboard/templates/topics/partials/topic_cards.html` | 토픽 카드 HTMX 파셜 |
| `tests/dashboard/test_topic_service.py` | TopicService 단위 테스트 |

### Modified Files

| File | Change |
|------|--------|
| `src/reddit_insight/dashboard/services/__init__.py` | TopicService export 추가 |
| `src/reddit_insight/dashboard/routers/__init__.py` | topics 라우터 export 추가 |
| `src/reddit_insight/dashboard/app.py` | topics 라우터 등록 |
| `src/reddit_insight/dashboard/templates/base.html` | 내비게이션에 Topics 메뉴 추가 |

## Architecture

```
User visits /dashboard/topics
    |
Topics page loads with controls
    |
User clicks "Run Analysis"
    |
runTopicAnalysis() [JavaScript]
    |
GET /dashboard/topics/analyze?n_topics=5&method=auto
    |
TopicService.analyze_topics(n_topics, method)
    |
TopicModeler.fit_transform(documents)
    |
TopicAnalysisView.to_chart_data()
    |
Chart.js visualization (distribution pie + coherence bar)
    +
Topic keyword cards
```

## Features Implemented

1. **TopicService**
   - `analyze_topics(n_topics, method, documents)` 메서드
   - 저장된 분석 데이터에서 자동 문서 추출
   - Chart.js 형식 데이터 변환 (`to_chart_data()`)
   - 토픽별 문서 분포 계산

2. **API Endpoints**
   - `GET /dashboard/topics` - 메인 페이지
   - `GET /dashboard/topics/analyze` - 토픽 분석 JSON
   - `GET /dashboard/topics/distribution` - 토픽 분포 데이터
   - `GET /dashboard/topics/keywords-partial` - 키워드 카드 HTML
   - `GET /dashboard/topics/document-count` - 문서 수 확인

3. **UI Components**
   - 토픽 수 조절 슬라이더 (2-10)
   - 방법 선택 드롭다운 (Auto/LDA/NMF)
   - 요약 카드 (토픽 수, 방법, coherence, 문서 수)
   - 토픽 분포 도넛 차트
   - 토픽 coherence 점수 바 차트
   - 토픽별 키워드 카드 (색상 구분)

4. **Topic Modeling Methods**
   - auto (데이터 크기에 따라 자동 선택)
   - lda (Latent Dirichlet Allocation)
   - nmf (Non-negative Matrix Factorization)

## Verification

### Tests

```bash
pytest tests/dashboard/test_topic_service.py -v
# 19 passed in 1.81s
```

### Manual Testing

```bash
# 서버 시작
python -m reddit_insight.dashboard.main

# API 테스트
curl "http://localhost:8888/dashboard/topics/analyze?n_topics=5&method=auto"

# UI 확인
# 브라우저에서 /dashboard/topics → "Run Analysis" 클릭
```

## Commits

1. `9f577f0` - feat(16-01): add topic service
2. `a9c30da` - feat(16-01): add topics router
3. `08a1bc4` - feat(16-01): add topics page template
4. `7f2be87` - feat(16-01): add topics to navigation and register router
5. `196aa72` - test(16-01): add topic service tests

## Success Criteria Met

- [x] TopicService가 TopicModeler 호출 성공
- [x] `/dashboard/topics` 페이지 렌더링
- [x] 토픽별 키워드 카드 표시
- [x] 토픽 분포 파이 차트 표시
- [x] Coherence Score 표시

## Notes

- 토픽별 고유 색상 10가지 팔레트 적용 (blue, red, green, purple, orange, teal, pink, yellow, indigo, gray)
- 저장된 분석 데이터에서 문서 자동 추출 (insights, keywords, demands, competition)
- 10자 미만의 짧은 문서는 자동 필터링
- 토픽 분포는 각 문서의 dominant topic 기준으로 계산
- 데이터 부족 시 친절한 안내 메시지 표시
