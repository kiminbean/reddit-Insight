"""설정 관리 모듈.

pydantic-settings 기반의 환경변수 설정 관리 시스템.
모든 설정은 REDDIT_INSIGHT_ 접두사를 가진 환경변수로 오버라이드 가능.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """애플리케이션 설정.

    환경변수 또는 .env 파일에서 설정을 로드한다.
    모든 환경변수는 REDDIT_INSIGHT_ 접두사를 사용한다.

    Example:
        REDDIT_INSIGHT_DEBUG=true
        REDDIT_INSIGHT_LOG_LEVEL=DEBUG
    """

    model_config = SettingsConfigDict(
        env_prefix="REDDIT_INSIGHT_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = Field(
        default="Reddit Insight",
        description="애플리케이션 이름",
    )
    debug: bool = Field(
        default=False,
        description="디버그 모드 활성화",
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="로깅 레벨",
    )

    # Data
    data_dir: Path = Field(
        default=Path("./data"),
        description="데이터 저장 디렉토리",
    )

    # Reddit API (Phase 2에서 사용)
    reddit_client_id: str | None = Field(
        default=None,
        description="Reddit API Client ID",
    )
    reddit_client_secret: str | None = Field(
        default=None,
        description="Reddit API Client Secret",
    )
    reddit_user_agent: str = Field(
        default="RedditInsight/0.1.0",
        description="Reddit API User Agent",
    )

    # Database
    database_url: str = Field(
        default="sqlite:///./data/reddit_insight.db",
        description="데이터베이스 연결 URL",
    )

    # LLM API
    llm_provider: Literal["claude", "openai"] = Field(
        default="claude",
        description="LLM 제공자 (claude 또는 openai)",
    )
    anthropic_api_key: str | None = Field(
        default=None,
        description="Anthropic API 키 (Claude 사용 시 필수)",
    )
    openai_api_key: str | None = Field(
        default=None,
        description="OpenAI API 키 (OpenAI 사용 시 필수)",
    )
    llm_model: str | None = Field(
        default=None,
        description="LLM 모델 이름 (미지정 시 기본값 사용)",
    )
    llm_rate_limit_rpm: int = Field(
        default=60,
        description="LLM API 분당 요청 수 제한",
    )
    llm_rate_limit_tpm: int = Field(
        default=100000,
        description="LLM API 분당 토큰 수 제한",
    )
    llm_cache_ttl: int = Field(
        default=86400,
        description="LLM 응답 캐시 TTL (초, 기본 24시간)",
    )


@lru_cache
def get_settings() -> Settings:
    """설정 인스턴스를 반환한다 (싱글톤 패턴).

    lru_cache로 인해 한 번만 생성되고 이후에는 캐시된 인스턴스를 반환한다.

    Returns:
        Settings: 애플리케이션 설정 인스턴스

    Example:
        >>> settings = get_settings()
        >>> print(settings.app_name)
        Reddit Insight
    """
    return Settings()
