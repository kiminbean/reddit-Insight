"""토픽 모델링 서비스.

TopicModeler ML 모듈을 래핑하여 대시보드용 토픽 분석 데이터를 제공한다.
"""

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

from reddit_insight.analysis.ml import TopicModeler, TopicModelerConfig
from reddit_insight.analysis.ml.models import TopicResult
from reddit_insight.dashboard.data_store import get_current_data


@dataclass
class TopicKeywordView:
    """토픽 키워드 뷰 데이터.

    Attributes:
        word: 키워드
        weight: 가중치 (0-1)
        weight_percent: 가중치 백분율
    """

    word: str
    weight: float
    weight_percent: float


@dataclass
class TopicView:
    """토픽 뷰 데이터.

    Attributes:
        id: 토픽 ID
        label: 토픽 레이블 (상위 3개 키워드 조합)
        keywords: 키워드 목록
        coherence: 토픽 coherence 점수
    """

    id: int
    label: str
    keywords: list[TopicKeywordView]
    coherence: float | None = None


@dataclass
class TopicAnalysisView:
    """토픽 분석 결과 뷰 데이터.

    대시보드에서 토픽 모델링 결과를 표시하기 위한 데이터 구조.

    Attributes:
        topics: 토픽 목록
        n_topics: 토픽 개수
        overall_coherence: 전체 coherence 점수
        method: 사용된 방법 (lda, nmf)
        document_count: 분석된 문서 수
        topic_distribution: 토픽별 문서 비율
    """

    topics: list[TopicView]
    n_topics: int
    overall_coherence: float
    method: str
    document_count: int
    topic_distribution: list[float] = field(default_factory=list)

    def to_chart_data(self) -> dict[str, Any]:
        """Chart.js 형식의 파이 차트 데이터로 변환한다.

        Returns:
            Chart.js에서 사용할 수 있는 데이터 딕셔너리
        """
        # 토픽별 문서 비율 계산
        labels = [f"Topic {t.id}: {t.label}" for t in self.topics]

        # 토픽별 색상 생성
        colors = self._generate_colors(len(self.topics))

        return {
            "labels": labels,
            "datasets": [
                {
                    "label": "Document Distribution",
                    "data": self.topic_distribution,
                    "backgroundColor": colors["background"],
                    "borderColor": colors["border"],
                    "borderWidth": 1,
                }
            ],
            "metadata": {
                "n_topics": self.n_topics,
                "method": self.method,
                "overall_coherence": round(self.overall_coherence, 3),
                "document_count": self.document_count,
                "topics": [
                    {
                        "id": t.id,
                        "label": t.label,
                        "coherence": round(t.coherence, 3) if t.coherence else None,
                        "keywords": [
                            {"word": kw.word, "weight": round(kw.weight, 3)}
                            for kw in t.keywords[:10]
                        ],
                    }
                    for t in self.topics
                ],
            },
        }

    def _generate_colors(self, count: int) -> dict[str, list[str]]:
        """토픽별 고유 색상을 생성한다.

        Args:
            count: 색상 개수

        Returns:
            background와 border 색상 목록
        """
        # 미리 정의된 색상 팔레트
        base_colors = [
            (59, 130, 246),   # blue
            (239, 68, 68),    # red
            (34, 197, 94),    # green
            (168, 85, 247),   # purple
            (249, 115, 22),   # orange
            (20, 184, 166),   # teal
            (236, 72, 153),   # pink
            (234, 179, 8),    # yellow
            (99, 102, 241),   # indigo
            (107, 114, 128),  # gray
        ]

        background = []
        border = []

        for i in range(count):
            r, g, b = base_colors[i % len(base_colors)]
            background.append(f"rgba({r}, {g}, {b}, 0.6)")
            border.append(f"rgb({r}, {g}, {b})")

        return {"background": background, "border": border}


class TopicService:
    """토픽 모델링 서비스.

    TopicModeler를 래핑하여 대시보드에서 사용할 수 있는 형태로 데이터를 제공한다.

    Example:
        >>> service = TopicService()
        >>> result = service.analyze_topics(n_topics=5)
        >>> chart_data = result.to_chart_data()
    """

    def __init__(self) -> None:
        """서비스를 초기화한다."""
        self._cached_result: TopicResult | None = None
        self._cached_documents: list[str] | None = None

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
                # description 필드
                if "description" in insight:
                    documents.append(insight["description"])
                # evidence 필드
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

    def analyze_topics(
        self,
        n_topics: int = 5,
        method: str = "auto",
        documents: list[str] | None = None,
    ) -> TopicAnalysisView:
        """토픽 분석을 수행한다.

        Args:
            n_topics: 추출할 토픽 수 (2-10)
            method: 토픽 모델링 방법 ("auto", "lda", "nmf")
            documents: 분석할 문서 목록 (None이면 저장된 데이터 사용)

        Returns:
            TopicAnalysisView: 토픽 분석 결과 뷰 데이터
        """
        # 파라미터 검증
        n_topics = max(2, min(10, n_topics))

        # 문서 로드
        if documents is None:
            documents = self._get_documents_from_data()

        if len(documents) < 2:
            return self._create_empty_result(n_topics, method)

        # TopicModeler 설정 및 실행
        config = TopicModelerConfig(
            n_topics=n_topics,
            method=method,  # type: ignore[arg-type]
            max_features=1000,
            min_df=1,  # 최소 문서 빈도를 낮춤 (데이터가 적을 수 있음)
            max_df=0.95,
            n_top_words=10,
        )

        modeler = TopicModeler(config)

        try:
            result = modeler.fit_transform(documents)
            self._cached_result = result
            self._cached_documents = documents

            return self._convert_to_view(result, len(documents))
        except Exception as e:
            # 분석 실패 시 빈 결과 반환
            return self._create_empty_result(n_topics, method, error_message=str(e))

    def _convert_to_view(
        self, result: TopicResult, document_count: int
    ) -> TopicAnalysisView:
        """TopicResult를 TopicAnalysisView로 변환한다.

        Args:
            result: TopicModeler 결과
            document_count: 분석된 문서 수

        Returns:
            TopicAnalysisView 인스턴스
        """
        topics = []
        for topic in result.topics:
            keywords = [
                TopicKeywordView(
                    word=kw,
                    weight=wt,
                    weight_percent=round(wt * 100, 1),
                )
                for kw, wt in zip(topic.keywords, topic.weights)
            ]

            topics.append(
                TopicView(
                    id=topic.id,
                    label=topic.label,
                    keywords=keywords,
                    coherence=topic.coherence,
                )
            )

        # 토픽별 문서 분포 계산
        topic_distribution = self._calculate_topic_distribution(
            result.document_topic_distribution, result.n_topics
        )

        return TopicAnalysisView(
            topics=topics,
            n_topics=result.n_topics,
            overall_coherence=result.coherence_score,
            method=result.method,
            document_count=document_count,
            topic_distribution=topic_distribution,
        )

    def _calculate_topic_distribution(
        self,
        doc_topic_dist: list[list[float]],
        n_topics: int,
    ) -> list[float]:
        """토픽별 문서 분포를 계산한다.

        각 문서에서 가장 높은 확률의 토픽을 해당 문서의 토픽으로 할당하고,
        각 토픽에 할당된 문서의 비율을 계산한다.

        Args:
            doc_topic_dist: 문서별 토픽 확률 분포
            n_topics: 토픽 수

        Returns:
            토픽별 문서 비율 (백분율)
        """
        if not doc_topic_dist:
            return [100 / n_topics] * n_topics if n_topics > 0 else []

        # 각 토픽에 할당된 문서 수 카운트
        topic_counts = [0] * n_topics

        for doc_dist in doc_topic_dist:
            if doc_dist:
                # 가장 높은 확률의 토픽 인덱스
                dominant_topic = max(range(len(doc_dist)), key=lambda i: doc_dist[i])
                if dominant_topic < n_topics:
                    topic_counts[dominant_topic] += 1

        # 백분율로 변환
        total_docs = len(doc_topic_dist)
        if total_docs == 0:
            return [100 / n_topics] * n_topics if n_topics > 0 else []

        return [round((count / total_docs) * 100, 1) for count in topic_counts]

    def _create_empty_result(
        self,
        n_topics: int,
        method: str,
        error_message: str | None = None,
    ) -> TopicAnalysisView:
        """빈 결과를 생성한다.

        Args:
            n_topics: 요청된 토픽 수
            method: 요청된 방법
            error_message: 에러 메시지 (있는 경우)

        Returns:
            빈 TopicAnalysisView
        """
        method_name = method
        if error_message:
            method_name = f"{method} (Error: {error_message[:30]})"

        return TopicAnalysisView(
            topics=[],
            n_topics=0,
            overall_coherence=0.0,
            method=method_name,
            document_count=0,
            topic_distribution=[],
        )

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
def get_topic_service() -> TopicService:
    """TopicService 싱글톤 인스턴스를 반환한다.

    Returns:
        TopicService 인스턴스
    """
    return TopicService()
