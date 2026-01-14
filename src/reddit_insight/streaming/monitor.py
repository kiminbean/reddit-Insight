"""서브레딧 실시간 모니터.

서브레딧의 새 게시물과 활동 변화를 실시간으로 모니터링한다.
폴링 기반으로 동작하며, SSE 스트림을 통해 클라이언트에 업데이트를 전송한다.
"""

from __future__ import annotations

import asyncio
import logging
from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from reddit_insight.data_source import UnifiedDataSource
    from reddit_insight.reddit.models import Post

logger = logging.getLogger(__name__)


class LiveUpdateType(str, Enum):
    """실시간 업데이트 유형.

    Values:
        NEW_POST: 새 게시물 감지
        ACTIVITY_SPIKE: 활동량 급증 감지
        KEYWORD_SURGE: 키워드 급등 감지
        STATUS: 상태 메시지 (연결, 헬스체크 등)
    """

    NEW_POST = "new_post"
    ACTIVITY_SPIKE = "activity_spike"
    KEYWORD_SURGE = "keyword_surge"
    STATUS = "status"


@dataclass
class LiveUpdate:
    """실시간 업데이트 데이터.

    SSE를 통해 클라이언트로 전송되는 업데이트 정보.

    Attributes:
        type: 업데이트 유형
        timestamp: 업데이트 생성 시간
        data: 업데이트 데이터 (유형에 따라 다름)
        subreddit: 업데이트가 발생한 서브레딧
    """

    type: LiveUpdateType
    timestamp: datetime
    data: dict[str, Any]
    subreddit: str = ""

    def to_dict(self) -> dict[str, Any]:
        """딕셔너리로 변환한다.

        Returns:
            JSON 직렬화 가능한 딕셔너리
        """
        return {
            "type": self.type.value,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
            "subreddit": self.subreddit,
        }

    @classmethod
    def new_post(cls, post: "Post", subreddit: str) -> "LiveUpdate":
        """새 게시물 업데이트를 생성한다.

        Args:
            post: 새로 감지된 게시물
            subreddit: 서브레딧 이름

        Returns:
            새 게시물 업데이트
        """
        return cls(
            type=LiveUpdateType.NEW_POST,
            timestamp=datetime.now(UTC),
            data={
                "id": post.id,
                "title": post.title,
                "author": post.author,
                "score": post.score,
                "num_comments": post.num_comments,
                "url": post.url,
                "created_utc": post.created_utc.isoformat(),
            },
            subreddit=subreddit,
        )

    @classmethod
    def activity_spike(
        cls,
        subreddit: str,
        current_rate: float,
        baseline_rate: float,
        spike_factor: float,
    ) -> "LiveUpdate":
        """활동량 급증 업데이트를 생성한다.

        Args:
            subreddit: 서브레딧 이름
            current_rate: 현재 활동률 (posts/minute)
            baseline_rate: 기준 활동률
            spike_factor: 급증 배수

        Returns:
            활동량 급증 업데이트
        """
        return cls(
            type=LiveUpdateType.ACTIVITY_SPIKE,
            timestamp=datetime.now(UTC),
            data={
                "current_rate": round(current_rate, 2),
                "baseline_rate": round(baseline_rate, 2),
                "spike_factor": round(spike_factor, 2),
                "message": f"Activity {spike_factor:.1f}x higher than baseline",
            },
            subreddit=subreddit,
        )

    @classmethod
    def status(cls, message: str, subreddit: str = "") -> "LiveUpdate":
        """상태 메시지 업데이트를 생성한다.

        Args:
            message: 상태 메시지
            subreddit: 서브레딧 이름 (옵션)

        Returns:
            상태 업데이트
        """
        return cls(
            type=LiveUpdateType.STATUS,
            timestamp=datetime.now(UTC),
            data={"message": message},
            subreddit=subreddit,
        )


@dataclass
class ActivityTracker:
    """활동량 추적기.

    시간대별 게시물 수를 추적하여 활동량 급증을 감지한다.

    Attributes:
        window_size: 추적 윈도우 크기 (기록 개수)
        spike_threshold: 급증 판정 임계값 (배수)
    """

    window_size: int = 10
    spike_threshold: float = 2.0
    _post_counts: deque[int] = field(default_factory=lambda: deque(maxlen=10))

    def record(self, count: int) -> tuple[bool, float]:
        """게시물 수를 기록하고 급증 여부를 판정한다.

        Args:
            count: 현재 기간의 새 게시물 수

        Returns:
            (급증 여부, 급증 배수) 튜플
        """
        if len(self._post_counts) < 3:
            # 데이터가 충분하지 않으면 급증 판정 불가
            self._post_counts.append(count)
            return False, 1.0

        # 기준 활동률 계산 (이전 기록들의 평균)
        baseline = sum(self._post_counts) / len(self._post_counts)

        # 급증 배수 계산
        if baseline > 0:
            spike_factor = count / baseline
        else:
            spike_factor = count if count > 0 else 1.0

        self._post_counts.append(count)

        # 급증 판정
        is_spike = spike_factor >= self.spike_threshold and count >= 2

        return is_spike, spike_factor

    def get_baseline(self) -> float:
        """기준 활동률을 반환한다.

        Returns:
            평균 게시물 수 (posts/interval)
        """
        if not self._post_counts:
            return 0.0
        return sum(self._post_counts) / len(self._post_counts)


class SubredditMonitor:
    """서브레딧 실시간 모니터.

    지정된 서브레딧의 새 게시물과 활동량 변화를 폴링 방식으로 모니터링한다.
    SSE 클라이언트가 subscribe()로 구독하면, 업데이트가 발생할 때마다 Queue에 전달된다.

    Attributes:
        subreddit: 모니터링 대상 서브레딧 이름
        interval: 폴링 간격 (초)

    Example:
        >>> monitor = SubredditMonitor("python", data_source, interval=30)
        >>> asyncio.create_task(monitor.start())
        >>> queue = await monitor.subscribe()
        >>> while True:
        ...     update = await queue.get()
        ...     print(f"New update: {update.type}")
    """

    def __init__(
        self,
        subreddit: str,
        data_source: "UnifiedDataSource",
        *,
        interval: int = 30,
        max_posts_per_poll: int = 25,
    ) -> None:
        """SubredditMonitor 초기화.

        Args:
            subreddit: 모니터링할 서브레딧 이름
            data_source: 데이터 소스 (UnifiedDataSource)
            interval: 폴링 간격 (초, 기본: 30)
            max_posts_per_poll: 폴링당 최대 수집 게시물 수 (기본: 25)
        """
        self.subreddit = subreddit
        self._data_source = data_source
        self.interval = interval
        self._max_posts = max_posts_per_poll

        self._running = False
        self._task: asyncio.Task | None = None
        self._last_post_id: str | None = None
        self._seen_post_ids: set[str] = set()
        self._subscribers: list[asyncio.Queue[LiveUpdate]] = []
        self._activity_tracker = ActivityTracker()

        logger.info(
            "SubredditMonitor created: r/%s (interval=%ds)",
            subreddit,
            interval,
        )

    @property
    def is_running(self) -> bool:
        """모니터링 실행 중 여부."""
        return self._running

    @property
    def subscriber_count(self) -> int:
        """현재 구독자 수."""
        return len(self._subscribers)

    async def start(self) -> None:
        """모니터링을 시작한다.

        백그라운드 태스크로 폴링을 시작한다.
        이미 실행 중이면 아무 작업도 하지 않는다.
        """
        if self._running:
            logger.debug("Monitor already running: r/%s", self.subreddit)
            return

        self._running = True
        logger.info("Starting monitor: r/%s", self.subreddit)

        # 시작 상태 알림
        await self._broadcast(
            LiveUpdate.status(f"Started monitoring r/{self.subreddit}", self.subreddit)
        )

        # 백그라운드 폴링 시작
        while self._running:
            try:
                updates = await self._check_updates()
                for update in updates:
                    await self._broadcast(update)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in monitor loop: %s", e)
                # 에러 알림
                await self._broadcast(
                    LiveUpdate.status(f"Error: {str(e)[:100]}", self.subreddit)
                )

            await asyncio.sleep(self.interval)

        logger.info("Monitor stopped: r/%s", self.subreddit)

    async def stop(self) -> None:
        """모니터링을 중지한다.

        실행 중인 폴링 루프를 종료하고 모든 구독자에게 종료 알림을 보낸다.
        """
        if not self._running:
            return

        self._running = False
        logger.info("Stopping monitor: r/%s", self.subreddit)

        # 종료 상태 알림
        await self._broadcast(
            LiveUpdate.status(f"Stopped monitoring r/{self.subreddit}", self.subreddit)
        )

        # 백그라운드 태스크 취소
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def subscribe(self) -> asyncio.Queue[LiveUpdate]:
        """업데이트를 구독한다.

        SSE 클라이언트가 호출하여 업데이트를 받을 Queue를 얻는다.

        Returns:
            업데이트를 받을 asyncio.Queue
        """
        queue: asyncio.Queue[LiveUpdate] = asyncio.Queue()
        self._subscribers.append(queue)
        logger.debug(
            "New subscriber for r/%s (total: %d)",
            self.subreddit,
            len(self._subscribers),
        )
        return queue

    def unsubscribe(self, queue: asyncio.Queue[LiveUpdate]) -> None:
        """구독을 해제한다.

        Args:
            queue: 구독 시 반환받은 Queue
        """
        if queue in self._subscribers:
            self._subscribers.remove(queue)
            logger.debug(
                "Subscriber removed for r/%s (remaining: %d)",
                self.subreddit,
                len(self._subscribers),
            )

    async def _check_updates(self) -> list[LiveUpdate]:
        """새 게시물 및 활동 변화를 확인한다.

        Returns:
            감지된 업데이트 목록
        """
        updates: list[LiveUpdate] = []

        try:
            # 새 게시물 수집
            posts = await self._data_source.get_new_posts(
                self.subreddit, limit=self._max_posts
            )

            if not posts:
                return updates

            # 새 게시물 필터링
            new_posts = []
            for post in posts:
                if post.id not in self._seen_post_ids:
                    new_posts.append(post)
                    self._seen_post_ids.add(post.id)

            # seen_post_ids가 너무 커지지 않도록 관리
            if len(self._seen_post_ids) > 1000:
                # 가장 최근 500개만 유지
                recent_ids = {p.id for p in posts[:500]}
                self._seen_post_ids = recent_ids

            # 새 게시물 업데이트 생성
            for post in new_posts[:10]:  # 한 번에 최대 10개
                updates.append(LiveUpdate.new_post(post, self.subreddit))

            # 활동량 급증 체크
            is_spike, spike_factor = self._activity_tracker.record(len(new_posts))

            if is_spike:
                baseline = self._activity_tracker.get_baseline()
                updates.append(
                    LiveUpdate.activity_spike(
                        subreddit=self.subreddit,
                        current_rate=len(new_posts) / (self.interval / 60),
                        baseline_rate=baseline / (self.interval / 60),
                        spike_factor=spike_factor,
                    )
                )

            logger.debug(
                "r/%s: %d new posts, %d total updates",
                self.subreddit,
                len(new_posts),
                len(updates),
            )

        except Exception as e:
            logger.error("Failed to check updates for r/%s: %s", self.subreddit, e)
            # 에러는 상위에서 처리

        return updates

    async def _broadcast(self, update: LiveUpdate) -> None:
        """모든 구독자에게 업데이트를 전송한다.

        Args:
            update: 전송할 업데이트
        """
        # 끊어진 구독자 제거를 위한 리스트
        dead_subscribers = []

        for queue in self._subscribers:
            try:
                # 논블로킹으로 전송 시도
                queue.put_nowait(update)
            except asyncio.QueueFull:
                # Queue가 가득 찬 경우 (느린 클라이언트)
                logger.warning("Queue full, dropping update for slow client")
            except Exception as e:
                logger.error("Failed to send update: %s", e)
                dead_subscribers.append(queue)

        # 끊어진 구독자 제거
        for queue in dead_subscribers:
            self.unsubscribe(queue)

    def __repr__(self) -> str:
        """문자열 표현."""
        status = "running" if self._running else "stopped"
        return (
            f"SubredditMonitor("
            f"subreddit=r/{self.subreddit}, "
            f"status={status}, "
            f"subscribers={len(self._subscribers)}"
            f")"
        )
