"""
Reddit text tokenizer module.

Provides tokenization and n-gram extraction for Reddit text analysis.
"""

import re
from dataclasses import dataclass, field

from reddit_insight.analysis.stopwords import StopwordManager


@dataclass
class TokenizerConfig:
    """
    Configuration for RedditTokenizer.

    Attributes:
        lowercase: Convert tokens to lowercase
        remove_stopwords: Filter out stopwords
        min_token_length: Minimum token length to keep
        max_token_length: Maximum token length to keep
        remove_numbers: Remove purely numeric tokens
        remove_punctuation: Remove punctuation from tokens
        language: Language for stopwords
    """

    lowercase: bool = True
    remove_stopwords: bool = True
    min_token_length: int = 2
    max_token_length: int = 50
    remove_numbers: bool = False
    remove_punctuation: bool = True
    language: str = "english"


@dataclass
class RedditTokenizer:
    """
    Tokenizer optimized for Reddit text content.

    Handles Reddit-specific patterns like URLs, mentions, and markdown.
    Provides tokenization and n-gram extraction capabilities.

    Example:
        >>> tokenizer = RedditTokenizer()
        >>> tokens = tokenizer.tokenize("Hello World! This is a test post.")
        >>> print(tokens)
        ['hello', 'world', 'test', 'post']
    """

    config: TokenizerConfig = field(default_factory=TokenizerConfig)
    _stopword_manager: StopwordManager = field(init=False, repr=False)
    _word_pattern: re.Pattern[str] = field(init=False, repr=False)
    _url_pattern: re.Pattern[str] = field(init=False, repr=False)
    _mention_pattern: re.Pattern[str] = field(init=False, repr=False)
    _emoji_pattern: re.Pattern[str] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        """Initialize patterns and stopword manager after dataclass init."""
        self._stopword_manager = StopwordManager(language=self.config.language)

        # Word pattern: alphanumeric with optional internal apostrophes/hyphens
        self._word_pattern = re.compile(
            r"\b[a-zA-Z0-9]+(?:[''-][a-zA-Z0-9]+)*\b"
        )

        # URL pattern: match http(s) URLs and common URL patterns
        self._url_pattern = re.compile(
            r"https?://\S+|www\.\S+|[\w.-]+\.(?:com|org|net|io|co|gov|edu)\S*",
            re.IGNORECASE
        )

        # Reddit mention pattern: u/username, r/subreddit
        self._mention_pattern = re.compile(
            r"(?:u|r)/[\w_-]+",
            re.IGNORECASE
        )

        # Emoji pattern: Unicode emoji ranges
        self._emoji_pattern = re.compile(
            r"[\U0001F600-\U0001F64F"  # emoticons
            r"\U0001F300-\U0001F5FF"   # symbols & pictographs
            r"\U0001F680-\U0001F6FF"   # transport & map symbols
            r"\U0001F1E0-\U0001F1FF"   # flags
            r"\U00002702-\U000027B0"   # dingbats
            r"\U000024C2-\U0001F251"   # enclosed characters
            r"]+",
            flags=re.UNICODE
        )

    @property
    def stopword_manager(self) -> StopwordManager:
        """Access the stopword manager for customization."""
        return self._stopword_manager

    def _preprocess_text(self, text: str) -> str:
        """
        Preprocess text before tokenization.

        Removes URLs, mentions, emojis, and normalizes whitespace.

        Args:
            text: Raw text to preprocess

        Returns:
            Cleaned text ready for tokenization
        """
        # Remove URLs
        text = self._url_pattern.sub(" ", text)

        # Remove Reddit mentions
        text = self._mention_pattern.sub(" ", text)

        # Remove emojis
        text = self._emoji_pattern.sub(" ", text)

        # Remove HTML entities
        text = re.sub(r"&\w+;", " ", text)

        # Normalize whitespace
        text = re.sub(r"\s+", " ", text).strip()

        return text

    def _normalize_token(self, token: str) -> str | None:
        """
        Normalize a single token.

        Applies lowercase, length filtering, stopword filtering, etc.

        Args:
            token: Token to normalize

        Returns:
            Normalized token or None if it should be filtered out
        """
        # Apply lowercase if configured
        if self.config.lowercase:
            token = token.lower()

        # Check length constraints
        if len(token) < self.config.min_token_length:
            return None
        if len(token) > self.config.max_token_length:
            return None

        # Remove purely numeric tokens if configured
        if self.config.remove_numbers and token.isdigit():
            return None

        # Filter stopwords if configured
        if self.config.remove_stopwords and self._stopword_manager.is_stopword(token):
            return None

        return token

    def tokenize(self, text: str) -> list[str]:
        """
        Tokenize text into a list of words.

        Applies preprocessing, word extraction, and normalization.

        Args:
            text: Text to tokenize

        Returns:
            List of normalized tokens
        """
        if not text or not text.strip():
            return []

        # Preprocess
        cleaned_text = self._preprocess_text(text)

        # Extract words
        raw_tokens = self._word_pattern.findall(cleaned_text)

        # Normalize and filter
        tokens: list[str] = []
        for token in raw_tokens:
            normalized = self._normalize_token(token)
            if normalized:
                tokens.append(normalized)

        return tokens

    def tokenize_batch(self, texts: list[str]) -> list[list[str]]:
        """
        Tokenize multiple texts.

        Args:
            texts: List of texts to tokenize

        Returns:
            List of token lists, one per input text
        """
        return [self.tokenize(text) for text in texts]

    def get_ngrams(self, tokens: list[str], n: int = 2) -> list[str]:
        """
        Extract n-grams from a list of tokens.

        Args:
            tokens: List of tokens
            n: Size of n-grams (default: 2 for bigrams)

        Returns:
            List of n-gram strings joined by underscores
        """
        if len(tokens) < n:
            return []

        ngrams: list[str] = []
        for i in range(len(tokens) - n + 1):
            ngram = "_".join(tokens[i : i + n])
            ngrams.append(ngram)

        return ngrams

    def get_ngrams_from_text(self, text: str, n: int = 2) -> list[str]:
        """
        Extract n-grams directly from text.

        Convenience method combining tokenization and n-gram extraction.

        Args:
            text: Text to process
            n: Size of n-grams (default: 2 for bigrams)

        Returns:
            List of n-gram strings
        """
        tokens = self.tokenize(text)
        return self.get_ngrams(tokens, n)

    def get_vocabulary(self, texts: list[str]) -> set[str]:
        """
        Build vocabulary from multiple texts.

        Args:
            texts: List of texts to process

        Returns:
            Set of unique tokens across all texts
        """
        vocabulary: set[str] = set()
        for text in texts:
            vocabulary.update(self.tokenize(text))
        return vocabulary

    def token_frequencies(self, text: str) -> dict[str, int]:
        """
        Count token frequencies in text.

        Args:
            text: Text to analyze

        Returns:
            Dictionary mapping tokens to their frequencies
        """
        tokens = self.tokenize(text)
        frequencies: dict[str, int] = {}
        for token in tokens:
            frequencies[token] = frequencies.get(token, 0) + 1
        return frequencies
