# Summary 17-01: Text Clustering UI

## Completed Tasks

### Task 1: ClusterService 생성
- **파일**: `src/reddit_insight/dashboard/services/cluster_service.py`
- TextClusterer ML 모듈을 래핑하여 대시보드용 데이터 제공
- ClusterView, ClusterAnalysisView 데이터클래스 구현
- 저장된 분석 데이터에서 문서 추출 기능
- Chart.js 형식 데이터 변환 메서드 포함

### Task 2: Clusters 라우터 생성
- **파일**: `src/reddit_insight/dashboard/routers/clusters.py`
- `/dashboard/clusters` - 클러스터링 메인 페이지
- `/dashboard/clusters/analyze` - 클러스터링 실행 API
- `/dashboard/clusters/distribution` - 클러스터 분포 데이터
- `/dashboard/clusters/cluster/{id}` - 클러스터 상세 페이지
- `/dashboard/clusters/cluster/{id}/documents` - 클러스터 문서 목록

### Task 3: Clusters 페이지 템플릿 생성
- **파일**: `src/reddit_insight/dashboard/templates/clusters/index.html`
- 클러스터 수 입력 (자동/수동 선택 지원)
- 클러스터링 방법 선택 (Auto, K-Means, Agglomerative)
- 클러스터 크기 분포 바 차트 (Chart.js)
- 클러스터 구성 비율 파이 차트
- 클러스터 카드 그리드 (키워드, 샘플 문서 표시)
- **파일**: `src/reddit_insight/dashboard/templates/clusters/partials/cluster_cards.html`

### Task 4: 클러스터 상세 페이지 생성
- **파일**: `src/reddit_insight/dashboard/templates/clusters/detail.html`
- 클러스터 ID, 레이블, 키워드 표시
- 해당 클러스터의 모든 문서 목록 (페이지네이션)
- 다른 클러스터로 이동 링크
- 에러 상태 처리

### Task 5: 내비게이션에 Clusters 메뉴 추가
- **파일**: `src/reddit_insight/dashboard/templates/base.html`
- 데스크톱 네비게이션에 Clusters 링크 추가
- 모바일 메뉴에 Clusters 링크 추가
- 활성 상태 스타일링 적용

## Created/Modified Files

### New Files
- `src/reddit_insight/dashboard/services/cluster_service.py`
- `src/reddit_insight/dashboard/routers/clusters.py`
- `src/reddit_insight/dashboard/templates/clusters/index.html`
- `src/reddit_insight/dashboard/templates/clusters/partials/cluster_cards.html`
- `src/reddit_insight/dashboard/templates/clusters/detail.html`
- `tests/dashboard/test_cluster_service.py`

### Modified Files
- `src/reddit_insight/dashboard/services/__init__.py` - ClusterService export 추가
- `src/reddit_insight/dashboard/routers/__init__.py` - clusters 라우터 추가
- `src/reddit_insight/dashboard/app.py` - clusters 라우터 등록
- `src/reddit_insight/dashboard/templates/base.html` - Clusters 메뉴 추가

## Feature Highlights

### Clustering Analysis
- **자동 클러스터 수 선택**: Silhouette Score 기반 최적 클러스터 수 결정
- **수동 설정**: 2-10개 범위에서 클러스터 수 직접 지정
- **방법 선택**: K-Means, Agglomerative, Auto(자동 선택)

### Visualization
- **바 차트**: 클러스터별 문서 수 분포
- **도넛 차트**: 클러스터 구성 비율
- **클러스터 카드**: 대표 키워드 및 샘플 문서

### Quality Metrics
- **Silhouette Score**: 클러스터링 품질 지표 (-1 ~ 1)
- **클러스터 크기**: 각 클러스터의 문서 수
- **비율**: 전체 대비 각 클러스터 비율

## Verification

```bash
# 1. 서비스 테스트
pytest tests/dashboard/test_cluster_service.py -v

# 2. 대시보드 실행
python -m reddit_insight.dashboard

# 3. UI 확인
# 브라우저에서 http://localhost:8888/dashboard/clusters 접속
# "Run Clustering" 버튼 클릭 후 결과 확인
```

## Success Criteria Met

- [x] ClusterService가 TextClusterer 호출 성공
- [x] `/dashboard/clusters` 페이지 렌더링
- [x] 클러스터별 키워드 및 샘플 문서 표시
- [x] 클러스터 크기 분포 차트 표시
- [x] 클러스터 상세 페이지 동작
- [x] 네비게이션에 Clusters 메뉴 표시

## Commits

1. `feat(17-01): add ClusterService for text clustering`
2. `feat(17-01): add clusters router for clustering visualization`
3. `feat(17-01): add clusters page template with visualization`
4. `feat(17-01): add cluster detail page template`
5. `feat(17-01): add Clusters menu to navigation`
