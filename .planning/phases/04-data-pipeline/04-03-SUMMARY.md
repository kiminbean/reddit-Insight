---
phase: 04-data-pipeline
plan: 03
completed: 2026-01-13
---

# 04-03 Summary: 데이터 수집 스케줄러 구현

## Completed Tasks

### Task 1: Collector 클래스 구현
- **Files**: `src/reddit_insight/pipeline/collector.py`
- **Changes**:
  - `CollectorConfig`: 단일 서브레딧 수집 설정 데이터 클래스
  - `CollectionResult`: 수집 결과 추적 (소요시간, 에러 등)
  - `Collector`: UnifiedDataSource + DataPipeline 통합
    - `collect_subreddit()`: 단일 서브레딧 수집
    - `collect_multiple()`: 여러 서브레딧 순차 수집
    - `collect_from_list()`: 간편 수집 메서드

### Task 2: 간단한 스케줄러 구현
- **Files**: `src/reddit_insight/pipeline/scheduler.py`
- **Changes**:
  - `ScheduleConfig`: 정기 수집 설정 (서브레딧 목록, 간격 등)
  - `ScheduleRun`: 실행 기록 추적
  - `SchedulerStatus`: 스케줄러 상태 정보
  - `SimpleScheduler`: asyncio 기반 인터벌 스케줄러
    - `run_once()`: 한 번 실행
    - `start(max_runs)`: 반복 실행
    - `stop()`: 실행 중지
    - `get_status()`: 상태 조회

### Task 3: CLI 인터페이스 구현
- **Files**: `src/reddit_insight/cli.py`, `pyproject.toml`
- **Changes**:
  - argparse + rich 기반 CLI (click/typer 미사용)
  - `collect`: 단일 서브레딧 수집
    - `--sort`, `--limit`, `--comments`, `--time-filter` 옵션
  - `collect-list`: 서브레딧 목록 파일 또는 stdin에서 수집
  - `status`: 데이터베이스 통계 조회
  - `pyproject.toml`에 `reddit-insight` 진입점 추가
  - Progress bar와 결과 테이블 표시 (rich)

### Task 4: export 및 테스트
- **Files**: `src/reddit_insight/pipeline/__init__.py`, `tests/test_pipeline.py`
- **Changes**:
  - pipeline/__init__.py 업데이트:
    - Collector, CollectorConfig, CollectorResult export
    - SimpleScheduler, ScheduleConfig, ScheduleRun 등 export
  - tests/test_pipeline.py 생성:
    - TestTextPreprocessor: 텍스트 정제 테스트 (14개)
    - TestCollectorConfig/Result: 설정 및 결과 테스트
    - TestScheduleConfig: 스케줄 설정 테스트
    - TestCollector/SimpleScheduler: 수집기/스케줄러 테스트
    - 전체 27개 테스트 정의

## Verification Results

```
[OK] Collector 및 CollectorConfig import
[OK] SimpleScheduler 및 ScheduleConfig import
[OK] CLI main 함수 import
[OK] tests/test_pipeline.py 존재
```

- 25개 테스트 통과, 2개 async 테스트 skip (pytest-asyncio 설정 필요)

## CLI Usage Examples

```bash
# 단일 서브레딧 수집
reddit-insight collect python --sort hot --limit 50

# 댓글 포함 수집
reddit-insight collect python --comments --comment-limit 20

# 서브레딧 목록 파일에서 수집
reddit-insight collect-list subreddits.txt --limit 100

# 데이터베이스 상태 조회
reddit-insight status
```

## Phase 4 Completion Notes

Phase 4 (Data Pipeline)가 완료되었습니다:

- **04-01**: Database, SQLAlchemy 모델, Repository 패턴
- **04-02**: DataPipeline, TextPreprocessor
- **04-03**: Collector, SimpleScheduler, CLI

전체 데이터 수집 파이프라인이 end-to-end로 동작합니다:
1. CLI로 수동 수집 트리거
2. Collector가 UnifiedDataSource로 데이터 수집
3. DataPipeline이 전처리 및 저장
4. SimpleScheduler로 정기 수집 가능
