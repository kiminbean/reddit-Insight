"""
Business opportunity scoring system.

인사이트를 비즈니스 가치 기준으로 점수화하여 우선순위를 결정하는 스코어링 시스템.
5가지 차원(시장 규모, 경쟁 강도, 긴급성, 트렌드, 실현 가능성)으로 평가한다.

Example:
    >>> from reddit_insight.insights.scoring import OpportunityScorer
    >>> scorer = OpportunityScorer()
    >>> score = scorer.score_insight(insight, context)
    >>> print(f"Grade: {score.grade}, Total: {score.total_score:.1f}")
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from reddit_insight.insights.rules_engine import AnalysisContext, Insight


# =============================================================================
# SCORING DATA STRUCTURES
# =============================================================================


class ScoreDimension(Enum):
    """
    스코어링 차원 열거형.

    비즈니스 기회를 평가하는 5가지 핵심 차원.

    Attributes:
        MARKET_SIZE: 시장 규모 (수요 빈도 기반)
        COMPETITION: 경쟁 강도 (낮을수록 좋음)
        URGENCY: 긴급성 (불만 심각도, 대안 탐색 빈도)
        TREND: 트렌드 방향 (상승/하락)
        FEASIBILITY: 실현 가능성 (기술적 복잡도)
    """

    MARKET_SIZE = "market_size"
    COMPETITION = "competition"
    URGENCY = "urgency"
    TREND = "trend"
    FEASIBILITY = "feasibility"

    @property
    def description(self) -> str:
        """Get human-readable description for the dimension."""
        descriptions = {
            ScoreDimension.MARKET_SIZE: "Market size based on demand frequency",
            ScoreDimension.COMPETITION: "Competition intensity (lower is better)",
            ScoreDimension.URGENCY: "Urgency based on pain points and alternatives",
            ScoreDimension.TREND: "Trend direction (rising or falling)",
            ScoreDimension.FEASIBILITY: "Technical feasibility assessment",
        }
        return descriptions.get(self, "Unknown dimension")


@dataclass
class DimensionScore:
    """
    차원별 점수.

    개별 평가 차원의 점수와 근거를 저장한다.

    Attributes:
        dimension: 평가 차원
        score: 점수 (0-100)
        weight: 가중치 (0-1)
        rationale: 점수 산정 근거

    Example:
        >>> dim_score = DimensionScore(
        ...     dimension=ScoreDimension.MARKET_SIZE,
        ...     score=75.0,
        ...     weight=0.25,
        ...     rationale="High demand frequency detected"
        ... )
    """

    dimension: ScoreDimension
    score: float
    weight: float
    rationale: str

    def __post_init__(self) -> None:
        """Validate score is within bounds."""
        self.score = max(0.0, min(100.0, self.score))
        self.weight = max(0.0, min(1.0, self.weight))

    @property
    def weighted_score(self) -> float:
        """Calculate weighted score contribution."""
        return self.score * self.weight

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"DimensionScore({self.dimension.value}: "
            f"{self.score:.1f} x {self.weight:.2f})"
        )


@dataclass
class BusinessScore:
    """
    비즈니스 기회 종합 점수.

    모든 차원의 점수를 종합한 비즈니스 기회 평가 결과.

    Attributes:
        total_score: 종합 점수 (0-100)
        dimensions: 차원별 점수 목록
        grade: 등급 (A/B/C/D/F)
        recommendation: 추천 문구

    Example:
        >>> score = BusinessScore(
        ...     total_score=78.5,
        ...     dimensions=[dim1, dim2, dim3],
        ...     grade="B",
        ...     recommendation="Strong opportunity with moderate competition"
        ... )
    """

    total_score: float
    dimensions: list[DimensionScore]
    grade: str
    recommendation: str

    def __post_init__(self) -> None:
        """Validate total score is within bounds."""
        self.total_score = max(0.0, min(100.0, self.total_score))

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"BusinessScore(total={self.total_score:.1f}, "
            f"grade='{self.grade}', dims={len(self.dimensions)})"
        )

    def get_dimension_score(self, dimension: ScoreDimension) -> DimensionScore | None:
        """Get score for a specific dimension."""
        for dim in self.dimensions:
            if dim.dimension == dimension:
                return dim
        return None

    @property
    def strengths(self) -> list[DimensionScore]:
        """Get dimensions with scores >= 70."""
        return [d for d in self.dimensions if d.score >= 70.0]

    @property
    def weaknesses(self) -> list[DimensionScore]:
        """Get dimensions with scores < 40."""
        return [d for d in self.dimensions if d.score < 40.0]

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "total_score": self.total_score,
            "grade": self.grade,
            "recommendation": self.recommendation,
            "dimensions": [
                {
                    "dimension": d.dimension.value,
                    "score": d.score,
                    "weight": d.weight,
                    "weighted_score": d.weighted_score,
                    "rationale": d.rationale,
                }
                for d in self.dimensions
            ],
        }


@dataclass
class ScoringConfig:
    """
    스코어링 설정.

    차원별 가중치 및 스코어링 옵션을 설정한다.

    Attributes:
        market_size_weight: 시장 규모 가중치 (default: 0.25)
        competition_weight: 경쟁 강도 가중치 (default: 0.20)
        urgency_weight: 긴급성 가중치 (default: 0.25)
        trend_weight: 트렌드 가중치 (default: 0.15)
        feasibility_weight: 실현 가능성 가중치 (default: 0.15)

    Example:
        >>> config = ScoringConfig(
        ...     market_size_weight=0.30,
        ...     competition_weight=0.25
        ... )
    """

    market_size_weight: float = 0.25
    competition_weight: float = 0.20
    urgency_weight: float = 0.25
    trend_weight: float = 0.15
    feasibility_weight: float = 0.15

    def __post_init__(self) -> None:
        """Validate weights sum to approximately 1.0."""
        total = (
            self.market_size_weight
            + self.competition_weight
            + self.urgency_weight
            + self.trend_weight
            + self.feasibility_weight
        )
        # Allow small tolerance for floating point
        if abs(total - 1.0) > 0.01:
            # Normalize weights
            self.market_size_weight /= total
            self.competition_weight /= total
            self.urgency_weight /= total
            self.trend_weight /= total
            self.feasibility_weight /= total

    def get_weight(self, dimension: ScoreDimension) -> float:
        """Get weight for a specific dimension."""
        weights = {
            ScoreDimension.MARKET_SIZE: self.market_size_weight,
            ScoreDimension.COMPETITION: self.competition_weight,
            ScoreDimension.URGENCY: self.urgency_weight,
            ScoreDimension.TREND: self.trend_weight,
            ScoreDimension.FEASIBILITY: self.feasibility_weight,
        }
        return weights.get(dimension, 0.0)


# =============================================================================
# DIMENSION CALCULATORS
# =============================================================================


class DimensionCalculator(Protocol):
    """
    차원별 점수 계산기 프로토콜.

    각 평가 차원의 점수를 계산하는 인터페이스.
    """

    def calculate(
        self,
        insight: Insight,
        context: AnalysisContext,
        weight: float,
    ) -> DimensionScore:
        """
        차원 점수 계산.

        Args:
            insight: 평가할 인사이트
            context: 분석 컨텍스트
            weight: 가중치

        Returns:
            차원별 점수
        """
        ...


class MarketSizeCalculator:
    """
    시장 규모 계산기.

    수요 빈도와 관련 수요 클러스터 수를 기반으로 시장 규모를 추정한다.
    높은 빈도와 많은 관련 수요 = 높은 점수.
    """

    def calculate(
        self,
        insight: Insight,
        context: AnalysisContext,
        weight: float,
    ) -> DimensionScore:
        """
        시장 규모 점수 계산.

        평가 기준:
        - 관련 수요 클러스터 수
        - 수요 우선순위 점수
        - 증거 데이터 수
        """
        score = 50.0  # Base score
        rationale_parts: list[str] = []

        # Factor 1: Related demands count
        related_demands_count = len(insight.related_demands)
        if related_demands_count >= 5:
            score += 25.0
            rationale_parts.append(f"High demand diversity ({related_demands_count} related)")
        elif related_demands_count >= 3:
            score += 15.0
            rationale_parts.append(f"Moderate demand diversity ({related_demands_count} related)")
        elif related_demands_count >= 1:
            score += 5.0
            rationale_parts.append(f"Some related demands ({related_demands_count})")

        # Factor 2: High-priority demands in context
        if context.has_demand_data:
            high_priority = context.get_high_priority_demands(min_score=60.0)
            if len(high_priority) >= 5:
                score += 20.0
                rationale_parts.append("Strong demand signals")
            elif len(high_priority) >= 2:
                score += 10.0
                rationale_parts.append("Moderate demand signals")

        # Factor 3: Evidence weight
        demand_evidence = [e for e in insight.evidence if e.source_type == "demand"]
        if demand_evidence:
            avg_weight = sum(e.weight for e in demand_evidence) / len(demand_evidence)
            score += avg_weight * 10.0
            rationale_parts.append(f"Demand evidence strength: {avg_weight:.1%}")

        # Clamp score
        score = min(100.0, max(0.0, score))

        rationale = "; ".join(rationale_parts) if rationale_parts else "Baseline market size estimate"

        return DimensionScore(
            dimension=ScoreDimension.MARKET_SIZE,
            score=score,
            weight=weight,
            rationale=rationale,
        )


class CompetitionCalculator:
    """
    경쟁 강도 계산기.

    관련 제품/서비스 수와 경쟁사 감성 점수를 기반으로 경쟁 강도를 평가한다.
    낮은 경쟁 = 높은 점수 (역산).
    """

    def calculate(
        self,
        insight: Insight,
        context: AnalysisContext,
        weight: float,
    ) -> DimensionScore:
        """
        경쟁 강도 점수 계산.

        평가 기준:
        - 관련 엔티티(경쟁사) 수
        - 경쟁사 감성 점수 (부정적일수록 기회)
        - 대안 탐색 빈도
        """
        score = 70.0  # Base score (assume moderate opportunity)
        rationale_parts: list[str] = []

        # Factor 1: Related entities count (more = more competition = lower score)
        entity_count = len(insight.related_entities)
        if entity_count == 0:
            score += 20.0
            rationale_parts.append("No direct competitors identified")
        elif entity_count <= 2:
            score += 10.0
            rationale_parts.append(f"Low competition ({entity_count} entities)")
        elif entity_count <= 5:
            score -= 10.0
            rationale_parts.append(f"Moderate competition ({entity_count} entities)")
        else:
            score -= 25.0
            rationale_parts.append(f"High competition ({entity_count} entities)")

        # Factor 2: Competitor sentiment (negative sentiment = opportunity)
        if context.entity_sentiments:
            negative_entities = context.get_negative_entities()
            if len(negative_entities) >= 3:
                score += 15.0
                rationale_parts.append("Multiple competitors with negative sentiment")
            elif len(negative_entities) >= 1:
                score += 10.0
                rationale_parts.append("Some competitors with negative sentiment")

        # Factor 3: Alternatives seeking (more = dissatisfied users = opportunity)
        if context.alternatives:
            if len(context.alternatives) >= 5:
                score += 15.0
                rationale_parts.append("High alternative-seeking activity")
            elif len(context.alternatives) >= 2:
                score += 10.0
                rationale_parts.append("Moderate alternative-seeking activity")

        # Clamp score
        score = min(100.0, max(0.0, score))

        rationale = "; ".join(rationale_parts) if rationale_parts else "Baseline competition assessment"

        return DimensionScore(
            dimension=ScoreDimension.COMPETITION,
            score=score,
            weight=weight,
            rationale=rationale,
        )


class UrgencyCalculator:
    """
    긴급성 계산기.

    불만 심각도, 대안 탐색 빈도, WTP(Willingness to Pay) 신호를 기반으로
    긴급성을 평가한다.
    """

    def calculate(
        self,
        insight: Insight,
        context: AnalysisContext,
        weight: float,
    ) -> DimensionScore:
        """
        긴급성 점수 계산.

        평가 기준:
        - 불만 심각도
        - WTP 신호 존재
        - 인사이트 우선순위
        """
        score = 50.0  # Base score
        rationale_parts: list[str] = []

        # Factor 1: Severe complaints
        if context.complaints:
            severe = context.get_severe_complaints(min_severity=0.7)
            if len(severe) >= 5:
                score += 25.0
                rationale_parts.append(f"High pain points ({len(severe)} severe complaints)")
            elif len(severe) >= 2:
                score += 15.0
                rationale_parts.append(f"Moderate pain points ({len(severe)} severe complaints)")
            elif len(severe) >= 1:
                score += 5.0
                rationale_parts.append("Some severe complaints")

        # Factor 2: Willingness to pay evidence
        wtp_evidence = [
            e for e in insight.evidence
            if "wtp" in e.summary.lower() or "willingness" in e.summary.lower() or "pay" in e.summary.lower()
        ]
        if wtp_evidence:
            score += 20.0
            rationale_parts.append("Willingness to pay signals detected")

        # Factor 3: Insight priority (higher priority = more urgent)
        if insight.priority >= 80:
            score += 15.0
            rationale_parts.append("Very high insight priority")
        elif insight.priority >= 60:
            score += 10.0
            rationale_parts.append("High insight priority")
        elif insight.priority >= 40:
            score += 5.0
            rationale_parts.append("Moderate insight priority")

        # Factor 4: Alternative seeking behavior
        if context.alternatives and len(context.alternatives) >= 3:
            score += 10.0
            rationale_parts.append("Users actively seeking alternatives")

        # Clamp score
        score = min(100.0, max(0.0, score))

        rationale = "; ".join(rationale_parts) if rationale_parts else "Baseline urgency estimate"

        return DimensionScore(
            dimension=ScoreDimension.URGENCY,
            score=score,
            weight=weight,
            rationale=rationale,
        )


class TrendCalculator:
    """
    트렌드 계산기.

    급상승 키워드(Rising Score)와 시계열 변화율을 기반으로 트렌드 방향을 평가한다.
    상승 트렌드 = 높은 점수.
    """

    def calculate(
        self,
        insight: Insight,
        context: AnalysisContext,
        weight: float,
    ) -> DimensionScore:
        """
        트렌드 점수 계산.

        평가 기준:
        - Rising Score 점수
        - 급상승 키워드 매칭
        - 트렌드 관련 증거
        """
        score = 50.0  # Base score (neutral trend)
        rationale_parts: list[str] = []

        # Factor 1: Rising keywords in context
        if context.has_trend_data:
            top_rising = context.get_top_rising_keywords(top_n=5)
            if top_rising:
                max_score = max(r.score for r in top_rising)
                if max_score >= 70:
                    score += 30.0
                    rationale_parts.append(f"Strong rising trend (score: {max_score:.1f})")
                elif max_score >= 50:
                    score += 20.0
                    rationale_parts.append(f"Moderate rising trend (score: {max_score:.1f})")
                elif max_score >= 30:
                    score += 10.0
                    rationale_parts.append(f"Some rising signals (score: {max_score:.1f})")

        # Factor 2: Trend-related evidence
        trend_evidence = [e for e in insight.evidence if e.source_type == "trend"]
        if trend_evidence:
            avg_weight = sum(e.weight for e in trend_evidence) / len(trend_evidence)
            score += avg_weight * 15.0
            rationale_parts.append(f"Trend evidence: {len(trend_evidence)} sources")

        # Factor 3: Insight type (EMERGING_TREND gets bonus)
        from reddit_insight.insights.rules_engine import InsightType

        if insight.insight_type == InsightType.EMERGING_TREND:
            score += 15.0
            rationale_parts.append("Emerging trend insight type")

        # Factor 4: Related demands matching rising keywords
        if context.has_trend_data and insight.related_demands:
            rising_keywords = {r.keyword.lower() for r in context.rising_keywords}
            matching = sum(
                1 for d in insight.related_demands
                if any(kw in d.lower() for kw in rising_keywords)
            )
            if matching >= 2:
                score += 10.0
                rationale_parts.append(f"Demands align with trends ({matching} matches)")

        # Clamp score
        score = min(100.0, max(0.0, score))

        rationale = "; ".join(rationale_parts) if rationale_parts else "Neutral trend assessment"

        return DimensionScore(
            dimension=ScoreDimension.TREND,
            score=score,
            weight=weight,
            rationale=rationale,
        )


class FeasibilityCalculator:
    """
    실현 가능성 계산기.

    기술적 복잡도와 기존 솔루션 유무를 기반으로 실현 가능성을 평가한다.
    기존 솔루션이 있으면 검증된 시장으로 간주하여 점수 상승.
    """

    def calculate(
        self,
        insight: Insight,
        context: AnalysisContext,
        weight: float,
    ) -> DimensionScore:
        """
        실현 가능성 점수 계산.

        평가 기준:
        - 기존 솔루션 존재 (검증된 시장)
        - 인사이트 신뢰도
        - 증거 데이터 품질
        """
        score = 60.0  # Base score (moderately feasible)
        rationale_parts: list[str] = []

        # Factor 1: Existing solutions (validated market)
        if insight.related_entities:
            entity_count = len(insight.related_entities)
            if entity_count >= 3:
                score += 15.0
                rationale_parts.append("Validated market with existing solutions")
            elif entity_count >= 1:
                score += 10.0
                rationale_parts.append("Some existing solutions identified")
        else:
            # No existing solutions - could be harder but also opportunity
            score -= 5.0
            rationale_parts.append("No existing solutions (unvalidated market)")

        # Factor 2: Insight confidence (higher confidence = more reliable)
        if insight.confidence >= 0.8:
            score += 15.0
            rationale_parts.append("High confidence insight")
        elif insight.confidence >= 0.6:
            score += 10.0
            rationale_parts.append("Moderate confidence insight")
        elif insight.confidence < 0.4:
            score -= 10.0
            rationale_parts.append("Low confidence - more validation needed")

        # Factor 3: Evidence quality
        if insight.evidence:
            high_weight_evidence = [e for e in insight.evidence if e.weight >= 0.7]
            if len(high_weight_evidence) >= 3:
                score += 10.0
                rationale_parts.append("Strong supporting evidence")
            elif len(high_weight_evidence) >= 1:
                score += 5.0
                rationale_parts.append("Some supporting evidence")

        # Factor 4: Improvement opportunity type (proven demand)
        from reddit_insight.insights.rules_engine import InsightType

        if insight.insight_type == InsightType.IMPROVEMENT_OPPORTUNITY:
            score += 10.0
            rationale_parts.append("Improvement on existing solution")
        elif insight.insight_type == InsightType.UNMET_NEED:
            score += 5.0
            rationale_parts.append("Clear unmet need identified")

        # Clamp score
        score = min(100.0, max(0.0, score))

        rationale = "; ".join(rationale_parts) if rationale_parts else "Baseline feasibility estimate"

        return DimensionScore(
            dimension=ScoreDimension.FEASIBILITY,
            score=score,
            weight=weight,
            rationale=rationale,
        )


# =============================================================================
# SCORED OPPORTUNITY
# =============================================================================


@dataclass
class ScoredOpportunity:
    """
    스코어링된 비즈니스 기회.

    인사이트와 해당 점수를 함께 저장한다.

    Attributes:
        insight: 인사이트
        score: 비즈니스 점수
        rank: 순위 (1부터 시작)

    Example:
        >>> opportunity = ScoredOpportunity(
        ...     insight=insight,
        ...     score=business_score,
        ...     rank=1
        ... )
    """

    insight: Insight
    score: BusinessScore
    rank: int = 0

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"ScoredOpportunity(rank={self.rank}, "
            f"score={self.score.total_score:.1f}, "
            f"grade='{self.score.grade}')"
        )

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "rank": self.rank,
            "insight": self.insight.to_dict(),
            "score": self.score.to_dict(),
        }


# =============================================================================
# OPPORTUNITY SCORER
# =============================================================================


class OpportunityScorer:
    """
    비즈니스 기회 스코어러.

    인사이트를 비즈니스 가치 기준으로 점수화하여 우선순위를 결정한다.

    Attributes:
        _config: 스코어링 설정
        _calculators: 차원별 계산기 매핑

    Example:
        >>> scorer = OpportunityScorer()
        >>> score = scorer.score_insight(insight, context)
        >>> print(f"Grade: {score.grade}, Total: {score.total_score:.1f}")

        >>> # Score multiple insights
        >>> scored = scorer.score_insights(insights, context)
        >>> for insight, score in scored[:5]:
        ...     print(f"{insight.title}: {score.grade}")
    """

    def __init__(self, config: ScoringConfig | None = None) -> None:
        """
        스코어러 초기화.

        Args:
            config: 스코어링 설정 (None이면 기본값 사용)
        """
        self._config = config or ScoringConfig()
        self._calculators: dict[ScoreDimension, DimensionCalculator] = {
            ScoreDimension.MARKET_SIZE: MarketSizeCalculator(),
            ScoreDimension.COMPETITION: CompetitionCalculator(),
            ScoreDimension.URGENCY: UrgencyCalculator(),
            ScoreDimension.TREND: TrendCalculator(),
            ScoreDimension.FEASIBILITY: FeasibilityCalculator(),
        }

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"OpportunityScorer(dimensions={len(self._calculators)})"

    @property
    def config(self) -> ScoringConfig:
        """Get scoring configuration."""
        return self._config

    def score_insight(
        self,
        insight: Insight,
        context: AnalysisContext,
    ) -> BusinessScore:
        """
        단일 인사이트 스코어링.

        모든 차원에 대해 점수를 계산하고 종합 점수를 산출한다.

        Args:
            insight: 평가할 인사이트
            context: 분석 컨텍스트

        Returns:
            비즈니스 점수
        """
        dimension_scores: list[DimensionScore] = []

        # Calculate each dimension
        for dimension, calculator in self._calculators.items():
            weight = self._config.get_weight(dimension)
            dim_score = calculator.calculate(insight, context, weight)
            dimension_scores.append(dim_score)

        # Calculate total weighted score
        total_score = sum(d.weighted_score for d in dimension_scores)

        # Calculate grade
        grade = self._calculate_grade(total_score)

        # Generate recommendation
        recommendation = self._generate_recommendation(insight, dimension_scores, total_score, grade)

        return BusinessScore(
            total_score=total_score,
            dimensions=dimension_scores,
            grade=grade,
            recommendation=recommendation,
        )

    def score_insights(
        self,
        insights: list[Insight],
        context: AnalysisContext,
    ) -> list[tuple[Insight, BusinessScore]]:
        """
        여러 인사이트 스코어링 및 정렬.

        모든 인사이트를 스코어링하고 점수 내림차순으로 정렬한다.

        Args:
            insights: 평가할 인사이트 목록
            context: 분석 컨텍스트

        Returns:
            (인사이트, 점수) 튜플 목록 (점수 내림차순)
        """
        scored: list[tuple[Insight, BusinessScore]] = []

        for insight in insights:
            score = self.score_insight(insight, context)
            scored.append((insight, score))

        # Sort by total score descending
        scored.sort(key=lambda x: x[1].total_score, reverse=True)

        return scored

    def rank_opportunities(
        self,
        insights: list[Insight],
        context: AnalysisContext,
    ) -> list[ScoredOpportunity]:
        """
        인사이트를 랭킹된 기회 목록으로 변환.

        Args:
            insights: 인사이트 목록
            context: 분석 컨텍스트

        Returns:
            순위가 부여된 ScoredOpportunity 목록
        """
        scored = self.score_insights(insights, context)

        opportunities: list[ScoredOpportunity] = []
        for rank, (insight, score) in enumerate(scored, start=1):
            opportunity = ScoredOpportunity(
                insight=insight,
                score=score,
                rank=rank,
            )
            opportunities.append(opportunity)

        return opportunities

    def _calculate_grade(self, score: float) -> str:
        """
        등급 계산.

        Args:
            score: 종합 점수 (0-100)

        Returns:
            등급 문자열 (A/B/C/D/F)
        """
        if score >= 80:
            return "A"
        elif score >= 60:
            return "B"
        elif score >= 40:
            return "C"
        elif score >= 20:
            return "D"
        else:
            return "F"

    def _generate_recommendation(
        self,
        insight: Insight,
        dimensions: list[DimensionScore],
        total_score: float,
        grade: str,
    ) -> str:
        """
        추천 문구 생성.

        점수와 차원별 분석을 바탕으로 추천 문구를 생성한다.

        Args:
            insight: 인사이트
            dimensions: 차원별 점수
            total_score: 종합 점수
            grade: 등급

        Returns:
            추천 문구
        """
        # Find strengths and weaknesses
        strengths = [d for d in dimensions if d.score >= 70]
        weaknesses = [d for d in dimensions if d.score < 40]

        # Build recommendation based on grade
        if grade == "A":
            base = "Excellent opportunity - high priority for immediate action."
        elif grade == "B":
            base = "Strong opportunity - worth pursuing with proper planning."
        elif grade == "C":
            base = "Moderate opportunity - requires further validation."
        elif grade == "D":
            base = "Weak opportunity - significant challenges identified."
        else:
            base = "Poor opportunity - not recommended at this time."

        # Add strength highlights
        if strengths:
            strength_names = [s.dimension.value.replace("_", " ").title() for s in strengths[:2]]
            base += f" Strengths: {', '.join(strength_names)}."

        # Add weakness warnings
        if weaknesses:
            weakness_names = [w.dimension.value.replace("_", " ").title() for w in weaknesses[:2]]
            base += f" Concerns: {', '.join(weakness_names)}."

        return base

    def to_markdown(self, opportunities: list[ScoredOpportunity]) -> str:
        """
        기회 목록을 마크다운으로 변환.

        Args:
            opportunities: 스코어링된 기회 목록

        Returns:
            마크다운 형식 문자열
        """
        from datetime import UTC, datetime

        lines: list[str] = []

        lines.append("# Business Opportunity Rankings")
        lines.append("")
        lines.append(f"**Generated**: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}")
        lines.append(f"**Total Opportunities**: {len(opportunities)}")
        lines.append("")

        if not opportunities:
            lines.append("_No opportunities to rank._")
            return "\n".join(lines)

        # Summary table
        lines.append("## Summary")
        lines.append("")
        lines.append("| Rank | Grade | Score | Title |")
        lines.append("|------|-------|-------|-------|")

        for opp in opportunities[:10]:
            title = opp.insight.title[:40] + "..." if len(opp.insight.title) > 40 else opp.insight.title
            lines.append(
                f"| {opp.rank} | {opp.score.grade} | {opp.score.total_score:.1f} | {title} |"
            )

        lines.append("")

        # Detailed breakdown for top 5
        lines.append("## Top Opportunities Detail")
        lines.append("")

        for opp in opportunities[:5]:
            lines.append(f"### #{opp.rank}: {opp.insight.title}")
            lines.append("")
            lines.append(f"**Grade**: {opp.score.grade} | **Score**: {opp.score.total_score:.1f}")
            lines.append("")
            lines.append(f"**Type**: {opp.insight.insight_type.value}")
            lines.append("")
            lines.append(f"**Recommendation**: {opp.score.recommendation}")
            lines.append("")

            # Dimension breakdown
            lines.append("**Dimension Scores**:")
            lines.append("")
            for dim in opp.score.dimensions:
                dim_name = dim.dimension.value.replace("_", " ").title()
                bar = "=" * int(dim.score / 5)  # Visual bar
                lines.append(f"- {dim_name}: {dim.score:.1f} [{bar}]")
                lines.append(f"  - {dim.rationale}")
            lines.append("")

        return "\n".join(lines)

    def to_dict(self, opportunities: list[ScoredOpportunity]) -> dict:
        """
        기회 목록을 딕셔너리로 변환.

        Args:
            opportunities: 스코어링된 기회 목록

        Returns:
            딕셔너리 형태
        """
        from datetime import UTC, datetime

        return {
            "generated_at": datetime.now(UTC).isoformat(),
            "total_opportunities": len(opportunities),
            "opportunities": [opp.to_dict() for opp in opportunities],
            "grade_distribution": {
                grade: len([o for o in opportunities if o.score.grade == grade])
                for grade in ["A", "B", "C", "D", "F"]
            },
        }
