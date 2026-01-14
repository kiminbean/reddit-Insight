"""알림 규칙 정의.

알림 유형과 규칙을 정의하는 데이터 모델을 제공한다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AlertType(str, Enum):
    """알림 유형.

    Values:
        KEYWORD_SURGE: 키워드 급등 감지
        SENTIMENT_SHIFT: 감성 변화 감지
        ACTIVITY_SPIKE: 활동량 급증 감지
        NEW_TRENDING: 새로운 트렌딩 키워드 감지
        CUSTOM: 사용자 정의 알림
    """

    KEYWORD_SURGE = "keyword_surge"
    SENTIMENT_SHIFT = "sentiment_shift"
    ACTIVITY_SPIKE = "activity_spike"
    NEW_TRENDING = "new_trending"
    CUSTOM = "custom"


@dataclass
class AlertCondition:
    """알림 조건.

    Attributes:
        threshold: 임계값
        window_minutes: 시간 윈도우 (분)
        comparison: 비교 연산자 (gt, gte, lt, lte, eq)
        field: 비교할 필드명
    """

    threshold: float
    window_minutes: int = 60
    comparison: str = "gte"  # gt, gte, lt, lte, eq
    field: str = "value"

    def evaluate(self, value: float) -> bool:
        """조건을 평가한다.

        Args:
            value: 평가할 값

        Returns:
            조건 충족 여부
        """
        if self.comparison == "gt":
            return value > self.threshold
        elif self.comparison == "gte":
            return value >= self.threshold
        elif self.comparison == "lt":
            return value < self.threshold
        elif self.comparison == "lte":
            return value <= self.threshold
        elif self.comparison == "eq":
            return value == self.threshold
        return False

    def to_dict(self) -> dict[str, Any]:
        """딕셔너리로 변환한다."""
        return {
            "threshold": self.threshold,
            "window_minutes": self.window_minutes,
            "comparison": self.comparison,
            "field": self.field,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AlertCondition":
        """딕셔너리에서 생성한다."""
        return cls(
            threshold=data.get("threshold", 0),
            window_minutes=data.get("window_minutes", 60),
            comparison=data.get("comparison", "gte"),
            field=data.get("field", "value"),
        )


@dataclass
class AlertRule:
    """알림 규칙.

    특정 조건이 충족될 때 알림을 트리거하는 규칙을 정의한다.

    Attributes:
        id: 규칙 고유 식별자
        name: 규칙 이름
        type: 알림 유형
        subreddit: 대상 서브레딧 (빈 문자열이면 모든 서브레딧)
        condition: 알림 조건
        notifiers: 사용할 알림 채널 목록 (예: ["email", "webhook"])
        enabled: 활성화 여부
        metadata: 추가 메타데이터 (예: 이메일 수신자, 웹훅 URL)
    """

    id: str
    name: str
    type: AlertType
    subreddit: str
    condition: AlertCondition
    notifiers: list[str] = field(default_factory=list)
    enabled: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def matches(self, subreddit: str, alert_type: AlertType) -> bool:
        """규칙이 주어진 조건에 매치되는지 확인한다.

        Args:
            subreddit: 서브레딧 이름
            alert_type: 알림 유형

        Returns:
            매치 여부
        """
        if not self.enabled:
            return False

        # 유형이 일치해야 함
        if self.type != alert_type:
            return False

        # 서브레딧 필터링 (빈 문자열이면 모든 서브레딧에 적용)
        if self.subreddit and self.subreddit.lower() != subreddit.lower():
            return False

        return True

    def to_dict(self) -> dict[str, Any]:
        """딕셔너리로 변환한다."""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type.value,
            "subreddit": self.subreddit,
            "condition": self.condition.to_dict(),
            "notifiers": self.notifiers,
            "enabled": self.enabled,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AlertRule":
        """딕셔너리에서 생성한다."""
        return cls(
            id=data["id"],
            name=data["name"],
            type=AlertType(data["type"]),
            subreddit=data.get("subreddit", ""),
            condition=AlertCondition.from_dict(data.get("condition", {})),
            notifiers=data.get("notifiers", []),
            enabled=data.get("enabled", True),
            metadata=data.get("metadata", {}),
        )


# 기본 규칙 프리셋
DEFAULT_RULE_PRESETS: dict[str, dict[str, Any]] = {
    "keyword_surge_high": {
        "name": "High Keyword Surge",
        "type": AlertType.KEYWORD_SURGE,
        "condition": AlertCondition(threshold=3.0, window_minutes=60, comparison="gte"),
        "description": "Triggers when keyword frequency increases 3x or more",
    },
    "sentiment_negative": {
        "name": "Negative Sentiment Alert",
        "type": AlertType.SENTIMENT_SHIFT,
        "condition": AlertCondition(threshold=-0.3, window_minutes=120, comparison="lte"),
        "description": "Triggers when sentiment drops below -0.3",
    },
    "activity_spike": {
        "name": "Activity Spike Detection",
        "type": AlertType.ACTIVITY_SPIKE,
        "condition": AlertCondition(threshold=2.0, window_minutes=30, comparison="gte"),
        "description": "Triggers when activity is 2x higher than baseline",
    },
}
