"""LLM API 클라이언트 모듈.

Claude(Anthropic)와 OpenAI API 클라이언트를 제공한다.
추상 베이스 클래스(LLMClient)를 통해 일관된 인터페이스를 보장한다.
"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from reddit_insight.llm.cache import LLMCache
    from reddit_insight.llm.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """LLM API 관련 기본 예외."""

    pass


class LLMRateLimitError(LLMError):
    """Rate limit 초과 시 발생하는 예외."""

    def __init__(self, message: str, retry_after: float | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class LLMClient(ABC):
    """LLM API 클라이언트 추상 베이스 클래스.

    모든 LLM 클라이언트는 이 클래스를 상속받아야 한다.
    """

    def __init__(
        self,
        api_key: str,
        model: str,
        rate_limiter: RateLimiter | None = None,
        cache: LLMCache | None = None,
    ) -> None:
        """LLM 클라이언트를 초기화한다.

        Args:
            api_key: API 키
            model: 사용할 모델 이름
            rate_limiter: Rate limiter 인스턴스 (선택)
            cache: 캐시 인스턴스 (선택)
        """
        self.api_key = api_key
        self.model = model
        self.rate_limiter = rate_limiter
        self.cache = cache

    @abstractmethod
    async def _call_api(
        self,
        prompt: str,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> str:
        """실제 API 호출을 수행한다.

        Args:
            prompt: 입력 프롬프트
            max_tokens: 최대 토큰 수
            temperature: 창의성 조절 (0-1)
            **kwargs: 추가 파라미터

        Returns:
            생성된 텍스트

        Raises:
            LLMError: API 호출 실패 시
        """
        ...

    async def complete(
        self,
        prompt: str,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        use_cache: bool = True,
        **kwargs: Any,
    ) -> str:
        """프롬프트에 대한 완성을 생성한다.

        Rate limiting과 캐싱을 자동으로 적용한다.

        Args:
            prompt: 입력 프롬프트
            max_tokens: 최대 토큰 수
            temperature: 창의성 조절 (0-1)
            use_cache: 캐시 사용 여부
            **kwargs: 추가 파라미터

        Returns:
            생성된 텍스트

        Raises:
            LLMError: API 호출 실패 시
            LLMRateLimitError: Rate limit 초과 시
        """
        # 캐시 확인
        if use_cache and self.cache is not None:
            cached = self.cache.get(prompt, self.model)
            if cached is not None:
                logger.debug("Cache hit for prompt (hash: %s)", hash(prompt) % 10000)
                return cached

        # Rate limiting
        if self.rate_limiter is not None:
            estimated_tokens = self.rate_limiter.estimate_tokens(prompt) + max_tokens
            await self.rate_limiter.acquire(estimated_tokens)

        # API 호출
        result = await self._call_api(
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs,
        )

        # 캐시 저장
        if use_cache and self.cache is not None:
            self.cache.set(prompt, self.model, result)

        return result

    async def complete_with_retry(
        self,
        prompt: str,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        use_cache: bool = True,
        **kwargs: Any,
    ) -> str:
        """재시도 로직이 포함된 완성을 생성한다.

        지수 백오프(exponential backoff)를 사용하여 재시도한다.

        Args:
            prompt: 입력 프롬프트
            max_retries: 최대 재시도 횟수
            initial_delay: 초기 대기 시간 (초)
            max_tokens: 최대 토큰 수
            temperature: 창의성 조절 (0-1)
            use_cache: 캐시 사용 여부
            **kwargs: 추가 파라미터

        Returns:
            생성된 텍스트

        Raises:
            LLMError: 모든 재시도 실패 시
        """
        last_error: LLMError | None = None
        delay = initial_delay

        for attempt in range(max_retries + 1):
            try:
                return await self.complete(
                    prompt=prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    use_cache=use_cache,
                    **kwargs,
                )
            except LLMRateLimitError as e:
                last_error = e
                wait_time = e.retry_after if e.retry_after else delay
                logger.warning(
                    "Rate limit hit, waiting %.1fs (attempt %d/%d)",
                    wait_time,
                    attempt + 1,
                    max_retries + 1,
                )
                await asyncio.sleep(wait_time)
                delay *= 2  # Exponential backoff
            except LLMError as e:
                last_error = e
                if attempt < max_retries:
                    logger.warning(
                        "API error: %s, retrying in %.1fs (attempt %d/%d)",
                        str(e),
                        delay,
                        attempt + 1,
                        max_retries + 1,
                    )
                    await asyncio.sleep(delay)
                    delay *= 2

        error_msg = f"All {max_retries + 1} attempts failed"
        if last_error:
            error_msg += f": {last_error}"
        raise LLMError(error_msg)


class ClaudeClient(LLMClient):
    """Anthropic Claude API 클라이언트.

    Claude 3 모델을 사용한 텍스트 생성을 지원한다.
    """

    DEFAULT_MODEL = "claude-3-haiku-20240307"

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_MODEL,
        rate_limiter: RateLimiter | None = None,
        cache: LLMCache | None = None,
    ) -> None:
        """Claude 클라이언트를 초기화한다.

        Args:
            api_key: Anthropic API 키
            model: 사용할 Claude 모델 (기본: claude-3-haiku-20240307)
            rate_limiter: Rate limiter 인스턴스 (선택)
            cache: 캐시 인스턴스 (선택)
        """
        super().__init__(api_key, model, rate_limiter, cache)
        self._client: Any = None

    def _get_client(self) -> Any:
        """Anthropic 클라이언트 인스턴스를 반환한다 (lazy initialization)."""
        if self._client is None:
            try:
                import anthropic

                self._client = anthropic.Anthropic(api_key=self.api_key)
            except ImportError as e:
                raise LLMError(
                    "anthropic 패키지가 설치되지 않았습니다. "
                    "'pip install anthropic'을 실행하세요."
                ) from e
        return self._client

    async def _call_api(
        self,
        prompt: str,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        system: str | None = None,
        **kwargs: Any,
    ) -> str:
        """Claude API를 호출한다.

        Args:
            prompt: 입력 프롬프트
            max_tokens: 최대 토큰 수
            temperature: 창의성 조절 (0-1)
            system: 시스템 프롬프트 (선택)
            **kwargs: 추가 파라미터

        Returns:
            생성된 텍스트

        Raises:
            LLMError: API 호출 실패 시
            LLMRateLimitError: Rate limit 초과 시
        """
        try:
            import anthropic
        except ImportError as e:
            raise LLMError(
                "anthropic 패키지가 설치되지 않았습니다. "
                "'pip install anthropic'을 실행하세요."
            ) from e

        try:
            client = self._get_client()

            # 동기 클라이언트를 비동기로 실행
            # Anthropic의 동기 API를 사용하고 asyncio.to_thread로 래핑
            def _sync_call() -> str:
                create_kwargs: dict[str, Any] = {
                    "model": self.model,
                    "max_tokens": max_tokens,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": temperature,
                }

                if system:
                    create_kwargs["system"] = system

                message = client.messages.create(**create_kwargs)
                return message.content[0].text  # type: ignore[return-value]

            result = await asyncio.to_thread(_sync_call)
            logger.debug("Claude API call successful (model: %s)", self.model)
            return result

        except anthropic.RateLimitError as e:
            logger.warning("Claude rate limit exceeded: %s", str(e))
            # Anthropic API에서 retry-after 헤더를 제공하면 사용
            raise LLMRateLimitError(str(e), retry_after=60.0) from e
        except anthropic.APIError as e:
            logger.error("Claude API error: %s", str(e))
            raise LLMError(f"Claude API error: {e}") from e
        except LLMError:
            raise
        except Exception as e:
            logger.error("Unexpected error calling Claude API: %s", str(e))
            raise LLMError(f"Unexpected error: {e}") from e


class OpenAIClient(LLMClient):
    """OpenAI API 클라이언트.

    GPT 모델을 사용한 텍스트 생성을 지원한다.
    Claude API의 백업으로 사용된다.
    """

    DEFAULT_MODEL = "gpt-4o-mini"

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_MODEL,
        rate_limiter: RateLimiter | None = None,
        cache: LLMCache | None = None,
    ) -> None:
        """OpenAI 클라이언트를 초기화한다.

        Args:
            api_key: OpenAI API 키
            model: 사용할 GPT 모델 (기본: gpt-4o-mini)
            rate_limiter: Rate limiter 인스턴스 (선택)
            cache: 캐시 인스턴스 (선택)
        """
        super().__init__(api_key, model, rate_limiter, cache)
        self._client: Any = None

    def _get_client(self) -> Any:
        """OpenAI 클라이언트 인스턴스를 반환한다 (lazy initialization)."""
        if self._client is None:
            try:
                import openai

                self._client = openai.OpenAI(api_key=self.api_key)
            except ImportError as e:
                raise LLMError(
                    "openai 패키지가 설치되지 않았습니다. "
                    "'pip install openai'를 실행하세요."
                ) from e
        return self._client

    async def _call_api(
        self,
        prompt: str,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        system: str | None = None,
        **kwargs: Any,
    ) -> str:
        """OpenAI API를 호출한다.

        Args:
            prompt: 입력 프롬프트
            max_tokens: 최대 토큰 수
            temperature: 창의성 조절 (0-1)
            system: 시스템 프롬프트 (선택)
            **kwargs: 추가 파라미터

        Returns:
            생성된 텍스트

        Raises:
            LLMError: API 호출 실패 시
            LLMRateLimitError: Rate limit 초과 시
        """
        try:
            import openai
        except ImportError as e:
            raise LLMError(
                "openai 패키지가 설치되지 않았습니다. "
                "'pip install openai'를 실행하세요."
            ) from e

        try:
            client = self._get_client()

            # 동기 클라이언트를 비동기로 실행
            def _sync_call() -> str:
                messages: list[dict[str, str]] = []

                if system:
                    messages.append({"role": "system", "content": system})

                messages.append({"role": "user", "content": prompt})

                response = client.chat.completions.create(
                    model=self.model,
                    messages=messages,  # type: ignore[arg-type]
                    max_tokens=max_tokens,
                    temperature=temperature,
                )

                content = response.choices[0].message.content
                return content if content else ""

            result = await asyncio.to_thread(_sync_call)
            logger.debug("OpenAI API call successful (model: %s)", self.model)
            return result

        except openai.RateLimitError as e:
            logger.warning("OpenAI rate limit exceeded: %s", str(e))
            raise LLMRateLimitError(str(e), retry_after=60.0) from e
        except openai.APIError as e:
            logger.error("OpenAI API error: %s", str(e))
            raise LLMError(f"OpenAI API error: {e}") from e
        except LLMError:
            raise
        except Exception as e:
            logger.error("Unexpected error calling OpenAI API: %s", str(e))
            raise LLMError(f"Unexpected error: {e}") from e


def get_llm_client(
    provider: Literal["claude", "openai"] = "claude",
    api_key: str | None = None,
    model: str | None = None,
    rate_limiter: RateLimiter | None = None,
    cache: LLMCache | None = None,
) -> LLMClient:
    """설정에 따라 적절한 LLM 클라이언트를 반환한다.

    Args:
        provider: LLM 제공자 ("claude" 또는 "openai")
        api_key: API 키 (None이면 환경변수에서 로드)
        model: 사용할 모델 (None이면 기본값 사용)
        rate_limiter: Rate limiter 인스턴스 (선택)
        cache: 캐시 인스턴스 (선택)

    Returns:
        LLMClient 인스턴스

    Raises:
        ValueError: 지원하지 않는 provider이거나 API 키가 없는 경우
    """
    from reddit_insight.config import get_settings

    settings = get_settings()

    if provider == "claude":
        key = api_key or settings.anthropic_api_key
        if not key:
            raise ValueError(
                "Anthropic API 키가 필요합니다. "
                "REDDIT_INSIGHT_ANTHROPIC_API_KEY 환경변수를 설정하세요."
            )
        return ClaudeClient(
            api_key=key,
            model=model or settings.llm_model or ClaudeClient.DEFAULT_MODEL,
            rate_limiter=rate_limiter,
            cache=cache,
        )
    elif provider == "openai":
        key = api_key or settings.openai_api_key
        if not key:
            raise ValueError(
                "OpenAI API 키가 필요합니다. "
                "REDDIT_INSIGHT_OPENAI_API_KEY 환경변수를 설정하세요."
            )
        return OpenAIClient(
            api_key=key,
            model=model or settings.llm_model or OpenAIClient.DEFAULT_MODEL,
            rate_limiter=rate_limiter,
            cache=cache,
        )
    else:
        raise ValueError(f"지원하지 않는 LLM provider: {provider}")
