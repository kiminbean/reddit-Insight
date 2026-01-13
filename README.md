# Reddit Insight

Reddit 데이터 수집 및 분석 도구 - 키워드 기반 게시물 수집, 트렌드 분석, 수요 발견, 경쟁 분석, 비즈니스 인사이트 추출

## 개요

Reddit Insight는 Reddit 커뮤니티의 데이터를 수집하고 분석하여 비즈니스 인사이트를 추출하는 종합 분석 도구입니다. 트렌드 분석, 수요 패턴 발견, 경쟁사 분석을 통해 실행 가능한 비즈니스 기회를 식별합니다.

## 주요 기능

### 데이터 수집
- Reddit API를 통한 서브레딧 게시물 및 댓글 수집
- 스크래핑 기반 백업 데이터 소스
- SQLite 기반 로컬 데이터 저장

### 트렌드 분석
- 키워드 추출 및 빈도 분석 (TF-IDF, YAKE)
- 시계열 기반 트렌드 추적
- 상승/하락 키워드 탐지

### 수요 분석
- 사용자 요구사항 패턴 탐지
- 수요 신호 클러스터링
- 우선순위 기반 기회 평가

### 경쟁 분석
- 제품/서비스 언급 탐지
- 감성 분석 (긍정/부정/중립)
- 불만 사항 및 대안 패턴 분석

### 비즈니스 인사이트
- 룰 기반 인사이트 생성
- 비즈니스 스코어 및 실현 가능성 평가
- 실행 권고사항 생성

### ML 분석 기능
- 트렌드 예측 (ETS/ARIMA 시계열 모델)
- 이상 탐지 (Z-Score, IQR, Isolation Forest)
- 토픽 모델링 (LDA, NMF)
- 텍스트 클러스터링 (K-Means, Agglomerative)

### 시각화
- 웹 대시보드 (FastAPI + HTMX)
- ML 분석 결과 인터랙티브 차트
- 마크다운 리포트 생성
- CLI 기반 분석 결과 출력

## 설치

### 요구 사항

- Python 3.11 이상
- pip

### 설치 방법

```bash
# 기본 설치
pip install -e .

# 개발 환경 설치
pip install -e ".[dev]"
```

### 환경 변수 설정

Reddit API를 사용하려면 `.env` 파일을 생성하거나 환경 변수를 설정하세요:

```bash
# Reddit API 인증 (선택사항 - 없으면 스크래핑 사용)
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USER_AGENT=reddit-insight/0.1.0

# 데이터베이스 경로 (기본값: ./data/reddit_insight.db)
DATABASE_URL=sqlite+aiosqlite:///./data/reddit_insight.db
```

Reddit API 키 발급: https://www.reddit.com/prefs/apps

## 빠른 시작

### 1. 데이터 수집

```bash
# 단일 서브레딧 수집
reddit-insight collect python -l 100

# 여러 서브레딧 수집
reddit-insight collect-list subreddits.txt

# 댓글도 함께 수집
reddit-insight collect python -l 100 --comments
```

### 2. 분석 실행

```bash
# 전체 분석 실행 (트렌드, 수요, 경쟁 분석)
reddit-insight analyze full python
```

### 3. 리포트 생성

```bash
# 마크다운 리포트 생성
reddit-insight report generate ./reports -s python
```

### 4. 대시보드 실행

```bash
# 웹 대시보드 시작
reddit-insight dashboard start

# 개발 모드 (자동 재시작)
reddit-insight dashboard start --reload
```

브라우저에서 http://localhost:8000 접속

### 5. ML 분석 사용

대시보드에서 ML 분석 기능을 사용할 수 있습니다:

- **트렌드 예측**: `/dashboard/trends/predict/{keyword}` - 키워드의 미래 트렌드 예측
- **이상 탐지**: `/dashboard/trends/anomalies/{keyword}` - 비정상적인 트렌드 포인트 탐지
- **토픽 분석**: `/dashboard/topics` - 문서에서 잠재 토픽 추출
- **클러스터링**: `/dashboard/clusters` - 유사 문서 자동 그룹화

자세한 사용법은 [대시보드 가이드](docs/dashboard-guide.md)를 참조하세요.

## CLI 명령어

### collect - 데이터 수집

```bash
reddit-insight collect <subreddit> [options]

옵션:
  -s, --sort       정렬 방식 (hot/new/top, 기본: hot)
  -l, --limit      수집할 게시물 수 (기본: 100)
  -c, --comments   댓글도 수집
  -t, --time-filter  top 정렬 시 기간 (hour/day/week/month/year/all)
```

### collect-list - 일괄 수집

```bash
reddit-insight collect-list <file> [options]

# 파일 형식 (한 줄에 하나씩)
python
javascript
webdev
```

### analyze - 분석

```bash
reddit-insight analyze full <subreddit> [-l LIMIT]
```

### report - 리포트 생성

```bash
reddit-insight report generate <output_dir> -s <subreddit> [-l LIMIT]
```

### dashboard - 대시보드

```bash
reddit-insight dashboard start [--host HOST] [--port PORT] [--reload]
```

### status - 상태 확인

```bash
reddit-insight status
```

## 프로젝트 구조

```
reddit-insight/
├── src/reddit_insight/
│   ├── analysis/          # 분석 모듈
│   │   ├── keywords.py    # 키워드 추출
│   │   ├── trends.py      # 트렌드 분석
│   │   ├── demand_*.py    # 수요 분석
│   │   ├── competitive.py # 경쟁 분석
│   │   └── sentiment.py   # 감성 분석
│   ├── dashboard/         # 웹 대시보드
│   │   ├── app.py         # FastAPI 앱
│   │   ├── routers/       # API 라우터
│   │   └── templates/     # Jinja2 템플릿
│   ├── insights/          # 인사이트 생성
│   │   ├── rules_engine.py
│   │   ├── scoring.py
│   │   └── feasibility.py
│   ├── pipeline/          # 데이터 파이프라인
│   │   ├── collector.py
│   │   └── preprocessor.py
│   ├── reddit/            # Reddit 클라이언트
│   ├── reports/           # 리포트 생성
│   ├── scraping/          # 스크래핑 모듈
│   ├── storage/           # 데이터 저장
│   └── cli.py             # CLI 진입점
├── tests/                 # 테스트
├── docs/                  # 문서
├── pyproject.toml
└── README.md
```

## API 문서

대시보드 실행 후 다음 경로에서 API 문서를 확인할 수 있습니다:

- Swagger UI: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc

## 프로그래매틱 사용

```python
from reddit_insight.pipeline.collector import Collector, CollectorConfig
from reddit_insight.analysis.keywords import UnifiedKeywordExtractor
from reddit_insight.analysis.trends import KeywordTrendAnalyzer
from reddit_insight.analysis.demand_analyzer import DemandAnalyzer
from reddit_insight.analysis.competitive import CompetitiveAnalyzer

# 데이터 수집
async with Collector() as collector:
    config = CollectorConfig(subreddit="python", limit=100)
    result = await collector.collect_subreddit(config)

# 키워드 추출
extractor = UnifiedKeywordExtractor()
keywords = extractor.extract_from_posts(posts, num_keywords=20)

# 트렌드 분석
analyzer = KeywordTrendAnalyzer()
trends = analyzer.find_trending_keywords(posts, num_keywords=10)

# 수요 분석
demand_analyzer = DemandAnalyzer()
demand_report = demand_analyzer.analyze(posts)

# 경쟁 분석
competitive_analyzer = CompetitiveAnalyzer()
competitive_report = competitive_analyzer.analyze(posts)
```

## 개발

### 테스트 실행

```bash
# 전체 테스트
pytest

# 커버리지 포함
pytest --cov=src/reddit_insight

# 특정 테스트
pytest tests/test_analysis.py -v
```

### 코드 품질

```bash
# 린트 검사
ruff check src/ tests/

# 린트 자동 수정
ruff check src/ tests/ --fix

# 타입 검사
mypy src/
```

### 포맷팅

```bash
ruff format src/ tests/
```

## Docker 배포

### Docker Compose (권장)

```bash
# 환경 변수 설정
cp .env.example .env
# .env 파일 편집하여 필요한 값 설정

# 컨테이너 시작
docker-compose up -d

# 로그 확인
docker-compose logs -f
```

### Docker 단독 실행

```bash
# 이미지 빌드
docker build -t reddit-insight .

# 컨테이너 실행
docker run -d -p 8888:8888 \
  -e SECRET_KEY=your-secret-key \
  -v $(pwd)/data:/app/data \
  reddit-insight
```

브라우저에서 http://localhost:8888 접속

## 인증 및 API 키

### API 키 생성

```bash
# CLI로 API 키 생성
reddit-insight api-key create --name "My App" --rate-limit 1000

# 또는 대시보드에서 생성
# http://localhost:8888/dashboard/settings/api-keys
```

### API 키 사용

```bash
# 헤더에 API 키 포함
curl -H "X-API-Key: your-api-key" http://localhost:8888/api/v1/analyze
```

## 환경 변수

| 변수 | 설명 | 기본값 |
|------|------|--------|
| `SECRET_KEY` | JWT 서명 키 | (필수) |
| `DATABASE_URL` | 데이터베이스 URL | `sqlite:///./data/reddit_insight.db` |
| `REDDIT_CLIENT_ID` | Reddit API Client ID | - |
| `REDDIT_CLIENT_SECRET` | Reddit API Secret | - |
| `RATE_LIMIT_PER_MINUTE` | 분당 요청 제한 | `100` |
| `LOG_LEVEL` | 로그 레벨 | `INFO` |
| `ALLOWED_ORIGINS` | CORS 허용 도메인 | `*` |

## 스케줄된 분석

자동 분석 작업을 설정할 수 있습니다:

```bash
# CLI로 스케줄 추가
reddit-insight schedule add python --interval 6h

# 스케줄 목록 확인
reddit-insight schedule list

# 또는 대시보드에서 관리
# http://localhost:8888/dashboard/settings/scheduler
```

## 모니터링

### 헬스 체크

```bash
curl http://localhost:8888/health
```

### 요청 통계

```bash
# CLI로 통계 확인
python -m reddit_insight.dashboard.monitoring stats 24

# 오류 로그 확인
python -m reddit_insight.dashboard.monitoring errors 50
```

## 기술 스택

- **Python 3.11+**: 코어 언어
- **SQLAlchemy 2.0**: 비동기 ORM
- **aiosqlite**: 비동기 SQLite
- **FastAPI**: 웹 프레임워크
- **HTMX**: 동적 UI
- **rich**: CLI 출력
- **scikit-learn**: ML 분석
- **YAKE**: 키워드 추출
- **NLTK**: 텍스트 처리
- **APScheduler**: 스케줄 작업
- **Docker**: 컨테이너 배포

## 라이선스

MIT License

## 기여

이슈와 풀 리퀘스트를 환영합니다.

1. 포크
2. 기능 브랜치 생성 (`git checkout -b feature/amazing-feature`)
3. 변경사항 커밋 (`git commit -m 'Add amazing feature'`)
4. 브랜치 푸시 (`git push origin feature/amazing-feature`)
5. 풀 리퀘스트 생성
