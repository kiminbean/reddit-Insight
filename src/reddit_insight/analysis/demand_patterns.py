"""
Demand pattern detection module.

수요 표현 패턴을 정의하고 감지하기 위한 모듈.
"이거 있으면 좋겠다" 류의 미충족 수요를 텍스트에서 자동 추출한다.

Example:
    >>> from reddit_insight.analysis.demand_patterns import (
    ...     DemandPatternLibrary, DemandCategory
    ... )
    >>> library = DemandPatternLibrary.create_english_library()
    >>> patterns = library.get_patterns(DemandCategory.FEATURE_REQUEST)
    >>> print(f"Feature request patterns: {len(patterns)}")
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum


class DemandCategory(Enum):
    """
    수요 표현 카테고리.

    미충족 수요를 5가지 유형으로 분류한다.

    Attributes:
        FEATURE_REQUEST: 기능 요청 ("I wish there was...")
        PAIN_POINT: 불만/문제점 ("Frustrated with...")
        SEARCH_QUERY: 검색/탐색 ("Looking for...", "Does anyone know...")
        WILLINGNESS_TO_PAY: 구매 의향 ("I'd pay for...")
        ALTERNATIVE_SEEKING: 대안 탐색 ("Is there anything like...")
    """

    FEATURE_REQUEST = "feature_request"
    PAIN_POINT = "pain_point"
    SEARCH_QUERY = "search_query"
    WILLINGNESS_TO_PAY = "willingness_to_pay"
    ALTERNATIVE_SEEKING = "alternative_seeking"

    @property
    def description(self) -> str:
        """Get human-readable description for the category."""
        descriptions = {
            DemandCategory.FEATURE_REQUEST: "Feature request or wish",
            DemandCategory.PAIN_POINT: "Pain point or frustration",
            DemandCategory.SEARCH_QUERY: "Search or recommendation query",
            DemandCategory.WILLINGNESS_TO_PAY: "Willingness to pay",
            DemandCategory.ALTERNATIVE_SEEKING: "Alternative or replacement seeking",
        }
        return descriptions.get(self, "Unknown category")


@dataclass
class DemandPattern:
    """
    수요 표현 패턴 정의.

    정규식과 키워드를 사용하여 특정 유형의 수요 표현을 탐지한다.

    Attributes:
        pattern_id: 고유 패턴 식별자
        category: 수요 카테고리
        regex_pattern: 정규식 패턴 문자열
        keywords: 트리거 키워드 목록
        language: 언어 코드 (기본값: "en")
        weight: 중요도 가중치 (기본값: 1.0)
        examples: 예시 문장 목록

    Example:
        >>> pattern = DemandPattern(
        ...     pattern_id="en_wish_001",
        ...     category=DemandCategory.FEATURE_REQUEST,
        ...     regex_pattern=r"i wish (?:there was|someone would)",
        ...     keywords=["wish", "there was"],
        ...     examples=["I wish there was a better tool for this"]
        ... )
    """

    pattern_id: str
    category: DemandCategory
    regex_pattern: str
    keywords: list[str] = field(default_factory=list)
    language: str = "en"
    weight: float = 1.0
    examples: list[str] = field(default_factory=list)

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"DemandPattern(id='{self.pattern_id}', "
            f"category={self.category.value}, weight={self.weight})"
        )


@dataclass
class DemandMatch:
    """
    수요 패턴 매칭 결과.

    텍스트에서 수요 패턴이 매칭된 결과를 저장한다.

    Attributes:
        pattern: 매칭된 패턴
        text: 원본 텍스트
        matched_span: 매칭된 텍스트의 시작/끝 위치 (start, end)
        context: 매칭 주변 텍스트
        confidence: 매칭 신뢰도 (0-1)

    Example:
        >>> match = DemandMatch(
        ...     pattern=pattern,
        ...     text="I wish there was a better way to do this",
        ...     matched_span=(0, 17),
        ...     context="I wish there was a better way to do this",
        ...     confidence=0.95
        ... )
    """

    pattern: DemandPattern
    text: str
    matched_span: tuple[int, int]
    context: str
    confidence: float

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"DemandMatch(pattern='{self.pattern.pattern_id}', "
            f"span={self.matched_span}, confidence={self.confidence:.2f})"
        )

    @property
    def matched_text(self) -> str:
        """Get the matched portion of text."""
        start, end = self.matched_span
        return self.text[start:end]

    @property
    def category(self) -> DemandCategory:
        """Get the category of the matched pattern."""
        return self.pattern.category
