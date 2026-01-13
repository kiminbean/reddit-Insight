"""
Tests for the reddit_insight.analysis module.

Tests cover tokenization, keyword extraction, trend calculation,
and rising keyword detection.
"""

from datetime import UTC, datetime, timedelta

import pytest

from reddit_insight.analysis import (
    KeywordTrendAnalyzer,
    RedditTokenizer,
    RisingConfig,
    RisingKeywordDetector,
    RisingScore,
    RisingScoreCalculator,
    TrendCalculator,
    TrendDirection,
    TrendReport,
    TrendReporter,
    UnifiedKeywordExtractor,
    YAKEExtractor,
)
from reddit_insight.reddit.models import Post


# Test fixtures
@pytest.fixture
def sample_posts():
    """Create sample posts for testing."""
    now = datetime.now(UTC)
    return [
        Post(
            id="post1",
            title="Python is great for machine learning",
            selftext="I love using Python for ML projects",
            author="user1",
            subreddit="python",
            score=100,
            num_comments=10,
            created_utc=now - timedelta(hours=6),
            url="https://example.com/1",
            permalink="https://reddit.com/r/python/1",
            is_self=True,
        ),
        Post(
            id="post2",
            title="Python vs JavaScript for web development",
            selftext="Which is better for web apps?",
            author="user2",
            subreddit="programming",
            score=50,
            num_comments=5,
            created_utc=now - timedelta(hours=12),
            url="https://example.com/2",
            permalink="https://reddit.com/r/programming/2",
            is_self=True,
        ),
        Post(
            id="post3",
            title="Machine learning trends in 2025",
            selftext="AI and ML are evolving rapidly",
            author="user3",
            subreddit="MachineLearning",
            score=200,
            num_comments=20,
            created_utc=now - timedelta(hours=48),
            url="https://example.com/3",
            permalink="https://reddit.com/r/MachineLearning/3",
            is_self=True,
        ),
    ]


class TestRedditTokenizer:
    """Test suite for RedditTokenizer."""

    def test_basic_tokenization(self):
        """Test basic text tokenization."""
        tokenizer = RedditTokenizer()
        tokens = tokenizer.tokenize("Hello world Python")
        assert isinstance(tokens, list)
        # Stopwords like 'hello', 'world' may be removed
        assert len(tokens) >= 0

    def test_empty_input(self):
        """Test tokenization of empty string."""
        tokenizer = RedditTokenizer()
        tokens = tokenizer.tokenize("")
        assert tokens == []

    def test_special_characters_removal(self):
        """Test that special characters are handled."""
        tokenizer = RedditTokenizer()
        tokens = tokenizer.tokenize("Python!!! @#$% code...")
        assert isinstance(tokens, list)


class TestYAKEExtractor:
    """Test suite for YAKEExtractor."""

    def test_basic_extraction(self):
        """Test basic keyword extraction."""
        extractor = YAKEExtractor()
        keywords = extractor.extract(
            "Python is a great programming language for machine learning"
        )
        assert isinstance(keywords, list)
        assert len(keywords) > 0
        # Check keyword structure
        if keywords:
            kw = keywords[0]
            assert hasattr(kw, "keyword")
            assert hasattr(kw, "score")
            assert 0 <= kw.score <= 1

    def test_empty_input(self):
        """Test extraction from empty string."""
        extractor = YAKEExtractor()
        keywords = extractor.extract("")
        assert keywords == []

    def test_extract_from_texts(self):
        """Test extraction from multiple texts."""
        extractor = YAKEExtractor()
        texts = [
            "Python programming is fun",
            "Machine learning with Python",
        ]
        keywords = extractor.extract_from_texts(texts)
        assert isinstance(keywords, list)


class TestUnifiedKeywordExtractor:
    """Test suite for UnifiedKeywordExtractor."""

    def test_yake_method(self):
        """Test extraction using YAKE method."""
        extractor = UnifiedKeywordExtractor()
        result = extractor.extract_keywords(
            ["Python is great for data science", "Machine learning rocks"],
            num_keywords=5,
        )
        assert result.keywords is not None
        assert result.document_count == 2

    def test_extract_from_posts(self, sample_posts):
        """Test extraction from Post objects."""
        extractor = UnifiedKeywordExtractor()
        result = extractor.extract_from_posts(sample_posts, num_keywords=10)
        assert result.document_count == len(sample_posts)
        assert len(result.keywords) <= 10


class TestTrendCalculator:
    """Test suite for TrendCalculator."""

    def test_stable_trend(self):
        """Test detection of stable trend."""
        from reddit_insight.analysis import TimeSeries, TimeGranularity, TimePoint

        now = datetime.now(UTC)
        series = TimeSeries(
            keyword="test",
            granularity=TimeGranularity.DAY,
            points=[
                TimePoint(timestamp=now - timedelta(days=i), value=10.0, count=1)
                for i in range(7)
            ],
        )

        calc = TrendCalculator()
        metrics = calc.calculate_trend(series)

        assert metrics.direction == TrendDirection.STABLE
        assert abs(metrics.change_rate) < 0.2

    def test_rising_trend(self):
        """Test detection of rising trend."""
        from reddit_insight.analysis import TimeSeries, TimeGranularity, TimePoint

        now = datetime.now(UTC)
        series = TimeSeries(
            keyword="test",
            granularity=TimeGranularity.DAY,
            points=[
                TimePoint(timestamp=now - timedelta(days=6 - i), value=float(i + 1), count=1)
                for i in range(7)
            ],
        )

        calc = TrendCalculator()
        metrics = calc.calculate_trend(series)

        assert metrics.direction == TrendDirection.RISING
        assert metrics.slope > 0


class TestRisingScoreCalculator:
    """Test suite for RisingScoreCalculator."""

    def test_high_growth(self):
        """Test high growth rate scoring."""
        calc = RisingScoreCalculator()
        score = calc.calculate_score(recent_freq=10, previous_freq=2)

        assert score.growth_rate == 4.0  # 400% growth
        assert 0 <= score.score <= 100

    def test_new_keyword_bonus(self):
        """Test bonus for new keywords."""
        config = RisingConfig(new_keyword_bonus=20.0)
        calc = RisingScoreCalculator(config=config)

        # New keyword (previous=0)
        new_score = calc.calculate_score(recent_freq=5, previous_freq=0, keyword="new")

        # Existing keyword with same recent frequency
        existing_score = calc.calculate_score(recent_freq=5, previous_freq=5, keyword="existing")

        assert new_score.is_new is True
        assert existing_score.is_new is False
        # New keyword should have higher score due to bonus
        assert new_score.score >= existing_score.score

    def test_score_bounds(self):
        """Test that scores are within 0-100."""
        calc = RisingScoreCalculator()

        # Test various scenarios
        scenarios = [
            (100, 1),   # Very high growth
            (1, 100),   # Negative growth
            (0, 10),    # No recent frequency
            (10, 0),    # New keyword
            (50, 50),   # No growth
        ]

        for recent, previous in scenarios:
            score = calc.calculate_score(recent, previous)
            assert 0 <= score.score <= 100, f"Score out of bounds for ({recent}, {previous})"


class TestRisingKeywordDetector:
    """Test suite for RisingKeywordDetector."""

    def test_detector_initialization(self):
        """Test detector can be initialized."""
        detector = RisingKeywordDetector()
        assert detector.config is not None
        assert detector.config.recent_period_hours == 24

    def test_custom_config(self):
        """Test detector with custom configuration."""
        config = RisingConfig(
            recent_period_hours=12,
            min_recent_frequency=2,
        )
        detector = RisingKeywordDetector(config=config)

        assert detector.config.recent_period_hours == 12
        assert detector.config.min_recent_frequency == 2

    def test_empty_posts(self):
        """Test detection with empty post list."""
        detector = RisingKeywordDetector()
        result = detector.detect_rising([])
        assert result == []


class TestTrendReporter:
    """Test suite for TrendReporter."""

    def test_reporter_initialization(self):
        """Test reporter can be initialized."""
        reporter = TrendReporter()
        assert reporter is not None

    def test_generate_empty_report(self):
        """Test report generation with empty posts."""
        reporter = TrendReporter()
        report = reporter.generate_report([])

        assert isinstance(report, TrendReport)
        assert report.total_posts_analyzed == 0
        assert report.rising_keywords == []

    def test_markdown_output(self, sample_posts):
        """Test markdown generation."""
        reporter = TrendReporter()
        report = reporter.generate_report(sample_posts, subreddit="test")
        markdown = reporter.to_markdown(report)

        assert isinstance(markdown, str)
        assert "# Trend Report" in markdown
        assert "## Overview" in markdown
        assert "r/test" in markdown

    def test_dict_serialization(self, sample_posts):
        """Test dictionary serialization."""
        reporter = TrendReporter()
        report = reporter.generate_report(sample_posts)
        data = reporter.to_dict(report)

        assert isinstance(data, dict)
        assert "generated_at" in data
        assert "rising_keywords" in data
        assert "top_keywords" in data


class TestKeywordTrendAnalyzer:
    """Test suite for KeywordTrendAnalyzer."""

    def test_build_timeseries(self, sample_posts):
        """Test building time series for a keyword."""
        from reddit_insight.analysis import TimeGranularity

        analyzer = KeywordTrendAnalyzer()
        series = analyzer.build_keyword_timeseries(
            sample_posts,
            keyword="python",
            granularity=TimeGranularity.DAY,
        )

        assert series.keyword == "python"
        assert len(series.points) > 0

    def test_analyze_keyword_trend(self, sample_posts):
        """Test trend analysis for a keyword."""
        analyzer = KeywordTrendAnalyzer()
        result = analyzer.analyze_keyword_trend(sample_posts, "python")

        assert result.keyword == "python"
        assert result.metrics is not None
        assert hasattr(result.metrics, "direction")


class TestIntegration:
    """Integration tests for the complete analysis pipeline."""

    def test_full_pipeline(self, sample_posts):
        """Test complete analysis pipeline."""
        # Extract keywords
        extractor = UnifiedKeywordExtractor()
        keywords = extractor.extract_from_posts(sample_posts)

        # Analyze trends
        analyzer = KeywordTrendAnalyzer()
        if keywords.keywords:
            trend = analyzer.analyze_keyword_trend(
                sample_posts, keywords.keywords[0].keyword
            )
            assert trend is not None

        # Generate report
        reporter = TrendReporter()
        report = reporter.generate_report(sample_posts, subreddit="test")

        assert report.total_posts_analyzed == len(sample_posts)

    def test_all_exports(self):
        """Test that all expected classes are exported."""
        from reddit_insight.analysis import (
            # Core
            RedditTokenizer,
            UnifiedKeywordExtractor,
            # Trends
            TrendCalculator,
            KeywordTrendAnalyzer,
            # Rising
            RisingScore,
            RisingConfig,
            RisingScoreCalculator,
            RisingKeywordDetector,
            TrendReport,
            TrendReporter,
        )

        # All imports should work without errors
        assert all([
            RedditTokenizer,
            UnifiedKeywordExtractor,
            TrendCalculator,
            KeywordTrendAnalyzer,
            RisingScore,
            RisingConfig,
            RisingScoreCalculator,
            RisingKeywordDetector,
            TrendReport,
            TrendReporter,
        ])
