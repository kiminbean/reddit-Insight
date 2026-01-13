"""
Demand analysis and prioritization module.

수요를 분류하고 비즈니스 관점에서 우선순위를 부여하는 모듈.
클러스터링, 우선순위 점수 계산, 리포트 생성을 담당한다.

Example:
    >>> from reddit_insight.analysis.demand_analyzer import DemandAnalyzer
    >>> analyzer = DemandAnalyzer()
    >>> report = analyzer.analyze_posts(posts)
    >>> print(report.top_opportunities[0].priority.total_score)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from reddit_insight.analysis.demand_detector import (
    DemandDetector,
)
from reddit_insight.analysis.demand_patterns import (
    DemandCategory,
    DemandMatch,
)

if TYPE_CHECKING:
    from reddit_insight.analysis.keywords import UnifiedKeywordExtractor
    from reddit_insight.reddit.models import Post


# =============================================================================
# DEMAND CLUSTERING
# =============================================================================


@dataclass
class DemandCluster:
    """
    유사한 수요를 그룹화한 클러스터.

    비슷한 수요 표현을 하나로 묶어 빈도와 대표 텍스트를 제공한다.

    Attributes:
        cluster_id: 클러스터 고유 식별자
        representative: 대표 수요 텍스트
        matches: 클러스터에 속한 수요 매칭 목록
        frequency: 발생 빈도 (매칭 수)
        categories: 포함된 카테고리 목록
        keywords: 관련 키워드 목록

    Example:
        >>> cluster = DemandCluster(
        ...     cluster_id="cluster_001",
        ...     representative="better way to organize notes",
        ...     matches=[match1, match2],
        ...     frequency=2,
        ...     categories=[DemandCategory.FEATURE_REQUEST],
        ...     keywords=["organize", "notes"]
        ... )
    """

    cluster_id: str
    representative: str
    matches: list[DemandMatch]
    frequency: int
    categories: list[DemandCategory]
    keywords: list[str] = field(default_factory=list)

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"DemandCluster(id='{self.cluster_id}', "
            f"representative='{self.representative[:30]}...', "
            f"frequency={self.frequency})"
        )

    @property
    def primary_category(self) -> DemandCategory | None:
        """Get the most common category in the cluster."""
        if not self.categories:
            return None
        # Count occurrences of each category
        category_counts: dict[DemandCategory, int] = {}
        for match in self.matches:
            cat = match.category
            category_counts[cat] = category_counts.get(cat, 0) + 1
        # Return the most common one
        return max(category_counts, key=category_counts.get)  # type: ignore

    @property
    def average_confidence(self) -> float:
        """Get the average confidence of matches in the cluster."""
        if not self.matches:
            return 0.0
        return sum(m.confidence for m in self.matches) / len(self.matches)


@dataclass
class DemandClusterer:
    """
    유사한 수요를 그룹화하는 클러스터러.

    키워드 겹침 기반으로 유사한 수요 표현을 클러스터링한다.

    Attributes:
        keyword_extractor: 키워드 추출기 (None이면 내부 생성)
        similarity_threshold: 유사도 임계값 (0-1)

    Example:
        >>> clusterer = DemandClusterer(similarity_threshold=0.7)
        >>> clusters = clusterer.cluster_demands(matches)
        >>> print(f"Found {len(clusters)} demand clusters")
    """

    keyword_extractor: UnifiedKeywordExtractor | None = None
    similarity_threshold: float = 0.7
    _initialized: bool = field(default=False, repr=False)

    def __post_init__(self) -> None:
        """Initialize keyword extractor if needed."""
        if self.keyword_extractor is None:
            # Lazy import to avoid circular dependency
            from reddit_insight.analysis.keywords import UnifiedKeywordExtractor

            self.keyword_extractor = UnifiedKeywordExtractor()
        self._initialized = True

    def _extract_keywords_from_text(self, text: str) -> set[str]:
        """
        텍스트에서 키워드 집합 추출.

        간단한 단어 기반 추출을 사용하여 빠른 유사도 계산을 지원한다.

        Args:
            text: 입력 텍스트

        Returns:
            소문자 키워드 집합
        """
        # Simple word-based extraction for fast similarity
        words = text.lower().split()
        # Filter short words and common stopwords
        stopwords = {
            "i", "a", "an", "the", "to", "for", "of", "is", "was", "with",
            "that", "this", "it", "be", "have", "has", "there", "would",
            "could", "should", "can", "if", "on", "in", "at", "by", "or",
            "and", "but", "so", "any", "some", "my", "your", "we", "they",
        }
        return {w for w in words if len(w) > 2 and w not in stopwords}

    def _calculate_similarity(
        self,
        match1: DemandMatch,
        match2: DemandMatch,
    ) -> float:
        """
        두 수요 매칭 간 유사도 계산.

        Jaccard 유사도를 사용하여 키워드 겹침을 측정한다.

        Args:
            match1: 첫 번째 수요 매칭
            match2: 두 번째 수요 매칭

        Returns:
            유사도 점수 (0-1)
        """
        # Extract keywords from context
        keywords1 = self._extract_keywords_from_text(match1.context)
        keywords2 = self._extract_keywords_from_text(match2.context)

        if not keywords1 or not keywords2:
            return 0.0

        # Jaccard similarity
        intersection = keywords1 & keywords2
        union = keywords1 | keywords2

        if not union:
            return 0.0

        return len(intersection) / len(union)

    def _extract_representative(self, matches: list[DemandMatch]) -> str:
        """
        클러스터 대표 텍스트 선정.

        신뢰도가 가장 높은 매칭의 컨텍스트를 대표 텍스트로 선정한다.

        Args:
            matches: 클러스터 내 매칭 목록

        Returns:
            대표 텍스트 문자열
        """
        if not matches:
            return ""

        # Select match with highest confidence
        best_match = max(matches, key=lambda m: m.confidence)

        # Extract meaningful part from context
        context = best_match.context.strip()

        # Truncate if too long
        if len(context) > 100:
            # Try to find sentence boundary
            end_markers = ".!?"
            for i in range(min(100, len(context)), 50, -1):
                if context[i - 1] in end_markers:
                    return context[:i]
            return context[:100] + "..."

        return context

    def _extract_cluster_keywords(
        self,
        matches: list[DemandMatch],
    ) -> list[str]:
        """
        클러스터에서 공통 키워드 추출.

        Args:
            matches: 클러스터 내 매칭 목록

        Returns:
            공통 키워드 목록
        """
        if not matches:
            return []

        # Collect all keywords
        all_keywords: dict[str, int] = {}
        for match in matches:
            keywords = self._extract_keywords_from_text(match.context)
            for kw in keywords:
                all_keywords[kw] = all_keywords.get(kw, 0) + 1

        # Return keywords that appear in multiple matches
        threshold = max(1, len(matches) // 2)
        common_keywords = [
            kw for kw, count in all_keywords.items()
            if count >= threshold
        ]

        # Sort by frequency
        common_keywords.sort(key=lambda k: all_keywords[k], reverse=True)

        return common_keywords[:10]  # Limit to top 10

    def cluster_demands(
        self,
        matches: list[DemandMatch],
    ) -> list[DemandCluster]:
        """
        유사한 수요를 그룹화.

        그리디 클러스터링 알고리즘을 사용하여 유사한 수요를 묶는다.

        Args:
            matches: 수요 매칭 목록

        Returns:
            수요 클러스터 목록

        Example:
            >>> clusters = clusterer.cluster_demands(matches)
            >>> for cluster in clusters:
            ...     print(f"{cluster.representative}: {cluster.frequency}")
        """
        if not matches:
            return []

        # Sort by confidence (descending) for better representative selection
        sorted_matches = sorted(
            matches, key=lambda m: m.confidence, reverse=True
        )

        # Greedy clustering
        clusters: list[list[DemandMatch]] = []
        used: set[int] = set()

        for i, match in enumerate(sorted_matches):
            if i in used:
                continue

            # Start new cluster
            cluster_matches = [match]
            used.add(i)

            # Find similar matches
            for j, other in enumerate(sorted_matches):
                if j in used:
                    continue

                similarity = self._calculate_similarity(match, other)
                if similarity >= self.similarity_threshold:
                    cluster_matches.append(other)
                    used.add(j)

            clusters.append(cluster_matches)

        # Convert to DemandCluster objects
        result: list[DemandCluster] = []
        for idx, cluster_matches in enumerate(clusters):
            # Collect unique categories
            categories = list({m.category for m in cluster_matches})

            cluster = DemandCluster(
                cluster_id=f"cluster_{idx:03d}",
                representative=self._extract_representative(cluster_matches),
                matches=cluster_matches,
                frequency=len(cluster_matches),
                categories=categories,
                keywords=self._extract_cluster_keywords(cluster_matches),
            )
            result.append(cluster)

        # Sort by frequency (descending)
        result.sort(key=lambda c: c.frequency, reverse=True)

        return result


# =============================================================================
# PRIORITY CALCULATION
# =============================================================================


@dataclass
class PriorityConfig:
    """
    우선순위 계산 설정.

    각 요소별 가중치를 정의한다.

    Attributes:
        frequency_weight: 빈도 가중치 (기본값: 0.3)
        payment_weight: 구매 의향 가중치 (기본값: 0.3)
        urgency_weight: 긴급성 가중치 (기본값: 0.2)
        recency_weight: 최신성 가중치 (기본값: 0.2)

    Example:
        >>> config = PriorityConfig(frequency_weight=0.4, payment_weight=0.3)
        >>> calculator = PriorityCalculator(config=config)
    """

    frequency_weight: float = 0.3
    payment_weight: float = 0.3
    urgency_weight: float = 0.2
    recency_weight: float = 0.2


@dataclass
class PriorityScore:
    """
    우선순위 점수 상세.

    클러스터의 비즈니스 우선순위를 다각도로 평가한 결과.

    Attributes:
        total_score: 총합 점수 (0-100)
        frequency_score: 빈도 점수 (0-100)
        payment_intent_score: 구매 의향 점수 (0-100)
        urgency_score: 긴급성 점수 (0-100)
        recency_score: 최신성 점수 (0-100)
        breakdown: 점수 세부 내역

    Example:
        >>> score = PriorityScore(
        ...     total_score=75.5,
        ...     frequency_score=80.0,
        ...     payment_intent_score=90.0,
        ...     urgency_score=60.0,
        ...     recency_score=70.0,
        ...     breakdown={"frequency": 24.0, "payment": 27.0, ...}
        ... )
    """

    total_score: float
    frequency_score: float
    payment_intent_score: float
    urgency_score: float
    recency_score: float
    breakdown: dict[str, float] = field(default_factory=dict)

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"PriorityScore(total={self.total_score:.1f})"


class PriorityCalculator:
    """
    수요 클러스터 우선순위 계산기.

    빈도, 구매 의향, 긴급성, 최신성 4가지 요소를 기반으로
    비즈니스 우선순위 점수를 계산한다.

    Attributes:
        config: 우선순위 설정

    Example:
        >>> calculator = PriorityCalculator()
        >>> score = calculator.calculate_priority(cluster)
        >>> print(f"Total score: {score.total_score}")
    """

    def __init__(self, config: PriorityConfig | None = None) -> None:
        """
        우선순위 계산기 초기화.

        Args:
            config: 우선순위 설정 (None이면 기본 설정 사용)
        """
        self.config = config or PriorityConfig()

    def _frequency_score(self, cluster: DemandCluster) -> float:
        """
        빈도 기반 점수 계산.

        로그 스케일을 사용하여 큰 빈도의 영향을 완화한다.

        Args:
            cluster: 수요 클러스터

        Returns:
            빈도 점수 (0-100)
        """
        # Log scale: score = 100 * log(1 + frequency) / log(1 + max_expected)
        # Assuming max_expected is 100 matches
        max_expected = 100
        normalized = math.log(1 + cluster.frequency) / math.log(1 + max_expected)
        return min(normalized * 100, 100)

    def _payment_intent_score(self, cluster: DemandCluster) -> float:
        """
        구매 의향 점수 계산.

        WILLINGNESS_TO_PAY 카테고리 비율에 기반한다.

        Args:
            cluster: 수요 클러스터

        Returns:
            구매 의향 점수 (0-100)
        """
        if not cluster.matches:
            return 0.0

        # Count WILLINGNESS_TO_PAY category
        wtp_count = sum(
            1 for m in cluster.matches
            if m.category == DemandCategory.WILLINGNESS_TO_PAY
        )

        # Ratio * 100, with bonus for any WTP presence
        ratio = wtp_count / len(cluster.matches)

        # Bonus: if any WTP exists, minimum 20 points
        if wtp_count > 0:
            return max(ratio * 100, 20) + 10  # +10 bonus for presence

        return ratio * 100

    def _urgency_score(self, cluster: DemandCluster) -> float:
        """
        긴급성 점수 계산.

        PAIN_POINT 카테고리 비율과 평균 신뢰도에 기반한다.

        Args:
            cluster: 수요 클러스터

        Returns:
            긴급성 점수 (0-100)
        """
        if not cluster.matches:
            return 0.0

        # Count PAIN_POINT category
        pain_count = sum(
            1 for m in cluster.matches
            if m.category == DemandCategory.PAIN_POINT
        )

        # Ratio weighted by average confidence
        ratio = pain_count / len(cluster.matches)
        confidence_factor = cluster.average_confidence

        return min(ratio * confidence_factor * 100 + 20, 100)

    def _recency_score(
        self,
        cluster: DemandCluster,
        reference_time: datetime | None = None,
    ) -> float:
        """
        최신성 점수 계산.

        시간 감쇠를 적용하여 최근 수요에 높은 점수를 부여한다.
        (현재는 시간 정보가 없어 평균 신뢰도 기반으로 대체)

        Args:
            cluster: 수요 클러스터
            reference_time: 기준 시간 (None이면 현재 시간)

        Returns:
            최신성 점수 (0-100)
        """
        # Since we don't have timestamps in DemandMatch,
        # use confidence as a proxy (higher confidence = more relevant)
        if not cluster.matches:
            return 0.0

        # Use average confidence as proxy for recency relevance
        return cluster.average_confidence * 100

    def calculate_priority(
        self,
        cluster: DemandCluster,
        reference_time: datetime | None = None,
    ) -> PriorityScore:
        """
        클러스터 우선순위 계산.

        4가지 요소를 가중 평균하여 총합 점수를 계산한다.

        Args:
            cluster: 수요 클러스터
            reference_time: 최신성 계산 기준 시간

        Returns:
            우선순위 점수 상세

        Example:
            >>> score = calculator.calculate_priority(cluster)
            >>> print(f"Total: {score.total_score:.1f}")
            >>> print(f"Breakdown: {score.breakdown}")
        """
        # Calculate individual scores
        freq_score = self._frequency_score(cluster)
        payment_score = self._payment_intent_score(cluster)
        urgency_score = self._urgency_score(cluster)
        recency_score = self._recency_score(cluster, reference_time)

        # Weighted total
        breakdown = {
            "frequency": freq_score * self.config.frequency_weight,
            "payment_intent": payment_score * self.config.payment_weight,
            "urgency": urgency_score * self.config.urgency_weight,
            "recency": recency_score * self.config.recency_weight,
        }

        total = sum(breakdown.values())

        return PriorityScore(
            total_score=total,
            frequency_score=freq_score,
            payment_intent_score=payment_score,
            urgency_score=urgency_score,
            recency_score=recency_score,
            breakdown=breakdown,
        )

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"PriorityCalculator(config={self.config})"


# =============================================================================
# INTEGRATED ANALYZER AND REPORT
# =============================================================================


@dataclass
class PrioritizedDemand:
    """
    우선순위가 부여된 수요.

    클러스터와 우선순위 점수, 순위를 함께 제공한다.

    Attributes:
        cluster: 수요 클러스터
        priority: 우선순위 점수
        rank: 순위 (1부터 시작)
        business_potential: 비즈니스 잠재력 (high/medium/low)

    Example:
        >>> demand = prioritized_demands[0]
        >>> print(f"Rank {demand.rank}: {demand.cluster.representative}")
        >>> print(f"Potential: {demand.business_potential}")
    """

    cluster: DemandCluster
    priority: PriorityScore
    rank: int
    business_potential: str = "medium"

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"PrioritizedDemand(rank={self.rank}, "
            f"score={self.priority.total_score:.1f}, "
            f"potential='{self.business_potential}')"
        )


@dataclass
class DemandReport:
    """
    수요 분석 리포트.

    전체 분석 결과를 요약한 리포트 데이터 구조.

    Attributes:
        generated_at: 리포트 생성 시간
        total_demands: 총 수요 탐지 수
        total_clusters: 총 클러스터 수
        top_opportunities: 상위 비즈니스 기회 목록
        by_category: 카테고리별 수요 수
        recommendations: 권장 사항 목록

    Example:
        >>> report = analyzer.analyze_posts(posts)
        >>> print(f"Found {report.total_clusters} demand clusters")
        >>> for opp in report.top_opportunities[:5]:
        ...     print(f"- {opp.cluster.representative}")
    """

    generated_at: datetime
    total_demands: int
    total_clusters: int
    top_opportunities: list[PrioritizedDemand]
    by_category: dict[DemandCategory, int]
    recommendations: list[str] = field(default_factory=list)

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"DemandReport(demands={self.total_demands}, "
            f"clusters={self.total_clusters}, "
            f"opportunities={len(self.top_opportunities)})"
        )


class DemandAnalyzer:
    """
    수요 통합 분석기.

    수요 탐지, 클러스터링, 우선순위화를 통합하여 비즈니스 인사이트를 제공한다.

    Attributes:
        detector: 수요 탐지기
        clusterer: 수요 클러스터러
        priority_calculator: 우선순위 계산기

    Example:
        >>> analyzer = DemandAnalyzer()
        >>> report = analyzer.analyze_posts(posts, top_n=10)
        >>> print(analyzer.to_markdown(report))
    """

    def __init__(
        self,
        detector: DemandDetector | None = None,
        clusterer: DemandClusterer | None = None,
        priority_calculator: PriorityCalculator | None = None,
    ) -> None:
        """
        수요 분석기 초기화.

        Args:
            detector: 수요 탐지기 (None이면 기본 탐지기 사용)
            clusterer: 수요 클러스터러 (None이면 기본 클러스터러 사용)
            priority_calculator: 우선순위 계산기 (None이면 기본 계산기 사용)
        """
        self.detector = detector or DemandDetector()
        self.clusterer = clusterer or DemandClusterer()
        self.priority_calculator = priority_calculator or PriorityCalculator()

    def _determine_business_potential(
        self,
        priority: PriorityScore,
    ) -> str:
        """
        비즈니스 잠재력 등급 결정.

        Args:
            priority: 우선순위 점수

        Returns:
            잠재력 등급 (high/medium/low)
        """
        total = priority.total_score
        if total >= 60:
            return "high"
        elif total >= 40:
            return "medium"
        else:
            return "low"

    def _generate_recommendations(
        self,
        prioritized: list[PrioritizedDemand],
        by_category: dict[DemandCategory, int],
    ) -> list[str]:
        """
        권장 사항 생성.

        분석 결과를 바탕으로 비즈니스 권장 사항을 생성한다.

        Args:
            prioritized: 우선순위화된 수요 목록
            by_category: 카테고리별 수요 수

        Returns:
            권장 사항 목록
        """
        recommendations: list[str] = []

        if not prioritized:
            return ["No demands detected. Consider expanding the analysis scope."]

        # High potential demands
        high_potential = [p for p in prioritized if p.business_potential == "high"]
        if high_potential:
            recommendations.append(
                f"Focus on {len(high_potential)} high-potential opportunities "
                f"identified in this analysis."
            )

        # Payment intent
        wtp_count = by_category.get(DemandCategory.WILLINGNESS_TO_PAY, 0)
        if wtp_count > 0:
            recommendations.append(
                f"Found {wtp_count} expressions of willingness to pay. "
                "These represent immediate monetization opportunities."
            )

        # Pain points
        pain_count = by_category.get(DemandCategory.PAIN_POINT, 0)
        if pain_count > 0:
            recommendations.append(
                f"Identified {pain_count} pain points. "
                "Addressing these could lead to product differentiation."
            )

        # Alternative seeking
        alt_count = by_category.get(DemandCategory.ALTERNATIVE_SEEKING, 0)
        if alt_count > 0:
            recommendations.append(
                f"Detected {alt_count} users seeking alternatives. "
                "Market disruption opportunity exists."
            )

        # Top opportunity detail
        if prioritized:
            top = prioritized[0]
            recommendations.append(
                f"Top priority: '{top.cluster.representative[:50]}...' "
                f"(score: {top.priority.total_score:.1f})"
            )

        return recommendations

    def prioritize_clusters(
        self,
        clusters: list[DemandCluster],
    ) -> list[PrioritizedDemand]:
        """
        클러스터 우선순위 정렬.

        모든 클러스터에 우선순위 점수를 부여하고 정렬한다.

        Args:
            clusters: 수요 클러스터 목록

        Returns:
            우선순위화된 수요 목록

        Example:
            >>> prioritized = analyzer.prioritize_clusters(clusters)
            >>> for p in prioritized[:5]:
            ...     print(f"Rank {p.rank}: {p.priority.total_score:.1f}")
        """
        if not clusters:
            return []

        # Calculate priority for each cluster
        scored: list[tuple[DemandCluster, PriorityScore]] = []
        for cluster in clusters:
            priority = self.priority_calculator.calculate_priority(cluster)
            scored.append((cluster, priority))

        # Sort by total score (descending)
        scored.sort(key=lambda x: x[1].total_score, reverse=True)

        # Create PrioritizedDemand objects with rank
        result: list[PrioritizedDemand] = []
        for rank, (cluster, priority) in enumerate(scored, start=1):
            potential = self._determine_business_potential(priority)
            result.append(
                PrioritizedDemand(
                    cluster=cluster,
                    priority=priority,
                    rank=rank,
                    business_potential=potential,
                )
            )

        return result

    def analyze_posts(
        self,
        posts: list[Post],
        top_n: int = 10,
    ) -> DemandReport:
        """
        게시물에서 수요 분석 수행.

        전체 파이프라인을 실행하여 수요 리포트를 생성한다.

        Args:
            posts: Reddit Post 객체 목록
            top_n: 상위 기회 수 (기본값: 10)

        Returns:
            수요 분석 리포트

        Example:
            >>> report = analyzer.analyze_posts(posts, top_n=10)
            >>> print(f"Found {report.total_clusters} clusters")
        """
        # Step 1: Detect demands
        all_matches = self.detector.detect_in_posts(posts)

        # Step 2: Cluster demands
        clusters = self.clusterer.cluster_demands(all_matches)

        # Step 3: Prioritize clusters
        prioritized = self.prioritize_clusters(clusters)

        # Step 4: Calculate category stats
        by_category: dict[DemandCategory, int] = {}
        for match in all_matches:
            cat = match.category
            by_category[cat] = by_category.get(cat, 0) + 1

        # Step 5: Generate recommendations
        recommendations = self._generate_recommendations(prioritized, by_category)

        # Build report
        return DemandReport(
            generated_at=datetime.now(UTC),
            total_demands=len(all_matches),
            total_clusters=len(clusters),
            top_opportunities=prioritized[:top_n],
            by_category=by_category,
            recommendations=recommendations,
        )

    def analyze_texts(
        self,
        texts: list[str],
        top_n: int = 10,
    ) -> DemandReport:
        """
        텍스트 목록에서 수요 분석 수행.

        Post 객체 없이 텍스트만으로 분석할 때 사용한다.

        Args:
            texts: 분석할 텍스트 목록
            top_n: 상위 기회 수 (기본값: 10)

        Returns:
            수요 분석 리포트

        Example:
            >>> texts = ["I wish there was...", "Looking for..."]
            >>> report = analyzer.analyze_texts(texts)
        """
        # Detect demands from all texts
        all_matches: list[DemandMatch] = []
        for text in texts:
            matches = self.detector.detect(text)
            all_matches.extend(matches)

        # Cluster demands
        clusters = self.clusterer.cluster_demands(all_matches)

        # Prioritize clusters
        prioritized = self.prioritize_clusters(clusters)

        # Calculate category stats
        by_category: dict[DemandCategory, int] = {}
        for match in all_matches:
            cat = match.category
            by_category[cat] = by_category.get(cat, 0) + 1

        # Generate recommendations
        recommendations = self._generate_recommendations(prioritized, by_category)

        return DemandReport(
            generated_at=datetime.now(UTC),
            total_demands=len(all_matches),
            total_clusters=len(clusters),
            top_opportunities=prioritized[:top_n],
            by_category=by_category,
            recommendations=recommendations,
        )

    def to_markdown(self, report: DemandReport) -> str:
        """
        리포트를 마크다운 형식으로 변환.

        Args:
            report: 수요 분석 리포트

        Returns:
            마크다운 형식 문자열

        Example:
            >>> md = analyzer.to_markdown(report)
            >>> print(md)
        """
        lines: list[str] = []

        # Header
        lines.append("# Demand Analysis Report")
        lines.append("")
        lines.append(
            f"Generated: {report.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}"
        )
        lines.append("")

        # Summary
        lines.append("## Summary")
        lines.append("")
        lines.append(f"- **Total Demands Detected**: {report.total_demands}")
        lines.append(f"- **Total Clusters**: {report.total_clusters}")
        lines.append(
            f"- **Top Opportunities**: {len(report.top_opportunities)}"
        )
        lines.append("")

        # Category breakdown
        lines.append("## Category Breakdown")
        lines.append("")
        lines.append("| Category | Count |")
        lines.append("|----------|-------|")
        for category, count in sorted(
            report.by_category.items(), key=lambda x: x[1], reverse=True
        ):
            lines.append(f"| {category.value.replace('_', ' ').title()} | {count} |")
        lines.append("")

        # Top opportunities
        lines.append("## Top Opportunities")
        lines.append("")

        for opp in report.top_opportunities[:10]:
            lines.append(
                f"### {opp.rank}. {opp.cluster.representative[:60]}"
                + ("..." if len(opp.cluster.representative) > 60 else "")
            )
            lines.append("")
            lines.append(f"- **Score**: {opp.priority.total_score:.1f}/100")
            lines.append(f"- **Potential**: {opp.business_potential.upper()}")
            lines.append(f"- **Frequency**: {opp.cluster.frequency}")
            if opp.cluster.keywords:
                lines.append(f"- **Keywords**: {', '.join(opp.cluster.keywords[:5])}")

            # Score breakdown
            lines.append("- **Score Breakdown**:")
            lines.append(
                f"  - Frequency: {opp.priority.frequency_score:.1f}"
            )
            lines.append(
                f"  - Payment Intent: {opp.priority.payment_intent_score:.1f}"
            )
            lines.append(
                f"  - Urgency: {opp.priority.urgency_score:.1f}"
            )
            lines.append(
                f"  - Recency: {opp.priority.recency_score:.1f}"
            )
            lines.append("")

        # Recommendations
        if report.recommendations:
            lines.append("## Recommendations")
            lines.append("")
            for rec in report.recommendations:
                lines.append(f"- {rec}")
            lines.append("")

        return "\n".join(lines)

    def to_dict(self, report: DemandReport) -> dict:
        """
        리포트를 딕셔너리로 변환.

        JSON 직렬화에 적합한 형태로 변환한다.

        Args:
            report: 수요 분석 리포트

        Returns:
            딕셔너리 형태 리포트

        Example:
            >>> d = analyzer.to_dict(report)
            >>> import json
            >>> print(json.dumps(d, indent=2))
        """
        return {
            "generated_at": report.generated_at.isoformat(),
            "total_demands": report.total_demands,
            "total_clusters": report.total_clusters,
            "by_category": {
                cat.value: count for cat, count in report.by_category.items()
            },
            "top_opportunities": [
                {
                    "rank": opp.rank,
                    "representative": opp.cluster.representative,
                    "frequency": opp.cluster.frequency,
                    "keywords": opp.cluster.keywords,
                    "business_potential": opp.business_potential,
                    "priority": {
                        "total_score": opp.priority.total_score,
                        "frequency_score": opp.priority.frequency_score,
                        "payment_intent_score": opp.priority.payment_intent_score,
                        "urgency_score": opp.priority.urgency_score,
                        "recency_score": opp.priority.recency_score,
                        "breakdown": opp.priority.breakdown,
                    },
                }
                for opp in report.top_opportunities
            ],
            "recommendations": report.recommendations,
        }

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"DemandAnalyzer(detector={self.detector!r}, "
            f"clusterer={self.clusterer!r})"
        )
