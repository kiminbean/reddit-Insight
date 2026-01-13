"""
TF-IDF analysis module.

Provides TF-IDF (Term Frequency-Inverse Document Frequency) analysis
for corpus-based keyword extraction using scikit-learn.
"""

from __future__ import annotations

import pickle
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from scipy.sparse import spmatrix
from sklearn.feature_extraction.text import TfidfVectorizer

from reddit_insight.analysis.keywords import Keyword
from reddit_insight.analysis.tokenizer import RedditTokenizer


@dataclass
class TFIDFConfig:
    """
    Configuration for TF-IDF analysis.

    Attributes:
        max_features: Maximum number of features (vocabulary size)
        min_df: Minimum document frequency (int for count, float for proportion)
        max_df: Maximum document frequency (float for proportion)
        ngram_range: Range of n-gram sizes to consider (min, max)
        use_idf: Whether to use inverse document frequency weighting
    """

    max_features: int = 1000
    min_df: int = 2
    max_df: float = 0.95
    ngram_range: tuple[int, int] = (1, 2)
    use_idf: bool = True


@dataclass
class TFIDFAnalyzer:
    """
    TF-IDF analyzer for corpus-based keyword extraction.

    Uses scikit-learn's TfidfVectorizer with custom Reddit tokenization.

    Example:
        >>> analyzer = TFIDFAnalyzer()
        >>> analyzer.fit(["Python programming", "Data science with Python"])
        >>> keywords = analyzer.get_top_keywords(5)
        >>> print(keywords[0].keyword)
        'python'
    """

    config: TFIDFConfig = field(default_factory=TFIDFConfig)
    _vectorizer: TfidfVectorizer = field(init=False, repr=False)
    _tokenizer: RedditTokenizer = field(init=False, repr=False)
    _fitted: bool = field(init=False, default=False)
    _feature_names: list[str] | None = field(init=False, default=None)
    _tfidf_matrix: spmatrix | None = field(init=False, default=None)

    def __post_init__(self) -> None:
        """Initialize tokenizer and vectorizer."""
        self._tokenizer = RedditTokenizer()

        # Create vectorizer with custom tokenizer
        self._vectorizer = TfidfVectorizer(
            tokenizer=self._tokenize_for_tfidf,
            lowercase=False,  # Tokenizer handles this
            max_features=self.config.max_features,
            min_df=self.config.min_df,
            max_df=self.config.max_df,
            ngram_range=self.config.ngram_range,
            use_idf=self.config.use_idf,
            token_pattern=None,  # Using custom tokenizer
        )

    def _tokenize_for_tfidf(self, text: str) -> list[str]:
        """
        Tokenize text for TF-IDF.

        Uses RedditTokenizer for consistent preprocessing.

        Args:
            text: Input text

        Returns:
            List of tokens
        """
        return self._tokenizer.tokenize(text)

    def fit(self, texts: list[str]) -> TFIDFAnalyzer:
        """
        Fit the TF-IDF vectorizer on a corpus.

        Args:
            texts: List of documents to learn vocabulary from

        Returns:
            Self for method chaining
        """
        if not texts:
            raise ValueError("Cannot fit on empty corpus")

        self._tfidf_matrix = self._vectorizer.fit_transform(texts)
        self._feature_names = list(self._vectorizer.get_feature_names_out())
        self._fitted = True

        return self

    def transform(self, texts: list[str]) -> spmatrix:
        """
        Transform texts to TF-IDF vectors.

        Args:
            texts: List of documents to transform

        Returns:
            Sparse matrix of TF-IDF vectors

        Raises:
            RuntimeError: If vectorizer is not fitted
        """
        if not self._fitted:
            raise RuntimeError("Vectorizer not fitted. Call fit() first.")

        return self._vectorizer.transform(texts)

    def fit_transform(self, texts: list[str]) -> spmatrix:
        """
        Fit vectorizer and transform texts in one step.

        Args:
            texts: List of documents

        Returns:
            Sparse matrix of TF-IDF vectors
        """
        self.fit(texts)
        return self._tfidf_matrix  # type: ignore[return-value]

    def get_top_keywords(self, n: int = 20) -> list[Keyword]:
        """
        Get top keywords from the fitted corpus.

        Calculates the average TF-IDF score for each term across
        all documents and returns the highest scoring terms.

        Args:
            n: Number of top keywords to return

        Returns:
            List of Keyword objects sorted by score (highest first)

        Raises:
            RuntimeError: If vectorizer is not fitted
        """
        if not self._fitted or self._tfidf_matrix is None:
            raise RuntimeError("Vectorizer not fitted. Call fit() first.")

        # Calculate mean TF-IDF score for each term across all documents
        mean_tfidf = np.array(self._tfidf_matrix.mean(axis=0)).flatten()

        # Get indices sorted by score (descending)
        top_indices = mean_tfidf.argsort()[::-1][:n]

        keywords = []
        for idx in top_indices:
            if mean_tfidf[idx] > 0:
                keywords.append(
                    Keyword(
                        keyword=self._feature_names[idx],  # type: ignore
                        score=float(mean_tfidf[idx]),
                    )
                )

        return keywords

    def get_document_keywords(self, text: str, n: int = 10) -> list[Keyword]:
        """
        Get top keywords for a single document.

        Args:
            text: Document text
            n: Number of keywords to return

        Returns:
            List of Keyword objects for the document

        Raises:
            RuntimeError: If vectorizer is not fitted
        """
        if not self._fitted:
            raise RuntimeError("Vectorizer not fitted. Call fit() first.")

        # Transform single document
        tfidf_vector = self._vectorizer.transform([text])
        scores = np.array(tfidf_vector.toarray()).flatten()

        # Get top indices
        top_indices = scores.argsort()[::-1][:n]

        keywords = []
        for idx in top_indices:
            if scores[idx] > 0:
                keywords.append(
                    Keyword(
                        keyword=self._feature_names[idx],  # type: ignore
                        score=float(scores[idx]),
                    )
                )

        return keywords

    def get_keywords_by_document(
        self, texts: list[str], n: int = 5
    ) -> list[list[Keyword]]:
        """
        Get top keywords for each document in a list.

        Args:
            texts: List of document texts
            n: Number of keywords per document

        Returns:
            List of keyword lists, one per document

        Raises:
            RuntimeError: If vectorizer is not fitted
        """
        if not self._fitted:
            raise RuntimeError("Vectorizer not fitted. Call fit() first.")

        # Transform all documents
        tfidf_matrix = self._vectorizer.transform(texts)

        results = []
        for i in range(tfidf_matrix.shape[0]):
            scores = np.array(tfidf_matrix[i].toarray()).flatten()
            top_indices = scores.argsort()[::-1][:n]

            doc_keywords = []
            for idx in top_indices:
                if scores[idx] > 0:
                    doc_keywords.append(
                        Keyword(
                            keyword=self._feature_names[idx],  # type: ignore
                            score=float(scores[idx]),
                        )
                    )

            results.append(doc_keywords)

        return results

    def get_vocabulary(self) -> dict[str, int]:
        """
        Get the vocabulary mapping.

        Returns:
            Dictionary mapping terms to feature indices

        Raises:
            RuntimeError: If vectorizer is not fitted
        """
        if not self._fitted:
            raise RuntimeError("Vectorizer not fitted. Call fit() first.")

        return dict(self._vectorizer.vocabulary_)

    def save(self, path: str) -> None:
        """
        Save the fitted vectorizer to a file.

        Args:
            path: File path to save to

        Raises:
            RuntimeError: If vectorizer is not fitted
        """
        if not self._fitted:
            raise RuntimeError("Vectorizer not fitted. Call fit() first.")

        save_path = Path(path)
        save_path.parent.mkdir(parents=True, exist_ok=True)

        with open(save_path, "wb") as f:
            pickle.dump(
                {
                    "vectorizer": self._vectorizer,
                    "feature_names": self._feature_names,
                    "config": self.config,
                },
                f,
            )

    def load(self, path: str) -> TFIDFAnalyzer:
        """
        Load a fitted vectorizer from a file.

        Args:
            path: File path to load from

        Returns:
            Self for method chaining
        """
        with open(path, "rb") as f:
            data = pickle.load(f)

        self._vectorizer = data["vectorizer"]
        self._feature_names = data["feature_names"]
        self.config = data["config"]
        self._fitted = True

        return self
