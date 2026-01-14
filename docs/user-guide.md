# User Guide

Reddit Insight 사용자 가이드입니다.

## 목차

1. [설치 및 설정](#설치-및-설정)
2. [Reddit API 키 발급](#reddit-api-키-발급)
3. [CLI 사용법](#cli-사용법)
4. [대시보드 사용법](#대시보드-사용법)
5. [ML 분석 기능](#ml-분석-기능)
6. [v2.0 새 기능](#v20-새-기능)
7. [리포트 생성](#리포트-생성)
8. [FAQ 및 트러블슈팅](#faq-및-트러블슈팅)

---

## 설치 및 설정

### 시스템 요구사항

- **Python**: 3.11 이상
- **OS**: macOS, Linux, Windows
- **메모리**: 최소 4GB RAM (ML 분석 시 8GB 권장)
- **디스크**: 1GB 이상 여유 공간

### 설치 방법

#### 1. 저장소 클론

```bash
git clone https://github.com/your-repo/reddit-insight.git
cd reddit-insight
```

#### 2. 가상환경 생성 (권장)

```bash
# venv 사용
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows

# 또는 conda 사용
conda create -n reddit-insight python=3.11
conda activate reddit-insight
```

#### 3. 의존성 설치

```bash
# 기본 설치
pip install -e .

# 개발 환경 설치 (테스트 도구 포함)
pip install -e ".[dev]"
```

### 환경 변수 설정

프로젝트 루트에 `.env` 파일을 생성합니다:

```bash
# .env

# Reddit API 인증 (선택사항 - 없으면 스크래핑 사용)
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USER_AGENT=reddit-insight/1.0.0

# 데이터베이스 경로
DATABASE_URL=sqlite+aiosqlite:///./data/reddit_insight.db

# 대시보드 설정
SECRET_KEY=your-secret-key-here
RATE_LIMIT_PER_MINUTE=100

# 로그 설정
LOG_LEVEL=INFO
```

### 설치 확인

```bash
# 버전 확인
reddit-insight --version

# 상태 확인
reddit-insight status
```

---

## Reddit API 키 발급

Reddit API를 사용하면 더 안정적인 데이터 수집이 가능합니다.

### 1. Reddit 앱 생성

1. https://www.reddit.com/prefs/apps 접속
2. Reddit 계정으로 로그인
3. 페이지 하단 "create another app..." 클릭

### 2. 앱 정보 입력

| 필드 | 입력값 |
|------|--------|
| **name** | `reddit-insight` (원하는 이름) |
| **app type** | `script` 선택 |
| **description** | 간단한 설명 (선택) |
| **about url** | 비워둠 |
| **redirect uri** | `http://localhost:8080` |

### 3. 앱 생성 완료

생성 후 표시되는 정보:
- **client_id**: 앱 이름 아래 "personal use script" 아래 문자열
- **client_secret**: "secret" 옆 문자열

### 4. 환경 변수 설정

```bash
# .env 파일에 추가
REDDIT_CLIENT_ID=abcdefg12345     # client_id 값
REDDIT_CLIENT_SECRET=xyz789abc    # client_secret 값
REDDIT_USER_AGENT=reddit-insight/1.0.0 by /u/your_username
```

### API 없이 사용하기

Reddit API 키가 없어도 사용 가능합니다. 이 경우 자동으로 스크래핑 모드로 전환됩니다:

```bash
# API 키 없이 실행 - 자동으로 스크래핑 사용
reddit-insight collect python -l 50
```

---

## CLI 사용법

Reddit Insight는 `reddit-insight` 명령어로 사용합니다.

### 명령어 목록

```bash
reddit-insight --help
```

| 명령어 | 설명 |
|--------|------|
| `collect` | 단일 서브레딧 데이터 수집 |
| `collect-list` | 파일에서 여러 서브레딧 일괄 수집 |
| `analyze` | 분석 실행 |
| `report` | 리포트 생성 |
| `dashboard` | 대시보드 서버 관리 |
| `status` | 시스템 상태 확인 |
| `api-key` | API 키 관리 |
| `schedule` | 스케줄 작업 관리 |

---

### collect - 데이터 수집

단일 서브레딧에서 게시물을 수집합니다.

```bash
reddit-insight collect <subreddit> [OPTIONS]
```

**옵션**:

| 옵션 | 단축 | 기본값 | 설명 |
|------|------|--------|------|
| `--sort` | `-s` | hot | 정렬 방식 (hot/new/top/rising) |
| `--limit` | `-l` | 100 | 수집할 게시물 수 |
| `--comments` | `-c` | false | 댓글도 함께 수집 |
| `--time-filter` | `-t` | all | top 정렬 시 기간 |

**예시**:

```bash
# 기본 수집 (hot 100개)
reddit-insight collect python

# new 정렬, 200개 수집
reddit-insight collect webdev -s new -l 200

# top 정렬, 이번 주 기준, 댓글 포함
reddit-insight collect programming -s top -t week -c

# 여러 서브레딧 순차 수집
for sub in python javascript rust; do
    reddit-insight collect $sub -l 100
done
```

---

### collect-list - 일괄 수집

파일에서 서브레딧 목록을 읽어 일괄 수집합니다.

```bash
reddit-insight collect-list <file> [OPTIONS]
```

**파일 형식** (`subreddits.txt`):

```
python
javascript
webdev
programming
# 주석은 # 으로 시작
rust
golang
```

**예시**:

```bash
# 파일에서 일괄 수집
reddit-insight collect-list subreddits.txt -l 100
```

---

### analyze - 분석 실행

수집된 데이터를 분석합니다.

```bash
reddit-insight analyze <type> <subreddit> [OPTIONS]
```

**분석 유형**:

| 유형 | 설명 |
|------|------|
| `full` | 전체 분석 (트렌드 + 수요 + 경쟁) |
| `trends` | 트렌드 분석만 |
| `demands` | 수요 분석만 |
| `competition` | 경쟁 분석만 |

**예시**:

```bash
# 전체 분석
reddit-insight analyze full python

# 최근 50개 게시물만 분석
reddit-insight analyze full python -l 50

# 트렌드 분석만
reddit-insight analyze trends python
```

---

### report - 리포트 생성

분석 결과를 마크다운 리포트로 생성합니다.

```bash
reddit-insight report generate <output_dir> [OPTIONS]
```

**옵션**:

| 옵션 | 단축 | 설명 |
|------|------|------|
| `--subreddit` | `-s` | 대상 서브레딧 |
| `--limit` | `-l` | 분석할 게시물 수 |

**예시**:

```bash
# reports/ 디렉토리에 리포트 생성
reddit-insight report generate ./reports -s python

# 특정 서브레딧 리포트
reddit-insight report generate ./reports -s webdev -l 200
```

---

### dashboard - 대시보드 관리

웹 대시보드 서버를 관리합니다.

```bash
reddit-insight dashboard <command> [OPTIONS]
```

**명령어**:

| 명령어 | 설명 |
|--------|------|
| `start` | 대시보드 서버 시작 |

**옵션**:

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `--host` | 127.0.0.1 | 바인드 호스트 |
| `--port` | 8000 | 바인드 포트 |
| `--reload` | false | 개발 모드 (자동 재시작) |

**예시**:

```bash
# 기본 실행
reddit-insight dashboard start

# 다른 포트에서 실행
reddit-insight dashboard start --port 3000

# 외부 접근 허용 (주의: 보안 고려 필요)
reddit-insight dashboard start --host 0.0.0.0

# 개발 모드
reddit-insight dashboard start --reload
```

---

### status - 상태 확인

시스템 상태를 확인합니다.

```bash
reddit-insight status
```

출력 예시:

```
Reddit Insight Status
=====================

Database: ./data/reddit_insight.db
  - Posts: 1,234
  - Comments: 5,678
  - Subreddits: 5

Recent Analyses:
  - r/python: 2024-01-15 10:30:00 (100 posts)
  - r/javascript: 2024-01-15 09:15:00 (150 posts)

API Status: Active (Reddit API connected)
```

---

### 전체 워크플로우 예시

```bash
# 1. 데이터 수집
reddit-insight collect python -l 200 -c

# 2. 분석 실행
reddit-insight analyze full python

# 3. 대시보드에서 결과 확인
reddit-insight dashboard start

# 4. (선택) 리포트 생성
reddit-insight report generate ./reports -s python
```

---

## 대시보드 사용법

대시보드는 분석 결과를 시각적으로 탐색할 수 있는 웹 인터페이스입니다.

### 대시보드 시작

```bash
reddit-insight dashboard start
```

브라우저에서 http://localhost:8000 접속

### 메인 페이지

**URL**: `/dashboard`

- 요약 통계 (서브레딧, 게시물, 댓글 수)
- 최근 분석 기록
- 분석 시작 버튼

### 분석 시작

**URL**: `/dashboard/analyze`

1. 서브레딧 이름 입력 (예: `python`)
2. 게시물 수 설정 (기본 100)
3. "Start Analysis" 클릭
4. 분석 완료 후 결과 페이지로 이동

### 트렌드 뷰

**URL**: `/dashboard/trends`

- **상위 키워드**: 빈도 기준 정렬된 키워드 목록
- **Rising 키워드**: 급상승 중인 키워드
- **타임라인 차트**: 키워드 클릭 시 시계열 차트 표시

**필터 옵션**:
- 서브레딧 선택
- 분석 기간 (1-30일)
- 표시 키워드 수 (1-100개)

### 수요 분석 뷰

**URL**: `/dashboard/demands`

- **카테고리별 분포**: 수요 유형별 파이 차트
- **상위 기회**: 우선순위 순 정렬된 수요 목록
- **상세 보기**: 수요 클릭 시 상세 정보

**수요 카테고리**:
| 카테고리 | 설명 |
|----------|------|
| Feature Request | "~하면 좋겠다" |
| Pain Point | 문제점, 불만 |
| Search Query | 질문, 추천 요청 |
| Willingness to Pay | 구매 의향 |
| Alternative Seeking | 대안 탐색 |

### 경쟁 분석 뷰

**URL**: `/dashboard/competition`

- **엔티티 목록**: 탐지된 제품/서비스
- **감성 분포**: 긍정/중립/부정 비율
- **불만 목록**: 주요 불만 사항
- **제품 전환**: A에서 B로 전환 패턴

### 인사이트 뷰

**URL**: `/dashboard/insights`

- **인사이트 목록**: 생성된 비즈니스 인사이트
- **기회 랭킹**: 점수 기준 정렬
- **추천 사항**: 실행 권고

**인사이트 유형**:
- 미충족 수요 (Unmet Demand)
- 시장 기회 (Market Opportunity)
- 경쟁 약점 (Competitive Gap)
- 트렌드 기회 (Trend Opportunity)
- 구매 의향 (Purchase Intent)

### 검색

**URL**: `/search`

전체 데이터에서 키워드, 엔티티, 인사이트를 검색합니다.

---

## ML 분석 기능

### 트렌드 예측

키워드의 미래 트렌드를 예측합니다.

**URL**: `/dashboard/trends/predict/{keyword}`

```
http://localhost:8000/dashboard/trends/predict/python?days=7
```

**파라미터**:
| 파라미터 | 설명 | 기본값 |
|---------|------|--------|
| days | 예측 기간 | 7일 |
| historical_days | 학습 데이터 기간 | 14일 |
| confidence | 신뢰수준 | 0.95 |

**사용 모델**: ETS (Exponential Smoothing) / ARIMA

**차트 구성**:
- 실선: 과거 데이터
- 점선: 예측값
- 음영: 신뢰구간 (상한/하한)

---

### 이상 탐지

비정상적인 급등/급락 포인트를 탐지합니다.

**URL**: `/dashboard/trends/anomalies/{keyword}`

```
http://localhost:8000/dashboard/trends/anomalies/python?days=30&method=auto
```

**파라미터**:
| 파라미터 | 설명 | 기본값 |
|---------|------|--------|
| days | 분석 기간 | 30일 |
| method | 탐지 방법 | auto |
| threshold | 임계값 | 3.0 |

**탐지 방법**:
| 방법 | 설명 | 적합한 경우 |
|------|------|------------|
| zscore | Z-Score 기반 | 정규분포 데이터 |
| iqr | 사분위수 범위 | 이상치가 많은 데이터 |
| isolation_forest | ML 앙상블 | 복잡한 패턴 |
| auto | 자동 선택 | 일반적인 경우 |

**차트 표시**:
- 정상 포인트: 파란색
- 이상 포인트: 빨간색 마커

---

### 토픽 모델링

문서에서 잠재 토픽을 추출합니다.

**URL**: `/dashboard/topics`

**파라미터**:
| 파라미터 | 설명 | 기본값 |
|---------|------|--------|
| n_topics | 토픽 수 | 5 |
| method | 모델링 방법 | auto |

**모델링 방법**:
| 방법 | 설명 |
|------|------|
| lda | Latent Dirichlet Allocation (확률 모델) |
| nmf | Non-negative Matrix Factorization (행렬 분해) |
| auto | 데이터에 따라 자동 선택 |

**결과 표시**:
- 토픽별 상위 키워드
- 문서-토픽 분포 (파이 차트)
- Coherence Score (품질 지표)

---

### 텍스트 클러스터링

유사한 문서를 자동으로 그룹화합니다.

**URL**: `/dashboard/clusters`

**파라미터**:
| 파라미터 | 설명 | 기본값 |
|---------|------|--------|
| n_clusters | 클러스터 수 | auto |
| method | 클러스터링 방법 | auto |

**클러스터링 방법**:
| 방법 | 설명 |
|------|------|
| kmeans | K-Means (중심점 기반) |
| agglomerative | 계층적 클러스터링 |
| auto | 자동 선택 |

**결과 표시**:
- 클러스터별 크기 (바 차트)
- 클러스터별 대표 키워드
- 클러스터별 대표 문서
- Silhouette Score (품질 지표)

---

## v2.0 새 기능

v2.0에서 추가된 새로운 기능들입니다. 자세한 내용은 [v2.0 Features Guide](./v2-features.md)를 참조하세요.

### LLM 분석 (AI Analysis)

Claude 또는 OpenAI API를 활용한 고급 AI 분석 기능:

- **AI 요약**: 게시물 핵심 내용 자동 요약
- **카테고리화**: 텍스트 자동 분류
- **심층 감성 분석**: 뉘앙스 포함 상세 분석
- **인사이트 생성**: 비즈니스 기회 해석

**접속**: `/dashboard/llm`

**설정**:
```bash
# .env
ANTHROPIC_API_KEY=sk-ant-xxxxx  # Claude API
# 또는
OPENAI_API_KEY=sk-xxxxx         # OpenAI API
```

---

### 멀티 서브레딧 비교

여러 서브레딧을 동시에 비교 분석:

- **크로스 트렌드 비교**: 키워드 트렌드 비교
- **벤치마킹**: 활동량, 감성, 키워드 비교
- **유사도 분석**: 서브레딧 간 토픽 유사도

**접속**: `/dashboard/comparison`

**제한**: 최소 2개, 최대 5개 서브레딧

---

### 실시간 모니터링

SSE 기반 실시간 모니터링:

- **실시간 게시물 스트림**: 새 게시물 즉시 알림
- **활동량 모니터링**: 실시간 추적
- **다중 서브레딧**: 여러 서브레딧 동시 모니터링

**접속**: `/dashboard/live`

---

### 알림 시스템

조건 기반 알림 설정:

- **키워드 급등 알림**: 특정 키워드 급증 시 알림
- **활동량 임계값**: 설정 임계값 초과 시 알림
- **다양한 채널**: 콘솔, Email, Webhook

**접속**: `/dashboard/alerts`

**설정**:
```bash
# .env (Email 알림)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# Webhook 알림
ALERT_WEBHOOK_URL=https://your-server.com/webhook
```

---

### PDF/Excel 내보내기

분석 결과 내보내기:

- **PDF 리포트**: 전문적인 보고서
- **Excel**: 데이터 분석용 파일

**접속**: 각 분석 페이지의 Export 버튼

---

## 리포트 생성

### CLI로 생성

```bash
# 마크다운 리포트 생성
reddit-insight report generate ./reports -s python
```

### 대시보드에서 생성

1. `/dashboard/insights/report/generate` 접속
2. 서브레딧 선택 (선택사항)
3. "Preview" 버튼으로 미리보기
4. "Download" 버튼으로 다운로드

### 리포트 구성

생성되는 리포트는 다음 섹션을 포함합니다:

1. **Executive Summary**: 핵심 요약
2. **Market Overview**: 시장 개요
3. **Business Items Ranking**: 기회 순위
4. **Trend Analysis**: 트렌드 분석
5. **Demand Analysis**: 수요 분석
6. **Competition Analysis**: 경쟁 분석
7. **Recommendations**: 권장 사항
8. **Risk Factors**: 리스크 요인
9. **Conclusion**: 결론

### API로 리포트 데이터 가져오기

```bash
# JSON 형식으로 리포트 데이터 가져오기
curl http://localhost:8000/dashboard/insights/report/json?subreddit=python
```

---

## FAQ 및 트러블슈팅

### 설치 관련

#### Q: pip install 시 의존성 충돌이 발생합니다

```bash
# 가상환경에서 클린 설치
python -m venv .venv --clear
source .venv/bin/activate
pip install -e .
```

#### Q: M1 Mac에서 설치 오류가 발생합니다

```bash
# ARM 네이티브 패키지 설치
pip install --no-cache-dir numpy scipy scikit-learn
pip install -e .
```

---

### 데이터 수집 관련

#### Q: "Rate limit exceeded" 오류가 발생합니다

Reddit API 요청 제한에 도달했습니다. 해결 방법:

1. 잠시 기다린 후 재시도 (보통 10분)
2. `--limit` 값을 줄여서 시도
3. API 키 없이 스크래핑 모드 사용 (자동 전환)

#### Q: 스크래핑이 실패합니다

```bash
# 네트워크 연결 확인
curl https://old.reddit.com/r/python.json

# User-Agent 설정 확인
# .env에 적절한 User-Agent 설정 필요
REDDIT_USER_AGENT=reddit-insight/1.0.0 (by /u/your_username)
```

#### Q: 댓글이 수집되지 않습니다

```bash
# -c 또는 --comments 옵션 사용
reddit-insight collect python -l 100 -c
```

---

### 대시보드 관련

#### Q: 대시보드가 시작되지 않습니다

```bash
# 포트 사용 중 확인
lsof -i :8000

# 다른 포트에서 시작
reddit-insight dashboard start --port 3000

# 로그 확인
LOG_LEVEL=DEBUG reddit-insight dashboard start
```

#### Q: 데이터가 표시되지 않습니다

1. 먼저 데이터 수집 실행:
   ```bash
   reddit-insight collect python -l 100
   ```

2. 분석 실행:
   ```bash
   reddit-insight analyze full python
   ```

3. 대시보드 새로고침

#### Q: 차트가 로드되지 않습니다

- 브라우저 개발자 도구에서 콘솔 오류 확인
- JavaScript가 활성화되어 있는지 확인
- Chart.js CDN 접근 가능 여부 확인

---

### ML 분석 관련

#### Q: 예측 결과가 정확하지 않습니다

- 충분한 과거 데이터 필요 (최소 10일 이상)
- `historical_days` 파라미터 증가:
  ```
  /dashboard/trends/predict/python?historical_days=30
  ```

#### Q: 토픽/클러스터링이 실행되지 않습니다

- 최소 2개 이상의 문서 필요
- 문서 수 확인:
  ```
  GET /dashboard/topics/document-count
  GET /dashboard/clusters/document-count
  ```

#### Q: "Out of memory" 오류

- 분석할 데이터 양 줄이기:
  ```bash
  reddit-insight analyze full python -l 50
  ```
- ML 파라미터 축소:
  ```
  ?n_topics=3&n_clusters=3
  ```

---

### 데이터베이스 관련

#### Q: 데이터베이스 파일 위치는 어디인가요?

기본값: `./data/reddit_insight.db`

환경 변수로 변경 가능:
```bash
DATABASE_URL=sqlite+aiosqlite:///./custom/path.db
```

#### Q: 데이터베이스를 초기화하고 싶습니다

```bash
# 데이터베이스 파일 삭제
rm ./data/reddit_insight.db

# 다음 실행 시 자동 생성됨
```

#### Q: 데이터를 백업하고 싶습니다

```bash
# SQLite 파일 복사
cp ./data/reddit_insight.db ./backup/reddit_insight_backup.db
```

---

### 성능 관련

#### Q: 분석이 너무 느립니다

1. 분석할 데이터 양 줄이기:
   ```bash
   reddit-insight analyze full python -l 50
   ```

2. 특정 분석만 실행:
   ```bash
   reddit-insight analyze trends python  # 트렌드만
   ```

3. 캐시 활용 (대시보드에서 동일 데이터 재사용)

#### Q: 메모리 사용량이 높습니다

- 동시 분석 작업 수 제한
- 분석 후 명시적 데이터 해제
- 배치 크기 조절

---

### API 인증 관련

#### Q: API 키를 생성하고 싶습니다

```bash
# CLI로 생성
reddit-insight api-key create --name "My App" --rate-limit 100
```

#### Q: API 키가 작동하지 않습니다

1. 키가 활성화되어 있는지 확인
2. 올바른 헤더 사용:
   ```bash
   curl -H "X-API-Key: your-key" http://localhost:8000/api/v1/subreddits
   ```

---

### 기타

#### Q: 로그를 더 자세히 보고 싶습니다

```bash
# 디버그 로그 활성화
LOG_LEVEL=DEBUG reddit-insight dashboard start
```

#### Q: 특정 버전 의존성 문제

```bash
# 의존성 버전 확인
pip list | grep -E "(fastapi|sqlalchemy|statsmodels)"

# 특정 버전 설치
pip install "fastapi==0.109.0"
```

---

## 지원

- **문서**: https://github.com/your-repo/reddit-insight/docs
- **이슈**: https://github.com/your-repo/reddit-insight/issues
- **API 문서**: http://localhost:8000/api/docs (서버 실행 시)

---

*최종 업데이트: 2026-01-14*
