"""AlertManager 테스트.

알림 관리자의 규칙 관리, 알림 생성, 알림 전송 기능 테스트.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from reddit_insight.alerts.manager import Alert, AlertManager
from reddit_insight.alerts.rules import AlertCondition, AlertRule, AlertType


# =============================================================================
# AlertCondition Tests
# =============================================================================


class TestAlertCondition:
    """AlertCondition 테스트."""

    def test_evaluate_gte(self):
        """gte 비교가 올바르게 동작한다."""
        condition = AlertCondition(threshold=10.0, comparison="gte")

        assert condition.evaluate(10.0) is True
        assert condition.evaluate(15.0) is True
        assert condition.evaluate(9.9) is False

    def test_evaluate_gt(self):
        """gt 비교가 올바르게 동작한다."""
        condition = AlertCondition(threshold=10.0, comparison="gt")

        assert condition.evaluate(10.0) is False
        assert condition.evaluate(10.1) is True
        assert condition.evaluate(9.9) is False

    def test_evaluate_lte(self):
        """lte 비교가 올바르게 동작한다."""
        condition = AlertCondition(threshold=5.0, comparison="lte")

        assert condition.evaluate(5.0) is True
        assert condition.evaluate(4.0) is True
        assert condition.evaluate(6.0) is False

    def test_evaluate_lt(self):
        """lt 비교가 올바르게 동작한다."""
        condition = AlertCondition(threshold=5.0, comparison="lt")

        assert condition.evaluate(5.0) is False
        assert condition.evaluate(4.9) is True
        assert condition.evaluate(6.0) is False

    def test_evaluate_eq(self):
        """eq 비교가 올바르게 동작한다."""
        condition = AlertCondition(threshold=10.0, comparison="eq")

        assert condition.evaluate(10.0) is True
        assert condition.evaluate(10.1) is False
        assert condition.evaluate(9.9) is False

    def test_to_dict(self):
        """to_dict()가 올바른 딕셔너리를 반환한다."""
        condition = AlertCondition(
            threshold=10.0,
            window_minutes=30,
            comparison="gte",
            field="score",
        )

        result = condition.to_dict()

        assert result["threshold"] == 10.0
        assert result["window_minutes"] == 30
        assert result["comparison"] == "gte"
        assert result["field"] == "score"

    def test_from_dict(self):
        """from_dict()가 올바르게 생성한다."""
        data = {
            "threshold": 15.0,
            "window_minutes": 60,
            "comparison": "lt",
            "field": "sentiment",
        }

        condition = AlertCondition.from_dict(data)

        assert condition.threshold == 15.0
        assert condition.window_minutes == 60
        assert condition.comparison == "lt"
        assert condition.field == "sentiment"


# =============================================================================
# AlertRule Tests
# =============================================================================


class TestAlertRule:
    """AlertRule 테스트."""

    @pytest.fixture
    def sample_rule(self):
        """샘플 규칙을 생성한다."""
        return AlertRule(
            id="rule_001",
            name="Test Rule",
            type=AlertType.KEYWORD_SURGE,
            subreddit="python",
            condition=AlertCondition(threshold=2.0),
            notifiers=["email", "webhook"],
            enabled=True,
        )

    def test_matches_correct_type_and_subreddit(self, sample_rule):
        """유형과 서브레딧이 일치하면 매치된다."""
        assert sample_rule.matches("python", AlertType.KEYWORD_SURGE) is True

    def test_matches_case_insensitive_subreddit(self, sample_rule):
        """서브레딧 비교는 대소문자를 구분하지 않는다."""
        assert sample_rule.matches("Python", AlertType.KEYWORD_SURGE) is True
        assert sample_rule.matches("PYTHON", AlertType.KEYWORD_SURGE) is True

    def test_matches_wrong_type(self, sample_rule):
        """유형이 다르면 매치되지 않는다."""
        assert sample_rule.matches("python", AlertType.SENTIMENT_SHIFT) is False

    def test_matches_wrong_subreddit(self, sample_rule):
        """서브레딧이 다르면 매치되지 않는다."""
        assert sample_rule.matches("java", AlertType.KEYWORD_SURGE) is False

    def test_matches_disabled_rule(self, sample_rule):
        """비활성화된 규칙은 매치되지 않는다."""
        sample_rule.enabled = False
        assert sample_rule.matches("python", AlertType.KEYWORD_SURGE) is False

    def test_matches_empty_subreddit_matches_all(self):
        """빈 서브레딧은 모든 서브레딧에 매치된다."""
        rule = AlertRule(
            id="rule_002",
            name="Global Rule",
            type=AlertType.ACTIVITY_SPIKE,
            subreddit="",  # 모든 서브레딧
            condition=AlertCondition(threshold=2.0),
        )

        assert rule.matches("python", AlertType.ACTIVITY_SPIKE) is True
        assert rule.matches("java", AlertType.ACTIVITY_SPIKE) is True
        assert rule.matches("rust", AlertType.ACTIVITY_SPIKE) is True

    def test_to_dict(self, sample_rule):
        """to_dict()가 올바른 딕셔너리를 반환한다."""
        result = sample_rule.to_dict()

        assert result["id"] == "rule_001"
        assert result["name"] == "Test Rule"
        assert result["type"] == "keyword_surge"
        assert result["subreddit"] == "python"
        assert result["enabled"] is True
        assert "email" in result["notifiers"]

    def test_from_dict(self):
        """from_dict()가 올바르게 생성한다."""
        data = {
            "id": "rule_003",
            "name": "Imported Rule",
            "type": "sentiment_shift",
            "subreddit": "news",
            "condition": {"threshold": -0.5, "comparison": "lte"},
            "notifiers": ["webhook"],
            "enabled": False,
        }

        rule = AlertRule.from_dict(data)

        assert rule.id == "rule_003"
        assert rule.name == "Imported Rule"
        assert rule.type == AlertType.SENTIMENT_SHIFT
        assert rule.subreddit == "news"
        assert rule.condition.threshold == -0.5
        assert rule.enabled is False


# =============================================================================
# Alert Tests
# =============================================================================


class TestAlert:
    """Alert 테스트."""

    def test_to_dict(self):
        """to_dict()가 올바른 딕셔너리를 반환한다."""
        alert = Alert(
            id="alert_001",
            rule_id="rule_001",
            type=AlertType.KEYWORD_SURGE,
            message="Test alert",
            data={"value": 2.5},
            triggered_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
            subreddit="python",
            sent=True,
            sent_to=["email"],
        )

        result = alert.to_dict()

        assert result["id"] == "alert_001"
        assert result["rule_id"] == "rule_001"
        assert result["type"] == "keyword_surge"
        assert result["message"] == "Test alert"
        assert result["sent"] is True
        assert "email" in result["sent_to"]

    def test_from_dict(self):
        """from_dict()가 올바르게 생성한다."""
        data = {
            "id": "alert_002",
            "rule_id": "rule_002",
            "type": "activity_spike",
            "message": "Activity spike detected",
            "data": {"value": 3.0},
            "triggered_at": "2024-01-01T12:00:00+00:00",
            "subreddit": "news",
        }

        alert = Alert.from_dict(data)

        assert alert.id == "alert_002"
        assert alert.rule_id == "rule_002"
        assert alert.type == AlertType.ACTIVITY_SPIKE
        assert alert.subreddit == "news"


# =============================================================================
# AlertManager Tests
# =============================================================================


class TestAlertManager:
    """AlertManager 테스트."""

    @pytest.fixture
    def manager(self):
        """AlertManager 인스턴스를 생성한다."""
        return AlertManager(max_history=100)

    @pytest.fixture
    def sample_rule(self):
        """샘플 규칙을 생성한다."""
        return AlertRule(
            id="rule_001",
            name="Test Rule",
            type=AlertType.KEYWORD_SURGE,
            subreddit="python",
            condition=AlertCondition(threshold=2.0, field="value"),
            notifiers=["email"],
            enabled=True,
        )

    @pytest.fixture
    def mock_notifier(self):
        """Mock Notifier를 생성한다."""
        notifier = AsyncMock()
        notifier.send = AsyncMock(return_value=True)
        return notifier

    # -------------------------------------------------------------------------
    # Rule Management Tests
    # -------------------------------------------------------------------------

    def test_add_rule(self, manager, sample_rule):
        """규칙을 추가할 수 있다."""
        manager.add_rule(sample_rule)

        assert len(manager.get_rules()) == 1
        assert manager.get_rule("rule_001") == sample_rule

    def test_add_rule_duplicate_id(self, manager, sample_rule):
        """동일한 ID의 규칙을 추가하면 예외가 발생한다."""
        manager.add_rule(sample_rule)

        with pytest.raises(ValueError, match="already exists"):
            manager.add_rule(sample_rule)

    def test_update_rule(self, manager, sample_rule):
        """규칙을 업데이트할 수 있다."""
        manager.add_rule(sample_rule)

        sample_rule.name = "Updated Rule"
        manager.update_rule(sample_rule)

        assert manager.get_rule("rule_001").name == "Updated Rule"

    def test_update_rule_not_found(self, manager, sample_rule):
        """존재하지 않는 규칙을 업데이트하면 예외가 발생한다."""
        with pytest.raises(KeyError, match="not found"):
            manager.update_rule(sample_rule)

    def test_remove_rule(self, manager, sample_rule):
        """규칙을 제거할 수 있다."""
        manager.add_rule(sample_rule)
        assert manager.remove_rule("rule_001") is True
        assert manager.get_rule("rule_001") is None

    def test_remove_rule_not_found(self, manager):
        """존재하지 않는 규칙을 제거하면 False를 반환한다."""
        assert manager.remove_rule("nonexistent") is False

    def test_get_rules_enabled_only(self, manager):
        """활성화된 규칙만 조회할 수 있다."""
        rule1 = AlertRule(
            id="rule_1",
            name="Enabled Rule",
            type=AlertType.KEYWORD_SURGE,
            subreddit="",
            condition=AlertCondition(threshold=2.0),
            enabled=True,
        )
        rule2 = AlertRule(
            id="rule_2",
            name="Disabled Rule",
            type=AlertType.KEYWORD_SURGE,
            subreddit="",
            condition=AlertCondition(threshold=2.0),
            enabled=False,
        )

        manager.add_rule(rule1)
        manager.add_rule(rule2)

        all_rules = manager.get_rules()
        enabled_rules = manager.get_rules(enabled_only=True)

        assert len(all_rules) == 2
        assert len(enabled_rules) == 1
        assert enabled_rules[0].id == "rule_1"

    def test_enable_disable_rule(self, manager, sample_rule):
        """규칙을 활성화/비활성화할 수 있다."""
        manager.add_rule(sample_rule)

        manager.disable_rule("rule_001")
        assert manager.get_rule("rule_001").enabled is False

        manager.enable_rule("rule_001")
        assert manager.get_rule("rule_001").enabled is True

    # -------------------------------------------------------------------------
    # Notifier Management Tests
    # -------------------------------------------------------------------------

    def test_register_notifier(self, manager, mock_notifier):
        """알림 전송자를 등록할 수 있다."""
        manager.register_notifier("email", mock_notifier)

        assert "email" in manager.get_notifiers()

    def test_unregister_notifier(self, manager, mock_notifier):
        """알림 전송자를 해제할 수 있다."""
        manager.register_notifier("email", mock_notifier)
        assert manager.unregister_notifier("email") is True
        assert "email" not in manager.get_notifiers()

    def test_unregister_notifier_not_found(self, manager):
        """존재하지 않는 알림 전송자를 해제하면 False를 반환한다."""
        assert manager.unregister_notifier("nonexistent") is False

    # -------------------------------------------------------------------------
    # Rule Evaluation Tests
    # -------------------------------------------------------------------------

    def test_check_rules_triggers_alert(self, manager, sample_rule):
        """조건이 충족되면 알림이 생성된다."""
        manager.add_rule(sample_rule)

        metrics = {"value": 2.5}  # threshold(2.0)보다 큼
        alerts = manager.check_rules("python", metrics)

        assert len(alerts) == 1
        assert alerts[0].rule_id == "rule_001"
        assert alerts[0].type == AlertType.KEYWORD_SURGE

    def test_check_rules_no_trigger_below_threshold(self, manager, sample_rule):
        """조건이 충족되지 않으면 알림이 생성되지 않는다."""
        manager.add_rule(sample_rule)

        metrics = {"value": 1.5}  # threshold(2.0)보다 작음
        alerts = manager.check_rules("python", metrics)

        assert len(alerts) == 0

    def test_check_rules_wrong_subreddit(self, manager, sample_rule):
        """다른 서브레딧은 알림을 트리거하지 않는다."""
        manager.add_rule(sample_rule)

        metrics = {"value": 2.5}
        alerts = manager.check_rules("java", metrics)  # 다른 서브레딧

        assert len(alerts) == 0

    def test_check_rules_filter_by_type(self, manager, sample_rule):
        """알림 유형으로 필터링할 수 있다."""
        manager.add_rule(sample_rule)

        metrics = {"value": 2.5}

        # KEYWORD_SURGE 타입으로 필터링하면 알림 생성
        alerts = manager.check_rules(
            "python", metrics, alert_type=AlertType.KEYWORD_SURGE
        )
        assert len(alerts) == 1

        # 다른 타입으로 필터링하면 알림 없음
        alerts = manager.check_rules(
            "python", metrics, alert_type=AlertType.SENTIMENT_SHIFT
        )
        assert len(alerts) == 0

    def test_check_rules_cooldown(self, manager, sample_rule):
        """쿨다운 기간 동안 동일한 규칙은 재트리거되지 않는다."""
        manager.add_rule(sample_rule)
        manager._cooldown_minutes = 5

        metrics = {"value": 2.5}

        # 첫 번째 체크: 알림 생성
        alerts1 = manager.check_rules("python", metrics)
        assert len(alerts1) == 1

        # 두 번째 체크: 쿨다운으로 인해 알림 없음
        alerts2 = manager.check_rules("python", metrics)
        assert len(alerts2) == 0

    # -------------------------------------------------------------------------
    # Alert Processing Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_process_alert(self, manager, sample_rule, mock_notifier):
        """알림을 처리하고 전송한다."""
        manager.add_rule(sample_rule)
        manager.register_notifier("email", mock_notifier)

        alert = Alert(
            id="alert_001",
            rule_id="rule_001",
            type=AlertType.KEYWORD_SURGE,
            message="Test alert",
            data={},
            triggered_at=datetime.now(UTC),
            subreddit="python",
        )

        processed = await manager.process_alert(alert)

        assert processed.sent is True
        assert "email" in processed.sent_to
        mock_notifier.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_alert_notifier_failure(
        self, manager, sample_rule, mock_notifier
    ):
        """알림 전송이 실패하면 에러가 기록된다."""
        mock_notifier.send = AsyncMock(return_value=False)
        manager.add_rule(sample_rule)
        manager.register_notifier("email", mock_notifier)

        alert = Alert(
            id="alert_001",
            rule_id="rule_001",
            type=AlertType.KEYWORD_SURGE,
            message="Test alert",
            data={},
            triggered_at=datetime.now(UTC),
            subreddit="python",
        )

        processed = await manager.process_alert(alert)

        assert processed.sent is False
        assert processed.error is not None

    @pytest.mark.asyncio
    async def test_send_test_alert(self, manager, mock_notifier):
        """테스트 알림을 전송할 수 있다."""
        manager.register_notifier("email", mock_notifier)

        result = await manager.send_test_alert("email")

        assert result is True
        mock_notifier.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_test_alert_notifier_not_found(self, manager):
        """존재하지 않는 알림 전송자로 테스트하면 False를 반환한다."""
        result = await manager.send_test_alert("nonexistent")
        assert result is False

    # -------------------------------------------------------------------------
    # History Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_get_history(self, manager, sample_rule, mock_notifier):
        """알림 이력을 조회할 수 있다."""
        manager.add_rule(sample_rule)
        manager.register_notifier("email", mock_notifier)

        alert = Alert(
            id="alert_001",
            rule_id="rule_001",
            type=AlertType.KEYWORD_SURGE,
            message="Test alert",
            data={},
            triggered_at=datetime.now(UTC),
            subreddit="python",
        )

        await manager.process_alert(alert)

        history = manager.get_history()
        assert len(history) == 1
        assert history[0].id == "alert_001"

    @pytest.mark.asyncio
    async def test_get_history_filter_by_rule(self, manager, mock_notifier):
        """규칙 ID로 이력을 필터링할 수 있다."""
        rule1 = AlertRule(
            id="rule_1",
            name="Rule 1",
            type=AlertType.KEYWORD_SURGE,
            subreddit="",
            condition=AlertCondition(threshold=2.0),
            notifiers=["email"],
        )
        rule2 = AlertRule(
            id="rule_2",
            name="Rule 2",
            type=AlertType.ACTIVITY_SPIKE,
            subreddit="",
            condition=AlertCondition(threshold=2.0),
            notifiers=["email"],
        )

        manager.add_rule(rule1)
        manager.add_rule(rule2)
        manager.register_notifier("email", mock_notifier)

        alert1 = Alert(
            id="alert_1",
            rule_id="rule_1",
            type=AlertType.KEYWORD_SURGE,
            message="Alert 1",
            data={},
            triggered_at=datetime.now(UTC),
        )
        alert2 = Alert(
            id="alert_2",
            rule_id="rule_2",
            type=AlertType.ACTIVITY_SPIKE,
            message="Alert 2",
            data={},
            triggered_at=datetime.now(UTC),
        )

        await manager.process_alert(alert1)
        await manager.process_alert(alert2)

        history = manager.get_history(rule_id="rule_1")
        assert len(history) == 1
        assert history[0].rule_id == "rule_1"

    def test_clear_history(self, manager):
        """이력을 삭제할 수 있다."""
        # 직접 이력에 추가
        manager._history.append(
            Alert(
                id="test",
                rule_id="rule",
                type=AlertType.KEYWORD_SURGE,
                message="Test",
                data={},
                triggered_at=datetime.now(UTC),
            )
        )

        count = manager.clear_history()
        assert count == 1
        assert len(manager.get_history()) == 0

    # -------------------------------------------------------------------------
    # Stats and Export Tests
    # -------------------------------------------------------------------------

    def test_get_stats(self, manager, sample_rule):
        """통계를 조회할 수 있다."""
        manager.add_rule(sample_rule)

        stats = manager.get_stats()

        assert stats["total_rules"] == 1
        assert stats["enabled_rules"] == 1
        assert stats["history_count"] == 0

    def test_export_import_rules(self, manager):
        """규칙을 내보내고 가져올 수 있다."""
        rule = AlertRule(
            id="export_rule",
            name="Export Test",
            type=AlertType.KEYWORD_SURGE,
            subreddit="test",
            condition=AlertCondition(threshold=2.0),
            notifiers=["email"],
        )
        manager.add_rule(rule)

        # 내보내기
        exported = manager.export_rules()
        assert len(exported) == 1
        assert exported[0]["id"] == "export_rule"

        # 새 매니저에 가져오기
        new_manager = AlertManager()
        count = new_manager.import_rules(exported)

        assert count == 1
        assert new_manager.get_rule("export_rule") is not None
