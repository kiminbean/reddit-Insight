"""Reddit API 인증 모듈.

Reddit OAuth2 인증을 위한 자격증명 관리 및 유효성 검사.
실제 인증 연결은 client.py에서 PRAW를 통해 수행된다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# User Agent 형식 검증용 정규표현식
# 형식: <platform>:<app_id>:<version> (by /u/<username>)
USER_AGENT_PATTERN = re.compile(
    r"^[\w]+:[\w\-]+:[\d]+\.[\d]+\.[\d]+( \(by /u/[\w\-]+\))?$"
)

# 기본 User Agent
DEFAULT_USER_AGENT = "python:reddit-insight:0.1.0 (by /u/reddit_insight_bot)"


class AuthenticationError(Exception):
    """Reddit 인증 실패 예외.

    자격증명이 유효하지 않거나 인증에 실패했을 때 발생한다.
    """

    pass


@dataclass
class RedditAuth:
    """Reddit API 자격증명 관리자.

    OAuth2 인증에 필요한 자격증명을 저장하고 유효성을 검사한다.

    Attributes:
        client_id: Reddit 앱 Client ID
        client_secret: Reddit 앱 Client Secret
        user_agent: API 요청 시 사용할 User-Agent 문자열

    Example:
        >>> auth = RedditAuth(
        ...     client_id="my_client_id",
        ...     client_secret="my_client_secret",
        ...     user_agent="python:myapp:1.0.0"
        ... )
        >>> auth.is_configured
        True
    """

    client_id: str | None
    client_secret: str | None
    user_agent: str = DEFAULT_USER_AGENT

    @property
    def is_configured(self) -> bool:
        """자격증명이 설정되어 있는지 확인.

        Returns:
            bool: client_id와 client_secret이 모두 설정되어 있으면 True
        """
        return bool(self.client_id and self.client_secret)

    def validate(self) -> None:
        """자격증명 유효성 검사.

        Raises:
            AuthenticationError: 자격증명이 유효하지 않은 경우

        Note:
            이 메서드는 형식 검증만 수행한다.
            실제 Reddit API 인증 유효성은 connect() 시점에 확인된다.
        """
        errors: list[str] = []

        if not self.client_id:
            errors.append("client_id가 설정되지 않았습니다")

        if not self.client_secret:
            errors.append("client_secret이 설정되지 않았습니다")

        if not self.user_agent:
            errors.append("user_agent가 설정되지 않았습니다")

        if errors:
            raise AuthenticationError(
                f"Reddit 인증 설정 오류: {'; '.join(errors)}"
            )


def get_user_agent(
    platform: str = "python",
    app_id: str = "reddit-insight",
    version: str = "0.1.0",
    username: str | None = "reddit_insight_bot",
) -> str:
    """표준 형식의 User-Agent 문자열 생성.

    Reddit API는 User-Agent를 통해 앱을 식별하므로,
    고유하고 설명적인 User-Agent 사용이 권장된다.

    Args:
        platform: 플랫폼 이름 (기본: "python")
        app_id: 앱 식별자 (기본: "reddit-insight")
        version: 앱 버전 (기본: "0.1.0")
        username: Reddit 사용자명 (기본: "reddit_insight_bot")

    Returns:
        str: 형식화된 User-Agent 문자열

    Example:
        >>> get_user_agent()
        'python:reddit-insight:0.1.0 (by /u/reddit_insight_bot)'
        >>> get_user_agent(username=None)
        'python:reddit-insight:0.1.0'
    """
    base = f"{platform}:{app_id}:{version}"
    if username:
        return f"{base} (by /u/{username})"
    return base


def validate_user_agent(user_agent: str) -> bool:
    """User-Agent 형식 유효성 검사.

    Args:
        user_agent: 검사할 User-Agent 문자열

    Returns:
        bool: 유효한 형식이면 True
    """
    return bool(USER_AGENT_PATTERN.match(user_agent))
