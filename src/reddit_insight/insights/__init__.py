"""
Reddit Insight Business Insights Module.

수요 분석과 경쟁 분석 결과를 결합하여 비즈니스 인사이트를 생성하는 모듈.
규칙 기반 엔진으로 자동 인사이트 생성을 지원하고, 비즈니스 기회 스코어링 및
실행 가능성 분석을 제공한다.

Example:
    >>> from reddit_insight.insights import RulesEngine, InsightType
    >>> engine = RulesEngine()
    >>> engine.load_default_rules()
    >>> context = engine.build_context(
    ...     demand_report=demand_report,
    ...     competitive_report=competitive_report
    ... )
    >>> insights = engine.generate_insights(context)
    >>> for insight in insights:
    ...     print(f"{insight.title}: {insight.confidence:.0%}")

    >>> # Score and rank opportunities
    >>> from reddit_insight.insights import OpportunityScorer
    >>> scorer = OpportunityScorer()
    >>> opportunities = scorer.rank_opportunities(insights, context)
    >>> for opp in opportunities[:5]:
    ...     print(f"#{opp.rank}: {opp.score.grade} - {opp.insight.title}")

    >>> # Analyze feasibility and generate recommendations
    >>> from reddit_insight.insights import FeasibilityAnalyzer, InsightReportGenerator
    >>> analyzer = FeasibilityAnalyzer()
    >>> recommendations = analyzer.generate_recommendations(opportunities, context)
    >>> generator = InsightReportGenerator()
    >>> report = generator.generate(insights, opportunities, recommendations)
    >>> print(generator.to_markdown(report))
"""

from reddit_insight.insights.feasibility import (
    ActionableRecommendation,
    FactorAssessment,
    FeasibilityAnalyzer,
    FeasibilityConfig,
    FeasibilityFactor,
    FeasibilityScore,
    InsightReport,
    InsightReportGenerator,
)
from reddit_insight.insights.rules_engine import (
    AnalysisContext,
    DEFAULT_RULES,
    Insight,
    InsightEvidence,
    InsightRule,
    InsightType,
    RulesEngine,
)
from reddit_insight.insights.scoring import (
    BusinessScore,
    DimensionScore,
    OpportunityScorer,
    ScoreDimension,
    ScoredOpportunity,
    ScoringConfig,
)

__all__ = [
    # Insight Types
    "InsightType",
    # Data Structures
    "Insight",
    "InsightEvidence",
    # Rules
    "InsightRule",
    "AnalysisContext",
    "DEFAULT_RULES",
    # Engine
    "RulesEngine",
    # Scoring
    "ScoreDimension",
    "DimensionScore",
    "BusinessScore",
    "ScoringConfig",
    "OpportunityScorer",
    "ScoredOpportunity",
    # Feasibility
    "FeasibilityFactor",
    "FactorAssessment",
    "FeasibilityScore",
    "FeasibilityConfig",
    "FeasibilityAnalyzer",
    "ActionableRecommendation",
    # Report
    "InsightReport",
    "InsightReportGenerator",
]
