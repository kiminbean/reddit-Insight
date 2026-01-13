"""텍스트 클러스터링 서비스.

TextClusterer ML 모듈을 래핑하여 대시보드용 클러스터링 데이터를 제공한다.
"""

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

from reddit_insight.analysis.ml import TextClusterer, TextClustererConfig
from reddit_insight.analysis.ml.models import ClusterResult
from reddit_insight.dashboard.data_store import get_current_data


@dataclass
class ClusterKeywordView:
    """클러스터 키워드 뷰 데이터.

    Attributes:
        word: 키워드
        rank: 순위 (1부터 시작)
    """

    word: str
    rank: int


@dataclass
class ClusterView:
    """클러스터 뷰 데이터.

    Attributes:
        id: 클러스터 ID
        label: 클러스터 레이블 (상위 키워드 조합)
        size: 클러스터 내 문서 수
        keywords: 대표 키워드 목록
        sample_docs: 샘플 문서 목록
        percentage: 전체 대비 비율 (%)
    """

    id: int
    label: str
    size: int
    keywords: list[ClusterKeywordView]
    sample_docs: list[str]
    percentage: float = 0.0


@dataclass
class ClusterAnalysisView:
    """클러스터링 분석 결과 뷰 데이터.

    대시보드에서 클러스터링 결과를 표시하기 위한 데이터 구조.

    Attributes:
        clusters: 클러스터 목록
        n_clusters: 클러스터 개수
        silhouette_score: 실루엣 점수 (-1 ~ 1, 높을수록 좋음)
        method: 사용된 방법 (kmeans, agglomerative)
        document_count: 분석된 문서 수
        cluster_sizes: 클러스터별 문서 수 목록 (차트용)
    """

    clusters: list[ClusterView]
    n_clusters: int
    silhouette_score: float
    method: str
    document_count: int
    cluster_sizes: list[int] = field(default_factory=list)

    def to_chart_data(self) -> dict[str, Any]:
        """Chart.js 형식의 바 차트 데이터로 변환한다.

        Returns:
            Chart.js에서 사용할 수 있는 데이터 딕셔너리
        """
        labels = [f"Cluster {c.id}: {c.label}" for c in self.clusters]
        sizes = [c.size for c in self.clusters]

        colors = self._generate_colors(len(self.clusters))

        return {
            "labels": labels,
            "datasets": [
                {
                    "label": "Document Count",
                    "data": sizes,
                    "backgroundColor": colors["background"],
                    "borderColor": colors["border"],
                    "borderWidth": 1,
                }
            ],
            "metadata": {
                "n_clusters": self.n_clusters,
                "method": self.method,
                "silhouette_score": round(self.silhouette_score, 3),
                "document_count": self.document_count,
                "clusters": [
                    {
                        "id": c.id,
                        "label": c.label,
                        "size": c.size,
                        "percentage": round(c.percentage, 1),
                        "keywords": [{"word": kw.word, "rank": kw.rank} for kw in c.keywords],
                        "sample_docs": c.sample_docs[:3],
                    }
                    for c in self.clusters
                ],
            },
        }

    def _generate_colors(self, count: int) -> dict[str, list[str]]:
        """클러스터별 고유 색상을 생성한다.

        Args:
            count: 색상 개수

        Returns:
            background와 border 색상 목록
        """
        base_colors = [
            (59, 130, 246),  # blue
            (239, 68, 68),  # red
            (34, 197, 94),  # green
            (168, 85, 247),  # purple
            (249, 115, 22),  # orange
            (20, 184, 166),  # teal
            (236, 72, 153),  # pink
            (234, 179, 8),  # yellow
            (99, 102, 241),  # indigo
            (107, 114, 128),  # gray
        ]

        background = []
        border = []

        for i in range(count):
            r, g, b = base_colors[i % len(base_colors)]
            background.append(f"rgba({r}, {g}, {b}, 0.6)")
            border.append(f"rgb({r}, {g}, {b})")

        return {"background": background, "border": border}


class ClusterService:
    """텍스트 클러스터링 서비스.

    TextClusterer를 래핑하여 대시보드에서 사용할 수 있는 형태로 데이터를 제공한다.

    Example:
        >>> service = ClusterService()
        >>> result = service.cluster_documents(n_clusters=5)
        >>> chart_data = result.to_chart_data()
    """

    def __init__(self) -> None:
        """서비스를 초기화한다."""
        self._cached_result: ClusterResult | None = None
        self._cached_documents: list[str] | None = None
        self._cached_labels: list[int] | None = None

    def _get_documents_from_data(self) -> list[str]:
        """저장된 분석 데이터에서 문서(텍스트)를 추출한다.

        Returns:
            문서 텍스트 목록
        """
        data = get_current_data()
        if data is None:
            return []

        documents = []

        # 인사이트에서 텍스트 추출
        for insight in data.insights:
            if isinstance(insight, dict):
                if "description" in insight:
                    documents.append(insight["description"])
                if "evidence" in insight and isinstance(insight["evidence"], list):
                    for evidence in insight["evidence"]:
                        if isinstance(evidence, str):
                            documents.append(evidence)

        # 키워드 데이터에서 관련 텍스트 추출
        for kw in data.keywords:
            if isinstance(kw, dict) and "keyword" in kw:
                documents.append(kw["keyword"])

        # demands에서 텍스트 추출
        if data.demands and isinstance(data.demands, dict):
            pain_points = data.demands.get("pain_points", [])
            for pp in pain_points:
                if isinstance(pp, dict):
                    if "text" in pp:
                        documents.append(pp["text"])
                    if "description" in pp:
                        documents.append(pp["description"])

            feature_requests = data.demands.get("feature_requests", [])
            for fr in feature_requests:
                if isinstance(fr, dict):
                    if "text" in fr:
                        documents.append(fr["text"])
                    if "description" in fr:
                        documents.append(fr["description"])

        # competition에서 텍스트 추출
        if data.competition and isinstance(data.competition, dict):
            entities = data.competition.get("entities", [])
            for entity in entities:
                if isinstance(entity, dict):
                    if "name" in entity:
                        documents.append(entity["name"])
                    if "mentions" in entity and isinstance(entity["mentions"], list):
                        for mention in entity["mentions"]:
                            if isinstance(mention, str):
                                documents.append(mention)

            complaints = data.competition.get("complaints", [])
            for complaint in complaints:
                if isinstance(complaint, dict) and "text" in complaint:
                    documents.append(complaint["text"])

        # 빈 문자열 및 너무 짧은 문서 필터링
        documents = [doc.strip() for doc in documents if doc and len(doc.strip()) > 10]

        return documents

    def cluster_documents(
        self,
        n_clusters: int | None = None,
        method: str = "auto",
        documents: list[str] | None = None,
    ) -> ClusterAnalysisView:
        """문서 클러스터링을 수행한다.

        Args:
            n_clusters: 클러스터 수 (None이면 자동 선택)
            method: 클러스터링 방법 ("auto", "kmeans", "agglomerative")
            documents: 클러스터링할 문서 목록 (None이면 저장된 데이터 사용)

        Returns:
            ClusterAnalysisView: 클러스터링 분석 결과 뷰 데이터
        """
        # 문서 로드
        if documents is None:
            documents = self._get_documents_from_data()

        if len(documents) < 2:
            return self._create_empty_result(n_clusters or 0, method)

        # n_clusters 검증
        max_possible = min(10, len(documents) - 1)
        if n_clusters is not None:
            n_clusters = max(2, min(n_clusters, max_possible))

        # TextClusterer 설정 및 실행
        config = TextClustererConfig(
            n_clusters=n_clusters,
            method=method,  # type: ignore[arg-type]
            max_features=500,
            min_df=1,
            max_df=0.95,
            n_keywords=5,
            max_clusters=max_possible,
        )

        clusterer = TextClusterer(config)

        try:
            result = clusterer.cluster(documents)
            self._cached_result = result
            self._cached_documents = documents
            self._cached_labels = result.labels

            return self._convert_to_view(result, len(documents))
        except Exception as e:
            return self._create_empty_result(
                n_clusters or 0, method, error_message=str(e)
            )

    def _convert_to_view(
        self, result: ClusterResult, document_count: int
    ) -> ClusterAnalysisView:
        """ClusterResult를 ClusterAnalysisView로 변환한다.

        Args:
            result: TextClusterer 결과
            document_count: 분석된 문서 수

        Returns:
            ClusterAnalysisView 인스턴스
        """
        clusters = []
        total_size = sum(c.size for c in result.clusters)

        for cluster in result.clusters:
            keywords = [
                ClusterKeywordView(word=kw, rank=i + 1)
                for i, kw in enumerate(cluster.keywords)
            ]

            percentage = (cluster.size / total_size * 100) if total_size > 0 else 0

            # 샘플 문서 (처음 100자만)
            sample_docs = [doc[:100] + "..." if len(doc) > 100 else doc for doc in cluster.representative_items[:3]]

            clusters.append(
                ClusterView(
                    id=cluster.id,
                    label=cluster.label,
                    size=cluster.size,
                    keywords=keywords,
                    sample_docs=sample_docs,
                    percentage=percentage,
                )
            )

        # 크기순으로 정렬
        clusters.sort(key=lambda c: c.size, reverse=True)

        return ClusterAnalysisView(
            clusters=clusters,
            n_clusters=result.n_clusters,
            silhouette_score=result.silhouette_score,
            method=result.method,
            document_count=document_count,
            cluster_sizes=[c.size for c in clusters],
        )

    def _create_empty_result(
        self,
        n_clusters: int,
        method: str,
        error_message: str | None = None,
    ) -> ClusterAnalysisView:
        """빈 결과를 생성한다.

        Args:
            n_clusters: 요청된 클러스터 수
            method: 요청된 방법
            error_message: 에러 메시지 (있는 경우)

        Returns:
            빈 ClusterAnalysisView
        """
        method_name = method
        if error_message:
            method_name = f"{method} (Error: {error_message[:50]})"

        return ClusterAnalysisView(
            clusters=[],
            n_clusters=0,
            silhouette_score=0.0,
            method=method_name,
            document_count=0,
            cluster_sizes=[],
        )

    def get_cluster_documents(self, cluster_id: int) -> list[str]:
        """특정 클러스터에 속한 모든 문서를 반환한다.

        Args:
            cluster_id: 클러스터 ID

        Returns:
            해당 클러스터의 문서 목록
        """
        if self._cached_documents is None or self._cached_labels is None:
            return []

        return [
            doc
            for doc, label in zip(self._cached_documents, self._cached_labels)
            if label == cluster_id
        ]

    def get_cluster_by_id(self, cluster_id: int) -> ClusterView | None:
        """특정 클러스터 정보를 반환한다.

        Args:
            cluster_id: 클러스터 ID

        Returns:
            ClusterView 또는 None
        """
        if self._cached_result is None:
            return None

        for cluster in self._cached_result.clusters:
            if cluster.id == cluster_id:
                keywords = [
                    ClusterKeywordView(word=kw, rank=i + 1)
                    for i, kw in enumerate(cluster.keywords)
                ]

                total_size = sum(c.size for c in self._cached_result.clusters)
                percentage = (cluster.size / total_size * 100) if total_size > 0 else 0

                sample_docs = [
                    doc[:100] + "..." if len(doc) > 100 else doc
                    for doc in cluster.representative_items[:3]
                ]

                return ClusterView(
                    id=cluster.id,
                    label=cluster.label,
                    size=cluster.size,
                    keywords=keywords,
                    sample_docs=sample_docs,
                    percentage=percentage,
                )

        return None

    def get_available_document_count(self) -> int:
        """분석 가능한 문서 수를 반환한다.

        Returns:
            문서 수
        """
        return len(self._get_documents_from_data())


# =============================================================================
# DEPENDENCY INJECTION
# =============================================================================


@lru_cache(maxsize=1)
def get_cluster_service() -> ClusterService:
    """ClusterService 싱글톤 인스턴스를 반환한다.

    Returns:
        ClusterService 인스턴스
    """
    return ClusterService()
