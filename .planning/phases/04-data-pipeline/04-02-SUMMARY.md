---
phase: 04-data-pipeline
plan: 02
status: completed
completed_at: 2026-01-13
---

# 04-02 Summary: 데이터 전처리 파이프라인

## Objective
수집된 Reddit 데이터를 정제하고 분석 가능한 형태로 변환하는 데이터 파이프라인 구축

## What Was Done

### Task 1: Repository 패턴 구현
- **BaseRepository**: AsyncSession 주입을 통한 트랜잭션 관리 기본 클래스
- **SubredditRepository**: get_by_name, get_or_create, update_metrics, list_all
- **PostRepository**: get_by_reddit_id, save, save_many, get_by_subreddit, get_recent
- **CommentRepository**: get_by_reddit_id, save, save_many, get_by_post
- SQLite ON CONFLICT DO UPDATE로 upsert 지원

### Task 2: 텍스트 전처리기 구현
- **TextPreprocessor** 클래스 생성
- clean_text: URL 제거, HTML 엔티티 디코딩, 연속 공백/줄바꿈 정규화
- is_deleted_content: [deleted], [removed] 콘텐츠 감지
- normalize_author: 삭제된 사용자 처리 (None 반환)
- extract_urls: 텍스트에서 URL 목록 추출
- extract_mentions: /u/user 및 /r/subreddit 멘션 추출
- get_text_stats: 문자/단어/문장 수 통계 계산

### Task 3: 데이터 파이프라인 클래스 구현
- **ProcessingResult**: 처리 통계 데이터 클래스 (total, new, duplicates, filtered, errors)
- **CollectionResult**: 전체 수집 결과 (posts, comments 결과 통합)
- **DataPipeline.process_posts**: 게시물 전처리 및 bulk 저장
- **DataPipeline.process_comments**: 댓글 전처리 및 bulk 저장
- **DataPipeline.ensure_subreddit**: 서브레딧 정보 upsert
- **DataPipeline.collect_and_store**: 수집 -> 전처리 -> 저장 end-to-end 워크플로우
- UnifiedDataSource 통합으로 API/스크래핑 자동 전환 지원

### Task 4: export 및 통합
- pipeline/__init__.py: DataPipeline, ProcessingResult, CollectionResult export
- storage/__init__.py: PostRepository, CommentRepository, SubredditRepository export
- __all__ 정의로 공개 인터페이스 명확화

## Files Created/Modified
- `src/reddit_insight/storage/repository.py` (신규, 416줄)
- `src/reddit_insight/pipeline/__init__.py` (신규, 18줄)
- `src/reddit_insight/pipeline/preprocessor.py` (신규, 262줄)
- `src/reddit_insight/pipeline/data_pipeline.py` (신규, 415줄)
- `src/reddit_insight/storage/__init__.py` (수정)

## Verification Results
```
[OK] Repository 패턴 import 성공
[OK] TextPreprocessor 동작 확인
[OK] DataPipeline 및 ProcessingResult 동작 확인
[OK] 모든 모듈 import 성공
```

## Architecture Decisions
1. **Repository 패턴**: 데이터 접근 로직을 추상화하여 도메인 로직과 분리
2. **세션 주입**: 트랜잭션 범위를 호출자가 제어 가능
3. **Bulk upsert**: SQLite ON CONFLICT DO UPDATE로 효율적인 대량 저장
4. **삭제 콘텐츠 필터링**: [deleted], [removed] 자동 감지 및 필터링
5. **ProcessingResult 합산**: 여러 처리 결과를 통합하여 통계 추적

## Usage Example
```python
from reddit_insight.storage import Database
from reddit_insight.pipeline import DataPipeline

async with Database() as db:
    pipeline = DataPipeline(db)
    result = await pipeline.collect_and_store(
        subreddit="python",
        sort="hot",
        limit=100,
        include_comments=True,
    )
    print(f"새 게시물: {result.posts.new}")
    print(f"새 댓글: {result.comments.new}")
```

## Commits
1. `[04-02] Task 1: Repository 패턴 구현`
2. `[04-02] Task 2: 텍스트 전처리기 구현`
3. `[04-02] Task 3: 데이터 파이프라인 클래스 구현`
4. `[04-02] Task 4: export 및 통합`

## Next Steps
- 04-03: 분석 파이프라인 구현 (트렌드 감지, 키워드 추출)
- 단위 테스트 추가 (Repository, TextPreprocessor)
- 스케줄링 기능으로 자동 수집 구현
