"""
PDF Report Generator Module.

HTML 기반 PDF 리포트 생성기를 제공한다.
WeasyPrint를 사용하여 HTML을 PDF로 변환한다.

Example:
    >>> from reddit_insight.reports import PDFGenerator
    >>> from reddit_insight.dashboard.services.report_service import ReportData
    >>> generator = PDFGenerator()
    >>> pdf_bytes = generator.generate(report_data)
    >>> with open("report.pdf", "wb") as f:
    ...     f.write(pdf_bytes)
"""

from __future__ import annotations

from datetime import UTC, datetime
from io import BytesIO
from typing import TYPE_CHECKING, Any

try:
    from weasyprint import CSS, HTML
    WEASYPRINT_AVAILABLE = True
except (ImportError, OSError):
    # OSError can occur if system libraries (pango, cairo) are missing
    WEASYPRINT_AVAILABLE = False
    CSS = None  # type: ignore[misc, assignment]
    HTML = None  # type: ignore[misc, assignment]

if TYPE_CHECKING:
    from reddit_insight.dashboard.services.report_service import ReportData


# =============================================================================
# PDF STYLES
# =============================================================================

PDF_STYLES = """
@page {
    size: A4;
    margin: 2cm;
    @top-center {
        content: "Reddit Insight Business Report";
        font-size: 9pt;
        color: #666;
    }
    @bottom-center {
        content: "Page " counter(page) " of " counter(pages);
        font-size: 9pt;
        color: #666;
    }
}

body {
    font-family: 'Noto Sans KR', 'Helvetica Neue', Arial, sans-serif;
    font-size: 11pt;
    line-height: 1.6;
    color: #333;
}

h1 {
    color: #1a56db;
    font-size: 24pt;
    margin-bottom: 0.5em;
    border-bottom: 2px solid #1a56db;
    padding-bottom: 0.3em;
}

h2 {
    color: #1e40af;
    font-size: 16pt;
    margin-top: 1.5em;
    margin-bottom: 0.5em;
    border-left: 4px solid #1e40af;
    padding-left: 0.5em;
}

h3 {
    color: #374151;
    font-size: 13pt;
    margin-top: 1em;
    margin-bottom: 0.3em;
}

h4 {
    color: #4b5563;
    font-size: 11pt;
    margin-top: 0.8em;
    margin-bottom: 0.2em;
}

p {
    margin: 0.5em 0;
}

ul, ol {
    margin: 0.5em 0;
    padding-left: 1.5em;
}

li {
    margin: 0.3em 0;
}

table {
    width: 100%;
    border-collapse: collapse;
    margin: 1em 0;
    font-size: 10pt;
}

th {
    background-color: #f3f4f6;
    border: 1px solid #d1d5db;
    padding: 8px 12px;
    text-align: left;
    font-weight: 600;
}

td {
    border: 1px solid #d1d5db;
    padding: 8px 12px;
}

tr:nth-child(even) {
    background-color: #f9fafb;
}

.header {
    margin-bottom: 2em;
}

.header-meta {
    color: #6b7280;
    font-size: 10pt;
    margin-top: 0.5em;
}

.executive-summary {
    background-color: #f0f9ff;
    border: 1px solid #bfdbfe;
    border-radius: 8px;
    padding: 1em;
    margin: 1em 0;
}

.business-item {
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    padding: 1em;
    margin: 1em 0;
    page-break-inside: avoid;
}

.business-item-header {
    display: flex;
    align-items: center;
    margin-bottom: 0.5em;
}

.rank-badge {
    display: inline-block;
    width: 28px;
    height: 28px;
    border-radius: 50%;
    background-color: #1a56db;
    color: white;
    text-align: center;
    line-height: 28px;
    font-weight: bold;
    font-size: 12pt;
    margin-right: 0.5em;
}

.rank-badge.high {
    background-color: #16a34a;
}

.rank-badge.medium {
    background-color: #2563eb;
}

.rank-badge.low {
    background-color: #ca8a04;
}

.score-badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 9pt;
    font-weight: 600;
    margin-left: auto;
}

.score-badge.high {
    background-color: #dcfce7;
    color: #166534;
}

.score-badge.medium {
    background-color: #dbeafe;
    color: #1e40af;
}

.score-badge.low {
    background-color: #fef9c3;
    color: #854d0e;
}

.metric-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 0.5em;
    margin: 0.5em 0;
    font-size: 10pt;
}

.metric-label {
    color: #6b7280;
}

.metric-value {
    font-weight: 600;
    color: #111827;
}

.evidence {
    font-style: italic;
    color: #4b5563;
    border-left: 3px solid #d1d5db;
    padding-left: 0.8em;
    margin: 0.5em 0;
    font-size: 10pt;
}

.recommendations li {
    margin: 0.5em 0;
}

.risk-item {
    display: flex;
    align-items: flex-start;
    margin: 0.5em 0;
}

.risk-icon {
    color: #ca8a04;
    margin-right: 0.5em;
}

.footer {
    margin-top: 2em;
    padding-top: 1em;
    border-top: 1px solid #e5e7eb;
    font-size: 9pt;
    color: #6b7280;
    text-align: center;
}

.keyword-tag {
    display: inline-block;
    background-color: #e0e7ff;
    color: #3730a3;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 9pt;
    margin: 2px;
}
"""


# =============================================================================
# PDF GENERATOR CLASS
# =============================================================================


class PDFGenerator:
    """
    PDF 리포트 생성기.

    ReportData를 HTML로 변환한 후 WeasyPrint로 PDF를 생성한다.

    Attributes:
        _styles: CSS 스타일 문자열

    Example:
        >>> generator = PDFGenerator()
        >>> pdf_bytes = generator.generate(report_data)
        >>> generator.save(pdf_bytes, "report.pdf")
    """

    def __init__(self, styles: str | None = None) -> None:
        """
        PDF 생성기 초기화.

        Args:
            styles: 커스텀 CSS 스타일 (None이면 기본 스타일 사용)

        Raises:
            ImportError: WeasyPrint가 설치되지 않은 경우
        """
        if not WEASYPRINT_AVAILABLE:
            raise ImportError(
                "WeasyPrint is required for PDF generation. "
                "Install with: pip install weasyprint"
            )
        self._styles = styles or PDF_STYLES

    def __repr__(self) -> str:
        """String representation for debugging."""
        return "PDFGenerator()"

    # =========================================================================
    # PUBLIC METHODS
    # =========================================================================

    def generate(self, report: ReportData) -> bytes:
        """
        ReportData를 PDF로 변환한다.

        Args:
            report: ReportData 인스턴스

        Returns:
            PDF 바이트 데이터
        """
        html_content = self._render_html(report)
        return self.generate_from_html(html_content)

    def generate_from_html(self, html: str) -> bytes:
        """
        HTML 문자열을 PDF로 변환한다.

        Args:
            html: HTML 문자열

        Returns:
            PDF 바이트 데이터
        """
        html_doc = HTML(string=html)
        css = CSS(string=self._styles)

        buffer = BytesIO()
        html_doc.write_pdf(buffer, stylesheets=[css])
        buffer.seek(0)

        return buffer.read()

    def save(self, pdf_bytes: bytes, filepath: str) -> None:
        """
        PDF를 파일로 저장한다.

        Args:
            pdf_bytes: PDF 바이트 데이터
            filepath: 저장할 파일 경로
        """
        with open(filepath, "wb") as f:
            f.write(pdf_bytes)

    # =========================================================================
    # PRIVATE METHODS - HTML RENDERING
    # =========================================================================

    def _render_html(self, report: ReportData) -> str:
        """
        ReportData를 HTML로 렌더링한다.

        Args:
            report: ReportData 인스턴스

        Returns:
            HTML 문자열
        """
        sections = [
            self._render_header(report),
            self._render_executive_summary(report),
            self._render_market_overview(report),
            self._render_business_items(report),
            self._render_trend_analysis(report),
            self._render_recommendations(report),
            self._render_risk_factors(report),
            self._render_conclusion(report),
            self._render_footer(report),
        ]

        body = "\n".join(sections)

        return f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>Reddit Insight Business Report - r/{report.subreddit}</title>
</head>
<body>
{body}
</body>
</html>"""

    def _render_header(self, report: ReportData) -> str:
        """헤더 섹션 렌더링."""
        return f"""
<div class="header">
    <h1>비즈니스 분석 보고서: r/{report.subreddit}</h1>
    <div class="header-meta">
        <p><strong>생성일시:</strong> {report.generated_at.strftime('%Y-%m-%d %H:%M UTC')}</p>
        <p><strong>분석 기간:</strong> {report.analysis_period}</p>
        <p><strong>분석 게시물 수:</strong> {report.total_posts_analyzed:,}개</p>
    </div>
</div>
"""

    def _render_executive_summary(self, report: ReportData) -> str:
        """Executive Summary 섹션 렌더링."""
        # Convert newlines to HTML breaks
        summary_html = report.executive_summary.replace("\n", "<br>")
        return f"""
<h2>1. Executive Summary</h2>
<div class="executive-summary">
    {summary_html}
</div>
"""

    def _render_market_overview(self, report: ReportData) -> str:
        """시장 개요 섹션 렌더링."""
        overview = report.market_overview
        key_topics_html = ""

        if overview.get("key_topics"):
            topics = "".join(
                f'<span class="keyword-tag">{topic}</span>'
                for topic in overview["key_topics"]
            )
            key_topics_html = f"""
<h4>주요 토픽</h4>
<div>{topics}</div>
"""

        return f"""
<h2>2. 시장 개요</h2>
<table>
    <tr>
        <th>항목</th>
        <th>값</th>
    </tr>
    <tr>
        <td>커뮤니티</td>
        <td>{overview.get('community_size', 'N/A')}</td>
    </tr>
    <tr>
        <td>활동 수준</td>
        <td>{overview.get('activity_level', 'N/A')}</td>
    </tr>
    <tr>
        <td>데이터 품질</td>
        <td>{overview.get('data_quality', 'N/A')}</td>
    </tr>
    <tr>
        <td>시장 성숙도</td>
        <td>{overview.get('market_maturity', 'N/A')}</td>
    </tr>
</table>
{key_topics_html}
"""

    def _render_business_items(self, report: ReportData) -> str:
        """비즈니스 아이템 섹션 렌더링."""
        if not report.business_items:
            return """
<h2>3. 비즈니스 기회</h2>
<p><em>도출된 비즈니스 아이템이 없습니다.</em></p>
"""

        items_html = []
        for item in report.business_items:
            # Score badge class
            if item.opportunity_score >= 80:
                score_class = "high"
            elif item.opportunity_score >= 60:
                score_class = "medium"
            else:
                score_class = "low"

            # Key features
            features_html = "".join(f"<li>{f}</li>" for f in item.key_features)

            # Next steps
            steps_html = "".join(f"<li>{s}</li>" for s in item.next_steps)

            # Evidence
            evidence_html = ""
            if item.evidence:
                evidence_items = "".join(
                    f'<p class="evidence">"{e[:200]}..."</p>'
                    for e in item.evidence[:2]
                )
                evidence_html = f"""
<h4>근거 데이터</h4>
{evidence_items}
"""

            items_html.append(f"""
<div class="business-item">
    <div class="business-item-header">
        <span class="rank-badge {score_class}">#{item.rank}</span>
        <h3 style="margin: 0; flex: 1;">{item.title}</h3>
        <span class="score-badge {score_class}">Score: {item.opportunity_score:.1f}</span>
    </div>

    <div class="metric-grid">
        <div><span class="metric-label">카테고리:</span> <span class="metric-value">{item.category}</span></div>
        <div><span class="metric-label">시장 잠재력:</span> <span class="metric-value">{item.market_potential}</span></div>
        <div><span class="metric-label">리스크:</span> <span class="metric-value">{item.risk_level}</span></div>
    </div>

    <p>{item.description}</p>

    <h4>타겟 고객</h4>
    <p>{item.target_audience}</p>

    <h4>핵심 기능</h4>
    <ul>{features_html}</ul>

    <h4>경쟁 우위</h4>
    <p>{item.competitive_advantage}</p>

    <h4>다음 단계</h4>
    <ol>{steps_html}</ol>

    {evidence_html}
</div>
""")

        return f"""
<h2>3. 비즈니스 기회</h2>
{"".join(items_html)}
"""

    def _render_trend_analysis(self, report: ReportData) -> str:
        """트렌드 분석 섹션 렌더링."""
        trend = report.trend_analysis

        keywords_table = ""
        if trend.get("top_keywords"):
            rows = "".join(
                f"""<tr>
                    <td>{i}</td>
                    <td>{kw['keyword']}</td>
                    <td>{kw['score']:.2f}</td>
                </tr>"""
                for i, kw in enumerate(trend["top_keywords"][:10], 1)
            )
            keywords_table = f"""
<h3>상위 키워드</h3>
<table>
    <tr>
        <th>순위</th>
        <th>키워드</th>
        <th>점수</th>
    </tr>
    {rows}
</table>
"""

        return f"""
<h2>4. 트렌드 분석</h2>
<p>{trend.get('trend_summary', '트렌드 데이터가 없습니다.')}</p>
{keywords_table}
"""

    def _render_recommendations(self, report: ReportData) -> str:
        """추천 사항 섹션 렌더링."""
        if not report.recommendations:
            return """
<h2>5. 추천 사항</h2>
<p><em>추천 사항이 없습니다.</em></p>
"""

        items = "".join(f"<li>{rec}</li>" for rec in report.recommendations)
        return f"""
<h2>5. 추천 사항</h2>
<ul class="recommendations">
{items}
</ul>
"""

    def _render_risk_factors(self, report: ReportData) -> str:
        """리스크 요인 섹션 렌더링."""
        if not report.risk_factors:
            return """
<h2>6. 리스크 요인</h2>
<p><em>식별된 리스크가 없습니다.</em></p>
"""

        items = "".join(
            f'<li class="risk-item">{risk}</li>'
            for risk in report.risk_factors
        )
        return f"""
<h2>6. 리스크 요인</h2>
<ul>
{items}
</ul>
"""

    def _render_conclusion(self, report: ReportData) -> str:
        """결론 섹션 렌더링."""
        return f"""
<h2>7. 결론</h2>
<p>{report.conclusion}</p>
"""

    def _render_footer(self, report: ReportData) -> str:
        """푸터 섹션 렌더링."""
        return f"""
<div class="footer">
    <p>본 보고서는 Reddit 커뮤니티 데이터를 기반으로 자동 생성되었습니다.</p>
    <p>실제 비즈니스 의사결정 시 추가적인 시장 조사 및 전문가 검토를 권장합니다.</p>
    <p>Generated by Reddit Insight - {report.generated_at.strftime('%Y-%m-%d %H:%M UTC')}</p>
</div>
"""


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================


def generate_pdf_from_report(report: ReportData) -> bytes:
    """
    ReportData에서 PDF를 생성하는 유틸리티 함수.

    Args:
        report: ReportData 인스턴스

    Returns:
        PDF 바이트 데이터

    Example:
        >>> pdf_bytes = generate_pdf_from_report(report_data)
    """
    generator = PDFGenerator()
    return generator.generate(report)
