"""ClusterService 단위 테스트.

TextClusterer ML 모듈을 래핑하는 클러스터 서비스의 동작을 검증한다.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from reddit_insight.dashboard.data_store import AnalysisData
from reddit_insight.dashboard.services.cluster_service import (
    ClusterAnalysisView,
    ClusterKeywordView,
    ClusterService,
    ClusterView,
    get_cluster_service,
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
def cluster_service() -> ClusterService:
    """테스트용 ClusterService를 생성한다."""
    return ClusterService()


# =============================================================================
# CLUSTER KEYWORD VIEW TESTS
# =============================================================================


class TestClusterKeywordView:
    """ClusterKeywordView 데이터 클래스 테스트."""

    def test_basic_properties(self):
        """기본 속성이 올바르게 작동한다."""
        # Given
        view = ClusterKeywordView(word="python", rank=1)

        # Then
        assert view.word == "python"
        assert view.rank == 1


# =============================================================================
# CLUSTER VIEW TESTS
# =============================================================================


class TestClusterView:
    """ClusterView 데이터 클래스 테스트."""

    def test_basic_properties(self):
        """기본 속성이 올바르게 작동한다."""
        # Given
        keywords = [
            ClusterKeywordView(word="python", rank=1),
            ClusterKeywordView(word="data", rank=2),
        ]

        view = ClusterView(
            id=0,
            label="python_data_science",
            size=10,
            keywords=keywords,
            sample_docs=["Sample document 1", "Sample document 2"],
            percentage=25.0,
        )

        # Then
        assert view.id == 0
        assert view.label == "python_data_science"
        assert view.size == 10
        assert len(view.keywords) == 2
        assert len(view.sample_docs) == 2
        assert view.percentage == 25.0


# =============================================================================
# CLUSTER ANALYSIS VIEW TESTS
# =============================================================================


class TestClusterAnalysisView:
    """ClusterAnalysisView 데이터 클래스 테스트."""

    def test_basic_properties(self):
        """기본 속성이 올바르게 작동한다."""
        # Given
        clusters = [
            ClusterView(
                id=0,
                label="cluster_0",
                size=30,
                keywords=[ClusterKeywordView("word1", 1)],
                sample_docs=["doc1"],
                percentage=60.0,
            ),
            ClusterView(
                id=1,
                label="cluster_1",
                size=20,
                keywords=[ClusterKeywordView("word2", 1)],
                sample_docs=["doc2"],
                percentage=40.0,
            ),
        ]

        view = ClusterAnalysisView(
            clusters=clusters,
            n_clusters=2,
            silhouette_score=0.45,
            method="kmeans",
            document_count=50,
            cluster_sizes=[30, 20],
        )

        # Then
        assert view.n_clusters == 2
        assert view.silhouette_score == 0.45
        assert view.method == "kmeans"
        assert view.document_count == 50
        assert len(view.cluster_sizes) == 2

    def test_to_chart_data_structure(self):
        """to_chart_data()가 올바른 구조의 데이터를 반환한다."""
        # Given
        clusters = [
            ClusterView(
                id=0,
                label="python_data",
                size=25,
                keywords=[
                    ClusterKeywordView("python", 1),
                    ClusterKeywordView("data", 2),
                ],
                sample_docs=["Sample doc"],
                percentage=50.0,
            ),
        ]

        view = ClusterAnalysisView(
            clusters=clusters,
            n_clusters=1,
            silhouette_score=0.4,
            method="kmeans",
            document_count=50,
            cluster_sizes=[25],
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
        clusters = [
            ClusterView(
                id=0,
                label="cluster_0",
                size=50,
                keywords=[ClusterKeywordView("word", 1)],
                sample_docs=[],
                percentage=100.0,
            ),
        ]

        view = ClusterAnalysisView(
            clusters=clusters,
            n_clusters=1,
            silhouette_score=0.42,
            method="agglomerative",
            document_count=50,
            cluster_sizes=[50],
        )

        # When
        chart_data = view.to_chart_data()

        # Then
        metadata = chart_data["metadata"]
        assert metadata["n_clusters"] == 1
        assert metadata["method"] == "agglomerative"
        assert metadata["silhouette_score"] == 0.42
        assert metadata["document_count"] == 50
        assert len(metadata["clusters"]) == 1


# =============================================================================
# CLUSTER SERVICE TESTS
# =============================================================================


class TestClusterService:
    """ClusterService 테스트."""

    def test_cluster_documents_with_documents(
        self, cluster_service: ClusterService, sample_documents: list[str]
    ):
        """cluster_documents()가 문서 목록으로 클러스터링을 수행한다."""
        # When
        result = cluster_service.cluster_documents(
            n_clusters=3, method="auto", documents=sample_documents
        )

        # Then
        assert isinstance(result, ClusterAnalysisView)
        assert result.n_clusters > 0
        assert result.document_count == len(sample_documents)
        assert len(result.clusters) > 0

    def test_cluster_documents_n_clusters_parameter(
        self, cluster_service: ClusterService, sample_documents: list[str]
    ):
        """n_clusters 파라미터가 클러스터 수를 결정한다."""
        # When
        result_3 = cluster_service.cluster_documents(n_clusters=3, documents=sample_documents)
        result_5 = cluster_service.cluster_documents(n_clusters=5, documents=sample_documents)

        # Then
        assert result_3.n_clusters <= 3
        assert result_5.n_clusters <= 5

    def test_cluster_documents_auto_clusters(
        self, cluster_service: ClusterService, sample_documents: list[str]
    ):
        """n_clusters=None일 때 자동으로 클러스터 수를 선택한다."""
        # When
        result = cluster_service.cluster_documents(
            n_clusters=None, documents=sample_documents
        )

        # Then
        assert isinstance(result, ClusterAnalysisView)
        assert result.n_clusters > 0

    def test_cluster_documents_method_parameter(
        self, cluster_service: ClusterService, sample_documents: list[str]
    ):
        """method 파라미터가 클러스터링 방법을 결정한다."""
        # When
        result_kmeans = cluster_service.cluster_documents(
            n_clusters=3, method="kmeans", documents=sample_documents
        )
        result_agg = cluster_service.cluster_documents(
            n_clusters=3, method="agglomerative", documents=sample_documents
        )

        # Then
        assert result_kmeans.method == "kmeans"
        assert result_agg.method == "agglomerative"

    def test_cluster_documents_returns_keywords(
        self, cluster_service: ClusterService, sample_documents: list[str]
    ):
        """cluster_documents()가 클러스터별 키워드를 반환한다."""
        # When
        result = cluster_service.cluster_documents(n_clusters=3, documents=sample_documents)

        # Then
        for cluster in result.clusters:
            assert len(cluster.keywords) > 0
            for kw in cluster.keywords:
                assert isinstance(kw.word, str)
                assert kw.rank >= 1

    def test_cluster_documents_returns_sizes(
        self, cluster_service: ClusterService, sample_documents: list[str]
    ):
        """cluster_documents()가 클러스터 크기를 반환한다."""
        # When
        result = cluster_service.cluster_documents(n_clusters=3, documents=sample_documents)

        # Then
        assert len(result.cluster_sizes) == result.n_clusters
        assert sum(result.cluster_sizes) == result.document_count

    def test_cluster_documents_returns_percentages(
        self, cluster_service: ClusterService, sample_documents: list[str]
    ):
        """cluster_documents()가 클러스터 비율을 반환한다."""
        # When
        result = cluster_service.cluster_documents(n_clusters=3, documents=sample_documents)

        # Then
        total_percentage = sum(c.percentage for c in result.clusters)
        assert abs(total_percentage - 100.0) < 1.0

    @patch("reddit_insight.dashboard.services.cluster_service.get_current_data")
    def test_cluster_documents_from_stored_data(
        self,
        mock_get_current_data: MagicMock,
        cluster_service: ClusterService,
        mock_analysis_data: AnalysisData,
    ):
        """저장된 데이터에서 클러스터링을 수행한다."""
        # Given
        mock_get_current_data.return_value = mock_analysis_data

        # When
        result = cluster_service.cluster_documents(n_clusters=3)

        # Then
        assert isinstance(result, ClusterAnalysisView)
        mock_get_current_data.assert_called_once()

    @patch("reddit_insight.dashboard.services.cluster_service.get_current_data")
    def test_get_available_document_count(
        self,
        mock_get_current_data: MagicMock,
        cluster_service: ClusterService,
        mock_analysis_data: AnalysisData,
    ):
        """get_available_document_count()가 문서 수를 반환한다."""
        # Given
        mock_get_current_data.return_value = mock_analysis_data

        # When
        count = cluster_service.get_available_document_count()

        # Then
        assert count > 0


# =============================================================================
# CLUSTER SERVICE DOCUMENT RETRIEVAL TESTS
# =============================================================================


class TestClusterServiceDocumentRetrieval:
    """ClusterService 문서 조회 테스트."""

    def test_get_cluster_documents(
        self, cluster_service: ClusterService, sample_documents: list[str]
    ):
        """get_cluster_documents()가 클러스터 문서를 반환한다."""
        # Given: 먼저 클러스터링 실행
        result = cluster_service.cluster_documents(n_clusters=3, documents=sample_documents)

        # When: 첫 번째 클러스터 문서 조회
        if result.clusters:
            cluster_id = result.clusters[0].id
            docs = cluster_service.get_cluster_documents(cluster_id)

            # Then
            assert isinstance(docs, list)
            assert len(docs) == result.clusters[0].size

    def test_get_cluster_documents_no_cached_result(
        self, cluster_service: ClusterService
    ):
        """캐시된 결과 없이 get_cluster_documents() 호출 시 빈 목록 반환."""
        # When: 클러스터링 실행 없이 바로 조회
        docs = cluster_service.get_cluster_documents(0)

        # Then
        assert docs == []

    def test_get_cluster_by_id(
        self, cluster_service: ClusterService, sample_documents: list[str]
    ):
        """get_cluster_by_id()가 특정 클러스터 정보를 반환한다."""
        # Given
        result = cluster_service.cluster_documents(n_clusters=3, documents=sample_documents)

        # When
        if result.clusters:
            cluster_id = result.clusters[0].id
            cluster = cluster_service.get_cluster_by_id(cluster_id)

            # Then
            assert cluster is not None
            assert cluster.id == cluster_id

    def test_get_cluster_by_id_not_found(
        self, cluster_service: ClusterService, sample_documents: list[str]
    ):
        """존재하지 않는 클러스터 ID로 조회 시 None 반환."""
        # Given
        cluster_service.cluster_documents(n_clusters=3, documents=sample_documents)

        # When
        cluster = cluster_service.get_cluster_by_id(999)

        # Then
        assert cluster is None


# =============================================================================
# SINGLETON TESTS
# =============================================================================


class TestClusterServiceSingleton:
    """ClusterService 싱글톤 테스트."""

    def test_get_cluster_service_returns_singleton(self):
        """get_cluster_service()가 싱글톤 인스턴스를 반환한다."""
        # When
        service1 = get_cluster_service()
        service2 = get_cluster_service()

        # Then
        assert service1 is service2


# =============================================================================
# EDGE CASE TESTS
# =============================================================================


class TestClusterServiceEdgeCases:
    """ClusterService 엣지 케이스 테스트."""

    def test_insufficient_documents(self, cluster_service: ClusterService):
        """문서가 부족할 때 빈 결과를 반환한다."""
        # Given
        short_docs = ["Only one document"]

        # When
        result = cluster_service.cluster_documents(n_clusters=3, documents=short_docs)

        # Then
        assert isinstance(result, ClusterAnalysisView)
        assert result.n_clusters == 0
        assert len(result.clusters) == 0

    def test_empty_documents(self, cluster_service: ClusterService):
        """빈 문서 목록을 처리한다."""
        # Given
        empty_docs: list[str] = []

        # When
        result = cluster_service.cluster_documents(n_clusters=3, documents=empty_docs)

        # Then
        assert isinstance(result, ClusterAnalysisView)
        assert result.n_clusters == 0

    def test_n_clusters_boundary_values(
        self, cluster_service: ClusterService, sample_documents: list[str]
    ):
        """클러스터 수 경계값을 처리한다."""
        # When: 최소값 테스트
        result_min = cluster_service.cluster_documents(n_clusters=2, documents=sample_documents)
        assert result_min.n_clusters >= 0

        # When: 최대값 테스트
        result_max = cluster_service.cluster_documents(n_clusters=10, documents=sample_documents)
        assert result_max.n_clusters <= 10

        # When: 범위 미만 테스트 (2로 제한)
        result_under = cluster_service.cluster_documents(n_clusters=1, documents=sample_documents)
        assert result_under.n_clusters >= 0

        # When: 범위 초과 테스트 (max_possible로 제한)
        result_over = cluster_service.cluster_documents(n_clusters=20, documents=sample_documents)
        assert result_over.n_clusters <= len(sample_documents) - 1

    @patch("reddit_insight.dashboard.services.cluster_service.get_current_data")
    def test_no_stored_data(
        self, mock_get_current_data: MagicMock, cluster_service: ClusterService
    ):
        """저장된 데이터가 없을 때 빈 결과를 반환한다."""
        # Given
        mock_get_current_data.return_value = None

        # When
        result = cluster_service.cluster_documents(n_clusters=3)

        # Then
        assert isinstance(result, ClusterAnalysisView)
        assert result.n_clusters == 0

    def test_very_short_documents(self, cluster_service: ClusterService):
        """매우 짧은 문서들을 처리한다."""
        # Given: 10자 미만 문서들 (필터링됨)
        short_docs = ["hi", "hello", "yes", "no"]

        # When
        result = cluster_service.cluster_documents(n_clusters=2, documents=short_docs)

        # Then
        assert isinstance(result, ClusterAnalysisView)

    def test_special_characters_in_documents(
        self, cluster_service: ClusterService, sample_documents: list[str]
    ):
        """특수 문자가 포함된 문서를 처리한다."""
        # Given
        docs_with_special = sample_documents + [
            "C++ is a powerful language!!! @#$%",
            "Use python3.11 for better performance...",
        ]

        # When
        result = cluster_service.cluster_documents(n_clusters=3, documents=docs_with_special)

        # Then
        assert isinstance(result, ClusterAnalysisView)
        assert result.n_clusters > 0

    def test_silhouette_score_range(
        self, cluster_service: ClusterService, sample_documents: list[str]
    ):
        """실루엣 점수가 유효한 범위 내에 있다."""
        # When
        result = cluster_service.cluster_documents(n_clusters=3, documents=sample_documents)

        # Then
        if result.n_clusters > 1:
            assert -1.0 <= result.silhouette_score <= 1.0
