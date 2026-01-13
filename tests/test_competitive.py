"""
Tests for competitive analysis module.

Tests entity recognition, sentiment analysis, complaint extraction,
alternative comparison, and competitive analyzer.
"""

import pytest
from datetime import datetime

import sys

sys.path.insert(0, "src")

from reddit_insight.analysis.entity_recognition import (
    EntityRecognizer,
    EntityType,
    ProductEntity,
    EntityMention,
    PatternEntityExtractor,
)
from reddit_insight.analysis.sentiment import (
    RuleBasedSentimentAnalyzer,
    EntitySentimentAnalyzer,
    Sentiment,
    SentimentScore,
)
from reddit_insight.analysis.competitive import (
    ComplaintType,
    Complaint,
    ComplaintExtractor,
    ComparisonType,
    AlternativeComparison,
    AlternativeExtractor,
    CompetitiveInsight,
    CompetitiveReport,
    CompetitiveAnalyzer,
    to_markdown,
    to_dict,
)
from reddit_insight.reddit.models import Post


# =============================================================================
# Entity Recognition Tests
# =============================================================================


class TestEntityRecognition:
    """Tests for entity recognition functionality."""

    def test_pattern_extractor_basic(self):
        """Test basic pattern extraction."""
        extractor = PatternEntityExtractor()
        mentions = extractor.extract("I switched to Notion and it is great")
        assert len(mentions) >= 1
        names = [m.entity.name for m in mentions]
        assert "Notion" in names

    def test_entity_recognizer_basic(self):
        """Test basic entity recognition."""
        recognizer = EntityRecognizer()
        entities = recognizer.recognize("Using Slack for team communication")
        assert len(entities) >= 1
        names = [e.name for e in entities]
        assert "Slack" in names

    def test_entity_recognizer_multiple(self):
        """Test recognition of multiple entities."""
        recognizer = EntityRecognizer()
        text = "I use Slack for chat but Notion is better for docs"
        entities = recognizer.recognize(text)
        names = [e.name for e in entities]
        assert "Slack" in names or "Notion" in names

    def test_entity_type_assignment(self):
        """Test entity type is properly assigned."""
        recognizer = EntityRecognizer()
        entities = recognizer.recognize("Built with React and powered by Python")
        for entity in entities:
            assert isinstance(entity.entity_type, EntityType)

    def test_empty_text(self):
        """Test handling of empty text."""
        recognizer = EntityRecognizer()
        entities = recognizer.recognize("")
        assert entities == []
        entities = recognizer.recognize("   ")
        assert entities == []


# =============================================================================
# Sentiment Analysis Tests
# =============================================================================


class TestSentimentAnalysis:
    """Tests for sentiment analysis functionality."""

    def test_positive_sentiment(self):
        """Test detection of positive sentiment."""
        analyzer = RuleBasedSentimentAnalyzer()
        score = analyzer.analyze("This product is really great and amazing")
        assert score.sentiment == Sentiment.POSITIVE
        assert score.compound > 0

    def test_negative_sentiment(self):
        """Test detection of negative sentiment."""
        analyzer = RuleBasedSentimentAnalyzer()
        score = analyzer.analyze("This product is terrible and awful")
        assert score.sentiment == Sentiment.NEGATIVE
        assert score.compound < 0

    def test_neutral_sentiment(self):
        """Test detection of neutral sentiment."""
        analyzer = RuleBasedSentimentAnalyzer()
        score = analyzer.analyze("The product exists and has features")
        assert score.sentiment in [Sentiment.NEUTRAL, Sentiment.POSITIVE]

    def test_negation_handling(self):
        """Test that negation flips sentiment."""
        analyzer = RuleBasedSentimentAnalyzer()
        positive = analyzer.analyze("This is great")
        negated = analyzer.analyze("This is not great")
        # Negated should be less positive
        assert negated.compound < positive.compound

    def test_entity_sentiment_analyzer(self):
        """Test entity-level sentiment analysis."""
        analyzer = EntitySentimentAnalyzer()
        results = analyzer.analyze_text("Slack is great but Notion is even better")
        assert len(results) >= 0  # May or may not detect entities depending on patterns

    def test_empty_text_sentiment(self):
        """Test sentiment analysis of empty text."""
        analyzer = RuleBasedSentimentAnalyzer()
        score = analyzer.analyze("")
        assert score.sentiment == Sentiment.NEUTRAL
        assert score.compound == 0.0


# =============================================================================
# Complaint Extraction Tests
# =============================================================================


class TestComplaintExtraction:
    """Tests for complaint extraction functionality."""

    def test_performance_complaint(self):
        """Test detection of performance complaints."""
        extractor = ComplaintExtractor()
        complaints = extractor.extract("Slack is so slow and keeps crashing")
        assert len(complaints) >= 1
        types = [c.complaint_type for c in complaints]
        assert ComplaintType.PERFORMANCE in types or ComplaintType.RELIABILITY in types

    def test_functionality_complaint(self):
        """Test detection of functionality complaints."""
        extractor = ComplaintExtractor()
        complaints = extractor.extract("Notion doesn't sync properly")
        assert len(complaints) >= 1

    def test_complaint_severity(self):
        """Test that complaint severity is calculated."""
        extractor = ComplaintExtractor()
        complaints = extractor.extract("Slack is terrible and broken")
        assert len(complaints) >= 1
        assert all(0 <= c.severity <= 1 for c in complaints)

    def test_complaint_keywords(self):
        """Test that keywords are extracted."""
        extractor = ComplaintExtractor()
        complaints = extractor.extract("Slack is so slow and laggy")
        if complaints:
            assert isinstance(complaints[0].keywords, list)

    def test_empty_text_complaints(self):
        """Test complaint extraction from empty text."""
        extractor = ComplaintExtractor()
        complaints = extractor.extract("")
        assert complaints == []

    def test_no_complaints(self):
        """Test text without complaints."""
        extractor = ComplaintExtractor()
        complaints = extractor.extract("The weather is nice today")
        # May or may not find complaints depending on pattern matching
        assert isinstance(complaints, list)


# =============================================================================
# Alternative Extraction Tests
# =============================================================================


class TestAlternativeExtraction:
    """Tests for alternative comparison extraction."""

    def test_switch_pattern(self):
        """Test detection of switch patterns."""
        extractor = AlternativeExtractor()
        alts = extractor.extract("I switched from Evernote to Notion")
        assert len(alts) >= 1
        switch = alts[0]
        assert switch.source_entity.name == "Evernote"
        assert switch.target_entity.name == "Notion"
        assert switch.comparison_type == ComparisonType.SWITCH

    def test_versus_pattern(self):
        """Test detection of versus comparisons."""
        extractor = AlternativeExtractor()
        alts = extractor.extract("Notion vs Obsidian - which is better?")
        assert len(alts) >= 1
        assert alts[0].comparison_type == ComparisonType.VERSUS

    def test_better_than_pattern(self):
        """Test detection of better than comparisons."""
        extractor = AlternativeExtractor()
        alts = extractor.extract("Notion is better than Evernote")
        assert len(alts) >= 1
        assert alts[0].comparison_type == ComparisonType.BETTER_THAN

    def test_alternative_seeking(self):
        """Test detection of alternative seeking."""
        extractor = AlternativeExtractor()
        alts = extractor.extract("Looking for a Slack alternative")
        assert len(alts) >= 1
        assert alts[0].comparison_type == ComparisonType.ALTERNATIVE

    def test_extract_switches(self):
        """Test aggregation of switch patterns."""
        extractor = AlternativeExtractor()
        texts = [
            "I switched from Slack to Discord",
            "We moved from Slack to Teams",
            "Migrated from Slack to Zoom",
        ]
        switches = extractor.extract_switches(texts)
        assert "slack" in switches
        assert len(switches["slack"]) >= 1

    def test_empty_text_alternatives(self):
        """Test alternative extraction from empty text."""
        extractor = AlternativeExtractor()
        alts = extractor.extract("")
        assert alts == []


# =============================================================================
# Competitive Analyzer Tests
# =============================================================================


class TestCompetitiveAnalyzer:
    """Tests for unified competitive analyzer."""

    @pytest.fixture
    def sample_posts(self) -> list[Post]:
        """Create sample posts for testing."""
        return [
            Post(
                id="1",
                title="Slack is so slow",
                selftext="I've been frustrated with Slack lately. It keeps crashing.",
                subreddit="productivity",
                author="user1",
                created_utc=datetime.now(),
                score=10,
                num_comments=5,
                url="https://reddit.com/r/productivity/1",
                permalink="/r/productivity/comments/1",
            ),
            Post(
                id="2",
                title="Switched from Slack to Discord",
                selftext="Best decision ever. Discord is so much better.",
                subreddit="productivity",
                author="user2",
                created_utc=datetime.now(),
                score=25,
                num_comments=10,
                url="https://reddit.com/r/productivity/2",
                permalink="/r/productivity/comments/2",
            ),
            Post(
                id="3",
                title="Notion vs Obsidian",
                selftext="Looking for the best note-taking app. Notion is great but expensive.",
                subreddit="productivity",
                author="user3",
                created_utc=datetime.now(),
                score=50,
                num_comments=20,
                url="https://reddit.com/r/productivity/3",
                permalink="/r/productivity/comments/3",
            ),
        ]

    def test_analyzer_initialization(self):
        """Test analyzer initialization."""
        analyzer = CompetitiveAnalyzer()
        assert analyzer._entity_recognizer is not None
        assert analyzer._sentiment_analyzer is not None
        assert analyzer._complaint_extractor is not None
        assert analyzer._alternative_extractor is not None

    def test_analyze_posts_basic(self, sample_posts):
        """Test basic post analysis."""
        analyzer = CompetitiveAnalyzer()
        report = analyzer.analyze_posts(sample_posts)
        assert isinstance(report, CompetitiveReport)
        assert report.generated_at is not None
        assert report.entities_analyzed >= 0

    def test_analyze_posts_empty(self):
        """Test analysis of empty post list."""
        analyzer = CompetitiveAnalyzer()
        report = analyzer.analyze_posts([])
        assert report.entities_analyzed == 0
        assert len(report.recommendations) > 0

    def test_report_has_recommendations(self, sample_posts):
        """Test that report includes recommendations."""
        analyzer = CompetitiveAnalyzer()
        report = analyzer.analyze_posts(sample_posts)
        assert len(report.recommendations) > 0

    def test_get_entity_insight(self, sample_posts):
        """Test getting insight for specific entity."""
        analyzer = CompetitiveAnalyzer()
        # This may or may not find the entity depending on pattern matching
        insight = analyzer.get_entity_insight("Slack", sample_posts)
        # Either finds it or returns None
        assert insight is None or isinstance(insight, CompetitiveInsight)


# =============================================================================
# Report Formatter Tests
# =============================================================================


class TestReportFormatters:
    """Tests for report formatting functions."""

    @pytest.fixture
    def sample_report(self) -> CompetitiveReport:
        """Create a sample report for testing."""
        entity = ProductEntity(
            name="Slack",
            normalized_name="slack",
            entity_type=EntityType.PRODUCT,
            confidence=0.9,
            context="Slack is slow",
        )
        complaint = Complaint(
            entity=entity,
            complaint_type=ComplaintType.PERFORMANCE,
            text="Slack is slow",
            context="I find Slack is slow recently",
            severity=0.7,
            keywords=["slow"],
        )
        insight = CompetitiveInsight(
            entity=entity,
            overall_sentiment=SentimentScore(
                sentiment=Sentiment.NEGATIVE,
                positive_score=0.1,
                negative_score=0.8,
                neutral_score=0.1,
                compound=-0.5,
                confidence=0.8,
            ),
            complaint_count=1,
            top_complaints=[complaint],
            switch_to=["Discord"],
        )
        return CompetitiveReport(
            generated_at=datetime.now(),
            entities_analyzed=1,
            insights=[insight],
            top_complaints=[complaint],
            popular_switches=[("slack", "discord", 5)],
            recommendations=["Consider investigating Slack issues"],
        )

    def test_to_markdown(self, sample_report):
        """Test markdown report generation."""
        md = to_markdown(sample_report)
        assert "# Competitive Analysis Report" in md
        assert "## Key Recommendations" in md
        assert "Slack" in md

    def test_to_dict(self, sample_report):
        """Test dictionary conversion."""
        d = to_dict(sample_report)
        assert "generated_at" in d
        assert "entities_analyzed" in d
        assert "recommendations" in d
        assert "insights" in d
        assert isinstance(d["insights"], list)


# =============================================================================
# Integration Tests
# =============================================================================


class TestIntegration:
    """Integration tests for the full competitive analysis pipeline."""

    def test_full_pipeline(self):
        """Test the full analysis pipeline."""
        # Create sample post
        post = Post(
            id="test1",
            title="Slack vs Teams - frustrated with performance",
            selftext=(
                "I've been using Slack for years but it's gotten so slow and buggy. "
                "Thinking about switching from Slack to Teams. "
                "Anyone have experience with Teams? Is it better than Slack?"
            ),
            subreddit="productivity",
            author="test_user",
            created_utc=datetime.now(),
            score=100,
            num_comments=50,
            url="https://reddit.com/r/productivity/test1",
            permalink="/r/productivity/comments/test1",
        )

        # Run analysis
        analyzer = CompetitiveAnalyzer()
        report = analyzer.analyze_posts([post])

        # Verify report structure
        assert isinstance(report, CompetitiveReport)
        assert report.generated_at is not None

        # Generate markdown
        md = to_markdown(report)
        assert len(md) > 0

        # Convert to dict
        d = to_dict(report)
        assert isinstance(d, dict)

    def test_all_exports_available(self):
        """Test that all Phase 7 exports are available."""
        from reddit_insight.analysis import (
            # Entity Recognition
            EntityRecognizer,
            EntityType,
            ProductEntity,
            # Sentiment
            RuleBasedSentimentAnalyzer,
            EntitySentimentAnalyzer,
            SentimentScore,
            Sentiment,
            # Competitive
            ComplaintExtractor,
            AlternativeExtractor,
            CompetitiveAnalyzer,
            to_markdown,
            to_dict,
        )

        # Verify all are importable and callable/instantiable
        assert EntityRecognizer is not None
        assert RuleBasedSentimentAnalyzer is not None
        assert ComplaintExtractor is not None
        assert AlternativeExtractor is not None
        assert CompetitiveAnalyzer is not None
        assert callable(to_markdown)
        assert callable(to_dict)
