"""라이브 스트리밍 서비스.

서브레딧 실시간 모니터링을 관리하는 서비스.
여러 서브레딧의 모니터를 생성하고 관리하며, SSE 스트림을 위한 인터페이스를 제공한다.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from reddit_insight.streaming.monitor import LiveUpdate, SubredditMonitor

logger = logging.getLogger(__name__)


class LiveService:
    """라이브 스트리밍 서비스.

    서브레딧별 모니터를 관리하고, SSE 클라이언트에게 업데이트 스트림을 제공한다.

    Attributes:
        default_interval: 기본 폴링 간격 (초)

    Example:
        >>> service = LiveService()
        >>> monitor = await service.start_monitoring("python")
        >>> queue = await monitor.subscribe()
        >>> async for update in queue:
        ...     print(update)
    """

    def __init__(self, default_interval: int = 30) -> None:
        """LiveService 초기화.

        Args:
            default_interval: 기본 폴링 간격 (초)
        """
        self.default_interval = default_interval
        self._monitors: dict[str, SubredditMonitor] = {}
        self._tasks: dict[str, asyncio.Task] = {}
        self._data_source = None

    def _get_data_source(self):
        """데이터 소스를 지연 초기화한다."""
        if self._data_source is None:
            from reddit_insight.data_source import UnifiedDataSource

            self._data_source = UnifiedDataSource()
        return self._data_source

    async def start_monitoring(
        self,
        subreddit: str,
        *,
        interval: int | None = None,
    ) -> "SubredditMonitor":
        """서브레딧 모니터링을 시작한다.

        이미 모니터링 중인 서브레딧이면 기존 모니터를 반환한다.

        Args:
            subreddit: 모니터링할 서브레딧 이름
            interval: 폴링 간격 (초). None이면 기본값 사용.

        Returns:
            SubredditMonitor: 해당 서브레딧의 모니터 인스턴스
        """
        subreddit = subreddit.lower().strip()

        # 이미 모니터링 중이면 기존 모니터 반환
        if subreddit in self._monitors:
            monitor = self._monitors[subreddit]
            if monitor.is_running:
                logger.debug("Already monitoring r/%s", subreddit)
                return monitor

        # 새 모니터 생성
        from reddit_insight.streaming.monitor import SubredditMonitor

        poll_interval = interval or self.default_interval
        data_source = self._get_data_source()

        monitor = SubredditMonitor(
            subreddit=subreddit,
            data_source=data_source,
            interval=poll_interval,
        )

        self._monitors[subreddit] = monitor

        # 백그라운드 태스크로 시작
        task = asyncio.create_task(monitor.start())
        self._tasks[subreddit] = task

        logger.info(
            "Started monitoring r/%s (interval=%ds)",
            subreddit,
            poll_interval,
        )

        return monitor

    async def stop_monitoring(self, subreddit: str) -> bool:
        """서브레딧 모니터링을 중지한다.

        Args:
            subreddit: 중지할 서브레딧 이름

        Returns:
            bool: 성공적으로 중지되었으면 True
        """
        subreddit = subreddit.lower().strip()

        if subreddit not in self._monitors:
            logger.warning("Not monitoring r/%s", subreddit)
            return False

        monitor = self._monitors[subreddit]
        await monitor.stop()

        # 태스크 정리
        if subreddit in self._tasks:
            task = self._tasks[subreddit]
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            del self._tasks[subreddit]

        del self._monitors[subreddit]

        logger.info("Stopped monitoring r/%s", subreddit)
        return True

    def get_monitor(self, subreddit: str) -> "SubredditMonitor | None":
        """서브레딧의 모니터를 반환한다.

        Args:
            subreddit: 서브레딧 이름

        Returns:
            SubredditMonitor | None: 모니터 인스턴스 또는 None
        """
        return self._monitors.get(subreddit.lower().strip())

    def get_active_monitors(self) -> list[str]:
        """활성 모니터 목록을 반환한다.

        Returns:
            활성 모니터의 서브레딧 이름 목록
        """
        return [
            subreddit
            for subreddit, monitor in self._monitors.items()
            if monitor.is_running
        ]

    def get_monitor_stats(self) -> dict[str, dict]:
        """모든 모니터의 상태를 반환한다.

        Returns:
            서브레딧별 상태 정보 딕셔너리
        """
        return {
            subreddit: {
                "is_running": monitor.is_running,
                "subscriber_count": monitor.subscriber_count,
                "interval": monitor.interval,
            }
            for subreddit, monitor in self._monitors.items()
        }

    async def subscribe(self, subreddit: str) -> "asyncio.Queue[LiveUpdate]":
        """서브레딧의 업데이트를 구독한다.

        모니터링이 시작되어 있지 않으면 자동으로 시작한다.

        Args:
            subreddit: 구독할 서브레딧 이름

        Returns:
            업데이트를 받을 Queue
        """
        monitor = self._monitors.get(subreddit.lower().strip())

        if monitor is None or not monitor.is_running:
            monitor = await self.start_monitoring(subreddit)

        return await monitor.subscribe()

    def unsubscribe(
        self,
        subreddit: str,
        queue: "asyncio.Queue[LiveUpdate]",
    ) -> None:
        """구독을 해제한다.

        Args:
            subreddit: 서브레딧 이름
            queue: 구독 시 반환받은 Queue
        """
        monitor = self._monitors.get(subreddit.lower().strip())
        if monitor:
            monitor.unsubscribe(queue)

    async def shutdown(self) -> None:
        """서비스를 종료하고 모든 모니터를 중지한다."""
        logger.info("Shutting down LiveService...")

        # 모든 모니터 중지
        subreddits = list(self._monitors.keys())
        for subreddit in subreddits:
            await self.stop_monitoring(subreddit)

        # 데이터 소스 정리
        if self._data_source:
            await self._data_source.close()
            self._data_source = None

        logger.info("LiveService shutdown complete")


# =============================================================================
# Singleton Pattern
# =============================================================================

_live_service: LiveService | None = None


def get_live_service() -> LiveService:
    """LiveService 싱글톤 인스턴스를 반환한다.

    Returns:
        LiveService: 싱글톤 인스턴스
    """
    global _live_service
    if _live_service is None:
        _live_service = LiveService()
    return _live_service


def reset_live_service() -> None:
    """LiveService 싱글톤을 리셋한다.

    테스트에서 사용한다.
    """
    global _live_service
    if _live_service is not None:
        # 비동기 shutdown은 별도로 호출해야 함
        _live_service = None
