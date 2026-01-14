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
        REDDIT_STOPWORDS: Default Reddit-specific stopwords (50+ words)
    """

    REDDIT_STOPWORDS: ClassVar[frozenset[str]] = frozenset({
        # Reddit platform terms
        "reddit", "subreddit", "subreddits", "sub", "subs", "redditor", "redditors",
        "post", "posts", "posting", "posted", "comment", "comments", "commenting",
        "thread", "threads", "upvote", "upvotes", "upvoted", "upvoting",
        "downvote", "downvotes", "downvoted", "downvoting", "karma",
        "edit", "edited", "edits", "deleted", "removed", "mod", "mods",
        "moderator", "moderators", "admin", "admins", "flair", "flairs",
        "op", "oc", "ama", "iama", "eli5", "til", "tifu", "tldr", "tl",
        "nsfw", "nsfl", "spoiler", "crosspost", "repost", "reposts",
        "sticky", "stickied", "pinned", "locked", "archived",
        "sidebar", "wiki", "faq", "rules", "banned", "ban",
        "award", "awards", "gold", "silver", "platinum", "gilded",

        # URL and link remnants
        "http", "https", "www", "com", "org", "net", "io", "co", "edu", "gov",
        "html", "htm", "php", "asp", "aspx", "pdf", "jpg", "jpeg", "png", "gif",
        "mp4", "webm", "mp3", "wav", "imgur", "gfycat", "giphy", "youtube", "youtu",
        "v.redd.it", "i.redd.it", "preview.redd.it", "redd.it", "reddit.com",
        "streamable", "gyfcat", "redgifs", "tenor",

        # Common Reddit expressions/acronyms
        "lol", "lmao", "lmfao", "rofl", "roflmao", "haha", "hahaha", "hehe",
        "btw", "imo", "imho", "fwiw", "afaik", "iirc", "ymmv", "ianal",
        "tbh", "ngl", "smh", "omg", "wtf", "wth", "ftw", "ffs",
        "ikr", "idk", "idgaf", "stfu", "gtfo", "inb4", "iiuc",
        "fyi", "psa", "dae", "cmv", "ysk", "lpt", "otoh",
        "brb", "afk", "ttyl", "rn", "irl", "nvm", "tba", "tbd",

        # Formatting artifacts
        "nbsp", "amp", "gt", "lt", "quot", "apos", "nbsp;", "&amp;", "&gt;", "&lt;",
        "x200b", "x200B",  # Zero-width space

        # Common filler words in Reddit discussions
        "gonna", "wanna", "gotta", "kinda", "sorta", "dunno", "lemme",
        "yeah", "yep", "yup", "nope", "nah", "meh", "ugh", "hmm",
        "okay", "ok", "alright", "aight",
        "basically", "literally", "actually", "honestly", "seriously",
        "apparently", "probably", "maybe", "perhaps", "definitely",

        # User/subreddit mention patterns (handled separately but included)
        "user", "users", "username", "account", "profile",
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


# ============================================================================
# Text Cleaning Utilities
# ============================================================================

import re
from typing import Pattern

# Pattern for URLs
URL_PATTERN: Pattern[str] = re.compile(
    r"https?://\S+|www\.\S+|\S+\.(com|org|net|io|co|edu|gov)/\S*",
    re.IGNORECASE,
)

# Pattern for subreddit mentions (r/subreddit)
SUBREDDIT_PATTERN: Pattern[str] = re.compile(
    r"\br/[A-Za-z0-9_]+\b",
    re.IGNORECASE,
)

# Pattern for user mentions (u/username)
USER_PATTERN: Pattern[str] = re.compile(
    r"\bu/[A-Za-z0-9_-]+\b",
    re.IGNORECASE,
)

# Pattern for markdown links [text](url)
MARKDOWN_LINK_PATTERN: Pattern[str] = re.compile(
    r"\[([^\]]+)\]\([^)]+\)",
)

# Pattern for multiple spaces
MULTI_SPACE_PATTERN: Pattern[str] = re.compile(r"\s+")

# Pattern for numbers only
NUMBERS_ONLY_PATTERN: Pattern[str] = re.compile(r"^\d+$")


def remove_urls(text: str) -> str:
    """
    Remove URLs from text.

    Args:
        text: Input text

    Returns:
        Text with URLs removed
    """
    return URL_PATTERN.sub(" ", text)


def remove_subreddit_mentions(text: str) -> str:
    """
    Remove subreddit mentions (r/subreddit) from text.

    Args:
        text: Input text

    Returns:
        Text with subreddit mentions removed
    """
    return SUBREDDIT_PATTERN.sub(" ", text)


def remove_user_mentions(text: str) -> str:
    """
    Remove user mentions (u/username) from text.

    Args:
        text: Input text

    Returns:
        Text with user mentions removed
    """
    return USER_PATTERN.sub(" ", text)


def extract_markdown_link_text(text: str) -> str:
    """
    Replace markdown links with just the link text.

    [text](url) -> text

    Args:
        text: Input text

    Returns:
        Text with markdown links replaced by link text
    """
    return MARKDOWN_LINK_PATTERN.sub(r"\1", text)


def normalize_whitespace(text: str) -> str:
    """
    Normalize whitespace - collapse multiple spaces to single space.

    Args:
        text: Input text

    Returns:
        Text with normalized whitespace
    """
    return MULTI_SPACE_PATTERN.sub(" ", text).strip()


def clean_reddit_text(text: str) -> str:
    """
    Clean Reddit text by removing URLs, mentions, and normalizing.

    Applies the following transformations:
    1. Extract markdown link text
    2. Remove URLs
    3. Remove subreddit mentions (r/...)
    4. Remove user mentions (u/...)
    5. Normalize whitespace

    Args:
        text: Input Reddit text

    Returns:
        Cleaned text suitable for analysis

    Example:
        >>> text = "Check [this link](https://example.com) r/python u/user123"
        >>> clean_reddit_text(text)
        'Check this link'
    """
    if not text:
        return ""

    # Apply cleaning steps in order
    cleaned = extract_markdown_link_text(text)
    cleaned = remove_urls(cleaned)
    cleaned = remove_subreddit_mentions(cleaned)
    cleaned = remove_user_mentions(cleaned)
    cleaned = normalize_whitespace(cleaned)

    return cleaned


def is_valid_keyword(keyword: str, min_length: int = 3) -> bool:
    """
    Check if a keyword is valid for extraction.

    A valid keyword:
    - Has at least min_length characters
    - Is not only numbers
    - Is not in the Reddit stopwords
    - Contains at least one letter

    Args:
        keyword: Keyword to validate
        min_length: Minimum character length (default: 3)

    Returns:
        True if keyword is valid, False otherwise

    Example:
        >>> is_valid_keyword("python")
        True
        >>> is_valid_keyword("123")
        False
        >>> is_valid_keyword("op")
        False
    """
    if not keyword:
        return False

    keyword_lower = keyword.lower().strip()

    # Check minimum length
    if len(keyword_lower) < min_length:
        return False

    # Check if only numbers
    if NUMBERS_ONLY_PATTERN.match(keyword_lower):
        return False

    # Check if in Reddit stopwords
    if keyword_lower in StopwordManager.REDDIT_STOPWORDS:
        return False

    # Must contain at least one letter
    if not any(c.isalpha() for c in keyword_lower):
        return False

    return True


def filter_keywords(keywords: list[str], min_length: int = 3) -> list[str]:
    """
    Filter a list of keywords, removing invalid ones.

    Args:
        keywords: List of keywords to filter
        min_length: Minimum character length (default: 3)

    Returns:
        Filtered list of valid keywords
    """
    return [kw for kw in keywords if is_valid_keyword(kw, min_length)]
