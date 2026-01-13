"""
Keyword extraction module.

Provides keyword extraction for Reddit text analysis using multiple methods:
- YAKE: Statistical method for single documents (no training required)
- TF-IDF: Corpus-based method for identifying important terms
- Combined: Merges results from multiple methods
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
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


class KeywordMethod(Enum):
    """
    Keyword extraction method enumeration.

    Attributes:
        YAKE: Statistical single-document extraction
        TFIDF: Corpus-based extraction using TF-IDF
        COMBINED: Merge results from multiple methods
    """

    YAKE = "yake"
    TFIDF = "tfidf"
    COMBINED = "combined"


@dataclass
class KeywordResult:
    """
    Result container for keyword extraction.

    Attributes:
        keywords: List of extracted keywords
        method: Extraction method used
        document_count: Number of documents processed
        extracted_at: Timestamp of extraction
    """

    keywords: list[Keyword]
    method: KeywordMethod
    document_count: int
    extracted_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"KeywordResult(method={self.method.value}, "
            f"keywords={len(self.keywords)}, docs={self.document_count})"
        )


@dataclass
class UnifiedKeywordExtractor:
    """
    Unified keyword extractor supporting multiple methods.

    Provides a single interface for extracting keywords using
    YAKE, TF-IDF, or a combination of both methods.

    Example:
        >>> extractor = UnifiedKeywordExtractor()
        >>> result = extractor.extract_keywords(
        ...     texts=["Python is great", "Machine learning rocks"],
        ...     num_keywords=10
        ... )
        >>> print(result.keywords[0].keyword)
    """

    method: KeywordMethod = KeywordMethod.YAKE
    _yake: YAKEExtractor = field(init=False, repr=False)
    _tfidf: "TFIDFAnalyzer | None" = field(init=False, repr=False, default=None)

    def __post_init__(self) -> None:
        """Initialize extractors."""
        self._yake = YAKEExtractor()

    def _get_tfidf(self) -> "TFIDFAnalyzer":
        """Lazy initialization of TF-IDF analyzer."""
        if self._tfidf is None:
            # Import here to avoid circular dependency
            from reddit_insight.analysis.tfidf import TFIDFAnalyzer

            self._tfidf = TFIDFAnalyzer()
        return self._tfidf

    def _merge_keywords(
        self,
        yake_keywords: list[Keyword],
        tfidf_keywords: list[Keyword],
        num_keywords: int,
    ) -> list[Keyword]:
        """
        Merge keywords from YAKE and TF-IDF methods.

        Uses weighted averaging for duplicates and combines unique keywords.

        Args:
            yake_keywords: Keywords from YAKE extraction
            tfidf_keywords: Keywords from TF-IDF extraction
            num_keywords: Maximum number of keywords to return

        Returns:
            Merged list of keywords sorted by combined score
        """
        # Create lookup for TF-IDF keywords (lowercase for matching)
        tfidf_lookup: dict[str, Keyword] = {
            kw.keyword.lower(): kw for kw in tfidf_keywords
        }

        merged: dict[str, Keyword] = {}

        # Process YAKE keywords first
        for kw in yake_keywords:
            key = kw.keyword.lower()
            tfidf_match = tfidf_lookup.get(key)

            if tfidf_match:
                # Average the scores (weighted: YAKE 0.5, TF-IDF 0.5)
                combined_score = (kw.score + tfidf_match.score) / 2
                merged[key] = Keyword(
                    keyword=kw.keyword,  # Keep original casing from YAKE
                    score=combined_score,
                    frequency=kw.frequency,
                )
                # Remove from TF-IDF lookup to track processed
                del tfidf_lookup[key]
            else:
                # YAKE only, reduce score slightly
                merged[key] = Keyword(
                    keyword=kw.keyword,
                    score=kw.score * 0.8,  # Slight penalty for single-method
                    frequency=kw.frequency,
                )

        # Add remaining TF-IDF keywords with reduced score
        for key, kw in tfidf_lookup.items():
            if key not in merged:
                merged[key] = Keyword(
                    keyword=kw.keyword,
                    score=kw.score * 0.8,  # Slight penalty for single-method
                    frequency=kw.frequency,
                )

        # Sort by score and limit
        sorted_keywords = sorted(merged.values(), key=lambda k: k.score, reverse=True)
        return sorted_keywords[:num_keywords]

    def extract_keywords(
        self,
        texts: list[str],
        num_keywords: int = 20,
        method: KeywordMethod | None = None,
    ) -> KeywordResult:
        """
        Extract keywords from texts using the specified method.

        Args:
            texts: List of input texts
            num_keywords: Number of keywords to extract
            method: Extraction method (uses instance default if None)

        Returns:
            KeywordResult containing extracted keywords
        """
        if not texts:
            return KeywordResult(
                keywords=[],
                method=method or self.method,
                document_count=0,
            )

        active_method = method or self.method

        if active_method == KeywordMethod.YAKE:
            keywords = self._yake.extract_from_texts(texts)[:num_keywords]

        elif active_method == KeywordMethod.TFIDF:
            tfidf = self._get_tfidf()
            tfidf.fit(texts)
            keywords = tfidf.get_top_keywords(num_keywords)

        elif active_method == KeywordMethod.COMBINED:
            # Get keywords from both methods
            yake_keywords = self._yake.extract_from_texts(texts)[:num_keywords * 2]

            tfidf = self._get_tfidf()
            tfidf.fit(texts)
            tfidf_keywords = tfidf.get_top_keywords(num_keywords * 2)

            keywords = self._merge_keywords(yake_keywords, tfidf_keywords, num_keywords)

        else:
            raise ValueError(f"Unknown method: {active_method}")

        return KeywordResult(
            keywords=keywords,
            method=active_method,
            document_count=len(texts),
        )

    def extract_from_posts(
        self,
        posts: list["Post"],
        num_keywords: int = 20,
        method: KeywordMethod | None = None,
    ) -> KeywordResult:
        """
        Extract keywords from Reddit Post objects.

        Args:
            posts: List of Post objects
            num_keywords: Number of keywords to extract
            method: Extraction method (uses instance default if None)

        Returns:
            KeywordResult containing extracted keywords
        """
        if not posts:
            return KeywordResult(
                keywords=[],
                method=method or self.method,
                document_count=0,
            )

        # Convert posts to texts
        texts = []
        for post in posts:
            text_parts = [post.title]
            if post.selftext:
                text_parts.append(post.selftext)
            texts.append(" ".join(text_parts))

        return self.extract_keywords(texts, num_keywords, method)
