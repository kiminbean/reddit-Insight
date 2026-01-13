# Summary 14-01: Trend Prediction UI

## Objective

TrendPredictor ML 모듈의 시계열 예측 결과를 대시보드에 시각화한다. 예측값, 신뢰구간, 예측 정확도를 차트로 표시한다.

## Changes Made

### 1. PredictionService 생성

**파일**: `src/reddit_insight/dashboard/services/prediction_service.py`

```python
class PredictionView:
    """예측 결과 뷰 데이터."""
    keyword: str
    historical_dates: list[str]
    historical_values: list[float]
    forecast_dates: list[str]
    forecast_values: list[float]
    confidence_lower: list[float]
    confidence_upper: list[float]
    model_name: str
    metrics: dict[str, float]
    confidence_level: float

class PredictionService:
    def predict_keyword_trend(
        self, keyword: str, historical_days: int = 14,
        forecast_days: int = 7, confidence_level: float = 0.95
    ) -> PredictionView
```

- TrendPredictor ML 모듈 래핑
- TimeSeries 데이터 변환 및 예측 수행
- 데이터 부족 시 이동평균 기반 fallback
- `to_chart_data()` 메서드로 Chart.js 형식 변환

### 2. 예측 API 엔드포인트

**파일**: `src/reddit_insight/dashboard/routers/trends.py`

```python
@router.get("/predict/{keyword}")
async def predict_keyword(keyword: str, days: int = 7, ...)

@router.get("/predict-partial/{keyword}")
async def predict_partial(request: Request, keyword: str, ...)
```

- `/dashboard/trends/predict/{keyword}` - JSON 데이터 반환
- `/dashboard/trends/predict-partial/{keyword}` - HTMX HTML partial 반환
- 예측 기간(1-14일), 과거 데이터 기간(10-30일), 신뢰수준(0.5-0.99) 파라미터

### 3. 예측 차트 컴포넌트

**파일**: `src/reddit_insight/dashboard/templates/trends/partials/prediction_chart.html`

- Chart.js 기반 예측 시각화
- 실제 데이터: 파란색 실선
- 예측 데이터: 녹색 점선
- 신뢰구간: 녹색 반투명 영역
- 모델 메트릭 표시 (MAE, RMSE, MAPE)
- 예측 기간 선택 드롭다운 (3/7/14일)

### 4. Trends 페이지 통합

**파일**: `src/reddit_insight/dashboard/templates/trends/index.html`

- Prediction section 컨테이너 추가
- `loadPrediction(keyword)` JavaScript 함수
- 로딩 스피너 및 에러 처리 UI
- 자동 스크롤 to prediction section

**파일**: `src/reddit_insight/dashboard/templates/trends/partials/keyword_list.html`

- Predict 버튼 컬럼 추가
- 행 클릭 시 예측 로드

## Tests

```
tests/dashboard/test_prediction_service.py - 13 tests
├── TestPredictionView - 3 tests
│   ├── test_basic_properties PASSED
│   ├── test_to_chart_data_structure PASSED
│   └── test_to_chart_data_metadata PASSED
├── TestPredictionService - 5 tests
│   ├── test_predict_keyword_trend_returns_prediction_view PASSED
│   ├── test_predict_keyword_trend_forecast_days_parameter PASSED
│   ├── test_predict_keyword_trend_with_insufficient_data PASSED
│   ├── test_predict_keyword_trend_confidence_bounds PASSED
│   └── test_get_available_keywords PASSED
├── TestPredictionServiceSingleton - 1 test
│   └── test_get_prediction_service_returns_singleton PASSED
└── TestPredictionServiceEdgeCases - 4 tests
    ├── test_empty_timeline PASSED
    ├── test_forecast_days_boundary_values PASSED
    ├── test_special_characters_in_keyword PASSED
    └── test_confidence_level_boundary PASSED
```

## Verification

```bash
# 테스트 실행
PYTHONPATH=src pytest tests/dashboard/test_prediction_service.py -v

# 수동 검증
PYTHONPATH=src uvicorn reddit_insight.dashboard.app:app --port 8888
# http://localhost:8888/dashboard/trends 접속
# 키워드 클릭 또는 Predict 버튼 클릭
# 예측 차트 확인

# API 테스트
curl "http://localhost:8888/dashboard/trends/predict/python?days=7"
```

## Commits

- `feat(14-01): add PredictionService for trend forecasting`
- `feat(14-01): add prediction API endpoints`
- `feat(14-01): add prediction chart component`
- `feat(14-01): integrate prediction UI into trends page`
- `test(14-01): add PredictionService unit tests`

## Success Criteria

- [x] PredictionService가 TrendPredictor 호출 성공
- [x] `/dashboard/trends/predict/{keyword}` API 동작
- [x] 예측 차트가 실제값, 예측값, 신뢰구간 표시
- [x] 예측 메트릭 (MAE, RMSE, MAPE) 표시
- [x] 키워드 클릭 시 예측 차트 로드

## Output Files

- `src/reddit_insight/dashboard/services/prediction_service.py` (NEW)
- `src/reddit_insight/dashboard/services/__init__.py` (MODIFIED)
- `src/reddit_insight/dashboard/routers/trends.py` (MODIFIED)
- `src/reddit_insight/dashboard/templates/trends/partials/prediction_chart.html` (NEW)
- `src/reddit_insight/dashboard/templates/trends/partials/keyword_list.html` (MODIFIED)
- `src/reddit_insight/dashboard/templates/trends/index.html` (MODIFIED)
- `tests/dashboard/test_prediction_service.py` (NEW)
