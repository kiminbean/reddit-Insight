"""
Competitive analysis module for product/service comparison.

Provides complaint extraction, alternative comparison detection, and
competitive insights generation for Reddit discussions.

Example:
    >>> from reddit_insight.analysis.competitive import CompetitiveAnalyzer
    >>> analyzer = CompetitiveAnalyzer()
    >>> from reddit_insight.reddit.models import Post
    >>> posts = [Post(id="1", title="Slack is slow", ...)]
    >>> report = analyzer.analyze_posts(posts)
    >>> print(report.recommendations[0])
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from reddit_insight.reddit.models import Post

from reddit_insight.analysis.entity_recognition import (
    EntityRecognizer,
    ProductEntity,
    EntityType,
)
from reddit_insight.analysis.sentiment import (
    RuleBasedSentimentAnalyzer,
    EntitySentimentAnalyzer,
    SentimentScore,
    Sentiment,
)


# ============================================================================
# Complaint Types and Data Structures
# ============================================================================


class ComplaintType(Enum):
    """
    Complaint type enumeration for categorizing user complaints.

    Attributes:
        FUNCTIONALITY: Functionality issues (feature not working)
        PERFORMANCE: Performance issues (slow, lag)
        USABILITY: Usability issues (hard to use, confusing)
        PRICING: Pricing issues (expensive, overpriced)
        SUPPORT: Support issues (poor customer service)
        RELIABILITY: Reliability issues (crashes, unstable)
        OTHER: Other unclassified complaints
    """

    FUNCTIONALITY = "functionality"
    PERFORMANCE = "performance"
    USABILITY = "usability"
    PRICING = "pricing"
    SUPPORT = "support"
    RELIABILITY = "reliability"
    OTHER = "other"

    @property
    def description(self) -> str:
        """Get human-readable description for the complaint type."""
        descriptions = {
            ComplaintType.FUNCTIONALITY: "Functionality issue",
            ComplaintType.PERFORMANCE: "Performance issue",
            ComplaintType.USABILITY: "Usability issue",
            ComplaintType.PRICING: "Pricing issue",
            ComplaintType.SUPPORT: "Support issue",
            ComplaintType.RELIABILITY: "Reliability issue",
            ComplaintType.OTHER: "Other issue",
        }
        return descriptions.get(self, "Unknown issue")


@dataclass
class Complaint:
    """
    Represents a complaint extracted from text.

    Attributes:
        entity: The product/service being complained about
        complaint_type: Type of complaint
        text: Original matched text
        context: Surrounding context
        severity: Severity score (0-1, higher is more severe)
        keywords: Keywords that triggered the complaint detection
    """

    entity: ProductEntity
    complaint_type: ComplaintType
    text: str
    context: str
    severity: float
    keywords: list[str] = field(default_factory=list)

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"Complaint('{self.entity.name}', "
            f"type={self.complaint_type.value}, "
            f"severity={self.severity:.2f})"
        )


# ============================================================================
# Complaint Patterns
# ============================================================================

# Patterns for extracting complaints from text
# Each tuple: (pattern_id, regex, ComplaintType, severity_base)
COMPLAINT_PATTERNS: list[tuple[str, str, ComplaintType, float]] = [
    # Performance issues - slow, buggy
    (
        "perf_slow_buggy",
        r"([A-Z][a-zA-Z0-9]*)\s+(?:is|was|has been)\s+(?:so\s+)?(?:slow|buggy|broken|terrible|awful)",
        ComplaintType.PERFORMANCE,
        0.7,
    ),
    # Generic problems/issues
    (
        "generic_problem",
        r"(?:problem|issue|trouble)\s+with\s+([A-Z][a-zA-Z0-9]*)",
        ComplaintType.OTHER,
        0.5,
    ),
    # Functionality not working
    (
        "func_not_working",
        r"([A-Z][a-zA-Z0-9]*)\s+(?:doesn't|won't|can't|couldn't)\s+\w+",
        ComplaintType.FUNCTIONALITY,
        0.6,
    ),
    # Hate expressions
    (
        "hate_expr",
        r"(?:hate|hated|hating)\s+([A-Z][a-zA-Z0-9]*)",
        ComplaintType.OTHER,
        0.8,
    ),
    # Reliability issues - crashes, freezing
    (
        "reliability_crash",
        r"([A-Z][a-zA-Z0-9]*)\s+(?:keeps?|kept)\s+(?:crashing|freezing|failing)",
        ComplaintType.RELIABILITY,
        0.8,
    ),
    # Usability issues
    (
        "usability_confusing",
        r"([A-Z][a-zA-Z0-9]*)\s+(?:is|was)\s+(?:so\s+)?(?:confusing|complicated|hard to use|difficult)",
        ComplaintType.USABILITY,
        0.6,
    ),
    # Pricing issues
    (
        "pricing_expensive",
        r"([A-Z][a-zA-Z0-9]*)\s+(?:is|was)\s+(?:too\s+)?(?:expensive|overpriced|pricey)",
        ComplaintType.PRICING,
        0.6,
    ),
    # Support issues
    (
        "support_poor",
        r"([A-Z][a-zA-Z0-9]*)\s+(?:has\s+)?(?:terrible|awful|poor|bad)\s+(?:support|customer service)",
        ComplaintType.SUPPORT,
        0.7,
    ),
    # Frustration expressions
    (
        "frustration",
        r"(?:frustrated|annoyed|disappointed)\s+(?:with|by)\s+([A-Z][a-zA-Z0-9]*)",
        ComplaintType.OTHER,
        0.7,
    ),
]

# Keywords for complaint type classification
COMPLAINT_TYPE_KEYWORDS: dict[ComplaintType, set[str]] = {
    ComplaintType.FUNCTIONALITY: {
        "broken", "not working", "doesn't work", "won't work", "bug", "bugs",
        "feature", "missing", "incomplete", "fails", "failed",
    },
    ComplaintType.PERFORMANCE: {
        "slow", "sluggish", "lag", "laggy", "freeze", "freezing", "hang",
        "unresponsive", "crawl", "takes forever", "memory", "cpu", "battery",
    },
    ComplaintType.USABILITY: {
        "confusing", "complicated", "hard to use", "difficult", "unintuitive",
        "clunky", "awkward", "poor ux", "bad ui", "user interface",
    },
    ComplaintType.PRICING: {
        "expensive", "overpriced", "pricey", "costly", "price", "subscription",
        "fee", "charge", "pay", "cost", "money", "ripoff", "scam",
    },
    ComplaintType.SUPPORT: {
        "support", "customer service", "help", "response", "ticket",
        "contact", "representative", "chat", "email",
    },
    ComplaintType.RELIABILITY: {
        "crash", "crashes", "crashing", "unstable", "unreliable", "fail",
        "failing", "down", "outage", "error", "errors", "glitch",
    },
}


# ============================================================================
# Complaint Extractor
# ============================================================================


@dataclass
class ComplaintExtractor:
    """
    Extracts complaints about products/services from text.

    Uses pattern matching and sentiment analysis to identify complaints
    and classify them by type and severity.

    Example:
        >>> extractor = ComplaintExtractor()
        >>> complaints = extractor.extract("Slack is so slow and keeps crashing")
        >>> print(complaints[0].complaint_type)
        ComplaintType.PERFORMANCE
    """

    _entity_recognizer: EntityRecognizer | None = field(default=None, repr=False)
    _sentiment_analyzer: RuleBasedSentimentAnalyzer | None = field(default=None, repr=False)
    _compiled_patterns: dict[str, re.Pattern[str]] = field(
        default_factory=dict, init=False, repr=False
    )

    def __post_init__(self) -> None:
        """Initialize dependencies and compile patterns."""
        if self._entity_recognizer is None:
            self._entity_recognizer = EntityRecognizer()
        if self._sentiment_analyzer is None:
            self._sentiment_analyzer = RuleBasedSentimentAnalyzer()

        # Compile patterns
        for pattern_id, regex, _, _ in COMPLAINT_PATTERNS:
            try:
                self._compiled_patterns[pattern_id] = re.compile(regex, re.IGNORECASE)
            except re.error:
                pass

    def _classify_complaint_type(self, text: str) -> ComplaintType:
        """
        Classify the complaint type based on text keywords.

        Args:
            text: Text to classify

        Returns:
            ComplaintType classification
        """
        text_lower = text.lower()

        # Count keyword matches for each type
        type_scores: dict[ComplaintType, int] = {}
        for ctype, keywords in COMPLAINT_TYPE_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > 0:
                type_scores[ctype] = score

        if not type_scores:
            return ComplaintType.OTHER

        # Return type with highest score
        return max(type_scores, key=lambda t: type_scores[t])

    def _calculate_severity(self, sentiment: SentimentScore) -> float:
        """
        Calculate complaint severity based on sentiment score.

        More negative sentiment = higher severity.

        Args:
            sentiment: SentimentScore from analysis

        Returns:
            Severity score (0-1)
        """
        # Map compound score (-1 to 1) to severity (0 to 1)
        # More negative = higher severity
        if sentiment.compound >= 0:
            # Positive sentiment = low severity
            return 0.1
        else:
            # Negative compound ranges from 0 to -1
            # Map to severity 0.3 to 1.0
            return 0.3 + (abs(sentiment.compound) * 0.7)

    def _extract_context(
        self, text: str, start: int, end: int, window: int = 100
    ) -> str:
        """
        Extract context around a match.

        Args:
            text: Full text
            start: Match start position
            end: Match end position
            window: Context window size

        Returns:
            Context string
        """
        ctx_start = max(0, start - window)
        ctx_end = min(len(text), end + window)

        # Expand to word boundaries
        while ctx_start > 0 and text[ctx_start - 1].isalnum():
            ctx_start -= 1
        while ctx_end < len(text) and text[ctx_end].isalnum():
            ctx_end += 1

        return text[ctx_start:ctx_end].strip()

    def _extract_keywords(self, text: str) -> list[str]:
        """
        Extract complaint-related keywords from text.

        Args:
            text: Text to analyze

        Returns:
            List of detected keywords
        """
        text_lower = text.lower()
        keywords = []

        for keyword_set in COMPLAINT_TYPE_KEYWORDS.values():
            for kw in keyword_set:
                if kw in text_lower and kw not in keywords:
                    keywords.append(kw)

        return keywords[:5]  # Limit to 5 keywords

    def extract(self, text: str) -> list[Complaint]:
        """
        Extract complaints from text.

        Args:
            text: Input text to analyze

        Returns:
            List of Complaint objects
        """
        if not text or not text.strip():
            return []

        complaints: list[Complaint] = []
        seen_entities: set[str] = set()

        assert self._sentiment_analyzer is not None
        assert self._entity_recognizer is not None

        # Try each complaint pattern
        for pattern_id, _, base_type, base_severity in COMPLAINT_PATTERNS:
            compiled = self._compiled_patterns.get(pattern_id)
            if compiled is None:
                continue

            for match in compiled.finditer(text):
                # Get entity name from capture group
                entity_name = match.group(1)
                if not entity_name:
                    continue

                # Skip if already processed this entity
                entity_key = entity_name.lower()
                if entity_key in seen_entities:
                    continue
                seen_entities.add(entity_key)

                # Extract context
                context = self._extract_context(text, match.start(), match.end())

                # Analyze sentiment of context
                sentiment = self._sentiment_analyzer.analyze(context)

                # Calculate severity
                severity = max(base_severity, self._calculate_severity(sentiment))

                # Classify complaint type (may override base_type if more specific)
                complaint_type = self._classify_complaint_type(context)
                if complaint_type == ComplaintType.OTHER:
                    complaint_type = base_type

                # Create entity
                entity = ProductEntity(
                    name=entity_name,
                    normalized_name=entity_name.lower(),
                    entity_type=EntityType.PRODUCT,
                    confidence=0.7,
                    context=match.group(0),
                )

                # Extract keywords
                keywords = self._extract_keywords(context)

                complaints.append(
                    Complaint(
                        entity=entity,
                        complaint_type=complaint_type,
                        text=match.group(0),
                        context=context,
                        severity=severity,
                        keywords=keywords,
                    )
                )

        # Sort by severity (highest first)
        complaints.sort(key=lambda c: c.severity, reverse=True)
        return complaints


# ============================================================================
# Comparison Types and Data Structures
# ============================================================================


class ComparisonType(Enum):
    """
    Comparison type enumeration for alternative seeking patterns.

    Attributes:
        SWITCH: Switching from one product to another
        ALTERNATIVE: Seeking alternatives
        VERSUS: Direct comparison (A vs B)
        BETTER_THAN: Superiority comparison
        RECOMMENDATION: Recommendation of alternatives
    """

    SWITCH = "switch"
    ALTERNATIVE = "alternative"
    VERSUS = "versus"
    BETTER_THAN = "better_than"
    RECOMMENDATION = "recommendation"

    @property
    def description(self) -> str:
        """Get human-readable description for the comparison type."""
        descriptions = {
            ComparisonType.SWITCH: "Product switch",
            ComparisonType.ALTERNATIVE: "Alternative seeking",
            ComparisonType.VERSUS: "Direct comparison",
            ComparisonType.BETTER_THAN: "Superiority comparison",
            ComparisonType.RECOMMENDATION: "Recommendation",
        }
        return descriptions.get(self, "Unknown comparison")


@dataclass
class AlternativeComparison:
    """
    Represents a comparison or alternative mention between products.

    Attributes:
        source_entity: The original product being compared from
        target_entity: The alternative product (may be None for seeking patterns)
        comparison_type: Type of comparison
        text: Original matched text
        context: Surrounding context
        sentiment_towards_source: Sentiment about source product
        sentiment_towards_target: Sentiment about target product (if available)
    """

    source_entity: ProductEntity
    target_entity: ProductEntity | None
    comparison_type: ComparisonType
    text: str
    context: str
    sentiment_towards_source: SentimentScore
    sentiment_towards_target: SentimentScore | None = None

    def __repr__(self) -> str:
        """String representation for debugging."""
        target = self.target_entity.name if self.target_entity else "?"
        return (
            f"AlternativeComparison({self.source_entity.name} -> {target}, "
            f"type={self.comparison_type.value})"
        )


# ============================================================================
# Alternative Patterns
# ============================================================================

# Patterns for extracting alternative comparisons
# Each tuple: (pattern_id, regex, ComparisonType, has_two_entities)
ALTERNATIVE_PATTERNS: list[tuple[str, str, ComparisonType, bool]] = [
    # Switch patterns - "switched from X to Y"
    (
        "switch_from_to",
        r"(?:switched|moved|migrated)\s+from\s+([A-Z][a-zA-Z0-9]*)\s+to\s+([A-Z][a-zA-Z0-9]*)",
        ComparisonType.SWITCH,
        True,
    ),
    # Alternative seeking - "X alternative", "alternative to X"
    (
        "alt_seeking",
        r"([A-Z][a-zA-Z0-9]*)\s+(?:alternative|replacement)",
        ComparisonType.ALTERNATIVE,
        False,
    ),
    (
        "alt_to",
        r"alternative\s+to\s+([A-Z][a-zA-Z0-9]*)",
        ComparisonType.ALTERNATIVE,
        False,
    ),
    # Versus patterns - "X vs Y"
    (
        "versus",
        r"([A-Z][a-zA-Z0-9]*)\s+vs\.?\s+([A-Z][a-zA-Z0-9]*)",
        ComparisonType.VERSUS,
        True,
    ),
    # Better than patterns
    (
        "better_than",
        r"([A-Z][a-zA-Z0-9]*)\s+(?:is\s+)?better\s+than\s+([A-Z][a-zA-Z0-9]*)",
        ComparisonType.BETTER_THAN,
        True,
    ),
    # Recommendation patterns
    (
        "recommend_over",
        r"(?:recommend|prefer)\s+([A-Z][a-zA-Z0-9]*)\s+over\s+([A-Z][a-zA-Z0-9]*)",
        ComparisonType.RECOMMENDATION,
        True,
    ),
    # "try X instead of Y"
    (
        "try_instead",
        r"try\s+([A-Z][a-zA-Z0-9]*)\s+instead\s+of\s+([A-Z][a-zA-Z0-9]*)",
        ComparisonType.RECOMMENDATION,
        True,
    ),
    # "replaced X with Y"
    (
        "replaced_with",
        r"replaced\s+([A-Z][a-zA-Z0-9]*)\s+with\s+([A-Z][a-zA-Z0-9]*)",
        ComparisonType.SWITCH,
        True,
    ),
]


# ============================================================================
# Alternative Extractor
# ============================================================================


@dataclass
class AlternativeExtractor:
    """
    Extracts alternative comparisons and switch patterns from text.

    Identifies when users are comparing products, seeking alternatives,
    or describing switches between products.

    Example:
        >>> extractor = AlternativeExtractor()
        >>> alts = extractor.extract("I switched from Evernote to Notion")
        >>> print(alts[0].source_entity.name, "->", alts[0].target_entity.name)
        Evernote -> Notion
    """

    _entity_recognizer: EntityRecognizer | None = field(default=None, repr=False)
    _sentiment_analyzer: RuleBasedSentimentAnalyzer | None = field(default=None, repr=False)
    _compiled_patterns: dict[str, re.Pattern[str]] = field(
        default_factory=dict, init=False, repr=False
    )

    def __post_init__(self) -> None:
        """Initialize dependencies and compile patterns."""
        if self._entity_recognizer is None:
            self._entity_recognizer = EntityRecognizer()
        if self._sentiment_analyzer is None:
            self._sentiment_analyzer = RuleBasedSentimentAnalyzer()

        # Compile patterns
        for pattern_id, regex, _, _ in ALTERNATIVE_PATTERNS:
            try:
                self._compiled_patterns[pattern_id] = re.compile(regex, re.IGNORECASE)
            except re.error:
                pass

    def _create_entity(self, name: str, context: str) -> ProductEntity:
        """Create a ProductEntity from name and context."""
        return ProductEntity(
            name=name,
            normalized_name=name.lower(),
            entity_type=EntityType.PRODUCT,
            confidence=0.7,
            context=context,
        )

    def _extract_context(
        self, text: str, start: int, end: int, window: int = 100
    ) -> str:
        """Extract context around a match."""
        ctx_start = max(0, start - window)
        ctx_end = min(len(text), end + window)

        while ctx_start > 0 and text[ctx_start - 1].isalnum():
            ctx_start -= 1
        while ctx_end < len(text) and text[ctx_end].isalnum():
            ctx_end += 1

        return text[ctx_start:ctx_end].strip()

    def _analyze_entity_sentiment(
        self, text: str, entity_name: str
    ) -> SentimentScore:
        """Analyze sentiment towards an entity in text."""
        assert self._sentiment_analyzer is not None

        # Find context around entity mention
        text_lower = text.lower()
        entity_lower = entity_name.lower()
        pos = text_lower.find(entity_lower)

        if pos >= 0:
            # Get surrounding context
            start = max(0, pos - 50)
            end = min(len(text), pos + len(entity_name) + 50)
            context = text[start:end]
            return self._sentiment_analyzer.analyze(context)
        else:
            return self._sentiment_analyzer.analyze(text)

    def extract(self, text: str) -> list[AlternativeComparison]:
        """
        Extract alternative comparisons from text.

        Args:
            text: Input text to analyze

        Returns:
            List of AlternativeComparison objects
        """
        if not text or not text.strip():
            return []

        comparisons: list[AlternativeComparison] = []
        seen_pairs: set[tuple[str, str | None]] = set()

        for pattern_id, _, comp_type, has_two_entities in ALTERNATIVE_PATTERNS:
            compiled = self._compiled_patterns.get(pattern_id)
            if compiled is None:
                continue

            for match in compiled.finditer(text):
                # Extract entity names
                source_name = match.group(1)
                target_name = match.group(2) if has_two_entities and len(match.groups()) > 1 else None

                if not source_name:
                    continue

                # Skip duplicates
                pair_key = (source_name.lower(), target_name.lower() if target_name else None)
                if pair_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)

                # Extract context
                context = self._extract_context(text, match.start(), match.end())

                # Create entities
                source_entity = self._create_entity(source_name, match.group(0))
                target_entity = self._create_entity(target_name, match.group(0)) if target_name else None

                # Analyze sentiment
                source_sentiment = self._analyze_entity_sentiment(context, source_name)
                target_sentiment = (
                    self._analyze_entity_sentiment(context, target_name)
                    if target_name
                    else None
                )

                comparisons.append(
                    AlternativeComparison(
                        source_entity=source_entity,
                        target_entity=target_entity,
                        comparison_type=comp_type,
                        text=match.group(0),
                        context=context,
                        sentiment_towards_source=source_sentiment,
                        sentiment_towards_target=target_sentiment,
                    )
                )

        return comparisons

    def extract_switches(self, texts: list[str]) -> dict[str, list[str]]:
        """
        Extract and aggregate switch patterns from multiple texts.

        Args:
            texts: List of texts to analyze

        Returns:
            Dictionary mapping source products to list of target products
        """
        switches: dict[str, list[str]] = {}

        for text in texts:
            comparisons = self.extract(text)
            for comp in comparisons:
                if comp.comparison_type == ComparisonType.SWITCH and comp.target_entity:
                    source = comp.source_entity.normalized_name
                    target = comp.target_entity.normalized_name
                    if source not in switches:
                        switches[source] = []
                    if target not in switches[source]:
                        switches[source].append(target)

        return switches


# ============================================================================
# Competitive Insight and Report
# ============================================================================


@dataclass
class CompetitiveInsight:
    """
    Competitive insight for a single entity.

    Aggregates complaints, sentiment, and alternative mentions for a product.

    Attributes:
        entity: The product/service entity
        overall_sentiment: Aggregated sentiment score
        complaint_count: Total number of complaints
        top_complaints: Top complaints by severity
        alternatives_mentioned: Products mentioned as alternatives
        switch_to: Products people switch to from this product
        switch_from: Products people switch from to this product
    """

    entity: ProductEntity
    overall_sentiment: SentimentScore
    complaint_count: int
    top_complaints: list[Complaint] = field(default_factory=list)
    alternatives_mentioned: list[str] = field(default_factory=list)
    switch_to: list[str] = field(default_factory=list)
    switch_from: list[str] = field(default_factory=list)

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"CompetitiveInsight('{self.entity.name}', "
            f"complaints={self.complaint_count}, "
            f"sentiment={self.overall_sentiment.compound:.2f})"
        )


@dataclass
class CompetitiveReport:
    """
    Comprehensive competitive analysis report.

    Summarizes insights across all analyzed entities.

    Attributes:
        generated_at: Report generation timestamp
        entities_analyzed: Number of entities analyzed
        insights: List of entity-level insights
        top_complaints: Overall top complaints
        popular_switches: Most common product switches (from, to, count)
        recommendations: Generated recommendations
    """

    generated_at: datetime
    entities_analyzed: int
    insights: list[CompetitiveInsight] = field(default_factory=list)
    top_complaints: list[Complaint] = field(default_factory=list)
    popular_switches: list[tuple[str, str, int]] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"CompetitiveReport(entities={self.entities_analyzed}, "
            f"insights={len(self.insights)}, "
            f"complaints={len(self.top_complaints)})"
        )


# ============================================================================
# Competitive Analyzer
# ============================================================================


@dataclass
class CompetitiveAnalyzer:
    """
    Unified competitive analysis system.

    Combines entity recognition, sentiment analysis, complaint extraction,
    and alternative detection for comprehensive competitive insights.

    Example:
        >>> analyzer = CompetitiveAnalyzer()
        >>> posts = [Post(id="1", title="Slack is slow", ...)]
        >>> report = analyzer.analyze_posts(posts)
        >>> print(to_markdown(report))
    """

    _entity_recognizer: EntityRecognizer | None = field(default=None, repr=False)
    _sentiment_analyzer: EntitySentimentAnalyzer | None = field(default=None, repr=False)
    _complaint_extractor: ComplaintExtractor | None = field(default=None, repr=False)
    _alternative_extractor: AlternativeExtractor | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        """Initialize all sub-analyzers."""
        if self._entity_recognizer is None:
            self._entity_recognizer = EntityRecognizer()
        if self._sentiment_analyzer is None:
            self._sentiment_analyzer = EntitySentimentAnalyzer()
        if self._complaint_extractor is None:
            self._complaint_extractor = ComplaintExtractor()
        if self._alternative_extractor is None:
            self._alternative_extractor = AlternativeExtractor()

    def _combine_post_text(self, post: "Post") -> str:
        """Combine post title and selftext."""
        parts = [post.title]
        if post.selftext:
            parts.append(post.selftext)
        return " ".join(parts)

    def _generate_recommendations(
        self,
        insights: list[CompetitiveInsight],
        switches: list[tuple[str, str, int]],
    ) -> list[str]:
        """
        Generate actionable recommendations from insights.

        Args:
            insights: Entity insights
            switches: Popular switch patterns

        Returns:
            List of recommendation strings
        """
        recommendations: list[str] = []

        # Find entities with negative sentiment
        negative_entities = [
            i for i in insights
            if i.overall_sentiment.sentiment == Sentiment.NEGATIVE
        ]
        if negative_entities:
            names = ", ".join(i.entity.name for i in negative_entities[:3])
            recommendations.append(
                f"Products with negative sentiment: {names}. "
                "Consider investigating their pain points for opportunity."
            )

        # Find common complaint types
        all_complaints = []
        for insight in insights:
            all_complaints.extend(insight.top_complaints)

        if all_complaints:
            type_counts = Counter(c.complaint_type for c in all_complaints)
            most_common = type_counts.most_common(1)
            if most_common:
                ctype, count = most_common[0]
                recommendations.append(
                    f"Most common complaint type: {ctype.description} ({count} occurrences). "
                    "Products addressing this issue may find market opportunity."
                )

        # Identify switch opportunities
        if switches:
            most_switched = switches[0]
            from_name, to_name, count = most_switched
            recommendations.append(
                f"Popular product switch: {from_name} -> {to_name} ({count} mentions). "
                f"Investigate why users are leaving {from_name}."
            )

        # Default recommendation if none generated
        if not recommendations:
            recommendations.append(
                "Continue monitoring discussions for emerging trends and pain points."
            )

        return recommendations

    def analyze_posts(self, posts: list["Post"]) -> CompetitiveReport:
        """
        Analyze posts for competitive insights.

        Args:
            posts: List of Post objects to analyze

        Returns:
            CompetitiveReport with comprehensive insights
        """
        if not posts:
            return CompetitiveReport(
                generated_at=datetime.now(),
                entities_analyzed=0,
                recommendations=["No posts provided for analysis."],
            )

        assert self._entity_recognizer is not None
        assert self._sentiment_analyzer is not None
        assert self._complaint_extractor is not None
        assert self._alternative_extractor is not None

        # Collect all text
        all_texts = [self._combine_post_text(p) for p in posts]
        combined_text = " ".join(all_texts)

        # Extract entities
        entity_dict = self._entity_recognizer.recognize_in_posts(posts)

        # Extract complaints
        all_complaints: list[Complaint] = []
        for text in all_texts:
            complaints = self._complaint_extractor.extract(text)
            all_complaints.extend(complaints)

        # Extract alternatives
        all_alternatives: list[AlternativeComparison] = []
        for text in all_texts:
            alternatives = self._alternative_extractor.extract(text)
            all_alternatives.extend(alternatives)

        # Aggregate switch patterns
        switch_counter: Counter[tuple[str, str]] = Counter()
        for alt in all_alternatives:
            if alt.comparison_type == ComparisonType.SWITCH and alt.target_entity:
                key = (alt.source_entity.normalized_name, alt.target_entity.normalized_name)
                switch_counter[key] += 1

        popular_switches = [
            (from_name, to_name, count)
            for (from_name, to_name), count in switch_counter.most_common(10)
        ]

        # Get entity sentiments
        entity_sentiments = self._sentiment_analyzer.analyze_posts(posts)

        # Build insights per entity
        insights: list[CompetitiveInsight] = []
        for name, entity in entity_dict.items():
            # Get sentiment
            sentiment_data = entity_sentiments.get(name)
            if sentiment_data:
                overall_sentiment = sentiment_data.sentiment
            else:
                overall_sentiment = SentimentScore(
                    sentiment=Sentiment.NEUTRAL,
                    positive_score=0.0,
                    negative_score=0.0,
                    neutral_score=1.0,
                    compound=0.0,
                    confidence=0.5,
                )

            # Filter complaints for this entity
            entity_complaints = [
                c for c in all_complaints
                if c.entity.normalized_name == name
            ]
            entity_complaints.sort(key=lambda c: c.severity, reverse=True)

            # Find alternatives mentioned with this entity
            alternatives_mentioned: list[str] = []
            switch_to: list[str] = []
            switch_from: list[str] = []

            for alt in all_alternatives:
                if alt.source_entity.normalized_name == name:
                    if alt.target_entity:
                        if alt.comparison_type == ComparisonType.SWITCH:
                            switch_to.append(alt.target_entity.name)
                        else:
                            alternatives_mentioned.append(alt.target_entity.name)
                elif alt.target_entity and alt.target_entity.normalized_name == name:
                    if alt.comparison_type == ComparisonType.SWITCH:
                        switch_from.append(alt.source_entity.name)

            insights.append(
                CompetitiveInsight(
                    entity=entity,
                    overall_sentiment=overall_sentiment,
                    complaint_count=len(entity_complaints),
                    top_complaints=entity_complaints[:5],
                    alternatives_mentioned=list(set(alternatives_mentioned)),
                    switch_to=list(set(switch_to)),
                    switch_from=list(set(switch_from)),
                )
            )

        # Sort insights by complaint count
        insights.sort(key=lambda i: i.complaint_count, reverse=True)

        # Get overall top complaints
        all_complaints.sort(key=lambda c: c.severity, reverse=True)
        top_complaints = all_complaints[:10]

        # Generate recommendations
        recommendations = self._generate_recommendations(insights, popular_switches)

        return CompetitiveReport(
            generated_at=datetime.now(),
            entities_analyzed=len(entity_dict),
            insights=insights,
            top_complaints=top_complaints,
            popular_switches=popular_switches,
            recommendations=recommendations,
        )

    def get_entity_insight(
        self, entity_name: str, posts: list["Post"]
    ) -> CompetitiveInsight | None:
        """
        Get insight for a specific entity.

        Args:
            entity_name: Name of the entity to analyze
            posts: List of posts to analyze

        Returns:
            CompetitiveInsight for the entity, or None if not found
        """
        report = self.analyze_posts(posts)

        entity_name_lower = entity_name.lower()
        for insight in report.insights:
            if insight.entity.normalized_name == entity_name_lower:
                return insight
            if insight.entity.name.lower() == entity_name_lower:
                return insight

        return None


# ============================================================================
# Report Formatters
# ============================================================================


def to_markdown(report: CompetitiveReport) -> str:
    """
    Convert CompetitiveReport to markdown format.

    Args:
        report: CompetitiveReport to format

    Returns:
        Markdown string
    """
    lines: list[str] = []

    # Header
    lines.append("# Competitive Analysis Report")
    lines.append("")
    lines.append(f"**Generated:** {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"**Entities Analyzed:** {report.entities_analyzed}")
    lines.append("")

    # Recommendations
    lines.append("## Key Recommendations")
    lines.append("")
    for i, rec in enumerate(report.recommendations, 1):
        lines.append(f"{i}. {rec}")
    lines.append("")

    # Popular Switches
    if report.popular_switches:
        lines.append("## Popular Product Switches")
        lines.append("")
        lines.append("| From | To | Count |")
        lines.append("|------|-----|-------|")
        for from_name, to_name, count in report.popular_switches[:5]:
            lines.append(f"| {from_name} | {to_name} | {count} |")
        lines.append("")

    # Top Complaints
    if report.top_complaints:
        lines.append("## Top Complaints")
        lines.append("")
        for complaint in report.top_complaints[:5]:
            lines.append(
                f"- **{complaint.entity.name}** ({complaint.complaint_type.value}): "
                f"severity {complaint.severity:.2f}"
            )
            if complaint.keywords:
                lines.append(f"  - Keywords: {', '.join(complaint.keywords)}")
        lines.append("")

    # Entity Insights
    if report.insights:
        lines.append("## Entity Insights")
        lines.append("")
        for insight in report.insights[:10]:
            lines.append(f"### {insight.entity.name}")
            lines.append("")
            lines.append(
                f"- **Sentiment:** {insight.overall_sentiment.sentiment.value} "
                f"(compound: {insight.overall_sentiment.compound:.2f})"
            )
            lines.append(f"- **Complaints:** {insight.complaint_count}")
            if insight.switch_to:
                lines.append(f"- **Users switching to:** {', '.join(insight.switch_to)}")
            if insight.switch_from:
                lines.append(f"- **Users switching from:** {', '.join(insight.switch_from)}")
            lines.append("")

    return "\n".join(lines)


def to_dict(report: CompetitiveReport) -> dict:
    """
    Convert CompetitiveReport to dictionary format.

    Args:
        report: CompetitiveReport to convert

    Returns:
        Dictionary representation
    """
    return {
        "generated_at": report.generated_at.isoformat(),
        "entities_analyzed": report.entities_analyzed,
        "recommendations": report.recommendations,
        "popular_switches": [
            {"from": f, "to": t, "count": c}
            for f, t, c in report.popular_switches
        ],
        "top_complaints": [
            {
                "entity": c.entity.name,
                "type": c.complaint_type.value,
                "severity": c.severity,
                "text": c.text,
                "keywords": c.keywords,
            }
            for c in report.top_complaints
        ],
        "insights": [
            {
                "entity": i.entity.name,
                "sentiment": i.overall_sentiment.sentiment.value,
                "compound": i.overall_sentiment.compound,
                "complaint_count": i.complaint_count,
                "switch_to": i.switch_to,
                "switch_from": i.switch_from,
                "alternatives_mentioned": i.alternatives_mentioned,
            }
            for i in report.insights
        ],
    }
