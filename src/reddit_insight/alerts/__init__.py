"""알림 모듈.

알림 규칙 관리, 알림 생성, 다양한 채널로의 알림 전송 기능을 제공한다.
"""

from reddit_insight.alerts.manager import Alert, AlertManager
from reddit_insight.alerts.notifiers import (
    EmailNotifier,
    Notifier,
    SlackNotifier,
    WebhookNotifier,
)
from reddit_insight.alerts.rules import AlertRule, AlertType

__all__ = [
    "Alert",
    "AlertManager",
    "AlertRule",
    "AlertType",
    "EmailNotifier",
    "Notifier",
    "SlackNotifier",
    "WebhookNotifier",
]
