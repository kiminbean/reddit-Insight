"""
Reddit Insight Reports Module.

마크다운 리포트 템플릿 시스템과 리포트 생성기를 제공한다.
Jinja2 기반 템플릿과 마크다운 유틸리티를 통해 분석 결과를 문서화한다.
PDF 및 Excel 내보내기 기능도 제공한다.

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

    >>> # Using PDF/Excel generators
    >>> from reddit_insight.reports import PDFGenerator, ExcelGenerator
    >>> pdf_gen = PDFGenerator()
    >>> pdf_bytes = pdf_gen.generate(report_data)
    >>> excel_gen = ExcelGenerator()
    >>> excel_bytes = excel_gen.generate(report_data)

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
    ReportDataCollector,
    # Generator
    ReportGenerator,
    # Data Classes
    TrendReportData,
)

# PDF and Excel generators (optional dependencies)
try:
    from reddit_insight.reports.pdf_generator import (
        PDFGenerator,
        generate_pdf_from_report,
    )
except (ImportError, OSError):
    PDFGenerator = None  # type: ignore[misc, assignment]
    generate_pdf_from_report = None  # type: ignore[misc, assignment]

try:
    from reddit_insight.reports.excel_generator import (
        ExcelGenerator,
        generate_excel_from_report,
    )
except ImportError:
    ExcelGenerator = None  # type: ignore[misc, assignment]
    generate_excel_from_report = None  # type: ignore[misc, assignment]

from reddit_insight.reports.templates import (
    COMPETITIVE_REPORT_TEMPLATE,
    # Default Templates
    DEFAULT_TEMPLATES,
    DEMAND_REPORT_TEMPLATE,
    FULL_REPORT_TEMPLATE,
    INSIGHT_REPORT_TEMPLATE,
    TREND_REPORT_TEMPLATE,
    # Data Classes
    ReportTemplate,
    # Enums
    ReportType,
    # Registry
    TemplateRegistry,
    format_badge,
    format_date,
    format_list,
    # Data Formatters
    format_percentage,
    format_score,
    # Markdown Helpers
    format_table,
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
    # PDF/Excel Generators (optional)
    "PDFGenerator",
    "ExcelGenerator",
    "generate_pdf_from_report",
    "generate_excel_from_report",
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
