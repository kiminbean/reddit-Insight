"""ComparisonAnalyzer 테스트.

서브레딧 비교 분석기의 단위 테스트.
"""

from __future__ import annotations

import pytest
from dataclasses import dataclass, field
from typing import Any

from reddit_insight.analysis.comparison import (
    ComparisonAnalyzer,
    ComparisonResult,
    SubredditMetrics,
    compare_subreddits,
)


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
def python_data() -> MockAnalysisData:
    """Python 서브레딧 테스트 데이터."""
    return MockAnalysisData(
        subreddit="python",
        post_count=100,
        keywords=[
            {"keyword": "django", "score": 0.9},
            {"keyword": "fastapi", "score": 0.8},
            {"keyword": "machine learning", "score": 0.7},
            {"keyword": "web development", "score": 0.6},
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
            {"keyword": "web development", "score": 0.75},
            {"keyword": "node", "score": 0.65},
        ],
        competition={
            "sentiment_summary": {
                "positive": 50,
                "neutral": 35,
                "negative": 15,
            }
        },
    )


@pytest.fixture
def rust_data() -> MockAnalysisData:
    """Rust 서브레딧 테스트 데이터."""
    return MockAnalysisData(
        subreddit="rust",
        post_count=80,
        keywords=[
            {"keyword": "memory safety", "score": 0.9},
            {"keyword": "cargo", "score": 0.85},
            {"keyword": "machine learning", "score": 0.7},
            {"keyword": "systems programming", "score": 0.65},
        ],
        competition={
            "sentiment_summary": {
                "positive": 70,
                "neutral": 20,
                "negative": 10,
            }
        },
    )


class TestComparisonAnalyzerInit:
    """ComparisonAnalyzer 초기화 테스트."""

    def test_init_with_two_sources(
        self, python_data: MockAnalysisData, javascript_data: MockAnalysisData
    ) -> None:
        """2개 데이터 소스로 초기화할 수 있다."""
        analyzer = ComparisonAnalyzer([python_data, javascript_data])  # type: ignore
        assert len(analyzer.data_sources) == 2

    def test_init_with_five_sources(self, python_data: MockAnalysisData) -> None:
        """5개 데이터 소스로 초기화할 수 있다."""
        sources = [
            MockAnalysisData(subreddit=f"sub{i}", post_count=i * 10)
            for i in range(5)
        ]
        analyzer = ComparisonAnalyzer(sources)  # type: ignore
        assert len(analyzer.data_sources) == 5

    def test_init_fails_with_one_source(self, python_data: MockAnalysisData) -> None:
        """1개 데이터 소스로는 초기화할 수 없다."""
        with pytest.raises(ValueError, match="최소 2개"):
            ComparisonAnalyzer([python_data])  # type: ignore

    def test_init_fails_with_six_sources(self) -> None:
        """6개 이상 데이터 소스로는 초기화할 수 없다."""
        sources = [MockAnalysisData(subreddit=f"sub{i}") for i in range(6)]
        with pytest.raises(ValueError, match="최대 5개"):
            ComparisonAnalyzer(sources)  # type: ignore


class TestCompare:
    """compare 메서드 테스트."""

    def test_compare_returns_result(
        self, python_data: MockAnalysisData, javascript_data: MockAnalysisData
    ) -> None:
        """compare()는 ComparisonResult를 반환한다."""
        analyzer = ComparisonAnalyzer([python_data, javascript_data])  # type: ignore
        result = analyzer.compare()

        assert isinstance(result, ComparisonResult)
        assert len(result.subreddits) == 2
        assert "python" in result.subreddits
        assert "javascript" in result.subreddits

    def test_compare_extracts_metrics(
        self, python_data: MockAnalysisData, javascript_data: MockAnalysisData
    ) -> None:
        """compare()는 각 서브레딧의 메트릭을 추출한다."""
        analyzer = ComparisonAnalyzer([python_data, javascript_data])  # type: ignore
        result = analyzer.compare()

        assert len(result.metrics) == 2

        python_metrics = next(m for m in result.metrics if m.subreddit == "python")
        assert python_metrics.post_count == 100
        assert len(python_metrics.top_keywords) == 4

    def test_compare_finds_common_keywords(
        self, python_data: MockAnalysisData, javascript_data: MockAnalysisData
    ) -> None:
        """compare()는 공통 키워드를 찾는다."""
        analyzer = ComparisonAnalyzer([python_data, javascript_data])  # type: ignore
        result = analyzer.compare()

        # 'web development'이 공통 키워드
        assert "web development" in result.common_keywords

    def test_compare_finds_unique_keywords(
        self, python_data: MockAnalysisData, javascript_data: MockAnalysisData
    ) -> None:
        """compare()는 고유 키워드를 찾는다."""
        analyzer = ComparisonAnalyzer([python_data, javascript_data])  # type: ignore
        result = analyzer.compare()

        # python의 고유 키워드
        assert "django" in result.unique_keywords.get("python", [])
        assert "fastapi" in result.unique_keywords.get("python", [])

        # javascript의 고유 키워드
        assert "react" in result.unique_keywords.get("javascript", [])
        assert "typescript" in result.unique_keywords.get("javascript", [])


class TestKeywordOverlap:
    """키워드 오버랩 테스트."""

    def test_overlap_matrix_dimensions(
        self, python_data: MockAnalysisData, javascript_data: MockAnalysisData
    ) -> None:
        """오버랩 행렬은 NxN 차원이다."""
        analyzer = ComparisonAnalyzer([python_data, javascript_data])  # type: ignore
        result = analyzer.compare()

        assert len(result.keyword_overlap_matrix) == 2
        assert len(result.keyword_overlap_matrix[0]) == 2
        assert len(result.keyword_overlap_matrix[1]) == 2

    def test_diagonal_is_one(
        self, python_data: MockAnalysisData, javascript_data: MockAnalysisData
    ) -> None:
        """대각선 값은 1.0이다 (자기 자신과의 유사도)."""
        analyzer = ComparisonAnalyzer([python_data, javascript_data])  # type: ignore
        result = analyzer.compare()

        assert result.keyword_overlap_matrix[0][0] == 1.0
        assert result.keyword_overlap_matrix[1][1] == 1.0

    def test_symmetric_matrix(
        self, python_data: MockAnalysisData, javascript_data: MockAnalysisData
    ) -> None:
        """오버랩 행렬은 대칭이다."""
        analyzer = ComparisonAnalyzer([python_data, javascript_data])  # type: ignore
        result = analyzer.compare()

        assert result.keyword_overlap_matrix[0][1] == result.keyword_overlap_matrix[1][0]

    def test_overlap_value_range(
        self,
        python_data: MockAnalysisData,
        javascript_data: MockAnalysisData,
        rust_data: MockAnalysisData,
    ) -> None:
        """오버랩 값은 0~1 범위다."""
        analyzer = ComparisonAnalyzer([python_data, javascript_data, rust_data])  # type: ignore
        result = analyzer.compare()

        for row in result.keyword_overlap_matrix:
            for value in row:
                assert 0.0 <= value <= 1.0


class TestCommonKeywords:
    """공통 키워드 테스트."""

    def test_find_keywords_in_all(
        self,
        python_data: MockAnalysisData,
        javascript_data: MockAnalysisData,
        rust_data: MockAnalysisData,
    ) -> None:
        """모든 서브레딧에 나타나는 키워드를 찾는다."""
        # python, rust에 machine learning 있음
        analyzer = ComparisonAnalyzer([python_data, rust_data])  # type: ignore
        result = analyzer.compare()

        # machine learning은 둘 다 있음
        assert "machine learning" in result.common_keywords

    def test_min_overlap_parameter(
        self,
        python_data: MockAnalysisData,
        javascript_data: MockAnalysisData,
        rust_data: MockAnalysisData,
    ) -> None:
        """min_overlap 파라미터로 최소 등장 횟수를 조절한다."""
        analyzer = ComparisonAnalyzer([python_data, javascript_data, rust_data])  # type: ignore
        analyzer.compare()

        # min_overlap=3이면 3개 모두에 나타나야 함
        common_all = analyzer.find_common_keywords(min_overlap=3)

        # web development은 python, javascript에만 있음
        assert "web development" not in common_all


class TestUniqueKeywords:
    """고유 키워드 테스트."""

    def test_unique_not_in_others(
        self, python_data: MockAnalysisData, javascript_data: MockAnalysisData
    ) -> None:
        """고유 키워드는 다른 서브레딧에 없다."""
        analyzer = ComparisonAnalyzer([python_data, javascript_data])  # type: ignore
        result = analyzer.compare()

        # python 고유 키워드가 javascript에 없음 확인
        python_unique = set(result.unique_keywords.get("python", []))
        js_keywords = set(k.lower() for k in result.metrics[1].top_keywords)

        for kw in python_unique:
            assert kw.lower() not in js_keywords

    def test_empty_unique_when_all_shared(self) -> None:
        """모든 키워드가 공유되면 고유 키워드는 비어 있다."""
        data1 = MockAnalysisData(
            subreddit="sub1",
            keywords=[{"keyword": "shared1"}, {"keyword": "shared2"}],
        )
        data2 = MockAnalysisData(
            subreddit="sub2",
            keywords=[{"keyword": "shared1"}, {"keyword": "shared2"}],
        )

        analyzer = ComparisonAnalyzer([data1, data2])  # type: ignore
        result = analyzer.compare()

        assert result.unique_keywords.get("sub1", []) == []
        assert result.unique_keywords.get("sub2", []) == []


class TestSentimentComparison:
    """감성 비교 테스트."""

    def test_sentiment_for_each_subreddit(
        self, python_data: MockAnalysisData, javascript_data: MockAnalysisData
    ) -> None:
        """각 서브레딧의 감성 분포를 포함한다."""
        analyzer = ComparisonAnalyzer([python_data, javascript_data])  # type: ignore
        result = analyzer.compare()

        assert "python" in result.sentiment_comparison
        assert "javascript" in result.sentiment_comparison

        python_sentiment = result.sentiment_comparison["python"]
        assert "positive" in python_sentiment
        assert "neutral" in python_sentiment
        assert "negative" in python_sentiment

    def test_sentiment_values_sum_to_one(
        self, python_data: MockAnalysisData, javascript_data: MockAnalysisData
    ) -> None:
        """감성 분포 값의 합은 1이다."""
        analyzer = ComparisonAnalyzer([python_data, javascript_data])  # type: ignore
        result = analyzer.compare()

        for subreddit, sentiment in result.sentiment_comparison.items():
            total = sum(sentiment.values())
            assert abs(total - 1.0) < 0.01, f"{subreddit}: {total}"


class TestSubredditMetrics:
    """SubredditMetrics 테스트."""

    def test_to_dict(self) -> None:
        """to_dict()는 딕셔너리를 반환한다."""
        metrics = SubredditMetrics(
            subreddit="test",
            post_count=100,
            avg_score=50.5,
            avg_comments=10.3,
            top_keywords=["python", "django"],
            sentiment_distribution={"positive": 0.6, "neutral": 0.3, "negative": 0.1},
        )

        d = metrics.to_dict()

        assert d["subreddit"] == "test"
        assert d["post_count"] == 100
        assert d["avg_score"] == 50.5
        assert d["top_keywords"] == ["python", "django"]
        assert d["sentiment_distribution"]["positive"] == 0.6


class TestComparisonResult:
    """ComparisonResult 테스트."""

    def test_to_dict(
        self, python_data: MockAnalysisData, javascript_data: MockAnalysisData
    ) -> None:
        """to_dict()는 딕셔너리를 반환한다."""
        analyzer = ComparisonAnalyzer([python_data, javascript_data])  # type: ignore
        result = analyzer.compare()

        d = result.to_dict()

        assert isinstance(d, dict)
        assert "subreddits" in d
        assert "metrics" in d
        assert "common_keywords" in d
        assert "unique_keywords" in d
        assert "keyword_overlap_matrix" in d
        assert "sentiment_comparison" in d


class TestHelperFunction:
    """헬퍼 함수 테스트."""

    def test_compare_subreddits(
        self, python_data: MockAnalysisData, javascript_data: MockAnalysisData
    ) -> None:
        """compare_subreddits()는 비교 결과를 반환한다."""
        result = compare_subreddits([python_data, javascript_data])  # type: ignore

        assert isinstance(result, ComparisonResult)
        assert len(result.subreddits) == 2
