"""
Tests for demand discovery module.

Tests for DemandPatterns, DemandDetector, and DemandAnalyzer.
"""

from __future__ import annotations

import pytest
from datetime import UTC, datetime

from reddit_insight.analysis.demand_patterns import (
    DemandCategory,
    DemandMatch,
    DemandPattern,
    DemandPatternLibrary,
    ENGLISH_PATTERNS,
)
from reddit_insight.analysis.demand_detector import (
    DemandDetector,
    DemandDetectorConfig,
    DemandSummary,
)
from reddit_insight.analysis.demand_analyzer import (
    DemandAnalyzer,
    DemandCluster,
    DemandClusterer,
    DemandReport,
    PrioritizedDemand,
    PriorityCalculator,
    PriorityConfig,
    PriorityScore,
)
from reddit_insight.reddit.models import Post


# =============================================================================
# TEST FIXTURES
# =============================================================================


@pytest.fixture
def english_library() -> DemandPatternLibrary:
    """Create an English pattern library."""
    return DemandPatternLibrary.create_english_library()


@pytest.fixture
def detector() -> DemandDetector:
    """Create a demand detector with default settings."""
    return DemandDetector()


@pytest.fixture
def clusterer() -> DemandClusterer:
    """Create a demand clusterer with default settings."""
    return DemandClusterer()


@pytest.fixture
def priority_calculator() -> PriorityCalculator:
    """Create a priority calculator with default settings."""
    return PriorityCalculator()


@pytest.fixture
def analyzer() -> DemandAnalyzer:
    """Create a demand analyzer with default settings."""
    return DemandAnalyzer()


@pytest.fixture
def sample_texts() -> list[str]:
    """Sample texts containing demand expressions."""
    return [
        "I wish there was a better way to organize my notes. It's so frustrating!",
        "Looking for a good project management tool. Does anyone know of something free?",
        "I'd pay $50 for a tool that can do this automatically.",
        "Really frustrated with how slow this app is. Why can't it just work?",
        "Is there anything like Notion but with better offline support?",
        "Would love to see a dark mode option in this app.",
        "Can anyone recommend a good password manager?",
        "Willing to pay for quality software that actually works.",
        "Looking for an alternative to Evernote that's actually maintained.",
        "This is annoying when the app crashes every time I try to export.",
    ]


@pytest.fixture
def sample_posts() -> list[Post]:
    """Sample Post objects for testing."""
    return [
        Post(
            id="post1",
            title="I wish there was a better note-taking app",
            selftext="Really need something that syncs across all devices.",
            author="user1",
            subreddit="productivity",
            score=100,
            num_comments=50,
            created_utc=datetime.now(UTC),
            url="https://reddit.com/r/productivity/post1",
            permalink="https://reddit.com/r/productivity/post1",
            is_self=True,
        ),
        Post(
            id="post2",
            title="Looking for project management recommendations",
            selftext="I'd pay for something that integrates with my existing tools.",
            author="user2",
            subreddit="productivity",
            score=75,
            num_comments=30,
            created_utc=datetime.now(UTC),
            url="https://reddit.com/r/productivity/post2",
            permalink="https://reddit.com/r/productivity/post2",
            is_self=True,
        ),
        Post(
            id="post3",
            title="Frustrated with current options",
            selftext="Why can't anyone make a simple app that just works?",
            author="user3",
            subreddit="apps",
            score=50,
            num_comments=20,
            created_utc=datetime.now(UTC),
            url="https://reddit.com/r/apps/post3",
            permalink="https://reddit.com/r/apps/post3",
            is_self=True,
        ),
    ]


# =============================================================================
# TEST: DEMAND PATTERNS
# =============================================================================


class TestDemandPatterns:
    """Tests for demand pattern definitions."""

    def test_demand_category_values(self) -> None:
        """Test that all demand categories have correct values."""
        assert DemandCategory.FEATURE_REQUEST.value == "feature_request"
        assert DemandCategory.PAIN_POINT.value == "pain_point"
        assert DemandCategory.SEARCH_QUERY.value == "search_query"
        assert DemandCategory.WILLINGNESS_TO_PAY.value == "willingness_to_pay"
        assert DemandCategory.ALTERNATIVE_SEEKING.value == "alternative_seeking"

    def test_demand_category_description(self) -> None:
        """Test that categories have descriptions."""
        for category in DemandCategory:
            assert category.description is not None
            assert len(category.description) > 0

    def test_demand_pattern_creation(self) -> None:
        """Test DemandPattern dataclass creation."""
        pattern = DemandPattern(
            pattern_id="test_001",
            category=DemandCategory.FEATURE_REQUEST,
            regex_pattern=r"i wish there was",
            keywords=["wish", "there was"],
            weight=1.0,
            examples=["I wish there was a better tool"],
        )
        assert pattern.pattern_id == "test_001"
        assert pattern.category == DemandCategory.FEATURE_REQUEST
        assert pattern.weight == 1.0

    def test_english_patterns_exist(self) -> None:
        """Test that English patterns are defined."""
        assert len(ENGLISH_PATTERNS) > 0
        assert len(ENGLISH_PATTERNS) >= 15  # At least 15 patterns

    def test_english_patterns_categories(self) -> None:
        """Test that English patterns cover all categories."""
        categories_covered = set()
        for pattern in ENGLISH_PATTERNS:
            categories_covered.add(pattern.category)

        assert DemandCategory.FEATURE_REQUEST in categories_covered
        assert DemandCategory.PAIN_POINT in categories_covered
        assert DemandCategory.SEARCH_QUERY in categories_covered
        assert DemandCategory.WILLINGNESS_TO_PAY in categories_covered
        assert DemandCategory.ALTERNATIVE_SEEKING in categories_covered


class TestDemandPatternLibrary:
    """Tests for DemandPatternLibrary."""

    def test_create_english_library(self, english_library: DemandPatternLibrary) -> None:
        """Test creating English pattern library."""
        assert english_library.language == "en"
        assert len(english_library) > 0

    def test_get_patterns_all(self, english_library: DemandPatternLibrary) -> None:
        """Test getting all patterns."""
        patterns = english_library.get_patterns()
        assert len(patterns) == len(english_library)

    def test_get_patterns_by_category(
        self, english_library: DemandPatternLibrary
    ) -> None:
        """Test getting patterns by category."""
        feature_patterns = english_library.get_patterns(DemandCategory.FEATURE_REQUEST)
        assert len(feature_patterns) > 0
        for pattern in feature_patterns:
            assert pattern.category == DemandCategory.FEATURE_REQUEST

    def test_get_pattern_by_id(self, english_library: DemandPatternLibrary) -> None:
        """Test getting pattern by ID."""
        # Get first pattern
        all_patterns = english_library.get_patterns()
        if all_patterns:
            pattern_id = all_patterns[0].pattern_id
            pattern = english_library.get_pattern_by_id(pattern_id)
            assert pattern is not None
            assert pattern.pattern_id == pattern_id

    def test_get_compiled_pattern(self, english_library: DemandPatternLibrary) -> None:
        """Test getting compiled regex pattern."""
        all_patterns = english_library.get_patterns()
        if all_patterns:
            pattern_id = all_patterns[0].pattern_id
            compiled = english_library.get_compiled_pattern(pattern_id)
            assert compiled is not None

    def test_create_multilingual_library(self) -> None:
        """Test creating multilingual library."""
        library = DemandPatternLibrary.create_multilingual_library()
        assert library.language == "multi"
        assert len(library) > 0


# =============================================================================
# TEST: DEMAND DETECTOR
# =============================================================================


class TestDemandDetector:
    """Tests for DemandDetector."""

    def test_detector_initialization(self, detector: DemandDetector) -> None:
        """Test detector initialization."""
        assert detector.config is not None
        assert detector.library is not None

    def test_detect_feature_request(self, detector: DemandDetector) -> None:
        """Test detecting feature request patterns."""
        text = "I wish there was a better way to organize my notes"
        matches = detector.detect(text)
        assert len(matches) > 0
        assert any(m.category == DemandCategory.FEATURE_REQUEST for m in matches)

    def test_detect_pain_point(self, detector: DemandDetector) -> None:
        """Test detecting pain point patterns."""
        text = "I'm really frustrated with how slow this app is"
        matches = detector.detect(text)
        assert len(matches) > 0
        assert any(m.category == DemandCategory.PAIN_POINT for m in matches)

    def test_detect_search_query(self, detector: DemandDetector) -> None:
        """Test detecting search query patterns."""
        text = "Does anyone know of a good project management tool?"
        matches = detector.detect(text)
        assert len(matches) > 0
        assert any(m.category == DemandCategory.SEARCH_QUERY for m in matches)

    def test_detect_willingness_to_pay(self, detector: DemandDetector) -> None:
        """Test detecting willingness to pay patterns."""
        text = "I'd pay $50 for a tool that does this automatically"
        matches = detector.detect(text)
        assert len(matches) > 0
        assert any(m.category == DemandCategory.WILLINGNESS_TO_PAY for m in matches)

    def test_detect_alternative_seeking(self, detector: DemandDetector) -> None:
        """Test detecting alternative seeking patterns."""
        text = "Looking for an alternative to Notion"
        matches = detector.detect(text)
        assert len(matches) > 0
        assert any(m.category == DemandCategory.ALTERNATIVE_SEEKING for m in matches)

    def test_detect_empty_text(self, detector: DemandDetector) -> None:
        """Test detecting from empty text."""
        matches = detector.detect("")
        assert len(matches) == 0

    def test_detect_no_patterns(self, detector: DemandDetector) -> None:
        """Test detecting from text without patterns."""
        text = "The weather is nice today."
        matches = detector.detect(text)
        assert len(matches) == 0

    def test_match_confidence(self, detector: DemandDetector) -> None:
        """Test that matches have confidence scores."""
        text = "I wish there was a better tool"
        matches = detector.detect(text)
        for match in matches:
            assert 0.0 <= match.confidence <= 1.0

    def test_match_context(self, detector: DemandDetector) -> None:
        """Test that matches have context."""
        text = "I really wish there was a better tool for this task."
        matches = detector.detect(text)
        for match in matches:
            assert len(match.context) > 0

    def test_detect_in_post(
        self, detector: DemandDetector, sample_posts: list[Post]
    ) -> None:
        """Test detecting in Post object."""
        post = sample_posts[0]
        matches = detector.detect_in_post(post)
        assert len(matches) > 0

    def test_detect_in_posts(
        self, detector: DemandDetector, sample_posts: list[Post]
    ) -> None:
        """Test detecting in multiple Post objects."""
        matches = detector.detect_in_posts(sample_posts)
        assert len(matches) > 0

    def test_get_category_stats(
        self, detector: DemandDetector, sample_texts: list[str]
    ) -> None:
        """Test category statistics."""
        all_matches = []
        for text in sample_texts:
            all_matches.extend(detector.detect(text))

        stats = detector.get_category_stats(all_matches)
        assert isinstance(stats, dict)
        assert len(stats) > 0

    def test_summarize(
        self, detector: DemandDetector, sample_texts: list[str]
    ) -> None:
        """Test summarize method."""
        all_matches = []
        for text in sample_texts:
            all_matches.extend(detector.detect(text))

        summary = detector.summarize(all_matches, analyzed_texts=len(sample_texts))
        assert isinstance(summary, DemandSummary)
        assert summary.total_matches == len(all_matches)
        assert summary.analyzed_texts == len(sample_texts)


# =============================================================================
# TEST: DEMAND CLUSTERER
# =============================================================================


class TestDemandClusterer:
    """Tests for DemandClusterer."""

    def test_clusterer_initialization(self, clusterer: DemandClusterer) -> None:
        """Test clusterer initialization."""
        assert clusterer.keyword_extractor is not None
        assert clusterer.similarity_threshold == 0.7

    def test_cluster_demands_empty(self, clusterer: DemandClusterer) -> None:
        """Test clustering with empty matches."""
        clusters = clusterer.cluster_demands([])
        assert len(clusters) == 0

    def test_cluster_demands(
        self,
        clusterer: DemandClusterer,
        detector: DemandDetector,
        sample_texts: list[str],
    ) -> None:
        """Test clustering demands."""
        all_matches = []
        for text in sample_texts:
            all_matches.extend(detector.detect(text))

        clusters = clusterer.cluster_demands(all_matches)
        assert len(clusters) > 0
        for cluster in clusters:
            assert isinstance(cluster, DemandCluster)
            assert len(cluster.matches) > 0
            assert cluster.frequency == len(cluster.matches)

    def test_cluster_has_representative(
        self,
        clusterer: DemandClusterer,
        detector: DemandDetector,
        sample_texts: list[str],
    ) -> None:
        """Test that clusters have representative text."""
        all_matches = []
        for text in sample_texts:
            all_matches.extend(detector.detect(text))

        clusters = clusterer.cluster_demands(all_matches)
        for cluster in clusters:
            assert len(cluster.representative) > 0

    def test_cluster_has_categories(
        self,
        clusterer: DemandClusterer,
        detector: DemandDetector,
        sample_texts: list[str],
    ) -> None:
        """Test that clusters have categories."""
        all_matches = []
        for text in sample_texts:
            all_matches.extend(detector.detect(text))

        clusters = clusterer.cluster_demands(all_matches)
        for cluster in clusters:
            assert len(cluster.categories) > 0


# =============================================================================
# TEST: PRIORITY CALCULATOR
# =============================================================================


class TestPriorityCalculator:
    """Tests for PriorityCalculator."""

    def test_calculator_initialization(
        self, priority_calculator: PriorityCalculator
    ) -> None:
        """Test calculator initialization."""
        assert priority_calculator.config is not None

    def test_custom_config(self) -> None:
        """Test calculator with custom config."""
        config = PriorityConfig(
            frequency_weight=0.4,
            payment_weight=0.3,
            urgency_weight=0.2,
            recency_weight=0.1,
        )
        calculator = PriorityCalculator(config=config)
        assert calculator.config.frequency_weight == 0.4

    def test_calculate_priority(
        self,
        priority_calculator: PriorityCalculator,
        clusterer: DemandClusterer,
        detector: DemandDetector,
        sample_texts: list[str],
    ) -> None:
        """Test priority calculation."""
        all_matches = []
        for text in sample_texts:
            all_matches.extend(detector.detect(text))

        clusters = clusterer.cluster_demands(all_matches)
        if clusters:
            priority = priority_calculator.calculate_priority(clusters[0])
            assert isinstance(priority, PriorityScore)
            assert 0 <= priority.total_score <= 100
            assert 0 <= priority.frequency_score <= 100
            assert 0 <= priority.payment_intent_score <= 100 + 10  # Has bonus

    def test_priority_breakdown(
        self,
        priority_calculator: PriorityCalculator,
        clusterer: DemandClusterer,
        detector: DemandDetector,
        sample_texts: list[str],
    ) -> None:
        """Test priority score breakdown."""
        all_matches = []
        for text in sample_texts:
            all_matches.extend(detector.detect(text))

        clusters = clusterer.cluster_demands(all_matches)
        if clusters:
            priority = priority_calculator.calculate_priority(clusters[0])
            assert "frequency" in priority.breakdown
            assert "payment_intent" in priority.breakdown
            assert "urgency" in priority.breakdown
            assert "recency" in priority.breakdown


# =============================================================================
# TEST: DEMAND ANALYZER
# =============================================================================


class TestDemandAnalyzer:
    """Tests for DemandAnalyzer."""

    def test_analyzer_initialization(self, analyzer: DemandAnalyzer) -> None:
        """Test analyzer initialization."""
        assert analyzer.detector is not None
        assert analyzer.clusterer is not None
        assert analyzer.priority_calculator is not None

    def test_analyze_texts(
        self, analyzer: DemandAnalyzer, sample_texts: list[str]
    ) -> None:
        """Test analyzing texts."""
        report = analyzer.analyze_texts(sample_texts)
        assert isinstance(report, DemandReport)
        assert report.total_demands > 0
        assert report.total_clusters > 0

    def test_analyze_posts(
        self, analyzer: DemandAnalyzer, sample_posts: list[Post]
    ) -> None:
        """Test analyzing posts."""
        report = analyzer.analyze_posts(sample_posts)
        assert isinstance(report, DemandReport)
        assert report.total_demands > 0

    def test_report_has_opportunities(
        self, analyzer: DemandAnalyzer, sample_texts: list[str]
    ) -> None:
        """Test that report has opportunities."""
        report = analyzer.analyze_texts(sample_texts, top_n=5)
        assert len(report.top_opportunities) > 0
        for opp in report.top_opportunities:
            assert isinstance(opp, PrioritizedDemand)
            assert opp.rank > 0
            assert opp.business_potential in ["high", "medium", "low"]

    def test_report_has_recommendations(
        self, analyzer: DemandAnalyzer, sample_texts: list[str]
    ) -> None:
        """Test that report has recommendations."""
        report = analyzer.analyze_texts(sample_texts)
        assert len(report.recommendations) > 0

    def test_report_category_breakdown(
        self, analyzer: DemandAnalyzer, sample_texts: list[str]
    ) -> None:
        """Test report category breakdown."""
        report = analyzer.analyze_texts(sample_texts)
        assert len(report.by_category) > 0

    def test_to_markdown(
        self, analyzer: DemandAnalyzer, sample_texts: list[str]
    ) -> None:
        """Test markdown conversion."""
        report = analyzer.analyze_texts(sample_texts)
        md = analyzer.to_markdown(report)
        assert isinstance(md, str)
        assert "# Demand Analysis Report" in md
        assert "## Summary" in md
        assert "## Top Opportunities" in md

    def test_to_dict(
        self, analyzer: DemandAnalyzer, sample_texts: list[str]
    ) -> None:
        """Test dict conversion."""
        report = analyzer.analyze_texts(sample_texts)
        d = analyzer.to_dict(report)
        assert isinstance(d, dict)
        assert "generated_at" in d
        assert "total_demands" in d
        assert "total_clusters" in d
        assert "top_opportunities" in d
        assert "recommendations" in d

    def test_prioritize_clusters(
        self,
        analyzer: DemandAnalyzer,
        clusterer: DemandClusterer,
        detector: DemandDetector,
        sample_texts: list[str],
    ) -> None:
        """Test cluster prioritization."""
        all_matches = []
        for text in sample_texts:
            all_matches.extend(detector.detect(text))

        clusters = clusterer.cluster_demands(all_matches)
        prioritized = analyzer.prioritize_clusters(clusters)

        assert len(prioritized) == len(clusters)
        # Should be sorted by score (descending)
        for i in range(len(prioritized) - 1):
            assert prioritized[i].priority.total_score >= prioritized[i + 1].priority.total_score


# =============================================================================
# INTEGRATION TESTS
# =============================================================================


class TestIntegration:
    """Integration tests for the complete demand discovery pipeline."""

    def test_full_pipeline(self, sample_texts: list[str]) -> None:
        """Test complete pipeline from text to report."""
        # Create analyzer
        analyzer = DemandAnalyzer()

        # Analyze texts
        report = analyzer.analyze_texts(sample_texts, top_n=5)

        # Verify report
        assert report.total_demands > 0
        assert report.total_clusters > 0
        assert len(report.top_opportunities) > 0
        assert len(report.recommendations) > 0

        # Verify opportunities are prioritized
        for i, opp in enumerate(report.top_opportunities):
            assert opp.rank == i + 1

        # Verify markdown output
        md = analyzer.to_markdown(report)
        assert len(md) > 100

        # Verify dict output
        d = analyzer.to_dict(report)
        assert d["total_demands"] == report.total_demands

    def test_pipeline_with_posts(self, sample_posts: list[Post]) -> None:
        """Test pipeline with Post objects."""
        analyzer = DemandAnalyzer()
        report = analyzer.analyze_posts(sample_posts, top_n=5)

        assert report.total_demands > 0
        assert report.generated_at is not None

    def test_all_exports(self) -> None:
        """Test that all Phase 6 exports work."""
        from reddit_insight.analysis import (
            DemandAnalyzer,
            DemandDetector,
            DemandPatternLibrary,
            PriorityCalculator,
            DemandCluster,
            DemandClusterer,
            DemandReport,
            PrioritizedDemand,
            PriorityScore,
            PriorityConfig,
        )

        # All imports should work
        assert DemandAnalyzer is not None
        assert DemandDetector is not None
        assert DemandPatternLibrary is not None
        assert PriorityCalculator is not None
        assert DemandCluster is not None
        assert DemandClusterer is not None
        assert DemandReport is not None
        assert PrioritizedDemand is not None
        assert PriorityScore is not None
        assert PriorityConfig is not None
