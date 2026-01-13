"""
Stopword management module for Reddit text analysis.

Provides NLTK-based stopword filtering with Reddit-specific additions.
"""

from collections.abc import Iterable
from functools import lru_cache
from typing import ClassVar

import nltk


def ensure_nltk_data() -> None:
    """
    Ensure required NLTK data packages are downloaded.

    Downloads 'punkt' and 'stopwords' if not already available.
    Uses quiet mode to minimize console output.
    """
    required_packages = ["punkt", "stopwords"]

    for package in required_packages:
        try:
            nltk.data.find(f"corpora/{package}" if package == "stopwords" else f"tokenizers/{package}")
        except LookupError:
            nltk.download(package, quiet=True)


@lru_cache(maxsize=8)
def get_default_stopwords(language: str = "english") -> frozenset[str]:
    """
    Get default NLTK stopwords for the specified language.

    Args:
        language: Language name for stopwords (default: "english")

    Returns:
        Frozen set of stopwords for the language

    Note:
        Results are cached for performance.
    """
    ensure_nltk_data()

    try:
        from nltk.corpus import stopwords as nltk_stopwords
        return frozenset(nltk_stopwords.words(language))
    except OSError:
        # Fallback to minimal English stopwords if NLTK data unavailable
        return frozenset({
            "a", "an", "the", "and", "or", "but", "in", "on", "at", "to",
            "for", "of", "with", "by", "from", "is", "are", "was", "were",
            "be", "been", "being", "have", "has", "had", "do", "does", "did",
            "will", "would", "could", "should", "may", "might", "must",
            "i", "you", "he", "she", "it", "we", "they", "this", "that",
        })


class StopwordManager:
    """
    Manages stopwords for text preprocessing.

    Combines NLTK base stopwords with custom and Reddit-specific stopwords.
    Provides methods to add, remove, and query stopwords.

    Attributes:
        REDDIT_STOPWORDS: Default Reddit-specific stopwords
    """

    REDDIT_STOPWORDS: ClassVar[frozenset[str]] = frozenset({
        # Reddit platform terms
        "reddit", "subreddit", "sub", "subs", "redditor", "redditors",
        "post", "posts", "comment", "comments", "thread", "threads",
        "upvote", "upvotes", "downvote", "downvotes", "karma",
        "edit", "edited", "deleted", "removed",
        "op", "oc", "ama", "iama", "eli5", "til", "tifu", "tldr", "tl",

        # URL and link remnants
        "http", "https", "www", "com", "org", "net", "io",
        "imgur", "gfycat", "giphy", "youtube", "youtu",

        # Common Reddit expressions
        "lol", "lmao", "rofl", "haha", "hahaha",
        "btw", "imo", "imho", "fwiw", "afaik", "iirc",
        "tbh", "ngl", "smh", "ymmv", "iirc",

        # Formatting artifacts
        "nbsp", "amp", "gt", "lt",
    })

    def __init__(self, language: str = "english") -> None:
        """
        Initialize the stopword manager.

        Args:
            language: Language for base stopwords (default: "english")
        """
        self._language = language
        self._base_stopwords: set[str] = set(get_default_stopwords(language))
        self._custom_stopwords: set[str] = set()
        self._reddit_stopwords: set[str] = set(self.REDDIT_STOPWORDS)
        self._excluded_stopwords: set[str] = set()

    @property
    def language(self) -> str:
        """Get the current language setting."""
        return self._language

    def get_stopwords(self) -> set[str]:
        """
        Get the complete set of active stopwords.

        Returns:
            Combined set of base, custom, and Reddit stopwords,
            minus any explicitly excluded words.
        """
        all_stopwords = (
            self._base_stopwords
            | self._custom_stopwords
            | self._reddit_stopwords
        )
        return all_stopwords - self._excluded_stopwords

    def add_stopwords(self, words: Iterable[str]) -> None:
        """
        Add words to the custom stopword list.

        Args:
            words: Iterable of words to add as stopwords
        """
        self._custom_stopwords.update(word.lower() for word in words)

    def remove_stopwords(self, words: Iterable[str]) -> None:
        """
        Exclude words from being treated as stopwords.

        Args:
            words: Iterable of words to exclude from stopwords
        """
        self._excluded_stopwords.update(word.lower() for word in words)

    def is_stopword(self, word: str) -> bool:
        """
        Check if a word is a stopword.

        Args:
            word: Word to check

        Returns:
            True if the word is a stopword, False otherwise
        """
        word_lower = word.lower()
        if word_lower in self._excluded_stopwords:
            return False
        return word_lower in self.get_stopwords()

    def reset(self) -> None:
        """Reset custom and excluded stopwords to defaults."""
        self._custom_stopwords.clear()
        self._excluded_stopwords.clear()

    def __len__(self) -> int:
        """Return the number of active stopwords."""
        return len(self.get_stopwords())

    def __contains__(self, word: str) -> bool:
        """Check if a word is a stopword using 'in' operator."""
        return self.is_stopword(word)
