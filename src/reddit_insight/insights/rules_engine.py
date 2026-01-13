"""
Insight generation rules engine.

수요 분석과 경쟁 분석 결과를 결합하여 비즈니스 인사이트를 생성하는 규칙 엔진.
규칙 기반으로 조건-결론 패턴을 적용하여 자동으로 인사이트를 생성한다.

Example:
    >>> from reddit_insight.insights.rules_engine import RulesEngine
    >>> engine = RulesEngine()
    >>> engine.load_default_rules()
    >>> insights = engine.generate_insights(context)
    >>> for insight in insights:
    ...     print(f"{insight.title}: {insight.confidence:.0%}")
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from reddit_insight.analysis.competitive import (
        AlternativeComparison,
        Complaint,
        CompetitiveReport,
    )
    from reddit_insight.analysis.demand_analyzer import (
        DemandReport,
        PrioritizedDemand,
    )
    from reddit_insight.analysis.rising import RisingScore, TrendReport
    from reddit_insight.analysis.sentiment import EntitySentiment


# =============================================================================
# INSIGHT TYPES AND DATA STRUCTURES
# =============================================================================


class InsightType(Enum):
    """
    인사이트 유형 열거형.

    비즈니스 인사이트를 5가지 주요 유형으로 분류한다.

    Attributes:
        MARKET_GAP: 시장 공백 (수요 있으나 공급 부족)
        IMPROVEMENT_OPPORTUNITY: 개선 기회 (불만 많은 기존 제품)
        EMERGING_TREND: 떠오르는 트렌드 (급상승 키워드)
        COMPETITIVE_WEAKNESS: 경쟁사 약점
        UNMET_NEED: 미충족 수요
    """

    MARKET_GAP = "market_gap"
    IMPROVEMENT_OPPORTUNITY = "improvement_opportunity"
    EMERGING_TREND = "emerging_trend"
    COMPETITIVE_WEAKNESS = "competitive_weakness"
    UNMET_NEED = "unmet_need"

    @property
    def description(self) -> str:
        """Get human-readable description for the insight type."""
        descriptions = {
            InsightType.MARKET_GAP: "Market gap with unmet demand",
            InsightType.IMPROVEMENT_OPPORTUNITY: "Product improvement opportunity",
            InsightType.EMERGING_TREND: "Emerging market trend",
            InsightType.COMPETITIVE_WEAKNESS: "Competitor weakness",
            InsightType.UNMET_NEED: "Unmet customer need",
        }
        return descriptions.get(self, "Unknown insight type")


@dataclass
class InsightEvidence:
    """
    인사이트 근거 데이터.

    인사이트를 뒷받침하는 근거를 저장한다.

    Attributes:
        source_type: 근거 출처 유형 ("demand", "complaint", "sentiment", "trend")
        source_id: 근거 식별자
        summary: 근거 요약
        weight: 근거 가중치 (0-1)

    Example:
        >>> evidence = InsightEvidence(
        ...     source_type="demand",
        ...     source_id="cluster_001",
        ...     summary="High frequency demand for offline mode",
        ...     weight=0.8
        ... )
    """

    source_type: str
    source_id: str
    summary: str
    weight: float = 1.0

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"InsightEvidence({self.source_type}: '{self.summary[:30]}...')"

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "source_type": self.source_type,
            "source_id": self.source_id,
            "summary": self.summary,
            "weight": self.weight,
        }


@dataclass
class Insight:
    """
    비즈니스 인사이트.

    분석 결과에서 도출된 비즈니스 인사이트를 나타낸다.

    Attributes:
        insight_id: 인사이트 고유 식별자
        insight_type: 인사이트 유형
        title: 인사이트 제목
        description: 상세 설명
        evidence: 근거 데이터 목록
        confidence: 신뢰도 (0-1)
        priority: 우선순위 (0-100)
        related_entities: 관련 엔티티 목록
        related_demands: 관련 수요 목록
        created_at: 생성 시간

    Example:
        >>> insight = Insight(
        ...     insight_id="insight_001",
        ...     insight_type=InsightType.MARKET_GAP,
        ...     title="Market gap in offline note-taking",
        ...     description="High demand for offline mode but no solution",
        ...     evidence=[evidence1, evidence2],
        ...     confidence=0.85,
        ...     priority=75.0,
        ...     related_entities=["Notion", "Evernote"],
        ...     related_demands=["offline mode", "sync"]
        ... )
    """

    insight_id: str
    insight_type: InsightType
    title: str
    description: str
    evidence: list[InsightEvidence]
    confidence: float
    priority: float
    related_entities: list[str] = field(default_factory=list)
    related_demands: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"Insight('{self.title[:30]}...', "
            f"type={self.insight_type.value}, "
            f"confidence={self.confidence:.0%})"
        )

    @property
    def evidence_summary(self) -> str:
        """Get a summary of all evidence."""
        if not self.evidence:
            return "No supporting evidence"
        return "; ".join(e.summary for e in self.evidence[:3])

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "insight_id": self.insight_id,
            "insight_type": self.insight_type.value,
            "title": self.title,
            "description": self.description,
            "evidence": [e.to_dict() for e in self.evidence],
            "confidence": self.confidence,
            "priority": self.priority,
            "related_entities": self.related_entities,
            "related_demands": self.related_demands,
            "created_at": self.created_at.isoformat(),
        }


# =============================================================================
# ANALYSIS CONTEXT
# =============================================================================


@dataclass
class AnalysisContext:
    """
    분석 컨텍스트.

    인사이트 생성에 필요한 모든 분석 결과를 통합한 컨텍스트.

    Attributes:
        demands: 우선순위화된 수요 목록
        complaints: 불만 목록
        entity_sentiments: 엔티티별 감성 분석 결과
        rising_keywords: 급상승 키워드 목록
        alternatives: 대안 비교 목록

    Example:
        >>> context = AnalysisContext(
        ...     demands=prioritized_demands,
        ...     complaints=complaints,
        ...     entity_sentiments={"Slack": sentiment},
        ...     rising_keywords=rising_scores,
        ...     alternatives=comparisons
        ... )
    """

    demands: list["PrioritizedDemand"] = field(default_factory=list)
    complaints: list["Complaint"] = field(default_factory=list)
    entity_sentiments: dict[str, "EntitySentiment"] = field(default_factory=dict)
    rising_keywords: list["RisingScore"] = field(default_factory=list)
    alternatives: list["AlternativeComparison"] = field(default_factory=list)

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"AnalysisContext(demands={len(self.demands)}, "
            f"complaints={len(self.complaints)}, "
            f"entities={len(self.entity_sentiments)}, "
            f"rising={len(self.rising_keywords)})"
        )

    @property
    def has_demand_data(self) -> bool:
        """Check if demand data is available."""
        return len(self.demands) > 0

    @property
    def has_competitive_data(self) -> bool:
        """Check if competitive data is available."""
        return len(self.complaints) > 0 or len(self.entity_sentiments) > 0

    @property
    def has_trend_data(self) -> bool:
        """Check if trend data is available."""
        return len(self.rising_keywords) > 0

    def get_high_priority_demands(
        self, min_score: float = 50.0
    ) -> list["PrioritizedDemand"]:
        """Get demands with priority score above threshold."""
        return [d for d in self.demands if d.priority.total_score >= min_score]

    def get_severe_complaints(self, min_severity: float = 0.7) -> list["Complaint"]:
        """Get complaints with severity above threshold."""
        return [c for c in self.complaints if c.severity >= min_severity]

    def get_negative_entities(self) -> list[str]:
        """Get entities with negative sentiment."""
        negative = []
        for name, sentiment in self.entity_sentiments.items():
            if sentiment.sentiment.compound < -0.3:
                negative.append(name)
        return negative

    def get_top_rising_keywords(self, top_n: int = 5) -> list["RisingScore"]:
        """Get top rising keywords by score."""
        sorted_rising = sorted(
            self.rising_keywords, key=lambda r: r.score, reverse=True
        )
        return sorted_rising[:top_n]


# =============================================================================
# INSIGHT RULES
# =============================================================================


@dataclass
class InsightRule:
    """
    인사이트 생성 규칙.

    조건-결론 패턴으로 인사이트를 자동 생성하는 규칙.

    Attributes:
        rule_id: 규칙 고유 식별자
        name: 규칙 이름
        insight_type: 생성되는 인사이트 유형
        condition: 조건 함수 (AnalysisContext -> bool)
        generate: 인사이트 생성 함수 (AnalysisContext -> Insight)
        priority: 규칙 우선순위 (높을수록 먼저 평가)

    Example:
        >>> rule = InsightRule(
        ...     rule_id="market_gap_001",
        ...     name="High demand with low supply",
        ...     insight_type=InsightType.MARKET_GAP,
        ...     condition=lambda ctx: len(ctx.demands) > 0,
        ...     generate=lambda ctx: generate_market_gap_insight(ctx),
        ...     priority=10
        ... )
    """

    rule_id: str
    name: str
    insight_type: InsightType
    condition: Callable[[AnalysisContext], bool]
    generate: Callable[[AnalysisContext], Insight | None]
    priority: int = 0

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"InsightRule('{self.rule_id}', "
            f"name='{self.name}', "
            f"type={self.insight_type.value})"
        )


# =============================================================================
# DEFAULT RULE IMPLEMENTATIONS
# =============================================================================


def _generate_id() -> str:
    """Generate a unique insight ID."""
    return f"insight_{uuid.uuid4().hex[:12]}"


def _market_gap_condition(context: AnalysisContext) -> bool:
    """
    Market gap rule condition.

    True if there are high-priority demands with limited entity mentions.
    """
    high_demands = context.get_high_priority_demands(min_score=60.0)
    if not high_demands:
        return False

    # Check if there are few related entities (low supply)
    total_entities = len(context.entity_sentiments)
    return total_entities < 3 and len(high_demands) >= 2


def _market_gap_generate(context: AnalysisContext) -> Insight | None:
    """
    Generate market gap insight.

    Identifies markets with demand but insufficient supply.
    """
    high_demands = context.get_high_priority_demands(min_score=60.0)
    if not high_demands:
        return None

    top_demand = high_demands[0]

    # Build evidence
    evidence = [
        InsightEvidence(
            source_type="demand",
            source_id=top_demand.cluster.cluster_id,
            summary=f"High demand: '{top_demand.cluster.representative[:50]}'",
            weight=0.9,
        )
    ]

    # Add more demand evidence
    for demand in high_demands[1:3]:
        evidence.append(
            InsightEvidence(
                source_type="demand",
                source_id=demand.cluster.cluster_id,
                summary=f"Related demand: '{demand.cluster.representative[:40]}'",
                weight=0.7,
            )
        )

    return Insight(
        insight_id=_generate_id(),
        insight_type=InsightType.MARKET_GAP,
        title=f"Market gap in '{top_demand.cluster.keywords[0] if top_demand.cluster.keywords else 'this area'}'",
        description=(
            f"High demand detected ({len(high_demands)} clusters) but limited "
            f"existing solutions. Top demand: '{top_demand.cluster.representative[:60]}'. "
            f"This represents a potential market opportunity."
        ),
        evidence=evidence,
        confidence=min(top_demand.priority.total_score / 100, 0.95),
        priority=top_demand.priority.total_score,
        related_entities=list(context.entity_sentiments.keys())[:5],
        related_demands=[d.cluster.representative[:40] for d in high_demands[:5]],
    )


def _improvement_opportunity_condition(context: AnalysisContext) -> bool:
    """
    Improvement opportunity rule condition.

    True if there are severe complaints and alternative seeking.
    """
    severe_complaints = context.get_severe_complaints(min_severity=0.6)
    has_alternatives = len(context.alternatives) > 0

    return len(severe_complaints) >= 2 or (len(severe_complaints) >= 1 and has_alternatives)


def _improvement_opportunity_generate(context: AnalysisContext) -> Insight | None:
    """
    Generate improvement opportunity insight.

    Identifies products with high complaints that could be improved.
    """
    severe_complaints = context.get_severe_complaints(min_severity=0.6)
    if not severe_complaints:
        return None

    top_complaint = severe_complaints[0]

    # Build evidence
    evidence = [
        InsightEvidence(
            source_type="complaint",
            source_id=f"complaint_{top_complaint.entity.normalized_name}",
            summary=f"Complaint: {top_complaint.complaint_type.value} - '{top_complaint.text[:40]}'",
            weight=0.85,
        )
    ]

    # Add alternative evidence if available
    for alt in context.alternatives[:2]:
        if alt.source_entity.normalized_name == top_complaint.entity.normalized_name:
            evidence.append(
                InsightEvidence(
                    source_type="alternative",
                    source_id=f"alt_{alt.source_entity.normalized_name}",
                    summary=f"Users seeking alternatives from {alt.source_entity.name}",
                    weight=0.7,
                )
            )

    # Calculate confidence based on complaint severity and count
    avg_severity = sum(c.severity for c in severe_complaints) / len(severe_complaints)
    confidence = min(avg_severity * 0.9, 0.9)

    return Insight(
        insight_id=_generate_id(),
        insight_type=InsightType.IMPROVEMENT_OPPORTUNITY,
        title=f"Improvement opportunity for {top_complaint.entity.name}",
        description=(
            f"{top_complaint.entity.name} users show high dissatisfaction "
            f"({len(severe_complaints)} severe complaints). "
            f"Main issue: {top_complaint.complaint_type.value}. "
            f"Building a better alternative could capture this market."
        ),
        evidence=evidence,
        confidence=confidence,
        priority=avg_severity * 100,
        related_entities=[top_complaint.entity.name],
        related_demands=[c.text[:40] for c in severe_complaints[:5]],
    )


def _emerging_trend_condition(context: AnalysisContext) -> bool:
    """
    Emerging trend rule condition.

    True if there are rising keywords with high scores.
    """
    top_rising = context.get_top_rising_keywords(top_n=3)
    return any(r.score >= 50.0 for r in top_rising)


def _emerging_trend_generate(context: AnalysisContext) -> Insight | None:
    """
    Generate emerging trend insight.

    Identifies rapidly rising topics that represent opportunities.
    """
    top_rising = context.get_top_rising_keywords(top_n=5)
    high_rising = [r for r in top_rising if r.score >= 40.0]

    if not high_rising:
        return None

    top = high_rising[0]

    # Build evidence
    evidence = [
        InsightEvidence(
            source_type="trend",
            source_id=f"rising_{top.keyword}",
            summary=f"'{top.keyword}' rising score: {top.score:.1f}, growth: {top.growth_rate:.0%}",
            weight=0.9,
        )
    ]

    for rising in high_rising[1:3]:
        evidence.append(
            InsightEvidence(
                source_type="trend",
                source_id=f"rising_{rising.keyword}",
                summary=f"Related trend: '{rising.keyword}' (score: {rising.score:.1f})",
                weight=0.7,
            )
        )

    # Check if trend matches any demands
    demand_keywords = set()
    for demand in context.demands[:10]:
        demand_keywords.update(demand.cluster.keywords)

    matching_demands = [r.keyword for r in high_rising if r.keyword in demand_keywords]

    description = (
        f"'{top.keyword}' is rapidly emerging as a trending topic "
        f"(score: {top.score:.1f}, growth: {top.growth_rate:+.0%}). "
    )

    if matching_demands:
        description += f"This trend matches existing demand signals for: {', '.join(matching_demands[:3])}."
    else:
        description += "This could represent an early business opportunity."

    return Insight(
        insight_id=_generate_id(),
        insight_type=InsightType.EMERGING_TREND,
        title=f"Emerging trend: '{top.keyword}'",
        description=description,
        evidence=evidence,
        confidence=min(top.score / 100, 0.9),
        priority=top.score,
        related_entities=[],
        related_demands=[r.keyword for r in high_rising[:5]],
    )


def _competitive_weakness_condition(context: AnalysisContext) -> bool:
    """
    Competitive weakness rule condition.

    True if there are entities with negative sentiment and alternatives.
    """
    negative_entities = context.get_negative_entities()
    return len(negative_entities) > 0 and len(context.alternatives) > 0


def _competitive_weakness_generate(context: AnalysisContext) -> Insight | None:
    """
    Generate competitive weakness insight.

    Identifies competitors with weaknesses that can be exploited.
    """
    negative_entities = context.get_negative_entities()
    if not negative_entities:
        return None

    # Find the most negative entity
    most_negative = None
    lowest_score = 0.0

    for name in negative_entities:
        sentiment = context.entity_sentiments.get(name)
        if sentiment and sentiment.sentiment.compound < lowest_score:
            lowest_score = sentiment.sentiment.compound
            most_negative = name

    if not most_negative:
        return None

    sentiment = context.entity_sentiments[most_negative]

    # Build evidence
    evidence = [
        InsightEvidence(
            source_type="sentiment",
            source_id=f"sentiment_{most_negative}",
            summary=f"{most_negative} has negative sentiment (compound: {sentiment.sentiment.compound:.2f})",
            weight=0.85,
        )
    ]

    # Find related complaints
    entity_complaints = [
        c for c in context.complaints
        if c.entity.normalized_name == most_negative.lower()
    ]
    if entity_complaints:
        evidence.append(
            InsightEvidence(
                source_type="complaint",
                source_id=f"complaints_{most_negative}",
                summary=f"{len(entity_complaints)} complaints about {most_negative}",
                weight=0.75,
            )
        )

    # Find alternatives being sought
    entity_alternatives = [
        a for a in context.alternatives
        if a.source_entity.normalized_name == most_negative.lower()
    ]
    if entity_alternatives:
        targets = [a.target_entity.name for a in entity_alternatives if a.target_entity]
        evidence.append(
            InsightEvidence(
                source_type="alternative",
                source_id=f"alternatives_{most_negative}",
                summary=f"Users seeking alternatives: {', '.join(targets[:3])}",
                weight=0.7,
            )
        )

    return Insight(
        insight_id=_generate_id(),
        insight_type=InsightType.COMPETITIVE_WEAKNESS,
        title=f"Competitive weakness: {most_negative}",
        description=(
            f"{most_negative} shows significant user dissatisfaction "
            f"(sentiment: {sentiment.sentiment.compound:.2f}). "
            f"{'Users are actively seeking alternatives. ' if entity_alternatives else ''}"
            f"This represents an opportunity to capture market share."
        ),
        evidence=evidence,
        confidence=min(abs(lowest_score), 0.9),
        priority=abs(lowest_score) * 100,
        related_entities=[most_negative] + negative_entities[:4],
        related_demands=[],
    )


def _unmet_need_condition(context: AnalysisContext) -> bool:
    """
    Unmet need rule condition.

    True if there are demands with willingness to pay signals.
    """
    from reddit_insight.analysis.demand_patterns import DemandCategory

    for demand in context.demands[:10]:
        for match in demand.cluster.matches:
            if match.category == DemandCategory.WILLINGNESS_TO_PAY:
                return True
    return False


def _unmet_need_generate(context: AnalysisContext) -> Insight | None:
    """
    Generate unmet need insight.

    Identifies needs where users have expressed willingness to pay.
    """
    from reddit_insight.analysis.demand_patterns import DemandCategory

    # Find demands with WTP signals
    wtp_demands = []
    for demand in context.demands[:20]:
        wtp_count = sum(
            1 for m in demand.cluster.matches
            if m.category == DemandCategory.WILLINGNESS_TO_PAY
        )
        if wtp_count > 0:
            wtp_demands.append((demand, wtp_count))

    if not wtp_demands:
        return None

    # Sort by WTP count
    wtp_demands.sort(key=lambda x: x[1], reverse=True)
    top_demand, wtp_count = wtp_demands[0]

    # Build evidence
    evidence = [
        InsightEvidence(
            source_type="demand",
            source_id=top_demand.cluster.cluster_id,
            summary=f"'{top_demand.cluster.representative[:50]}' with {wtp_count} WTP signals",
            weight=0.95,
        )
    ]

    for demand, count in wtp_demands[1:3]:
        evidence.append(
            InsightEvidence(
                source_type="demand",
                source_id=demand.cluster.cluster_id,
                summary=f"Related WTP demand: '{demand.cluster.representative[:40]}'",
                weight=0.75,
            )
        )

    return Insight(
        insight_id=_generate_id(),
        insight_type=InsightType.UNMET_NEED,
        title=f"Monetizable unmet need: {top_demand.cluster.keywords[0] if top_demand.cluster.keywords else 'solution'}",
        description=(
            f"Users have expressed willingness to pay for: "
            f"'{top_demand.cluster.representative[:60]}'. "
            f"Found {len(wtp_demands)} demand clusters with payment intent signals. "
            f"This represents a validated monetization opportunity."
        ),
        evidence=evidence,
        confidence=0.9,
        priority=top_demand.priority.total_score + 10,  # Bonus for WTP
        related_entities=[],
        related_demands=[d[0].cluster.representative[:40] for d in wtp_demands[:5]],
    )


# =============================================================================
# DEFAULT RULES
# =============================================================================


DEFAULT_RULES: list[InsightRule] = [
    InsightRule(
        rule_id="market_gap_001",
        name="Market Gap - High Demand Low Supply",
        insight_type=InsightType.MARKET_GAP,
        condition=_market_gap_condition,
        generate=_market_gap_generate,
        priority=10,
    ),
    InsightRule(
        rule_id="improvement_001",
        name="Improvement Opportunity - High Complaints",
        insight_type=InsightType.IMPROVEMENT_OPPORTUNITY,
        condition=_improvement_opportunity_condition,
        generate=_improvement_opportunity_generate,
        priority=9,
    ),
    InsightRule(
        rule_id="trend_001",
        name="Emerging Trend - Rising Keywords",
        insight_type=InsightType.EMERGING_TREND,
        condition=_emerging_trend_condition,
        generate=_emerging_trend_generate,
        priority=8,
    ),
    InsightRule(
        rule_id="competitive_001",
        name="Competitive Weakness - Negative Sentiment",
        insight_type=InsightType.COMPETITIVE_WEAKNESS,
        condition=_competitive_weakness_condition,
        generate=_competitive_weakness_generate,
        priority=7,
    ),
    InsightRule(
        rule_id="unmet_need_001",
        name="Unmet Need - Willingness to Pay",
        insight_type=InsightType.UNMET_NEED,
        condition=_unmet_need_condition,
        generate=_unmet_need_generate,
        priority=10,  # High priority due to monetization potential
    ),
]


# =============================================================================
# RULES ENGINE
# =============================================================================


class RulesEngine:
    """
    인사이트 생성 규칙 엔진.

    등록된 규칙을 평가하여 자동으로 인사이트를 생성한다.

    Attributes:
        _rules: 등록된 규칙 목록

    Example:
        >>> engine = RulesEngine()
        >>> engine.load_default_rules()
        >>> context = engine.build_context(
        ...     demand_report=demand_report,
        ...     competitive_report=competitive_report
        ... )
        >>> insights = engine.generate_insights(context)
        >>> for insight in insights:
        ...     print(f"{insight.title}: {insight.confidence:.0%}")
    """

    def __init__(self, rules: list[InsightRule] | None = None) -> None:
        """
        규칙 엔진 초기화.

        Args:
            rules: 초기 규칙 목록 (None이면 빈 목록으로 시작)
        """
        self._rules: list[InsightRule] = rules or []

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"RulesEngine(rules={len(self._rules)})"

    @property
    def rules(self) -> list[InsightRule]:
        """Get registered rules."""
        return list(self._rules)

    def add_rule(self, rule: InsightRule) -> None:
        """
        규칙 추가.

        Args:
            rule: 추가할 규칙
        """
        self._rules.append(rule)

    def remove_rule(self, rule_id: str) -> bool:
        """
        규칙 제거.

        Args:
            rule_id: 제거할 규칙 ID

        Returns:
            제거 성공 여부
        """
        original_len = len(self._rules)
        self._rules = [r for r in self._rules if r.rule_id != rule_id]
        return len(self._rules) < original_len

    def get_rules(self) -> list[InsightRule]:
        """
        등록된 규칙 목록 반환.

        Returns:
            규칙 목록
        """
        return list(self._rules)

    def get_rule(self, rule_id: str) -> InsightRule | None:
        """
        규칙 ID로 규칙 조회.

        Args:
            rule_id: 규칙 ID

        Returns:
            규칙 또는 None
        """
        for rule in self._rules:
            if rule.rule_id == rule_id:
                return rule
        return None

    def load_default_rules(self) -> None:
        """
        기본 규칙 로드.

        기존 규칙을 유지하면서 기본 규칙을 추가한다.
        """
        existing_ids = {r.rule_id for r in self._rules}
        for rule in DEFAULT_RULES:
            if rule.rule_id not in existing_ids:
                self._rules.append(rule)

    def clear_rules(self) -> None:
        """모든 규칙 제거."""
        self._rules = []

    def evaluate_rule(
        self,
        rule: InsightRule,
        context: AnalysisContext,
    ) -> Insight | None:
        """
        단일 규칙 평가.

        Args:
            rule: 평가할 규칙
            context: 분석 컨텍스트

        Returns:
            생성된 인사이트 또는 None
        """
        try:
            if rule.condition(context):
                return rule.generate(context)
        except Exception:
            # Log error but continue with other rules
            pass
        return None

    def generate_insights(
        self,
        context: AnalysisContext,
        max_insights: int | None = None,
    ) -> list[Insight]:
        """
        인사이트 생성.

        모든 규칙을 평가하여 인사이트를 생성한다.

        Args:
            context: 분석 컨텍스트
            max_insights: 최대 인사이트 수 (None이면 제한 없음)

        Returns:
            생성된 인사이트 목록 (우선순위 순)
        """
        insights: list[Insight] = []

        # Sort rules by priority (descending)
        sorted_rules = sorted(self._rules, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            insight = self.evaluate_rule(rule, context)
            if insight is not None:
                insights.append(insight)

            # Check max limit
            if max_insights and len(insights) >= max_insights:
                break

        # Sort by priority (descending)
        insights.sort(key=lambda i: i.priority, reverse=True)

        return insights

    def build_context(
        self,
        demand_report: "DemandReport | None" = None,
        competitive_report: "CompetitiveReport | None" = None,
        trend_report: "TrendReport | None" = None,
    ) -> AnalysisContext:
        """
        분석 결과로부터 컨텍스트 구축.

        Args:
            demand_report: 수요 분석 리포트
            competitive_report: 경쟁 분석 리포트
            trend_report: 트렌드 분석 리포트

        Returns:
            통합된 분석 컨텍스트
        """
        context = AnalysisContext()

        # Extract from demand report
        if demand_report:
            context.demands = list(demand_report.top_opportunities)

        # Extract from competitive report
        if competitive_report:
            context.complaints = list(competitive_report.top_complaints)

            # Build entity sentiments from insights
            for insight in competitive_report.insights:
                context.entity_sentiments[insight.entity.name] = insight

            context.alternatives = []
            # Note: alternatives need to be extracted separately if needed

        # Extract from trend report
        if trend_report:
            context.rising_keywords = list(trend_report.rising_keywords)

        return context

    def to_markdown(self, insights: list[Insight]) -> str:
        """
        인사이트 목록을 마크다운으로 변환.

        Args:
            insights: 인사이트 목록

        Returns:
            마크다운 형식 문자열
        """
        lines: list[str] = []

        lines.append("# Business Insights Report")
        lines.append("")
        lines.append(f"**Generated**: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}")
        lines.append(f"**Total Insights**: {len(insights)}")
        lines.append("")

        if not insights:
            lines.append("_No insights generated._")
            return "\n".join(lines)

        # Group by type
        by_type: dict[InsightType, list[Insight]] = {}
        for insight in insights:
            if insight.insight_type not in by_type:
                by_type[insight.insight_type] = []
            by_type[insight.insight_type].append(insight)

        # Output by type
        for insight_type in InsightType:
            type_insights = by_type.get(insight_type, [])
            if not type_insights:
                continue

            lines.append(f"## {insight_type.description}")
            lines.append("")

            for insight in type_insights:
                lines.append(f"### {insight.title}")
                lines.append("")
                lines.append(f"**Confidence**: {insight.confidence:.0%} | **Priority**: {insight.priority:.1f}")
                lines.append("")
                lines.append(insight.description)
                lines.append("")

                if insight.evidence:
                    lines.append("**Evidence**:")
                    for ev in insight.evidence[:3]:
                        lines.append(f"- {ev.summary}")
                    lines.append("")

                if insight.related_entities:
                    lines.append(f"**Related Entities**: {', '.join(insight.related_entities[:5])}")
                    lines.append("")

        return "\n".join(lines)

    def to_dict(self, insights: list[Insight]) -> dict:
        """
        인사이트 목록을 딕셔너리로 변환.

        Args:
            insights: 인사이트 목록

        Returns:
            딕셔너리 형태
        """
        return {
            "generated_at": datetime.now(UTC).isoformat(),
            "total_insights": len(insights),
            "insights": [i.to_dict() for i in insights],
            "by_type": {
                t.value: len([i for i in insights if i.insight_type == t])
                for t in InsightType
            },
        }
