"""Notifier 테스트.

알림 전송자의 단위 테스트 (Mock SMTP, HTTP 사용).
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from reddit_insight.alerts.manager import Alert
from reddit_insight.alerts.notifiers import (
    ConsoleNotifier,
    DiscordNotifier,
    EmailNotifier,
    SlackNotifier,
    WebhookNotifier,
)
from reddit_insight.alerts.rules import AlertType


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_alert():
    """샘플 알림을 생성한다."""
    return Alert(
        id="alert_001",
        rule_id="rule_001",
        type=AlertType.KEYWORD_SURGE,
        message="Keyword surge detected in r/python",
        data={
            "value": 2.5,
            "threshold": 2.0,
            "metrics": {"keyword_count": 150},
        },
        triggered_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
        subreddit="python",
    )


# =============================================================================
# EmailNotifier Tests
# =============================================================================


class TestEmailNotifier:
    """EmailNotifier 테스트."""

    @pytest.fixture
    def notifier(self):
        """EmailNotifier 인스턴스를 생성한다."""
        return EmailNotifier(
            smtp_host="smtp.test.com",
            smtp_port=587,
            username="test@test.com",
            password="testpass",
            from_addr="test@test.com",
        )

    @pytest.mark.asyncio
    async def test_send_no_recipients(self, notifier, sample_alert):
        """수신자가 없으면 False를 반환한다."""
        result = await notifier.send(sample_alert, {})
        assert result is False

    @pytest.mark.asyncio
    async def test_send_success(self, notifier, sample_alert):
        """이메일 전송이 성공하면 True를 반환한다."""
        with patch("smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_server

            result = await notifier.send(
                sample_alert,
                {"to_addrs": ["recipient@test.com"]},
            )

            assert result is True
            mock_server.starttls.assert_called_once()
            mock_server.login.assert_called_once_with("test@test.com", "testpass")
            mock_server.sendmail.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_smtp_error(self, notifier, sample_alert):
        """SMTP 에러 발생 시 False를 반환한다."""
        with patch("smtplib.SMTP") as mock_smtp:
            mock_smtp.return_value.__enter__.side_effect = Exception("SMTP Error")

            result = await notifier.send(
                sample_alert,
                {"to_addrs": ["recipient@test.com"]},
            )

            assert result is False

    def test_format_email_body(self, notifier, sample_alert):
        """이메일 본문이 올바르게 포맷팅된다."""
        body = notifier._format_email_body(sample_alert)

        assert "keyword_surge" in body
        assert "Keyword surge detected" in body
        assert "r/python" in body
        assert "value: 2.5" in body

    def test_format_html_body(self, notifier, sample_alert):
        """HTML 본문이 올바르게 포맷팅된다."""
        html = notifier._format_html_body(sample_alert)

        assert "<html>" in html
        assert "KEYWORD_SURGE" in html
        assert "r/python" in html


# =============================================================================
# WebhookNotifier Tests
# =============================================================================


class TestWebhookNotifier:
    """WebhookNotifier 테스트."""

    @pytest.fixture
    def notifier(self):
        """WebhookNotifier 인스턴스를 생성한다."""
        return WebhookNotifier(default_url="https://example.com/webhook")

    @pytest.mark.asyncio
    async def test_send_no_url(self, sample_alert):
        """URL이 없으면 False를 반환한다."""
        notifier = WebhookNotifier()  # default_url 없음
        result = await notifier.send(sample_alert, {})
        assert result is False

    @pytest.mark.asyncio
    async def test_send_success(self, notifier, sample_alert):
        """웹훅 전송이 성공하면 True를 반환한다."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            result = await notifier.send(sample_alert, {})

            assert result is True

    @pytest.mark.asyncio
    async def test_send_with_custom_url(self, notifier, sample_alert):
        """메타데이터의 URL이 기본 URL보다 우선한다."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_instance = MagicMock()
            mock_instance.post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value = mock_instance

            await notifier.send(
                sample_alert,
                {"url": "https://custom.com/hook"},
            )

            # 커스텀 URL로 호출되었는지 확인
            call_args = mock_instance.post.call_args
            assert call_args[0][0] == "https://custom.com/hook"

    @pytest.mark.asyncio
    async def test_send_server_error(self, notifier, sample_alert):
        """서버 에러 시 False를 반환한다."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            result = await notifier.send(sample_alert, {})

            assert result is False

    @pytest.mark.asyncio
    async def test_send_network_error(self, notifier, sample_alert):
        """네트워크 에러 시 False를 반환한다."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=Exception("Network Error")
            )

            result = await notifier.send(sample_alert, {})

            assert result is False

    def test_format_payload(self, notifier, sample_alert):
        """페이로드가 올바르게 포맷팅된다."""
        payload = notifier._format_payload(sample_alert)

        assert payload["id"] == "alert_001"
        assert payload["type"] == "keyword_surge"
        assert payload["message"] == "Keyword surge detected in r/python"
        assert payload["subreddit"] == "python"
        assert "triggered_at" in payload


# =============================================================================
# SlackNotifier Tests
# =============================================================================


class TestSlackNotifier:
    """SlackNotifier 테스트."""

    @pytest.fixture
    def notifier(self):
        """SlackNotifier 인스턴스를 생성한다."""
        return SlackNotifier(
            webhook_url="https://hooks.slack.com/services/xxx/yyy/zzz",
            channel="#alerts",
            username="Test Bot",
        )

    def test_format_payload(self, notifier, sample_alert):
        """Slack 형식 페이로드가 올바르게 생성된다."""
        payload = notifier._format_payload(sample_alert)

        assert payload["username"] == "Test Bot"
        assert payload["channel"] == "#alerts"
        assert "attachments" in payload

        attachment = payload["attachments"][0]
        assert "color" in attachment
        assert attachment["text"] == sample_alert.message
        assert "fields" in attachment

    def test_format_payload_color_mapping(self, notifier):
        """알림 유형에 따라 색상이 올바르게 지정된다."""
        alert_types_colors = {
            AlertType.KEYWORD_SURGE: "#36a64f",
            AlertType.SENTIMENT_SHIFT: "#ff9500",
            AlertType.ACTIVITY_SPIKE: "#007aff",
            AlertType.NEW_TRENDING: "#5856d6",
            AlertType.CUSTOM: "#8e8e93",
        }

        for alert_type, expected_color in alert_types_colors.items():
            alert = Alert(
                id="test",
                rule_id="test",
                type=alert_type,
                message="Test",
                data={},
                triggered_at=datetime.now(UTC),
            )
            payload = notifier._format_payload(alert)
            assert payload["attachments"][0]["color"] == expected_color

    @pytest.mark.asyncio
    async def test_send_success(self, notifier, sample_alert):
        """Slack 전송이 성공하면 True를 반환한다."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            result = await notifier.send(sample_alert, {})

            assert result is True


# =============================================================================
# DiscordNotifier Tests
# =============================================================================


class TestDiscordNotifier:
    """DiscordNotifier 테스트."""

    @pytest.fixture
    def notifier(self):
        """DiscordNotifier 인스턴스를 생성한다."""
        return DiscordNotifier(
            webhook_url="https://discord.com/api/webhooks/xxx/yyy",
            username="Reddit Insight Test",
        )

    def test_format_payload(self, notifier, sample_alert):
        """Discord 형식 페이로드가 올바르게 생성된다."""
        payload = notifier._format_payload(sample_alert)

        assert payload["username"] == "Reddit Insight Test"
        assert "embeds" in payload

        embed = payload["embeds"][0]
        assert "title" in embed
        assert embed["description"] == sample_alert.message
        assert "color" in embed
        assert "fields" in embed
        assert "timestamp" in embed

    def test_format_payload_fields(self, notifier, sample_alert):
        """Discord 임베드 필드가 올바르게 생성된다."""
        payload = notifier._format_payload(sample_alert)
        fields = payload["embeds"][0]["fields"]

        # 서브레딧 필드 확인
        subreddit_field = next(
            (f for f in fields if f["name"] == "Subreddit"), None
        )
        assert subreddit_field is not None
        assert subreddit_field["value"] == "r/python"

    @pytest.mark.asyncio
    async def test_send_success(self, notifier, sample_alert):
        """Discord 전송이 성공하면 True를 반환한다."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 204  # Discord는 204 반환
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            result = await notifier.send(sample_alert, {})

            assert result is True


# =============================================================================
# ConsoleNotifier Tests
# =============================================================================


class TestConsoleNotifier:
    """ConsoleNotifier 테스트."""

    @pytest.mark.asyncio
    async def test_send_success(self, sample_alert, capsys):
        """콘솔에 알림이 출력된다."""
        notifier = ConsoleNotifier(verbose=True)
        result = await notifier.send(sample_alert, {})

        assert result is True

        captured = capsys.readouterr()
        assert "[ALERT]" in captured.out
        assert "KEYWORD_SURGE" in captured.out
        assert "Keyword surge detected" in captured.out
        assert "r/python" in captured.out

    @pytest.mark.asyncio
    async def test_send_non_verbose(self, sample_alert, capsys):
        """verbose=False이면 상세 정보가 출력되지 않는다."""
        notifier = ConsoleNotifier(verbose=False)
        result = await notifier.send(sample_alert, {})

        assert result is True

        captured = capsys.readouterr()
        assert "[ALERT]" in captured.out
        # verbose=False이면 Details: 섹션이 없음
        assert "Details:" not in captured.out

    @pytest.mark.asyncio
    async def test_send_verbose_with_details(self, sample_alert, capsys):
        """verbose=True이면 상세 정보가 출력된다."""
        notifier = ConsoleNotifier(verbose=True)
        result = await notifier.send(sample_alert, {})

        assert result is True

        captured = capsys.readouterr()
        assert "Details:" in captured.out
        assert "value: 2.5" in captured.out


# =============================================================================
# Integration Tests
# =============================================================================


class TestNotifierIntegration:
    """Notifier 통합 테스트."""

    @pytest.mark.asyncio
    async def test_multiple_notifiers(self, sample_alert):
        """여러 Notifier를 동시에 사용할 수 있다."""
        console = ConsoleNotifier()
        webhook = WebhookNotifier(default_url="https://example.com/hook")

        # 콘솔은 항상 성공
        assert await console.send(sample_alert, {}) is True

        # 웹훅은 mock으로 성공 시뮬레이션
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            assert await webhook.send(sample_alert, {}) is True

    def test_notifier_inheritance(self):
        """SlackNotifier와 DiscordNotifier가 WebhookNotifier를 상속한다."""
        assert issubclass(SlackNotifier, WebhookNotifier)
        assert issubclass(DiscordNotifier, WebhookNotifier)

    @pytest.mark.asyncio
    async def test_alert_with_no_subreddit(self):
        """서브레딧이 없는 알림도 처리할 수 있다."""
        alert = Alert(
            id="alert_002",
            rule_id="rule_002",
            type=AlertType.CUSTOM,
            message="Custom alert without subreddit",
            data={"custom_field": "value"},
            triggered_at=datetime.now(UTC),
            subreddit="",  # 빈 서브레딧
        )

        notifier = ConsoleNotifier()
        result = await notifier.send(alert, {})
        assert result is True
