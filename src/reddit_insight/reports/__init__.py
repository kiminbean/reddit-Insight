"""
Reddit Insight Reports Module.

마크다운 리포트 템플릿 시스템과 리포트 생성기를 제공한다.
Jinja2 기반 템플릿과 마크다운 유틸리티를 통해 분석 결과를 문서화한다.

Example:
    >>> from reddit_insight.reports import TemplateRegistry, ReportType
    >>> registry = TemplateRegistry()
    >>> registry.load_defaults()
    >>> template = registry.get("trend_report")
    >>> markdown = template.render(
    ...     title="Weekly Trend Analysis",
    ...     summary="Key trends identified...",
    ...     top_keywords=[...],
    ...     rising_keywords=[...]
    ... )
    >>> print(markdown)

    >>> # Using report generator
    >>> from reddit_insight.reports import ReportGenerator, ReportConfig
    >>> from reddit_insight.reports import ReportDataCollector, TrendReportData
    >>> generator = ReportGenerator()
    >>> data = ReportDataCollector(
    ...     trend_report=TrendReportData(title="Weekly Trend")
    ... )
    >>> full_report = generator.generate_full_report(data)
    >>> generator.save_report(full_report, "output/report.md")

    >>> # Using helpers
    >>> from reddit_insight.reports import format_table, format_percentage
    >>> print(format_table(["Name", "Score"], [["A", "90"]]))
    | Name | Score |
    |------|-------|
    | A | 90 |
"""

from reddit_insight.reports.generator import (
    # Config
    ReportConfig,
    # Data Classes
    TrendReportData,
    ReportDataCollector,
    # Generator
    ReportGenerator,
)
from reddit_insight.reports.templates import (
    # Enums
    ReportType,
    # Data Classes
    ReportTemplate,
    # Registry
    TemplateRegistry,
    # Default Templates
    DEFAULT_TEMPLATES,
    TREND_REPORT_TEMPLATE,
    DEMAND_REPORT_TEMPLATE,
    COMPETITIVE_REPORT_TEMPLATE,
    INSIGHT_REPORT_TEMPLATE,
    FULL_REPORT_TEMPLATE,
    # Markdown Helpers
    format_table,
    format_list,
    format_badge,
    # Data Formatters
    format_percentage,
    format_score,
    format_date,
    format_trend,
    # Text Charts
    text_bar,
    text_sparkline,
)

__all__ = [
    # Enums
    "ReportType",
    # Data Classes
    "ReportTemplate",
    "ReportConfig",
    "TrendReportData",
    "ReportDataCollector",
    # Registry
    "TemplateRegistry",
    # Generator
    "ReportGenerator",
    # Default Templates
    "DEFAULT_TEMPLATES",
    "TREND_REPORT_TEMPLATE",
    "DEMAND_REPORT_TEMPLATE",
    "COMPETITIVE_REPORT_TEMPLATE",
    "INSIGHT_REPORT_TEMPLATE",
    "FULL_REPORT_TEMPLATE",
    # Markdown Helpers
    "format_table",
    "format_list",
    "format_badge",
    # Data Formatters
    "format_percentage",
    "format_score",
    "format_date",
    "format_trend",
    # Text Charts
    "text_bar",
    "text_sparkline",
]
