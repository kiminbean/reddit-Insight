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

### 시각화
- 웹 대시보드 (FastAPI + HTMX)
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

## 라이선스

MIT License

## 기여

이슈와 풀 리퀘스트를 환영합니다.

1. 포크
2. 기능 브랜치 생성 (`git checkout -b feature/amazing-feature`)
3. 변경사항 커밋 (`git commit -m 'Add amazing feature'`)
4. 브랜치 푸시 (`git push origin feature/amazing-feature`)
5. 풀 리퀘스트 생성
