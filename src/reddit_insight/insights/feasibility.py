"""
Feasibility analysis system.

비즈니스 기회의 실행 가능성을 평가하여 최종 추천을 생성하는 시스템.
5가지 요소(기술적 복잡도, 리소스 요구량, 시장 진입 장벽, 가치 실현 시간, 경쟁 리스크)로 평가한다.

Example:
    >>> from reddit_insight.insights.feasibility import FeasibilityAnalyzer
    >>> analyzer = FeasibilityAnalyzer()
    >>> score = analyzer.analyze(insight, business_score, context)
    >>> print(f"Risk Level: {score.risk_level}, Total: {score.total_score:.1f}")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from reddit_insight.insights.rules_engine import AnalysisContext, Insight
    from reddit_insight.insights.scoring import BusinessScore, ScoredOpportunity


# =============================================================================
# FEASIBILITY FACTORS
# =============================================================================


class FeasibilityFactor(Enum):
    """
    실행 가능성 평가 요소 열거형.

    비즈니스 기회의 실행 가능성을 5가지 요소로 평가한다.

    Attributes:
        TECHNICAL_COMPLEXITY: 기술적 복잡도 (높은 점수 = 낮은 복잡도)
        RESOURCE_REQUIREMENT: 리소스 요구량 (높은 점수 = 적은 리소스)
        MARKET_BARRIER: 시장 진입 장벽 (높은 점수 = 낮은 장벽)
        TIME_TO_VALUE: 가치 실현 시간 (높은 점수 = 빠른 가치 실현)
        COMPETITION_RISK: 경쟁 리스크 (높은 점수 = 낮은 리스크)
    """

    TECHNICAL_COMPLEXITY = "technical_complexity"
    RESOURCE_REQUIREMENT = "resource_requirement"
    MARKET_BARRIER = "market_barrier"
    TIME_TO_VALUE = "time_to_value"
    COMPETITION_RISK = "competition_risk"

    @property
    def description(self) -> str:
        """Get human-readable description for the factor."""
        descriptions = {
            FeasibilityFactor.TECHNICAL_COMPLEXITY: "Technical complexity (higher = easier)",
            FeasibilityFactor.RESOURCE_REQUIREMENT: "Resource requirement (higher = less needed)",
            FeasibilityFactor.MARKET_BARRIER: "Market entry barrier (higher = lower barrier)",
            FeasibilityFactor.TIME_TO_VALUE: "Time to value (higher = faster realization)",
            FeasibilityFactor.COMPETITION_RISK: "Competition risk (higher = lower risk)",
        }
        return descriptions.get(self, "Unknown factor")


# =============================================================================
# FEASIBILITY DATA STRUCTURES
# =============================================================================


@dataclass
class FactorAssessment:
    """
    요소별 평가 결과.

    개별 실행 가능성 요소의 점수와 근거를 저장한다.

    Attributes:
        factor: 평가 요소
        score: 점수 (0-100, 높을수록 유리)
        assessment: 평가 설명
        evidence: 근거 목록

    Example:
        >>> assessment = FactorAssessment(
        ...     factor=FeasibilityFactor.TECHNICAL_COMPLEXITY,
        ...     score=75.0,
        ...     assessment="Low complexity due to existing solutions",
        ...     evidence=["Similar product exists", "Standard tech stack"]
        ... )
    """

    factor: FeasibilityFactor
    score: float
    assessment: str
    evidence: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate score is within bounds."""
        self.score = max(0.0, min(100.0, self.score))

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"FactorAssessment({self.factor.value}: "
            f"{self.score:.1f}, '{self.assessment[:30]}...')"
        )

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "factor": self.factor.value,
            "score": self.score,
            "assessment": self.assessment,
            "evidence": self.evidence,
        }


@dataclass
class FeasibilityScore:
    """
    실행 가능성 종합 점수.

    모든 요소의 점수를 종합한 실행 가능성 평가 결과.

    Attributes:
        total_score: 종합 점수 (0-100)
        factors: 요소별 평가 결과 목록
        risk_level: 리스크 수준 (LOW/MEDIUM/HIGH)
        recommendation: 추천 문구

    Example:
        >>> score = FeasibilityScore(
        ...     total_score=72.5,
        ...     factors=[assessment1, assessment2],
        ...     risk_level="LOW",
        ...     recommendation="Highly feasible - proceed with implementation"
        ... )
    """

    total_score: float
    factors: list[FactorAssessment]
    risk_level: str
    recommendation: str

    def __post_init__(self) -> None:
        """Validate total score is within bounds."""
        self.total_score = max(0.0, min(100.0, self.total_score))

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"FeasibilityScore(total={self.total_score:.1f}, "
            f"risk='{self.risk_level}', factors={len(self.factors)})"
        )

    def get_factor_assessment(
        self, factor: FeasibilityFactor
    ) -> FactorAssessment | None:
        """Get assessment for a specific factor."""
        for f in self.factors:
            if f.factor == factor:
                return f
        return None

    @property
    def strengths(self) -> list[FactorAssessment]:
        """Get factors with scores >= 70."""
        return [f for f in self.factors if f.score >= 70.0]

    @property
    def weaknesses(self) -> list[FactorAssessment]:
        """Get factors with scores < 40."""
        return [f for f in self.factors if f.score < 40.0]

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "total_score": self.total_score,
            "risk_level": self.risk_level,
            "recommendation": self.recommendation,
            "factors": [f.to_dict() for f in self.factors],
        }


@dataclass
class FeasibilityConfig:
    """
    실행 가능성 평가 설정.

    요소별 가중치를 설정한다.

    Attributes:
        technical_weight: 기술적 복잡도 가중치 (default: 0.25)
        resource_weight: 리소스 요구량 가중치 (default: 0.20)
        barrier_weight: 시장 진입 장벽 가중치 (default: 0.20)
        time_weight: 가치 실현 시간 가중치 (default: 0.20)
        competition_weight: 경쟁 리스크 가중치 (default: 0.15)

    Example:
        >>> config = FeasibilityConfig(
        ...     technical_weight=0.30,
        ...     resource_weight=0.25
        ... )
    """

    technical_weight: float = 0.25
    resource_weight: float = 0.20
    barrier_weight: float = 0.20
    time_weight: float = 0.20
    competition_weight: float = 0.15

    def __post_init__(self) -> None:
        """Validate weights sum to approximately 1.0."""
        total = (
            self.technical_weight
            + self.resource_weight
            + self.barrier_weight
            + self.time_weight
            + self.competition_weight
        )
        # Allow small tolerance for floating point
        if abs(total - 1.0) > 0.01:
            # Normalize weights
            self.technical_weight /= total
            self.resource_weight /= total
            self.barrier_weight /= total
            self.time_weight /= total
            self.competition_weight /= total

    def get_weight(self, factor: FeasibilityFactor) -> float:
        """Get weight for a specific factor."""
        weights = {
            FeasibilityFactor.TECHNICAL_COMPLEXITY: self.technical_weight,
            FeasibilityFactor.RESOURCE_REQUIREMENT: self.resource_weight,
            FeasibilityFactor.MARKET_BARRIER: self.barrier_weight,
            FeasibilityFactor.TIME_TO_VALUE: self.time_weight,
            FeasibilityFactor.COMPETITION_RISK: self.competition_weight,
        }
        return weights.get(factor, 0.0)
