"""간단한 스케줄러.

SimpleScheduler는 정기적인 데이터 수집을 위한 간단한 인터벌 스케줄러다.
프로덕션에서는 cron, APScheduler 등 전문 스케줄러 사용을 권장한다.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum

from reddit_insight.pipeline.collector import (
    CollectionResult,
    Collector,
    CollectorConfig,
)

logger = logging.getLogger(__name__)


@dataclass
class ScheduleConfig:
    """스케줄 설정.

    정기 수집에 필요한 설정을 담는다.

    Attributes:
        subreddits: 수집할 서브레딧 목록
        interval_minutes: 수집 간격 (분)
        sort: 정렬 방식
        limit: 수집할 게시물 수
        include_comments: 댓글 수집 여부
        comment_limit: 게시물당 수집할 댓글 수
        time_filter: top 정렬 시 기간 필터
    """

    subreddits: list[str]
    interval_minutes: int = 60
    sort: str = "hot"
    limit: int = 100
    include_comments: bool = False
    comment_limit: int = 50
    time_filter: str = "week"

    def to_collector_configs(self) -> list[CollectorConfig]:
        """CollectorConfig 목록으로 변환."""
        return [
            CollectorConfig(
                subreddit=subreddit,
                sort=self.sort,
                limit=self.limit,
                include_comments=self.include_comments,
                comment_limit=self.comment_limit,
                time_filter=self.time_filter,
            )
            for subreddit in self.subreddits
        ]


@dataclass
class ScheduleRun:
    """스케줄 실행 기록.

    Attributes:
        run_id: 실행 ID
        started_at: 시작 시각
        completed_at: 완료 시각
        results: 수집 결과 목록
        success: 성공 여부
        error: 에러 메시지 (실패한 경우)
    """

    run_id: int
    started_at: datetime
    completed_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    results: list[CollectionResult] = field(default_factory=list)
    success: bool = True
    error: str | None = None

    @property
    def duration_seconds(self) -> float:
        """실행 소요 시간 (초)."""
        return (self.completed_at - self.started_at).total_seconds()

    @property
    def total_new_posts(self) -> int:
        """새로 수집한 게시물 수."""
        return sum(r.posts_result.new for r in self.results)

    def to_dict(self) -> dict:
        """딕셔너리로 변환."""
        return {
            "run_id": self.run_id,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat(),
            "duration_seconds": self.duration_seconds,
            "success": self.success,
            "total_new_posts": self.total_new_posts,
            "subreddits_collected": len(self.results),
            "error": self.error,
        }


class SchedulerState(Enum):
    """스케줄러 상태."""

    IDLE = "idle"
    RUNNING = "running"
    STOPPED = "stopped"


@dataclass
class SchedulerStatus:
    """스케줄러 상태 정보.

    Attributes:
        state: 현재 상태
        last_run: 마지막 실행 기록
        next_run_at: 다음 실행 예정 시각
        total_runs: 총 실행 횟수
        successful_runs: 성공한 실행 횟수
        failed_runs: 실패한 실행 횟수
        total_posts_collected: 총 수집된 게시물 수
    """

    state: SchedulerState = SchedulerState.IDLE
    last_run: ScheduleRun | None = None
    next_run_at: datetime | None = None
    total_runs: int = 0
    successful_runs: int = 0
    failed_runs: int = 0
    total_posts_collected: int = 0

    def to_dict(self) -> dict:
        """딕셔너리로 변환."""
        return {
            "state": self.state.value,
            "last_run": self.last_run.to_dict() if self.last_run else None,
            "next_run_at": self.next_run_at.isoformat() if self.next_run_at else None,
            "total_runs": self.total_runs,
            "successful_runs": self.successful_runs,
            "failed_runs": self.failed_runs,
            "total_posts_collected": self.total_posts_collected,
        }


class SimpleScheduler:
    """간단한 인터벌 스케줄러.

    asyncio.sleep()을 사용한 간단한 스케줄러다.
    프로덕션에서는 cron, APScheduler 등 전문 스케줄러 사용을 권장한다.

    Example:
        >>> async with Collector() as collector:
        ...     config = ScheduleConfig(
        ...         subreddits=["python", "programming"],
        ...         interval_minutes=30,
        ...     )
        ...     scheduler = SimpleScheduler(collector, config)
        ...
        ...     # 한 번만 실행
        ...     results = await scheduler.run_once()
        ...
        ...     # 3번 반복 실행
        ...     await scheduler.start(max_runs=3)
    """

    def __init__(
        self,
        collector: Collector,
        config: ScheduleConfig,
    ) -> None:
        """SimpleScheduler 초기화.

        Args:
            collector: Collector 인스턴스 (이미 연결된 상태여야 함)
            config: 스케줄 설정
        """
        self._collector = collector
        self._config = config
        self._running = False
        self._run_count = 0
        self._run_history: list[ScheduleRun] = []
        self._status = SchedulerStatus()

    @property
    def config(self) -> ScheduleConfig:
        """현재 스케줄 설정."""
        return self._config

    @config.setter
    def config(self, value: ScheduleConfig) -> None:
        """스케줄 설정 변경."""
        self._config = value

    @property
    def is_running(self) -> bool:
        """실행 중 여부."""
        return self._running

    @property
    def run_history(self) -> list[ScheduleRun]:
        """실행 이력."""
        return self._run_history.copy()

    def get_status(self) -> SchedulerStatus:
        """현재 상태 반환."""
        return self._status

    async def run_once(self) -> list[CollectionResult]:
        """한 번 실행.

        Returns:
            list[CollectionResult]: 수집 결과 목록
        """
        self._run_count += 1
        run_id = self._run_count
        started_at = datetime.now(UTC)

        logger.info(f"스케줄 실행 #{run_id} 시작")

        run = ScheduleRun(
            run_id=run_id,
            started_at=started_at,
        )

        try:
            configs = self._config.to_collector_configs()
            results = await self._collector.collect_multiple(configs)

            run.results = results
            run.completed_at = datetime.now(UTC)
            run.success = all(r.success for r in results)

            # 상태 업데이트
            self._status.total_runs += 1
            if run.success:
                self._status.successful_runs += 1
            else:
                self._status.failed_runs += 1
            self._status.total_posts_collected += run.total_new_posts

            logger.info(
                f"스케줄 실행 #{run_id} 완료: "
                f"{run.total_new_posts} 새 게시물, "
                f"{run.duration_seconds:.2f}초"
            )

        except Exception as e:
            run.completed_at = datetime.now(UTC)
            run.success = False
            run.error = str(e)
            self._status.total_runs += 1
            self._status.failed_runs += 1
            logger.error(f"스케줄 실행 #{run_id} 실패: {e}")

        self._run_history.append(run)
        self._status.last_run = run

        return run.results

    async def start(self, max_runs: int | None = None) -> None:
        """반복 실행 시작.

        Args:
            max_runs: 최대 실행 횟수. None이면 stop() 호출 전까지 무한 반복
        """
        if self._running:
            logger.warning("스케줄러가 이미 실행 중입니다")
            return

        self._running = True
        self._status.state = SchedulerState.RUNNING
        runs_completed = 0

        logger.info(
            f"스케줄러 시작: "
            f"{len(self._config.subreddits)}개 서브레딧, "
            f"{self._config.interval_minutes}분 간격"
            + (f", 최대 {max_runs}회" if max_runs else "")
        )

        try:
            while self._running:
                # 실행
                await self.run_once()
                runs_completed += 1

                # 최대 횟수 체크
                if max_runs is not None and runs_completed >= max_runs:
                    logger.info(f"최대 실행 횟수 {max_runs}회 도달, 중지")
                    break

                # 다음 실행까지 대기
                if self._running:
                    interval_seconds = self._config.interval_minutes * 60
                    next_run_at = datetime.now(UTC).replace(
                        second=0, microsecond=0
                    )
                    # 실제 다음 실행 시각 계산
                    from datetime import timedelta
                    next_run_at = datetime.now(UTC) + timedelta(
                        seconds=interval_seconds
                    )
                    self._status.next_run_at = next_run_at

                    logger.info(
                        f"다음 실행까지 {self._config.interval_minutes}분 대기 "
                        f"(예정: {next_run_at.isoformat()})"
                    )
                    await asyncio.sleep(interval_seconds)

        except asyncio.CancelledError:
            logger.info("스케줄러 취소됨")
            raise
        finally:
            self._running = False
            self._status.state = SchedulerState.STOPPED
            self._status.next_run_at = None

        logger.info(
            f"스케줄러 종료: 총 {runs_completed}회 실행, "
            f"총 {self._status.total_posts_collected} 게시물 수집"
        )

    def stop(self) -> None:
        """실행 중지.

        다음 실행 전까지 기다린 후 중지된다.
        즉시 중지가 필요하면 asyncio.Task.cancel()을 사용한다.
        """
        if not self._running:
            logger.warning("스케줄러가 실행 중이 아닙니다")
            return

        logger.info("스케줄러 중지 요청")
        self._running = False

    def clear_history(self) -> None:
        """실행 이력 초기화."""
        self._run_history.clear()
        self._status = SchedulerStatus()
        logger.info("스케줄러 이력 초기화")
