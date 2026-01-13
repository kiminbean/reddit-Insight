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


# =============================================================================
# ENGLISH PATTERNS
# =============================================================================

ENGLISH_PATTERNS: list[DemandPattern] = [
    # -------------------------------------------------------------------------
    # FEATURE_REQUEST patterns (weight: 1.0)
    # -------------------------------------------------------------------------
    DemandPattern(
        pattern_id="en_feature_wish",
        category=DemandCategory.FEATURE_REQUEST,
        regex_pattern=r"i wish (?:there was|someone would|we had|i could)",
        keywords=["wish", "there was", "someone would"],
        language="en",
        weight=1.0,
        examples=[
            "I wish there was a better way to organize my files",
            "I wish someone would make an app for this",
            "I wish we had a tool that could do this automatically",
        ],
    ),
    DemandPattern(
        pattern_id="en_feature_would_be",
        category=DemandCategory.FEATURE_REQUEST,
        regex_pattern=r"(?:would|it'?d) (?:be (?:great|nice|awesome|cool)|love) (?:to see|if|to have)",
        keywords=["would be great", "would love", "would be nice"],
        language="en",
        weight=1.0,
        examples=[
            "Would be great to see this feature added",
            "It'd be nice if we could customize this",
            "Would love to have a dark mode option",
        ],
    ),
    DemandPattern(
        pattern_id="en_feature_need",
        category=DemandCategory.FEATURE_REQUEST,
        regex_pattern=r"(?:we|i|really) need (?:a|an|something|some kind of)",
        keywords=["need", "really need"],
        language="en",
        weight=0.9,
        examples=[
            "We need a better solution for this",
            "I really need something that works offline",
            "We need some kind of integration with Slack",
        ],
    ),
    DemandPattern(
        pattern_id="en_feature_why_no",
        category=DemandCategory.FEATURE_REQUEST,
        regex_pattern=r"why (?:isn't|is there no|doesn't|can't) (?:there|it|this)",
        keywords=["why isn't", "why is there no", "why doesn't"],
        language="en",
        weight=0.9,
        examples=[
            "Why isn't there an option for this?",
            "Why is there no dark mode?",
            "Why doesn't this support export to PDF?",
        ],
    ),
    # -------------------------------------------------------------------------
    # PAIN_POINT patterns (weight: 0.9)
    # -------------------------------------------------------------------------
    DemandPattern(
        pattern_id="en_pain_frustrated",
        category=DemandCategory.PAIN_POINT,
        regex_pattern=r"(?:so |really |very )?frustrated (?:with|by|that|when)",
        keywords=["frustrated", "frustrating"],
        language="en",
        weight=0.9,
        examples=[
            "So frustrated with this app's constant crashes",
            "Really frustrated that there's no way to export data",
            "Frustrated when it takes forever to load",
        ],
    ),
    DemandPattern(
        pattern_id="en_pain_annoying",
        category=DemandCategory.PAIN_POINT,
        regex_pattern=r"(?:so |really |very )?annoying (?:that|when|how)",
        keywords=["annoying", "annoys me"],
        language="en",
        weight=0.85,
        examples=[
            "So annoying that I have to do this manually",
            "Really annoying when the app crashes randomly",
            "Annoying how there's no undo button",
        ],
    ),
    DemandPattern(
        pattern_id="en_pain_hate",
        category=DemandCategory.PAIN_POINT,
        regex_pattern=r"(?:i )?(?:hate|can't stand) (?:how|when|that|it when)",
        keywords=["hate", "can't stand"],
        language="en",
        weight=0.85,
        examples=[
            "I hate how slow this is",
            "Can't stand when it freezes",
            "Hate that there's no offline mode",
        ],
    ),
    DemandPattern(
        pattern_id="en_pain_why_cant",
        category=DemandCategory.PAIN_POINT,
        regex_pattern=r"why (?:can't|won't|doesn't) (?:it|this|the app)",
        keywords=["why can't", "why won't", "why doesn't"],
        language="en",
        weight=0.8,
        examples=[
            "Why can't this just work properly?",
            "Why won't it remember my settings?",
            "Why doesn't the app sync automatically?",
        ],
    ),
    # -------------------------------------------------------------------------
    # SEARCH_QUERY patterns (weight: 0.95)
    # -------------------------------------------------------------------------
    DemandPattern(
        pattern_id="en_search_looking",
        category=DemandCategory.SEARCH_QUERY,
        regex_pattern=r"(?:i'm |i am )?(?:looking|searching) for (?:a|an|something|any)",
        keywords=["looking for", "searching for"],
        language="en",
        weight=0.95,
        examples=[
            "Looking for a good project management tool",
            "I'm searching for something to help with budgeting",
            "Looking for any recommendations",
        ],
    ),
    DemandPattern(
        pattern_id="en_search_anyone_know",
        category=DemandCategory.SEARCH_QUERY,
        regex_pattern=r"does anyone (?:know (?:of|about|if)|have (?:a|any))",
        keywords=["does anyone know", "does anyone have"],
        language="en",
        weight=0.95,
        examples=[
            "Does anyone know of a good alternative?",
            "Does anyone know about a free tool for this?",
            "Does anyone have any recommendations?",
        ],
    ),
    DemandPattern(
        pattern_id="en_search_is_there",
        category=DemandCategory.SEARCH_QUERY,
        regex_pattern=r"is there (?:a|an|any|anything)",
        keywords=["is there", "is there any"],
        language="en",
        weight=0.9,
        examples=[
            "Is there a tool that can do this?",
            "Is there any app for managing subscriptions?",
            "Is there anything better than X?",
        ],
    ),
    DemandPattern(
        pattern_id="en_search_recommend",
        category=DemandCategory.SEARCH_QUERY,
        regex_pattern=r"(?:can anyone|could someone|anybody) recommend",
        keywords=["recommend", "recommendations"],
        language="en",
        weight=0.95,
        examples=[
            "Can anyone recommend a good note-taking app?",
            "Could someone recommend an alternative?",
            "Anybody recommend something for meal planning?",
        ],
    ),
    DemandPattern(
        pattern_id="en_search_suggestions",
        category=DemandCategory.SEARCH_QUERY,
        regex_pattern=r"(?:any |looking for )?suggestions? (?:for|on|about)",
        keywords=["suggestions", "suggest"],
        language="en",
        weight=0.9,
        examples=[
            "Any suggestions for a password manager?",
            "Looking for suggestions on budgeting apps",
            "Suggestions for a beginner-friendly IDE?",
        ],
    ),
    # -------------------------------------------------------------------------
    # WILLINGNESS_TO_PAY patterns (weight: 1.2)
    # -------------------------------------------------------------------------
    DemandPattern(
        pattern_id="en_pay_would_pay",
        category=DemandCategory.WILLINGNESS_TO_PAY,
        regex_pattern=r"(?:i'?d|i would|would) pay (?:\$?\d+|good money|for)",
        keywords=["would pay", "I'd pay"],
        language="en",
        weight=1.2,
        examples=[
            "I'd pay $50 for this feature",
            "I would pay good money for a working solution",
            "Would pay for a premium version with these features",
        ],
    ),
    DemandPattern(
        pattern_id="en_pay_willing",
        category=DemandCategory.WILLINGNESS_TO_PAY,
        regex_pattern=r"(?:willing|happy|glad) to pay",
        keywords=["willing to pay", "happy to pay"],
        language="en",
        weight=1.2,
        examples=[
            "I'm willing to pay for quality",
            "Happy to pay if it actually works",
            "Glad to pay for a tool that saves me time",
        ],
    ),
    DemandPattern(
        pattern_id="en_pay_take_money",
        category=DemandCategory.WILLINGNESS_TO_PAY,
        regex_pattern=r"(?:take|shut up and take) my money",
        keywords=["take my money", "shut up and take my money"],
        language="en",
        weight=1.3,
        examples=[
            "Take my money!",
            "Shut up and take my money if this existed",
            "Someone make this and take my money",
        ],
    ),
    # -------------------------------------------------------------------------
    # ALTERNATIVE_SEEKING patterns (weight: 1.0)
    # -------------------------------------------------------------------------
    DemandPattern(
        pattern_id="en_alt_alternative",
        category=DemandCategory.ALTERNATIVE_SEEKING,
        regex_pattern=r"(?:looking for an? |any )?(?:alternative|replacement) (?:to|for)",
        keywords=["alternative to", "replacement for"],
        language="en",
        weight=1.0,
        examples=[
            "Looking for an alternative to Notion",
            "Any alternative to this paid service?",
            "Need a replacement for the discontinued app",
        ],
    ),
    DemandPattern(
        pattern_id="en_alt_something_like",
        category=DemandCategory.ALTERNATIVE_SEEKING,
        regex_pattern=r"(?:something|anything) (?:like|similar to|comparable to)",
        keywords=["something like", "similar to", "anything like"],
        language="en",
        weight=1.0,
        examples=[
            "Is there something like Notion but free?",
            "Looking for anything similar to Todoist",
            "Something comparable to Figma for Linux?",
        ],
    ),
    DemandPattern(
        pattern_id="en_alt_better_option",
        category=DemandCategory.ALTERNATIVE_SEEKING,
        regex_pattern=r"(?:better|cheaper|free|open.?source) (?:alternative|option|version)",
        keywords=["better alternative", "cheaper alternative", "free alternative"],
        language="en",
        weight=1.0,
        examples=[
            "Is there a better alternative?",
            "Looking for a cheaper option",
            "Any free version of this tool?",
        ],
    ),
    DemandPattern(
        pattern_id="en_alt_switch_from",
        category=DemandCategory.ALTERNATIVE_SEEKING,
        regex_pattern=r"(?:want to |trying to |need to )?(?:switch|migrate|move) (?:from|away from)",
        keywords=["switch from", "migrate from", "move away from"],
        language="en",
        weight=0.95,
        examples=[
            "Want to switch from Evernote to something else",
            "Trying to migrate from Google Docs",
            "Need to move away from this subscription model",
        ],
    ),
]
