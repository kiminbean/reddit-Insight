"""PDF Generator 테스트.

PDFGenerator 클래스의 PDF 생성 기능을 테스트한다.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import pytest

# Check if WeasyPrint and its dependencies are available
try:
    from weasyprint import CSS, HTML
    WEASYPRINT_AVAILABLE = True
except (ImportError, OSError):
    WEASYPRINT_AVAILABLE = False

# Skip all tests in this module if WeasyPrint is not available
pytestmark = pytest.mark.skipif(
    not WEASYPRINT_AVAILABLE,
    reason="WeasyPrint not available (requires system libraries: pango, cairo)"
)


# =============================================================================
# TEST FIXTURES
# =============================================================================


@dataclass
class BusinessItem:
    """테스트용 BusinessItem."""

    rank: int
    title: str
    category: str
    opportunity_score: float
    market_potential: str
    risk_level: str
    description: str
    target_audience: str
    key_features: list[str]
    competitive_advantage: str
    next_steps: list[str]
    evidence: list[str]


@dataclass
class MockReportData:
    """테스트용 ReportData mock."""

    subreddit: str
    generated_at: datetime
    analysis_period: str
    total_posts_analyzed: int
    total_keywords: int
    total_insights: int
    executive_summary: str
    market_overview: dict[str, Any]
    business_items: list[BusinessItem]
    trend_analysis: dict[str, Any]
    demand_analysis: dict[str, Any]
    competition_analysis: dict[str, Any]
    recommendations: list[str]
    risk_factors: list[str]
    conclusion: str


@pytest.fixture
def sample_report_data() -> MockReportData:
    """샘플 리포트 데이터를 생성한다."""
    return MockReportData(
        subreddit="python",
        generated_at=datetime.now(UTC),
        analysis_period="Last 7 days",
        total_posts_analyzed=150,
        total_keywords=50,
        total_insights=10,
        executive_summary=(
            "r/python 커뮤니티의 150개 게시물 분석 결과, "
            "10개의 인사이트와 3개의 비즈니스 기회를 도출했습니다.\n\n"
            "**최우선 기회**: AI 기반 코드 분석 도구"
        ),
        market_overview={
            "community_size": "r/python",
            "activity_level": "활발",
            "data_quality": "충분",
            "market_maturity": "성장 시장 - 일부 솔루션 존재, 기회 있음",
            "key_topics": ["python", "ai", "machine learning", "automation"],
        },
        business_items=[
            BusinessItem(
                rank=1,
                title="AI 기반 코드 분석 도구",
                category="신규 시장 진입",
                opportunity_score=85.5,
                market_potential="높음",
                risk_level="낮음",
                description="개발자를 위한 AI 기반 코드 품질 분석 및 개선 도구",
                target_audience="소프트웨어 개발자 및 기술 전문가",
                key_features=["AI 기반 자동화", "실시간 처리", "외부 서비스 연동"],
                competitive_advantage="시장 내 미개척 영역 선점으로 인한 선발자 우위",
                next_steps=[
                    "MVP 개발 및 초기 사용자 테스트 진행",
                    "핵심 타겟 고객 인터뷰 실시",
                ],
                evidence=[
                    "I wish there was a tool that could automatically review my code",
                    "We need better AI integration in our development workflow",
                ],
            ),
            BusinessItem(
                rank=2,
                title="파이썬 학습 플랫폼",
                category="트렌드 기반 서비스",
                opportunity_score=72.0,
                market_potential="중간",
                risk_level="중간",
                description="초보자를 위한 인터랙티브 파이썬 학습 플랫폼",
                target_audience="학생 및 교육 관련 사용자",
                key_features=["실시간 처리", "협업 기능"],
                competitive_advantage="트렌드 선도를 통한 시장 리더십 확보",
                next_steps=[
                    "시장 조사 및 수요 검증 심화",
                    "프로토타입 개발 및 피드백 수집",
                ],
                evidence=[
                    "Learning Python is hard without proper guidance",
                ],
            ),
        ],
        trend_analysis={
            "total_keywords": 50,
            "top_keywords": [
                {"keyword": "python", "score": 0.95},
                {"keyword": "ai", "score": 0.88},
                {"keyword": "machine learning", "score": 0.82},
                {"keyword": "automation", "score": 0.75},
                {"keyword": "data science", "score": 0.70},
            ],
            "rising_topics": [],
            "trend_summary": "주요 키워드: python, ai, machine learning.",
        },
        demand_analysis={
            "total_demands": 25,
            "by_category": {"feature_request": 10, "pain_point": 8, "search_query": 7},
            "top_opportunities": [],
            "demand_summary": "총 25개의 수요 신호가 감지되었습니다.",
        },
        competition_analysis={
            "entities_mentioned": [],
            "sentiment_distribution": {},
            "key_complaints": [],
            "competition_summary": "경쟁 분석 데이터가 충분하지 않습니다.",
        },
        recommendations=[
            "1. **AI 기반 코드 분석 도구** 기회를 우선 검토하세요.",
            "2. 사용자 수요가 높은 기능에 집중하여 MVP를 설계하세요.",
            "3. 타겟 커뮤니티에서 직접 피드백을 수집하세요.",
        ],
        risk_factors=[
            "데이터 샘플 크기가 작아 분석 결과의 신뢰도가 제한될 수 있음",
            "Reddit 커뮤니티 의견이 전체 시장을 대표하지 않을 수 있음",
        ],
        conclusion=(
            "본 분석을 통해 2개의 비즈니스 기회를 도출했습니다. "
            "제시된 추천 사항을 참고하여 시장 검증을 진행하시기 바랍니다."
        ),
    )


@pytest.fixture
def empty_report_data() -> MockReportData:
    """빈 리포트 데이터를 생성한다."""
    return MockReportData(
        subreddit="empty_sub",
        generated_at=datetime.now(UTC),
        analysis_period="Last 7 days",
        total_posts_analyzed=10,
        total_keywords=0,
        total_insights=0,
        executive_summary="분석 데이터가 충분하지 않습니다.",
        market_overview={
            "community_size": "r/empty_sub",
            "activity_level": "낮음",
            "data_quality": "추가 필요",
        },
        business_items=[],
        trend_analysis={
            "total_keywords": 0,
            "top_keywords": [],
            "trend_summary": "트렌드 데이터가 없습니다.",
        },
        demand_analysis={
            "total_demands": 0,
            "demand_summary": "수요 분석 데이터가 없습니다.",
        },
        competition_analysis={
            "competition_summary": "경쟁 분석 데이터가 없습니다.",
        },
        recommendations=[],
        risk_factors=[],
        conclusion="데이터가 충분하지 않습니다.",
    )


# =============================================================================
# IMPORT TESTS
# =============================================================================


class TestPDFGeneratorImport:
    """PDFGenerator import 테스트."""

    def test_import_pdf_generator(self) -> None:
        """PDFGenerator를 import할 수 있다."""
        try:
            from reddit_insight.reports.pdf_generator import PDFGenerator
            assert PDFGenerator is not None
        except ImportError as e:
            # WeasyPrint가 설치되지 않은 경우
            pytest.skip(f"WeasyPrint not available: {e}")

    def test_import_utility_function(self) -> None:
        """generate_pdf_from_report 유틸리티 함수를 import할 수 있다."""
        try:
            from reddit_insight.reports.pdf_generator import generate_pdf_from_report
            assert generate_pdf_from_report is not None
        except ImportError as e:
            pytest.skip(f"WeasyPrint not available: {e}")


# =============================================================================
# PDF GENERATION TESTS
# =============================================================================


class TestPDFGenerator:
    """PDFGenerator 테스트."""

    @pytest.fixture
    def generator(self):
        """PDFGenerator 인스턴스를 생성한다."""
        try:
            from reddit_insight.reports.pdf_generator import PDFGenerator
            return PDFGenerator()
        except ImportError:
            pytest.skip("WeasyPrint not available")

    def test_generator_repr(self, generator) -> None:
        """PDFGenerator repr이 올바르게 반환된다."""
        assert repr(generator) == "PDFGenerator()"

    def test_generate_from_html_returns_bytes(self, generator) -> None:
        """generate_from_html이 바이트를 반환한다."""
        html = "<html><body><h1>Test</h1></body></html>"
        result = generator.generate_from_html(html)

        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_generate_from_html_creates_valid_pdf(self, generator) -> None:
        """generate_from_html이 유효한 PDF를 생성한다."""
        html = "<html><body><h1>Test Report</h1><p>Content</p></body></html>"
        result = generator.generate_from_html(html)

        # PDF 매직 넘버 확인
        assert result.startswith(b"%PDF")

    def test_generate_creates_pdf(self, generator, sample_report_data) -> None:
        """generate가 ReportData에서 PDF를 생성한다."""
        result = generator.generate(sample_report_data)

        assert isinstance(result, bytes)
        assert result.startswith(b"%PDF")
        assert len(result) > 1000  # 최소 크기 확인

    def test_generate_includes_report_content(
        self, generator, sample_report_data
    ) -> None:
        """생성된 PDF가 리포트 내용을 포함한다."""
        # PDF 내용 자체를 검사하기 어려우므로
        # HTML 렌더링이 올바르게 작동하는지 확인
        html = generator._render_html(sample_report_data)

        assert sample_report_data.subreddit in html
        assert "Executive Summary" in html
        assert sample_report_data.business_items[0].title in html

    def test_generate_with_empty_data(self, generator, empty_report_data) -> None:
        """빈 데이터로도 PDF를 생성할 수 있다."""
        result = generator.generate(empty_report_data)

        assert isinstance(result, bytes)
        assert result.startswith(b"%PDF")

    def test_generate_with_korean_content(self, generator) -> None:
        """한국어 내용이 포함된 HTML을 PDF로 변환할 수 있다."""
        html = """
        <html>
        <body>
            <h1>비즈니스 분석 보고서</h1>
            <p>한국어 내용이 포함되어 있습니다.</p>
            <ul>
                <li>첫 번째 항목</li>
                <li>두 번째 항목</li>
            </ul>
        </body>
        </html>
        """
        result = generator.generate_from_html(html)

        assert isinstance(result, bytes)
        assert result.startswith(b"%PDF")


class TestPDFGeneratorHTMLRendering:
    """PDFGenerator HTML 렌더링 테스트."""

    @pytest.fixture
    def generator(self):
        """PDFGenerator 인스턴스를 생성한다."""
        try:
            from reddit_insight.reports.pdf_generator import PDFGenerator
            return PDFGenerator()
        except ImportError:
            pytest.skip("WeasyPrint not available")

    def test_render_html_includes_header(
        self, generator, sample_report_data
    ) -> None:
        """렌더링된 HTML이 헤더를 포함한다."""
        html = generator._render_html(sample_report_data)

        assert "<h1>" in html
        assert sample_report_data.subreddit in html
        assert "생성일시" in html

    def test_render_html_includes_business_items(
        self, generator, sample_report_data
    ) -> None:
        """렌더링된 HTML이 비즈니스 아이템을 포함한다."""
        html = generator._render_html(sample_report_data)

        for item in sample_report_data.business_items:
            assert item.title in html
            assert item.category in html

    def test_render_html_includes_trend_analysis(
        self, generator, sample_report_data
    ) -> None:
        """렌더링된 HTML이 트렌드 분석을 포함한다."""
        html = generator._render_html(sample_report_data)

        assert "트렌드 분석" in html
        for kw in sample_report_data.trend_analysis["top_keywords"][:5]:
            assert kw["keyword"] in html

    def test_render_html_includes_recommendations(
        self, generator, sample_report_data
    ) -> None:
        """렌더링된 HTML이 추천 사항을 포함한다."""
        html = generator._render_html(sample_report_data)

        assert "추천 사항" in html

    def test_render_html_includes_footer(
        self, generator, sample_report_data
    ) -> None:
        """렌더링된 HTML이 푸터를 포함한다."""
        html = generator._render_html(sample_report_data)

        assert "Reddit Insight" in html
        assert "class=\"footer\"" in html


class TestPDFGeneratorCustomStyles:
    """PDFGenerator 커스텀 스타일 테스트."""

    def test_custom_styles_applied(self) -> None:
        """커스텀 스타일이 적용된다."""
        try:
            from reddit_insight.reports.pdf_generator import PDFGenerator

            custom_css = "body { font-size: 14pt; color: red; }"
            generator = PDFGenerator(styles=custom_css)

            assert generator._styles == custom_css
        except ImportError:
            pytest.skip("WeasyPrint not available")


# =============================================================================
# UTILITY FUNCTION TESTS
# =============================================================================


class TestGeneratePDFFromReport:
    """generate_pdf_from_report 유틸리티 함수 테스트."""

    def test_utility_function_works(self, sample_report_data) -> None:
        """유틸리티 함수가 PDF를 생성한다."""
        try:
            from reddit_insight.reports.pdf_generator import generate_pdf_from_report

            result = generate_pdf_from_report(sample_report_data)

            assert isinstance(result, bytes)
            assert result.startswith(b"%PDF")
        except ImportError:
            pytest.skip("WeasyPrint not available")
