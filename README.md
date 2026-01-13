# Reddit Insight

Reddit 데이터 수집 및 분석 도구 - 키워드 기반 게시물 수집, 요약, 인사이트 추출

## 개요

Reddit Insight는 사용자가 지정한 키워드에 대해 Reddit 게시물을 수집하고, 요약 및 인사이트를 추출하는 도구입니다.

### 주요 기능

- 키워드 기반 Reddit 게시물 검색 및 수집
- 게시물 및 댓글 데이터 분석
- 자동 요약 생성 (향후 구현 예정)
- 인사이트 추출 (향후 구현 예정)

## 설치

### 요구 사항

- Python 3.11 이상
- pip

### 기본 설치

```bash
pip install -e .
```

### 개발 환경 설치

```bash
pip install -e ".[dev]"
```

## 개발

### 프로젝트 구조

```
reddit-insight/
├── src/
│   └── reddit_insight/     # 메인 패키지
├── tests/                  # 테스트
├── pyproject.toml          # 프로젝트 설정
└── README.md
```

### 테스트 실행

```bash
pytest
```

### 타입 체크

```bash
mypy src/
```

### 린터 실행

```bash
ruff check src/ tests/
```

## 라이선스

MIT License
