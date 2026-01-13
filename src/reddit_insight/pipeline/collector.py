"""데이터 수집기.

Collector 클래스는 UnifiedDataSource와 DataPipeline을 통합하여
서브레딧 데이터 수집을 간편하게 수행한다.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime

from reddit_insight.data_source import DataSourceStrategy, UnifiedDataSource
from reddit_insight.pipeline.data_pipeline import DataPipeline, ProcessingResult
from reddit_insight.storage.database import Database

logger = logging.getLogger(__name__)


@dataclass
class CollectorConfig:
    """수집 설정.

    단일 서브레딧 수집에 필요한 설정을 담는다.

    Attributes:
        subreddit: 서브레딧 이름
        sort: 정렬 방식 (hot, new, top)
        limit: 수집할 게시물 수
        include_comments: 댓글 수집 여부
        comment_limit: 게시물당 수집할 댓글 수
        time_filter: top 정렬 시 기간 필터
    """

    subreddit: str
    sort: str = "hot"
    limit: int = 100
    include_comments: bool = False
    comment_limit: int = 50
    time_filter: str = "week"


@dataclass
class CollectionResult:
    """수집 결과.

    단일 서브레딧 수집 결과를 담는다.

    Attributes:
        subreddit: 서브레딧 이름
        posts_result: 게시물 처리 결과
        comments_result: 댓글 처리 결과 (수집한 경우)
        duration_seconds: 수집 소요 시간 (초)
        collected_at: 수집 시각
        error: 에러 메시지 (실패한 경우)
    """

    subreddit: str
    posts_result: ProcessingResult = field(default_factory=ProcessingResult)
    comments_result: ProcessingResult | None = None
    duration_seconds: float = 0.0
    collected_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    error: str | None = None

    @property
    def success(self) -> bool:
        """수집 성공 여부."""
        return self.error is None

    def to_dict(self) -> dict:
        """딕셔너리로 변환."""
        result = {
            "subreddit": self.subreddit,
            "posts": self.posts_result.to_dict(),
            "duration_seconds": self.duration_seconds,
            "collected_at": self.collected_at.isoformat(),
            "success": self.success,
        }
        if self.comments_result is not None:
            result["comments"] = self.comments_result.to_dict()
        if self.error is not None:
            result["error"] = self.error
        return result


class Collector:
    """데이터 수집기.

    UnifiedDataSource로 데이터를 수집하고 DataPipeline으로 저장한다.
    여러 서브레딧을 순차적으로 수집할 수 있다.

    Example:
        >>> collector = Collector()
        >>> await collector.connect()
        >>> try:
        ...     result = await collector.collect_subreddit(
        ...         CollectorConfig(subreddit="python", limit=50)
        ...     )
        ...     print(f"새 게시물: {result.posts_result.new}")
        ... finally:
        ...     await collector.disconnect()

        >>> # 컨텍스트 매니저 사용
        >>> async with Collector() as collector:
        ...     results = await collector.collect_from_list(
        ...         ["python", "programming"],
        ...         limit=50,
        ...     )
    """

    def __init__(
        self,
        database: Database | None = None,
        data_source: UnifiedDataSource | None = None,
        strategy: DataSourceStrategy = DataSourceStrategy.API_FIRST,
    ) -> None:
        """Collector 초기화.

        Args:
            database: Database 인스턴스. None이면 새로 생성
            data_source: UnifiedDataSource 인스턴스. None이면 새로 생성
            strategy: 데이터 소스 전략 (기본: API_FIRST)
        """
        self._db = database
        self._data_source = data_source
        self._strategy = strategy
        self._pipeline: DataPipeline | None = None
        self._owns_db = database is None
        self._owns_data_source = data_source is None

    async def connect(self) -> None:
        """리소스 연결."""
        # 데이터베이스 연결
        if self._db is None:
            self._db = Database()
            await self._db.connect()
        elif self._db._engine is None:
            await self._db.connect()

        # 파이프라인 생성
        self._pipeline = DataPipeline(self._db)

        # 데이터 소스 생성
        if self._data_source is None:
            self._data_source = UnifiedDataSource(strategy=self._strategy)

        logger.info("Collector 연결 완료")

    async def disconnect(self) -> None:
        """리소스 해제."""
        if self._owns_data_source and self._data_source is not None:
            await self._data_source.close()
            self._data_source = None

        if self._owns_db and self._db is not None:
            await self._db.disconnect()
            self._db = None

        self._pipeline = None
        logger.info("Collector 리소스 해제 완료")

    async def __aenter__(self) -> Collector:
        """비동기 컨텍스트 매니저 진입."""
        await self.connect()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object | None,
    ) -> None:
        """비동기 컨텍스트 매니저 종료."""
        await self.disconnect()

    def _ensure_connected(self) -> None:
        """연결 상태 확인.

        Raises:
            RuntimeError: 연결되지 않은 상태에서 호출 시
        """
        if self._pipeline is None or self._data_source is None:
            raise RuntimeError("Collector가 연결되지 않았습니다. connect()를 먼저 호출하세요.")

    async def collect_subreddit(self, config: CollectorConfig) -> CollectionResult:
        """단일 서브레딧 수집.

        Args:
            config: 수집 설정

        Returns:
            CollectionResult: 수집 결과
        """
        self._ensure_connected()
        assert self._pipeline is not None  # type narrowing
        assert self._data_source is not None  # type narrowing

        start_time = time.monotonic()
        result = CollectionResult(subreddit=config.subreddit)

        try:
            # 서브레딧 정보 수집 및 저장
            try:
                subreddit_info = await self._data_source.get_subreddit_info(
                    config.subreddit
                )
                if subreddit_info is not None:
                    await self._pipeline.ensure_subreddit(subreddit_info)
                    logger.info(f"r/{config.subreddit} 정보 저장 완료")
            except Exception as e:
                logger.warning(f"서브레딧 정보 수집 실패: {e}")

            # 게시물 수집
            if config.sort == "hot":
                posts = await self._data_source.get_hot_posts(
                    config.subreddit, limit=config.limit
                )
            elif config.sort == "new":
                posts = await self._data_source.get_new_posts(
                    config.subreddit, limit=config.limit
                )
            elif config.sort == "top":
                posts = await self._data_source.get_top_posts(
                    config.subreddit,
                    time_filter=config.time_filter,
                    limit=config.limit,
                )
            else:
                logger.warning(f"알 수 없는 정렬 방식: {config.sort}, hot으로 대체")
                posts = await self._data_source.get_hot_posts(
                    config.subreddit, limit=config.limit
                )

            logger.info(
                f"r/{config.subreddit} {config.sort} 게시물 {len(posts)}개 수집 완료"
            )

            # 게시물 처리 및 저장
            result.posts_result = await self._pipeline.process_posts(
                posts, config.subreddit
            )

            # 댓글 수집 (옵션)
            if config.include_comments and posts:
                result.comments_result = ProcessingResult()

                for post in posts:
                    try:
                        comments = await self._data_source.get_post_comments(
                            post.id, limit=config.comment_limit
                        )
                        comment_result = await self._pipeline.process_comments(
                            comments, post.id
                        )
                        result.comments_result = (
                            result.comments_result + comment_result
                        )
                    except Exception as e:
                        logger.warning(f"post/{post.id} 댓글 수집 실패: {e}")
                        result.comments_result.errors += 1

                logger.info(
                    f"r/{config.subreddit} 댓글 수집 완료: "
                    f"new={result.comments_result.new}, "
                    f"duplicates={result.comments_result.duplicates}"
                )

        except Exception as e:
            result.error = str(e)
            logger.error(f"r/{config.subreddit} 수집 실패: {e}")

        result.duration_seconds = time.monotonic() - start_time
        result.collected_at = datetime.now(UTC)

        logger.info(
            f"r/{config.subreddit} 수집 완료: "
            f"{result.duration_seconds:.2f}초, "
            f"posts={result.posts_result.new} new"
        )

        return result

    async def collect_multiple(
        self, configs: list[CollectorConfig]
    ) -> list[CollectionResult]:
        """여러 서브레딧 순차 수집.

        Args:
            configs: 수집 설정 목록

        Returns:
            list[CollectionResult]: 수집 결과 목록
        """
        results: list[CollectionResult] = []

        for config in configs:
            result = await self.collect_subreddit(config)
            results.append(result)

        # 통계 로깅
        total_posts = sum(r.posts_result.new for r in results)
        total_time = sum(r.duration_seconds for r in results)
        success_count = sum(1 for r in results if r.success)

        logger.info(
            f"전체 수집 완료: "
            f"{success_count}/{len(configs)} 성공, "
            f"새 게시물 {total_posts}개, "
            f"총 {total_time:.2f}초"
        )

        return results

    async def collect_from_list(
        self,
        subreddits: list[str],
        sort: str = "hot",
        limit: int = 100,
        include_comments: bool = False,
        comment_limit: int = 50,
        time_filter: str = "week",
    ) -> list[CollectionResult]:
        """서브레딧 목록으로 간편 수집.

        Args:
            subreddits: 서브레딧 이름 목록
            sort: 정렬 방식
            limit: 수집할 게시물 수
            include_comments: 댓글 수집 여부
            comment_limit: 게시물당 수집할 댓글 수
            time_filter: top 정렬 시 기간 필터

        Returns:
            list[CollectionResult]: 수집 결과 목록
        """
        configs = [
            CollectorConfig(
                subreddit=subreddit,
                sort=sort,
                limit=limit,
                include_comments=include_comments,
                comment_limit=comment_limit,
                time_filter=time_filter,
            )
            for subreddit in subreddits
        ]

        return await self.collect_multiple(configs)
