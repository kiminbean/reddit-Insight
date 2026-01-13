"""
Reddit Insight Business Insights Module.

수요 분석과 경쟁 분석 결과를 결합하여 비즈니스 인사이트를 생성하는 모듈.
규칙 기반 엔진으로 자동 인사이트 생성을 지원한다.

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
"""

from reddit_insight.insights.rules_engine import (
    AnalysisContext,
    DEFAULT_RULES,
    Insight,
    InsightEvidence,
    InsightRule,
    InsightType,
    RulesEngine,
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
]
