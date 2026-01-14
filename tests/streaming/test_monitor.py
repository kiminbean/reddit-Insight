"""SubredditMonitor 테스트.

실시간 모니터링 기능의 단위 테스트.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from reddit_insight.streaming.monitor import (
    ActivityTracker,
    LiveUpdate,
    LiveUpdateType,
    SubredditMonitor,
)


# =============================================================================
# LiveUpdate Tests
# =============================================================================


class TestLiveUpdate:
    """LiveUpdate 데이터클래스 테스트."""

    def test_to_dict(self):
        """to_dict()가 올바른 딕셔너리를 반환한다."""
        update = LiveUpdate(
            type=LiveUpdateType.NEW_POST,
            timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
            data={"title": "Test Post"},
            subreddit="python",
        )

        result = update.to_dict()

        assert result["type"] == "new_post"
        assert result["timestamp"] == "2024-01-01T12:00:00+00:00"
        assert result["data"] == {"title": "Test Post"}
        assert result["subreddit"] == "python"

    def test_new_post_factory(self):
        """new_post() 팩토리 메서드가 올바른 업데이트를 생성한다."""
        # Mock Post 객체
        mock_post = MagicMock()
        mock_post.id = "abc123"
        mock_post.title = "Test Title"
        mock_post.author = "test_user"
        mock_post.score = 100
        mock_post.num_comments = 25
        mock_post.url = "https://reddit.com/r/python/comments/abc123"
        mock_post.created_utc = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)

        update = LiveUpdate.new_post(mock_post, "python")

        assert update.type == LiveUpdateType.NEW_POST
        assert update.subreddit == "python"
        assert update.data["id"] == "abc123"
        assert update.data["title"] == "Test Title"
        assert update.data["author"] == "test_user"
        assert update.data["score"] == 100

    def test_activity_spike_factory(self):
        """activity_spike() 팩토리 메서드가 올바른 업데이트를 생성한다."""
        update = LiveUpdate.activity_spike(
            subreddit="python",
            current_rate=10.5,
            baseline_rate=3.2,
            spike_factor=3.28,
        )

        assert update.type == LiveUpdateType.ACTIVITY_SPIKE
        assert update.subreddit == "python"
        assert update.data["current_rate"] == 10.5
        assert update.data["baseline_rate"] == 3.2
        assert update.data["spike_factor"] == 3.28
        assert "3.3x higher" in update.data["message"]

    def test_status_factory(self):
        """status() 팩토리 메서드가 올바른 업데이트를 생성한다."""
        update = LiveUpdate.status("Connected", "python")

        assert update.type == LiveUpdateType.STATUS
        assert update.subreddit == "python"
        assert update.data["message"] == "Connected"


# =============================================================================
# ActivityTracker Tests
# =============================================================================


class TestActivityTracker:
    """ActivityTracker 테스트."""

    def test_record_insufficient_data(self):
        """데이터가 충분하지 않으면 급증으로 판정하지 않는다."""
        tracker = ActivityTracker()

        # 처음 3개 기록은 급증 판정 불가
        is_spike, factor = tracker.record(5)
        assert is_spike is False

        is_spike, factor = tracker.record(5)
        assert is_spike is False

        is_spike, factor = tracker.record(5)
        assert is_spike is False

    def test_record_detects_spike(self):
        """활동량 급증을 올바르게 감지한다."""
        tracker = ActivityTracker(spike_threshold=2.0)

        # 기준 데이터 축적
        for _ in range(5):
            tracker.record(2)

        # 급증 발생 (2.0x 이상)
        is_spike, factor = tracker.record(10)

        assert is_spike is True
        assert factor >= 2.0

    def test_record_no_spike_below_threshold(self):
        """임계값 미만이면 급증으로 판정하지 않는다."""
        tracker = ActivityTracker(spike_threshold=2.0)

        # 기준 데이터 축적
        for _ in range(5):
            tracker.record(5)

        # 급증 아님 (1.6x < 2.0)
        is_spike, factor = tracker.record(8)

        assert is_spike is False

    def test_get_baseline(self):
        """기준 활동률을 올바르게 계산한다."""
        tracker = ActivityTracker()

        tracker.record(2)
        tracker.record(4)
        tracker.record(6)

        baseline = tracker.get_baseline()
        assert baseline == 4.0  # (2 + 4 + 6) / 3

    def test_get_baseline_empty(self):
        """데이터가 없으면 기준값 0을 반환한다."""
        tracker = ActivityTracker()
        assert tracker.get_baseline() == 0.0


# =============================================================================
# SubredditMonitor Tests
# =============================================================================


class TestSubredditMonitor:
    """SubredditMonitor 테스트."""

    @pytest.fixture
    def mock_data_source(self):
        """Mock UnifiedDataSource."""
        data_source = AsyncMock()
        data_source.get_new_posts = AsyncMock(return_value=[])
        return data_source

    @pytest.fixture
    def monitor(self, mock_data_source):
        """SubredditMonitor 인스턴스."""
        return SubredditMonitor(
            subreddit="python",
            data_source=mock_data_source,
            interval=1,  # 테스트용 짧은 간격
        )

    def test_init(self, mock_data_source):
        """초기화가 올바르게 수행된다."""
        monitor = SubredditMonitor(
            subreddit="python",
            data_source=mock_data_source,
            interval=30,
            max_posts_per_poll=50,
        )

        assert monitor.subreddit == "python"
        assert monitor.interval == 30
        assert monitor.is_running is False
        assert monitor.subscriber_count == 0

    @pytest.mark.asyncio
    async def test_subscribe(self, monitor):
        """구독이 올바르게 동작한다."""
        assert monitor.subscriber_count == 0

        queue1 = await monitor.subscribe()
        assert monitor.subscriber_count == 1

        queue2 = await monitor.subscribe()
        assert monitor.subscriber_count == 2

        assert isinstance(queue1, asyncio.Queue)
        assert isinstance(queue2, asyncio.Queue)

    @pytest.mark.asyncio
    async def test_unsubscribe(self, monitor):
        """구독 해제가 올바르게 동작한다."""
        queue = await monitor.subscribe()
        assert monitor.subscriber_count == 1

        monitor.unsubscribe(queue)
        assert monitor.subscriber_count == 0

    @pytest.mark.asyncio
    async def test_broadcast(self, monitor):
        """브로드캐스트가 모든 구독자에게 전달된다."""
        queue1 = await monitor.subscribe()
        queue2 = await monitor.subscribe()

        update = LiveUpdate.status("Test message", "python")
        await monitor._broadcast(update)

        # 두 Queue 모두 업데이트를 받아야 함
        received1 = queue1.get_nowait()
        received2 = queue2.get_nowait()

        assert received1.type == LiveUpdateType.STATUS
        assert received2.type == LiveUpdateType.STATUS

    @pytest.mark.asyncio
    async def test_check_updates_new_posts(self, monitor, mock_data_source):
        """새 게시물을 올바르게 감지한다."""
        # Mock 게시물 생성
        mock_post = MagicMock()
        mock_post.id = "new_post_1"
        mock_post.title = "New Post"
        mock_post.author = "user"
        mock_post.score = 10
        mock_post.num_comments = 5
        mock_post.url = "https://reddit.com/r/python/new_post_1"
        mock_post.created_utc = datetime.now(UTC)

        mock_data_source.get_new_posts.return_value = [mock_post]

        updates = await monitor._check_updates()

        # 새 게시물 업데이트가 있어야 함
        new_post_updates = [u for u in updates if u.type == LiveUpdateType.NEW_POST]
        assert len(new_post_updates) == 1
        assert new_post_updates[0].data["id"] == "new_post_1"

    @pytest.mark.asyncio
    async def test_check_updates_no_duplicates(self, monitor, mock_data_source):
        """중복 게시물을 필터링한다."""
        mock_post = MagicMock()
        mock_post.id = "same_post"
        mock_post.title = "Same Post"
        mock_post.author = "user"
        mock_post.score = 10
        mock_post.num_comments = 5
        mock_post.url = "https://reddit.com/r/python/same_post"
        mock_post.created_utc = datetime.now(UTC)

        mock_data_source.get_new_posts.return_value = [mock_post]

        # 첫 번째 호출
        updates1 = await monitor._check_updates()
        new_post_updates1 = [u for u in updates1 if u.type == LiveUpdateType.NEW_POST]
        assert len(new_post_updates1) == 1

        # 두 번째 호출 (같은 게시물)
        updates2 = await monitor._check_updates()
        new_post_updates2 = [u for u in updates2 if u.type == LiveUpdateType.NEW_POST]
        assert len(new_post_updates2) == 0  # 중복이므로 없어야 함

    @pytest.mark.asyncio
    async def test_start_stop(self, monitor):
        """시작과 중지가 올바르게 동작한다."""
        assert monitor.is_running is False

        # 별도 태스크로 실행
        task = asyncio.create_task(monitor.start())

        # 잠시 대기하여 시작되도록 함
        await asyncio.sleep(0.1)
        assert monitor.is_running is True

        # 중지
        await monitor.stop()
        assert monitor.is_running is False

        # 태스크 정리
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    def test_repr(self, monitor):
        """문자열 표현이 올바르다."""
        repr_str = repr(monitor)

        assert "SubredditMonitor" in repr_str
        assert "r/python" in repr_str
        assert "stopped" in repr_str


# =============================================================================
# Integration Tests
# =============================================================================


class TestMonitorIntegration:
    """모니터 통합 테스트."""

    @pytest.mark.asyncio
    async def test_full_flow(self):
        """전체 플로우를 테스트한다."""
        # Mock 데이터 소스
        data_source = AsyncMock()

        # Mock 게시물 시퀀스
        posts_sequence = [
            [],  # 첫 번째 폴링: 빈 결과
            [self._create_mock_post("post1")],  # 두 번째 폴링: 새 게시물
            [self._create_mock_post("post1"), self._create_mock_post("post2")],  # 세 번째
        ]
        data_source.get_new_posts = AsyncMock(side_effect=posts_sequence)

        monitor = SubredditMonitor(
            subreddit="test",
            data_source=data_source,
            interval=0.1,
        )

        # 구독
        queue = await monitor.subscribe()

        # 시작 (백그라운드)
        task = asyncio.create_task(monitor.start())

        try:
            # 첫 번째 메시지는 상태 메시지 (시작 알림)
            update = await asyncio.wait_for(queue.get(), timeout=1.0)
            assert update.type == LiveUpdateType.STATUS

            # 두 번째 폴링 이후 새 게시물 알림
            update = await asyncio.wait_for(queue.get(), timeout=1.0)
            assert update.type == LiveUpdateType.NEW_POST
            assert update.data["id"] == "post1"

        finally:
            await monitor.stop()
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    def _create_mock_post(self, post_id: str) -> MagicMock:
        """Mock 게시물을 생성한다."""
        post = MagicMock()
        post.id = post_id
        post.title = f"Post {post_id}"
        post.author = "user"
        post.score = 10
        post.num_comments = 5
        post.url = f"https://reddit.com/r/test/{post_id}"
        post.created_utc = datetime.now(UTC)
        return post
