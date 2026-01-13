"""
Sentiment analysis module for Reddit text analysis.

Provides rule-based sentiment analysis for identifying positive, negative, and
neutral sentiment in Reddit discussions, with entity-level sentiment extraction.

Example:
    >>> from reddit_insight.analysis.sentiment import RuleBasedSentimentAnalyzer
    >>> analyzer = RuleBasedSentimentAnalyzer()
    >>> score = analyzer.analyze("This product is really great!")
    >>> print(score.sentiment)
    Sentiment.POSITIVE
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from reddit_insight.analysis.entity_recognition import EntityRecognizer, ProductEntity
    from reddit_insight.reddit.models import Post


class Sentiment(Enum):
    """
    Sentiment classification enumeration.

    Attributes:
        POSITIVE: Positive sentiment
        NEGATIVE: Negative sentiment
        NEUTRAL: Neutral sentiment
        MIXED: Mixed sentiment (both positive and negative)
    """

    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    MIXED = "mixed"


@dataclass
class SentimentScore:
    """
    Detailed sentiment score for analyzed text.

    Attributes:
        sentiment: Overall sentiment classification
        positive_score: Positive sentiment score (0-1)
        negative_score: Negative sentiment score (0-1)
        neutral_score: Neutral sentiment score (0-1)
        compound: Compound score (-1 to 1, overall sentiment intensity)
        confidence: Confidence in the sentiment classification (0-1)
    """

    sentiment: Sentiment
    positive_score: float
    negative_score: float
    neutral_score: float
    compound: float
    confidence: float

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"SentimentScore({self.sentiment.value}, "
            f"compound={self.compound:.2f}, conf={self.confidence:.2f})"
        )


# ============================================================================
# Sentiment Lexicon - Positive Words
# ============================================================================

POSITIVE_WORDS: set[str] = {
    # General positive
    "great",
    "awesome",
    "excellent",
    "amazing",
    "love",
    "best",
    "fantastic",
    "wonderful",
    "perfect",
    "brilliant",
    "outstanding",
    "superb",
    "incredible",
    "magnificent",
    "marvelous",
    # Recommendations
    "recommend",
    "recommended",
    "recommending",
    "suggest",
    "suggesting",
    # Usability
    "helpful",
    "easy",
    "simple",
    "intuitive",
    "user-friendly",
    "userfriendly",
    "smooth",
    "seamless",
    "elegant",
    "clean",
    # Performance
    "fast",
    "quick",
    "speedy",
    "efficient",
    "powerful",
    "robust",
    "reliable",
    "stable",
    "solid",
    "responsive",
    # Quality
    "beautiful",
    "impressive",
    "polished",
    "premium",
    "quality",
    "well-designed",
    "well-made",
    "professional",
    # Value
    "worth",
    "valuable",
    "affordable",
    "free",
    "cheap",
    "bargain",
    # Satisfaction
    "happy",
    "satisfied",
    "pleased",
    "delighted",
    "thrilled",
    "excited",
    "glad",
    "enjoy",
    "enjoying",
    "enjoyed",
    # Improvement
    "improved",
    "better",
    "upgrade",
    "enhanced",
    "upgraded",
    # Actions
    "like",
    "liked",
    "loved",
    "prefer",
    "preferred",
    "appreciate",
    "appreciated",
    # Comparative
    "superior",
    "greatest",
    "finest",
    "top",
    "topnotch",
    # Reddit-specific positive
    "upvote",
    "upvoted",
    "goat",
    "goated",
    "fire",
    "lit",
    "dope",
    "sick",
    "clutch",
    "based",
    "chad",
    "godsend",
    "lifesaver",
    "gamechanging",
    "gamechanger",
}

# ============================================================================
# Sentiment Lexicon - Negative Words
# ============================================================================

NEGATIVE_WORDS: set[str] = {
    # General negative
    "bad",
    "terrible",
    "awful",
    "horrible",
    "hate",
    "worst",
    "poor",
    "disappointing",
    "disappointed",
    "frustrating",
    "frustrated",
    "annoying",
    "annoyed",
    "pathetic",
    "dreadful",
    "atrocious",
    # Broken/Issues
    "broken",
    "buggy",
    "bugged",
    "glitchy",
    "crashed",
    "crash",
    "crashes",
    "freezes",
    "freeze",
    "lag",
    "laggy",
    "lagging",
    # Usability issues
    "useless",
    "pointless",
    "worthless",
    "complicated",
    "confusing",
    "confused",
    "difficult",
    "hard",
    "clunky",
    "awkward",
    "unintuitive",
    "cumbersome",
    # Performance issues
    "slow",
    "sluggish",
    "unreliable",
    "unstable",
    "inconsistent",
    "unresponsive",
    # Value issues
    "expensive",
    "overpriced",
    "ripoff",
    "scam",
    "waste",
    "wasted",
    "costly",
    # Dissatisfaction
    "unhappy",
    "unsatisfied",
    "dissatisfied",
    "regret",
    "regretted",
    "mistake",
    "fail",
    "failed",
    "failure",
    "failing",
    # Actions
    "dislike",
    "disliked",
    "hated",
    "avoid",
    "avoiding",
    "cancel",
    "cancelled",
    "canceled",
    "uninstall",
    "uninstalled",
    # Quality issues
    "ugly",
    "hideous",
    "unpolished",
    "amateurish",
    "mediocre",
    "subpar",
    "inferior",
    # Comparative
    "worse",
    "downgrade",
    "downgraded",
    # Reddit-specific negative
    "downvote",
    "downvoted",
    "cringe",
    "cringey",
    "trash",
    "garbage",
    "junk",
    "sucks",
    "suck",
    "sucked",
    "bs",
    "crap",
    "crappy",
    "shitty",
    "shit",
    "lame",
    "meh",
    "nope",
    "nah",
    "ugh",
    "yikes",
    "bloated",
    "spyware",
    "malware",
}

# ============================================================================
# Modifier Lexicons
# ============================================================================

NEGATORS: set[str] = {
    # Basic negations
    "not",
    "no",
    "never",
    "neither",
    "nobody",
    "nothing",
    "nowhere",
    "none",
    # Contractions
    "isn't",
    "isnt",
    "aren't",
    "arent",
    "wasn't",
    "wasnt",
    "weren't",
    "werent",
    "don't",
    "dont",
    "doesn't",
    "doesnt",
    "didn't",
    "didnt",
    "won't",
    "wont",
    "wouldn't",
    "wouldnt",
    "couldn't",
    "couldnt",
    "shouldn't",
    "shouldnt",
    "can't",
    "cant",
    "cannot",
    "haven't",
    "havent",
    "hasn't",
    "hasnt",
    "hadn't",
    "hadnt",
    # Other negators
    "without",
    "lack",
    "lacking",
    "lacks",
    "barely",
    "hardly",
    "scarcely",
    "seldom",
    "rarely",
}

INTENSIFIERS: dict[str, float] = {
    # Strong intensifiers (2x)
    "extremely": 2.0,
    "absolutely": 2.0,
    "incredibly": 2.0,
    "insanely": 2.0,
    "ridiculously": 2.0,
    "amazingly": 2.0,
    "unbelievably": 2.0,
    "exceptionally": 2.0,
    # Medium intensifiers (1.5x)
    "very": 1.5,
    "really": 1.5,
    "truly": 1.5,
    "highly": 1.5,
    "totally": 1.5,
    "completely": 1.5,
    "utterly": 1.5,
    "definitely": 1.5,
    "certainly": 1.5,
    "particularly": 1.5,
    "especially": 1.5,
    "seriously": 1.5,
    "genuinely": 1.5,
    # Light intensifiers (1.2-1.3x)
    "so": 1.3,
    "quite": 1.2,
    "pretty": 1.2,
    "fairly": 1.1,
    "rather": 1.2,
    "super": 1.5,
    "mega": 1.5,
    "ultra": 1.5,
    "hella": 1.5,
    "mad": 1.5,
    "wicked": 1.5,
    # Reddit-specific intensifiers
    "lowkey": 1.2,
    "highkey": 1.5,
    "deadass": 1.5,
    "fr": 1.3,
    "frfr": 1.5,
    "legit": 1.3,
    "literally": 1.5,
    "actually": 1.2,
    "honestly": 1.3,
    "straight": 1.2,
    "straight-up": 1.5,
}

DIMINISHERS: dict[str, float] = {
    # Mild diminishers (0.6-0.7x)
    "slightly": 0.5,
    "somewhat": 0.6,
    "rather": 0.7,
    "a bit": 0.5,
    "a little": 0.5,
    "kind of": 0.6,
    "kinda": 0.6,
    "sort of": 0.6,
    "sorta": 0.6,
    "partially": 0.6,
    "partly": 0.6,
    "marginally": 0.5,
    "mildly": 0.5,
    "moderately": 0.7,
    "relatively": 0.7,
    "almost": 0.8,
    "nearly": 0.8,
    "barely": 0.3,
    "hardly": 0.3,
    "scarcely": 0.3,
    # Reddit-specific
    "lowkey": 0.7,  # Can be diminisher or intensifier depending on context
    "ish": 0.6,
}

# ============================================================================
# Emoji and Emoticon Sentiment
# ============================================================================

POSITIVE_EMOTICONS: dict[str, float] = {
    # Standard emoticons
    ":)": 0.6,
    ":-)": 0.6,
    ":D": 0.8,
    ":-D": 0.8,
    "=)": 0.6,
    "=D": 0.8,
    ";)": 0.5,
    ";-)": 0.5,
    ":P": 0.4,
    ":-P": 0.4,
    "xD": 0.7,
    "XD": 0.7,
    "<3": 0.8,
    # Reddit text expressions
    "lol": 0.3,
    "lmao": 0.4,
    "rofl": 0.5,
    "haha": 0.4,
    "hehe": 0.3,
}

NEGATIVE_EMOTICONS: dict[str, float] = {
    # Standard emoticons
    ":(": 0.6,
    ":-(": 0.6,
    ":'(": 0.7,
    ":((": 0.7,
    "=/": 0.4,
    ":/": 0.3,
    ":-/": 0.3,
    ">:(": 0.7,
    "-_-": 0.4,
    ":|": 0.2,
    # Reddit text expressions
    "smh": 0.3,
    "facepalm": 0.4,
}


# ============================================================================
# Sentiment Analyzer Configuration
# ============================================================================


@dataclass
class SentimentAnalyzerConfig:
    """
    Configuration for sentiment analyzer.

    Attributes:
        use_negation: Whether to handle negation (e.g., "not good")
        use_intensifiers: Whether to apply intensifier/diminisher modifiers
        neutral_threshold: Threshold below which sentiment is neutral
        mixed_threshold: Threshold for mixed sentiment (when both pos/neg are high)
    """

    use_negation: bool = True
    use_intensifiers: bool = True
    neutral_threshold: float = 0.03
    mixed_threshold: float = 0.25


# ============================================================================
# Rule-Based Sentiment Analyzer
# ============================================================================


@dataclass
class RuleBasedSentimentAnalyzer:
    """
    Rule-based sentiment analyzer using lexicon matching.

    Uses predefined sentiment lexicons with support for negation handling,
    intensifiers, and emoticons to analyze text sentiment.

    Example:
        >>> analyzer = RuleBasedSentimentAnalyzer()
        >>> score = analyzer.analyze("This product is really great!")
        >>> print(score.sentiment)
        Sentiment.POSITIVE
    """

    config: SentimentAnalyzerConfig = field(default_factory=SentimentAnalyzerConfig)

    def _tokenize_simple(self, text: str) -> list[str]:
        """
        Simple tokenization for sentiment analysis.

        Preserves emoticons and handles contractions.

        Args:
            text: Input text

        Returns:
            List of tokens (lowercase)
        """
        import re

        if not text:
            return []

        # Preserve emoticons by extracting them first
        emoticon_pattern = r"[:;=]['\-]?[)(DPp\[\]/\\|]|<3|[xX][Dd]|-_-|>:\("
        emoticons = re.findall(emoticon_pattern, text)

        # Replace emoticons with placeholders
        placeholder_text = text
        emoticon_map = {}
        for i, emo in enumerate(emoticons):
            placeholder = f"__EMO{i}__"
            emoticon_map[placeholder] = emo
            placeholder_text = placeholder_text.replace(emo, f" {placeholder} ", 1)

        # Basic tokenization: split on whitespace and punctuation
        tokens = re.findall(r"\b[\w'-]+\b|__EMO\d+__", placeholder_text.lower())

        # Restore emoticons
        result = []
        for token in tokens:
            if token in emoticon_map:
                result.append(emoticon_map[token])
            else:
                result.append(token)

        return result

    def _tokenize_with_context(self, text: str) -> list[tuple[str, str | None, str | None]]:
        """
        Tokenize text with surrounding context for modifier handling.

        Args:
            text: Input text

        Returns:
            List of tuples (token, prev_token, prev_prev_token)
        """
        tokens = self._tokenize_simple(text)

        if not tokens:
            return []

        result: list[tuple[str, str | None, str | None]] = []
        for i, token in enumerate(tokens):
            prev_token = tokens[i - 1] if i > 0 else None
            prev_prev_token = tokens[i - 2] if i > 1 else None
            result.append((token, prev_token, prev_prev_token))

        return result

    def _calculate_word_sentiment(
        self,
        word: str,
        prev_word: str | None,
        prev_prev_word: str | None,
    ) -> float:
        """
        Calculate sentiment score for a single word.

        Args:
            word: Current word
            prev_word: Previous word (for modifier detection)
            prev_prev_word: Word before previous (for two-word modifiers)

        Returns:
            Sentiment score (-1 to 1)
        """
        word_lower = word.lower()
        prev_lower = prev_word.lower() if prev_word else None
        prev_prev_lower = prev_prev_word.lower() if prev_prev_word else None

        # Check emoticons first
        if word in POSITIVE_EMOTICONS:
            return POSITIVE_EMOTICONS[word]
        if word in NEGATIVE_EMOTICONS:
            return -NEGATIVE_EMOTICONS[word]

        # Determine base sentiment
        base_score = 0.0
        if word_lower in POSITIVE_WORDS:
            base_score = 0.7  # Base positive score
        elif word_lower in NEGATIVE_WORDS:
            base_score = -0.7  # Base negative score
        else:
            return 0.0  # Not a sentiment word

        # Apply modifiers if enabled
        if self.config.use_intensifiers:
            # Check for intensifiers
            if prev_lower and prev_lower in INTENSIFIERS:
                base_score *= INTENSIFIERS[prev_lower]
            # Check for diminishers
            elif prev_lower and prev_lower in DIMINISHERS:
                base_score *= DIMINISHERS[prev_lower]
            # Check two-word phrases (e.g., "a bit", "kind of")
            elif prev_lower and prev_prev_lower:
                two_word = f"{prev_prev_lower} {prev_lower}"
                if two_word in DIMINISHERS:
                    base_score *= DIMINISHERS[two_word]

        # Apply negation if enabled
        if self.config.use_negation:
            # Check for negation in previous words (window of 2)
            if prev_lower and prev_lower in NEGATORS:
                base_score *= -0.8  # Flip and reduce intensity
            elif prev_prev_lower and prev_prev_lower in NEGATORS:
                base_score *= -0.6  # Weaker flip for farther negation

        # Clamp to [-1, 1]
        return max(-1.0, min(1.0, base_score))

    def _aggregate_scores(self, word_scores: list[float]) -> SentimentScore:
        """
        Aggregate word-level sentiment scores into overall sentiment.

        Args:
            word_scores: List of word sentiment scores

        Returns:
            Aggregated SentimentScore
        """
        if not word_scores:
            return SentimentScore(
                sentiment=Sentiment.NEUTRAL,
                positive_score=0.0,
                negative_score=0.0,
                neutral_score=1.0,
                compound=0.0,
                confidence=0.5,  # Low confidence for empty input
            )

        # Separate positive and negative scores
        positive_scores = [s for s in word_scores if s > 0]
        negative_scores = [s for s in word_scores if s < 0]

        # Calculate raw scores
        pos_sum = sum(positive_scores)
        neg_sum = sum(abs(s) for s in negative_scores)
        total_sentiment_words = len(positive_scores) + len(negative_scores)

        # Normalize scores (using a normalization factor similar to VADER)
        # This prevents the score from growing indefinitely with more words
        alpha = 15  # Normalization constant
        norm_pos = pos_sum / (pos_sum + alpha) if pos_sum > 0 else 0.0
        norm_neg = neg_sum / (neg_sum + alpha) if neg_sum > 0 else 0.0

        # Calculate compound score
        # Ranges from -1 (most negative) to 1 (most positive)
        compound = (pos_sum - neg_sum) / (pos_sum + neg_sum + alpha)

        # Calculate neutral score (proportion of non-sentiment words)
        total_words = len(word_scores)
        neutral_ratio = 1.0 - (total_sentiment_words / total_words) if total_words > 0 else 1.0
        neutral_score = min(1.0, max(0.0, neutral_ratio))

        # Normalize positive and negative scores
        total_score = norm_pos + norm_neg + 0.001  # Avoid division by zero
        positive_score = norm_pos / total_score
        negative_score = norm_neg / total_score

        # Determine sentiment classification
        sentiment = self._classify_sentiment(
            positive_score, negative_score, compound
        )

        # Calculate confidence based on number of sentiment words and their consistency
        if total_sentiment_words == 0:
            confidence = 0.3
        else:
            # Higher confidence with more sentiment words and clearer polarity
            word_confidence = min(1.0, total_sentiment_words / 5.0)  # Max at 5 words
            polarity_confidence = abs(compound)
            confidence = 0.4 + 0.3 * word_confidence + 0.3 * polarity_confidence

        return SentimentScore(
            sentiment=sentiment,
            positive_score=round(positive_score, 4),
            negative_score=round(negative_score, 4),
            neutral_score=round(neutral_score, 4),
            compound=round(compound, 4),
            confidence=round(confidence, 4),
        )

    def _classify_sentiment(
        self,
        positive_score: float,
        negative_score: float,
        compound: float,
    ) -> Sentiment:
        """
        Classify overall sentiment based on scores.

        Args:
            positive_score: Normalized positive score
            negative_score: Normalized negative score
            compound: Compound sentiment score

        Returns:
            Sentiment classification
        """
        # Check for mixed sentiment (both positive and negative are significant)
        if (
            positive_score > self.config.mixed_threshold
            and negative_score > self.config.mixed_threshold
        ):
            return Sentiment.MIXED

        # Check for neutral
        if abs(compound) < self.config.neutral_threshold:
            return Sentiment.NEUTRAL

        # Classify as positive or negative
        if compound > 0:
            return Sentiment.POSITIVE
        else:
            return Sentiment.NEGATIVE

    def analyze(self, text: str) -> SentimentScore:
        """
        Analyze sentiment of text.

        Args:
            text: Input text to analyze

        Returns:
            SentimentScore with detailed sentiment information
        """
        if not text or not text.strip():
            return SentimentScore(
                sentiment=Sentiment.NEUTRAL,
                positive_score=0.0,
                negative_score=0.0,
                neutral_score=1.0,
                compound=0.0,
                confidence=0.0,
            )

        # Tokenize with context
        tokens_with_context = self._tokenize_with_context(text)

        # Calculate word-level sentiment scores
        word_scores: list[float] = []
        for token, prev_token, prev_prev_token in tokens_with_context:
            score = self._calculate_word_sentiment(token, prev_token, prev_prev_token)
            word_scores.append(score)

        # Aggregate scores
        return self._aggregate_scores(word_scores)


# ============================================================================
# Entity-Sentiment Integration
# ============================================================================


@dataclass
class EntitySentiment:
    """
    Represents sentiment associated with a specific entity.

    Attributes:
        entity: The product/service entity
        sentiment: Sentiment score for the entity
        context: Text context where entity was found
        mention_count: Number of times this entity was mentioned
    """

    entity: ProductEntity
    sentiment: SentimentScore
    context: str
    mention_count: int = 1

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"EntitySentiment('{self.entity.name}', "
            f"{self.sentiment.sentiment.value}, "
            f"mentions={self.mention_count})"
        )


@dataclass
class EntitySentimentAnalyzer:
    """
    Analyzer that combines entity recognition with sentiment analysis.

    Extracts entities from text and analyzes sentiment in the context
    surrounding each entity mention.

    Example:
        >>> analyzer = EntitySentimentAnalyzer()
        >>> results = analyzer.analyze_text("Slack is great but Notion is better")
        >>> for r in results:
        ...     print(f"{r.entity.name}: {r.sentiment.sentiment.value}")
    """

    _entity_recognizer: EntityRecognizer | None = field(default=None, repr=False)
    _sentiment_analyzer: RuleBasedSentimentAnalyzer = field(
        default_factory=RuleBasedSentimentAnalyzer, repr=False
    )
    _context_window: int = field(default=50, repr=False)

    def __post_init__(self) -> None:
        """Initialize recognizer if not provided."""
        if self._entity_recognizer is None:
            from reddit_insight.analysis.entity_recognition import EntityRecognizer

            self._entity_recognizer = EntityRecognizer()

    def _extract_entity_context(
        self,
        text: str,
        entity_start: int,
        entity_end: int,
        window: int | None = None,
    ) -> str:
        """
        Extract context window around an entity mention.

        Args:
            text: Full text
            entity_start: Start position of entity
            entity_end: End position of entity
            window: Context window size (characters on each side)

        Returns:
            Context string containing the entity and surrounding text
        """
        if window is None:
            window = self._context_window

        # Expand to word boundaries
        start = max(0, entity_start - window)
        end = min(len(text), entity_end + window)

        # Try to extend to word boundaries
        while start > 0 and text[start - 1].isalnum():
            start -= 1
        while end < len(text) and text[end].isalnum():
            end += 1

        return text[start:end].strip()

    def _find_entity_position(self, text: str, entity_name: str) -> tuple[int, int] | None:
        """
        Find position of entity in text (case-insensitive).

        Args:
            text: Text to search
            entity_name: Entity name to find

        Returns:
            Tuple of (start, end) positions or None if not found
        """
        import re

        # Case-insensitive search
        pattern = re.compile(re.escape(entity_name), re.IGNORECASE)
        match = pattern.search(text)

        if match:
            return (match.start(), match.end())
        return None

    def analyze_text(self, text: str) -> list[EntitySentiment]:
        """
        Analyze text for entities and their associated sentiment.

        Args:
            text: Input text to analyze

        Returns:
            List of EntitySentiment objects for each detected entity
        """
        if not text or not text.strip():
            return []

        # Recognize entities
        assert self._entity_recognizer is not None
        entities = self._entity_recognizer.recognize(text)

        if not entities:
            return []

        results: list[EntitySentiment] = []

        for entity in entities:
            # Find entity position for context extraction
            position = self._find_entity_position(text, entity.name)

            if position:
                # Extract context around entity
                context = self._extract_entity_context(
                    text, position[0], position[1]
                )
            else:
                # Fallback: use entity's stored context or full text
                context = entity.context if entity.context else text[:200]

            # Analyze sentiment of the context
            sentiment = self._sentiment_analyzer.analyze(context)

            results.append(
                EntitySentiment(
                    entity=entity,
                    sentiment=sentiment,
                    context=context,
                    mention_count=entity.mentions,
                )
            )

        return results

    def analyze_post(self, post: Post) -> list[EntitySentiment]:
        """
        Analyze a Reddit Post for entity sentiment.

        Combines title and selftext for analysis.

        Args:
            post: Reddit Post object

        Returns:
            List of EntitySentiment objects
        """
        # Combine title and selftext
        text_parts = [post.title]
        if post.selftext:
            text_parts.append(post.selftext)

        combined_text = " ".join(text_parts)
        return self.analyze_text(combined_text)

    def _aggregate_entity_sentiments(
        self,
        sentiments: list[EntitySentiment],
    ) -> dict[str, EntitySentiment]:
        """
        Aggregate sentiments for the same entity across multiple mentions.

        Averages sentiment scores and sums mention counts.

        Args:
            sentiments: List of EntitySentiment objects

        Returns:
            Dictionary mapping entity names to aggregated EntitySentiment
        """
        if not sentiments:
            return {}

        # Group by normalized entity name
        grouped: dict[str, list[EntitySentiment]] = {}
        for es in sentiments:
            key = es.entity.normalized_name
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(es)

        # Aggregate each group
        result: dict[str, EntitySentiment] = {}

        for name, group in grouped.items():
            if len(group) == 1:
                result[name] = group[0]
                continue

            # Calculate average sentiment scores
            total_mentions = sum(es.mention_count for es in group)
            avg_positive = sum(es.sentiment.positive_score * es.mention_count for es in group) / total_mentions
            avg_negative = sum(es.sentiment.negative_score * es.mention_count for es in group) / total_mentions
            avg_neutral = sum(es.sentiment.neutral_score * es.mention_count for es in group) / total_mentions
            avg_compound = sum(es.sentiment.compound * es.mention_count for es in group) / total_mentions
            avg_confidence = sum(es.sentiment.confidence * es.mention_count for es in group) / total_mentions

            # Determine overall sentiment from averaged compound
            if abs(avg_compound) < 0.03:
                sentiment_class = Sentiment.NEUTRAL
            elif avg_positive > 0.25 and avg_negative > 0.25:
                sentiment_class = Sentiment.MIXED
            elif avg_compound > 0:
                sentiment_class = Sentiment.POSITIVE
            else:
                sentiment_class = Sentiment.NEGATIVE

            # Use the entity with highest confidence as the representative
            best_entity = max(group, key=lambda es: es.entity.confidence).entity

            # Collect all contexts
            contexts = [es.context for es in group]
            combined_context = " | ".join(contexts[:3])  # Limit to 3 contexts

            result[name] = EntitySentiment(
                entity=best_entity,
                sentiment=SentimentScore(
                    sentiment=sentiment_class,
                    positive_score=round(avg_positive, 4),
                    negative_score=round(avg_negative, 4),
                    neutral_score=round(avg_neutral, 4),
                    compound=round(avg_compound, 4),
                    confidence=round(avg_confidence, 4),
                ),
                context=combined_context,
                mention_count=total_mentions,
            )

        return result

    def analyze_posts(self, posts: list[Post]) -> dict[str, EntitySentiment]:
        """
        Analyze multiple posts and aggregate entity sentiments.

        Args:
            posts: List of Post objects

        Returns:
            Dictionary mapping entity names to aggregated EntitySentiment
        """
        if not posts:
            return {}

        # Collect all entity sentiments
        all_sentiments: list[EntitySentiment] = []
        for post in posts:
            sentiments = self.analyze_post(post)
            all_sentiments.extend(sentiments)

        # Aggregate by entity
        return self._aggregate_entity_sentiments(all_sentiments)
