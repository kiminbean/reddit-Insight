"""ComparisonService 테스트.

비교 분석 서비스의 단위 테스트.
Mock을 사용하여 데이터베이스 접근 없이 테스트한다.
"""

from __future__ import annotations

import pytest
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from reddit_insight.dashboard.services.comparison_service import (
    ComparisonService,
    ComparisonView,
    SubredditMetricsView,
    get_comparison_service,
    reset_comparison_service,
)
from reddit_insight.dashboard.services.cache_service import CacheService


@dataclass
class MockAnalysisData:
    """테스트용 AnalysisData Mock."""

    subreddit: str = ""
    analyzed_at: str = ""
    post_count: int = 0
    keywords: list[dict[str, Any]] = field(default_factory=list)
    trends: list[dict[str, Any]] = field(default_factory=list)
    demands: dict[str, Any] = field(default_factory=dict)
    competition: dict[str, Any] = field(default_factory=dict)
    insights: list[dict[str, Any]] = field(default_factory=list)


@pytest.fixture
def cache() -> CacheService:
    """테스트용 CacheService를 생성한다."""
    return CacheService(default_ttl=60, max_entries=100)


@pytest.fixture
def service(cache: CacheService) -> ComparisonService:
    """테스트용 ComparisonService 인스턴스를 생성한다."""
    return ComparisonService(cache=cache)


@pytest.fixture
def python_data() -> MockAnalysisData:
    """Python 서브레딧 테스트 데이터."""
    return MockAnalysisData(
        subreddit="python",
        post_count=100,
        keywords=[
            {"keyword": "django", "score": 0.9},
            {"keyword": "fastapi", "score": 0.8},
            {"keyword": "machine learning", "score": 0.7},
        ],
        competition={
            "sentiment_summary": {
                "positive": 60,
                "neutral": 30,
                "negative": 10,
            }
        },
    )


@pytest.fixture
def javascript_data() -> MockAnalysisData:
    """JavaScript 서브레딧 테스트 데이터."""
    return MockAnalysisData(
        subreddit="javascript",
        post_count=150,
        keywords=[
            {"keyword": "react", "score": 0.95},
            {"keyword": "typescript", "score": 0.85},
            {"keyword": "machine learning", "score": 0.75},
        ],
        competition={
            "sentiment_summary": {
                "positive": 50,
                "neutral": 35,
                "negative": 15,
            }
        },
    )


class TestComparisonServiceInit:
    """ComparisonService 초기화 테스트."""

    def test_init_with_cache(self, cache: CacheService) -> None:
        """cache로 초기화할 수 있다."""
        service = ComparisonService(cache=cache)

        assert service.cache is cache

    def test_init_without_cache(self) -> None:
        """cache 없이 초기화하면 기본 캐시를 사용한다."""
        service = ComparisonService()

        assert service.cache is not None


class TestCompareSubreddits:
    """compare_subreddits 메서드 테스트."""

    @pytest.mark.asyncio
    async def test_compare_success(
        self,
        service: ComparisonService,
        python_data: MockAnalysisData,
        javascript_data: MockAnalysisData,
    ) -> None:
        """비교 분석이 성공한다."""
        with patch.object(service, "load_subreddit_data") as mock_load:

            async def side_effect(subreddit: str) -> MockAnalysisData | None:
                if subreddit == "python":
                    return python_data
                elif subreddit == "javascript":
                    return javascript_data
                return None

            mock_load.side_effect = side_effect

            result = await service.compare_subreddits(["python", "javascript"])

            assert result is not None
            assert isinstance(result, ComparisonView)
            assert len(result.subreddits) == 2
            assert "python" in result.subreddits
            assert "javascript" in result.subreddits

    @pytest.mark.asyncio
    async def test_compare_uses_cache(
        self,
        service: ComparisonService,
        python_data: MockAnalysisData,
        javascript_data: MockAnalysisData,
    ) -> None:
        """캐시된 결과를 반환한다."""
        with patch.object(service, "load_subreddit_data") as mock_load:

            async def side_effect(subreddit: str) -> MockAnalysisData | None:
                if subreddit == "python":
                    return python_data
                elif subreddit == "javascript":
                    return javascript_data
                return None

            mock_load.side_effect = side_effect

            # 첫 번째 호출
            result1 = await service.compare_subreddits(["python", "javascript"])

            # 두 번째 호출 - 캐시에서 가져옴
            result2 = await service.compare_subreddits(["python", "javascript"])

            # load_subreddit_data는 첫 번째 호출에서만 실행됨
            assert mock_load.call_count == 2  # 첫 번째: python, javascript

    @pytest.mark.asyncio
    async def test_compare_bypass_cache(
        self,
        service: ComparisonService,
        python_data: MockAnalysisData,
        javascript_data: MockAnalysisData,
    ) -> None:
        """use_cache=False로 캐시를 우회한다."""
        with patch.object(service, "load_subreddit_data") as mock_load:

            async def side_effect(subreddit: str) -> MockAnalysisData | None:
                if subreddit == "python":
                    return python_data
                elif subreddit == "javascript":
                    return javascript_data
                return None

            mock_load.side_effect = side_effect

            await service.compare_subreddits(["python", "javascript"], use_cache=True)
            await service.compare_subreddits(["python", "javascript"], use_cache=False)

            # 캐시를 우회했으므로 두 번 다 로드
            assert mock_load.call_count == 4

    @pytest.mark.asyncio
    async def test_compare_returns_none_missing_data(
        self, service: ComparisonService
    ) -> None:
        """데이터가 없으면 None을 반환한다."""
        with patch.object(service, "load_subreddit_data") as mock_load:
            mock_load.return_value = None

            result = await service.compare_subreddits(["python", "javascript"])

            assert result is None

    @pytest.mark.asyncio
    async def test_compare_validates_min_subreddits(
        self, service: ComparisonService
    ) -> None:
        """최소 2개 서브레딧이 필요하다."""
        with pytest.raises(ValueError, match="최소 2개"):
            await service.compare_subreddits(["python"])

    @pytest.mark.asyncio
    async def test_compare_validates_max_subreddits(
        self, service: ComparisonService
    ) -> None:
        """최대 5개 서브레딧까지 지원한다."""
        subreddits = [f"sub{i}" for i in range(6)]

        with pytest.raises(ValueError, match="최대 5개"):
            await service.compare_subreddits(subreddits)

    @pytest.mark.asyncio
    async def test_compare_normalizes_subreddit_names(
        self,
        service: ComparisonService,
        python_data: MockAnalysisData,
        javascript_data: MockAnalysisData,
    ) -> None:
        """서브레딧 이름을 정규화한다 (소문자, 정렬)."""
        with patch.object(service, "load_subreddit_data") as mock_load:

            async def side_effect(subreddit: str) -> MockAnalysisData | None:
                if subreddit == "python":
                    return python_data
                elif subreddit == "javascript":
                    return javascript_data
                return None

            mock_load.side_effect = side_effect

            result = await service.compare_subreddits(["PYTHON", "JavaScript"])

            assert result is not None
            # 정규화되어 저장됨
            assert "python" in result.subreddits or "PYTHON" in result.subreddits


class TestGetComparisonChartData:
    """get_comparison_chart_data 메서드 테스트."""

    def test_chart_data_structure(
        self, service: ComparisonService,
        python_data: MockAnalysisData,
        javascript_data: MockAnalysisData,
    ) -> None:
        """차트 데이터 구조가 올바르다."""
        from reddit_insight.analysis.comparison import ComparisonAnalyzer

        analyzer = ComparisonAnalyzer([python_data, javascript_data])  # type: ignore
        result = analyzer.compare()

        chart_data = service.get_comparison_chart_data(result)

        assert "activity" in chart_data
        assert "sentiment" in chart_data
        assert "heatmap" in chart_data

    def test_activity_chart_has_required_fields(
        self, service: ComparisonService,
        python_data: MockAnalysisData,
        javascript_data: MockAnalysisData,
    ) -> None:
        """활동량 차트가 필수 필드를 가진다."""
        from reddit_insight.analysis.comparison import ComparisonAnalyzer

        analyzer = ComparisonAnalyzer([python_data, javascript_data])  # type: ignore
        result = analyzer.compare()

        chart_data = service.get_comparison_chart_data(result)
        activity = chart_data["activity"]

        assert activity["type"] == "bar"
        assert "data" in activity
        assert "labels" in activity["data"]
        assert "datasets" in activity["data"]

    def test_sentiment_chart_is_stacked(
        self, service: ComparisonService,
        python_data: MockAnalysisData,
        javascript_data: MockAnalysisData,
    ) -> None:
        """감성 차트가 스택 바 차트다."""
        from reddit_insight.analysis.comparison import ComparisonAnalyzer

        analyzer = ComparisonAnalyzer([python_data, javascript_data])  # type: ignore
        result = analyzer.compare()

        chart_data = service.get_comparison_chart_data(result)
        sentiment = chart_data["sentiment"]

        assert sentiment["type"] == "bar"
        assert sentiment["options"]["scales"]["x"]["stacked"] is True
        assert sentiment["options"]["scales"]["y"]["stacked"] is True

    def test_heatmap_has_matrix(
        self, service: ComparisonService,
        python_data: MockAnalysisData,
        javascript_data: MockAnalysisData,
    ) -> None:
        """히트맵 데이터가 행렬을 가진다."""
        from reddit_insight.analysis.comparison import ComparisonAnalyzer

        analyzer = ComparisonAnalyzer([python_data, javascript_data])  # type: ignore
        result = analyzer.compare()

        chart_data = service.get_comparison_chart_data(result)
        heatmap = chart_data["heatmap"]

        assert "labels" in heatmap
        assert "matrix" in heatmap
        assert len(heatmap["matrix"]) == 2
        assert len(heatmap["matrix"][0]) == 2


class TestGetAvailableSubreddits:
    """get_available_subreddits 메서드 테스트."""

    def test_returns_subreddit_list(self, service: ComparisonService) -> None:
        """서브레딧 목록을 반환한다."""
        with patch(
            "reddit_insight.dashboard.services.comparison_service.get_all_subreddits"
        ) as mock_get:
            mock_get.return_value = ["python", "javascript", "rust"]

            result = service.get_available_subreddits()

            assert result == ["python", "javascript", "rust"]


class TestSubredditMetricsView:
    """SubredditMetricsView 테스트."""

    def test_from_metrics(self) -> None:
        """SubredditMetrics에서 SubredditMetricsView를 생성한다."""
        from reddit_insight.analysis.comparison import SubredditMetrics

        metrics = SubredditMetrics(
            subreddit="test",
            post_count=100,
            avg_score=50.5,
            avg_comments=10.3,
            top_keywords=["kw1", "kw2", "kw3"] + [f"kw{i}" for i in range(4, 15)],
            sentiment_distribution={"positive": 0.6, "neutral": 0.3, "negative": 0.1},
        )

        view = SubredditMetricsView.from_metrics(metrics)

        assert view.subreddit == "test"
        assert view.post_count == 100
        assert view.avg_score == 50.5
        assert len(view.top_keywords) == 10  # 상위 10개만


class TestComparisonView:
    """ComparisonView 테스트."""

    def test_from_result(
        self, python_data: MockAnalysisData, javascript_data: MockAnalysisData
    ) -> None:
        """ComparisonResult에서 ComparisonView를 생성한다."""
        from reddit_insight.analysis.comparison import ComparisonAnalyzer

        analyzer = ComparisonAnalyzer([python_data, javascript_data])  # type: ignore
        result = analyzer.compare()

        view = ComparisonView.from_result(result)

        assert len(view.subreddits) == 2
        assert len(view.metrics) == 2
        assert isinstance(view.common_keywords, list)
        assert isinstance(view.unique_keywords, dict)

    def test_from_result_with_chart_data(
        self, python_data: MockAnalysisData, javascript_data: MockAnalysisData
    ) -> None:
        """차트 데이터와 함께 ComparisonView를 생성한다."""
        from reddit_insight.analysis.comparison import ComparisonAnalyzer

        analyzer = ComparisonAnalyzer([python_data, javascript_data])  # type: ignore
        result = analyzer.compare()

        chart_data = {"activity": {}, "sentiment": {}}
        view = ComparisonView.from_result(result, chart_data=chart_data)

        assert view.chart_data == chart_data


class TestSingletonFactory:
    """싱글톤 팩토리 함수 테스트."""

    def test_get_comparison_service(self) -> None:
        """get_comparison_service()는 싱글톤을 반환한다."""
        reset_comparison_service()

        service1 = get_comparison_service()
        service2 = get_comparison_service()

        assert service1 is service2

        reset_comparison_service()

    def test_reset_comparison_service(self) -> None:
        """reset_comparison_service()로 싱글톤을 리셋한다."""
        reset_comparison_service()

        service1 = get_comparison_service()
        reset_comparison_service()
        service2 = get_comparison_service()

        assert service1 is not service2

        reset_comparison_service()
