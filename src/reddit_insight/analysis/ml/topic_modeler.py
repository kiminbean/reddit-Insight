"""
Topic modeling module for Reddit text analysis.

Provides LDA (Latent Dirichlet Allocation) and NMF (Non-negative Matrix Factorization)
based topic extraction for discovering themes in Reddit posts.

Example:
    >>> from reddit_insight.analysis.ml.topic_modeler import TopicModeler, TopicModelerConfig
    >>> modeler = TopicModeler(TopicModelerConfig(n_topics=5))
    >>> result = modeler.fit_transform(texts)
    >>> for topic in result.topics:
    ...     print(f"Topic {topic.id}: {topic.keywords[:3]}")
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

import numpy as np
from numpy.typing import NDArray
from scipy.sparse import spmatrix
from sklearn.decomposition import LatentDirichletAllocation, NMF
from sklearn.feature_extraction.text import TfidfVectorizer

from reddit_insight.analysis.ml.base import (
    AnalysisResult,
    MLAnalyzerBase,
    MLAnalyzerConfig,
)
from reddit_insight.analysis.ml.models import Topic, TopicResult
from reddit_insight.analysis.tokenizer import RedditTokenizer

if TYPE_CHECKING:
    pass


TopicMethod = Literal["lda", "nmf", "auto"]


@dataclass
class TopicModelerConfig(MLAnalyzerConfig):
    """
    Configuration for topic modeling.

    Attributes:
        n_topics: Number of topics to extract
        method: Topic modeling method ("lda", "nmf", or "auto")
        max_features: Maximum vocabulary size for TF-IDF
        min_df: Minimum document frequency for terms
        max_df: Maximum document frequency for terms (float for proportion)
        n_top_words: Number of top words to extract per topic
        max_iter: Maximum iterations for model fitting
    """

    n_topics: int = 5
    method: TopicMethod = "auto"
    max_features: int = 1000
    min_df: int = 2
    max_df: float = 0.95
    n_top_words: int = 10
    max_iter: int = 100


class TopicModeler(MLAnalyzerBase):
    """
    Topic modeler using LDA or NMF for discovering themes in text.

    Analyzes a collection of texts to discover latent topics and their
    associated keywords. Supports both LDA (probabilistic) and NMF
    (matrix factorization) approaches.

    Example:
        >>> config = TopicModelerConfig(n_topics=3, method="lda")
        >>> modeler = TopicModeler(config)
        >>> result = modeler.fit_transform(texts)
        >>> print(f"Found {result.n_topics} topics")
        >>> for topic in result.topics:
        ...     print(f"  {topic.label}: {topic.keywords[:5]}")
    """

    def __init__(self, config: TopicModelerConfig | None = None) -> None:
        """
        Initialize the topic modeler.

        Args:
            config: Configuration for the modeler, uses defaults if None
        """
        self._config = config or TopicModelerConfig()
        super().__init__(self._config)
        self._tokenizer = RedditTokenizer()
        self._vectorizer: TfidfVectorizer | None = None
        self._model: LatentDirichletAllocation | NMF | None = None
        self._feature_names: list[str] | None = None
        self._tfidf_matrix: spmatrix | None = None

    @property
    def topic_config(self) -> TopicModelerConfig:
        """Access the topic modeler configuration."""
        return self._config

    def _tokenize(self, text: str) -> list[str]:
        """Tokenize text using RedditTokenizer for consistency."""
        return self._tokenizer.tokenize(text)

    def _auto_select_method(self, n_documents: int) -> TopicMethod:
        """
        Automatically select the best method based on data size.

        Args:
            n_documents: Number of documents in the corpus

        Returns:
            Selected method: "nmf" for small datasets, "lda" for larger ones
        """
        # NMF is faster and works better for small datasets
        # LDA provides better probabilistic interpretation for larger datasets
        if n_documents < 100:
            return "nmf"
        return "lda"

    def _create_vectorizer(self) -> TfidfVectorizer:
        """Create and configure the TF-IDF vectorizer."""
        return TfidfVectorizer(
            tokenizer=self._tokenize,
            lowercase=False,  # Tokenizer handles this
            max_features=self._config.max_features,
            min_df=self._config.min_df,
            max_df=self._config.max_df,
            token_pattern=None,  # Using custom tokenizer
        )

    def _create_model(self, method: TopicMethod) -> LatentDirichletAllocation | NMF:
        """
        Create the topic model based on the selected method.

        Args:
            method: The modeling method to use

        Returns:
            Configured topic model instance
        """
        random_state = self._config.random_state

        if method == "lda":
            return LatentDirichletAllocation(
                n_components=self._config.n_topics,
                max_iter=self._config.max_iter,
                learning_method="batch",
                random_state=random_state,
            )
        else:  # nmf
            return NMF(
                n_components=self._config.n_topics,
                max_iter=self._config.max_iter,
                random_state=random_state,
                init="nndsvda",  # Better initialization
            )

    def _extract_topic_words(
        self,
        model: LatentDirichletAllocation | NMF,
        feature_names: list[str],
    ) -> list[Topic]:
        """
        Extract top words for each topic from the fitted model.

        Args:
            model: Fitted topic model
            feature_names: Vocabulary feature names

        Returns:
            List of Topic objects with keywords and weights
        """
        topics = []

        for topic_idx, topic_vector in enumerate(model.components_):
            # Get indices of top words sorted by weight
            top_indices = topic_vector.argsort()[::-1][: self._config.n_top_words]

            keywords = [feature_names[i] for i in top_indices]
            weights = [float(topic_vector[i]) for i in top_indices]

            # Normalize weights to sum to 1
            weight_sum = sum(weights)
            if weight_sum > 0:
                weights = [w / weight_sum for w in weights]

            topics.append(
                Topic(
                    id=topic_idx,
                    keywords=keywords,
                    weights=weights,
                )
            )

        return topics

    def _calculate_coherence(
        self,
        topics: list[Topic],
        tfidf_matrix: spmatrix,
        feature_names: list[str],
    ) -> float:
        """
        Calculate a simplified coherence score based on co-occurrence.

        This is a simplified version of the UMass coherence score.
        Higher values indicate more coherent topics.

        Args:
            topics: List of topics with keywords
            tfidf_matrix: Document-term TF-IDF matrix
            feature_names: Feature names from vectorizer

        Returns:
            Average coherence score across topics
        """
        # Build feature name to index mapping
        feature_to_idx = {name: idx for idx, name in enumerate(feature_names)}

        # Convert to dense array for easier computation
        doc_term_matrix = (tfidf_matrix > 0).toarray()  # Binary occurrence matrix

        topic_coherences = []

        for topic in topics:
            # Get indices for topic keywords that exist in vocabulary
            word_indices = [
                feature_to_idx[kw]
                for kw in topic.keywords
                if kw in feature_to_idx
            ]

            if len(word_indices) < 2:
                continue

            # Calculate pairwise co-occurrence coherence
            coherence_sum = 0.0
            pair_count = 0

            for i in range(len(word_indices)):
                for j in range(i + 1, len(word_indices)):
                    # Count documents where both words appear
                    both = np.sum(
                        doc_term_matrix[:, word_indices[i]]
                        & doc_term_matrix[:, word_indices[j]]
                    )
                    # Count documents where first word appears
                    first = np.sum(doc_term_matrix[:, word_indices[i]])

                    if first > 0:
                        # Log probability ratio (simplified UMass)
                        coherence_sum += np.log((both + 1) / first)
                        pair_count += 1

            if pair_count > 0:
                topic_coherences.append(coherence_sum / pair_count)

        if not topic_coherences:
            return 0.0

        return float(np.mean(topic_coherences))

    def _compute_document_topic_distribution(
        self,
        tfidf_matrix: spmatrix,
    ) -> list[list[float]]:
        """
        Compute topic distribution for each document.

        Args:
            tfidf_matrix: TF-IDF matrix of documents

        Returns:
            List of topic probability distributions per document
        """
        if self._model is None:
            return []

        # Transform to get document-topic matrix
        doc_topics = self._model.transform(tfidf_matrix)

        # Normalize to probabilities per document
        distributions = []
        for doc_vec in doc_topics:
            total = doc_vec.sum()
            if total > 0:
                normalized = (doc_vec / total).tolist()
            else:
                normalized = [1.0 / len(doc_vec)] * len(doc_vec)
            distributions.append(normalized)

        return distributions

    def fit_transform(self, texts: list[str]) -> TopicResult:
        """
        Fit the topic model and extract topics from texts.

        Args:
            texts: List of text documents to analyze

        Returns:
            TopicResult containing discovered topics and metrics

        Raises:
            ValueError: If texts is empty or has insufficient data
        """
        if not texts:
            raise ValueError("Cannot fit on empty corpus")

        # Filter empty texts
        valid_texts = [t for t in texts if t and t.strip()]
        if len(valid_texts) < 2:
            raise ValueError("Need at least 2 non-empty documents for topic modeling")

        start_time = time.time()

        # Determine method
        method: TopicMethod = self._config.method
        if method == "auto":
            method = self._auto_select_method(len(valid_texts))

        # Create and fit vectorizer
        self._vectorizer = self._create_vectorizer()
        self._tfidf_matrix = self._vectorizer.fit_transform(valid_texts)
        self._feature_names = list(self._vectorizer.get_feature_names_out())

        # Adjust n_topics if more than features
        actual_n_topics = min(
            self._config.n_topics,
            self._tfidf_matrix.shape[1],
            len(valid_texts) - 1,
        )

        # Update config for actual topics used
        original_n_topics = self._config.n_topics
        self._config.n_topics = actual_n_topics

        # Create and fit model
        self._model = self._create_model(method)
        self._model.fit(self._tfidf_matrix)
        self._is_fitted = True

        # Restore original config
        self._config.n_topics = original_n_topics

        # Extract topics
        topics = self._extract_topic_words(self._model, self._feature_names)

        # Calculate coherence
        coherence_score = self._calculate_coherence(
            topics, self._tfidf_matrix, self._feature_names
        )

        # Get document-topic distributions
        doc_topic_dist = self._compute_document_topic_distribution(self._tfidf_matrix)

        # Calculate perplexity for LDA
        perplexity: float | None = None
        if isinstance(self._model, LatentDirichletAllocation):
            perplexity = float(self._model.perplexity(self._tfidf_matrix))

        processing_time = (time.time() - start_time) * 1000

        return TopicResult(
            topics=topics,
            n_topics=len(topics),
            coherence_score=coherence_score,
            method=method,
            perplexity=perplexity,
            document_topic_distribution=doc_topic_dist,
            parameters={
                "max_features": self._config.max_features,
                "min_df": self._config.min_df,
                "max_df": self._config.max_df,
                "n_top_words": self._config.n_top_words,
                "max_iter": self._config.max_iter,
                "processing_time_ms": processing_time,
                "n_documents": len(valid_texts),
            },
        )

    def get_document_topics(self, text: str) -> list[tuple[int, float]]:
        """
        Get topic distribution for a single document.

        Args:
            text: Document text to analyze

        Returns:
            List of (topic_id, probability) tuples sorted by probability

        Raises:
            RuntimeError: If model is not fitted
        """
        if not self._is_fitted or self._model is None or self._vectorizer is None:
            raise RuntimeError("Model not fitted. Call fit_transform() first.")

        # Transform single document
        tfidf_vec = self._vectorizer.transform([text])
        topic_dist = self._model.transform(tfidf_vec)[0]

        # Normalize
        total = topic_dist.sum()
        if total > 0:
            topic_dist = topic_dist / total

        # Create sorted list of (topic_id, probability)
        topic_probs = [(i, float(prob)) for i, prob in enumerate(topic_dist)]
        topic_probs.sort(key=lambda x: x[1], reverse=True)

        return topic_probs

    def analyze(self, data: Any) -> AnalysisResult:
        """
        Perform topic modeling analysis.

        Implementation of MLAnalyzerBase.analyze() interface.

        Args:
            data: List of texts to analyze

        Returns:
            AnalysisResult containing TopicResult
        """
        if not isinstance(data, list):
            return self._create_error_result(
                "topic",
                "Data must be a list of strings",
            )

        try:
            topic_result = self.fit_transform(data)
            return AnalysisResult(
                result_type="topic",
                data=topic_result.to_dict(),
                metadata=self._create_metadata(
                    data_size=len(data),
                    processing_time_ms=topic_result.parameters.get(
                        "processing_time_ms", 0.0
                    ),
                    parameters=topic_result.parameters,
                ),
                confidence=max(0.0, min(1.0, (topic_result.coherence_score + 10) / 10)),
                success=True,
            )
        except ValueError as e:
            return self._create_error_result("topic", str(e))
