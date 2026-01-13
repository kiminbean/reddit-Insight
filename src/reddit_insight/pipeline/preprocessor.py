"""텍스트 전처리기.

Reddit 텍스트 데이터를 정제하고 정규화하는 기능을 제공한다.
URL 제거, HTML 엔티티 디코딩, Reddit 특수 패턴 처리 등을 포함한다.
"""

from __future__ import annotations

import html
import re
from typing import TypedDict


class MentionDict(TypedDict):
    """멘션 추출 결과 타입."""

    users: list[str]
    subreddits: list[str]


class TextPreprocessor:
    """Reddit 텍스트 전처리기.

    Reddit 게시물 및 댓글의 텍스트를 정제하고 정규화한다.
    URL 제거, 멘션 처리, HTML 엔티티 디코딩 등의 기능을 제공한다.

    Example:
        >>> preprocessor = TextPreprocessor()
        >>> preprocessor.clean_text("Hello &amp; World! https://example.com")
        'Hello & World!'
        >>> preprocessor.is_deleted_content("[deleted]")
        True
    """

    # 삭제된 콘텐츠 패턴
    DELETED_PATTERNS: frozenset[str] = frozenset(
        {"[deleted]", "[removed]", "[deleted by user]"}
    )

    # URL 패턴 (http/https 프로토콜)
    URL_PATTERN: re.Pattern[str] = re.compile(
        r"https?://[^\s<>\[\]\"'()]+",
        re.IGNORECASE,
    )

    # Reddit 사용자 멘션 패턴 (/u/username 또는 u/username)
    USER_MENTION_PATTERN: re.Pattern[str] = re.compile(
        r"/?u/([A-Za-z0-9_-]+)",
        re.IGNORECASE,
    )

    # Reddit 서브레딧 멘션 패턴 (/r/subreddit 또는 r/subreddit)
    SUBREDDIT_MENTION_PATTERN: re.Pattern[str] = re.compile(
        r"/?r/([A-Za-z0-9_]+)",
        re.IGNORECASE,
    )

    # 연속 공백 패턴
    MULTIPLE_SPACES_PATTERN: re.Pattern[str] = re.compile(r"[ \t]+")

    # 연속 줄바꿈 패턴 (3개 이상)
    MULTIPLE_NEWLINES_PATTERN: re.Pattern[str] = re.compile(r"\n{3,}")

    def clean_text(self, text: str) -> str:
        """텍스트 정제.

        다음 작업을 순서대로 수행한다:
        1. HTML 엔티티 디코딩 (&amp; -> &, &lt; -> < 등)
        2. URL 제거
        3. 연속 공백 정규화
        4. 연속 줄바꿈 정규화 (3개 이상 -> 2개)
        5. 앞뒤 공백 제거

        Args:
            text: 원본 텍스트

        Returns:
            정제된 텍스트
        """
        if not text:
            return ""

        # 1. HTML 엔티티 디코딩
        result = html.unescape(text)

        # 2. URL 제거
        result = self.URL_PATTERN.sub("", result)

        # 3. 연속 공백을 단일 공백으로
        result = self.MULTIPLE_SPACES_PATTERN.sub(" ", result)

        # 4. 연속 줄바꿈을 2개로 제한
        result = self.MULTIPLE_NEWLINES_PATTERN.sub("\n\n", result)

        # 5. 앞뒤 공백 제거
        result = result.strip()

        return result

    def is_deleted_content(self, text: str) -> bool:
        """삭제된 콘텐츠 여부 확인.

        Reddit에서 삭제되거나 제거된 콘텐츠를 식별한다.

        Args:
            text: 확인할 텍스트

        Returns:
            삭제된 콘텐츠면 True
        """
        if not text:
            return False

        normalized = text.strip().lower()
        return normalized in {p.lower() for p in self.DELETED_PATTERNS}

    def normalize_author(self, author: str) -> str | None:
        """작성자 이름 정규화.

        삭제된 사용자는 None을 반환하고, 정상 사용자는 원본을 반환한다.

        Args:
            author: 작성자 이름

        Returns:
            정규화된 작성자 이름 또는 None (삭제된 경우)
        """
        if not author:
            return None

        normalized = author.strip().lower()
        if normalized in {"[deleted]", "deleted", "[removed]"}:
            return None

        return author.strip()

    def extract_urls(self, text: str) -> list[str]:
        """텍스트에서 URL 추출.

        HTTP/HTTPS URL을 모두 추출한다.

        Args:
            text: 검색할 텍스트

        Returns:
            추출된 URL 목록
        """
        if not text:
            return []

        return self.URL_PATTERN.findall(text)

    def extract_mentions(self, text: str) -> MentionDict:
        """텍스트에서 멘션 추출.

        Reddit 사용자 멘션(/u/username)과
        서브레딧 멘션(/r/subreddit)을 추출한다.

        Args:
            text: 검색할 텍스트

        Returns:
            {'users': [...], 'subreddits': [...]} 형태의 딕셔너리
        """
        if not text:
            return {"users": [], "subreddits": []}

        users = self.USER_MENTION_PATTERN.findall(text)
        subreddits = self.SUBREDDIT_MENTION_PATTERN.findall(text)

        # 중복 제거 및 소문자 정규화
        unique_users = list(dict.fromkeys(u.lower() for u in users))
        unique_subreddits = list(dict.fromkeys(s.lower() for s in subreddits))

        return {"users": unique_users, "subreddits": unique_subreddits}

    def remove_mentions(self, text: str) -> str:
        """텍스트에서 멘션 제거.

        사용자 및 서브레딧 멘션을 제거한다.

        Args:
            text: 원본 텍스트

        Returns:
            멘션이 제거된 텍스트
        """
        if not text:
            return ""

        result = self.USER_MENTION_PATTERN.sub("", text)
        result = self.SUBREDDIT_MENTION_PATTERN.sub("", result)

        # 정리
        result = self.MULTIPLE_SPACES_PATTERN.sub(" ", result)
        return result.strip()

    def extract_hashtags(self, text: str) -> list[str]:
        """텍스트에서 해시태그 추출.

        Reddit에서는 해시태그가 일반적이지 않지만,
        일부 서브레딧에서 사용되는 경우를 위해 제공한다.

        Args:
            text: 검색할 텍스트

        Returns:
            추출된 해시태그 목록 (# 제외)
        """
        if not text:
            return []

        pattern = re.compile(r"#([A-Za-z0-9_]+)")
        hashtags = pattern.findall(text)

        # 중복 제거 및 소문자 정규화
        return list(dict.fromkeys(h.lower() for h in hashtags))

    def get_text_stats(self, text: str) -> dict[str, int]:
        """텍스트 통계 계산.

        문자 수, 단어 수, 문장 수 등의 기본 통계를 계산한다.

        Args:
            text: 분석할 텍스트

        Returns:
            통계 딕셔너리
        """
        if not text:
            return {
                "char_count": 0,
                "word_count": 0,
                "sentence_count": 0,
                "paragraph_count": 0,
                "url_count": 0,
            }

        # 문장 구분자 패턴
        sentence_pattern = re.compile(r"[.!?]+")

        cleaned = self.clean_text(text)
        words = cleaned.split()
        sentences = [s.strip() for s in sentence_pattern.split(cleaned) if s.strip()]
        paragraphs = [p.strip() for p in cleaned.split("\n\n") if p.strip()]
        urls = self.extract_urls(text)  # 원본 텍스트에서 URL 추출

        return {
            "char_count": len(cleaned),
            "word_count": len(words),
            "sentence_count": max(len(sentences), 1) if cleaned else 0,
            "paragraph_count": max(len(paragraphs), 1) if cleaned else 0,
            "url_count": len(urls),
        }
