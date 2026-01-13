"""
Text clustering module for Reddit analysis.

Provides K-means and Agglomerative clustering for grouping similar texts
such as Reddit posts with similar demands or complaints.

Example:
    >>> from reddit_insight.analysis.ml.text_clusterer import TextClusterer, TextClustererConfig
    >>> clusterer = TextClusterer(TextClustererConfig(n_clusters=3))
    >>> result = clusterer.cluster(texts)
    >>> for cluster in result.clusters:
    ...     print(f"Cluster {cluster.id}: {cluster.keywords[:3]}")
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

import numpy as np
from numpy.typing import NDArray
from scipy.sparse import spmatrix
from sklearn.cluster import AgglomerativeClustering, KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import silhouette_score

from reddit_insight.analysis.ml.base import (
    AnalysisResult,
    MLAnalyzerBase,
    MLAnalyzerConfig,
)
from reddit_insight.analysis.ml.models import Cluster, ClusterResult
from reddit_insight.analysis.tokenizer import RedditTokenizer

if TYPE_CHECKING:
    pass


ClusterMethod = Literal["kmeans", "agglomerative", "auto"]


@dataclass
class TextClustererConfig(MLAnalyzerConfig):
    """
    Configuration for text clustering.

    Attributes:
        n_clusters: Number of clusters (None for automatic selection)
        method: Clustering method ("kmeans", "agglomerative", or "auto")
        max_features: Maximum vocabulary size for TF-IDF
        min_cluster_size: Minimum documents per cluster for auto selection
        max_clusters: Maximum clusters for automatic selection
        n_keywords: Number of keywords to extract per cluster
        min_df: Minimum document frequency for terms
        max_df: Maximum document frequency for terms
    """

    n_clusters: int | None = None
    method: ClusterMethod = "auto"
    max_features: int = 500
    min_cluster_size: int = 2
    max_clusters: int = 10
    n_keywords: int = 5
    min_df: int = 1
    max_df: float = 0.95


class TextClusterer(MLAnalyzerBase):
    """
    Text clusterer using K-means or Agglomerative clustering.

    Groups similar texts together based on TF-IDF representations.
    Supports automatic cluster count selection using silhouette score.

    Example:
        >>> config = TextClustererConfig(n_clusters=3)
        >>> clusterer = TextClusterer(config)
        >>> result = clusterer.cluster(texts)
        >>> print(f"Created {result.n_clusters} clusters")
        >>> for cluster in result.clusters:
        ...     print(f"  {cluster.label}: {cluster.size} items")
    """

    def __init__(self, config: TextClustererConfig | None = None) -> None:
        """
        Initialize the text clusterer.

        Args:
            config: Configuration for the clusterer, uses defaults if None
        """
        self._config = config or TextClustererConfig()
        super().__init__(self._config)
        self._tokenizer = RedditTokenizer()
        self._vectorizer: TfidfVectorizer | None = None
        self._model: KMeans | AgglomerativeClustering | None = None
        self._feature_names: list[str] | None = None
        self._tfidf_matrix: spmatrix | None = None
        self._labels: NDArray[np.int_] | None = None

    @property
    def cluster_config(self) -> TextClustererConfig:
        """Access the clusterer configuration."""
        return self._config

    def _tokenize(self, text: str) -> list[str]:
        """Tokenize text using RedditTokenizer for consistency."""
        return self._tokenizer.tokenize(text)

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

    def _find_optimal_k(
        self,
        X: spmatrix,
        max_k: int,
    ) -> int:
        """
        Find optimal number of clusters using silhouette score.

        Args:
            X: TF-IDF matrix of documents
            max_k: Maximum number of clusters to try

        Returns:
            Optimal number of clusters
        """
        n_samples = X.shape[0]

        # Ensure reasonable bounds
        min_k = 2
        max_k = min(max_k, n_samples - 1, n_samples // self._config.min_cluster_size)

        if max_k < min_k:
            return min_k

        best_k = min_k
        best_score = -1.0

        # Convert to dense for silhouette calculation
        X_dense = X.toarray() if hasattr(X, "toarray") else X

        for k in range(min_k, max_k + 1):
            kmeans = KMeans(
                n_clusters=k,
                random_state=self._config.random_state,
                n_init=10,
            )
            labels = kmeans.fit_predict(X_dense)

            # Calculate silhouette score
            try:
                score = silhouette_score(X_dense, labels)
                if score > best_score:
                    best_score = score
                    best_k = k
            except ValueError:
                # May fail if all points in one cluster
                continue

        return best_k

    def _create_model(
        self,
        method: ClusterMethod,
        n_clusters: int,
    ) -> KMeans | AgglomerativeClustering:
        """
        Create the clustering model.

        Args:
            method: Clustering method to use
            n_clusters: Number of clusters

        Returns:
            Configured clustering model
        """
        if method == "agglomerative":
            return AgglomerativeClustering(
                n_clusters=n_clusters,
                linkage="ward",
            )
        else:  # kmeans or auto defaults to kmeans
            return KMeans(
                n_clusters=n_clusters,
                random_state=self._config.random_state,
                n_init=10,
            )

    def _extract_cluster_keywords(
        self,
        X: spmatrix,
        labels: NDArray[np.int_],
        feature_names: list[str],
    ) -> dict[int, list[str]]:
        """
        Extract representative keywords for each cluster.

        Args:
            X: TF-IDF matrix
            labels: Cluster assignments
            feature_names: Vocabulary feature names

        Returns:
            Dictionary mapping cluster ID to list of keywords
        """
        X_dense = X.toarray() if hasattr(X, "toarray") else X
        cluster_keywords: dict[int, list[str]] = {}

        unique_labels = np.unique(labels)

        for cluster_id in unique_labels:
            # Get indices of documents in this cluster
            cluster_mask = labels == cluster_id

            if not np.any(cluster_mask):
                cluster_keywords[int(cluster_id)] = []
                continue

            # Calculate mean TF-IDF for cluster
            cluster_center = X_dense[cluster_mask].mean(axis=0)

            # Ensure it's 1D
            if hasattr(cluster_center, "A1"):
                cluster_center = cluster_center.A1
            else:
                cluster_center = np.asarray(cluster_center).flatten()

            # Get top keywords by weight
            top_indices = cluster_center.argsort()[::-1][: self._config.n_keywords]
            keywords = [
                feature_names[i] for i in top_indices if cluster_center[i] > 0
            ]

            cluster_keywords[int(cluster_id)] = keywords

        return cluster_keywords

    def _get_cluster_centroids(
        self,
        X: spmatrix,
        labels: NDArray[np.int_],
    ) -> dict[int, list[float]]:
        """
        Calculate centroids for each cluster.

        Args:
            X: TF-IDF matrix
            labels: Cluster assignments

        Returns:
            Dictionary mapping cluster ID to centroid coordinates
        """
        X_dense = X.toarray() if hasattr(X, "toarray") else X
        centroids: dict[int, list[float]] = {}

        unique_labels = np.unique(labels)

        for cluster_id in unique_labels:
            cluster_mask = labels == cluster_id

            if not np.any(cluster_mask):
                centroids[int(cluster_id)] = []
                continue

            # Calculate centroid as mean of cluster points
            center = X_dense[cluster_mask].mean(axis=0)

            # Convert to list
            if hasattr(center, "A1"):
                center_list = center.A1.tolist()
            else:
                center_list = np.asarray(center).flatten().tolist()

            centroids[int(cluster_id)] = center_list

        return centroids

    def _get_representative_items(
        self,
        texts: list[str],
        labels: NDArray[np.int_],
        n_items: int = 3,
    ) -> dict[int, list[str]]:
        """
        Get representative text samples for each cluster.

        Args:
            texts: Original text documents
            labels: Cluster assignments
            n_items: Number of representative items per cluster

        Returns:
            Dictionary mapping cluster ID to sample texts
        """
        representatives: dict[int, list[str]] = {}
        unique_labels = np.unique(labels)

        for cluster_id in unique_labels:
            cluster_mask = labels == cluster_id
            cluster_texts = [
                texts[i] for i in range(len(texts)) if cluster_mask[i]
            ]

            # Take first n_items as representatives (could be improved with
            # selection based on distance to centroid)
            representatives[int(cluster_id)] = cluster_texts[:n_items]

        return representatives

    def cluster(self, texts: list[str]) -> ClusterResult:
        """
        Cluster the input texts.

        Args:
            texts: List of text documents to cluster

        Returns:
            ClusterResult containing clusters and metrics

        Raises:
            ValueError: If texts is empty or has insufficient data
        """
        if not texts:
            raise ValueError("Cannot cluster empty corpus")

        # Filter empty texts
        valid_texts = [t for t in texts if t and t.strip()]
        if len(valid_texts) < 2:
            raise ValueError("Need at least 2 non-empty documents for clustering")

        start_time = time.time()

        # Create and fit vectorizer
        self._vectorizer = self._create_vectorizer()
        self._tfidf_matrix = self._vectorizer.fit_transform(valid_texts)
        self._feature_names = list(self._vectorizer.get_feature_names_out())

        # Determine number of clusters
        n_clusters = self._config.n_clusters
        if n_clusters is None:
            # Auto-select optimal k
            max_k = min(self._config.max_clusters, len(valid_texts) - 1)
            n_clusters = self._find_optimal_k(self._tfidf_matrix, max_k)
        else:
            # Ensure n_clusters doesn't exceed data size
            n_clusters = min(n_clusters, len(valid_texts) - 1)

        # Determine method
        method: ClusterMethod = self._config.method
        if method == "auto":
            # K-means is generally faster and works well for text
            method = "kmeans"

        # Create and fit model
        self._model = self._create_model(method, n_clusters)

        # Get dense matrix for fitting
        X_dense = self._tfidf_matrix.toarray()

        # Fit and get labels
        self._labels = self._model.fit_predict(X_dense)
        self._is_fitted = True

        # Calculate silhouette score
        try:
            sil_score = float(silhouette_score(X_dense, self._labels))
        except ValueError:
            sil_score = 0.0

        # Extract cluster information
        cluster_keywords = self._extract_cluster_keywords(
            self._tfidf_matrix, self._labels, self._feature_names
        )
        cluster_centroids = self._get_cluster_centroids(
            self._tfidf_matrix, self._labels
        )
        cluster_representatives = self._get_representative_items(
            valid_texts, self._labels
        )

        # Build Cluster objects
        clusters = []
        unique_labels = np.unique(self._labels)

        for cluster_id in unique_labels:
            size = int(np.sum(self._labels == cluster_id))
            keywords = cluster_keywords.get(int(cluster_id), [])

            # Generate label from keywords
            if keywords:
                label = "_".join(keywords[:3])
            else:
                label = f"cluster_{cluster_id}"

            clusters.append(
                Cluster(
                    id=int(cluster_id),
                    label=label,
                    size=size,
                    centroid=cluster_centroids.get(int(cluster_id), []),
                    keywords=keywords,
                    representative_items=cluster_representatives.get(
                        int(cluster_id), []
                    ),
                )
            )

        # Get inertia for K-means
        inertia: float | None = None
        if isinstance(self._model, KMeans):
            inertia = float(self._model.inertia_)

        processing_time = (time.time() - start_time) * 1000

        return ClusterResult(
            clusters=clusters,
            n_clusters=len(clusters),
            silhouette_score=sil_score,
            method=method,
            inertia=inertia,
            labels=self._labels.tolist(),
            parameters={
                "max_features": self._config.max_features,
                "min_cluster_size": self._config.min_cluster_size,
                "n_keywords": self._config.n_keywords,
                "processing_time_ms": processing_time,
                "n_documents": len(valid_texts),
            },
        )

    def assign_cluster(self, text: str) -> int:
        """
        Assign a new text to an existing cluster.

        Args:
            text: Text document to assign

        Returns:
            Cluster ID for the text

        Raises:
            RuntimeError: If model is not fitted
        """
        if not self._is_fitted or self._model is None or self._vectorizer is None:
            raise RuntimeError("Model not fitted. Call cluster() first.")

        # Transform text to TF-IDF
        tfidf_vec = self._vectorizer.transform([text])

        # For K-means, use predict
        if isinstance(self._model, KMeans):
            return int(self._model.predict(tfidf_vec.toarray())[0])

        # For Agglomerative, find nearest centroid
        X_dense = tfidf_vec.toarray()[0]
        if self._tfidf_matrix is None or self._labels is None:
            raise RuntimeError("Internal state error: missing matrix or labels")

        # Calculate centroids
        centroids = self._get_cluster_centroids(self._tfidf_matrix, self._labels)

        # Find nearest centroid
        min_dist = float("inf")
        nearest_cluster = 0

        for cluster_id, centroid in centroids.items():
            if not centroid:
                continue
            # Euclidean distance
            dist = np.sqrt(np.sum((X_dense - np.array(centroid)) ** 2))
            if dist < min_dist:
                min_dist = dist
                nearest_cluster = cluster_id

        return nearest_cluster

    def analyze(self, data: Any) -> AnalysisResult:
        """
        Perform clustering analysis.

        Implementation of MLAnalyzerBase.analyze() interface.

        Args:
            data: List of texts to cluster

        Returns:
            AnalysisResult containing ClusterResult
        """
        if not isinstance(data, list):
            return self._create_error_result(
                "cluster",
                "Data must be a list of strings",
            )

        try:
            cluster_result = self.cluster(data)
            return AnalysisResult(
                result_type="cluster",
                data=cluster_result.to_dict(),
                metadata=self._create_metadata(
                    data_size=len(data),
                    processing_time_ms=cluster_result.parameters.get(
                        "processing_time_ms", 0.0
                    ),
                    parameters=cluster_result.parameters,
                ),
                confidence=max(0.0, min(1.0, (cluster_result.silhouette_score + 1) / 2)),
                success=True,
            )
        except ValueError as e:
            return self._create_error_result("cluster", str(e))
