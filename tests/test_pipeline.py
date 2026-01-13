"""Pipeline 모듈 테스트.

TextPreprocessor, Collector, DataPipeline 테스트를 포함한다.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from reddit_insight.pipeline import (
    Collector,
    CollectorConfig,
    CollectorResult,
    ProcessingResult,
    SimpleScheduler,
    ScheduleConfig,
    TextPreprocessor,
)


# ========== TextPreprocessor 테스트 ==========


class TestTextPreprocessor:
    """TextPreprocessor 테스트 클래스."""

    @pytest.fixture
    def preprocessor(self) -> TextPreprocessor:
        """TextPreprocessor 인스턴스 반환."""
        return TextPreprocessor()

    def test_clean_text_removes_urls(self, preprocessor: TextPreprocessor) -> None:
        """URL이 제거되는지 확인."""
        text = "Check this out: https://example.com and http://test.org"
        result = preprocessor.clean_text(text)

        assert "https://example.com" not in result
        assert "http://test.org" not in result
        assert "Check this out:" in result

    def test_clean_text_decodes_html_entities(
        self, preprocessor: TextPreprocessor
    ) -> None:
        """HTML 엔티티가 디코딩되는지 확인."""
        text = "Hello &amp; World &lt;script&gt;"
        result = preprocessor.clean_text(text)

        assert result == "Hello & World <script>"

    def test_clean_text_normalizes_whitespace(
        self, preprocessor: TextPreprocessor
    ) -> None:
        """연속 공백이 정규화되는지 확인."""
        text = "Hello    World\t\tTest"
        result = preprocessor.clean_text(text)

        assert result == "Hello World Test"

    def test_clean_text_normalizes_newlines(
        self, preprocessor: TextPreprocessor
    ) -> None:
        """연속 줄바꿈이 정규화되는지 확인."""
        text = "Para 1\n\n\n\n\nPara 2"
        result = preprocessor.clean_text(text)

        assert result == "Para 1\n\nPara 2"

    def test_is_deleted_content_detects_deleted(
        self, preprocessor: TextPreprocessor
    ) -> None:
        """삭제된 콘텐츠가 감지되는지 확인."""
        assert preprocessor.is_deleted_content("[deleted]") is True
        assert preprocessor.is_deleted_content("[removed]") is True
        assert preprocessor.is_deleted_content("[deleted by user]") is True
        assert preprocessor.is_deleted_content("[DELETED]") is True

    def test_is_deleted_content_not_deleted(
        self, preprocessor: TextPreprocessor
    ) -> None:
        """정상 콘텐츠는 삭제로 감지되지 않는지 확인."""
        assert preprocessor.is_deleted_content("Normal text") is False
        assert preprocessor.is_deleted_content("") is False

    def test_normalize_author_deleted_user(
        self, preprocessor: TextPreprocessor
    ) -> None:
        """삭제된 사용자가 None으로 반환되는지 확인."""
        assert preprocessor.normalize_author("[deleted]") is None
        assert preprocessor.normalize_author("deleted") is None
        assert preprocessor.normalize_author("[removed]") is None

    def test_normalize_author_normal_user(
        self, preprocessor: TextPreprocessor
    ) -> None:
        """정상 사용자는 그대로 반환되는지 확인."""
        assert preprocessor.normalize_author("username") == "username"
        assert preprocessor.normalize_author("  username  ") == "username"

    def test_extract_urls(self, preprocessor: TextPreprocessor) -> None:
        """URL이 추출되는지 확인."""
        text = "Check https://example.com and http://test.org/path?q=1"
        urls = preprocessor.extract_urls(text)

        assert len(urls) == 2
        assert "https://example.com" in urls
        assert "http://test.org/path?q=1" in urls

    def test_extract_mentions(self, preprocessor: TextPreprocessor) -> None:
        """멘션이 추출되는지 확인."""
        text = "Hello /u/username and r/python /r/programming"
        mentions = preprocessor.extract_mentions(text)

        assert "username" in mentions["users"]
        assert "python" in mentions["subreddits"]
        assert "programming" in mentions["subreddits"]

    def test_remove_mentions(self, preprocessor: TextPreprocessor) -> None:
        """멘션이 제거되는지 확인."""
        text = "Hello /u/username check r/python"
        result = preprocessor.remove_mentions(text)

        assert "/u/username" not in result
        assert "r/python" not in result
        assert "Hello" in result
        assert "check" in result

    def test_extract_hashtags(self, preprocessor: TextPreprocessor) -> None:
        """해시태그가 추출되는지 확인."""
        text = "Check out #Python and #MachineLearning"
        hashtags = preprocessor.extract_hashtags(text)

        assert "python" in hashtags
        assert "machinelearning" in hashtags

    def test_get_text_stats(self, preprocessor: TextPreprocessor) -> None:
        """텍스트 통계가 계산되는지 확인."""
        text = "Hello world. This is a test! How are you?"
        stats = preprocessor.get_text_stats(text)

        assert stats["word_count"] == 9
        assert stats["sentence_count"] == 3
        assert stats["char_count"] > 0

    def test_get_text_stats_empty(self, preprocessor: TextPreprocessor) -> None:
        """빈 텍스트 통계가 0으로 반환되는지 확인."""
        stats = preprocessor.get_text_stats("")

        assert stats["word_count"] == 0
        assert stats["sentence_count"] == 0
        assert stats["char_count"] == 0


# ========== CollectorConfig 테스트 ==========


class TestCollectorConfig:
    """CollectorConfig 테스트 클래스."""

    def test_default_values(self) -> None:
        """기본값이 올바르게 설정되는지 확인."""
        config = CollectorConfig(subreddit="python")

        assert config.subreddit == "python"
        assert config.sort == "hot"
        assert config.limit == 100
        assert config.include_comments is False
        assert config.comment_limit == 50
        assert config.time_filter == "week"

    def test_custom_values(self) -> None:
        """커스텀 값이 올바르게 설정되는지 확인."""
        config = CollectorConfig(
            subreddit="programming",
            sort="top",
            limit=50,
            include_comments=True,
            comment_limit=100,
            time_filter="month",
        )

        assert config.subreddit == "programming"
        assert config.sort == "top"
        assert config.limit == 50
        assert config.include_comments is True
        assert config.comment_limit == 100
        assert config.time_filter == "month"


# ========== CollectorResult 테스트 ==========


class TestCollectorResult:
    """CollectorResult 테스트 클래스."""

    def test_success_property(self) -> None:
        """success 속성이 올바르게 작동하는지 확인."""
        result = CollectorResult(subreddit="python")
        assert result.success is True

        result.error = "Some error"
        assert result.success is False

    def test_to_dict(self) -> None:
        """to_dict가 올바른 형식을 반환하는지 확인."""
        result = CollectorResult(
            subreddit="python",
            posts_result=ProcessingResult(total=10, new=5, duplicates=3),
            duration_seconds=1.5,
        )

        d = result.to_dict()
        assert d["subreddit"] == "python"
        assert d["posts"]["total"] == 10
        assert d["posts"]["new"] == 5
        assert d["duration_seconds"] == 1.5
        assert d["success"] is True


# ========== ScheduleConfig 테스트 ==========


class TestScheduleConfig:
    """ScheduleConfig 테스트 클래스."""

    def test_default_values(self) -> None:
        """기본값이 올바르게 설정되는지 확인."""
        config = ScheduleConfig(subreddits=["python", "programming"])

        assert config.subreddits == ["python", "programming"]
        assert config.interval_minutes == 60
        assert config.sort == "hot"
        assert config.limit == 100

    def test_to_collector_configs(self) -> None:
        """to_collector_configs가 올바른 목록을 반환하는지 확인."""
        config = ScheduleConfig(
            subreddits=["python", "programming"],
            sort="new",
            limit=50,
        )

        collector_configs = config.to_collector_configs()

        assert len(collector_configs) == 2
        assert collector_configs[0].subreddit == "python"
        assert collector_configs[0].sort == "new"
        assert collector_configs[0].limit == 50
        assert collector_configs[1].subreddit == "programming"


# ========== Collector 테스트 (모킹) ==========


class TestCollector:
    """Collector 테스트 클래스."""

    @pytest.mark.asyncio
    async def test_connect_disconnect(self) -> None:
        """connect/disconnect가 올바르게 작동하는지 확인."""
        collector = Collector()

        # 연결 전에는 pipeline이 None
        assert collector._pipeline is None

        with patch.object(
            collector, "_db", new_callable=MagicMock
        ) as mock_db:
            # connect mock
            mock_db._engine = None
            mock_db.connect = AsyncMock()

            await collector.connect()

            # 연결 후에는 pipeline이 생성됨
            assert collector._pipeline is not None

            # disconnect mock
            collector._data_source = MagicMock()
            collector._data_source.close = AsyncMock()
            mock_db.disconnect = AsyncMock()

            await collector.disconnect()

    def test_ensure_connected_raises_when_not_connected(self) -> None:
        """연결되지 않은 상태에서 _ensure_connected가 예외를 발생시키는지 확인."""
        collector = Collector()

        with pytest.raises(RuntimeError, match="연결되지 않았습니다"):
            collector._ensure_connected()


# ========== SimpleScheduler 테스트 ==========


class TestSimpleScheduler:
    """SimpleScheduler 테스트 클래스."""

    def test_initial_state(self) -> None:
        """초기 상태가 올바른지 확인."""
        mock_collector = MagicMock(spec=Collector)
        config = ScheduleConfig(subreddits=["python"])

        scheduler = SimpleScheduler(mock_collector, config)

        assert scheduler.is_running is False
        assert len(scheduler.run_history) == 0

        status = scheduler.get_status()
        assert status.total_runs == 0

    @pytest.mark.asyncio
    async def test_run_once(self) -> None:
        """run_once가 올바르게 작동하는지 확인."""
        mock_collector = MagicMock(spec=Collector)
        mock_collector.collect_multiple = AsyncMock(return_value=[
            CollectorResult(
                subreddit="python",
                posts_result=ProcessingResult(total=10, new=5),
            )
        ])

        config = ScheduleConfig(subreddits=["python"])
        scheduler = SimpleScheduler(mock_collector, config)

        results = await scheduler.run_once()

        assert len(results) == 1
        assert results[0].subreddit == "python"
        assert len(scheduler.run_history) == 1

        status = scheduler.get_status()
        assert status.total_runs == 1
        assert status.successful_runs == 1

    def test_stop_when_not_running(self) -> None:
        """실행 중이 아닐 때 stop이 경고만 발생시키는지 확인."""
        mock_collector = MagicMock(spec=Collector)
        config = ScheduleConfig(subreddits=["python"])

        scheduler = SimpleScheduler(mock_collector, config)

        # 예외 없이 실행되어야 함
        scheduler.stop()

        assert scheduler.is_running is False

    def test_clear_history(self) -> None:
        """clear_history가 이력을 초기화하는지 확인."""
        mock_collector = MagicMock(spec=Collector)
        config = ScheduleConfig(subreddits=["python"])

        scheduler = SimpleScheduler(mock_collector, config)
        scheduler._status.total_runs = 5
        scheduler._status.successful_runs = 4

        scheduler.clear_history()

        assert len(scheduler.run_history) == 0
        assert scheduler.get_status().total_runs == 0


# ========== 통합 import 테스트 ==========


class TestPipelineExports:
    """Pipeline 모듈 export 테스트."""

    def test_all_exports_available(self) -> None:
        """모든 export가 사용 가능한지 확인."""
        from reddit_insight.pipeline import (
            Collector,
            CollectorConfig,
            CollectorResult,
            CollectionResult,
            DataPipeline,
            ProcessingResult,
            ScheduleConfig,
            ScheduleRun,
            SchedulerState,
            SchedulerStatus,
            SimpleScheduler,
            TextPreprocessor,
        )

        # 모든 클래스가 import 가능해야 함
        assert TextPreprocessor is not None
        assert DataPipeline is not None
        assert Collector is not None
        assert SimpleScheduler is not None
