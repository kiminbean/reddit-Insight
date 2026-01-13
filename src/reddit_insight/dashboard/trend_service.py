"""트렌드 데이터 서비스.

트렌드 분석 모듈과 대시보드 UI를 연결하여 키워드 트렌드 데이터를 제공한다.
"""

import random
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from reddit_insight.dashboard.data_store import get_current_data


@dataclass
class KeywordTrend:
    """키워드 트렌드 데이터.

    Attributes:
        keyword: 키워드
        frequency: 출현 빈도
        trend_direction: 트렌드 방향 (up/down/stable)
        change_percent: 변화율 (%)
    """

    keyword: str
    frequency: int
    trend_direction: str  # 'up', 'down', 'stable'
    change_percent: float


@dataclass
class RisingKeyword:
    """급상승 키워드 데이터.

    Attributes:
        keyword: 키워드
        rising_score: 급상승 점수 (0.0 ~ 1.0)
        first_seen: 최초 발견일
        growth_rate: 성장률 (%)
    """

    keyword: str
    rising_score: float
    first_seen: datetime | None
    growth_rate: float


@dataclass
class TimelinePoint:
    """타임라인 데이터 포인트.

    Attributes:
        date: 날짜
        count: 해당 날짜의 출현 횟수
    """

    date: date
    count: int


class TrendService:
    """트렌드 데이터 서비스.

    트렌드 분석 모듈에서 데이터를 가져와 대시보드에 필요한 형태로 변환한다.
    현재는 샘플 데이터를 반환하며, 추후 실제 분석 모듈과 연동된다.
    """

    def __init__(self) -> None:
        """TrendService를 초기화한다."""
        # 샘플 데이터를 위한 키워드 목록
        self._sample_keywords = [
            "python", "javascript", "rust", "golang", "typescript",
            "react", "vue", "svelte", "nextjs", "fastapi",
            "docker", "kubernetes", "aws", "gcp", "azure",
            "machine learning", "deep learning", "llm", "chatgpt", "ai",
            "startup", "saas", "microservices", "api", "database",
        ]

    def get_top_keywords(
        self,
        subreddit: str | None = None,
        days: int = 7,
        limit: int = 20,
    ) -> list[KeywordTrend]:
        """상위 키워드 트렌드를 반환한다.

        Args:
            subreddit: 필터링할 서브레딧 (None이면 전체)
            days: 분석 기간
            limit: 반환할 최대 키워드 수

        Returns:
            list[KeywordTrend]: 빈도순으로 정렬된 키워드 트렌드 목록
        """
        # 실제 데이터 사용 시도
        data = get_current_data()
        if data and data.keywords:
            keywords = []
            # 트렌드 정보와 매칭
            trend_map = {t["keyword"]: t for t in data.trends} if data.trends else {}

            for i, kw_data in enumerate(data.keywords[:limit]):
                keyword = kw_data["keyword"]
                frequency = int(kw_data.get("frequency", 0) or (100 - i * 3))

                # 트렌드 정보 가져오기
                trend_info = trend_map.get(keyword, {})
                direction = trend_info.get("direction", "stable")
                change_rate = trend_info.get("change_rate", 0)

                if direction == "rising":
                    trend_direction = "up"
                elif direction == "falling":
                    trend_direction = "down"
                else:
                    trend_direction = "stable"

                keywords.append(
                    KeywordTrend(
                        keyword=keyword,
                        frequency=frequency,
                        trend_direction=trend_direction,
                        change_percent=round(change_rate * 100, 1),
                    )
                )
            return keywords

        # 실제 데이터가 없으면 샘플 데이터 생성
        keywords = []
        for i, kw in enumerate(self._sample_keywords[:limit]):
            base_freq = 1000 - (i * 40)
            frequency = max(base_freq + random.randint(-50, 50), 10)

            direction_choice = random.random()
            if direction_choice < 0.4:
                trend_direction = "up"
                change_percent = random.uniform(5, 50)
            elif direction_choice < 0.7:
                trend_direction = "down"
                change_percent = -random.uniform(5, 30)
            else:
                trend_direction = "stable"
                change_percent = random.uniform(-5, 5)

            keywords.append(
                KeywordTrend(
                    keyword=kw,
                    frequency=frequency,
                    trend_direction=trend_direction,
                    change_percent=round(change_percent, 1),
                )
            )

        return keywords

    def get_rising_keywords(
        self,
        subreddit: str | None = None,
        limit: int = 20,
    ) -> list[RisingKeyword]:
        """급상승 키워드를 반환한다.

        Args:
            subreddit: 필터링할 서브레딧 (None이면 전체)
            limit: 반환할 최대 키워드 수

        Returns:
            list[RisingKeyword]: 급상승 점수순으로 정렬된 키워드 목록
        """
        # 실제 데이터에서 상승 트렌드 키워드 추출
        data = get_current_data()
        if data and data.trends:
            keywords = []
            rising_trends = [
                t for t in data.trends
                if t.get("direction") == "rising"
            ]
            # 변화율 기준 정렬
            rising_trends.sort(key=lambda x: x.get("change_rate", 0), reverse=True)

            for i, trend in enumerate(rising_trends[:limit]):
                change_rate = trend.get("change_rate", 0)
                rising_score = min(1.0, max(0.1, change_rate / 10))

                keywords.append(
                    RisingKeyword(
                        keyword=trend["keyword"],
                        rising_score=round(rising_score, 2),
                        first_seen=None,
                        growth_rate=round(change_rate * 100, 1),
                    )
                )

            if keywords:
                return keywords

        # 실제 데이터가 없으면 샘플 데이터 생성
        rising_candidates = [
            "claude", "gemini", "copilot", "cursor", "windsurf",
            "bun", "deno", "htmx", "astro", "qwik",
            "langchain", "llamaindex", "openai", "anthropic", "mistral",
            "vercel", "supabase", "planetscale", "neon", "turso",
        ]

        keywords = []
        for i, kw in enumerate(rising_candidates[:limit]):
            # 순위에 따라 점수 감소
            rising_score = max(1.0 - (i * 0.05), 0.1)
            growth_rate = rising_score * 100 + random.uniform(0, 50)

            # 최근 발견일 생성
            days_ago = random.randint(1, 14)
            first_seen = datetime.now() - timedelta(days=days_ago)

            keywords.append(
                RisingKeyword(
                    keyword=kw,
                    rising_score=round(rising_score, 2),
                    first_seen=first_seen,
                    growth_rate=round(growth_rate, 1),
                )
            )

        return keywords

    def get_keyword_timeline(
        self,
        keyword: str,
        days: int = 7,
    ) -> list[TimelinePoint]:
        """키워드의 일별 타임라인을 반환한다.

        Args:
            keyword: 조회할 키워드
            days: 분석 기간

        Returns:
            list[TimelinePoint]: 날짜순으로 정렬된 타임라인 데이터
        """
        # 샘플 데이터 생성 (추후 실제 데이터 연동)
        timeline = []
        today = date.today()

        # 기본 베이스라인 설정
        base_count = random.randint(50, 200)

        for i in range(days):
            point_date = today - timedelta(days=days - 1 - i)

            # 약간의 변동을 주면서 전반적으로 증가/감소 트렌드 시뮬레이션
            trend_factor = 1 + (i / days) * 0.3  # 시간이 지날수록 증가
            noise = random.uniform(0.8, 1.2)
            count = int(base_count * trend_factor * noise)

            timeline.append(TimelinePoint(date=point_date, count=count))

        return timeline


# 싱글톤 인스턴스 (추후 의존성 주입으로 변경 가능)
_trend_service: TrendService | None = None


def get_trend_service() -> TrendService:
    """TrendService 싱글톤 인스턴스를 반환한다.

    Returns:
        TrendService: 트렌드 서비스 인스턴스
    """
    global _trend_service
    if _trend_service is None:
        _trend_service = TrendService()
    return _trend_service
