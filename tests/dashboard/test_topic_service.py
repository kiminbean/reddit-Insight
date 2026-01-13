"""TopicService 단위 테스트.

TopicModeler ML 모듈을 래핑하는 토픽 서비스의 동작을 검증한다.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from reddit_insight.dashboard.data_store import AnalysisData
from reddit_insight.dashboard.services.topic_service import (
    TopicAnalysisView,
    TopicKeywordView,
    TopicService,
    TopicView,
    get_topic_service,
)


# =============================================================================
# TEST FIXTURES
# =============================================================================


@pytest.fixture
def sample_documents() -> list[str]:
    """테스트용 문서 목록을 생성한다."""
    return [
        "Python is a great programming language for data science",
        "Machine learning requires a lot of data processing",
        "JavaScript frameworks like React and Vue are popular",
        "Data analysis helps in making business decisions",
        "Python pandas library is useful for data manipulation",
        "Deep learning models need GPU for fast training",
        "Web development with JavaScript is becoming complex",
        "Data visualization with matplotlib and seaborn",
        "Natural language processing uses machine learning",
        "Frontend frameworks improve developer productivity",
        "Python is widely used in scientific computing",
        "Backend development with Node.js and Express",
    ]


@pytest.fixture
def mock_analysis_data() -> AnalysisData:
    """테스트용 분석 데이터를 생성한다."""
    return AnalysisData(
        subreddit="programming",
        analyzed_at="2024-01-01T00:00:00Z",
        post_count=100,
        keywords=[
            {"keyword": "python programming language"},
            {"keyword": "javascript web development"},
            {"keyword": "machine learning data science"},
        ],
        insights=[
            {
                "description": "Python is becoming more popular for data science",
                "evidence": [
                    "Many companies are hiring Python developers",
                    "Data science bootcamps focus on Python",
                ],
            },
            {
                "description": "JavaScript frameworks are evolving rapidly",
                "evidence": [
                    "React and Vue have large communities",
                    "New frameworks appear frequently",
                ],
            },
        ],
        demands={
            "pain_points": [
                {"text": "Python package management is confusing"},
                {"description": "JavaScript ecosystem is fragmented"},
            ],
            "feature_requests": [
                {"text": "Better debugging tools for Python"},
                {"description": "Improved TypeScript support"},
            ],
        },
        competition={
            "entities": [
                {"name": "PyCharm IDE", "mentions": ["PyCharm is great", "IDE comparison"]},
                {"name": "VS Code editor"},
            ],
            "complaints": [
                {"text": "PyCharm is slow on large projects"},
                {"text": "VS Code extensions can be buggy"},
            ],
        },
    )


@pytest.fixture
def topic_service() -> TopicService:
    """테스트용 TopicService를 생성한다."""
    return TopicService()


# =============================================================================
# TOPIC KEYWORD VIEW TESTS
# =============================================================================


class TestTopicKeywordView:
    """TopicKeywordView 데이터 클래스 테스트."""

    def test_basic_properties(self):
        """기본 속성이 올바르게 작동한다."""
        # Given
        view = TopicKeywordView(
            word="python",
            weight=0.25,
            weight_percent=25.0,
        )

        # Then
        assert view.word == "python"
        assert view.weight == 0.25
        assert view.weight_percent == 25.0


# =============================================================================
# TOPIC VIEW TESTS
# =============================================================================


class TestTopicView:
    """TopicView 데이터 클래스 테스트."""

    def test_basic_properties(self):
        """기본 속성이 올바르게 작동한다."""
        # Given
        keywords = [
            TopicKeywordView(word="python", weight=0.3, weight_percent=30.0),
            TopicKeywordView(word="data", weight=0.2, weight_percent=20.0),
        ]

        view = TopicView(
            id=0,
            label="python_data_science",
            keywords=keywords,
            coherence=0.45,
        )

        # Then
        assert view.id == 0
        assert view.label == "python_data_science"
        assert len(view.keywords) == 2
        assert view.coherence == 0.45


# =============================================================================
# TOPIC ANALYSIS VIEW TESTS
# =============================================================================


class TestTopicAnalysisView:
    """TopicAnalysisView 데이터 클래스 테스트."""

    def test_basic_properties(self):
        """기본 속성이 올바르게 작동한다."""
        # Given
        topics = [
            TopicView(
                id=0,
                label="topic_0",
                keywords=[TopicKeywordView("word1", 0.5, 50.0)],
                coherence=0.4,
            ),
            TopicView(
                id=1,
                label="topic_1",
                keywords=[TopicKeywordView("word2", 0.6, 60.0)],
                coherence=0.5,
            ),
        ]

        view = TopicAnalysisView(
            topics=topics,
            n_topics=2,
            overall_coherence=0.45,
            method="lda",
            document_count=100,
            topic_distribution=[60.0, 40.0],
        )

        # Then
        assert view.n_topics == 2
        assert view.overall_coherence == 0.45
        assert view.method == "lda"
        assert view.document_count == 100
        assert len(view.topic_distribution) == 2

    def test_to_chart_data_structure(self):
        """to_chart_data()가 올바른 구조의 데이터를 반환한다."""
        # Given
        topics = [
            TopicView(
                id=0,
                label="python_data",
                keywords=[
                    TopicKeywordView("python", 0.3, 30.0),
                    TopicKeywordView("data", 0.2, 20.0),
                ],
                coherence=0.4,
            ),
        ]

        view = TopicAnalysisView(
            topics=topics,
            n_topics=1,
            overall_coherence=0.4,
            method="lda",
            document_count=50,
            topic_distribution=[100.0],
        )

        # When
        chart_data = view.to_chart_data()

        # Then
        assert "labels" in chart_data
        assert "datasets" in chart_data
        assert "metadata" in chart_data
        assert len(chart_data["labels"]) == 1
        assert len(chart_data["datasets"]) == 1

    def test_to_chart_data_metadata(self):
        """to_chart_data()가 올바른 메타데이터를 포함한다."""
        # Given
        topics = [
            TopicView(
                id=0,
                label="topic_0",
                keywords=[TopicKeywordView("word", 0.5, 50.0)],
                coherence=0.4,
            ),
        ]

        view = TopicAnalysisView(
            topics=topics,
            n_topics=1,
            overall_coherence=0.42,
            method="nmf",
            document_count=100,
            topic_distribution=[100.0],
        )

        # When
        chart_data = view.to_chart_data()

        # Then
        metadata = chart_data["metadata"]
        assert metadata["n_topics"] == 1
        assert metadata["method"] == "nmf"
        assert metadata["overall_coherence"] == 0.42
        assert metadata["document_count"] == 100
        assert len(metadata["topics"]) == 1


# =============================================================================
# TOPIC SERVICE TESTS
# =============================================================================


class TestTopicService:
    """TopicService 테스트."""

    def test_analyze_topics_with_documents(
        self, topic_service: TopicService, sample_documents: list[str]
    ):
        """analyze_topics()가 문서 목록으로 토픽 분석을 수행한다."""
        # When
        result = topic_service.analyze_topics(
            n_topics=3, method="auto", documents=sample_documents
        )

        # Then
        assert isinstance(result, TopicAnalysisView)
        assert result.n_topics > 0
        assert result.document_count == len(sample_documents)
        assert len(result.topics) > 0

    def test_analyze_topics_n_topics_parameter(
        self, topic_service: TopicService, sample_documents: list[str]
    ):
        """n_topics 파라미터가 토픽 수를 결정한다."""
        # When
        result_3 = topic_service.analyze_topics(n_topics=3, documents=sample_documents)
        result_5 = topic_service.analyze_topics(n_topics=5, documents=sample_documents)

        # Then
        assert result_3.n_topics <= 3
        assert result_5.n_topics <= 5

    def test_analyze_topics_method_parameter(
        self, topic_service: TopicService, sample_documents: list[str]
    ):
        """method 파라미터가 토픽 모델링 방법을 결정한다."""
        # When
        result_lda = topic_service.analyze_topics(
            n_topics=3, method="lda", documents=sample_documents
        )
        result_nmf = topic_service.analyze_topics(
            n_topics=3, method="nmf", documents=sample_documents
        )

        # Then
        assert result_lda.method == "lda"
        assert result_nmf.method == "nmf"

    def test_analyze_topics_returns_keywords(
        self, topic_service: TopicService, sample_documents: list[str]
    ):
        """analyze_topics()가 토픽별 키워드를 반환한다."""
        # When
        result = topic_service.analyze_topics(n_topics=3, documents=sample_documents)

        # Then
        for topic in result.topics:
            assert len(topic.keywords) > 0
            for kw in topic.keywords:
                assert isinstance(kw.word, str)
                assert kw.weight >= 0

    def test_analyze_topics_returns_distribution(
        self, topic_service: TopicService, sample_documents: list[str]
    ):
        """analyze_topics()가 토픽 분포를 반환한다."""
        # When
        result = topic_service.analyze_topics(n_topics=3, documents=sample_documents)

        # Then
        assert len(result.topic_distribution) == result.n_topics
        # 분포 합이 대략 100%
        assert abs(sum(result.topic_distribution) - 100.0) < 1.0

    @patch("reddit_insight.dashboard.services.topic_service.get_current_data")
    def test_analyze_topics_from_stored_data(
        self,
        mock_get_current_data: MagicMock,
        topic_service: TopicService,
        mock_analysis_data: AnalysisData,
    ):
        """저장된 데이터에서 토픽 분석을 수행한다."""
        # Given
        mock_get_current_data.return_value = mock_analysis_data

        # When
        result = topic_service.analyze_topics(n_topics=3)

        # Then
        assert isinstance(result, TopicAnalysisView)
        mock_get_current_data.assert_called_once()

    @patch("reddit_insight.dashboard.services.topic_service.get_current_data")
    def test_get_available_document_count(
        self,
        mock_get_current_data: MagicMock,
        topic_service: TopicService,
        mock_analysis_data: AnalysisData,
    ):
        """get_available_document_count()가 문서 수를 반환한다."""
        # Given
        mock_get_current_data.return_value = mock_analysis_data

        # When
        count = topic_service.get_available_document_count()

        # Then
        assert count > 0


# =============================================================================
# SINGLETON TESTS
# =============================================================================


class TestTopicServiceSingleton:
    """TopicService 싱글톤 테스트."""

    def test_get_topic_service_returns_singleton(self):
        """get_topic_service()가 싱글톤 인스턴스를 반환한다."""
        # When
        service1 = get_topic_service()
        service2 = get_topic_service()

        # Then
        assert service1 is service2


# =============================================================================
# EDGE CASE TESTS
# =============================================================================


class TestTopicServiceEdgeCases:
    """TopicService 엣지 케이스 테스트."""

    def test_insufficient_documents(self, topic_service: TopicService):
        """문서가 부족할 때 빈 결과를 반환한다."""
        # Given
        short_docs = ["Only one document"]

        # When
        result = topic_service.analyze_topics(n_topics=3, documents=short_docs)

        # Then
        assert isinstance(result, TopicAnalysisView)
        assert result.n_topics == 0
        assert len(result.topics) == 0

    def test_empty_documents(self, topic_service: TopicService):
        """빈 문서 목록을 처리한다."""
        # Given
        empty_docs: list[str] = []

        # When
        result = topic_service.analyze_topics(n_topics=3, documents=empty_docs)

        # Then
        assert isinstance(result, TopicAnalysisView)
        assert result.n_topics == 0

    def test_n_topics_boundary_values(
        self, topic_service: TopicService, sample_documents: list[str]
    ):
        """토픽 수 경계값을 처리한다."""
        # When: 최소값 테스트
        result_min = topic_service.analyze_topics(n_topics=2, documents=sample_documents)
        assert result_min.n_topics >= 0

        # When: 최대값 테스트
        result_max = topic_service.analyze_topics(n_topics=10, documents=sample_documents)
        assert result_max.n_topics <= 10

        # When: 범위 미만 테스트 (2로 제한)
        result_under = topic_service.analyze_topics(n_topics=1, documents=sample_documents)
        assert result_under.n_topics >= 0

        # When: 범위 초과 테스트 (10으로 제한)
        result_over = topic_service.analyze_topics(n_topics=20, documents=sample_documents)
        assert result_over.n_topics <= 10

    @patch("reddit_insight.dashboard.services.topic_service.get_current_data")
    def test_no_stored_data(
        self, mock_get_current_data: MagicMock, topic_service: TopicService
    ):
        """저장된 데이터가 없을 때 빈 결과를 반환한다."""
        # Given
        mock_get_current_data.return_value = None

        # When
        result = topic_service.analyze_topics(n_topics=3)

        # Then
        assert isinstance(result, TopicAnalysisView)
        assert result.n_topics == 0

    def test_very_short_documents(self, topic_service: TopicService):
        """매우 짧은 문서들을 처리한다."""
        # Given: 10자 미만 문서들 (필터링됨)
        short_docs = ["hi", "hello", "yes", "no"]

        # When
        result = topic_service.analyze_topics(n_topics=2, documents=short_docs)

        # Then
        assert isinstance(result, TopicAnalysisView)
        # 짧은 문서는 필터링되어 분석 대상에서 제외됨

    def test_special_characters_in_documents(
        self, topic_service: TopicService, sample_documents: list[str]
    ):
        """특수 문자가 포함된 문서를 처리한다."""
        # Given
        docs_with_special = sample_documents + [
            "C++ is a powerful language!!! @#$%",
            "Use python3.11 for better performance...",
        ]

        # When
        result = topic_service.analyze_topics(n_topics=3, documents=docs_with_special)

        # Then
        assert isinstance(result, TopicAnalysisView)
        assert result.n_topics > 0
