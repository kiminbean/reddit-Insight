"""UnifiedDataSource 테스트.

API와 스크래핑 간 자동 전환 로직을 테스트합니다.
Mock을 사용하여 실제 네트워크 호출 없이 테스트합니다.
"""

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from reddit_insight.data_source import (
    APIUnavailableError,
    DataSourceError,
    DataSourceStrategy,
    ScrapingUnavailableError,
    SourceStatus,
    UnifiedDataSource,
)
from reddit_insight.reddit.models import Comment, Post, SubredditInfo


# ========== Helper ==========


def run_async(coro):
    """비동기 코루틴을 동기적으로 실행하는 헬퍼."""
    return asyncio.get_event_loop().run_until_complete(coro)


# ========== Fixtures ==========


@pytest.fixture
def sample_post() -> Post:
    """샘플 Post 모델 생성."""
    return Post(
        id="test123",
        title="Sample Post",
        selftext="This is a sample post.",
        author="test_user",
        subreddit="python",
        score=100,
        num_comments=25,
        created_utc=datetime(2024, 1, 1, tzinfo=UTC),
        url="https://reddit.com/r/python/comments/test123/",
        permalink="https://reddit.com/r/python/comments/test123/sample_post/",
        is_self=True,
    )


@pytest.fixture
def sample_comment() -> Comment:
    """샘플 Comment 모델 생성."""
    return Comment(
        id="comment123",
        body="This is a sample comment.",
        author="commenter",
        subreddit="python",
        score=10,
        created_utc=datetime(2024, 1, 2, tzinfo=UTC),
        parent_id="t3_test123",
        post_id="test123",
    )


@pytest.fixture
def sample_subreddit_info() -> SubredditInfo:
    """샘플 SubredditInfo 모델 생성."""
    return SubredditInfo(
        name="python",
        display_name="Python",
        title="Python Programming",
        description="News about the programming language Python",
        subscribers=1000000,
        created_utc=datetime(2008, 1, 1, tzinfo=UTC),
        over18=False,
    )


# ========== TestDataSourceStrategy ==========


class TestDataSourceStrategy:
    """DataSourceStrategy 열거형 테스트."""

    def test_strategy_values(self):
        """전략 값이 올바른지 확인."""
        assert DataSourceStrategy.API_ONLY.value == "api_only"
        assert DataSourceStrategy.SCRAPING_ONLY.value == "scraping_only"
        assert DataSourceStrategy.API_FIRST.value == "api_first"
        assert DataSourceStrategy.SCRAPING_FIRST.value == "scraping_first"

    def test_all_strategies_exist(self):
        """모든 전략이 정의되어 있는지 확인."""
        strategies = list(DataSourceStrategy)
        assert len(strategies) == 4


class TestSourceStatus:
    """SourceStatus 데이터 클래스 테스트."""

    def test_default_values(self):
        """기본값이 올바른지 확인."""
        status = SourceStatus()
        assert status.api_available is True
        assert status.scraping_available is True
        assert status.last_api_error is None
        assert status.last_scraping_error is None
        assert status.api_failure_count == 0
        assert status.scraping_failure_count == 0

    def test_api_temporarily_disabled(self):
        """API 일시적 비활성화 감지."""
        status = SourceStatus()
        assert not status.is_api_temporarily_disabled()

        # 임계값 미만
        status.api_failure_count = 4
        assert not status.is_api_temporarily_disabled()

        # 임계값 이상
        status.api_failure_count = 5
        assert status.is_api_temporarily_disabled()

    def test_scraping_temporarily_disabled(self):
        """스크래핑 일시적 비활성화 감지."""
        status = SourceStatus()
        assert not status.is_scraping_temporarily_disabled()

        status.scraping_failure_count = 5
        assert status.is_scraping_temporarily_disabled()

    def test_reset_failures(self):
        """실패 카운트 리셋."""
        status = SourceStatus()
        status.api_failure_count = 5
        status.last_api_error = "Test error"

        status.reset_api_failures()
        assert status.api_failure_count == 0
        assert status.last_api_error is None


# ========== TestUnifiedDataSource ==========


class TestUnifiedDataSource:
    """UnifiedDataSource 클래스 테스트."""

    def test_initialization(self):
        """초기화 테스트."""
        ds = UnifiedDataSource()
        assert ds.strategy == DataSourceStrategy.API_FIRST
        assert ds._api_client is None
        assert ds._scraper is None

    def test_custom_strategy(self):
        """커스텀 전략으로 초기화."""
        ds = UnifiedDataSource(strategy=DataSourceStrategy.SCRAPING_ONLY)
        assert ds.strategy == DataSourceStrategy.SCRAPING_ONLY

    def test_strategy_setter(self):
        """전략 변경 테스트."""
        ds = UnifiedDataSource()
        ds.strategy = DataSourceStrategy.SCRAPING_FIRST
        assert ds.strategy == DataSourceStrategy.SCRAPING_FIRST

    def test_get_status(self):
        """상태 조회 테스트."""
        ds = UnifiedDataSource()
        status = ds.get_status()
        assert isinstance(status, SourceStatus)
        assert status.api_available is True

    def test_repr(self):
        """문자열 표현 테스트."""
        ds = UnifiedDataSource()
        repr_str = repr(ds)
        assert "UnifiedDataSource" in repr_str
        assert "api_first" in repr_str

    def test_should_use_api_for_api_first(self):
        """API_FIRST 전략에서 API 사용 결정."""
        ds = UnifiedDataSource(strategy=DataSourceStrategy.API_FIRST)
        assert ds._should_use_api() is True
        assert ds._should_use_scraping() is False

    def test_should_use_scraping_for_scraping_first(self):
        """SCRAPING_FIRST 전략에서 스크래핑 사용 결정."""
        ds = UnifiedDataSource(strategy=DataSourceStrategy.SCRAPING_FIRST)
        assert ds._should_use_api() is False
        assert ds._should_use_scraping() is True

    def test_should_use_api_only(self):
        """API_ONLY 전략에서 API만 사용."""
        ds = UnifiedDataSource(strategy=DataSourceStrategy.API_ONLY)
        assert ds._should_use_api() is True
        assert ds._should_use_scraping() is False

    def test_should_use_scraping_only(self):
        """SCRAPING_ONLY 전략에서 스크래핑만 사용."""
        ds = UnifiedDataSource(strategy=DataSourceStrategy.SCRAPING_ONLY)
        assert ds._should_use_api() is False
        assert ds._should_use_scraping() is True

    def test_fallback_decision_api_first(self):
        """API_FIRST에서 폴백 결정."""
        ds = UnifiedDataSource(strategy=DataSourceStrategy.API_FIRST)
        error = Exception("Rate limit exceeded")
        assert ds._should_fallback_to_scraping(error) is True

    def test_no_fallback_for_api_only(self):
        """API_ONLY에서 폴백하지 않음."""
        ds = UnifiedDataSource(strategy=DataSourceStrategy.API_ONLY)
        error = Exception("Rate limit exceeded")
        assert ds._should_fallback_to_scraping(error) is False

    def test_no_fallback_for_scraping_only(self):
        """SCRAPING_ONLY에서 API로 폴백하지 않음."""
        ds = UnifiedDataSource(strategy=DataSourceStrategy.SCRAPING_ONLY)
        error = Exception("Request failed")
        assert ds._should_fallback_to_api(error) is False

    def test_record_api_failure(self):
        """API 실패 기록."""
        ds = UnifiedDataSource()
        error = Exception("Connection timeout")

        ds._record_api_failure(error)
        assert ds.get_status().api_failure_count == 1
        assert "Connection timeout" in ds.get_status().last_api_error

    def test_record_scraping_failure(self):
        """스크래핑 실패 기록."""
        ds = UnifiedDataSource()
        error = Exception("Parse error")

        ds._record_scraping_failure(error)
        assert ds.get_status().scraping_failure_count == 1
        assert "Parse error" in ds.get_status().last_scraping_error

    def test_record_api_success_resets_failures(self):
        """API 성공 시 실패 카운트 리셋."""
        ds = UnifiedDataSource()
        ds.get_status().api_failure_count = 3
        ds.get_status().last_api_error = "Previous error"

        ds._record_api_success()
        assert ds.get_status().api_failure_count == 0
        assert ds.get_status().last_api_error is None

    def test_record_scraping_success_resets_failures(self):
        """스크래핑 성공 시 실패 카운트 리셋."""
        ds = UnifiedDataSource()
        ds.get_status().scraping_failure_count = 3
        ds.get_status().last_scraping_error = "Previous error"

        ds._record_scraping_success()
        assert ds.get_status().scraping_failure_count == 0
        assert ds.get_status().last_scraping_error is None

    def test_api_disabled_uses_scraping(self):
        """API 비활성화 시 스크래핑 사용."""
        ds = UnifiedDataSource(strategy=DataSourceStrategy.API_FIRST)
        ds.get_status().api_failure_count = 5  # 임계값 이상

        assert ds._should_use_api() is False
        assert ds._should_use_scraping() is True


# ========== Integration Tests with Mocks ==========


class TestUnifiedDataSourceWithMocks:
    """Mock을 사용한 UnifiedDataSource 통합 테스트."""

    def test_api_first_success(self, sample_post):
        """API_FIRST: API 성공 시 API 결과 반환."""
        ds = UnifiedDataSource(strategy=DataSourceStrategy.API_FIRST)

        # API 클라이언트 Mock
        mock_client = MagicMock()
        mock_client.posts.get_hot.return_value = [sample_post]

        async def _test():
            with patch.object(ds, "_get_api_client", return_value=mock_client):
                result = await ds.get_hot_posts("python", limit=10)
            return result

        result = run_async(_test())
        assert len(result) == 1
        assert result[0].id == "test123"
        mock_client.posts.get_hot.assert_called_once_with("python", limit=10)

    def test_api_first_fallback_to_scraping(self, sample_post):
        """API_FIRST: API 실패 시 스크래핑으로 폴백."""
        ds = UnifiedDataSource(strategy=DataSourceStrategy.API_FIRST)

        # API 실패 Mock
        mock_client = MagicMock()
        mock_client.posts.get_hot.side_effect = Exception("Rate limit exceeded")

        # 스크래퍼 성공 Mock
        mock_scraper = MagicMock()
        mock_scraper.get_hot = AsyncMock(return_value=[sample_post])

        async def _test():
            with (
                patch.object(ds, "_get_api_client", return_value=mock_client),
                patch.object(ds, "_get_scraper", return_value=mock_scraper),
            ):
                result = await ds.get_hot_posts("python", limit=10)
            return result

        result = run_async(_test())
        assert len(result) == 1
        assert result[0].id == "test123"
        # 스크래핑이 호출되었는지 확인
        mock_scraper.get_hot.assert_called_once_with("python", limit=10)

    def test_scraping_only_uses_scraping(self, sample_post):
        """SCRAPING_ONLY: 스크래핑만 사용."""
        ds = UnifiedDataSource(strategy=DataSourceStrategy.SCRAPING_ONLY)

        mock_scraper = MagicMock()
        mock_scraper.get_hot = AsyncMock(return_value=[sample_post])

        async def _test():
            with patch.object(ds, "_get_scraper", return_value=mock_scraper):
                result = await ds.get_hot_posts("python", limit=10)
            return result

        result = run_async(_test())
        assert len(result) == 1
        mock_scraper.get_hot.assert_called_once()

    def test_api_only_no_fallback(self):
        """API_ONLY: API 실패 시 폴백 없이 에러."""
        ds = UnifiedDataSource(strategy=DataSourceStrategy.API_ONLY)

        mock_client = MagicMock()
        mock_client.posts.get_hot.side_effect = Exception("API Error")

        async def _test():
            with patch.object(ds, "_get_api_client", return_value=mock_client):
                await ds.get_hot_posts("python", limit=10)

        with pytest.raises(DataSourceError):
            run_async(_test())

    def test_failure_tracking_increments(self, sample_post):
        """실패 시 카운트 증가 확인."""
        ds = UnifiedDataSource(strategy=DataSourceStrategy.API_FIRST)

        mock_client = MagicMock()
        mock_client.posts.get_hot.side_effect = Exception("API Error")

        mock_scraper = MagicMock()
        mock_scraper.get_hot = AsyncMock(return_value=[sample_post])

        async def _test():
            with (
                patch.object(ds, "_get_api_client", return_value=mock_client),
                patch.object(ds, "_get_scraper", return_value=mock_scraper),
            ):
                await ds.get_hot_posts("python", limit=10)

        run_async(_test())

        # API 실패가 기록됨
        assert ds.get_status().api_failure_count == 1
        # 스크래핑 성공으로 스크래핑 카운트는 0
        assert ds.get_status().scraping_failure_count == 0

    def test_get_post_comments_with_mock(self, sample_comment):
        """댓글 수집 테스트."""
        ds = UnifiedDataSource(strategy=DataSourceStrategy.SCRAPING_ONLY)

        mock_scraper = MagicMock()
        mock_scraper.get_post_comments = AsyncMock(return_value=[sample_comment])

        async def _test():
            with patch.object(ds, "_get_scraper", return_value=mock_scraper):
                result = await ds.get_post_comments("test123", limit=100)
            return result

        result = run_async(_test())
        assert len(result) == 1
        assert result[0].id == "comment123"

    def test_get_subreddit_info_with_mock(self, sample_subreddit_info):
        """서브레딧 정보 조회 테스트."""
        ds = UnifiedDataSource(strategy=DataSourceStrategy.SCRAPING_ONLY)

        mock_scraper = MagicMock()
        mock_scraper.get_subreddit_info = AsyncMock(return_value=sample_subreddit_info)

        async def _test():
            with patch.object(ds, "_get_scraper", return_value=mock_scraper):
                result = await ds.get_subreddit_info("python")
            return result

        result = run_async(_test())
        assert result is not None
        assert result.name == "python"

    def test_search_subreddits_with_mock(self, sample_subreddit_info):
        """서브레딧 검색 테스트."""
        ds = UnifiedDataSource(strategy=DataSourceStrategy.SCRAPING_ONLY)

        mock_scraper = MagicMock()
        mock_scraper.search_subreddits = AsyncMock(return_value=[sample_subreddit_info])

        async def _test():
            with patch.object(ds, "_get_scraper", return_value=mock_scraper):
                result = await ds.search_subreddits("python", limit=25)
            return result

        result = run_async(_test())
        assert len(result) == 1
        assert result[0].name == "python"

    def test_context_manager(self):
        """비동기 컨텍스트 매니저 테스트."""

        async def _test():
            async with UnifiedDataSource() as ds:
                assert ds is not None
                assert isinstance(ds, UnifiedDataSource)

        run_async(_test())
