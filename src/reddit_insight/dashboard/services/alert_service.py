"""알림 서비스.

대시보드에서 사용하는 알림 관련 서비스 레이어.
"""

from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING, Any

from reddit_insight.alerts.manager import Alert, AlertManager
from reddit_insight.alerts.notifiers import (
    ConsoleNotifier,
    EmailNotifier,
    SlackNotifier,
    WebhookNotifier,
)
from reddit_insight.alerts.rules import AlertCondition, AlertRule, AlertType
from reddit_insight.config import get_settings

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# 전역 AlertManager 인스턴스
_alert_manager: AlertManager | None = None


def get_alert_manager() -> AlertManager:
    """AlertManager 싱글톤 인스턴스를 반환한다."""
    global _alert_manager

    if _alert_manager is None:
        _alert_manager = AlertManager()
        _initialize_notifiers(_alert_manager)
        _load_default_rules(_alert_manager)
        logger.info("AlertManager initialized with notifiers")

    return _alert_manager


def _initialize_notifiers(manager: AlertManager) -> None:
    """설정에서 Notifier들을 초기화하고 등록한다."""
    settings = get_settings()

    # 콘솔 알림 (항상 등록)
    manager.register_notifier("console", ConsoleNotifier(verbose=True))

    # 이메일 알림
    if all([
        settings.smtp_host,
        settings.smtp_username,
        settings.smtp_password,
        settings.smtp_from_addr,
    ]):
        email_notifier = EmailNotifier(
            smtp_host=settings.smtp_host,
            smtp_port=settings.smtp_port,
            username=settings.smtp_username,
            password=settings.smtp_password,
            from_addr=settings.smtp_from_addr,
        )
        manager.register_notifier("email", email_notifier)
        logger.info("Email notifier registered")

    # 웹훅 알림
    if settings.alert_webhook_url:
        # Slack 형식 감지
        if "hooks.slack.com" in settings.alert_webhook_url:
            webhook_notifier = SlackNotifier(webhook_url=settings.alert_webhook_url)
            manager.register_notifier("webhook", webhook_notifier)
            logger.info("Slack notifier registered")
        else:
            webhook_notifier = WebhookNotifier(default_url=settings.alert_webhook_url)
            manager.register_notifier("webhook", webhook_notifier)
            logger.info("Webhook notifier registered")


def _load_default_rules(manager: AlertManager) -> None:
    """기본 규칙을 로드한다."""
    # 기본적으로 활성화된 규칙 없음 (사용자가 설정)
    pass


class AlertService:
    """알림 서비스.

    대시보드에서 알림 관련 CRUD 작업을 수행한다.
    """

    def __init__(self) -> None:
        """AlertService 초기화."""
        self._manager = get_alert_manager()

    # =========================================================================
    # Rule Management
    # =========================================================================

    def get_rules(self, enabled_only: bool = False) -> list[dict[str, Any]]:
        """모든 규칙을 조회한다."""
        rules = self._manager.get_rules(enabled_only=enabled_only)
        return [rule.to_dict() for rule in rules]

    def get_rule(self, rule_id: str) -> dict[str, Any] | None:
        """규칙을 조회한다."""
        rule = self._manager.get_rule(rule_id)
        return rule.to_dict() if rule else None

    def create_rule(
        self,
        name: str,
        alert_type: str,
        subreddit: str,
        threshold: float,
        *,
        window_minutes: int = 60,
        comparison: str = "gte",
        field: str = "value",
        notifiers: list[str] | None = None,
        enabled: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """새 규칙을 생성한다."""
        rule_id = str(uuid.uuid4())[:8]

        condition = AlertCondition(
            threshold=threshold,
            window_minutes=window_minutes,
            comparison=comparison,
            field=field,
        )

        rule = AlertRule(
            id=rule_id,
            name=name,
            type=AlertType(alert_type),
            subreddit=subreddit,
            condition=condition,
            notifiers=notifiers or ["console"],
            enabled=enabled,
            metadata=metadata or {},
        )

        self._manager.add_rule(rule)
        logger.info("Created rule: %s (%s)", name, rule_id)

        return rule.to_dict()

    def update_rule(
        self,
        rule_id: str,
        **updates: Any,
    ) -> dict[str, Any] | None:
        """규칙을 업데이트한다."""
        rule = self._manager.get_rule(rule_id)
        if not rule:
            return None

        # 업데이트 적용
        if "name" in updates:
            rule.name = updates["name"]
        if "subreddit" in updates:
            rule.subreddit = updates["subreddit"]
        if "enabled" in updates:
            rule.enabled = updates["enabled"]
        if "notifiers" in updates:
            rule.notifiers = updates["notifiers"]
        if "metadata" in updates:
            rule.metadata = updates["metadata"]

        # 조건 업데이트
        if any(k in updates for k in ("threshold", "window_minutes", "comparison", "field")):
            rule.condition = AlertCondition(
                threshold=updates.get("threshold", rule.condition.threshold),
                window_minutes=updates.get("window_minutes", rule.condition.window_minutes),
                comparison=updates.get("comparison", rule.condition.comparison),
                field=updates.get("field", rule.condition.field),
            )

        self._manager.update_rule(rule)
        logger.info("Updated rule: %s", rule_id)

        return rule.to_dict()

    def delete_rule(self, rule_id: str) -> bool:
        """규칙을 삭제한다."""
        success = self._manager.remove_rule(rule_id)
        if success:
            logger.info("Deleted rule: %s", rule_id)
        return success

    def toggle_rule(self, rule_id: str) -> dict[str, Any] | None:
        """규칙을 토글한다 (활성화/비활성화)."""
        rule = self._manager.get_rule(rule_id)
        if not rule:
            return None

        if rule.enabled:
            self._manager.disable_rule(rule_id)
        else:
            self._manager.enable_rule(rule_id)

        return self._manager.get_rule(rule_id).to_dict()

    # =========================================================================
    # Alert History
    # =========================================================================

    def get_history(
        self,
        limit: int = 50,
        *,
        rule_id: str | None = None,
        subreddit: str | None = None,
    ) -> list[dict[str, Any]]:
        """알림 이력을 조회한다."""
        alerts = self._manager.get_history(
            limit=limit,
            rule_id=rule_id,
            subreddit=subreddit,
        )
        return [alert.to_dict() for alert in alerts]

    def clear_history(self) -> int:
        """알림 이력을 삭제한다."""
        return self._manager.clear_history()

    # =========================================================================
    # Test Alert
    # =========================================================================

    async def send_test_alert(self, notifier_name: str = "console") -> bool:
        """테스트 알림을 전송한다."""
        settings = get_settings()
        metadata = {}

        if notifier_name == "email":
            metadata["to_addrs"] = settings.get_alert_email_recipients()

        return await self._manager.send_test_alert(notifier_name, metadata)

    # =========================================================================
    # Stats and Info
    # =========================================================================

    def get_stats(self) -> dict[str, Any]:
        """알림 통계를 조회한다."""
        return self._manager.get_stats()

    def get_available_notifiers(self) -> list[str]:
        """사용 가능한 알림 채널 목록을 반환한다."""
        return self._manager.get_notifiers()

    def get_alert_types(self) -> list[dict[str, str]]:
        """사용 가능한 알림 유형 목록을 반환한다."""
        return [
            {"value": AlertType.KEYWORD_SURGE.value, "label": "Keyword Surge"},
            {"value": AlertType.SENTIMENT_SHIFT.value, "label": "Sentiment Shift"},
            {"value": AlertType.ACTIVITY_SPIKE.value, "label": "Activity Spike"},
            {"value": AlertType.NEW_TRENDING.value, "label": "New Trending"},
            {"value": AlertType.CUSTOM.value, "label": "Custom"},
        ]


# 싱글톤 서비스 인스턴스
_alert_service: AlertService | None = None


def get_alert_service() -> AlertService:
    """AlertService 싱글톤 인스턴스를 반환한다."""
    global _alert_service

    if _alert_service is None:
        _alert_service = AlertService()

    return _alert_service
