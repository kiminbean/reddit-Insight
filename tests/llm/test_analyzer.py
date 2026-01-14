"""LLM Analyzer 테스트.

Mock을 사용하여 실제 API 호출 없이 LLMAnalyzer의 각 기능을 테스트한다.
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from reddit_insight.llm import (
    LLMAnalyzer,
    CategoryResult,
    DeepSentimentResult,
    Insight,
    LLMClient,
    ClaudeClient,
)


@pytest.fixture
def mock_client() -> MagicMock:
    """Mock LLM 클라이언트를 생성한다."""
    client = MagicMock(spec=LLMClient)
    client.complete_with_retry = AsyncMock()
    return client


@pytest.fixture
def analyzer(mock_client: MagicMock) -> LLMAnalyzer:
    """테스트용 LLMAnalyzer 인스턴스를 생성한다."""
    return LLMAnalyzer(client=mock_client, max_retries=2)


class TestLLMAnalyzerInit:
    """LLMAnalyzer 초기화 테스트."""

    def test_init_with_client(self, mock_client: MagicMock) -> None:
        """클라이언트로 초기화된다."""
        analyzer = LLMAnalyzer(client=mock_client)

        assert analyzer.client == mock_client
        assert analyzer.max_retries == 3  # 기본값

    def test_init_with_custom_retries(self, mock_client: MagicMock) -> None:
        """커스텀 재시도 횟수로 초기화된다."""
        analyzer = LLMAnalyzer(client=mock_client, max_retries=5)

        assert analyzer.max_retries == 5


class TestSummarizePosts:
    """summarize_posts 메서드 테스트."""

    @pytest.mark.asyncio
    async def test_summarize_empty_posts(self, analyzer: LLMAnalyzer) -> None:
        """빈 게시물 목록은 기본 메시지를 반환한다."""
        result = await analyzer.summarize_posts([])

        assert result == "분석할 게시물이 없습니다."
        analyzer.client.complete_with_retry.assert_not_called()

    @pytest.mark.asyncio
    async def test_summarize_posts_success(
        self, analyzer: LLMAnalyzer, mock_client: MagicMock
    ) -> None:
        """게시물 요약이 성공한다."""
        posts = [
            {"title": "Test Post 1", "body": "Content 1", "score": 100},
            {"title": "Test Post 2", "body": "Content 2", "score": 50},
        ]
        expected_summary = "### 주요 주제\n1. 테스트 주제: 요약 내용"
        mock_client.complete_with_retry.return_value = expected_summary

        result = await analyzer.summarize_posts(posts)

        assert result == expected_summary
        mock_client.complete_with_retry.assert_called_once()

    @pytest.mark.asyncio
    async def test_summarize_posts_respects_max_posts(
        self, analyzer: LLMAnalyzer, mock_client: MagicMock
    ) -> None:
        """max_posts 제한이 적용된다."""
        posts = [{"title": f"Post {i}", "score": i} for i in range(100)]
        mock_client.complete_with_retry.return_value = "Summary"

        await analyzer.summarize_posts(posts, max_posts=10)

        # 프롬프트에 10개 게시물만 포함되었는지 확인
        call_args = mock_client.complete_with_retry.call_args
        prompt = call_args.kwargs["prompt"]
        assert "### 게시물 10" in prompt
        assert "### 게시물 11" not in prompt

    @pytest.mark.asyncio
    async def test_summarize_posts_handles_missing_fields(
        self, analyzer: LLMAnalyzer, mock_client: MagicMock
    ) -> None:
        """필드가 누락된 게시물도 처리한다."""
        posts = [
            {"title": "Post without body"},
            {"body": "Body without title"},
            {},  # 모든 필드 누락
        ]
        mock_client.complete_with_retry.return_value = "Summary"

        result = await analyzer.summarize_posts(posts)

        assert result == "Summary"


class TestCategorizeContent:
    """categorize_content 메서드 테스트."""

    @pytest.mark.asyncio
    async def test_categorize_empty_texts(self, analyzer: LLMAnalyzer) -> None:
        """빈 텍스트 목록은 빈 결과를 반환한다."""
        result = await analyzer.categorize_content([])

        assert result == []

    @pytest.mark.asyncio
    async def test_categorize_single_text(
        self, analyzer: LLMAnalyzer, mock_client: MagicMock
    ) -> None:
        """단일 텍스트 분류가 성공한다."""
        mock_client.complete_with_retry.return_value = """
        ```json
        {
            "primary_category": "Feature Request",
            "confidence": 85,
            "reason": "사용자가 새 기능을 요청함",
            "secondary_categories": [
                {"category": "Suggestion", "confidence": 60}
            ]
        }
        ```
        """

        result = await analyzer.categorize_content(["I wish this app had dark mode"])

        assert len(result) == 1
        assert result[0].category == "Feature Request"
        assert result[0].confidence == 85
        assert result[0].reason == "사용자가 새 기능을 요청함"

    @pytest.mark.asyncio
    async def test_categorize_multiple_texts(
        self, analyzer: LLMAnalyzer, mock_client: MagicMock
    ) -> None:
        """여러 텍스트 분류가 성공한다."""
        mock_client.complete_with_retry.side_effect = [
            '{"primary_category": "Bug Report", "confidence": 90}',
            '{"primary_category": "Question", "confidence": 75}',
        ]

        result = await analyzer.categorize_content(
            ["App crashes on startup", "How do I export data?"]
        )

        assert len(result) == 2
        assert result[0].category == "Bug Report"
        assert result[1].category == "Question"

    @pytest.mark.asyncio
    async def test_categorize_with_custom_categories(
        self, analyzer: LLMAnalyzer, mock_client: MagicMock
    ) -> None:
        """커스텀 카테고리로 분류한다."""
        custom_categories = ["Positive", "Negative", "Neutral"]
        mock_client.complete_with_retry.return_value = (
            '{"primary_category": "Positive", "confidence": 95}'
        )

        result = await analyzer.categorize_content(
            ["Great product!"],
            categories=custom_categories,
        )

        assert result[0].category == "Positive"
        # 프롬프트에 커스텀 카테고리가 포함되었는지 확인
        call_args = mock_client.complete_with_retry.call_args
        prompt = call_args.kwargs["prompt"]
        assert "Positive" in prompt
        assert "Negative" in prompt

    @pytest.mark.asyncio
    async def test_categorize_handles_parse_error(
        self, analyzer: LLMAnalyzer, mock_client: MagicMock
    ) -> None:
        """JSON 파싱 실패 시 기본값을 반환한다."""
        mock_client.complete_with_retry.return_value = "Invalid JSON response"

        result = await analyzer.categorize_content(["Some text"])

        assert len(result) == 1
        assert result[0].category == "Unknown"
        # JSON 파싱 실패 시 기본 confidence 50 사용 (parsed.get의 기본값)
        assert result[0].confidence == 50.0

    @pytest.mark.asyncio
    async def test_categorize_single_convenience_method(
        self, analyzer: LLMAnalyzer, mock_client: MagicMock
    ) -> None:
        """categorize_single 편의 메서드가 작동한다."""
        mock_client.complete_with_retry.return_value = (
            '{"primary_category": "Discussion", "confidence": 80}'
        )

        result = await analyzer.categorize_single("Let's discuss this topic")

        assert isinstance(result, CategoryResult)
        assert result.category == "Discussion"


class TestAnalyzeSentimentDeep:
    """analyze_sentiment_deep 메서드 테스트."""

    @pytest.mark.asyncio
    async def test_sentiment_empty_text(self, analyzer: LLMAnalyzer) -> None:
        """빈 텍스트는 중립 감성을 반환한다."""
        result = await analyzer.analyze_sentiment_deep("")

        assert result.overall_sentiment == "neutral"
        assert result.sentiment_score == 0.0

    @pytest.mark.asyncio
    async def test_sentiment_positive(
        self, analyzer: LLMAnalyzer, mock_client: MagicMock
    ) -> None:
        """긍정적 텍스트 분석이 성공한다."""
        mock_client.complete_with_retry.return_value = """
        {
            "overall_sentiment": "positive",
            "sentiment_score": 0.85,
            "factors": [
                {"aspect": "quality", "sentiment": "positive", "reason": "Good quality"}
            ],
            "emotions": ["satisfaction", "joy"],
            "is_opinion": true,
            "user_needs": ["keep it up"],
            "pain_points": []
        }
        """

        result = await analyzer.analyze_sentiment_deep(
            "I absolutely love this product! The quality is amazing."
        )

        assert result.overall_sentiment == "positive"
        assert result.sentiment_score == 0.85
        assert len(result.factors) == 1
        assert result.factors[0].aspect == "quality"
        assert "satisfaction" in result.emotions

    @pytest.mark.asyncio
    async def test_sentiment_negative(
        self, analyzer: LLMAnalyzer, mock_client: MagicMock
    ) -> None:
        """부정적 텍스트 분석이 성공한다."""
        mock_client.complete_with_retry.return_value = """
        {
            "overall_sentiment": "negative",
            "sentiment_score": -0.75,
            "factors": [
                {"aspect": "price", "sentiment": "negative", "reason": "Too expensive"},
                {"aspect": "service", "sentiment": "negative", "reason": "Slow response"}
            ],
            "emotions": ["frustration", "disappointment"],
            "is_opinion": true,
            "user_needs": ["lower price", "faster support"],
            "pain_points": ["high cost", "slow customer service"]
        }
        """

        result = await analyzer.analyze_sentiment_deep(
            "This is overpriced and the support is terrible!"
        )

        assert result.overall_sentiment == "negative"
        assert result.sentiment_score == -0.75
        assert len(result.factors) == 2
        assert len(result.pain_points) == 2

    @pytest.mark.asyncio
    async def test_sentiment_handles_api_error(
        self, analyzer: LLMAnalyzer, mock_client: MagicMock
    ) -> None:
        """API 오류 시 중립 감성을 반환한다."""
        mock_client.complete_with_retry.side_effect = Exception("API Error")

        result = await analyzer.analyze_sentiment_deep("Some text")

        assert result.overall_sentiment == "neutral"
        assert result.sentiment_score == 0.0


class TestGenerateInsights:
    """generate_insights 메서드 테스트."""

    @pytest.mark.asyncio
    async def test_insights_empty_data(self, analyzer: LLMAnalyzer) -> None:
        """빈 데이터는 빈 인사이트를 반환한다."""
        result = await analyzer.generate_insights({})

        assert result == []

    @pytest.mark.asyncio
    async def test_insights_success(
        self, analyzer: LLMAnalyzer, mock_client: MagicMock
    ) -> None:
        """인사이트 생성이 성공한다."""
        mock_client.complete_with_retry.return_value = """
### 인사이트 1: 가격 민감도 증가
- **발견**: 사용자들이 가격에 대한 불만을 많이 표출함
- **의미**: 경쟁사 대비 가격 경쟁력 약화
- **권장 조치**: 가격 재검토 또는 가치 제안 강화
- **우선순위**: 높음

### 인사이트 2: 모바일 앱 수요
- **발견**: 모바일 앱 요청이 증가하고 있음
- **의미**: 모바일 시장 진출 기회
- **권장 조치**: 모바일 앱 개발 검토
- **우선순위**: 중간
"""
        analysis_data = {
            "trends": {"rising": ["mobile", "app"]},
            "sentiment": {"negative_ratio": 0.3},
        }

        result = await analyzer.generate_insights(
            analysis_data,
            subreddit="test_sub",
            period="last 7 days",
        )

        assert len(result) == 2
        assert result[0].title == "가격 민감도 증가"
        assert result[0].priority == "high"
        assert result[1].priority == "medium"

    @pytest.mark.asyncio
    async def test_insights_handles_api_error(
        self, analyzer: LLMAnalyzer, mock_client: MagicMock
    ) -> None:
        """API 오류 시 빈 인사이트를 반환한다."""
        mock_client.complete_with_retry.side_effect = Exception("API Error")

        result = await analyzer.generate_insights({"some": "data"})

        assert result == []


class TestInterpretTrends:
    """interpret_trends 메서드 테스트."""

    @pytest.mark.asyncio
    async def test_interpret_trends_success(
        self, analyzer: LLMAnalyzer, mock_client: MagicMock
    ) -> None:
        """트렌드 해석이 성공한다."""
        expected_interpretation = "### 트렌드 요약\n1. AI 관련 토픽 급증"
        mock_client.complete_with_retry.return_value = expected_interpretation

        result = await analyzer.interpret_trends(
            trend_data={"keyword_counts": {"ai": 100, "ml": 50}},
            rising_keywords=["ai", "chatgpt"],
            declining_keywords=["legacy", "old"],
            target="r/technology",
            comparison_period="week over week",
        )

        assert result == expected_interpretation
        mock_client.complete_with_retry.assert_called_once()

    @pytest.mark.asyncio
    async def test_interpret_trends_handles_error(
        self, analyzer: LLMAnalyzer, mock_client: MagicMock
    ) -> None:
        """트렌드 해석 오류 시 에러 메시지를 반환한다."""
        mock_client.complete_with_retry.side_effect = Exception("API Error")

        result = await analyzer.interpret_trends(
            trend_data={},
            rising_keywords=[],
            declining_keywords=[],
        )

        assert "오류가 발생했습니다" in result


class TestHelperMethods:
    """헬퍼 메서드 테스트."""

    def test_format_posts_for_prompt(self, analyzer: LLMAnalyzer) -> None:
        """게시물 포맷팅이 올바르게 작동한다."""
        posts = [
            {"title": "Title 1", "body": "Body 1", "score": 100, "num_comments": 10},
            {"title": "Title 2", "selftext": "Body 2", "score": 50, "comments": 5},
        ]

        result = analyzer._format_posts_for_prompt(posts)

        assert "### 게시물 1" in result
        assert "**제목**: Title 1" in result
        assert "**점수**: 100" in result
        assert "### 게시물 2" in result

    def test_format_posts_truncates_long_body(self, analyzer: LLMAnalyzer) -> None:
        """긴 본문이 축약된다."""
        posts = [
            {"title": "Title", "body": "x" * 1000, "score": 0},
        ]

        result = analyzer._format_posts_for_prompt(posts)

        assert len(result) < 1000
        assert "..." in result

    def test_parse_json_response_with_code_block(self, analyzer: LLMAnalyzer) -> None:
        """코드 블록 내 JSON을 파싱한다."""
        response = """Here is the result:
        ```json
        {"key": "value", "number": 42}
        ```
        """

        result = analyzer._parse_json_response(response)

        assert result == {"key": "value", "number": 42}

    def test_parse_json_response_without_code_block(
        self, analyzer: LLMAnalyzer
    ) -> None:
        """코드 블록 없는 JSON을 파싱한다."""
        response = '{"key": "value"}'

        result = analyzer._parse_json_response(response)

        assert result == {"key": "value"}

    def test_parse_json_response_invalid_json(self, analyzer: LLMAnalyzer) -> None:
        """잘못된 JSON은 빈 딕셔너리를 반환한다."""
        response = "This is not JSON"

        result = analyzer._parse_json_response(response)

        assert result == {}

    def test_parse_insights_response(self, analyzer: LLMAnalyzer) -> None:
        """마크다운 인사이트 응답을 파싱한다."""
        response = """
### 인사이트 1: 첫 번째 인사이트
- **발견**: 발견 내용 1
- **의미**: 의미 설명 1
- **권장 조치**: 권장 사항 1
- **우선순위**: 높음

### 인사이트 2: 두 번째 인사이트
- **발견**: 발견 내용 2
- **의미**: 의미 설명 2
- **권장 조치**: 권장 사항 2
- **우선순위**: 낮음
"""

        result = analyzer._parse_insights_response(response)

        assert len(result) == 2
        assert result[0].title == "첫 번째 인사이트"
        assert result[0].finding == "발견 내용 1"
        assert result[0].priority == "high"
        assert result[1].priority == "low"
