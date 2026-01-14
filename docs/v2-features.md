# Reddit Insight v2.0 Features Guide

Reddit Insight v2.0에서 추가된 새로운 기능들에 대한 가이드입니다.

## 목차

1. [LLM 분석 (AI Analysis)](#llm-분석-ai-analysis)
2. [멀티 서브레딧 비교](#멀티-서브레딧-비교)
3. [실시간 모니터링](#실시간-모니터링)
4. [알림 시스템](#알림-시스템)
5. [PDF/Excel 내보내기](#pdfexcel-내보내기)
6. [캐싱 및 성능 개선](#캐싱-및-성능-개선)
7. [환경 설정](#환경-설정)

---

## LLM 분석 (AI Analysis)

### 개요

Claude 또는 OpenAI API를 활용하여 게시물에 대한 고급 AI 분석을 제공합니다.

### 기능

- **AI 요약**: 서브레딧 게시물들의 핵심 내용을 자동 요약
- **카테고리화**: 텍스트를 자동으로 분류 (Feature Request, Bug Report, Question 등)
- **심층 감성 분석**: 뉘앙스를 포함한 상세 감성 분석
- **인사이트 생성**: 비즈니스 기회 및 트렌드 해석

### 대시보드 사용법

1. 대시보드 메뉴에서 **AI Analysis** 선택
2. 분석하고자 하는 텍스트 입력 또는 서브레딧 선택
3. 원하는 분석 유형 선택:
   - **Summarize**: AI 요약 생성
   - **Categorize**: 텍스트 카테고리 분류
   - **Sentiment**: 심층 감성 분석
   - **Insights**: 비즈니스 인사이트 도출

### API 엔드포인트

```bash
# LLM 상태 확인
GET /dashboard/llm/status

# 텍스트 카테고리화
POST /dashboard/llm/categorize
Content-Type: application/x-www-form-urlencoded
text=분석할+텍스트

# 감성 분석
POST /dashboard/llm/sentiment
Content-Type: application/x-www-form-urlencoded
text=분석할+텍스트

# AI 요약 (서브레딧 기반)
GET /dashboard/llm/summary?subreddit=python

# AI 인사이트 (서브레딧 기반)
GET /dashboard/llm/insights?subreddit=python
```

### 환경 설정

```bash
# .env 파일에 추가

# Claude API (권장)
ANTHROPIC_API_KEY=sk-ant-xxxxx

# 또는 OpenAI API
OPENAI_API_KEY=sk-xxxxx

# LLM 설정
LLM_PROVIDER=claude  # 또는 openai
LLM_MODEL=claude-3-sonnet-20240229
LLM_MAX_TOKENS=4096
LLM_TEMPERATURE=0.7
```

---

## 멀티 서브레딧 비교

### 개요

여러 서브레딧을 동시에 비교 분석하여 트렌드와 특성을 벤치마킹합니다.

### 기능

- **크로스 서브레딧 트렌드 비교**: 여러 서브레딧의 키워드 트렌드 비교
- **벤치마킹**: 활동량, 감성, 키워드 분포 비교
- **유사도 분석**: 서브레딧 간 토픽 유사도 측정
- **차트 시각화**: 비교 결과를 다양한 차트로 시각화

### 대시보드 사용법

1. 대시보드 메뉴에서 **Comparison** 선택
2. 비교할 서브레딧 선택 (2~5개)
3. **Analyze** 버튼 클릭
4. 결과 확인:
   - 키워드 비교 차트
   - 활동량 비교
   - 감성 분포 비교
   - 유사도 매트릭스

### API 엔드포인트

```bash
# 비교 가능한 서브레딧 목록
GET /dashboard/comparison/available

# 비교 분석 실행
POST /dashboard/comparison/analyze
Content-Type: application/x-www-form-urlencoded
subreddits=python&subreddits=javascript

# 비교 분석 결과 (JSON)
GET /dashboard/comparison/analyze/json?subreddits=python&subreddits=javascript

# 차트 데이터
GET /dashboard/comparison/chart-data?subreddits=python&subreddits=javascript
```

### 제한사항

- 최소 2개, 최대 5개 서브레딧 동시 비교 가능
- 분석 데이터가 있는 서브레딧만 비교 가능

---

## 실시간 모니터링

### 개요

Server-Sent Events(SSE)를 활용하여 서브레딧의 새 게시물과 활동을 실시간으로 모니터링합니다.

### 기능

- **실시간 게시물 스트림**: 새 게시물 즉시 알림
- **활동량 모니터링**: 활동량 변화 실시간 추적
- **다중 서브레딧 모니터링**: 여러 서브레딧 동시 모니터링
- **커스텀 인터벌**: 폴링 간격 설정 가능

### 대시보드 사용법

1. 대시보드 메뉴에서 **Live** 선택
2. 모니터링할 서브레딧 입력
3. **Start Monitoring** 클릭
4. 실시간 업데이트 확인
5. **Stop** 버튼으로 모니터링 중지

### API 엔드포인트

```bash
# SSE 스트림 연결
GET /dashboard/live/stream/{subreddit}
# Response: Server-Sent Events 스트림

# 모니터링 시작
POST /dashboard/live/start/{subreddit}?interval=60

# 모니터링 중지
POST /dashboard/live/stop/{subreddit}

# 전체 모니터 상태
GET /dashboard/live/status

# 특정 서브레딧 모니터 상태
GET /dashboard/live/status/{subreddit}
```

### 클라이언트 연결 예시 (JavaScript)

```javascript
const eventSource = new EventSource('/dashboard/live/stream/python');

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);

  if (data.type === 'connected') {
    console.log('Connected:', data.message);
  } else if (data.type === 'new_post') {
    console.log('New post:', data.post);
  } else if (data.type === 'heartbeat') {
    console.log('Heartbeat received');
  }
};

eventSource.onerror = () => {
  console.log('Connection lost, reconnecting...');
};
```

### 파라미터

- `interval`: 폴링 간격 (초), 기본값: 30, 범위: 10-300

---

## 알림 시스템

### 개요

조건 기반 알림을 설정하여 중요한 변화를 놓치지 않도록 합니다.

### 기능

- **키워드 급등 알림**: 특정 키워드 언급량 급증 시 알림
- **활동량 임계값 알림**: 활동량이 설정 임계값 초과 시 알림
- **감성 변화 알림**: 감성 분포 급격한 변화 시 알림
- **다양한 알림 채널**: 콘솔, Email, Webhook 지원

### 대시보드 사용법

1. 대시보드 메뉴에서 **Alerts** 선택
2. **New Rule** 버튼 클릭
3. 규칙 설정:
   - 이름
   - 알림 유형 (keyword_surge, activity_spike 등)
   - 대상 서브레딧
   - 임계값
   - 알림 채널
4. **Save** 클릭
5. **History** 탭에서 발생한 알림 확인

### API 엔드포인트

```bash
# 규칙 목록 조회
GET /dashboard/alerts/rules

# 규칙 생성
POST /dashboard/alerts/rules
Content-Type: application/x-www-form-urlencoded
name=My+Rule&alert_type=keyword_surge&subreddit=python&threshold=50

# 규칙 상세 조회
GET /dashboard/alerts/rules/{rule_id}

# 규칙 활성화/비활성화 토글
POST /dashboard/alerts/rules/{rule_id}/toggle

# 규칙 삭제
DELETE /dashboard/alerts/rules/{rule_id}

# 알림 이력 조회
GET /dashboard/alerts/history?limit=50

# 알림 통계
GET /dashboard/alerts/stats

# 테스트 알림 전송
POST /dashboard/alerts/test
Content-Type: application/x-www-form-urlencoded
notifier=email
```

### 알림 유형

| 유형 | 설명 |
|------|------|
| `keyword_surge` | 키워드 언급량 급증 |
| `activity_spike` | 전체 활동량 급증 |
| `sentiment_shift` | 감성 분포 변화 |
| `new_competitor` | 새 경쟁자 언급 |

### 알림 채널 설정

#### Email

```bash
# .env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=alerts@yourdomain.com
ALERT_EMAIL_TO=team@yourdomain.com
```

#### Webhook

```bash
# .env
ALERT_WEBHOOK_URL=https://your-server.com/webhook
ALERT_WEBHOOK_SECRET=your-secret-key
```

---

## PDF/Excel 내보내기

### 개요

분석 결과를 PDF 또는 Excel 형식으로 내보내 공유할 수 있습니다.

### 기능

- **PDF 리포트**: 전문적인 PDF 보고서 생성
- **Excel 내보내기**: 데이터 분석용 Excel 파일 생성
- **커스텀 템플릿**: 리포트 템플릿 커스터마이징 가능

### 대시보드 사용법

1. 각 분석 페이지에서 **Export** 버튼 클릭
2. 형식 선택 (PDF / Excel)
3. 옵션 설정 (포함할 섹션 선택)
4. **Download** 클릭

### API 엔드포인트

```bash
# PDF 리포트 생성
GET /dashboard/insights/report/download?format=pdf

# Excel 내보내기
GET /dashboard/insights/report/download?format=excel
```

---

## 캐싱 및 성능 개선

### 개요

v2.0에서는 인메모리 캐싱과 페이지네이션을 도입하여 성능이 크게 개선되었습니다.

### 캐싱

- **자동 캐싱**: 자주 요청되는 데이터 자동 캐싱
- **TTL 기반 만료**: 설정 가능한 캐시 만료 시간
- **캐시 무효화**: 데이터 변경 시 자동 캐시 무효화

### 페이지네이션

- 대용량 데이터 목록에 페이지네이션 적용
- 페이지당 항목 수 설정 가능

### 설정

```bash
# .env
CACHE_TTL_SECONDS=300  # 캐시 만료 시간 (초)
DEFAULT_PAGE_SIZE=20   # 기본 페이지 크기
MAX_PAGE_SIZE=100      # 최대 페이지 크기
```

---

## 환경 설정

### v2.0 전체 환경 변수

```bash
# .env 예시

# === 기본 설정 ===
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite+aiosqlite:///./data/reddit_insight.db
LOG_LEVEL=INFO

# === Reddit API ===
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USER_AGENT=reddit-insight/2.0.0

# === LLM API ===
ANTHROPIC_API_KEY=sk-ant-xxxxx
# 또는
OPENAI_API_KEY=sk-xxxxx
LLM_PROVIDER=claude
LLM_MODEL=claude-3-sonnet-20240229
LLM_MAX_TOKENS=4096
LLM_TEMPERATURE=0.7

# === 알림 설정 ===
# Email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
ALERT_EMAIL_TO=team@yourdomain.com

# Webhook
ALERT_WEBHOOK_URL=https://your-server.com/webhook
ALERT_WEBHOOK_SECRET=your-secret-key

# === 성능 설정 ===
CACHE_TTL_SECONDS=300
DEFAULT_PAGE_SIZE=20
RATE_LIMIT_PER_MINUTE=100
```

### 서버 시작

```bash
# 개발 모드
PYTHONPATH=src uvicorn reddit_insight.dashboard.app:app --reload --port 8888

# 프로덕션 모드
PYTHONPATH=src uvicorn reddit_insight.dashboard.app:app --host 0.0.0.0 --port 8888 --workers 4
```

---

## 버전 정보

- **버전**: 2.0.0
- **릴리스 날짜**: 2025-01
- **호환성**: Python 3.11+

## 변경 이력

### v2.0.0 (2025-01)
- LLM 분석 기능 추가 (Claude/OpenAI 지원)
- 멀티 서브레딧 비교 기능 추가
- 실시간 모니터링 (SSE) 기능 추가
- 알림 시스템 (Email/Webhook) 추가
- PDF/Excel 내보내기 기능 추가
- 캐싱 시스템 도입으로 성능 개선
- 페이지네이션 지원
