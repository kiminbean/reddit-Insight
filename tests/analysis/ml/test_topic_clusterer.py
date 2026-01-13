"""
Tests for topic modeling and text clustering.

Tests TopicModeler (LDA/NMF) and TextClusterer (K-means/Agglomerative).
"""

import pytest

from reddit_insight.analysis.ml.models import (
    Cluster,
    ClusterResult,
    Topic,
    TopicResult,
)
from reddit_insight.analysis.ml.text_clusterer import (
    TextClusterer,
    TextClustererConfig,
)
from reddit_insight.analysis.ml.topic_modeler import (
    TopicModeler,
    TopicModelerConfig,
)


# Test fixtures
@pytest.fixture
def sample_texts() -> list[str]:
    """Sample texts for testing topic modeling and clustering."""
    return [
        "I need a tool for managing tasks and projects",
        "Looking for project management software",
        "How to organize my work better",
        "Best apps for productivity and focus",
        "Need help with concentration and time management",
        "Frustrated with slow loading times",
        "The app crashes frequently on my phone",
        "Performance issues with the latest update",
        "Bug in the login screen prevents access",
        "Error messages everywhere after update",
    ]


@pytest.fixture
def minimal_texts() -> list[str]:
    """Minimal texts for edge case testing."""
    return [
        "Python programming language",
        "Java programming language",
        "Machine learning algorithms",
        "Deep learning neural networks",
    ]


# TopicModeler Tests
class TestTopicModelerLDA:
    """Tests for LDA topic modeling."""

    def test_lda_extracts_topics(self, sample_texts: list[str]) -> None:
        """LDA method should extract topics from texts."""
        config = TopicModelerConfig(n_topics=2, method="lda")
        modeler = TopicModeler(config)
        result = modeler.fit_transform(sample_texts)

        assert result.n_topics == 2
        assert len(result.topics) == 2
        assert result.method == "lda"

    def test_lda_topics_have_keywords(self, sample_texts: list[str]) -> None:
        """LDA topics should have keywords."""
        config = TopicModelerConfig(n_topics=2, method="lda", n_top_words=5)
        modeler = TopicModeler(config)
        result = modeler.fit_transform(sample_texts)

        for topic in result.topics:
            assert len(topic.keywords) > 0
            assert len(topic.keywords) <= 5
            assert all(isinstance(kw, str) for kw in topic.keywords)

    def test_lda_has_perplexity(self, sample_texts: list[str]) -> None:
        """LDA should compute perplexity metric."""
        config = TopicModelerConfig(n_topics=2, method="lda")
        modeler = TopicModeler(config)
        result = modeler.fit_transform(sample_texts)

        assert result.perplexity is not None
        assert isinstance(result.perplexity, float)


class TestTopicModelerNMF:
    """Tests for NMF topic modeling."""

    def test_nmf_extracts_topics(self, sample_texts: list[str]) -> None:
        """NMF method should extract topics from texts."""
        config = TopicModelerConfig(n_topics=2, method="nmf")
        modeler = TopicModeler(config)
        result = modeler.fit_transform(sample_texts)

        assert result.n_topics == 2
        assert len(result.topics) == 2
        assert result.method == "nmf"

    def test_nmf_no_perplexity(self, sample_texts: list[str]) -> None:
        """NMF should not have perplexity (not a probabilistic model)."""
        config = TopicModelerConfig(n_topics=2, method="nmf")
        modeler = TopicModeler(config)
        result = modeler.fit_transform(sample_texts)

        assert result.perplexity is None


class TestTopicModelerAuto:
    """Tests for automatic method selection."""

    def test_auto_selects_method(self, minimal_texts: list[str]) -> None:
        """Auto should select appropriate method based on corpus size."""
        config = TopicModelerConfig(n_topics=2, method="auto")
        modeler = TopicModeler(config)
        result = modeler.fit_transform(minimal_texts)

        # Small corpus should use NMF
        assert result.method == "nmf"

    def test_auto_with_large_corpus(self, sample_texts: list[str]) -> None:
        """Auto should use LDA for larger corpora."""
        # Expand corpus to trigger LDA selection
        large_texts = sample_texts * 15  # 150 texts

        config = TopicModelerConfig(n_topics=2, method="auto")
        modeler = TopicModeler(config)
        result = modeler.fit_transform(large_texts)

        # Large corpus should use LDA
        assert result.method == "lda"


class TestTopicResultStructure:
    """Tests for TopicResult data structure."""

    def test_topic_result_has_required_fields(
        self, sample_texts: list[str]
    ) -> None:
        """TopicResult should have all required fields."""
        config = TopicModelerConfig(n_topics=2)
        modeler = TopicModeler(config)
        result = modeler.fit_transform(sample_texts)

        assert isinstance(result.topics, list)
        assert isinstance(result.n_topics, int)
        assert isinstance(result.coherence_score, float)
        assert isinstance(result.method, str)
        assert isinstance(result.document_topic_distribution, list)
        assert isinstance(result.parameters, dict)

    def test_topic_has_required_fields(self, sample_texts: list[str]) -> None:
        """Each Topic should have all required fields."""
        config = TopicModelerConfig(n_topics=2)
        modeler = TopicModeler(config)
        result = modeler.fit_transform(sample_texts)

        for topic in result.topics:
            assert isinstance(topic, Topic)
            assert isinstance(topic.id, int)
            assert isinstance(topic.keywords, list)
            assert isinstance(topic.weights, list)
            assert len(topic.keywords) == len(topic.weights)

    def test_document_topic_distribution(self, sample_texts: list[str]) -> None:
        """Document-topic distribution should match corpus size."""
        config = TopicModelerConfig(n_topics=2)
        modeler = TopicModeler(config)
        result = modeler.fit_transform(sample_texts)

        assert len(result.document_topic_distribution) == len(sample_texts)
        for dist in result.document_topic_distribution:
            assert len(dist) == 2  # n_topics
            assert abs(sum(dist) - 1.0) < 0.01  # Normalized

    def test_get_document_topics(self, sample_texts: list[str]) -> None:
        """get_document_topics should return topic distribution."""
        config = TopicModelerConfig(n_topics=2)
        modeler = TopicModeler(config)
        modeler.fit_transform(sample_texts)

        topics = modeler.get_document_topics("task management software")
        assert len(topics) == 2
        assert all(isinstance(t, tuple) for t in topics)
        assert all(len(t) == 2 for t in topics)
        # Sum of probabilities should be close to 1
        assert abs(sum(p for _, p in topics) - 1.0) < 0.01


# TextClusterer Tests
class TestTextClustererKMeans:
    """Tests for K-means clustering."""

    def test_kmeans_creates_clusters(self, sample_texts: list[str]) -> None:
        """K-means should create specified number of clusters."""
        config = TextClustererConfig(n_clusters=2, method="kmeans")
        clusterer = TextClusterer(config)
        result = clusterer.cluster(sample_texts)

        assert result.n_clusters == 2
        assert len(result.clusters) == 2
        assert result.method == "kmeans"

    def test_kmeans_cluster_sizes(self, sample_texts: list[str]) -> None:
        """Cluster sizes should sum to total documents."""
        config = TextClustererConfig(n_clusters=2, method="kmeans")
        clusterer = TextClusterer(config)
        result = clusterer.cluster(sample_texts)

        total_size = sum(c.size for c in result.clusters)
        assert total_size == len(sample_texts)

    def test_kmeans_has_inertia(self, sample_texts: list[str]) -> None:
        """K-means should compute inertia metric."""
        config = TextClustererConfig(n_clusters=2, method="kmeans")
        clusterer = TextClusterer(config)
        result = clusterer.cluster(sample_texts)

        assert result.inertia is not None
        assert isinstance(result.inertia, float)
        assert result.inertia >= 0


class TestTextClustererAgglomerative:
    """Tests for Agglomerative clustering."""

    def test_agglomerative_creates_clusters(
        self, sample_texts: list[str]
    ) -> None:
        """Agglomerative should create clusters."""
        config = TextClustererConfig(n_clusters=2, method="agglomerative")
        clusterer = TextClusterer(config)
        result = clusterer.cluster(sample_texts)

        assert result.n_clusters == 2
        assert result.method == "agglomerative"

    def test_agglomerative_no_inertia(self, sample_texts: list[str]) -> None:
        """Agglomerative should not have inertia metric."""
        config = TextClustererConfig(n_clusters=2, method="agglomerative")
        clusterer = TextClusterer(config)
        result = clusterer.cluster(sample_texts)

        assert result.inertia is None


class TestAutoClusterSelection:
    """Tests for automatic cluster count selection."""

    def test_auto_selects_clusters(self, sample_texts: list[str]) -> None:
        """Auto should select optimal number of clusters."""
        config = TextClustererConfig(n_clusters=None, max_clusters=5)
        clusterer = TextClusterer(config)
        result = clusterer.cluster(sample_texts)

        assert 2 <= result.n_clusters <= 5
        assert len(result.clusters) == result.n_clusters

    def test_silhouette_score_computed(self, sample_texts: list[str]) -> None:
        """Silhouette score should be computed."""
        config = TextClustererConfig(n_clusters=2)
        clusterer = TextClusterer(config)
        result = clusterer.cluster(sample_texts)

        assert isinstance(result.silhouette_score, float)
        assert -1 <= result.silhouette_score <= 1


class TestClusterResultStructure:
    """Tests for ClusterResult data structure."""

    def test_cluster_result_has_required_fields(
        self, sample_texts: list[str]
    ) -> None:
        """ClusterResult should have all required fields."""
        config = TextClustererConfig(n_clusters=2)
        clusterer = TextClusterer(config)
        result = clusterer.cluster(sample_texts)

        assert isinstance(result.clusters, list)
        assert isinstance(result.n_clusters, int)
        assert isinstance(result.silhouette_score, float)
        assert isinstance(result.method, str)
        assert isinstance(result.labels, list)
        assert isinstance(result.parameters, dict)

    def test_cluster_has_required_fields(
        self, sample_texts: list[str]
    ) -> None:
        """Each Cluster should have all required fields."""
        config = TextClustererConfig(n_clusters=2)
        clusterer = TextClusterer(config)
        result = clusterer.cluster(sample_texts)

        for cluster in result.clusters:
            assert isinstance(cluster, Cluster)
            assert isinstance(cluster.id, int)
            assert isinstance(cluster.label, str)
            assert isinstance(cluster.size, int)
            assert isinstance(cluster.keywords, list)
            assert cluster.size > 0

    def test_labels_match_documents(self, sample_texts: list[str]) -> None:
        """Labels should match number of documents."""
        config = TextClustererConfig(n_clusters=2)
        clusterer = TextClusterer(config)
        result = clusterer.cluster(sample_texts)

        assert len(result.labels) == len(sample_texts)
        assert all(0 <= label < result.n_clusters for label in result.labels)

    def test_assign_cluster(self, sample_texts: list[str]) -> None:
        """assign_cluster should classify new text."""
        config = TextClustererConfig(n_clusters=2, method="kmeans")
        clusterer = TextClusterer(config)
        clusterer.cluster(sample_texts)

        cluster_id = clusterer.assign_cluster("task management software")
        assert 0 <= cluster_id < 2


# Empty Input Handling Tests
class TestEmptyInputHandling:
    """Tests for handling empty or invalid inputs."""

    def test_topic_modeler_empty_corpus(self) -> None:
        """TopicModeler should raise error on empty corpus."""
        config = TopicModelerConfig(n_topics=2)
        modeler = TopicModeler(config)

        with pytest.raises(ValueError, match="empty"):
            modeler.fit_transform([])

    def test_topic_modeler_insufficient_docs(self) -> None:
        """TopicModeler should raise error with insufficient docs."""
        config = TopicModelerConfig(n_topics=2)
        modeler = TopicModeler(config)

        with pytest.raises(ValueError, match="at least 2"):
            modeler.fit_transform(["single document"])

    def test_text_clusterer_empty_corpus(self) -> None:
        """TextClusterer should raise error on empty corpus."""
        config = TextClustererConfig(n_clusters=2)
        clusterer = TextClusterer(config)

        with pytest.raises(ValueError, match="empty"):
            clusterer.cluster([])

    def test_text_clusterer_insufficient_docs(self) -> None:
        """TextClusterer should raise error with insufficient docs."""
        config = TextClustererConfig(n_clusters=2)
        clusterer = TextClusterer(config)

        with pytest.raises(ValueError, match="at least 2"):
            clusterer.cluster(["single document"])

    def test_get_document_topics_unfitted(self) -> None:
        """get_document_topics should raise error if not fitted."""
        modeler = TopicModeler()

        with pytest.raises(RuntimeError, match="not fitted"):
            modeler.get_document_topics("test text")

    def test_assign_cluster_unfitted(self) -> None:
        """assign_cluster should raise error if not fitted."""
        clusterer = TextClusterer()

        with pytest.raises(RuntimeError, match="not fitted"):
            clusterer.assign_cluster("test text")


# Integration with MLAnalyzerBase
class TestMLAnalyzerInterface:
    """Tests for MLAnalyzerBase interface compliance."""

    def test_topic_modeler_analyze(self, sample_texts: list[str]) -> None:
        """TopicModeler.analyze() should return AnalysisResult."""
        modeler = TopicModeler(TopicModelerConfig(n_topics=2))
        result = modeler.analyze(sample_texts)

        assert result.result_type == "topic"
        assert result.success is True
        assert result.data is not None
        assert 0 <= result.confidence <= 1

    def test_text_clusterer_analyze(self, sample_texts: list[str]) -> None:
        """TextClusterer.analyze() should return AnalysisResult."""
        clusterer = TextClusterer(TextClustererConfig(n_clusters=2))
        result = clusterer.analyze(sample_texts)

        assert result.result_type == "cluster"
        assert result.success is True
        assert result.data is not None
        assert 0 <= result.confidence <= 1

    def test_topic_modeler_analyze_invalid(self) -> None:
        """TopicModeler.analyze() should handle invalid input."""
        modeler = TopicModeler()
        result = modeler.analyze("not a list")

        assert result.success is False
        assert result.error_message is not None

    def test_text_clusterer_analyze_invalid(self) -> None:
        """TextClusterer.analyze() should handle invalid input."""
        clusterer = TextClusterer()
        result = clusterer.analyze("not a list")

        assert result.success is False
        assert result.error_message is not None


# Serialization Tests
class TestSerialization:
    """Tests for result serialization."""

    def test_topic_result_to_dict(self, sample_texts: list[str]) -> None:
        """TopicResult should serialize to dict."""
        modeler = TopicModeler(TopicModelerConfig(n_topics=2))
        result = modeler.fit_transform(sample_texts)
        data = result.to_dict()

        assert isinstance(data, dict)
        assert "topics" in data
        assert "n_topics" in data
        assert "coherence_score" in data
        assert "method" in data

    def test_cluster_result_to_dict(self, sample_texts: list[str]) -> None:
        """ClusterResult should serialize to dict."""
        clusterer = TextClusterer(TextClustererConfig(n_clusters=2))
        result = clusterer.cluster(sample_texts)
        data = result.to_dict()

        assert isinstance(data, dict)
        assert "clusters" in data
        assert "n_clusters" in data
        assert "silhouette_score" in data
        assert "method" in data
