# Dashboard Guide

Reddit Insight 웹 대시보드 사용 가이드입니다.

## 목차

1. [대시보드 시작](#대시보드-시작)
2. [메인 대시보드](#메인-대시보드)
3. [트렌드 뷰](#트렌드-뷰)
4. [수요 분석 뷰](#수요-분석-뷰)
5. [경쟁 분석 뷰](#경쟁-분석-뷰)
6. [인사이트 뷰](#인사이트-뷰)
7. [검색 기능](#검색-기능)
8. [API 엔드포인트](#api-엔드포인트)

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
