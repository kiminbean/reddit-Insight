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


# =============================================================================
# FACTOR EVALUATORS
# =============================================================================


class FactorEvaluator(Protocol):
    """
    요소별 평가기 프로토콜.

    각 실행 가능성 요소의 점수를 계산하는 인터페이스.
    """

    def evaluate(
        self,
        insight: Insight,
        context: AnalysisContext,
    ) -> FactorAssessment:
        """
        요소 평가 수행.

        Args:
            insight: 평가할 인사이트
            context: 분석 컨텍스트

        Returns:
            요소별 평가 결과
        """
        ...


class TechnicalComplexityEvaluator:
    """
    기술적 복잡도 평가기.

    기존 솔루션 유무와 기술 키워드를 기반으로 복잡도를 추정한다.
    높은 점수 = 낮은 복잡도 (더 실현 가능).

    평가 기준:
    - 기존 솔루션 유무: 있으면 검증된 기술 (높은 점수)
    - 기술 키워드: 복잡한 기술 언급 시 낮은 점수
    - 인사이트 유형: 개선 기회는 높은 점수
    """

    # Complex technology keywords that suggest higher complexity
    COMPLEX_KEYWORDS: set[str] = {
        "ai", "ml", "machine learning", "deep learning", "neural network",
        "blockchain", "distributed", "real-time", "scalable", "enterprise",
        "encryption", "security", "compliance", "integration", "legacy",
        "microservices", "kubernetes", "cloud native",
    }

    # Simple technology keywords that suggest lower complexity
    SIMPLE_KEYWORDS: set[str] = {
        "simple", "basic", "straightforward", "standard", "common",
        "web app", "mobile app", "crud", "dashboard", "form",
        "notification", "email", "api", "rest",
    }

    def evaluate(
        self,
        insight: Insight,
        context: AnalysisContext,
    ) -> FactorAssessment:
        """
        기술적 복잡도 평가.

        Args:
            insight: 평가할 인사이트
            context: 분석 컨텍스트

        Returns:
            기술적 복잡도 평가 결과
        """
        score = 60.0  # Base score (moderately feasible)
        evidence: list[str] = []

        # Factor 1: Existing solutions (validated technology)
        if insight.related_entities:
            entity_count = len(insight.related_entities)
            if entity_count >= 3:
                score += 15.0
                evidence.append(f"Multiple existing solutions ({entity_count}) - proven technology")
            elif entity_count >= 1:
                score += 10.0
                evidence.append("Existing solutions available - technology validated")
        else:
            score -= 10.0
            evidence.append("No existing solutions - unproven technology path")

        # Factor 2: Complex technology keywords in demands
        text_to_analyze = " ".join([
            insight.title.lower(),
            insight.description.lower(),
            " ".join(insight.related_demands).lower(),
        ])

        complex_found = [kw for kw in self.COMPLEX_KEYWORDS if kw in text_to_analyze]
        simple_found = [kw for kw in self.SIMPLE_KEYWORDS if kw in text_to_analyze]

        if complex_found:
            score -= len(complex_found) * 5.0
            evidence.append(f"Complex tech indicators: {', '.join(complex_found[:3])}")

        if simple_found:
            score += len(simple_found) * 5.0
            evidence.append(f"Simple tech indicators: {', '.join(simple_found[:3])}")

        # Factor 3: Insight type
        from reddit_insight.insights.rules_engine import InsightType

        if insight.insight_type == InsightType.IMPROVEMENT_OPPORTUNITY:
            score += 10.0
            evidence.append("Improvement on existing product - lower technical risk")
        elif insight.insight_type == InsightType.MARKET_GAP:
            score -= 5.0
            evidence.append("New market - may require novel technical approach")

        # Factor 4: Confidence as a proxy for clarity
        if insight.confidence >= 0.8:
            score += 5.0
            evidence.append("High confidence - clear technical requirements")
        elif insight.confidence < 0.5:
            score -= 5.0
            evidence.append("Low confidence - unclear technical requirements")

        # Clamp score
        score = min(100.0, max(0.0, score))

        assessment = self._generate_assessment(score, complex_found, simple_found)

        return FactorAssessment(
            factor=FeasibilityFactor.TECHNICAL_COMPLEXITY,
            score=score,
            assessment=assessment,
            evidence=evidence,
        )

    def _generate_assessment(
        self,
        score: float,
        complex_kw: list[str],
        simple_kw: list[str],
    ) -> str:
        """Generate human-readable assessment."""
        if score >= 70:
            return "Low technical complexity - straightforward implementation"
        elif score >= 50:
            if complex_kw:
                return f"Moderate complexity due to: {', '.join(complex_kw[:2])}"
            return "Moderate technical complexity - standard development effort"
        else:
            if complex_kw:
                return f"High complexity - requires expertise in: {', '.join(complex_kw[:2])}"
            return "High technical complexity - significant development challenges"


class ResourceRequirementEvaluator:
    """
    리소스 요구량 평가기.

    예상 개발 규모와 팀 규모 요구사항을 추정한다.
    높은 점수 = 적은 리소스 필요 (더 실현 가능).

    평가 기준:
    - 기존 솔루션 수: 많으면 라이브러리/도구 활용 가능
    - 인사이트 우선순위: 높은 우선순위는 더 많은 리소스 필요할 수 있음
    - 증거 데이터 양: 많은 증거는 더 명확한 요구사항
    """

    def evaluate(
        self,
        insight: Insight,
        context: AnalysisContext,
    ) -> FactorAssessment:
        """
        리소스 요구량 평가.

        Args:
            insight: 평가할 인사이트
            context: 분석 컨텍스트

        Returns:
            리소스 요구량 평가 결과
        """
        score = 60.0  # Base score
        evidence: list[str] = []

        # Factor 1: Existing ecosystem (libraries, tools available)
        if insight.related_entities:
            entity_count = len(insight.related_entities)
            if entity_count >= 5:
                score += 20.0
                evidence.append("Rich ecosystem - many tools/libraries available")
            elif entity_count >= 2:
                score += 10.0
                evidence.append("Some ecosystem support available")
        else:
            score -= 10.0
            evidence.append("Limited ecosystem - more custom development needed")

        # Factor 2: Evidence clarity (more evidence = clearer requirements)
        evidence_count = len(insight.evidence)
        if evidence_count >= 5:
            score += 15.0
            evidence.append("Clear requirements from multiple evidence sources")
        elif evidence_count >= 2:
            score += 5.0
            evidence.append("Some requirement clarity from evidence")
        else:
            score -= 10.0
            evidence.append("Unclear requirements - more research needed")

        # Factor 3: Related demands scope
        demand_count = len(insight.related_demands)
        if demand_count >= 5:
            # Many demands might mean larger scope
            score -= 10.0
            evidence.append(f"Broad scope ({demand_count} related demands)")
        elif demand_count <= 2:
            score += 10.0
            evidence.append("Focused scope - limited feature set")

        # Factor 4: Insight type
        from reddit_insight.insights.rules_engine import InsightType

        if insight.insight_type == InsightType.UNMET_NEED:
            score += 5.0
            evidence.append("Clear unmet need - focused resource allocation")
        elif insight.insight_type == InsightType.MARKET_GAP:
            score -= 5.0
            evidence.append("Market gap - may require broader resource investment")

        # Clamp score
        score = min(100.0, max(0.0, score))

        assessment = self._generate_assessment(score, demand_count)

        return FactorAssessment(
            factor=FeasibilityFactor.RESOURCE_REQUIREMENT,
            score=score,
            assessment=assessment,
            evidence=evidence,
        )

    def _generate_assessment(self, score: float, demand_count: int) -> str:
        """Generate human-readable assessment."""
        if score >= 70:
            return "Low resource requirement - small team can execute"
        elif score >= 50:
            return "Moderate resource requirement - standard team size needed"
        else:
            if demand_count >= 5:
                return "High resource requirement - broad scope requires larger team"
            return "High resource requirement - significant investment needed"


class MarketBarrierEvaluator:
    """
    시장 진입 장벽 평가기.

    경쟁 강도와 규제/인증 요구사항을 기반으로 평가한다.
    높은 점수 = 낮은 진입 장벽 (더 실현 가능).

    평가 기준:
    - 경쟁사 수: 적으면 진입 쉬움
    - 경쟁사 감성: 부정적이면 시장 진입 기회
    - 규제 키워드: 있으면 진입 어려움
    """

    # Regulatory/barrier keywords
    BARRIER_KEYWORDS: set[str] = {
        "compliance", "regulation", "hipaa", "gdpr", "pci", "sox",
        "certification", "license", "patent", "legal", "government",
        "enterprise", "b2b", "contract", "procurement",
    }

    def evaluate(
        self,
        insight: Insight,
        context: AnalysisContext,
    ) -> FactorAssessment:
        """
        시장 진입 장벽 평가.

        Args:
            insight: 평가할 인사이트
            context: 분석 컨텍스트

        Returns:
            시장 진입 장벽 평가 결과
        """
        score = 65.0  # Base score
        evidence: list[str] = []

        # Factor 1: Competition level
        entity_count = len(insight.related_entities)
        if entity_count == 0:
            score += 15.0
            evidence.append("No established competitors - open market")
        elif entity_count <= 2:
            score += 10.0
            evidence.append("Low competition - market opportunity")
        elif entity_count <= 5:
            score -= 5.0
            evidence.append(f"Moderate competition ({entity_count} players)")
        else:
            score -= 15.0
            evidence.append(f"Highly competitive market ({entity_count} players)")

        # Factor 2: Competitor sentiment (negative = opportunity)
        if context.entity_sentiments:
            negative_count = len(context.get_negative_entities())
            if negative_count >= 3:
                score += 15.0
                evidence.append("Multiple dissatisfied competitor users - market disruption opportunity")
            elif negative_count >= 1:
                score += 10.0
                evidence.append("Some competitor dissatisfaction - entry opportunity")

        # Factor 3: Alternative seeking behavior
        if context.alternatives:
            alt_count = len(context.alternatives)
            if alt_count >= 5:
                score += 10.0
                evidence.append("High alternative seeking - users ready to switch")
            elif alt_count >= 2:
                score += 5.0
                evidence.append("Some users seeking alternatives")

        # Factor 4: Regulatory barriers
        text_to_analyze = " ".join([
            insight.title.lower(),
            insight.description.lower(),
            " ".join(insight.related_demands).lower(),
        ])

        barriers_found = [kw for kw in self.BARRIER_KEYWORDS if kw in text_to_analyze]
        if barriers_found:
            score -= len(barriers_found) * 5.0
            evidence.append(f"Potential barriers: {', '.join(barriers_found[:3])}")

        # Clamp score
        score = min(100.0, max(0.0, score))

        assessment = self._generate_assessment(score, entity_count, barriers_found)

        return FactorAssessment(
            factor=FeasibilityFactor.MARKET_BARRIER,
            score=score,
            assessment=assessment,
            evidence=evidence,
        )

    def _generate_assessment(
        self,
        score: float,
        entity_count: int,
        barriers: list[str],
    ) -> str:
        """Generate human-readable assessment."""
        if score >= 70:
            return "Low market barriers - easy market entry"
        elif score >= 50:
            if barriers:
                return f"Moderate barriers due to: {', '.join(barriers[:2])}"
            return "Moderate market barriers - standard go-to-market effort"
        else:
            if entity_count > 5:
                return "High barriers - saturated competitive landscape"
            if barriers:
                return f"High barriers - regulatory challenges: {', '.join(barriers[:2])}"
            return "High market barriers - significant entry challenges"


class TimeToValueEvaluator:
    """
    가치 실현 시간 평가기.

    MVP 출시 예상 시간과 빠른 검증 가능성을 평가한다.
    높은 점수 = 빠른 가치 실현 (더 실현 가능).

    평가 기준:
    - 기존 솔루션 유무: 있으면 빠른 벤치마킹 가능
    - 인사이트 유형: 개선 기회는 빠른 실현
    - WTP 신호: 있으면 빠른 수익화 가능
    """

    def evaluate(
        self,
        insight: Insight,
        context: AnalysisContext,
    ) -> FactorAssessment:
        """
        가치 실현 시간 평가.

        Args:
            insight: 평가할 인사이트
            context: 분석 컨텍스트

        Returns:
            가치 실현 시간 평가 결과
        """
        score = 55.0  # Base score
        evidence: list[str] = []

        # Factor 1: Existing solutions for benchmarking
        if insight.related_entities:
            entity_count = len(insight.related_entities)
            if entity_count >= 2:
                score += 15.0
                evidence.append("Existing solutions enable fast benchmarking/validation")
            elif entity_count >= 1:
                score += 10.0
                evidence.append("Some market reference available")
        else:
            score -= 10.0
            evidence.append("No market reference - longer validation cycle")

        # Factor 2: Insight type affects time to value
        from reddit_insight.insights.rules_engine import InsightType

        if insight.insight_type == InsightType.IMPROVEMENT_OPPORTUNITY:
            score += 15.0
            evidence.append("Improvement opportunity - faster to implement")
        elif insight.insight_type == InsightType.EMERGING_TREND:
            score += 10.0
            evidence.append("Emerging trend - early mover advantage possible")
        elif insight.insight_type == InsightType.UNMET_NEED:
            score += 5.0
            evidence.append("Clear unmet need - focused development")
        elif insight.insight_type == InsightType.MARKET_GAP:
            score -= 5.0
            evidence.append("Market gap - may require longer validation")

        # Factor 3: WTP signals (faster monetization)
        wtp_evidence = [
            e for e in insight.evidence
            if any(kw in e.summary.lower() for kw in ["wtp", "pay", "willingness", "budget"])
        ]
        if wtp_evidence:
            score += 15.0
            evidence.append("WTP signals present - fast path to revenue")

        # Factor 4: High priority insight (urgent need = faster adoption)
        if insight.priority >= 80:
            score += 10.0
            evidence.append("High priority - urgent market need")
        elif insight.priority >= 60:
            score += 5.0
            evidence.append("Moderate priority - good market interest")

        # Factor 5: Severe complaints (users ready to switch)
        if context.complaints:
            severe = context.get_severe_complaints(min_severity=0.7)
            if len(severe) >= 3:
                score += 10.0
                evidence.append("Severe complaints - users ready for alternatives")

        # Clamp score
        score = min(100.0, max(0.0, score))

        assessment = self._generate_assessment(score, bool(wtp_evidence))

        return FactorAssessment(
            factor=FeasibilityFactor.TIME_TO_VALUE,
            score=score,
            assessment=assessment,
            evidence=evidence,
        )

    def _generate_assessment(self, score: float, has_wtp: bool) -> str:
        """Generate human-readable assessment."""
        if score >= 70:
            if has_wtp:
                return "Fast time to value - WTP signals indicate quick monetization"
            return "Fast time to value - rapid market validation possible"
        elif score >= 50:
            return "Moderate time to value - standard development timeline"
        else:
            return "Slow time to value - longer validation and development cycle"


class CompetitionRiskEvaluator:
    """
    경쟁 리스크 평가기.

    대형 플레이어 존재 여부와 방어 가능성을 평가한다.
    높은 점수 = 낮은 리스크 (더 실현 가능).

    평가 기준:
    - 대형 플레이어 존재: 있으면 리스크 높음
    - 경쟁사 만족도: 불만 많으면 방어 가능
    - 니치 마켓: 틈새 시장이면 방어 가능
    """

    # Major tech companies that increase competition risk
    MAJOR_PLAYERS: set[str] = {
        "google", "microsoft", "amazon", "apple", "meta", "facebook",
        "salesforce", "oracle", "sap", "adobe", "ibm", "slack",
        "dropbox", "zoom", "atlassian", "notion", "figma",
    }

    def evaluate(
        self,
        insight: Insight,
        context: AnalysisContext,
    ) -> FactorAssessment:
        """
        경쟁 리스크 평가.

        Args:
            insight: 평가할 인사이트
            context: 분석 컨텍스트

        Returns:
            경쟁 리스크 평가 결과
        """
        score = 65.0  # Base score
        evidence: list[str] = []

        # Factor 1: Major player presence
        related_entities_lower = [e.lower() for e in insight.related_entities]
        major_present = [
            p for p in self.MAJOR_PLAYERS
            if any(p in entity for entity in related_entities_lower)
        ]

        if major_present:
            score -= len(major_present) * 10.0
            evidence.append(f"Major players present: {', '.join(major_present[:3])}")
        else:
            score += 15.0
            evidence.append("No major tech players - lower competitive risk")

        # Factor 2: Competitor dissatisfaction (defensibility through better product)
        if context.entity_sentiments:
            negative_entities = context.get_negative_entities()
            if len(negative_entities) >= 2:
                score += 15.0
                evidence.append("Competitor users dissatisfied - differentiation opportunity")
            elif len(negative_entities) >= 1:
                score += 10.0
                evidence.append("Some competitor dissatisfaction")

        # Factor 3: Niche market indicators
        text_to_analyze = " ".join([
            insight.title.lower(),
            insight.description.lower(),
        ])

        niche_indicators = ["niche", "specific", "specialized", "targeted", "vertical"]
        niche_found = any(ind in text_to_analyze for ind in niche_indicators)
        if niche_found:
            score += 10.0
            evidence.append("Niche market opportunity - easier to defend")

        # Factor 4: Entity count (more competitors = higher risk)
        entity_count = len(insight.related_entities)
        if entity_count == 0:
            score += 10.0
            evidence.append("No direct competitors identified")
        elif entity_count <= 3:
            score += 5.0
            evidence.append("Limited direct competition")
        elif entity_count > 7:
            score -= 15.0
            evidence.append(f"Crowded market ({entity_count} competitors)")

        # Factor 5: Alternative seeking (users willing to switch)
        if context.alternatives and len(context.alternatives) >= 3:
            score += 10.0
            evidence.append("Users actively seeking alternatives - market fluidity")

        # Clamp score
        score = min(100.0, max(0.0, score))

        assessment = self._generate_assessment(score, major_present)

        return FactorAssessment(
            factor=FeasibilityFactor.COMPETITION_RISK,
            score=score,
            assessment=assessment,
            evidence=evidence,
        )

    def _generate_assessment(self, score: float, major_players: list[str]) -> str:
        """Generate human-readable assessment."""
        if score >= 70:
            return "Low competition risk - defensible market position"
        elif score >= 50:
            if major_players:
                return f"Moderate risk - differentiate from: {', '.join(major_players[:2])}"
            return "Moderate competition risk - standard competitive dynamics"
        else:
            if major_players:
                return f"High risk - competing with: {', '.join(major_players[:2])}"
            return "High competition risk - crowded market with strong players"


# =============================================================================
# ACTIONABLE RECOMMENDATION
# =============================================================================


@dataclass
class ActionableRecommendation:
    """
    실행 가능한 추천.

    인사이트, 비즈니스 점수, 실행 가능성을 종합한 최종 추천.

    Attributes:
        insight: 인사이트
        business_score: 비즈니스 점수
        feasibility_score: 실행 가능성 점수
        final_rank: 최종 순위
        action_items: 실행 항목 목록
        next_steps: 다음 단계 목록

    Example:
        >>> recommendation = ActionableRecommendation(
        ...     insight=insight,
        ...     business_score=business_score,
        ...     feasibility_score=feasibility_score,
        ...     final_rank=1,
        ...     action_items=["Build MVP", "User testing"],
        ...     next_steps=["Market research", "Competitor analysis"]
        ... )
    """

    insight: Insight
    business_score: BusinessScore
    feasibility_score: FeasibilityScore
    final_rank: int
    action_items: list[str] = field(default_factory=list)
    next_steps: list[str] = field(default_factory=list)

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"ActionableRecommendation(rank={self.final_rank}, "
            f"business={self.business_score.total_score:.1f}, "
            f"feasibility={self.feasibility_score.total_score:.1f})"
        )

    @property
    def combined_score(self) -> float:
        """Calculate combined score (business * feasibility weight)."""
        # Weight: 60% business value, 40% feasibility
        return (
            self.business_score.total_score * 0.6
            + self.feasibility_score.total_score * 0.4
        )

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "final_rank": self.final_rank,
            "combined_score": self.combined_score,
            "insight": self.insight.to_dict(),
            "business_score": self.business_score.to_dict(),
            "feasibility_score": self.feasibility_score.to_dict(),
            "action_items": self.action_items,
            "next_steps": self.next_steps,
        }


# =============================================================================
# FEASIBILITY ANALYZER
# =============================================================================


class FeasibilityAnalyzer:
    """
    실행 가능성 분석기.

    비즈니스 기회의 실행 가능성을 평가하고 최종 추천을 생성한다.

    Attributes:
        _config: 실행 가능성 설정
        _evaluators: 요소별 평가기 매핑

    Example:
        >>> analyzer = FeasibilityAnalyzer()
        >>> score = analyzer.analyze(insight, business_score, context)
        >>> print(f"Risk: {score.risk_level}, Score: {score.total_score:.1f}")

        >>> # Generate recommendations
        >>> recommendations = analyzer.generate_recommendations(
        ...     opportunities, context, top_n=5
        ... )
        >>> for rec in recommendations:
        ...     print(f"#{rec.final_rank}: {rec.insight.title}")
    """

    def __init__(self, config: FeasibilityConfig | None = None) -> None:
        """
        분석기 초기화.

        Args:
            config: 실행 가능성 설정 (None이면 기본값 사용)
        """
        self._config = config or FeasibilityConfig()
        self._evaluators: dict[FeasibilityFactor, FactorEvaluator] = {
            FeasibilityFactor.TECHNICAL_COMPLEXITY: TechnicalComplexityEvaluator(),
            FeasibilityFactor.RESOURCE_REQUIREMENT: ResourceRequirementEvaluator(),
            FeasibilityFactor.MARKET_BARRIER: MarketBarrierEvaluator(),
            FeasibilityFactor.TIME_TO_VALUE: TimeToValueEvaluator(),
            FeasibilityFactor.COMPETITION_RISK: CompetitionRiskEvaluator(),
        }

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"FeasibilityAnalyzer(factors={len(self._evaluators)})"

    @property
    def config(self) -> FeasibilityConfig:
        """Get feasibility configuration."""
        return self._config

    def analyze(
        self,
        insight: Insight,
        business_score: BusinessScore,
        context: AnalysisContext,
    ) -> FeasibilityScore:
        """
        단일 기회의 실행 가능성 분석.

        모든 요소에 대해 평가를 수행하고 종합 점수를 산출한다.

        Args:
            insight: 평가할 인사이트
            business_score: 비즈니스 점수
            context: 분석 컨텍스트

        Returns:
            실행 가능성 점수
        """
        factor_assessments: list[FactorAssessment] = []

        # Evaluate each factor
        for factor, evaluator in self._evaluators.items():
            assessment = evaluator.evaluate(insight, context)
            factor_assessments.append(assessment)

        # Calculate weighted total score
        total_score = 0.0
        for assessment in factor_assessments:
            weight = self._config.get_weight(assessment.factor)
            total_score += assessment.score * weight

        # Calculate risk level
        risk_level = self._calculate_risk_level(total_score)

        # Generate recommendation
        recommendation = self._generate_recommendation(
            insight, factor_assessments, total_score, risk_level
        )

        return FeasibilityScore(
            total_score=total_score,
            factors=factor_assessments,
            risk_level=risk_level,
            recommendation=recommendation,
        )

    def analyze_opportunities(
        self,
        scored_opportunities: list[ScoredOpportunity],
        context: AnalysisContext,
    ) -> list[tuple[ScoredOpportunity, FeasibilityScore]]:
        """
        여러 기회의 실행 가능성 분석 및 정렬.

        Args:
            scored_opportunities: 스코어링된 기회 목록
            context: 분석 컨텍스트

        Returns:
            (기회, 실행 가능성 점수) 튜플 목록 (combined score 내림차순)
        """
        results: list[tuple[ScoredOpportunity, FeasibilityScore]] = []

        for opportunity in scored_opportunities:
            feasibility = self.analyze(
                opportunity.insight,
                opportunity.score,
                context,
            )
            results.append((opportunity, feasibility))

        # Sort by combined score (business * 0.6 + feasibility * 0.4)
        results.sort(
            key=lambda x: x[0].score.total_score * 0.6 + x[1].total_score * 0.4,
            reverse=True,
        )

        return results

    def generate_recommendations(
        self,
        opportunities: list[ScoredOpportunity],
        context: AnalysisContext,
        top_n: int = 5,
    ) -> list[ActionableRecommendation]:
        """
        상위 N개 실행 가능한 추천 생성.

        비즈니스 점수와 실행 가능성을 종합하여 최종 추천을 생성한다.

        Args:
            opportunities: 스코어링된 기회 목록
            context: 분석 컨텍스트
            top_n: 반환할 최대 추천 수

        Returns:
            실행 가능한 추천 목록
        """
        # Analyze all opportunities
        analyzed = self.analyze_opportunities(opportunities, context)

        recommendations: list[ActionableRecommendation] = []

        for rank, (opportunity, feasibility) in enumerate(analyzed[:top_n], start=1):
            # Generate action items based on insight type
            action_items = self._generate_action_items(
                opportunity.insight, feasibility
            )

            # Generate next steps based on feasibility
            next_steps = self._generate_next_steps(
                opportunity.insight, feasibility
            )

            recommendation = ActionableRecommendation(
                insight=opportunity.insight,
                business_score=opportunity.score,
                feasibility_score=feasibility,
                final_rank=rank,
                action_items=action_items,
                next_steps=next_steps,
            )
            recommendations.append(recommendation)

        return recommendations

    def _calculate_risk_level(self, score: float) -> str:
        """
        리스크 수준 계산.

        Args:
            score: 종합 점수 (0-100)

        Returns:
            리스크 수준 (LOW/MEDIUM/HIGH)
        """
        if score >= 70:
            return "LOW"
        elif score >= 40:
            return "MEDIUM"
        else:
            return "HIGH"

    def _generate_recommendation(
        self,
        insight: Insight,
        factors: list[FactorAssessment],
        total_score: float,
        risk_level: str,
    ) -> str:
        """
        추천 문구 생성.

        Args:
            insight: 인사이트
            factors: 요소별 평가
            total_score: 종합 점수
            risk_level: 리스크 수준

        Returns:
            추천 문구
        """
        # Find strengths and weaknesses
        strengths = [f for f in factors if f.score >= 70]
        weaknesses = [f for f in factors if f.score < 40]

        if risk_level == "LOW":
            base = "Highly feasible - recommend immediate action."
        elif risk_level == "MEDIUM":
            base = "Moderately feasible - proceed with careful planning."
        else:
            base = "High risk - requires significant mitigation efforts."

        # Add strength highlights
        if strengths:
            strength_names = [
                s.factor.value.replace("_", " ").title() for s in strengths[:2]
            ]
            base += f" Strengths: {', '.join(strength_names)}."

        # Add weakness warnings
        if weaknesses:
            weakness_names = [
                w.factor.value.replace("_", " ").title() for w in weaknesses[:2]
            ]
            base += f" Risks: {', '.join(weakness_names)}."

        return base

    def _generate_action_items(
        self,
        insight: Insight,
        feasibility: FeasibilityScore,
    ) -> list[str]:
        """
        실행 항목 생성.

        Args:
            insight: 인사이트
            feasibility: 실행 가능성 점수

        Returns:
            실행 항목 목록
        """
        from reddit_insight.insights.rules_engine import InsightType

        action_items: list[str] = []

        # Base actions by insight type
        if insight.insight_type == InsightType.MARKET_GAP:
            action_items.append("Conduct detailed market research")
            action_items.append("Define MVP feature set")
            action_items.append("Build prototype for user testing")

        elif insight.insight_type == InsightType.IMPROVEMENT_OPPORTUNITY:
            action_items.append("Analyze competitor weaknesses in detail")
            action_items.append("Design improved solution addressing pain points")
            action_items.append("Create comparison landing page")

        elif insight.insight_type == InsightType.EMERGING_TREND:
            action_items.append("Monitor trend velocity and trajectory")
            action_items.append("Identify early adopter communities")
            action_items.append("Build quick MVP to test market")

        elif insight.insight_type == InsightType.COMPETITIVE_WEAKNESS:
            action_items.append("Target dissatisfied competitor users")
            action_items.append("Create migration guides and tools")
            action_items.append("Develop competitive positioning")

        elif insight.insight_type == InsightType.UNMET_NEED:
            action_items.append("Validate willingness to pay")
            action_items.append("Define pricing strategy")
            action_items.append("Build minimum viable product")

        # Add mitigation actions for weaknesses
        for weakness in feasibility.weaknesses[:2]:
            if weakness.factor == FeasibilityFactor.TECHNICAL_COMPLEXITY:
                action_items.append("Consider technical partnerships or outsourcing")
            elif weakness.factor == FeasibilityFactor.RESOURCE_REQUIREMENT:
                action_items.append("Explore phased development approach")
            elif weakness.factor == FeasibilityFactor.MARKET_BARRIER:
                action_items.append("Research regulatory requirements")
            elif weakness.factor == FeasibilityFactor.TIME_TO_VALUE:
                action_items.append("Identify quick wins for early validation")
            elif weakness.factor == FeasibilityFactor.COMPETITION_RISK:
                action_items.append("Develop unique differentiation strategy")

        return action_items[:5]  # Limit to 5 action items

    def _generate_next_steps(
        self,
        insight: Insight,
        feasibility: FeasibilityScore,
    ) -> list[str]:
        """
        다음 단계 생성.

        Args:
            insight: 인사이트
            feasibility: 실행 가능성 점수

        Returns:
            다음 단계 목록
        """
        next_steps: list[str] = []

        # Universal next steps based on risk level
        if feasibility.risk_level == "LOW":
            next_steps.append("Begin development planning")
            next_steps.append("Allocate initial resources")
            next_steps.append("Set project milestones")

        elif feasibility.risk_level == "MEDIUM":
            next_steps.append("Conduct feasibility deep-dive")
            next_steps.append("Identify risk mitigation strategies")
            next_steps.append("Build proof of concept")

        else:  # HIGH
            next_steps.append("Re-evaluate opportunity value")
            next_steps.append("Explore partnership options")
            next_steps.append("Consider pivot or alternative approach")

        # Add specific next steps based on strengths
        for strength in feasibility.strengths[:2]:
            if strength.factor == FeasibilityFactor.TIME_TO_VALUE:
                next_steps.append("Accelerate go-to-market timeline")
            elif strength.factor == FeasibilityFactor.MARKET_BARRIER:
                next_steps.append("Prioritize market entry speed")
            elif strength.factor == FeasibilityFactor.COMPETITION_RISK:
                next_steps.append("Capitalize on competitive advantage")

        # Add validation steps based on confidence
        if insight.confidence < 0.7:
            next_steps.append("Gather additional market validation data")

        return next_steps[:5]  # Limit to 5 next steps

    def to_markdown(
        self,
        recommendations: list[ActionableRecommendation],
    ) -> str:
        """
        추천 목록을 마크다운으로 변환.

        Args:
            recommendations: 추천 목록

        Returns:
            마크다운 형식 문자열
        """
        lines: list[str] = []

        lines.append("# Feasibility Analysis Report")
        lines.append("")
        lines.append(f"**Generated**: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}")
        lines.append(f"**Total Recommendations**: {len(recommendations)}")
        lines.append("")

        if not recommendations:
            lines.append("_No recommendations to display._")
            return "\n".join(lines)

        # Summary table
        lines.append("## Summary")
        lines.append("")
        lines.append("| Rank | Risk | Combined | Business | Feasibility | Title |")
        lines.append("|------|------|----------|----------|-------------|-------|")

        for rec in recommendations:
            title = (
                rec.insight.title[:30] + "..."
                if len(rec.insight.title) > 30
                else rec.insight.title
            )
            lines.append(
                f"| {rec.final_rank} | {rec.feasibility_score.risk_level} | "
                f"{rec.combined_score:.1f} | {rec.business_score.total_score:.1f} | "
                f"{rec.feasibility_score.total_score:.1f} | {title} |"
            )

        lines.append("")

        # Detailed breakdown
        lines.append("## Detailed Recommendations")
        lines.append("")

        for rec in recommendations:
            lines.append(f"### #{rec.final_rank}: {rec.insight.title}")
            lines.append("")
            lines.append(
                f"**Risk**: {rec.feasibility_score.risk_level} | "
                f"**Combined Score**: {rec.combined_score:.1f}"
            )
            lines.append("")
            lines.append(f"**Business Score**: {rec.business_score.total_score:.1f} ({rec.business_score.grade})")
            lines.append(f"**Feasibility Score**: {rec.feasibility_score.total_score:.1f}")
            lines.append("")

            # Feasibility factors
            lines.append("**Feasibility Breakdown**:")
            for factor in rec.feasibility_score.factors:
                factor_name = factor.factor.value.replace("_", " ").title()
                bar = "=" * int(factor.score / 5)
                lines.append(f"- {factor_name}: {factor.score:.1f} [{bar}]")
                lines.append(f"  - {factor.assessment}")
            lines.append("")

            # Action items
            if rec.action_items:
                lines.append("**Action Items**:")
                for item in rec.action_items:
                    lines.append(f"- {item}")
                lines.append("")

            # Next steps
            if rec.next_steps:
                lines.append("**Next Steps**:")
                for step in rec.next_steps:
                    lines.append(f"- {step}")
                lines.append("")

        return "\n".join(lines)


# =============================================================================
# INSIGHT REPORT
# =============================================================================


@dataclass
class InsightReport:
    """
    최종 인사이트 리포트.

    분석 전체 결과를 종합한 최종 리포트.

    Attributes:
        generated_at: 생성 시간
        analysis_summary: 분석 요약
        total_insights: 총 인사이트 수
        total_opportunities: 총 기회 수
        recommendations: 추천 목록
        market_overview: 시장 개요
        key_findings: 핵심 발견 사항

    Example:
        >>> report = InsightReport(
        ...     generated_at=datetime.now(UTC),
        ...     analysis_summary="Market analysis reveals 5 opportunities",
        ...     total_insights=10,
        ...     total_opportunities=5,
        ...     recommendations=[rec1, rec2],
        ...     market_overview="Growing market with high demand",
        ...     key_findings=["Finding 1", "Finding 2"]
        ... )
    """

    generated_at: datetime
    analysis_summary: str
    total_insights: int
    total_opportunities: int
    recommendations: list[ActionableRecommendation]
    market_overview: str
    key_findings: list[str] = field(default_factory=list)

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"InsightReport(insights={self.total_insights}, "
            f"opportunities={self.total_opportunities}, "
            f"recommendations={len(self.recommendations)})"
        )

    @property
    def top_recommendation(self) -> ActionableRecommendation | None:
        """Get the top-ranked recommendation."""
        if self.recommendations:
            return self.recommendations[0]
        return None

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "generated_at": self.generated_at.isoformat(),
            "analysis_summary": self.analysis_summary,
            "total_insights": self.total_insights,
            "total_opportunities": self.total_opportunities,
            "recommendations": [r.to_dict() for r in self.recommendations],
            "market_overview": self.market_overview,
            "key_findings": self.key_findings,
        }


# =============================================================================
# INSIGHT REPORT GENERATOR
# =============================================================================


class InsightReportGenerator:
    """
    인사이트 리포트 생성기.

    분석 결과를 종합하여 최종 리포트를 생성한다.

    Example:
        >>> generator = InsightReportGenerator()
        >>> report = generator.generate(insights, opportunities, recommendations)
        >>> markdown = generator.to_markdown(report)
        >>> print(markdown)
    """

    def generate(
        self,
        insights: list[Insight],
        opportunities: list[ScoredOpportunity],
        recommendations: list[ActionableRecommendation],
    ) -> InsightReport:
        """
        인사이트 리포트 생성.

        Args:
            insights: 인사이트 목록
            opportunities: 스코어링된 기회 목록
            recommendations: 추천 목록

        Returns:
            최종 인사이트 리포트
        """
        # Generate analysis summary
        analysis_summary = self._generate_summary(insights, opportunities, recommendations)

        # Generate market overview
        market_overview = self._generate_market_overview(insights, opportunities)

        # Generate key findings
        key_findings = self._generate_key_findings(insights, opportunities, recommendations)

        return InsightReport(
            generated_at=datetime.now(UTC),
            analysis_summary=analysis_summary,
            total_insights=len(insights),
            total_opportunities=len(opportunities),
            recommendations=recommendations,
            market_overview=market_overview,
            key_findings=key_findings,
        )

    def _generate_summary(
        self,
        insights: list[Insight],
        opportunities: list[ScoredOpportunity],
        recommendations: list[ActionableRecommendation],
    ) -> str:
        """Generate analysis summary."""
        from reddit_insight.insights.rules_engine import InsightType

        # Count by insight type
        type_counts: dict[InsightType, int] = {}
        for insight in insights:
            type_counts[insight.insight_type] = type_counts.get(insight.insight_type, 0) + 1

        # Count by grade
        grade_counts: dict[str, int] = {}
        for opp in opportunities:
            grade_counts[opp.score.grade] = grade_counts.get(opp.score.grade, 0) + 1

        # Build summary
        parts: list[str] = []
        parts.append(f"Analysis identified {len(insights)} insights across {len(type_counts)} categories.")

        if opportunities:
            a_count = grade_counts.get("A", 0)
            b_count = grade_counts.get("B", 0)
            if a_count > 0 or b_count > 0:
                parts.append(f"{a_count + b_count} high-quality opportunities (Grade A/B) found.")

        if recommendations:
            low_risk = sum(1 for r in recommendations if r.feasibility_score.risk_level == "LOW")
            if low_risk > 0:
                parts.append(f"{low_risk} recommendations with low execution risk.")

        return " ".join(parts)

    def _generate_market_overview(
        self,
        insights: list[Insight],
        opportunities: list[ScoredOpportunity],
    ) -> str:
        """Generate market overview."""
        from reddit_insight.insights.rules_engine import InsightType

        # Analyze market signals
        gap_count = sum(1 for i in insights if i.insight_type == InsightType.MARKET_GAP)
        trend_count = sum(1 for i in insights if i.insight_type == InsightType.EMERGING_TREND)
        weakness_count = sum(1 for i in insights if i.insight_type == InsightType.COMPETITIVE_WEAKNESS)

        parts: list[str] = []

        if gap_count > 0:
            parts.append(f"Market analysis reveals {gap_count} unaddressed market gaps.")

        if trend_count > 0:
            parts.append(f"{trend_count} emerging trends identified with growth potential.")

        if weakness_count > 0:
            parts.append(f"{weakness_count} competitor weaknesses present disruption opportunities.")

        # Calculate average opportunity score
        if opportunities:
            avg_score = sum(o.score.total_score for o in opportunities) / len(opportunities)
            if avg_score >= 70:
                parts.append("Overall market conditions are highly favorable.")
            elif avg_score >= 50:
                parts.append("Market conditions present moderate opportunities.")
            else:
                parts.append("Market conditions require careful evaluation.")

        return " ".join(parts) if parts else "Market analysis complete. Review recommendations for details."

    def _generate_key_findings(
        self,
        insights: list[Insight],
        opportunities: list[ScoredOpportunity],
        recommendations: list[ActionableRecommendation],
    ) -> list[str]:
        """Generate key findings."""
        findings: list[str] = []

        # Top opportunity finding
        if recommendations:
            top = recommendations[0]
            findings.append(
                f"Top opportunity: '{top.insight.title}' with combined score of {top.combined_score:.1f}"
            )

        # High confidence insights
        high_confidence = [i for i in insights if i.confidence >= 0.8]
        if high_confidence:
            findings.append(
                f"{len(high_confidence)} insights with high confidence (80%+) identified"
            )

        # Low risk opportunities
        low_risk = [r for r in recommendations if r.feasibility_score.risk_level == "LOW"]
        if low_risk:
            findings.append(
                f"{len(low_risk)} opportunities with low execution risk ready for implementation"
            )

        # Grade A opportunities
        grade_a = [o for o in opportunities if o.score.grade == "A"]
        if grade_a:
            findings.append(
                f"{len(grade_a)} Grade-A business opportunities identified"
            )

        # WTP signals
        wtp_insights = [
            i for i in insights
            if any("wtp" in e.summary.lower() or "pay" in e.summary.lower() for e in i.evidence)
        ]
        if wtp_insights:
            findings.append(
                f"{len(wtp_insights)} opportunities show willingness-to-pay signals"
            )

        return findings[:7]  # Limit to 7 findings

    def to_markdown(self, report: InsightReport) -> str:
        """
        리포트를 마크다운으로 변환.

        Args:
            report: 인사이트 리포트

        Returns:
            마크다운 형식 문자열
        """
        lines: list[str] = []

        lines.append("# Business Insight Report")
        lines.append("")
        lines.append(f"**Generated**: {report.generated_at.strftime('%Y-%m-%d %H:%M UTC')}")
        lines.append("")

        # Executive Summary
        lines.append("## Executive Summary")
        lines.append("")
        lines.append(report.analysis_summary)
        lines.append("")

        # Market Overview
        lines.append("## Market Overview")
        lines.append("")
        lines.append(report.market_overview)
        lines.append("")

        # Key Findings
        if report.key_findings:
            lines.append("## Key Findings")
            lines.append("")
            for i, finding in enumerate(report.key_findings, 1):
                lines.append(f"{i}. {finding}")
            lines.append("")

        # Statistics
        lines.append("## Analysis Statistics")
        lines.append("")
        lines.append(f"- **Total Insights**: {report.total_insights}")
        lines.append(f"- **Scored Opportunities**: {report.total_opportunities}")
        lines.append(f"- **Actionable Recommendations**: {len(report.recommendations)}")
        lines.append("")

        # Top Recommendations Summary
        if report.recommendations:
            lines.append("## Top Recommendations")
            lines.append("")
            lines.append("| Rank | Title | Combined | Risk | Grade |")
            lines.append("|------|-------|----------|------|-------|")

            for rec in report.recommendations[:5]:
                title = (
                    rec.insight.title[:35] + "..."
                    if len(rec.insight.title) > 35
                    else rec.insight.title
                )
                lines.append(
                    f"| {rec.final_rank} | {title} | {rec.combined_score:.1f} | "
                    f"{rec.feasibility_score.risk_level} | {rec.business_score.grade} |"
                )

            lines.append("")

        # Detailed Recommendations
        if report.recommendations:
            lines.append("## Detailed Analysis")
            lines.append("")

            for rec in report.recommendations[:3]:  # Top 3 detailed
                lines.append(f"### #{rec.final_rank}: {rec.insight.title}")
                lines.append("")
                lines.append(f"**Type**: {rec.insight.insight_type.value}")
                lines.append(f"**Combined Score**: {rec.combined_score:.1f}")
                lines.append(f"**Risk Level**: {rec.feasibility_score.risk_level}")
                lines.append("")

                lines.append("**Description**:")
                lines.append(rec.insight.description)
                lines.append("")

                if rec.action_items:
                    lines.append("**Recommended Actions**:")
                    for item in rec.action_items[:3]:
                        lines.append(f"- {item}")
                    lines.append("")

                if rec.next_steps:
                    lines.append("**Next Steps**:")
                    for step in rec.next_steps[:3]:
                        lines.append(f"- {step}")
                    lines.append("")

        # Footer
        lines.append("---")
        lines.append("*Report generated by Reddit Insight Analysis System*")

        return "\n".join(lines)

    def to_dict(self, report: InsightReport) -> dict:
        """
        리포트를 딕셔너리로 변환.

        Args:
            report: 인사이트 리포트

        Returns:
            딕셔너리 형태
        """
        return report.to_dict()
