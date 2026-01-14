"""알림 전송자.

다양한 채널로 알림을 전송하는 Notifier 구현체를 제공한다.
"""

from __future__ import annotations

import logging
import smtplib
from abc import ABC, abstractmethod
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import TYPE_CHECKING, Any

import httpx

if TYPE_CHECKING:
    from reddit_insight.alerts.manager import Alert

logger = logging.getLogger(__name__)


class Notifier(ABC):
    """알림 전송자 추상 클래스.

    모든 알림 전송자는 이 클래스를 상속받아야 한다.
    """

    @abstractmethod
    async def send(self, alert: "Alert", metadata: dict[str, Any]) -> bool:
        """알림을 전송한다.

        Args:
            alert: 전송할 알림
            metadata: 알림 규칙의 메타데이터 (수신자, URL 등)

        Returns:
            전송 성공 여부
        """


class EmailNotifier(Notifier):
    """이메일 알림 전송자.

    SMTP를 통해 이메일 알림을 전송한다.

    Example:
        >>> notifier = EmailNotifier(
        ...     smtp_host="smtp.gmail.com",
        ...     smtp_port=587,
        ...     username="user@gmail.com",
        ...     password="app_password",
        ...     from_addr="user@gmail.com",
        ... )
        >>> await notifier.send(alert, {"to_addrs": ["recipient@example.com"]})
    """

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        username: str,
        password: str,
        from_addr: str,
        *,
        use_tls: bool = True,
    ) -> None:
        """EmailNotifier 초기화.

        Args:
            smtp_host: SMTP 서버 호스트
            smtp_port: SMTP 서버 포트
            username: SMTP 인증 사용자명
            password: SMTP 인증 비밀번호
            from_addr: 발신자 이메일 주소
            use_tls: TLS 사용 여부 (기본: True)
        """
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_addr = from_addr
        self.use_tls = use_tls

    async def send(self, alert: "Alert", metadata: dict[str, Any]) -> bool:
        """이메일 알림을 전송한다.

        Args:
            alert: 전송할 알림
            metadata: 메타데이터 (to_addrs 필수)

        Returns:
            전송 성공 여부
        """
        to_addrs = metadata.get("to_addrs", [])
        if not to_addrs:
            logger.warning("No recipients specified for email notification")
            return False

        try:
            subject = f"[Reddit Insight] {alert.type.value}: {alert.message[:50]}"
            body = self._format_email_body(alert)

            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.from_addr
            msg["To"] = ", ".join(to_addrs)

            # 텍스트 버전
            text_part = MIMEText(body, "plain", "utf-8")
            msg.attach(text_part)

            # HTML 버전
            html_body = self._format_html_body(alert)
            html_part = MIMEText(html_body, "html", "utf-8")
            msg.attach(html_part)

            # SMTP 전송
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                server.login(self.username, self.password)
                server.sendmail(self.from_addr, to_addrs, msg.as_string())

            logger.info("Email sent to %d recipients", len(to_addrs))
            return True

        except Exception as e:
            logger.exception("Failed to send email: %s", e)
            return False

    def _format_email_body(self, alert: "Alert") -> str:
        """이메일 본문을 텍스트로 포맷팅한다."""
        lines = [
            f"Alert Type: {alert.type.value}",
            f"Message: {alert.message}",
            f"Subreddit: r/{alert.subreddit}" if alert.subreddit else "",
            f"Triggered At: {alert.triggered_at.isoformat()}",
            "",
            "Details:",
        ]

        for key, value in alert.data.items():
            lines.append(f"  - {key}: {value}")

        return "\n".join(line for line in lines if line or line == "")

    def _format_html_body(self, alert: "Alert") -> str:
        """이메일 본문을 HTML로 포맷팅한다."""
        subreddit_line = ""
        if alert.subreddit:
            subreddit_line = f'<p><strong>Subreddit:</strong> r/{alert.subreddit}</p>'

        details_html = ""
        if alert.data:
            details_items = "".join(
                f"<li><strong>{k}:</strong> {v}</li>"
                for k, v in alert.data.items()
            )
            details_html = f"""
            <h3>Details</h3>
            <ul>{details_items}</ul>
            """

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; }}
                .alert-box {{ background-color: #fff3cd; border: 1px solid #ffc107; border-radius: 8px; padding: 15px; margin-bottom: 20px; }}
                .alert-type {{ color: #856404; font-weight: bold; margin-bottom: 10px; }}
                h3 {{ color: #333; border-bottom: 1px solid #ddd; padding-bottom: 5px; }}
                ul {{ list-style-type: none; padding: 0; }}
                li {{ padding: 5px 0; }}
                .footer {{ color: #666; font-size: 12px; margin-top: 30px; border-top: 1px solid #ddd; padding-top: 10px; }}
            </style>
        </head>
        <body>
            <div class="alert-box">
                <div class="alert-type">{alert.type.value.upper()}</div>
                <p>{alert.message}</p>
            </div>

            {subreddit_line}
            <p><strong>Triggered At:</strong> {alert.triggered_at.isoformat()}</p>

            {details_html}

            <div class="footer">
                This is an automated notification from Reddit Insight.
            </div>
        </body>
        </html>
        """


class WebhookNotifier(Notifier):
    """웹훅 알림 전송자.

    HTTP POST를 통해 웹훅 알림을 전송한다.

    Example:
        >>> notifier = WebhookNotifier()
        >>> await notifier.send(alert, {"url": "https://example.com/webhook"})
    """

    def __init__(
        self,
        default_url: str | None = None,
        *,
        timeout: float = 30.0,
        headers: dict[str, str] | None = None,
    ) -> None:
        """WebhookNotifier 초기화.

        Args:
            default_url: 기본 웹훅 URL
            timeout: 요청 타임아웃 (초)
            headers: 추가 HTTP 헤더
        """
        self.default_url = default_url
        self.timeout = timeout
        self.headers = headers or {}

    async def send(self, alert: "Alert", metadata: dict[str, Any]) -> bool:
        """웹훅 알림을 전송한다.

        Args:
            alert: 전송할 알림
            metadata: 메타데이터 (url 옵션)

        Returns:
            전송 성공 여부
        """
        url = metadata.get("url") or self.default_url
        if not url:
            logger.warning("No webhook URL specified")
            return False

        payload = self._format_payload(alert)

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                headers = {
                    "Content-Type": "application/json",
                    **self.headers,
                }
                response = await client.post(url, json=payload, headers=headers)

                if response.status_code in (200, 201, 202, 204):
                    logger.info("Webhook sent successfully to %s", url)
                    return True
                else:
                    logger.warning(
                        "Webhook returned status %d: %s",
                        response.status_code,
                        response.text[:200],
                    )
                    return False

        except Exception as e:
            logger.exception("Failed to send webhook: %s", e)
            return False

    def _format_payload(self, alert: "Alert") -> dict[str, Any]:
        """웹훅 페이로드를 포맷팅한다."""
        return {
            "id": alert.id,
            "type": alert.type.value,
            "message": alert.message,
            "data": alert.data,
            "subreddit": alert.subreddit,
            "triggered_at": alert.triggered_at.isoformat(),
        }


class SlackNotifier(WebhookNotifier):
    """Slack 웹훅 알림 전송자.

    Slack Incoming Webhook을 통해 알림을 전송한다.

    Example:
        >>> notifier = SlackNotifier(webhook_url="https://hooks.slack.com/services/...")
        >>> await notifier.send(alert, {})
    """

    def __init__(
        self,
        webhook_url: str | None = None,
        *,
        channel: str | None = None,
        username: str = "Reddit Insight Bot",
        icon_emoji: str = ":bell:",
    ) -> None:
        """SlackNotifier 초기화.

        Args:
            webhook_url: Slack Incoming Webhook URL
            channel: 전송할 채널 (옵션)
            username: 봇 사용자명
            icon_emoji: 봇 아이콘 이모지
        """
        super().__init__(default_url=webhook_url)
        self.channel = channel
        self.username = username
        self.icon_emoji = icon_emoji

    def _format_payload(self, alert: "Alert") -> dict[str, Any]:
        """Slack 메시지 형식으로 페이로드를 포맷팅한다."""
        # 알림 유형에 따른 색상
        color_map = {
            "keyword_surge": "#36a64f",  # 초록
            "sentiment_shift": "#ff9500",  # 주황
            "activity_spike": "#007aff",  # 파랑
            "new_trending": "#5856d6",  # 보라
            "custom": "#8e8e93",  # 회색
        }
        color = color_map.get(alert.type.value, "#8e8e93")

        # 데이터 필드
        fields = []
        if alert.subreddit:
            fields.append({
                "title": "Subreddit",
                "value": f"r/{alert.subreddit}",
                "short": True,
            })

        for key, value in alert.data.items():
            if key in ("value", "threshold"):
                fields.append({
                    "title": key.replace("_", " ").title(),
                    "value": str(value),
                    "short": True,
                })

        payload: dict[str, Any] = {
            "username": self.username,
            "icon_emoji": self.icon_emoji,
            "attachments": [
                {
                    "fallback": alert.message,
                    "color": color,
                    "title": f":bell: {alert.type.value.replace('_', ' ').title()}",
                    "text": alert.message,
                    "fields": fields,
                    "footer": "Reddit Insight",
                    "ts": int(alert.triggered_at.timestamp()),
                }
            ],
        }

        if self.channel:
            payload["channel"] = self.channel

        return payload


class DiscordNotifier(WebhookNotifier):
    """Discord 웹훅 알림 전송자.

    Discord Webhook을 통해 알림을 전송한다.

    Example:
        >>> notifier = DiscordNotifier(webhook_url="https://discord.com/api/webhooks/...")
        >>> await notifier.send(alert, {})
    """

    def __init__(
        self,
        webhook_url: str | None = None,
        *,
        username: str = "Reddit Insight",
    ) -> None:
        """DiscordNotifier 초기화.

        Args:
            webhook_url: Discord Webhook URL
            username: 봇 사용자명
        """
        super().__init__(default_url=webhook_url)
        self.username = username

    def _format_payload(self, alert: "Alert") -> dict[str, Any]:
        """Discord 메시지 형식으로 페이로드를 포맷팅한다."""
        # 알림 유형에 따른 색상 (십진수)
        color_map = {
            "keyword_surge": 0x36A64F,  # 초록
            "sentiment_shift": 0xFF9500,  # 주황
            "activity_spike": 0x007AFF,  # 파랑
            "new_trending": 0x5856D6,  # 보라
            "custom": 0x8E8E93,  # 회색
        }
        color = color_map.get(alert.type.value, 0x8E8E93)

        # 임베드 필드
        fields = []
        if alert.subreddit:
            fields.append({
                "name": "Subreddit",
                "value": f"r/{alert.subreddit}",
                "inline": True,
            })

        for key, value in alert.data.items():
            if key in ("value", "threshold"):
                fields.append({
                    "name": key.replace("_", " ").title(),
                    "value": str(value),
                    "inline": True,
                })

        return {
            "username": self.username,
            "embeds": [
                {
                    "title": f"{alert.type.value.replace('_', ' ').title()}",
                    "description": alert.message,
                    "color": color,
                    "fields": fields,
                    "footer": {"text": "Reddit Insight"},
                    "timestamp": alert.triggered_at.isoformat(),
                }
            ],
        }


class ConsoleNotifier(Notifier):
    """콘솔 알림 전송자 (개발/디버깅용).

    알림을 콘솔에 출력한다.
    """

    def __init__(self, *, verbose: bool = False) -> None:
        """ConsoleNotifier 초기화.

        Args:
            verbose: 상세 출력 여부
        """
        self.verbose = verbose

    async def send(self, alert: "Alert", metadata: dict[str, Any]) -> bool:
        """알림을 콘솔에 출력한다."""
        print(f"\n{'='*60}")
        print(f"[ALERT] {alert.type.value.upper()}")
        print(f"Message: {alert.message}")
        if alert.subreddit:
            print(f"Subreddit: r/{alert.subreddit}")
        print(f"Time: {alert.triggered_at.isoformat()}")

        if self.verbose and alert.data:
            print("\nDetails:")
            for key, value in alert.data.items():
                print(f"  - {key}: {value}")

        print(f"{'='*60}\n")
        return True
