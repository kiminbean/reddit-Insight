# Dashboard Guide

Reddit Insight 웹 대시보드 사용 가이드입니다.

## 목차

1. [대시보드 시작](#대시보드-시작)
2. [메인 대시보드](#메인-대시보드)
3. [트렌드 뷰](#트렌드-뷰)
4. [ML 분석 기능](#ml-분석-기능)
   - [트렌드 예측](#트렌드-예측)
   - [이상 탐지](#이상-탐지)
   - [토픽 모델링](#토픽-모델링)
   - [텍스트 클러스터링](#텍스트-클러스터링)
5. [수요 분석 뷰](#수요-분석-뷰)
6. [경쟁 분석 뷰](#경쟁-분석-뷰)
7. [인사이트 뷰](#인사이트-뷰)
8. [보고서 생성](#보고서-생성)
9. [검색 기능](#검색-기능)
10. [API 엔드포인트](#api-엔드포인트)

---

## 대시보드 시작

### 서버 실행

```bash
# 기본 실행
reddit-insight dashboard start

# 포트 변경
reddit-insight dashboard start --port 3000

# 외부 접근 허용
reddit-insight dashboard start --host 0.0.0.0

# 개발 모드 (자동 재시작)
reddit-insight dashboard start --reload
```

### 접속 URL

서버 실행 후 브라우저에서 접속:

- **대시보드**: http://localhost:8000
- **API 문서 (Swagger)**: http://localhost:8000/api/docs
- **API 문서 (ReDoc)**: http://localhost:8000/api/redoc
- **헬스체크**: http://localhost:8000/health

---

## 메인 대시보드

### 접속 경로

```
http://localhost:8000/dashboard
```

### 구성 요소

메인 대시보드는 다음 섹션으로 구성됩니다:

1. **요약 통계**
   - 총 서브레딧 수
   - 총 게시물 수
   - 총 댓글 수

2. **서브레딧별 현황**
   - 서브레딧 목록
   - 게시물 수
   - 최근 업데이트 시간

3. **빠른 링크**
   - 트렌드 분석
   - 수요 분석
   - 경쟁 분석
   - 인사이트

### 데이터 새로고침

대시보드 데이터는 페이지 로드 시 자동으로 최신 데이터를 가져옵니다.
HTMX를 사용하여 부분 새로고침이 가능합니다.

---

## 트렌드 뷰

### 접속 경로

```
http://localhost:8000/trends
```

### 기능

1. **서브레딧 선택**
   - 분석할 서브레딧 선택
   - 필터 적용

2. **키워드 순위**
   - 상위 키워드 목록
   - 점수 표시
   - 시각화 차트

3. **트렌드 분석**
   - 상승 키워드
   - 하락 키워드
   - 변화율 표시

### 필터 옵션

| 필터 | 설명 |
|------|------|
| 서브레딧 | 특정 서브레딧 선택 |
| 기간 | 분석 기간 (7일, 30일, 90일) |
| 키워드 수 | 표시할 키워드 수 |

### API 엔드포인트

```
GET /api/trends?subreddit={name}&limit={n}
```

---

## ML 분석 기능

Reddit Insight는 다양한 ML 기반 분석 기능을 제공합니다.

### 트렌드 예측

키워드의 미래 트렌드를 예측하는 기능입니다.

#### 접속 경로

```
http://localhost:8000/dashboard/trends/predict/{keyword}
```

#### 기능

1. **시계열 예측**
   - ETS/ARIMA 모델 기반 예측
   - 1-14일 예측 기간 설정 가능
   - 신뢰 구간 표시

2. **파라미터**

| 파라미터 | 설명 | 기본값 | 범위 |
|---------|------|--------|------|
| `days` | 예측 기간(일) | 7 | 1-14 |
| `historical_days` | 과거 데이터 기간 | 14 | 10-30 |
| `confidence` | 신뢰수준 | 0.95 | 0.5-0.99 |

#### API 예시

```bash
# 기본 예측
curl "http://localhost:8000/dashboard/trends/predict/python"

# 커스텀 파라미터
curl "http://localhost:8000/dashboard/trends/predict/python?days=10&confidence=0.9"
```

#### 응답 형식

```json
{
  "labels": ["2024-01-01", "2024-01-02", ...],
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

### 이상 탐지

키워드 트렌드에서 비정상적인 급등/급락을 탐지합니다.

#### 접속 경로

```
http://localhost:8000/dashboard/trends/anomalies/{keyword}
```

#### 기능

1. **탐지 방법**
   - Z-Score: 정규분포 기반 이상치 탐지
   - IQR: 사분위수 범위 기반
   - Isolation Forest: 앙상블 기반 ML 탐지
   - Auto: 데이터 특성에 따라 자동 선택

2. **파라미터**

| 파라미터 | 설명 | 기본값 | 범위 |
|---------|------|--------|------|
| `days` | 분석 기간(일) | 30 | 7-90 |
| `method` | 탐지 방법 | auto | auto/zscore/iqr/isolation_forest |
| `threshold` | 이상 판정 임계값 | 3.0 | 1.0-5.0 |

#### API 예시

```bash
# 기본 이상 탐지
curl "http://localhost:8000/dashboard/trends/anomalies/python"

# Z-Score 방법 사용
curl "http://localhost:8000/dashboard/trends/anomalies/python?method=zscore&threshold=2.5"
```

---

### 토픽 모델링

수집된 문서에서 잠재 토픽을 추출합니다.

#### 접속 경로

```
http://localhost:8000/dashboard/topics
```

#### 기능

1. **토픽 추출**
   - LDA (Latent Dirichlet Allocation)
   - NMF (Non-negative Matrix Factorization)
   - 자동 방법 선택

2. **시각화**
   - 토픽별 키워드 분포
   - 문서-토픽 분포
   - Coherence Score

3. **파라미터**

| 파라미터 | 설명 | 기본값 | 범위 |
|---------|------|--------|------|
| `n_topics` | 토픽 수 | 5 | 2-10 |
| `method` | 모델링 방법 | auto | auto/lda/nmf |

#### API 예시

```bash
# 토픽 분석 실행
curl "http://localhost:8000/dashboard/topics/analyze?n_topics=5"

# 토픽 분포 조회
curl "http://localhost:8000/dashboard/topics/distribution"
```

---

### 텍스트 클러스터링

유사한 문서를 자동으로 그룹화합니다.

#### 접속 경로

```
http://localhost:8000/dashboard/clusters
```

#### 기능

1. **클러스터링 방법**
   - K-Means: 중심점 기반 클러스터링
   - Agglomerative: 계층적 클러스터링
   - 자동 클러스터 수 결정

2. **클러스터 분석**
   - 클러스터별 키워드
   - 대표 문서
   - Silhouette Score

3. **파라미터**

| 파라미터 | 설명 | 기본값 | 범위 |
|---------|------|--------|------|
| `n_clusters` | 클러스터 수 | auto | 2-10 (또는 null) |
| `method` | 클러스터링 방법 | auto | auto/kmeans/agglomerative |

#### API 예시

```bash
# 클러스터링 실행
curl "http://localhost:8000/dashboard/clusters/analyze?n_clusters=5"

# 클러스터 상세 조회
curl "http://localhost:8000/dashboard/clusters/cluster/0"

# 클러스터 문서 목록 (페이지네이션)
curl "http://localhost:8000/dashboard/clusters/cluster/0/documents?page=1&page_size=20"
```

---

## 수요 분석 뷰

### 접속 경로

```
http://localhost:8000/demands
```

### 기능

1. **수요 개요**
   - 총 수요 신호 수
   - 클러스터 수
   - 카테고리별 분포

2. **카테고리별 분석**
   - 기능 요청
   - 문제 해결
   - 도구 추천
   - 가격/가치

3. **상위 기회**
   - 우선순위 순 정렬
   - 상세 설명
   - 대표 텍스트

### 필터 옵션

| 필터 | 설명 |
|------|------|
| 서브레딧 | 특정 서브레딧 선택 |
| 카테고리 | 특정 카테고리 필터 |
| 우선순위 | 최소 우선순위 점수 |

### API 엔드포인트

```
GET /api/demands?subreddit={name}&category={cat}
```

---

## 경쟁 분석 뷰

### 접속 경로

```
http://localhost:8000/competition
```

### 기능

1. **엔티티 목록**
   - 탐지된 제품/서비스
   - 언급 횟수
   - 감성 점수

2. **감성 분석**
   - 긍정/부정/중립 비율
   - 시간별 추이

3. **불만 분석**
   - 불만 유형별 분류
   - 심각도 표시
   - 대표 문맥

4. **대체 패턴**
   - A에서 B로 전환 패턴
   - 빈도 표시

### 필터 옵션

| 필터 | 설명 |
|------|------|
| 서브레딧 | 특정 서브레딧 선택 |
| 감성 | 특정 감성 필터 (긍정/부정/중립) |
| 엔티티 타입 | 제품/서비스/브랜드 |

### API 엔드포인트

```
GET /api/competition?subreddit={name}&sentiment={type}
```

---

## 인사이트 뷰

### 접속 경로

```
http://localhost:8000/insights
```

### 기능

1. **인사이트 목록**
   - 순위별 정렬
   - 제목 및 설명
   - 신뢰도 점수

2. **비즈니스 스코어**
   - 종합 점수
   - 등급 (A~F)
   - 세부 요소

3. **실현 가능성**
   - 리스크 레벨
   - 요소별 점수
   - 권장 사항

4. **실행 항목**
   - 단계별 행동 지침
   - 우선순위
   - 예상 영향

### 필터 옵션

| 필터 | 설명 |
|------|------|
| 서브레딧 | 특정 서브레딧 선택 |
| 최소 점수 | 최소 비즈니스 점수 |
| 등급 | 특정 등급 필터 |

### API 엔드포인트

```
GET /api/insights?subreddit={name}&min_score={n}
```

---

## 보고서 생성

분석 결과를 종합한 비즈니스 보고서를 생성합니다.

### 접속 경로

```
http://localhost:8000/dashboard/insights/report/generate
```

### 기능

1. **보고서 미리보기**
   - 실시간 보고서 프리뷰
   - 섹션별 내용 확인

2. **다운로드 형식**
   - Markdown (.md)
   - JSON (API)

3. **보고서 구성**
   - Executive Summary
   - 시장 개요
   - 비즈니스 아이템 랭킹
   - 트렌드 분석
   - 수요 분석
   - 경쟁 분석
   - 권장 사항
   - 리스크 요인

### API 엔드포인트

| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/dashboard/insights/report/generate` | GET | 보고서 생성 페이지 |
| `/dashboard/insights/report/preview` | GET | 보고서 미리보기 |
| `/dashboard/insights/report/download` | GET | 마크다운 다운로드 |
| `/dashboard/insights/report/json` | GET | JSON 형식 보고서 |

### 예시

```bash
# 보고서 미리보기
curl "http://localhost:8000/dashboard/insights/report/preview?subreddit=python"

# 마크다운 다운로드
curl -O "http://localhost:8000/dashboard/insights/report/download?subreddit=python"

# JSON 보고서
curl "http://localhost:8000/dashboard/insights/report/json"
```

---

## 검색 기능

### 접속 경로

```
http://localhost:8000/search
```

### 기능

1. **통합 검색**
   - 게시물 제목 검색
   - 본문 내용 검색
   - 댓글 검색

2. **검색 결과**
   - 관련도 순 정렬
   - 하이라이트 표시
   - 페이지네이션

### 검색 옵션

| 옵션 | 설명 |
|------|------|
| 쿼리 | 검색어 |
| 서브레딧 | 검색 범위 제한 |
| 타입 | 게시물/댓글 |
| 기간 | 날짜 범위 |

### API 엔드포인트

```
GET /api/search?q={query}&subreddit={name}&type={type}
```

---

## API 엔드포인트

### 대시보드 API

| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/dashboard` | GET | 메인 대시보드 페이지 |
| `/health` | GET | 헬스체크 |

### 트렌드 API

| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/trends` | GET | 트렌드 페이지 |
| `/api/trends` | GET | 트렌드 데이터 API |

### 수요 분석 API

| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/demands` | GET | 수요 분석 페이지 |
| `/api/demands` | GET | 수요 데이터 API |

### 경쟁 분석 API

| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/competition` | GET | 경쟁 분석 페이지 |
| `/api/competition` | GET | 경쟁 데이터 API |

### 인사이트 API

| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/insights` | GET | 인사이트 페이지 |
| `/api/insights` | GET | 인사이트 데이터 API |

### 검색 API

| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/search` | GET | 검색 페이지 |
| `/api/search` | GET | 검색 API |

---

## API 문서

### Swagger UI

Swagger UI에서 모든 API 엔드포인트를 테스트할 수 있습니다:

```
http://localhost:8000/api/docs
```

### ReDoc

더 상세한 API 문서는 ReDoc에서 확인할 수 있습니다:

```
http://localhost:8000/api/redoc
```

---

## 커스터마이징

### 테마 변경

대시보드는 CSS 변수를 통해 테마를 커스터마이징할 수 있습니다.

```css
/* 커스텀 테마 예시 */
:root {
    --primary-color: #3b82f6;
    --secondary-color: #10b981;
    --background-color: #f3f4f6;
    --text-color: #1f2937;
}
```

### 위젯 추가

HTMX를 사용하여 동적 위젯을 추가할 수 있습니다.

```html
<!-- 커스텀 위젯 예시 -->
<div hx-get="/api/custom-widget"
     hx-trigger="load"
     hx-swap="innerHTML">
    Loading...
</div>
```

---

## 문제 해결

### 서버가 시작되지 않음

1. 포트가 이미 사용 중인지 확인:
   ```bash
   lsof -i :8000
   ```

2. 다른 포트로 시작:
   ```bash
   reddit-insight dashboard start --port 3000
   ```

### 데이터가 표시되지 않음

1. 데이터베이스에 데이터가 있는지 확인:
   ```bash
   reddit-insight status
   ```

2. 데이터 수집 실행:
   ```bash
   reddit-insight collect python -l 100
   ```

### 페이지 로딩이 느림

1. 분석할 데이터 양 줄이기
2. 캐싱 확인
3. 데이터베이스 인덱스 확인

---

## 프로그래매틱 접근

Python에서 대시보드 앱을 직접 사용할 수 있습니다:

```python
from reddit_insight.dashboard.app import app, create_app

# FastAPI 앱 인스턴스
fastapi_app = create_app()

# Uvicorn으로 실행
import uvicorn
uvicorn.run(fastapi_app, host="0.0.0.0", port=8000)
```

### 테스트 클라이언트

```python
from fastapi.testclient import TestClient
from reddit_insight.dashboard.app import app

client = TestClient(app)

# 헬스체크
response = client.get("/health")
assert response.status_code == 200

# 트렌드 API
response = client.get("/api/trends?subreddit=python")
data = response.json()
```
