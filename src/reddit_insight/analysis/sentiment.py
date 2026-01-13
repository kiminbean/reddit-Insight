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
    "love",
    "loved",
    "prefer",
    "preferred",
    "enjoy",
    "enjoyed",
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
