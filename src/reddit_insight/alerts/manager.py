"""알림 관리자.

알림 규칙을 관리하고, 메트릭을 평가하여 알림을 생성하고 전송한다.
"""

from __future__ import annotations

import logging
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from reddit_insight.alerts.rules import AlertCondition, AlertRule, AlertType

if TYPE_CHECKING:
    from reddit_insight.alerts.notifiers import Notifier

logger = logging.getLogger(__name__)


@dataclass
class Alert:
    """생성된 알림.

    Attributes:
        id: 알림 고유 식별자
        rule_id: 트리거한 규칙 ID
        type: 알림 유형
        message: 알림 메시지
        data: 알림 관련 데이터
        triggered_at: 트리거 시간
        subreddit: 관련 서브레딧
        sent: 전송 여부
        sent_to: 전송된 채널 목록
        error: 전송 실패 시 에러 메시지
    """

    id: str
    rule_id: str
    type: AlertType
    message: str
    data: dict[str, Any]
    triggered_at: datetime
    subreddit: str = ""
    sent: bool = False
    sent_to: list[str] = field(default_factory=list)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """딕셔너리로 변환한다."""
        return {
            "id": self.id,
            "rule_id": self.rule_id,
            "type": self.type.value,
            "message": self.message,
            "data": self.data,
            "triggered_at": self.triggered_at.isoformat(),
            "subreddit": self.subreddit,
            "sent": self.sent,
            "sent_to": self.sent_to,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Alert":
        """딕셔너리에서 생성한다."""
        triggered_at = data.get("triggered_at")
        if isinstance(triggered_at, str):
            triggered_at = datetime.fromisoformat(triggered_at)
        else:
            triggered_at = datetime.now(UTC)

        return cls(
            id=data.get("id", str(uuid.uuid4())),
            rule_id=data["rule_id"],
            type=AlertType(data["type"]),
            message=data["message"],
            data=data.get("data", {}),
            triggered_at=triggered_at,
            subreddit=data.get("subreddit", ""),
            sent=data.get("sent", False),
            sent_to=data.get("sent_to", []),
            error=data.get("error"),
        )


class AlertManager:
    """알림 관리자.

    알림 규칙을 관리하고, 메트릭을 평가하여 알림을 생성한다.
    등록된 Notifier를 통해 알림을 전송한다.

    Attributes:
        max_history: 유지할 최대 알림 이력 수

    Example:
        >>> manager = AlertManager()
        >>> manager.register_notifier("email", email_notifier)
        >>> manager.add_rule(AlertRule(...))
        >>> alerts = manager.check_rules("python", metrics)
        >>> for alert in alerts:
        ...     await manager.process_alert(alert)
    """

    def __init__(self, max_history: int = 1000) -> None:
        """AlertManager 초기화.

        Args:
            max_history: 유지할 최대 알림 이력 수
        """
        self._rules: dict[str, AlertRule] = {}
        self._notifiers: dict[str, "Notifier"] = {}
        self._history: deque[Alert] = deque(maxlen=max_history)
        self._cooldowns: dict[str, datetime] = {}  # rule_id -> last_triggered
        self._cooldown_minutes: int = 5  # 동일 규칙 재트리거 방지 시간

        logger.info("AlertManager initialized (max_history=%d)", max_history)

    # =========================================================================
    # Notifier Management
    # =========================================================================

    def register_notifier(self, name: str, notifier: "Notifier") -> None:
        """알림 전송자를 등록한다.

        Args:
            name: 알림 전송자 이름 (예: "email", "webhook")
            notifier: Notifier 인스턴스
        """
        self._notifiers[name] = notifier
        logger.info("Registered notifier: %s", name)

    def unregister_notifier(self, name: str) -> bool:
        """알림 전송자를 해제한다.

        Args:
            name: 알림 전송자 이름

        Returns:
            해제 성공 여부
        """
        if name in self._notifiers:
            del self._notifiers[name]
            logger.info("Unregistered notifier: %s", name)
            return True
        return False

    def get_notifiers(self) -> list[str]:
        """등록된 알림 전송자 이름 목록을 반환한다."""
        return list(self._notifiers.keys())

    # =========================================================================
    # Rule Management
    # =========================================================================

    def add_rule(self, rule: AlertRule) -> None:
        """알림 규칙을 추가한다.

        Args:
            rule: 추가할 규칙

        Raises:
            ValueError: 동일한 ID의 규칙이 이미 존재하는 경우
        """
        if rule.id in self._rules:
            raise ValueError(f"Rule with ID '{rule.id}' already exists")

        self._rules[rule.id] = rule
        logger.info("Added rule: %s (%s)", rule.name, rule.id)

    def update_rule(self, rule: AlertRule) -> None:
        """알림 규칙을 업데이트한다.

        Args:
            rule: 업데이트할 규칙

        Raises:
            KeyError: 규칙이 존재하지 않는 경우
        """
        if rule.id not in self._rules:
            raise KeyError(f"Rule with ID '{rule.id}' not found")

        self._rules[rule.id] = rule
        logger.info("Updated rule: %s (%s)", rule.name, rule.id)

    def remove_rule(self, rule_id: str) -> bool:
        """알림 규칙을 제거한다.

        Args:
            rule_id: 제거할 규칙 ID

        Returns:
            제거 성공 여부
        """
        if rule_id in self._rules:
            rule = self._rules.pop(rule_id)
            # 쿨다운도 제거
            self._cooldowns.pop(rule_id, None)
            logger.info("Removed rule: %s (%s)", rule.name, rule_id)
            return True
        return False

    def get_rule(self, rule_id: str) -> AlertRule | None:
        """규칙을 조회한다.

        Args:
            rule_id: 규칙 ID

        Returns:
            규칙 또는 None
        """
        return self._rules.get(rule_id)

    def get_rules(self, enabled_only: bool = False) -> list[AlertRule]:
        """모든 규칙을 반환한다.

        Args:
            enabled_only: 활성화된 규칙만 반환할지 여부

        Returns:
            규칙 목록
        """
        rules = list(self._rules.values())
        if enabled_only:
            rules = [r for r in rules if r.enabled]
        return rules

    def enable_rule(self, rule_id: str) -> bool:
        """규칙을 활성화한다.

        Args:
            rule_id: 규칙 ID

        Returns:
            성공 여부
        """
        rule = self._rules.get(rule_id)
        if rule:
            rule.enabled = True
            logger.info("Enabled rule: %s", rule_id)
            return True
        return False

    def disable_rule(self, rule_id: str) -> bool:
        """규칙을 비활성화한다.

        Args:
            rule_id: 규칙 ID

        Returns:
            성공 여부
        """
        rule = self._rules.get(rule_id)
        if rule:
            rule.enabled = False
            logger.info("Disabled rule: %s", rule_id)
            return True
        return False

    # =========================================================================
    # Rule Evaluation
    # =========================================================================

    def check_rules(
        self,
        subreddit: str,
        metrics: dict[str, Any],
        *,
        alert_type: AlertType | None = None,
    ) -> list[Alert]:
        """메트릭을 규칙과 비교하여 알림을 생성한다.

        Args:
            subreddit: 서브레딧 이름
            metrics: 평가할 메트릭 딕셔너리
            alert_type: 특정 알림 유형만 체크 (None이면 모든 유형)

        Returns:
            생성된 알림 목록
        """
        alerts: list[Alert] = []
        now = datetime.now(UTC)

        for rule in self._rules.values():
            if not rule.enabled:
                continue

            # 알림 유형 필터링
            if alert_type and rule.type != alert_type:
                continue

            # 서브레딧 매칭
            if rule.subreddit and rule.subreddit.lower() != subreddit.lower():
                continue

            # 쿨다운 체크
            if self._is_in_cooldown(rule.id, now):
                logger.debug("Rule %s is in cooldown", rule.id)
                continue

            # 조건 평가
            value = metrics.get(rule.condition.field, 0)
            if rule.condition.evaluate(value):
                alert = self._create_alert(rule, subreddit, metrics, value)
                alerts.append(alert)
                self._cooldowns[rule.id] = now
                logger.info(
                    "Alert triggered: %s for r/%s (value=%s)",
                    rule.name,
                    subreddit,
                    value,
                )

        return alerts

    def _is_in_cooldown(self, rule_id: str, now: datetime) -> bool:
        """규칙이 쿨다운 상태인지 확인한다."""
        last_triggered = self._cooldowns.get(rule_id)
        if last_triggered is None:
            return False

        elapsed_minutes = (now - last_triggered).total_seconds() / 60
        return elapsed_minutes < self._cooldown_minutes

    def _create_alert(
        self,
        rule: AlertRule,
        subreddit: str,
        metrics: dict[str, Any],
        value: float,
    ) -> Alert:
        """알림을 생성한다."""
        # 메시지 생성
        message = self._format_alert_message(rule, subreddit, value)

        return Alert(
            id=str(uuid.uuid4()),
            rule_id=rule.id,
            type=rule.type,
            message=message,
            data={
                "value": value,
                "threshold": rule.condition.threshold,
                "metrics": metrics,
                "rule_name": rule.name,
            },
            triggered_at=datetime.now(UTC),
            subreddit=subreddit,
        )

    def _format_alert_message(
        self,
        rule: AlertRule,
        subreddit: str,
        value: float,
    ) -> str:
        """알림 메시지를 포맷팅한다."""
        type_labels = {
            AlertType.KEYWORD_SURGE: "Keyword surge detected",
            AlertType.SENTIMENT_SHIFT: "Sentiment shift detected",
            AlertType.ACTIVITY_SPIKE: "Activity spike detected",
            AlertType.NEW_TRENDING: "New trending topic detected",
            AlertType.CUSTOM: "Custom alert triggered",
        }

        label = type_labels.get(rule.type, "Alert triggered")
        return f"{label} in r/{subreddit}: {rule.name} (value: {value:.2f})"

    # =========================================================================
    # Alert Processing
    # =========================================================================

    async def process_alert(self, alert: Alert) -> Alert:
        """알림을 처리하고 전송한다.

        등록된 Notifier를 통해 알림을 전송한다.

        Args:
            alert: 처리할 알림

        Returns:
            처리된 알림 (전송 상태 업데이트됨)
        """
        rule = self._rules.get(alert.rule_id)
        if not rule:
            logger.warning("Rule not found for alert: %s", alert.rule_id)
            alert.error = f"Rule not found: {alert.rule_id}"
            self._history.append(alert)
            return alert

        # 각 Notifier로 전송
        sent_to: list[str] = []
        errors: list[str] = []

        for notifier_name in rule.notifiers:
            notifier = self._notifiers.get(notifier_name)
            if not notifier:
                logger.warning("Notifier not found: %s", notifier_name)
                continue

            try:
                success = await notifier.send(alert, rule.metadata)
                if success:
                    sent_to.append(notifier_name)
                    logger.info("Alert sent via %s: %s", notifier_name, alert.id)
                else:
                    errors.append(f"{notifier_name}: failed")
                    logger.warning("Failed to send alert via %s", notifier_name)
            except Exception as e:
                errors.append(f"{notifier_name}: {e}")
                logger.exception("Error sending alert via %s", notifier_name)

        # 알림 상태 업데이트
        alert.sent = len(sent_to) > 0
        alert.sent_to = sent_to
        if errors:
            alert.error = "; ".join(errors)

        # 이력에 추가
        self._history.append(alert)

        return alert

    async def send_test_alert(
        self,
        notifier_name: str,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """테스트 알림을 전송한다.

        Args:
            notifier_name: 알림 전송자 이름
            metadata: 알림 메타데이터

        Returns:
            전송 성공 여부
        """
        notifier = self._notifiers.get(notifier_name)
        if not notifier:
            logger.warning("Notifier not found: %s", notifier_name)
            return False

        test_alert = Alert(
            id=str(uuid.uuid4()),
            rule_id="test",
            type=AlertType.CUSTOM,
            message="This is a test alert from Reddit Insight",
            data={"test": True},
            triggered_at=datetime.now(UTC),
            subreddit="test",
        )

        try:
            return await notifier.send(test_alert, metadata or {})
        except Exception as e:
            logger.exception("Error sending test alert via %s: %s", notifier_name, e)
            return False

    # =========================================================================
    # History
    # =========================================================================

    def get_history(
        self,
        limit: int = 100,
        *,
        rule_id: str | None = None,
        subreddit: str | None = None,
        sent_only: bool = False,
    ) -> list[Alert]:
        """알림 이력을 반환한다.

        Args:
            limit: 반환할 최대 개수
            rule_id: 특정 규칙의 알림만 필터링
            subreddit: 특정 서브레딧의 알림만 필터링
            sent_only: 전송된 알림만 반환

        Returns:
            알림 이력 (최신순)
        """
        alerts = list(self._history)

        # 필터링
        if rule_id:
            alerts = [a for a in alerts if a.rule_id == rule_id]
        if subreddit:
            alerts = [a for a in alerts if a.subreddit.lower() == subreddit.lower()]
        if sent_only:
            alerts = [a for a in alerts if a.sent]

        # 최신순 정렬 및 제한
        alerts.sort(key=lambda a: a.triggered_at, reverse=True)
        return alerts[:limit]

    def clear_history(self) -> int:
        """알림 이력을 삭제한다.

        Returns:
            삭제된 알림 수
        """
        count = len(self._history)
        self._history.clear()
        logger.info("Cleared %d alerts from history", count)
        return count

    # =========================================================================
    # Serialization
    # =========================================================================

    def get_stats(self) -> dict[str, Any]:
        """알림 통계를 반환한다."""
        history_list = list(self._history)

        total = len(history_list)
        sent = sum(1 for a in history_list if a.sent)
        failed = sum(1 for a in history_list if a.error)

        # 유형별 카운트
        by_type: dict[str, int] = {}
        for alert in history_list:
            type_name = alert.type.value
            by_type[type_name] = by_type.get(type_name, 0) + 1

        return {
            "total_rules": len(self._rules),
            "enabled_rules": sum(1 for r in self._rules.values() if r.enabled),
            "registered_notifiers": list(self._notifiers.keys()),
            "history_count": total,
            "sent_count": sent,
            "failed_count": failed,
            "by_type": by_type,
        }

    def export_rules(self) -> list[dict[str, Any]]:
        """규칙을 내보낸다.

        Returns:
            규칙 딕셔너리 목록
        """
        return [rule.to_dict() for rule in self._rules.values()]

    def import_rules(self, rules_data: list[dict[str, Any]]) -> int:
        """규칙을 가져온다.

        Args:
            rules_data: 규칙 딕셔너리 목록

        Returns:
            가져온 규칙 수
        """
        count = 0
        for data in rules_data:
            try:
                rule = AlertRule.from_dict(data)
                self._rules[rule.id] = rule
                count += 1
            except Exception as e:
                logger.warning("Failed to import rule: %s", e)

        logger.info("Imported %d rules", count)
        return count
