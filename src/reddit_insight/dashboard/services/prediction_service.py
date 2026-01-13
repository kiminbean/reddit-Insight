"""예측 서비스.

TrendPredictor ML 모듈을 래핑하여 대시보드용 트렌드 예측 데이터를 제공한다.
"""

from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from functools import lru_cache
from typing import Any

from reddit_insight.analysis.ml import TrendPredictor, TrendPredictorConfig
from reddit_insight.analysis.time_series import TimeGranularity, TimePoint, TimeSeries
from reddit_insight.dashboard.trend_service import TrendService, get_trend_service


@dataclass
class PredictionView:
    """예측 결과 뷰 데이터.

    대시보드에서 예측 차트를 표시하기 위한 데이터 구조.

    Attributes:
        keyword: 예측 대상 키워드
        historical_dates: 과거 데이터 날짜 목록
        historical_values: 과거 데이터 값 목록
        forecast_dates: 예측 날짜 목록
        forecast_values: 예측값 목록
        confidence_lower: 신뢰구간 하한 목록
        confidence_upper: 신뢰구간 상한 목록
        model_name: 사용된 모델명
        metrics: 모델 성능 메트릭 (MAE, RMSE, MAPE)
        confidence_level: 신뢰수준 (e.g., 0.95)
    """

    keyword: str
    historical_dates: list[str]
    historical_values: list[float]
    forecast_dates: list[str]
    forecast_values: list[float]
    confidence_lower: list[float]
    confidence_upper: list[float]
    model_name: str = "Unknown"
    metrics: dict[str, float] = field(default_factory=dict)
    confidence_level: float = 0.95

    @property
    def mae(self) -> float:
        """Mean Absolute Error를 반환한다."""
        return self.metrics.get("MAE", 0.0)

    @property
    def rmse(self) -> float:
        """Root Mean Square Error를 반환한다."""
        return self.metrics.get("RMSE", 0.0)

    @property
    def mape(self) -> float:
        """Mean Absolute Percentage Error를 반환한다."""
        return self.metrics.get("MAPE", 0.0)

    @property
    def confidence_percent(self) -> int:
        """신뢰수준을 백분율로 반환한다."""
        return int(self.confidence_level * 100)

    def to_chart_data(self) -> dict[str, Any]:
        """Chart.js 형식의 데이터로 변환한다.

        Returns:
            Chart.js에서 사용할 수 있는 데이터 딕셔너리
        """
        # 모든 날짜 (과거 + 예측)
        all_dates = self.historical_dates + self.forecast_dates

        # 과거 데이터셋 (예측 구간은 null)
        historical_data = self.historical_values + [None] * len(self.forecast_dates)

        # 예측 데이터셋 (과거 구간은 null, 마지막 과거값과 연결)
        forecast_data = [None] * (len(self.historical_dates) - 1)
        if self.historical_values:
            forecast_data.append(self.historical_values[-1])  # 연결점
        forecast_data.extend(self.forecast_values)

        # 신뢰구간 (과거 구간은 null)
        lower_data = [None] * (len(self.historical_dates) - 1)
        if self.historical_values:
            lower_data.append(self.historical_values[-1])
        lower_data.extend(self.confidence_lower)

        upper_data = [None] * (len(self.historical_dates) - 1)
        if self.historical_values:
            upper_data.append(self.historical_values[-1])
        upper_data.extend(self.confidence_upper)

        return {
            "labels": all_dates,
            "datasets": [
                {
                    "label": f"{self.keyword} (Historical)",
                    "data": historical_data,
                    "borderColor": "rgb(59, 130, 246)",
                    "backgroundColor": "rgba(59, 130, 246, 0.1)",
                    "fill": False,
                    "tension": 0.3,
                    "pointRadius": 3,
                },
                {
                    "label": f"{self.keyword} (Forecast)",
                    "data": forecast_data,
                    "borderColor": "rgb(34, 197, 94)",
                    "backgroundColor": "rgba(34, 197, 94, 0.1)",
                    "borderDash": [5, 5],
                    "fill": False,
                    "tension": 0.3,
                    "pointRadius": 3,
                },
                {
                    "label": f"{self.confidence_percent}% CI Lower",
                    "data": lower_data,
                    "borderColor": "rgba(34, 197, 94, 0.3)",
                    "backgroundColor": "transparent",
                    "borderDash": [2, 2],
                    "fill": False,
                    "tension": 0.3,
                    "pointRadius": 0,
                },
                {
                    "label": f"{self.confidence_percent}% CI Upper",
                    "data": upper_data,
                    "borderColor": "rgba(34, 197, 94, 0.3)",
                    "backgroundColor": "rgba(34, 197, 94, 0.1)",
                    "borderDash": [2, 2],
                    "fill": "-1",  # 이전 데이터셋과 사이를 채움
                    "tension": 0.3,
                    "pointRadius": 0,
                },
            ],
            "metadata": {
                "keyword": self.keyword,
                "model": self.model_name,
                "confidence_level": self.confidence_percent,
                "metrics": {
                    "MAE": round(self.mae, 2),
                    "RMSE": round(self.rmse, 2),
                    "MAPE": round(self.mape, 1),
                },
            },
        }


class PredictionService:
    """예측 서비스.

    TrendPredictor를 래핑하여 대시보드에서 사용할 수 있는 형태로 데이터를 제공한다.

    Example:
        >>> service = PredictionService()
        >>> prediction = service.predict_keyword_trend("python", forecast_days=7)
        >>> chart_data = prediction.to_chart_data()
    """

    def __init__(
        self,
        trend_service: TrendService | None = None,
        predictor_config: TrendPredictorConfig | None = None,
    ) -> None:
        """서비스를 초기화한다.

        Args:
            trend_service: 트렌드 데이터를 가져올 서비스 (기본: 싱글톤)
            predictor_config: TrendPredictor 설정 (기본: 자동 선택)
        """
        self._trend_service = trend_service or get_trend_service()
        self._default_config = predictor_config or TrendPredictorConfig(
            model_type="auto",
            confidence_level=0.95,
            min_data_points=10,
        )

    def predict_keyword_trend(
        self,
        keyword: str,
        historical_days: int = 14,
        forecast_days: int = 7,
        confidence_level: float = 0.95,
    ) -> PredictionView:
        """키워드의 트렌드 예측을 수행한다.

        Args:
            keyword: 예측할 키워드
            historical_days: 과거 데이터 일수
            forecast_days: 예측 기간 (1-14일)
            confidence_level: 신뢰수준 (0.0-1.0)

        Returns:
            PredictionView: 예측 결과 뷰 데이터

        Raises:
            ValueError: 데이터 부족 또는 잘못된 파라미터
        """
        # 파라미터 검증
        forecast_days = max(1, min(14, forecast_days))
        historical_days = max(10, min(30, historical_days))
        confidence_level = max(0.5, min(0.99, confidence_level))

        # TrendService에서 과거 데이터 가져오기
        timeline = self._trend_service.get_keyword_timeline(
            keyword=keyword,
            days=historical_days,
        )

        if len(timeline) < 10:
            # 데이터 부족 시 기본 예측값 반환
            return self._create_fallback_prediction(
                keyword=keyword,
                timeline=timeline,
                forecast_days=forecast_days,
                confidence_level=confidence_level,
            )

        # TimeSeries 객체 생성
        time_series = self._create_time_series(keyword, timeline)

        # TrendPredictor로 예측 수행
        config = TrendPredictorConfig(
            forecast_periods=forecast_days,
            confidence_level=confidence_level,
            model_type=self._default_config.model_type,
            min_data_points=self._default_config.min_data_points,
        )
        predictor = TrendPredictor(config)

        try:
            result = predictor.predict(time_series)

            # PredictionView로 변환
            return PredictionView(
                keyword=keyword,
                historical_dates=[str(point.date) for point in timeline],
                historical_values=[float(point.count) for point in timeline],
                forecast_dates=[ts.strftime("%Y-%m-%d") for ts in result.timestamps],
                forecast_values=result.values,
                confidence_lower=result.lower_bound,
                confidence_upper=result.upper_bound,
                model_name=result.model_name,
                metrics=result.metrics,
                confidence_level=confidence_level,
            )
        except Exception as e:
            # 예측 실패 시 fallback
            return self._create_fallback_prediction(
                keyword=keyword,
                timeline=timeline,
                forecast_days=forecast_days,
                confidence_level=confidence_level,
                error_message=str(e),
            )

    def _create_time_series(self, keyword: str, timeline: list) -> TimeSeries:
        """TimelinePoint 목록을 TimeSeries로 변환한다.

        Args:
            keyword: 키워드
            timeline: TimelinePoint 목록

        Returns:
            TimeSeries 객체
        """
        points = []
        for point in timeline:
            # date를 datetime으로 변환
            dt = datetime.combine(point.date, datetime.min.time(), tzinfo=UTC)
            points.append(TimePoint(timestamp=dt, value=float(point.count)))

        return TimeSeries(
            keyword=keyword,
            granularity=TimeGranularity.DAY,
            points=points,
        )

    def _create_fallback_prediction(
        self,
        keyword: str,
        timeline: list,
        forecast_days: int,
        confidence_level: float,
        error_message: str | None = None,
    ) -> PredictionView:
        """데이터 부족 또는 예측 실패 시 기본 예측값을 생성한다.

        간단한 이동평균 기반 예측을 수행한다.

        Args:
            keyword: 키워드
            timeline: 과거 타임라인 데이터
            forecast_days: 예측 기간
            confidence_level: 신뢰수준
            error_message: 에러 메시지 (있는 경우)

        Returns:
            PredictionView with simple forecast
        """
        # 과거 데이터
        historical_dates = [str(point.date) for point in timeline]
        historical_values = [float(point.count) for point in timeline]

        # 간단한 이동평균 예측
        if historical_values:
            avg_value = sum(historical_values) / len(historical_values)
            std_value = (
                (sum((v - avg_value) ** 2 for v in historical_values) / len(historical_values)) ** 0.5
                if len(historical_values) > 1
                else avg_value * 0.1
            )
        else:
            avg_value = 50.0
            std_value = 10.0

        # 예측값 생성
        last_date = timeline[-1].date if timeline else date.today()
        forecast_dates = []
        forecast_values = []
        confidence_lower = []
        confidence_upper = []

        z_score = 1.96 if confidence_level >= 0.95 else 1.645  # 간단한 z-score

        for i in range(forecast_days):
            forecast_date = last_date + timedelta(days=i + 1)
            forecast_dates.append(forecast_date.strftime("%Y-%m-%d"))

            # 평균값 + 약간의 트렌드
            value = avg_value
            forecast_values.append(round(value, 2))

            # 신뢰구간 (시간이 지날수록 넓어짐)
            interval = z_score * std_value * (1 + i * 0.1)
            confidence_lower.append(round(max(0, value - interval), 2))
            confidence_upper.append(round(value + interval, 2))

        model_name = "MovingAverage (Fallback)"
        if error_message:
            model_name += f" - {error_message[:30]}"

        return PredictionView(
            keyword=keyword,
            historical_dates=historical_dates,
            historical_values=historical_values,
            forecast_dates=forecast_dates,
            forecast_values=forecast_values,
            confidence_lower=confidence_lower,
            confidence_upper=confidence_upper,
            model_name=model_name,
            metrics={"MAE": 0.0, "RMSE": 0.0, "MAPE": 0.0},
            confidence_level=confidence_level,
        )

    def get_available_keywords(self, limit: int = 20) -> list[str]:
        """예측 가능한 키워드 목록을 반환한다.

        Args:
            limit: 최대 키워드 수

        Returns:
            키워드 문자열 목록
        """
        top_keywords = self._trend_service.get_top_keywords(limit=limit)
        return [kw.keyword for kw in top_keywords]


# =============================================================================
# DEPENDENCY INJECTION
# =============================================================================


@lru_cache(maxsize=1)
def get_prediction_service() -> PredictionService:
    """PredictionService 싱글톤 인스턴스를 반환한다.

    Returns:
        PredictionService 인스턴스
    """
    return PredictionService()
