# Getting Started

Reddit Insight를 시작하기 위한 단계별 가이드입니다.

## 목차

1. [설치](#설치)
2. [환경 설정](#환경-설정)
3. [첫 번째 데이터 수집](#첫-번째-데이터-수집)
4. [분석 실행](#분석-실행)
5. [결과 해석](#결과-해석)

## 설치

### 요구 사항

- Python 3.11 이상
- pip (최신 버전 권장)
- 인터넷 연결

### Python 버전 확인

```bash
python --version
# Python 3.11.x 이상이어야 합니다
```

### 설치 방법

**기본 설치**

```bash
# 저장소 클론
git clone https://github.com/ibkim/reddit-insight.git
cd reddit-insight

# 패키지 설치 (개발 모드)
pip install -e .
```

**개발 환경 설치**

테스트 및 코드 품질 도구를 포함하려면:

```bash
pip install -e ".[dev]"
```

### 설치 확인

```bash
reddit-insight --version
# reddit-insight 0.1.0
```

## 환경 설정

### 기본 설정

Reddit Insight는 별도의 설정 없이도 스크래핑 모드로 작동합니다.
하지만 Reddit API를 사용하면 더 안정적이고 빠른 데이터 수집이 가능합니다.

### Reddit API 설정 (권장)

1. [Reddit 앱 등록](https://www.reddit.com/prefs/apps) 페이지 방문
2. "create app" 또는 "create another app" 클릭
3. 앱 정보 입력:
   - name: `reddit-insight`
   - type: `script`
   - redirect uri: `http://localhost:8080`
4. 앱 생성 후 client_id와 client_secret 확인

**환경 변수 설정**

프로젝트 루트에 `.env` 파일 생성:

```bash
# .env
REDDIT_CLIENT_ID=your_client_id_here
REDDIT_CLIENT_SECRET=your_client_secret_here
REDDIT_USER_AGENT=reddit-insight/0.1.0
```

또는 환경 변수 직접 설정:

```bash
export REDDIT_CLIENT_ID=your_client_id_here
export REDDIT_CLIENT_SECRET=your_client_secret_here
export REDDIT_USER_AGENT=reddit-insight/0.1.0
```

### 데이터베이스 설정

기본적으로 SQLite 데이터베이스가 `./data/reddit_insight.db`에 생성됩니다.
다른 경로를 사용하려면:

```bash
# .env
DATABASE_URL=sqlite+aiosqlite:///path/to/your/database.db
```

## 첫 번째 데이터 수집

### 단일 서브레딧 수집

Python 서브레딧에서 최신 게시물 50개를 수집합니다:

```bash
reddit-insight collect python -l 50
```

출력 예시:
```
+---------------------------+
| r/python 수집 결과        |
+---------------------------+
| 항목         | 값         |
+--------------|------------|
| 새 게시물    | 50         |
| 중복 게시물  | 0          |
| 필터링됨     | 0          |
| 소요 시간    | 3.25초     |
+---------------------------+
Success: 데이터 수집이 완료되었습니다!
```

### 정렬 방식 변경

```bash
# 인기 게시물 (기본값)
reddit-insight collect python -s hot -l 100

# 최신 게시물
reddit-insight collect python -s new -l 100

# 주간 인기 게시물
reddit-insight collect python -s top -t week -l 100
```

### 댓글 포함 수집

```bash
reddit-insight collect python -l 50 --comments --comment-limit 30
```

### 수집 상태 확인

```bash
reddit-insight status
```

출력 예시:
```
+---------------------------+
| 전체 통계                 |
+---------------------------+
| 항목      | 개수          |
+-----------|---------------|
| 서브레딧  | 1             |
| 게시물    | 50            |
| 댓글      | 1,500         |
+---------------------------+
```

## 분석 실행

### 전체 분석

수집된 데이터에 대해 모든 분석을 실행합니다:

```bash
reddit-insight analyze full python
```

이 명령은 다음 분석을 수행합니다:
1. 키워드 추출 - 자주 언급되는 키워드 식별
2. 트렌드 분석 - 키워드의 시간별 변화 추적
3. 수요 분석 - 사용자 요구사항 패턴 탐지
4. 경쟁 분석 - 제품/서비스 언급 및 감성 분석

### 분석 결과 확인

분석 완료 후 다음과 같은 결과가 출력됩니다:

```
+---------------------------+
| 상위 키워드               |
+---------------------------+
| 순위 | 키워드   | 점수    |
|------|----------|---------|
| 1    | python   | 12.45   |
| 2    | django   | 8.32    |
| 3    | fastapi  | 6.21    |
+---------------------------+

+---------------------------+
| 키워드 트렌드             |
+---------------------------+
| 키워드  | 방향   | 변화율 |
|---------|--------|--------|
| fastapi | 상승   | +25.3% |
| flask   | 하락   | -12.1% |
| django  | 안정   | +2.5%  |
+---------------------------+
```

## 결과 해석

### 키워드 분석

- **점수**: 키워드의 상대적 중요도 (높을수록 자주 언급됨)
- **빈도**: 해당 키워드가 등장한 게시물 수

### 트렌드 분석

- **상승**: 최근 언급 빈도가 증가하는 키워드
- **하락**: 최근 언급 빈도가 감소하는 키워드
- **안정**: 변화가 크지 않은 키워드
- **변동**: 불규칙한 패턴을 보이는 키워드

### 수요 분석

- **카테고리별 분류**: 기능 요청, 문제 해결, 가격 관련 등
- **우선순위 점수**: 비즈니스 기회로서의 중요도

### 경쟁 분석

- **감성 점수**: -1(매우 부정) ~ +1(매우 긍정)
- **불만 유형**: 가격, 품질, 성능 등

## 다음 단계

- [CLI 레퍼런스](./cli-reference.md) - 모든 명령어 상세 설명
- [API 가이드](./api-guide.md) - 프로그래매틱 사용법
- [대시보드 가이드](./dashboard-guide.md) - 웹 UI 사용법

## 문제 해결

### 일반적인 오류

**"서브레딧을 찾을 수 없습니다"**

먼저 데이터를 수집해야 합니다:
```bash
reddit-insight collect <subreddit> -l 100
```

**"분석할 게시물이 없습니다"**

수집된 게시물이 충분한지 확인하세요:
```bash
reddit-insight status
```

**API 인증 오류**

환경 변수가 올바르게 설정되었는지 확인하세요:
```bash
echo $REDDIT_CLIENT_ID
```

### 도움 요청

```bash
# 전체 도움말
reddit-insight --help

# 특정 명령 도움말
reddit-insight collect --help
reddit-insight analyze --help
```
