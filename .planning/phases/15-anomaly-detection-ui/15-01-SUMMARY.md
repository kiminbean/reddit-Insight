# Summary 15-01: Anomaly Detection UI

## Outcome

**Status**: COMPLETE

AnomalyDetector ML 모듈의 이상 탐지 결과를 대시보드에 시각화하는 기능을 완성했다. 이상 포인트를 차트에서 빨간 점으로 하이라이트하고, 상세 정보를 테이블로 제공한다.

## Changes Made

### New Files

| File | Purpose |
|------|---------|
| `src/reddit_insight/dashboard/services/anomaly_service.py` | AnomalyDetector 래퍼 서비스 |
| `src/reddit_insight/dashboard/templates/trends/partials/anomaly_chart.html` | 이상 탐지 차트 컴포넌트 |
| `tests/dashboard/test_anomaly_service.py` | AnomalyService 단위 테스트 |

### Modified Files

| File | Change |
|------|--------|
| `src/reddit_insight/dashboard/services/__init__.py` | AnomalyService export 추가 |
| `src/reddit_insight/dashboard/routers/trends.py` | 이상 탐지 API 엔드포인트 추가 |
| `src/reddit_insight/dashboard/templates/trends/index.html` | 이상 탐지 섹션 및 JS 함수 추가 |
| `src/reddit_insight/dashboard/templates/trends/partials/keyword_list.html` | Anomaly 버튼 추가 |

## Architecture

```
User clicks "Anomaly" button
    ↓
loadAnomalyDetection(keyword) [JavaScript]
    ↓
GET /dashboard/trends/anomalies-partial/{keyword}
    ↓
AnomalyService.detect_anomalies(keyword, days)
    ↓
AnomalyDetector.detect(time_series)
    ↓
AnomalyView.to_chart_data()
    ↓
anomaly_chart.html [Chart.js visualization]
```

## Features Implemented

1. **AnomalyService**
   - `detect_anomalies(keyword, days, method, threshold)` 메서드
   - Chart.js 형식 데이터 변환 (`to_chart_data()`)
   - 정상/이상 포인트 데이터 분리

2. **API Endpoints**
   - `GET /dashboard/trends/anomalies/{keyword}` - JSON 데이터
   - `GET /dashboard/trends/anomalies-partial/{keyword}` - HTML 파셜

3. **UI Components**
   - 이상 포인트 빨간 점 하이라이트 (pointRadius: 8)
   - 요약 카드 (이상 개수, 전체 포인트, 이상 비율)
   - 분석 기간 선택 드롭다운 (14/30/60/90일)
   - 이상 포인트 상세 테이블

4. **Detection Methods**
   - auto (데이터 크기에 따라 자동 선택)
   - zscore (z-score 기반)
   - iqr (IQR 기반)
   - isolation_forest (Isolation Forest)

## Verification

### Tests

```bash
pytest tests/dashboard/test_anomaly_service.py -v
# 20 passed in 1.42s
```

### Manual Testing

```bash
# 서버 시작
python -m reddit_insight.dashboard.main

# API 테스트
curl http://localhost:8888/dashboard/trends/anomalies/python?days=30

# UI 확인
# 브라우저에서 /dashboard/trends → 키워드 행의 "Anomaly" 버튼 클릭
```

## Commits

1. `792be96` - feat(15-01): add AnomalyService for dashboard anomaly detection
2. `141d86c` - feat(15-01): add anomaly detection API endpoints
3. `ef68ea5` - feat(15-01): add anomaly detection chart component
4. `dc4fe1e` - feat(15-01): integrate anomaly detection into Trends page
5. `7829084` - test(15-01): add AnomalyService unit tests

## Success Criteria Met

- [x] AnomalyService가 AnomalyDetector 호출 성공
- [x] `/dashboard/trends/anomalies/{keyword}` API 동작
- [x] 차트에서 이상 포인트가 빨간 점으로 표시
- [x] 이상 탐지 요약 (개수, 방법) 표시

## Notes

- 정상 포인트는 파란색(rgb(59, 130, 246)), 이상 포인트는 빨간색(rgb(239, 68, 68))
- 이상 포인트는 정상 포인트보다 큰 반지름(8 vs 4)으로 구분
- 트렌드 라인은 반투명 배경으로 전체 추세 표시
- HTMX를 통한 동적 로딩으로 페이지 새로고침 없이 차트 표시
