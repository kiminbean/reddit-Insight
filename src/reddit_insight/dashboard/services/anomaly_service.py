"""이상 탐지 서비스.

AnomalyDetector ML 모듈을 래핑하여 대시보드용 이상 탐지 데이터를 제공한다.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any

from reddit_insight.analysis.ml import AnomalyDetector, AnomalyDetectorConfig
from reddit_insight.analysis.time_series import TimeGranularity, TimePoint, TimeSeries
from reddit_insight.dashboard.trend_service import TrendService, get_trend_service


@dataclass
class AnomalyPointView:
    """이상 포인트 뷰 데이터.

    Attributes:
        date: 날짜 (문자열)
        value: 관측값
        score: 이상 점수 (높을수록 이상)
        is_anomaly: 이상 여부
        expected_value: 예상값
        deviation: 편차
    """

    date: str
    value: float
    score: float
    is_anomaly: bool
    expected_value: float | None = None
    deviation: float | None = None


@dataclass
class AnomalyView:
    """이상 탐지 결과 뷰 데이터.

    대시보드에서 이상 탐지 차트를 표시하기 위한 데이터 구조.

    Attributes:
        keyword: 분석 대상 키워드
        dates: 날짜 목록
        values: 값 목록
        is_anomaly: 각 포인트의 이상 여부 목록
        anomaly_points: 이상 포인트 상세 정보 목록
        anomaly_count: 이상 포인트 개수
        total_points: 전체 포인트 개수
        method: 사용된 탐지 방법
        threshold: 사용된 임계값
    """

    keyword: str
    dates: list[str]
    values: list[float]
    is_anomaly: list[bool]
    anomaly_points: list[AnomalyPointView]
    anomaly_count: int
    total_points: int
    method: str = "auto"
    threshold: float = 3.0

    @property
    def anomaly_rate(self) -> float:
        """이상 비율을 반환한다."""
        if self.total_points == 0:
            return 0.0
        return self.anomaly_count / self.total_points

    @property
    def anomaly_rate_percent(self) -> float:
        """이상 비율을 백분율로 반환한다."""
        return round(self.anomaly_rate * 100, 1)

    def to_chart_data(self) -> dict[str, Any]:
        """Chart.js 형식의 데이터로 변환한다.

        Returns:
            Chart.js에서 사용할 수 있는 데이터 딕셔너리
        """
        # 정상 포인트와 이상 포인트 분리
        normal_data = []
        anomaly_data = []
        anomaly_indices = []

        for i, (value, is_anom) in enumerate(zip(self.values, self.is_anomaly)):
            if is_anom:
                normal_data.append(None)
                anomaly_data.append(value)
                anomaly_indices.append(i)
            else:
                normal_data.append(value)
                anomaly_data.append(None)

        return {
            "labels": self.dates,
            "datasets": [
                {
                    "label": f"{self.keyword} (Normal)",
                    "data": normal_data,
                    "borderColor": "rgb(59, 130, 246)",
                    "backgroundColor": "rgba(59, 130, 246, 0.1)",
                    "fill": True,
                    "tension": 0.3,
                    "pointRadius": 3,
                    "spanGaps": True,
                },
                {
                    "label": f"{self.keyword} (Anomaly)",
                    "data": anomaly_data,
                    "borderColor": "rgb(239, 68, 68)",
                    "backgroundColor": "rgba(239, 68, 68, 0.8)",
                    "fill": False,
                    "tension": 0,
                    "pointRadius": 8,
                    "pointStyle": "circle",
                    "showLine": False,
                },
            ],
            "metadata": {
                "keyword": self.keyword,
                "method": self.method,
                "threshold": self.threshold,
                "anomaly_count": self.anomaly_count,
                "total_points": self.total_points,
                "anomaly_rate": self.anomaly_rate_percent,
                "anomaly_indices": anomaly_indices,
                "anomaly_details": [
                    {
                        "date": ap.date,
                        "value": ap.value,
                        "score": round(ap.score, 2),
                        "expected": round(ap.expected_value, 2) if ap.expected_value else None,
                        "deviation": round(ap.deviation, 2) if ap.deviation else None,
                    }
                    for ap in self.anomaly_points
                ],
            },
        }


class AnomalyService:
    """이상 탐지 서비스.

    AnomalyDetector를 래핑하여 대시보드에서 사용할 수 있는 형태로 데이터를 제공한다.

    Example:
        >>> service = AnomalyService()
        >>> result = service.detect_anomalies("python", days=30)
        >>> chart_data = result.to_chart_data()
    """

    def __init__(
        self,
        trend_service: TrendService | None = None,
        detector_config: AnomalyDetectorConfig | None = None,
    ) -> None:
        """서비스를 초기화한다.

        Args:
            trend_service: 트렌드 데이터를 가져올 서비스 (기본: 싱글톤)
            detector_config: AnomalyDetector 설정 (기본: 자동 선택)
        """
        self._trend_service = trend_service or get_trend_service()
        self._default_config = detector_config or AnomalyDetectorConfig(
            method="auto",
            threshold=3.0,
            contamination=0.1,
            min_data_points=10,
        )

    def detect_anomalies(
        self,
        keyword: str,
        days: int = 30,
        method: str = "auto",
        threshold: float = 3.0,
    ) -> AnomalyView:
        """키워드 시계열에서 이상 포인트를 탐지한다.

        Args:
            keyword: 분석할 키워드
            days: 분석 기간 (7-90일)
            method: 탐지 방법 ("auto", "zscore", "iqr", "isolation_forest")
            threshold: 이상 판정 임계값 (z-score 방법에서 사용)

        Returns:
            AnomalyView: 이상 탐지 결과 뷰 데이터

        Raises:
            ValueError: 잘못된 파라미터
        """
        # 파라미터 검증
        days = max(7, min(90, days))
        threshold = max(1.0, min(5.0, threshold))

        # TrendService에서 과거 데이터 가져오기
        timeline = self._trend_service.get_keyword_timeline(
            keyword=keyword,
            days=days,
        )

        if len(timeline) < self._default_config.min_data_points:
            # 데이터 부족 시 기본 결과 반환
            return self._create_empty_result(
                keyword=keyword,
                timeline=timeline,
                method=method,
                threshold=threshold,
            )

        # TimeSeries 객체 생성
        time_series = self._create_time_series(keyword, timeline)

        # AnomalyDetector로 탐지 수행
        config = AnomalyDetectorConfig(
            method=method,  # type: ignore[arg-type]
            threshold=threshold,
            contamination=self._default_config.contamination,
            min_data_points=self._default_config.min_data_points,
        )
        detector = AnomalyDetector(config)

        try:
            result = detector.detect(time_series)

            # AnomalyView로 변환
            anomaly_points = []
            is_anomaly_list = []
            dates = [str(point.date) for point in timeline]
            values = [float(point.count) for point in timeline]

            for ap in result.anomalies:
                is_anomaly_list.append(ap.is_anomaly)
                if ap.is_anomaly:
                    # 해당 인덱스의 날짜 찾기
                    idx = result.anomalies.index(ap)
                    anomaly_points.append(
                        AnomalyPointView(
                            date=dates[idx] if idx < len(dates) else ap.timestamp.strftime("%Y-%m-%d"),
                            value=ap.value,
                            score=ap.anomaly_score,
                            is_anomaly=True,
                            expected_value=ap.expected_value,
                            deviation=ap.deviation,
                        )
                    )

            return AnomalyView(
                keyword=keyword,
                dates=dates,
                values=values,
                is_anomaly=is_anomaly_list,
                anomaly_points=anomaly_points,
                anomaly_count=result.anomaly_count,
                total_points=result.total_points,
                method=result.method,
                threshold=result.threshold,
            )
        except Exception as e:
            # 탐지 실패 시 빈 결과 반환
            return self._create_empty_result(
                keyword=keyword,
                timeline=timeline,
                method=method,
                threshold=threshold,
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

    def _create_empty_result(
        self,
        keyword: str,
        timeline: list,
        method: str,
        threshold: float,
        error_message: str | None = None,
    ) -> AnomalyView:
        """데이터 부족 또는 탐지 실패 시 빈 결과를 생성한다.

        Args:
            keyword: 키워드
            timeline: 과거 타임라인 데이터
            method: 탐지 방법
            threshold: 임계값
            error_message: 에러 메시지 (있는 경우)

        Returns:
            AnomalyView with empty anomalies
        """
        dates = [str(point.date) for point in timeline]
        values = [float(point.count) for point in timeline]
        is_anomaly = [False] * len(timeline)

        method_name = method
        if error_message:
            method_name = f"{method} (Error: {error_message[:30]})"

        return AnomalyView(
            keyword=keyword,
            dates=dates,
            values=values,
            is_anomaly=is_anomaly,
            anomaly_points=[],
            anomaly_count=0,
            total_points=len(timeline),
            method=method_name,
            threshold=threshold,
        )

    def get_available_keywords(self, limit: int = 20) -> list[str]:
        """분석 가능한 키워드 목록을 반환한다.

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
def get_anomaly_service() -> AnomalyService:
    """AnomalyService 싱글톤 인스턴스를 반환한다.

    Returns:
        AnomalyService 인스턴스
    """
    return AnomalyService()
