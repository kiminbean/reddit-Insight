# Summary 13-01: Recent Analyses Display Enhancement

## Objective

대시보드 홈의 Recent Analyses 섹션에서 개별 분석 결과 상세 페이지로 이동할 수 있도록 Analysis Detail 페이지를 구현했다.

## Changes Made

### 1. data_store.py - load_analysis_by_id() 함수 추가

```python
def load_analysis_by_id(analysis_id: int) -> AnalysisData | None:
    """특정 ID의 분석 결과를 데이터베이스에서 로드한다."""
```

- DB에서 특정 ID의 분석 결과를 조회
- 존재하지 않으면 None 반환

### 2. routers/dashboard.py - Analysis Detail 라우트 추가

```python
@router.get("/analysis/{analysis_id}", response_class=HTMLResponse)
async def analysis_detail(request: Request, analysis_id: int) -> HTMLResponse:
    """특정 분석 결과의 상세 페이지를 렌더링한다."""
```

- `/dashboard/analysis/{analysis_id}` 경로
- 존재하지 않는 ID에 대해 404 응답
- 주요 키워드 Top 5, 수요 Top 3, 인사이트 Top 3 추출

### 3. templates/dashboard/analysis_detail.html - 상세 페이지 템플릿

- 분석 메타데이터 (서브레딧, 분석일시, 게시물 수)
- Top Keywords 섹션 (순위, 키워드, 언급 횟수, 성장률)
- Top Demands 섹션 (제목, 설명, 긴급도 점수, 타입)
- Top Insights 섹션 (제목, 설명, 타입, 신뢰도)
- Summary 사이드바 (서브레딧, 게시물 수, 키워드 수, 인사이트 수)
- Explore Data 네비게이션 (Trends, Demands, Competition, Insights 링크)
- Re-analyze 버튼

## Tests

```
tests/dashboard/test_data_integration.py::TestDataStoreIntegration::test_load_analysis_by_id PASSED
tests/dashboard/test_data_integration.py::TestDataStoreIntegration::test_load_analysis_by_id_not_found PASSED
```

- ID로 분석 결과 조회 성공 테스트
- 존재하지 않는 ID 조회 시 None 반환 테스트

## Verification

```bash
# 테스트 실행
PYTHONPATH=src pytest tests/dashboard/ -v

# 수동 검증
PYTHONPATH=src uvicorn reddit_insight.dashboard.app:app --port 8888
# http://localhost:8888/dashboard 에서 Recent Analyses 클릭
# http://localhost:8888/dashboard/analysis/99999 에서 404 확인
```

## Commits

- `feat(13-01): add analysis detail page with load_analysis_by_id`

## Success Criteria

- [x] `/dashboard/analysis/{id}` 라우트 동작
- [x] Analysis Detail 페이지에서 키워드/수요/인사이트 요약 표시
- [x] 존재하지 않는 ID에 대해 404 처리
