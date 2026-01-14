"""LLM 클라이언트 테스트.

Mock을 사용하여 실제 API 호출 없이 테스트한다.
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from reddit_insight.llm import (
    ClaudeClient,
    LLMClient,
    LLMError,
    LLMRateLimitError,
    OpenAIClient,
    RateLimiter,
    LLMCache,
    get_llm_client,
)


class TestLLMClient:
    """LLMClient 추상 클래스 테스트."""

    def test_abstract_class_cannot_be_instantiated(self) -> None:
        """추상 클래스는 직접 인스턴스화할 수 없다."""
        with pytest.raises(TypeError):
            LLMClient(api_key="test", model="test")  # type: ignore[abstract]


class TestClaudeClient:
    """ClaudeClient 테스트."""

    @pytest.fixture
    def mock_anthropic(self) -> MagicMock:
        """Mock Anthropic 클라이언트."""
        with patch("reddit_insight.llm.client.asyncio.to_thread") as mock_to_thread:
            # Mock the async wrapper
            async def async_return(func):
                return func()

            mock_to_thread.side_effect = async_return
            yield mock_to_thread

    @pytest.fixture
    def client(self) -> ClaudeClient:
        """테스트용 Claude 클라이언트."""
        return ClaudeClient(api_key="test-api-key", model="claude-3-haiku-20240307")

    @pytest.mark.asyncio
    async def test_complete_basic(self, client: ClaudeClient) -> None:
        """기본 완성 호출이 작동한다."""
        # Mock _call_api directly to avoid import issues
        with patch.object(
            client, "_call_api", new_callable=AsyncMock
        ) as mock_call_api:
            mock_call_api.return_value = "Test response"

            result = await client.complete("Test prompt")

            assert result == "Test response"
            mock_call_api.assert_called_once()

    @pytest.mark.asyncio
    async def test_complete_with_cache_hit(self, client: ClaudeClient) -> None:
        """캐시 히트 시 API를 호출하지 않는다."""
        cache = LLMCache(ttl=3600)
        cache.set("Test prompt", "claude-3-haiku-20240307", "Cached response")

        client_with_cache = ClaudeClient(
            api_key="test-key",
            model="claude-3-haiku-20240307",
            cache=cache,
        )

        result = await client_with_cache.complete("Test prompt", use_cache=True)

        assert result == "Cached response"

    @pytest.mark.asyncio
    async def test_complete_with_rate_limiter(self, client: ClaudeClient) -> None:
        """Rate limiter가 호출된다."""
        rate_limiter = RateLimiter(requests_per_minute=60, tokens_per_minute=100000)

        with patch.object(rate_limiter, "acquire", new_callable=AsyncMock) as mock_acquire:
            client_with_rl = ClaudeClient(
                api_key="test-key",
                model="claude-3-haiku-20240307",
                rate_limiter=rate_limiter,
            )

            with patch.object(client_with_rl, "_call_api", new_callable=AsyncMock) as mock_call:
                mock_call.return_value = "Response"

                await client_with_rl.complete("Test prompt")

                mock_acquire.assert_called_once()

    @pytest.mark.asyncio
    async def test_complete_with_retry_success(self, client: ClaudeClient) -> None:
        """재시도 후 성공한다."""
        call_count = 0

        async def mock_complete(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise LLMError("Temporary error")
            return "Success after retry"

        with patch.object(client, "complete", side_effect=mock_complete):
            result = await client.complete_with_retry(
                "Test prompt",
                max_retries=3,
                initial_delay=0.01,
            )

            assert result == "Success after retry"
            assert call_count == 2

    @pytest.mark.asyncio
    async def test_complete_with_retry_exhausted(self, client: ClaudeClient) -> None:
        """모든 재시도가 실패하면 예외가 발생한다."""
        with patch.object(
            client, "complete", new_callable=AsyncMock
        ) as mock_complete:
            mock_complete.side_effect = LLMError("Persistent error")

            with pytest.raises(LLMError, match="All 3 attempts failed"):
                await client.complete_with_retry(
                    "Test prompt",
                    max_retries=2,
                    initial_delay=0.01,
                )

    @pytest.mark.asyncio
    async def test_rate_limit_error_retry(self, client: ClaudeClient) -> None:
        """Rate limit 에러 시 retry_after를 사용한다."""
        call_count = 0

        async def mock_complete(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise LLMRateLimitError("Rate limited", retry_after=0.01)
            return "Success"

        with patch.object(client, "complete", side_effect=mock_complete):
            result = await client.complete_with_retry(
                "Test prompt",
                max_retries=3,
                initial_delay=0.01,
            )

            assert result == "Success"

    def test_model_attribute(self, client: ClaudeClient) -> None:
        """모델 속성이 올바르게 설정된다."""
        assert client.model == "claude-3-haiku-20240307"

    def test_default_model(self) -> None:
        """기본 모델이 설정된다."""
        client = ClaudeClient(api_key="test-key")
        assert client.model == ClaudeClient.DEFAULT_MODEL


class TestOpenAIClient:
    """OpenAIClient 테스트."""

    @pytest.fixture
    def client(self) -> OpenAIClient:
        """테스트용 OpenAI 클라이언트."""
        return OpenAIClient(api_key="test-api-key", model="gpt-4o-mini")

    @pytest.mark.asyncio
    async def test_complete_basic(self, client: OpenAIClient) -> None:
        """기본 완성 호출이 작동한다."""
        with patch.object(client, "_get_client") as mock_get:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_choice = MagicMock()
            mock_choice.message.content = "Test response"
            mock_response.choices = [mock_choice]
            mock_client.chat.completions.create.return_value = mock_response
            mock_get.return_value = mock_client

            with patch("reddit_insight.llm.client.asyncio.to_thread") as mock_thread:
                async def run_sync(func):
                    return func()

                mock_thread.side_effect = run_sync

                result = await client.complete("Test prompt")

                assert result == "Test response"

    def test_model_attribute(self, client: OpenAIClient) -> None:
        """모델 속성이 올바르게 설정된다."""
        assert client.model == "gpt-4o-mini"

    def test_default_model(self) -> None:
        """기본 모델이 설정된다."""
        client = OpenAIClient(api_key="test-key")
        assert client.model == OpenAIClient.DEFAULT_MODEL


class TestGetLLMClient:
    """get_llm_client 팩토리 함수 테스트."""

    def test_get_claude_client(self) -> None:
        """Claude 클라이언트를 생성한다."""
        with patch("reddit_insight.config.get_settings") as mock_settings:
            mock_settings.return_value.anthropic_api_key = "test-key"
            mock_settings.return_value.llm_model = None

            client = get_llm_client(provider="claude")

            assert isinstance(client, ClaudeClient)

    def test_get_openai_client(self) -> None:
        """OpenAI 클라이언트를 생성한다."""
        with patch("reddit_insight.config.get_settings") as mock_settings:
            mock_settings.return_value.openai_api_key = "test-key"
            mock_settings.return_value.llm_model = None

            client = get_llm_client(provider="openai")

            assert isinstance(client, OpenAIClient)

    def test_missing_api_key_raises_error(self) -> None:
        """API 키가 없으면 에러가 발생한다."""
        with patch("reddit_insight.config.get_settings") as mock_settings:
            mock_settings.return_value.anthropic_api_key = None
            mock_settings.return_value.openai_api_key = None

            with pytest.raises(ValueError, match="API 키가 필요합니다"):
                get_llm_client(provider="claude")

    def test_unsupported_provider_raises_error(self) -> None:
        """지원하지 않는 provider는 에러가 발생한다."""
        with pytest.raises(ValueError, match="지원하지 않는 LLM provider"):
            get_llm_client(provider="unknown")  # type: ignore[arg-type]

    def test_custom_api_key_and_model(self) -> None:
        """커스텀 API 키와 모델을 사용한다."""
        with patch("reddit_insight.config.get_settings") as mock_settings:
            mock_settings.return_value.llm_model = None

            client = get_llm_client(
                provider="claude",
                api_key="custom-key",
                model="claude-3-opus-20240229",
            )

            assert isinstance(client, ClaudeClient)
            assert client.model == "claude-3-opus-20240229"
            assert client.api_key == "custom-key"


class TestLLMErrors:
    """LLM 예외 클래스 테스트."""

    def test_llm_error(self) -> None:
        """LLMError가 올바르게 생성된다."""
        error = LLMError("Test error")
        assert str(error) == "Test error"

    def test_llm_rate_limit_error(self) -> None:
        """LLMRateLimitError가 올바르게 생성된다."""
        error = LLMRateLimitError("Rate limited", retry_after=30.0)
        assert str(error) == "Rate limited"
        assert error.retry_after == 30.0

    def test_llm_rate_limit_error_no_retry_after(self) -> None:
        """LLMRateLimitError가 retry_after 없이 생성된다."""
        error = LLMRateLimitError("Rate limited")
        assert error.retry_after is None
