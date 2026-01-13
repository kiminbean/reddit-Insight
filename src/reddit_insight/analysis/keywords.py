"""
Keyword extraction module.

Provides YAKE-based keyword extraction for Reddit text analysis.
YAKE (Yet Another Keyword Extractor) is a statistical method that
extracts keywords from single documents without requiring training.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import yake

if TYPE_CHECKING:
    from reddit_insight.reddit.models import Post


@dataclass
class Keyword:
    """
    Represents an extracted keyword with its score.

    Attributes:
        keyword: The extracted keyword or keyphrase
        score: Importance score (0-1, higher = more important)
        frequency: Optional occurrence count in the corpus
    """

    keyword: str
    score: float
    frequency: int | None = None

    def __repr__(self) -> str:
        """String representation for debugging."""
        freq_str = f", freq={self.frequency}" if self.frequency is not None else ""
        return f"Keyword('{self.keyword}', score={self.score:.3f}{freq_str})"


@dataclass
class KeywordExtractorConfig:
    """
    Configuration for keyword extraction.

    Attributes:
        max_ngram_size: Maximum size of n-grams to consider
        deduplication_threshold: Threshold for removing similar keywords (0-1)
        num_keywords: Number of keywords to extract
        language: Language code for the text
    """

    max_ngram_size: int = 3
    deduplication_threshold: float = 0.9
    num_keywords: int = 20
    language: str = "en"


@dataclass
class YAKEExtractor:
    """
    YAKE-based keyword extractor for single documents.

    YAKE uses statistical features to identify keywords without
    requiring any training or external resources.

    Example:
        >>> extractor = YAKEExtractor()
        >>> keywords = extractor.extract("Python is great for machine learning")
        >>> print(keywords[0].keyword)
        'machine learning'
    """

    config: KeywordExtractorConfig = field(default_factory=KeywordExtractorConfig)
    _yake_extractor: yake.KeywordExtractor = field(init=False, repr=False)

    def __post_init__(self) -> None:
        """Initialize YAKE extractor with configuration."""
        self._yake_extractor = yake.KeywordExtractor(
            lan=self.config.language,
            n=self.config.max_ngram_size,
            dedupLim=self.config.deduplication_threshold,
            dedupFunc="seqm",  # Sequential matching for deduplication
            top=self.config.num_keywords,
            features=None,  # Use default features
        )

    def _normalize_score(self, yake_score: float) -> float:
        """
        Normalize YAKE score to 0-1 range where higher is better.

        YAKE scores are lower = more important, so we invert them.
        We use 1 / (1 + score) transformation to keep values in (0, 1].

        Args:
            yake_score: Raw YAKE score (lower = more important)

        Returns:
            Normalized score in range (0, 1] where higher = more important
        """
        # Avoid division by zero and ensure bounded output
        return 1.0 / (1.0 + yake_score)

    def extract(self, text: str) -> list[Keyword]:
        """
        Extract keywords from a single text.

        Args:
            text: Input text to extract keywords from

        Returns:
            List of Keyword objects sorted by importance (highest first)
        """
        if not text or not text.strip():
            return []

        # YAKE returns list of (keyword, score) tuples
        raw_keywords = self._yake_extractor.extract_keywords(text)

        keywords = [
            Keyword(
                keyword=kw,
                score=self._normalize_score(score),
            )
            for kw, score in raw_keywords
        ]

        # Sort by normalized score (highest first)
        keywords.sort(key=lambda k: k.score, reverse=True)

        return keywords

    def extract_from_texts(self, texts: list[str]) -> list[Keyword]:
        """
        Extract keywords from multiple texts combined.

        Joins all texts and extracts keywords from the combined corpus.

        Args:
            texts: List of input texts

        Returns:
            List of Keyword objects from the combined text
        """
        if not texts:
            return []

        # Combine texts with paragraph separators
        combined_text = "\n\n".join(text for text in texts if text and text.strip())

        return self.extract(combined_text)

    def extract_from_posts(self, posts: list["Post"]) -> list[Keyword]:
        """
        Extract keywords from Reddit Post objects.

        Combines title and selftext from each post.

        Args:
            posts: List of Post objects

        Returns:
            List of Keyword objects from all posts
        """
        if not posts:
            return []

        texts = []
        for post in posts:
            # Combine title and selftext
            text_parts = [post.title]
            if post.selftext:
                text_parts.append(post.selftext)
            texts.append(" ".join(text_parts))

        return self.extract_from_texts(texts)
