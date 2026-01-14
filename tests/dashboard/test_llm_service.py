"""LLM 대시보드 서비스 테스트.

Mock을 사용하여 실제 API 호출 없이 LLMService를 테스트한다.
"""

from __future__ import annotations

import pytest
from dataclasses import asdict
from unittest.mock import AsyncMock, MagicMock, patch

from reddit_insight.dashboard.services.llm_service import (
    LLMService,
    LLMSummaryView,
    LLMCategoryView,
    LLMSentimentView,
    LLMInsightView,
    get_llm_service,
    reset_llm_service,
)
from reddit_insight.dashboard.services.cache_service import CacheService
from reddit_insight.llm import (
    LLMAnalyzer,
    CategoryResult,
    DeepSentimentResult,
    SentimentAspect,
    Insight,
)


@pytest.fixture
def mock_analyzer() -> MagicMock:
    """Mock LLMAnalyzer를 생성한다."""
    analyzer = MagicMock(spec=LLMAnalyzer)
    analyzer.summarize_posts = AsyncMock()
    analyzer.categorize_content = AsyncMock()
    analyzer.analyze_sentiment_deep = AsyncMock()
    analyzer.generate_insights = AsyncMock()
    analyzer.interpret_trends = AsyncMock()
    return analyzer


@pytest.fixture
def cache() -> CacheService:
    """테스트용 CacheService를 생성한다."""
    return CacheService(default_ttl=60, max_entries=100)


@pytest.fixture
def service(mock_analyzer: MagicMock, cache: CacheService) -> LLMService:
    """테스트용 LLMService 인스턴스를 생성한다."""
    return LLMService(analyzer=mock_analyzer, cache=cache)


@pytest.fixture
def unconfigured_service(cache: CacheService) -> LLMService:
    """설정되지 않은 LLMService 인스턴스를 생성한다."""
    return LLMService(analyzer=None, cache=cache)


class TestLLMServiceInit:
    """LLMService 초기화 테스트."""

    def test_init_with_analyzer(self, mock_analyzer: MagicMock) -> None:
        """analyzer로 초기화되면 is_configured가 True다."""
        service = LLMService(analyzer=mock_analyzer)

        assert service.is_configured is True
        assert service.analyzer == mock_analyzer

    def test_init_without_analyzer(self) -> None:
        """analyzer 없이 초기화되면 is_configured가 False다."""
        service = LLMService(analyzer=None)

        assert service.is_configured is False
        assert service.analyzer is None


class TestGetSummary:
    """get_summary 메서드 테스트."""

    @pytest.mark.asyncio
    async def test_summary_success(
        self, service: LLMService, mock_analyzer: MagicMock
    ) -> None:
        """요약 생성이 성공한다."""
        mock_analyzer.summarize_posts.return_value = "### 주요 주제\n1. AI 관련 토픽"
        posts = [
            {"title": "Post 1", "score": 100},
            {"title": "Post 2", "score": 50},
        ]

        result = await service.get_summary("python", posts)

        assert isinstance(result, LLMSummaryView)
        assert result.summary == "### 주요 주제\n1. AI 관련 토픽"
        assert result.post_count == 2
        assert result.subreddit == "python"
        assert result.cached is False

    @pytest.mark.asyncio
    async def test_summary_uses_cache(
        self, service: LLMService, mock_analyzer: MagicMock, cache: CacheService
    ) -> None:
        """캐시된 요약을 반환한다."""
        # 먼저 캐시에 저장
        mock_analyzer.summarize_posts.return_value = "Summary"
        posts = [{"title": "Post 1"}]

        result1 = await service.get_summary("python", posts)
        result2 = await service.get_summary("python", posts)

        # 두 번째 호출은 캐시에서 가져옴
        assert result2.cached is True
        assert mock_analyzer.summarize_posts.call_count == 1

    @pytest.mark.asyncio
    async def test_summary_empty_posts(
        self, service: LLMService, mock_analyzer: MagicMock
    ) -> None:
        """빈 게시물 목록은 기본 메시지를 반환한다."""
        result = await service.get_summary("python", [])

        assert "게시물이 없습니다" in result.summary
        mock_analyzer.summarize_posts.assert_not_called()

    @pytest.mark.asyncio
    async def test_summary_unconfigured(self, unconfigured_service: LLMService) -> None:
        """설정되지 않은 서비스는 경고 메시지를 반환한다."""
        result = await unconfigured_service.get_summary("python", [{"title": "Post"}])

        assert "설정되지 않았습니다" in result.summary

    @pytest.mark.asyncio
    async def test_summary_bypass_cache(
        self, service: LLMService, mock_analyzer: MagicMock
    ) -> None:
        """use_cache=False로 캐시를 우회한다."""
        mock_analyzer.summarize_posts.return_value = "Summary"
        posts = [{"title": "Post 1"}]

        await service.get_summary("python", posts, use_cache=True)
        await service.get_summary("python", posts, use_cache=False)

        # 캐시를 우회했으므로 두 번 호출됨
        assert mock_analyzer.summarize_posts.call_count == 2


class TestGetAICategorization:
    """get_ai_categorization 메서드 테스트."""

    @pytest.mark.asyncio
    async def test_categorization_success(
        self, service: LLMService, mock_analyzer: MagicMock
    ) -> None:
        """카테고리화가 성공한다."""
        mock_analyzer.categorize_content.return_value = [
            CategoryResult(
                text="Text 1",
                category="Feature Request",
                confidence=85,
                reason="사용자 요청",
            ),
            CategoryResult(
                text="Text 2",
                category="Bug Report",
                confidence=90,
            ),
        ]

        result = await service.get_ai_categorization(["Text 1", "Text 2"])

        assert len(result) == 2
        assert isinstance(result[0], LLMCategoryView)
        assert result[0].category == "Feature Request"
        assert result[0].confidence == 85

    @pytest.mark.asyncio
    async def test_categorization_empty_texts(self, service: LLMService) -> None:
        """빈 텍스트 목록은 빈 결과를 반환한다."""
        result = await service.get_ai_categorization([])

        assert result == []

    @pytest.mark.asyncio
    async def test_categorization_unconfigured(
        self, unconfigured_service: LLMService
    ) -> None:
        """설정되지 않은 서비스는 기본값을 반환한다."""
        result = await unconfigured_service.get_ai_categorization(["Some text"])

        assert len(result) == 1
        assert result[0].category == "Uncategorized"
        assert result[0].confidence == 0

    @pytest.mark.asyncio
    async def test_categorize_single(
        self, service: LLMService, mock_analyzer: MagicMock
    ) -> None:
        """categorize_single 편의 메서드가 작동한다."""
        mock_analyzer.categorize_content.return_value = [
            CategoryResult(text="Text", category="Discussion", confidence=80)
        ]

        result = await service.categorize_single("Text")

        assert isinstance(result, LLMCategoryView)
        assert result.category == "Discussion"


class TestGetDeepSentiment:
    """get_deep_sentiment 메서드 테스트."""

    @pytest.mark.asyncio
    async def test_sentiment_success(
        self, service: LLMService, mock_analyzer: MagicMock
    ) -> None:
        """감성 분석이 성공한다."""
        mock_analyzer.analyze_sentiment_deep.return_value = DeepSentimentResult(
            overall_sentiment="positive",
            sentiment_score=0.85,
            factors=[
                SentimentAspect(aspect="quality", sentiment="positive", reason="Good")
            ],
            emotions=["satisfaction"],
            is_opinion=True,
            user_needs=["keep it up"],
            pain_points=[],
        )

        result = await service.get_deep_sentiment("Great product!")

        assert isinstance(result, LLMSentimentView)
        assert result.sentiment == "positive"
        assert result.score == 0.85
        assert len(result.factors) == 1
        assert "satisfaction" in result.emotions

    @pytest.mark.asyncio
    async def test_sentiment_empty_text(self, service: LLMService) -> None:
        """빈 텍스트는 중립 감성을 반환한다."""
        result = await service.get_deep_sentiment("")

        assert result.sentiment == "neutral"
        assert result.score == 0.0

    @pytest.mark.asyncio
    async def test_sentiment_unconfigured(
        self, unconfigured_service: LLMService
    ) -> None:
        """설정되지 않은 서비스는 unknown을 반환한다."""
        result = await unconfigured_service.get_deep_sentiment("Some text")

        assert result.sentiment == "unknown"


class TestGetInsights:
    """get_insights 메서드 테스트."""

    @pytest.mark.asyncio
    async def test_insights_success(
        self, service: LLMService, mock_analyzer: MagicMock
    ) -> None:
        """인사이트 생성이 성공한다."""
        mock_analyzer.generate_insights.return_value = [
            Insight(
                title="가격 민감도",
                finding="가격 불만 증가",
                meaning="경쟁력 약화",
                recommendation="가격 검토",
                priority="high",
            ),
        ]

        result = await service.get_insights(
            {"trends": {"rising": ["price"]}},
            subreddit="test",
        )

        assert len(result) == 1
        assert isinstance(result[0], LLMInsightView)
        assert result[0].title == "가격 민감도"
        assert result[0].priority == "high"

    @pytest.mark.asyncio
    async def test_insights_uses_cache(
        self, service: LLMService, mock_analyzer: MagicMock
    ) -> None:
        """캐시된 인사이트를 반환한다."""
        mock_analyzer.generate_insights.return_value = [
            Insight(title="Test", finding="F", meaning="M", recommendation="R")
        ]

        await service.get_insights({"data": "test"}, subreddit="python")
        await service.get_insights({"data": "test"}, subreddit="python")

        # 캐시로 인해 한 번만 호출됨
        assert mock_analyzer.generate_insights.call_count == 1

    @pytest.mark.asyncio
    async def test_insights_empty_data(self, service: LLMService) -> None:
        """빈 데이터는 빈 인사이트를 반환한다."""
        result = await service.get_insights({})

        assert result == []

    @pytest.mark.asyncio
    async def test_insights_unconfigured(
        self, unconfigured_service: LLMService
    ) -> None:
        """설정되지 않은 서비스는 빈 결과를 반환한다."""
        result = await unconfigured_service.get_insights({"data": "test"})

        assert result == []


class TestInterpretTrends:
    """interpret_trends 메서드 테스트."""

    @pytest.mark.asyncio
    async def test_interpret_success(
        self, service: LLMService, mock_analyzer: MagicMock
    ) -> None:
        """트렌드 해석이 성공한다."""
        mock_analyzer.interpret_trends.return_value = "### 트렌드 요약\n1. AI 급증"

        result = await service.interpret_trends(
            trend_data={"keyword_counts": {"ai": 100}},
            rising_keywords=["ai"],
            declining_keywords=["legacy"],
            target="r/python",
        )

        assert "트렌드 요약" in result

    @pytest.mark.asyncio
    async def test_interpret_unconfigured(
        self, unconfigured_service: LLMService
    ) -> None:
        """설정되지 않은 서비스는 경고 메시지를 반환한다."""
        result = await unconfigured_service.interpret_trends(
            trend_data={},
            rising_keywords=[],
            declining_keywords=[],
        )

        assert "설정되지 않았습니다" in result


class TestGetStatus:
    """get_status 메서드 테스트."""

    def test_status_configured(self, service: LLMService) -> None:
        """설정된 서비스의 상태를 반환한다."""
        status = service.get_status()

        assert status["configured"] is True
        assert "cache_stats" in status

    def test_status_unconfigured(self, unconfigured_service: LLMService) -> None:
        """설정되지 않은 서비스의 상태를 반환한다."""
        status = unconfigured_service.get_status()

        assert status["configured"] is False


class TestSingletonFactory:
    """싱글톤 팩토리 함수 테스트."""

    def test_get_llm_service_without_api_key(self) -> None:
        """API 키 없이 호출하면 비활성화 상태의 서비스를 반환한다."""
        reset_llm_service()

        with patch("reddit_insight.config.get_settings") as mock:
            mock.return_value.anthropic_api_key = None
            mock.return_value.openai_api_key = None

            service = get_llm_service()

            assert service.is_configured is False

        reset_llm_service()

    def test_get_llm_service_with_anthropic_key(self) -> None:
        """Anthropic API 키가 있으면 Claude 클라이언트로 초기화한다."""
        reset_llm_service()

        with patch("reddit_insight.config.get_settings") as mock_settings:
            with patch("reddit_insight.llm.get_llm_client") as mock_client:
                mock_settings.return_value.anthropic_api_key = "test-key"
                mock_settings.return_value.openai_api_key = None
                mock_client.return_value = MagicMock()

                service = get_llm_service()

                assert service.is_configured is True
                mock_client.assert_called_with(provider="claude")

        reset_llm_service()

    def test_reset_llm_service(self) -> None:
        """reset_llm_service로 싱글톤을 리셋한다."""
        reset_llm_service()

        with patch("reddit_insight.config.get_settings") as mock:
            mock.return_value.anthropic_api_key = None
            mock.return_value.openai_api_key = None

            service1 = get_llm_service()
            reset_llm_service()
            service2 = get_llm_service()

            # 리셋 후 새 인스턴스 생성됨
            assert service1 is not service2

        reset_llm_service()


class TestViewDataClasses:
    """뷰 모델 데이터클래스 테스트."""

    def test_category_view_from_result(self) -> None:
        """CategoryResult에서 LLMCategoryView를 생성한다."""
        result = CategoryResult(
            text="Some text",
            category="Feature Request",
            confidence=85,
            reason="User request",
            secondary_categories=[{"category": "Suggestion", "confidence": 60}],
        )

        view = LLMCategoryView.from_result(result)

        assert view.text == "Some text"
        assert view.category == "Feature Request"
        assert view.confidence == 85
        assert view.reason == "User request"
        assert len(view.secondary) == 1

    def test_sentiment_view_from_result(self) -> None:
        """DeepSentimentResult에서 LLMSentimentView를 생성한다."""
        result = DeepSentimentResult(
            overall_sentiment="positive",
            sentiment_score=0.8,
            factors=[
                SentimentAspect(aspect="quality", sentiment="positive", reason="Good")
            ],
            emotions=["joy"],
            is_opinion=True,
            user_needs=["more features"],
            pain_points=["slow loading"],
        )

        view = LLMSentimentView.from_result(result)

        assert view.sentiment == "positive"
        assert view.score == 0.8
        assert len(view.factors) == 1
        assert view.factors[0]["aspect"] == "quality"

    def test_insight_view_from_result(self) -> None:
        """Insight에서 LLMInsightView를 생성한다."""
        insight = Insight(
            title="Price Sensitivity",
            finding="Price complaints increasing",
            meaning="Competitiveness issue",
            recommendation="Review pricing",
            priority="high",
        )

        view = LLMInsightView.from_result(insight)

        assert view.title == "Price Sensitivity"
        assert view.priority == "high"
