# CLI Reference

Reddit Insight CLI 명령어 전체 레퍼런스입니다.

## 전역 옵션

모든 명령에서 사용 가능한 옵션입니다.

```bash
reddit-insight [OPTIONS] COMMAND [ARGS]...
```

| 옵션 | 설명 |
|------|------|
| `-d, --debug` | 디버그 모드 활성화 (상세 로그 출력) |
| `-v, --version` | 버전 정보 출력 |
| `--help` | 도움말 출력 |

## 명령어 목록

| 명령 | 설명 |
|------|------|
| `collect` | 단일 서브레딧 데이터 수집 |
| `collect-list` | 여러 서브레딧 일괄 수집 |
| `analyze` | 데이터 분석 |
| `report` | 리포트 생성 |
| `dashboard` | 웹 대시보드 관리 |
| `status` | 데이터베이스 상태 조회 |

---

## collect

단일 서브레딧에서 게시물을 수집합니다.

### 사용법

```bash
reddit-insight collect <subreddit> [OPTIONS]
```

### 인자

| 인자 | 필수 | 설명 |
|------|------|------|
| `subreddit` | 예 | 수집할 서브레딧 이름 (r/ 제외) |

### 옵션

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `-s, --sort` | `hot` | 정렬 방식 (`hot`, `new`, `top`) |
| `-l, --limit` | `100` | 수집할 게시물 수 |
| `-c, --comments` | `false` | 댓글 수집 여부 |
| `--comment-limit` | `50` | 게시물당 수집할 댓글 수 |
| `-t, --time-filter` | `week` | `top` 정렬 시 기간 필터 |

### time-filter 값

| 값 | 설명 |
|----|------|
| `hour` | 최근 1시간 |
| `day` | 최근 24시간 |
| `week` | 최근 1주 |
| `month` | 최근 1개월 |
| `year` | 최근 1년 |
| `all` | 전체 기간 |

### 예제

```bash
# 기본 수집
reddit-insight collect python

# 최신 게시물 200개 수집
reddit-insight collect python -s new -l 200

# 월간 인기 게시물 수집
reddit-insight collect python -s top -t month -l 100

# 댓글 포함 수집
reddit-insight collect python -l 50 -c --comment-limit 100

# 디버그 모드로 수집
reddit-insight -d collect python -l 50
```

### 출력

```
+---------------------------+
| r/python 수집 결과        |
+---------------------------+
| 항목         | 값         |
+--------------|------------|
| 새 게시물    | 100        |
| 중복 게시물  | 5          |
| 필터링됨     | 2          |
| 소요 시간    | 5.23초     |
+---------------------------+
Success: 데이터 수집이 완료되었습니다!
```

---

## collect-list

파일에서 서브레딧 목록을 읽어 일괄 수집합니다.

### 사용법

```bash
reddit-insight collect-list [FILE] [OPTIONS]
```

### 인자

| 인자 | 필수 | 설명 |
|------|------|------|
| `file` | 아니오 | 서브레딧 목록 파일 (생략 시 stdin) |

### 옵션

`collect` 명령과 동일한 옵션을 지원합니다.

### 파일 형식

한 줄에 하나의 서브레딧 이름을 작성합니다:

```text
# subreddits.txt
# 주석은 #으로 시작
python
javascript
webdev
programming
r/golang  # r/ 접두사는 자동 제거됨
```

### 예제

```bash
# 파일에서 읽기
reddit-insight collect-list subreddits.txt -l 100

# stdin에서 읽기
echo -e "python\njavascript" | reddit-insight collect-list -l 50

# 댓글 포함 일괄 수집
reddit-insight collect-list subreddits.txt -l 50 -c
```

### 출력

```
+------------------------------------------+
| 수집 결과 요약                            |
+------------------------------------------+
| 서브레딧     | 새 게시물 | 중복 | 소요시간 |
|--------------|-----------|------|----------|
| r/python     | 100       | 0    | 3.2초    |
| r/javascript | 98        | 2    | 3.5초    |
| r/webdev     | 95        | 5    | 3.1초    |
+------------------------------------------+
총 3/3 성공, 새 게시물 293개, 총 9.8초
```

---

## analyze

수집된 데이터를 분석합니다.

### 하위 명령어

| 명령 | 설명 |
|------|------|
| `full` | 전체 분석 실행 (트렌드, 수요, 경쟁) |

### analyze full

모든 분석을 한 번에 실행합니다.

```bash
reddit-insight analyze full <subreddit> [OPTIONS]
```

### 인자

| 인자 | 필수 | 설명 |
|------|------|------|
| `subreddit` | 예 | 분석할 서브레딧 이름 |

### 옵션

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `-l, --limit` | `500` | 분석할 최대 게시물 수 |

### 예제

```bash
# 기본 분석
reddit-insight analyze full python

# 더 많은 데이터로 분석
reddit-insight analyze full python -l 1000
```

### 출력

분석 결과에는 다음이 포함됩니다:

1. **상위 키워드** - 자주 언급되는 키워드 순위
2. **키워드 트렌드** - 시간에 따른 키워드 변화
3. **수요 분석 요약** - 탐지된 수요 신호 및 기회
4. **경쟁 분석 요약** - 엔티티 언급 및 감성 분석

---

## report

분석 결과를 마크다운 리포트로 생성합니다.

### 하위 명령어

| 명령 | 설명 |
|------|------|
| `generate` | 마크다운 리포트 생성 |

### report generate

```bash
reddit-insight report generate <output_dir> -s <subreddit> [OPTIONS]
```

### 인자

| 인자 | 필수 | 설명 |
|------|------|------|
| `output_dir` | 예 | 리포트 출력 디렉토리 |

### 옵션

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `-s, --subreddit` | 필수 | 분석할 서브레딧 이름 |
| `-l, --limit` | `500` | 분석할 최대 게시물 수 |

### 예제

```bash
# 리포트 생성
reddit-insight report generate ./reports -s python

# 더 많은 데이터로 리포트 생성
reddit-insight report generate ./reports -s python -l 1000
```

### 생성되는 파일

| 파일 | 설명 |
|------|------|
| `trend_report.md` | 트렌드 분석 리포트 |
| `demand_report.md` | 수요 분석 리포트 |
| `competitive_report.md` | 경쟁 분석 리포트 |
| `insight_report.md` | 비즈니스 인사이트 리포트 |
| `full_report.md` | 종합 리포트 |
| `report_metadata.json` | 메타데이터 |

---

## dashboard

웹 대시보드를 관리합니다.

### 하위 명령어

| 명령 | 설명 |
|------|------|
| `start` | 대시보드 서버 시작 |

### dashboard start

```bash
reddit-insight dashboard start [OPTIONS]
```

### 옵션

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `--host` | `127.0.0.1` | 서버 호스트 주소 |
| `--port` | `8000` | 서버 포트 |
| `--reload` | `false` | 개발 모드 (코드 변경 시 자동 재시작) |

### 예제

```bash
# 기본 실행
reddit-insight dashboard start

# 외부 접근 허용
reddit-insight dashboard start --host 0.0.0.0

# 다른 포트 사용
reddit-insight dashboard start --port 3000

# 개발 모드
reddit-insight dashboard start --reload
```

### 접속 URL

- 대시보드: http://localhost:8000
- API 문서 (Swagger): http://localhost:8000/api/docs
- API 문서 (ReDoc): http://localhost:8000/api/redoc

---

## status

데이터베이스에 저장된 데이터 통계를 조회합니다.

### 사용법

```bash
reddit-insight status
```

### 출력

```
+------------------------------------------+
| 전체 통계                                 |
+------------------------------------------+
| 항목       | 개수                         |
|------------|------------------------------|
| 서브레딧   | 5                            |
| 게시물     | 2,500                        |
| 댓글       | 12,350                       |
+------------------------------------------+

+------------------------------------------+
| 서브레딧별 게시물 (상위 10개)             |
+------------------------------------------+
| 서브레딧      | 게시물 수                   |
|---------------|----------------------------|
| r/python      | 1,000                      |
| r/javascript  | 800                        |
| r/webdev      | 700                        |
+------------------------------------------+
```

---

## 종료 코드

| 코드 | 의미 |
|------|------|
| `0` | 성공 |
| `1` | 오류 발생 |
| `130` | 사용자에 의해 중단 (Ctrl+C) |

---

## 환경 변수

| 변수 | 설명 |
|------|------|
| `REDDIT_CLIENT_ID` | Reddit API 클라이언트 ID |
| `REDDIT_CLIENT_SECRET` | Reddit API 클라이언트 시크릿 |
| `REDDIT_USER_AGENT` | Reddit API 유저 에이전트 |
| `DATABASE_URL` | 데이터베이스 연결 URL |

---

## 설정 파일

프로젝트 루트에 `.env` 파일을 생성하여 환경 변수를 설정할 수 있습니다:

```bash
# .env
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USER_AGENT=reddit-insight/0.1.0
DATABASE_URL=sqlite+aiosqlite:///./data/reddit_insight.db
```
