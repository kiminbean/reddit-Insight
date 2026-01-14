# API Reference

Reddit Insight의 REST API 레퍼런스 문서입니다.

## 목차

1. [개요](#개요)
2. [인증](#인증)
3. [Dashboard API](#dashboard-api)
4. [Trends API](#trends-api)
5. [ML Analysis API](#ml-analysis-api)
6. [Demands API](#demands-api)
7. [Competition API](#competition-api)
8. [Insights API](#insights-api)
9. [Reports API](#reports-api)
10. [Search API](#search-api)
11. [API v1 (Protected)](#api-v1-protected)
12. [에러 응답](#에러-응답)

---

## 개요

### Base URL

```
http://localhost:8000
```

### API 문서 URL

| URL | 설명 |
|-----|------|
| `/api/docs` | Swagger UI 문서 |
| `/api/redoc` | ReDoc 문서 |
| `/health` | 헬스체크 엔드포인트 |

### 응답 형식

모든 API는 다음 형식 중 하나로 응답합니다:

- **HTMLResponse**: 대시보드 페이지 및 HTMX 파셜
- **JSONResponse**: 차트 데이터 및 순수 API 응답

---

## 인증

### API 키 인증

Protected API(`/api/v1/*`)는 API 키 인증이 필요합니다.

```bash
# 헤더에 API 키 포함
curl -H "X-API-Key: your-api-key" http://localhost:8000/api/v1/subreddits
```

### API 키 생성

```bash
# CLI로 API 키 생성
reddit-insight api-key create --name "My App" --rate-limit 1000
```

### 대시보드 API

대시보드 관련 엔드포인트(`/dashboard/*`)는 인증 없이 접근 가능합니다.

---

## Dashboard API

대시보드 메인 페이지와 요약 데이터를 제공합니다.

### GET /dashboard

대시보드 홈 페이지를 렌더링합니다.

**응답**: HTMLResponse

**컨텍스트 데이터**:
- `summary`: 요약 통계 (서브레딧 수, 게시물 수, 댓글 수)
- `recent_analyses`: 최근 분석 기록 목록

---

### GET /dashboard/summary

대시보드 요약 데이터를 HTMX partial로 반환합니다.

**응답**: HTMLResponse (partial)

---

### GET /dashboard/analyze

분석 시작 페이지를 렌더링합니다.

**응답**: HTMLResponse

---

### GET /dashboard/analysis/{analysis_id}

특정 분석 결과의 상세 페이지를 렌더링합니다.

**경로 파라미터**:

| 파라미터 | 타입 | 설명 |
|---------|------|------|
| `analysis_id` | int | 분석 결과 ID |

**응답**: HTMLResponse

**상태 코드**:
- `200`: 성공
- `404`: 분석 결과 없음
- `500`: 서버 오류 (데이터베이스 연결 실패)

---

## Trends API

키워드 트렌드와 Rising 키워드를 시각화합니다.

### GET /dashboard/trends

트렌드 메인 페이지를 렌더링합니다.

**쿼리 파라미터**:

| 파라미터 | 타입 | 기본값 | 범위 | 설명 |
|---------|------|--------|------|------|
| `subreddit` | string | null | - | 필터링할 서브레딧 |
| `days` | int | 7 | 1-30 | 분석 기간(일) |
| `limit` | int | 20 | 1-100 | 표시할 키워드 수 |

**응답**: HTMLResponse

---

### GET /dashboard/trends/keywords

키워드 목록을 HTMX partial로 반환합니다.

**쿼리 파라미터**: `/dashboard/trends`와 동일

**응답**: HTMLResponse (partial)

---

### GET /dashboard/trends/rising

Rising 키워드를 HTMX partial로 반환합니다.

**쿼리 파라미터**:

| 파라미터 | 타입 | 기본값 | 범위 | 설명 |
|---------|------|--------|------|------|
| `subreddit` | string | null | - | 필터링할 서브레딧 |
| `limit` | int | 20 | 1-100 | 표시할 키워드 수 |

**응답**: HTMLResponse (partial)

---

### GET /dashboard/trends/chart-data

키워드 타임라인 차트 데이터를 JSON으로 반환합니다.

**쿼리 파라미터**:

| 파라미터 | 타입 | 기본값 | 범위 | 설명 |
|---------|------|--------|------|------|
| `keyword` | string | - | - | 타임라인을 조회할 키워드 (필수) |
| `days` | int | 7 | 1-30 | 분석 기간(일) |

**응답**: JSONResponse (Chart.js 형식)

```json
{
  "labels": ["2024-01-01", "2024-01-02", "..."],
  "datasets": [
    {
      "label": "python",
      "data": [10, 15, 12],
      "borderColor": "rgb(59, 130, 246)",
      "backgroundColor": "rgba(59, 130, 246, 0.1)",
      "fill": true,
      "tension": 0.3
    }
  ]
}
```

---

### GET /dashboard/trends/top-keywords-chart

상위 키워드 바 차트 데이터를 JSON으로 반환합니다.

**쿼리 파라미터**:

| 파라미터 | 타입 | 기본값 | 범위 | 설명 |
|---------|------|--------|------|------|
| `subreddit` | string | null | - | 필터링할 서브레딧 |
| `days` | int | 7 | 1-30 | 분석 기간(일) |
| `limit` | int | 10 | 1-20 | 표시할 키워드 수 |

**응답**: JSONResponse (Chart.js 형식)

---

## ML Analysis API

머신러닝 기반 분석 기능을 제공합니다.

### 트렌드 예측 (Prediction)

#### GET /dashboard/trends/predict/{keyword}

키워드의 트렌드 예측 데이터를 반환합니다. ETS/ARIMA 모델을 사용합니다.

**경로 파라미터**:

| 파라미터 | 타입 | 설명 |
|---------|------|------|
| `keyword` | string | 예측할 키워드 |

**쿼리 파라미터**:

| 파라미터 | 타입 | 기본값 | 범위 | 설명 |
|---------|------|--------|------|------|
| `days` | int | 7 | 1-14 | 예측 기간(일) |
| `historical_days` | int | 14 | 10-30 | 과거 데이터 기간(일) |
| `confidence` | float | 0.95 | 0.5-0.99 | 신뢰수준 |

**응답**: JSONResponse

```json
{
  "labels": ["2024-01-01", "2024-01-02", "..."],
  "datasets": [
    {"label": "Historical", "data": [10, 12, 15]},
    {"label": "Predicted", "data": [null, null, 18]},
    {"label": "Upper Bound", "data": [null, null, 22]},
    {"label": "Lower Bound", "data": [null, null, 14]}
  ],
  "metadata": {
    "model": "ets",
    "confidence_level": 0.95,
    "forecast_days": 7
  }
}
```

---

#### GET /dashboard/trends/predict-partial/{keyword}

예측 차트 파셜 HTML을 반환합니다.

**경로 파라미터**:

| 파라미터 | 타입 | 설명 |
|---------|------|------|
| `keyword` | string | 예측할 키워드 |

**쿼리 파라미터**:

| 파라미터 | 타입 | 기본값 | 범위 | 설명 |
|---------|------|--------|------|------|
| `days` | int | 7 | 1-14 | 예측 기간(일) |

**응답**: HTMLResponse (partial)

---

### 이상 탐지 (Anomaly Detection)

#### GET /dashboard/trends/anomalies/{keyword}

키워드의 이상 포인트를 탐지하여 반환합니다.

**경로 파라미터**:

| 파라미터 | 타입 | 설명 |
|---------|------|------|
| `keyword` | string | 분석할 키워드 |

**쿼리 파라미터**:

| 파라미터 | 타입 | 기본값 | 범위 | 설명 |
|---------|------|--------|------|------|
| `days` | int | 30 | 7-90 | 분석 기간(일) |
| `method` | string | "auto" | auto, zscore, iqr, isolation_forest | 탐지 방법 |
| `threshold` | float | 3.0 | 1.0-5.0 | 이상 판정 임계값 |

**탐지 방법**:
- `auto`: 데이터 특성에 따라 자동 선택
- `zscore`: Z-Score 기반 (정규분포 가정)
- `iqr`: 사분위수 범위 기반
- `isolation_forest`: Isolation Forest 앙상블 ML

**응답**: JSONResponse (Chart.js 형식)

---

#### GET /dashboard/trends/anomalies-partial/{keyword}

이상 탐지 차트 파셜 HTML을 반환합니다.

**쿼리 파라미터**:

| 파라미터 | 타입 | 기본값 | 범위 | 설명 |
|---------|------|--------|------|------|
| `days` | int | 30 | 7-90 | 분석 기간(일) |

**응답**: HTMLResponse (partial)

---

### 토픽 모델링 (Topic Modeling)

#### GET /dashboard/topics

토픽 분석 메인 페이지를 렌더링합니다.

**응답**: HTMLResponse

---

#### GET /dashboard/topics/analyze

토픽 분석을 실행하고 결과를 JSON으로 반환합니다.

**쿼리 파라미터**:

| 파라미터 | 타입 | 기본값 | 범위 | 설명 |
|---------|------|--------|------|------|
| `n_topics` | int | 5 | 2-10 | 추출할 토픽 수 |
| `method` | string | "auto" | auto, lda, nmf | 토픽 모델링 방법 |

**토픽 모델링 방법**:
- `auto`: 데이터에 따라 자동 선택
- `lda`: Latent Dirichlet Allocation
- `nmf`: Non-negative Matrix Factorization

**응답**: JSONResponse (Chart.js 형식)

---

#### GET /dashboard/topics/distribution

토픽별 문서 분포 데이터를 JSON으로 반환합니다 (파이 차트용).

**쿼리 파라미터**:

| 파라미터 | 타입 | 기본값 | 범위 | 설명 |
|---------|------|--------|------|------|
| `n_topics` | int | 5 | 2-10 | 토픽 수 |

**응답**: JSONResponse

```json
{
  "labels": ["Topic 0: AI", "Topic 1: Web", "..."],
  "data": [25, 30, 20, 15, 10],
  "n_topics": 5,
  "method": "lda"
}
```

---

#### GET /dashboard/topics/keywords-partial

토픽별 키워드 카드를 HTMX partial로 반환합니다.

**쿼리 파라미터**:

| 파라미터 | 타입 | 기본값 | 범위 | 설명 |
|---------|------|--------|------|------|
| `n_topics` | int | 5 | 2-10 | 추출할 토픽 수 |
| `method` | string | "auto" | auto, lda, nmf | 토픽 모델링 방법 |

**응답**: HTMLResponse (partial)

---

#### GET /dashboard/topics/document-count

분석 가능한 문서 수를 반환합니다.

**응답**: JSONResponse

```json
{
  "document_count": 150,
  "has_sufficient_data": true
}
```

---

### 텍스트 클러스터링 (Text Clustering)

#### GET /dashboard/clusters

클러스터링 메인 페이지를 렌더링합니다.

**응답**: HTMLResponse

---

#### GET /dashboard/clusters/analyze

클러스터링 분석을 실행하고 결과를 JSON으로 반환합니다.

**쿼리 파라미터**:

| 파라미터 | 타입 | 기본값 | 범위 | 설명 |
|---------|------|--------|------|------|
| `n_clusters` | int | null | 2-10 | 클러스터 수 (null이면 자동 선택) |
| `method` | string | "auto" | auto, kmeans, agglomerative | 클러스터링 방법 |

**클러스터링 방법**:
- `auto`: 데이터에 따라 자동 선택
- `kmeans`: K-Means 클러스터링
- `agglomerative`: 계층적 클러스터링

**응답**: JSONResponse (Chart.js 형식)

---

#### GET /dashboard/clusters/distribution

클러스터별 크기 분포 데이터를 JSON으로 반환합니다 (바 차트용).

**쿼리 파라미터**:

| 파라미터 | 타입 | 기본값 | 범위 | 설명 |
|---------|------|--------|------|------|
| `n_clusters` | int | null | 2-10 | 클러스터 수 |

**응답**: JSONResponse

```json
{
  "labels": ["Cluster 0: Python", "Cluster 1: JavaScript", "..."],
  "data": [45, 32, 23],
  "percentages": [45.0, 32.0, 23.0],
  "n_clusters": 3,
  "method": "kmeans",
  "silhouette_score": 0.67
}
```

---

#### GET /dashboard/clusters/cluster/{cluster_id}

특정 클러스터의 상세 정보를 표시합니다.

**경로 파라미터**:

| 파라미터 | 타입 | 설명 |
|---------|------|------|
| `cluster_id` | int | 클러스터 ID |

**응답**: HTMLResponse

---

#### GET /dashboard/clusters/cluster/{cluster_id}/documents

특정 클러스터의 문서 목록을 JSON으로 반환합니다.

**경로 파라미터**:

| 파라미터 | 타입 | 설명 |
|---------|------|------|
| `cluster_id` | int | 클러스터 ID |

**쿼리 파라미터**:

| 파라미터 | 타입 | 기본값 | 범위 | 설명 |
|---------|------|--------|------|------|
| `page` | int | 1 | 1+ | 페이지 번호 |
| `page_size` | int | 20 | 5-100 | 페이지당 항목 수 |

**응답**: JSONResponse

```json
{
  "cluster_id": 0,
  "documents": ["doc1", "doc2", "..."],
  "page": 1,
  "page_size": 20,
  "total_count": 45,
  "total_pages": 3,
  "has_next": true,
  "has_prev": false
}
```

---

#### GET /dashboard/clusters/cards-partial

클러스터 카드를 HTMX partial로 반환합니다.

**쿼리 파라미터**:

| 파라미터 | 타입 | 기본값 | 범위 | 설명 |
|---------|------|--------|------|------|
| `n_clusters` | int | null | 2-10 | 클러스터 수 |
| `method` | string | "auto" | auto, kmeans, agglomerative | 클러스터링 방법 |

**응답**: HTMLResponse (partial)

---

#### GET /dashboard/clusters/document-count

분석 가능한 문서 수를 반환합니다.

**응답**: JSONResponse

---

## Demands API

수요 분석 결과를 시각화합니다.

### GET /dashboard/demands

수요 분석 메인 페이지를 렌더링합니다.

**응답**: HTMLResponse

**컨텍스트 데이터**:
- `demands`: 수요 목록
- `category_stats`: 카테고리별 통계
- `categories`: 카테고리 목록
- `recommendations`: 분석 권장사항
- `total_demands`: 총 수요 수

---

### GET /dashboard/demands/list

수요 목록을 HTMX partial로 반환합니다.

**쿼리 파라미터**:

| 파라미터 | 타입 | 기본값 | 범위 | 설명 |
|---------|------|--------|------|------|
| `category` | string | null | - | 카테고리 필터 |
| `min_priority` | float | 0.0 | 0.0-100.0 | 최소 우선순위 |
| `limit` | int | 20 | 1-100 | 최대 반환 수 |

**카테고리 값**:
- `feature_request`: 기능 요청
- `pain_point`: 문제점/불만
- `search_query`: 검색/질문
- `willingness_to_pay`: 구매 의향
- `alternative_seeking`: 대안 탐색

**응답**: HTMLResponse (partial)

---

### GET /dashboard/demands/{demand_id}

수요 상세 페이지를 렌더링합니다.

**경로 파라미터**:

| 파라미터 | 타입 | 설명 |
|---------|------|------|
| `demand_id` | string | 수요 ID |

**응답**: HTMLResponse

**상태 코드**:
- `200`: 성공
- `404`: 수요 없음

---

### GET /dashboard/demands/categories/stats

카테고리별 분포를 JSON으로 반환합니다.

**응답**: JSONResponse

```json
{
  "feature_request": 25,
  "pain_point": 18,
  "search_query": 12,
  "willingness_to_pay": 8,
  "alternative_seeking": 5
}
```

---

## Competition API

경쟁 분석 결과를 시각화합니다.

### GET /dashboard/competition

경쟁 분석 메인 페이지를 렌더링합니다.

**응답**: HTMLResponse

**컨텍스트 데이터**:
- `entities`: 탐지된 엔티티 목록
- `complaints`: 불만 목록
- `sentiment_distribution`: 감성 분포
- `popular_switches`: 인기 제품 전환
- `recommendations`: 분석 권장사항

---

### GET /dashboard/competition/entities

엔티티 목록을 HTMX partial로 반환합니다.

**쿼리 파라미터**:

| 파라미터 | 타입 | 기본값 | 범위 | 설명 |
|---------|------|--------|------|------|
| `limit` | int | 20 | 1-100 | 최대 반환 수 |

**응답**: HTMLResponse (partial)

---

### GET /dashboard/competition/entity/{name}

엔티티 상세 페이지를 렌더링합니다.

**경로 파라미터**:

| 파라미터 | 타입 | 설명 |
|---------|------|------|
| `name` | string | 엔티티 이름 |

**응답**: HTMLResponse

**상태 코드**:
- `200`: 성공
- `404`: 엔티티 없음

---

### GET /dashboard/competition/sentiment-chart

감성 분포 차트 데이터를 JSON으로 반환합니다.

**응답**: JSONResponse (Chart.js 형식)

```json
{
  "labels": ["Positive", "Neutral", "Negative"],
  "datasets": [{
    "data": [40.5, 35.2, 24.3],
    "backgroundColor": ["#22c55e", "#6b7280", "#ef4444"],
    "borderColor": ["#16a34a", "#4b5563", "#dc2626"],
    "borderWidth": 1
  }]
}
```

---

### GET /dashboard/competition/complaints

불만 목록을 HTMX partial로 반환합니다.

**쿼리 파라미터**:

| 파라미터 | 타입 | 기본값 | 범위 | 설명 |
|---------|------|--------|------|------|
| `limit` | int | 10 | 1-50 | 최대 반환 수 |

**응답**: HTMLResponse (partial)

---

### GET /dashboard/competition/switches

인기 제품 전환 데이터를 JSON으로 반환합니다.

**응답**: JSONResponse

```json
[
  {"from": "Product A", "to": "Product B", "count": 15},
  {"from": "Product C", "to": "Product D", "count": 8}
]
```

---

## Insights API

비즈니스 인사이트를 시각화합니다.

### GET /dashboard/insights

인사이트 메인 페이지를 렌더링합니다.

**쿼리 파라미터**:

| 파라미터 | 타입 | 기본값 | 범위 | 설명 |
|---------|------|--------|------|------|
| `insight_type` | string | null | - | 인사이트 유형 필터 |
| `min_confidence` | float | 0.0 | 0.0-1.0 | 최소 신뢰도 |
| `limit` | int | 20 | 1-100 | 표시할 인사이트 수 |

**응답**: HTMLResponse

---

### GET /dashboard/insights/list

인사이트 목록을 HTMX partial로 반환합니다.

**쿼리 파라미터**: `/dashboard/insights`와 동일

**응답**: HTMLResponse (partial)

---

### GET /dashboard/insights/recommendations

추천 목록을 HTMX partial로 반환합니다.

**쿼리 파라미터**:

| 파라미터 | 타입 | 기본값 | 범위 | 설명 |
|---------|------|--------|------|------|
| `top_n` | int | 10 | 1-50 | 표시할 추천 수 |

**응답**: HTMLResponse (partial)

---

### GET /dashboard/insights/opportunities

기회 랭킹을 HTMX partial로 반환합니다.

**쿼리 파라미터**:

| 파라미터 | 타입 | 기본값 | 범위 | 설명 |
|---------|------|--------|------|------|
| `limit` | int | 20 | 1-100 | 표시할 기회 수 |

**응답**: HTMLResponse (partial)

---

### GET /dashboard/insights/{insight_id}

인사이트 상세 페이지를 렌더링합니다.

**경로 파라미터**:

| 파라미터 | 타입 | 설명 |
|---------|------|------|
| `insight_id` | string | 인사이트 ID |

**응답**: HTMLResponse

**상태 코드**:
- `200`: 성공
- `404`: 인사이트 없음

---

### GET /dashboard/insights/chart/score-breakdown/{insight_id}

인사이트 스코어 breakdown 차트 데이터를 JSON으로 반환합니다.

**경로 파라미터**:

| 파라미터 | 타입 | 설명 |
|---------|------|------|
| `insight_id` | string | 인사이트 ID |

**응답**: JSONResponse (Chart.js 레이더 차트 형식)

---

### GET /dashboard/insights/chart/grade-distribution

등급 분포 차트 데이터를 JSON으로 반환합니다.

**응답**: JSONResponse (Chart.js 도넛 차트 형식)

---

## Reports API

비즈니스 보고서를 생성합니다.

### GET /dashboard/insights/report/generate

보고서 생성 페이지를 렌더링합니다.

**응답**: HTMLResponse

---

### GET /dashboard/insights/report/preview

보고서 미리보기를 렌더링합니다.

**쿼리 파라미터**:

| 파라미터 | 타입 | 기본값 | 설명 |
|---------|------|--------|------|
| `subreddit` | string | null | 서브레딧 이름 |

**응답**: HTMLResponse (partial)

---

### GET /dashboard/insights/report/download

마크다운 보고서를 다운로드합니다.

**쿼리 파라미터**:

| 파라미터 | 타입 | 기본값 | 설명 |
|---------|------|--------|------|
| `subreddit` | string | null | 서브레딧 이름 |

**응답**: Response (text/markdown)

**헤더**:
```
Content-Disposition: attachment; filename=business_report_{subreddit}_{timestamp}.md
```

---

### GET /dashboard/insights/report/json

보고서 데이터를 JSON으로 반환합니다.

**쿼리 파라미터**:

| 파라미터 | 타입 | 기본값 | 설명 |
|---------|------|--------|------|
| `subreddit` | string | null | 서브레딧 이름 |

**응답**: JSONResponse

```json
{
  "subreddit": "python",
  "generated_at": "2024-01-15T10:30:00Z",
  "analysis_period": "7 days",
  "total_posts_analyzed": 150,
  "total_keywords": 200,
  "total_insights": 25,
  "executive_summary": "...",
  "market_overview": "...",
  "business_items": [...],
  "trend_analysis": "...",
  "demand_analysis": "...",
  "competition_analysis": "...",
  "recommendations": [...],
  "risk_factors": [...],
  "conclusion": "..."
}
```

---

## Search API

글로벌 검색 기능을 제공합니다.

### GET /search

검색 결과 페이지를 렌더링합니다.

**쿼리 파라미터**:

| 파라미터 | 타입 | 기본값 | 범위 | 설명 |
|---------|------|--------|------|------|
| `q` | string | "" | - | 검색어 |
| `type` | string | null | keywords, entities, insights, demands | 검색 유형 필터 |
| `limit` | int | 20 | 1-100 | 결과 수 |

**응답**: HTMLResponse

---

### GET /search/suggestions

자동완성 제안을 HTMX partial로 반환합니다.

**쿼리 파라미터**:

| 파라미터 | 타입 | 기본값 | 범위 | 설명 |
|---------|------|--------|------|------|
| `q` | string | "" | - | 검색어 (최소 2자) |
| `limit` | int | 5 | 1-10 | 제안 수 |

**응답**: HTMLResponse (partial)

---

### GET /search/results

검색 결과를 HTMX partial로 반환합니다.

**쿼리 파라미터**:

| 파라미터 | 타입 | 기본값 | 범위 | 설명 |
|---------|------|--------|------|------|
| `q` | string | "" | - | 검색어 |
| `type` | string | null | keywords, entities, insights, demands | 검색 유형 필터 |
| `limit` | int | 20 | 1-100 | 결과 수 |

**응답**: HTMLResponse (partial)

---

## API v1 (Protected)

인증이 필요한 RESTful API입니다.

### Public Endpoints

#### GET /api/v1/status

API 상태를 반환합니다.

**응답**: JSONResponse

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "auth_required": true
}
```

---

### Analysis Endpoints (No Auth)

#### POST /api/v1/analyze

새 분석 작업을 시작합니다.

**요청 본문**:

```json
{
  "subreddit": "python",
  "limit": 100
}
```

**응답**: JSONResponse

```json
{
  "job_id": "python_20240115103000",
  "subreddit": "python",
  "status": "pending",
  "message": "r/python 분석이 시작되었습니다."
}
```

---

#### GET /api/v1/analyze/status/{job_id}

분석 작업 상태를 반환합니다.

**경로 파라미터**:

| 파라미터 | 타입 | 설명 |
|---------|------|------|
| `job_id` | string | 작업 ID |

**응답**: JSONResponse

```json
{
  "job_id": "python_20240115103000",
  "subreddit": "python",
  "status": "running",
  "progress": 50,
  "current_step": "데이터 분석 중...",
  "started_at": "2024-01-15T10:30:00Z",
  "completed_at": null,
  "error": null
}
```

**상태 값**:
- `pending`: 대기 중
- `running`: 실행 중
- `completed`: 완료
- `failed`: 실패

---

#### GET /api/v1/analyze/jobs

모든 분석 작업 목록을 반환합니다.

**응답**: JSONResponse

```json
{
  "total": 3,
  "jobs": [
    {"job_id": "...", "status": "completed", ...},
    {"job_id": "...", "status": "running", ...}
  ]
}
```

---

### Protected Endpoints (Auth Required)

다음 엔드포인트는 `X-API-Key` 헤더가 필요합니다.

#### GET /api/v1/subreddits

분석된 서브레딧 목록을 반환합니다.

**응답**: JSONResponse

```json
["python", "javascript", "webdev"]
```

---

#### GET /api/v1/analysis/history

분석 이력을 반환합니다.

**쿼리 파라미터**:

| 파라미터 | 타입 | 기본값 | 설명 |
|---------|------|--------|------|
| `subreddit` | string | null | 서브레딧 필터 |
| `limit` | int | 10 | 최대 반환 수 |

**응답**: JSONResponse

```json
[
  {
    "id": 1,
    "subreddit": "python",
    "analyzed_at": "2024-01-15T10:30:00Z",
    "post_count": 100,
    "keyword_count": 50,
    "insight_count": 15
  }
]
```

---

#### GET /api/v1/analysis/{subreddit}

특정 서브레딧의 최신 분석 데이터를 반환합니다.

**경로 파라미터**:

| 파라미터 | 타입 | 설명 |
|---------|------|------|
| `subreddit` | string | 서브레딧 이름 |

**응답**: JSONResponse

---

#### GET /api/v1/keywords/{subreddit}

서브레딧의 키워드 데이터를 반환합니다.

**경로 파라미터**:

| 파라미터 | 타입 | 설명 |
|---------|------|------|
| `subreddit` | string | 서브레딧 이름 |

**쿼리 파라미터**:

| 파라미터 | 타입 | 기본값 | 설명 |
|---------|------|--------|------|
| `limit` | int | 50 | 최대 키워드 수 |

**응답**: JSONResponse

---

#### GET /api/v1/trends/{subreddit}

서브레딧의 트렌드 데이터를 반환합니다.

**응답**: JSONResponse

---

#### GET /api/v1/insights/{subreddit}

서브레딧의 인사이트 데이터를 반환합니다.

**응답**: JSONResponse

---

### Admin Endpoints (Auth Required)

#### POST /api/v1/admin/api-keys

새로운 API 키를 생성합니다.

**요청 본문**:

```json
{
  "name": "My App",
  "rate_limit": 100
}
```

**응답**: JSONResponse

```json
{
  "id": 1,
  "name": "My App",
  "api_key": "ri_xxxxxxxxxxxx",
  "rate_limit": 100,
  "message": "API key created successfully. Save this key, it won't be shown again."
}
```

---

#### GET /api/v1/admin/api-keys

모든 API 키 목록을 반환합니다.

**응답**: JSONResponse

```json
[
  {
    "id": 1,
    "name": "My App",
    "created_at": "2024-01-15T10:30:00Z",
    "last_used_at": "2024-01-15T12:00:00Z",
    "is_active": true,
    "rate_limit": 100
  }
]
```

---

#### DELETE /api/v1/admin/api-keys/{key_id}

API 키를 삭제합니다.

**경로 파라미터**:

| 파라미터 | 타입 | 설명 |
|---------|------|------|
| `key_id` | int | API 키 ID |

**응답**: JSONResponse

```json
{
  "message": "API key 1 deleted successfully"
}
```

---

#### PUT /api/v1/admin/api-keys/{key_id}/deactivate

API 키를 비활성화합니다.

**응답**: JSONResponse

```json
{
  "message": "API key 1 deactivated successfully"
}
```

---

## 에러 응답

### 공통 에러 형식

```json
{
  "detail": "Error message describing what went wrong"
}
```

### HTTP 상태 코드

| 코드 | 설명 |
|------|------|
| `200` | 성공 |
| `400` | 잘못된 요청 (파라미터 오류) |
| `401` | 인증 필요 |
| `403` | 권한 없음 |
| `404` | 리소스 없음 |
| `422` | 유효성 검사 실패 |
| `429` | 요청 제한 초과 |
| `500` | 서버 내부 오류 |

### 예시

```bash
# 404 응답 예시
curl http://localhost:8000/api/v1/analysis/nonexistent

# 응답
{
  "detail": "No analysis data found for r/nonexistent"
}
```

```bash
# 401 응답 예시
curl http://localhost:8000/api/v1/subreddits

# 응답
{
  "detail": "API key required"
}
```
