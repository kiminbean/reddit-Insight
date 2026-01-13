"""Reddit 수집기 테스트.

PostCollector와 CommentCollector의 단위 테스트.
실제 API 호출 없이 모킹으로 테스트한다.
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock, Mock, patch

import pytest

from reddit_insight.reddit.collectors import CommentCollector, PostCollector
from reddit_insight.reddit.models import Comment, Post


# ============================================================================
# Mock Fixtures
# ============================================================================


@pytest.fixture
def mock_submission():
    """PRAW Submission mock 객체 생성."""
    mock = MagicMock()
    mock.id = "abc123"
    mock.title = "Test Post Title"
    mock.selftext = "Test post body content"
    mock.author.name = "test_author"
    mock.subreddit.display_name = "test_subreddit"
    mock.score = 100
    mock.num_comments = 25
    mock.created_utc = 1704067200.0  # 2024-01-01 00:00:00 UTC
    mock.url = "https://example.com/test"
    mock.permalink = "/r/test_subreddit/comments/abc123/test_post/"
    mock.is_self = True
    return mock


@pytest.fixture
def mock_comment():
    """PRAW Comment mock 객체 생성."""
    mock = MagicMock()
    mock.id = "xyz789"
    mock.body = "This is a test comment"
    mock.author.name = "commenter"
    mock.subreddit.display_name = "test_subreddit"
    mock.score = 10
    mock.created_utc = 1704153600.0  # 2024-01-02 00:00:00 UTC
    mock.parent_id = "t3_abc123"
    mock.link_id = "t3_abc123"
    return mock


@pytest.fixture
def mock_reddit_client():
    """RedditClient mock 객체 생성."""
    mock = MagicMock()
    return mock


# ============================================================================
# PostCollector Tests
# ============================================================================


class TestPostCollector:
    """PostCollector 테스트 스위트."""

    def test_get_hot_returns_posts(self, mock_reddit_client, mock_submission):
        """get_hot이 Post 리스트를 반환하는지 테스트."""
        # Arrange
        mock_subreddit = MagicMock()
        mock_subreddit.hot.return_value = [mock_submission, mock_submission]
        mock_reddit_client.get_subreddit.return_value = mock_subreddit

        collector = PostCollector(mock_reddit_client)

        # Act
        posts = collector.get_hot("test_subreddit", limit=2)

        # Assert
        assert len(posts) == 2
        assert all(isinstance(p, Post) for p in posts)
        mock_reddit_client.get_subreddit.assert_called_once_with("test_subreddit")
        mock_subreddit.hot.assert_called_once_with(limit=2)

    def test_get_new_returns_posts(self, mock_reddit_client, mock_submission):
        """get_new가 Post 리스트를 반환하는지 테스트."""
        mock_subreddit = MagicMock()
        mock_subreddit.new.return_value = [mock_submission]
        mock_reddit_client.get_subreddit.return_value = mock_subreddit

        collector = PostCollector(mock_reddit_client)
        posts = collector.get_new("test_subreddit", limit=1)

        assert len(posts) == 1
        assert isinstance(posts[0], Post)
        mock_subreddit.new.assert_called_once_with(limit=1)

    def test_get_top_with_time_filter(self, mock_reddit_client, mock_submission):
        """get_top이 time_filter를 올바르게 전달하는지 테스트."""
        mock_subreddit = MagicMock()
        mock_subreddit.top.return_value = [mock_submission]
        mock_reddit_client.get_subreddit.return_value = mock_subreddit

        collector = PostCollector(mock_reddit_client)
        posts = collector.get_top("test_subreddit", time_filter="month", limit=10)

        assert len(posts) == 1
        mock_subreddit.top.assert_called_once_with(time_filter="month", limit=10)

    def test_get_top_invalid_time_filter(self, mock_reddit_client):
        """잘못된 time_filter에 대해 ValueError 발생 테스트."""
        collector = PostCollector(mock_reddit_client)

        with pytest.raises(ValueError, match="Invalid time_filter"):
            collector.get_top("test_subreddit", time_filter="invalid")

    def test_get_rising_returns_posts(self, mock_reddit_client, mock_submission):
        """get_rising이 Post 리스트를 반환하는지 테스트."""
        mock_subreddit = MagicMock()
        mock_subreddit.rising.return_value = [mock_submission]
        mock_reddit_client.get_subreddit.return_value = mock_subreddit

        collector = PostCollector(mock_reddit_client)
        posts = collector.get_rising("test_subreddit", limit=5)

        assert len(posts) == 1
        mock_subreddit.rising.assert_called_once_with(limit=5)

    def test_search_with_query(self, mock_reddit_client, mock_submission):
        """search가 검색 결과를 올바르게 반환하는지 테스트."""
        mock_subreddit = MagicMock()
        mock_subreddit.search.return_value = [mock_submission]
        mock_reddit_client.get_subreddit.return_value = mock_subreddit

        collector = PostCollector(mock_reddit_client)
        posts = collector.search("test_subreddit", query="python", sort="top", limit=50)

        assert len(posts) == 1
        mock_subreddit.search.assert_called_once_with(
            query="python", sort="top", limit=50
        )

    def test_search_invalid_sort(self, mock_reddit_client):
        """잘못된 sort에 대해 ValueError 발생 테스트."""
        collector = PostCollector(mock_reddit_client)

        with pytest.raises(ValueError, match="Invalid sort"):
            collector.search("test_subreddit", query="test", sort="invalid")

    def test_convert_submission(self, mock_reddit_client, mock_submission):
        """_convert_submission이 Post 모델을 올바르게 생성하는지 테스트."""
        collector = PostCollector(mock_reddit_client)
        post = collector._convert_submission(mock_submission)

        assert isinstance(post, Post)
        assert post.id == "abc123"
        assert post.title == "Test Post Title"
        assert post.selftext == "Test post body content"
        assert post.author == "test_author"
        assert post.subreddit == "test_subreddit"
        assert post.score == 100
        assert post.num_comments == 25
        assert post.is_self is True


# ============================================================================
# CommentCollector Tests
# ============================================================================


class TestCommentCollector:
    """CommentCollector 테스트 스위트."""

    def test_get_post_comments(self, mock_reddit_client, mock_comment):
        """get_post_comments가 댓글 리스트를 반환하는지 테스트."""
        # Arrange
        mock_reddit = MagicMock()
        mock_submission = MagicMock()

        # CommentForest mock 설정
        mock_comments = MagicMock()
        mock_comments.__iter__ = Mock(return_value=iter([mock_comment, mock_comment]))
        mock_submission.comments = mock_comments

        mock_reddit.submission.return_value = mock_submission
        mock_reddit_client._ensure_connected.return_value = mock_reddit

        collector = CommentCollector(mock_reddit_client)

        # Act
        comments = collector.get_post_comments("abc123", limit=10)

        # Assert
        assert len(comments) == 2
        assert all(isinstance(c, Comment) for c in comments)
        mock_reddit.submission.assert_called_once_with(id="abc123")
        mock_comments.replace_more.assert_called_once_with(limit=0)

    def test_get_post_comments_with_replace_more(self, mock_reddit_client, mock_comment):
        """replace_more_limit 옵션이 올바르게 전달되는지 테스트."""
        mock_reddit = MagicMock()
        mock_submission = MagicMock()
        mock_comments = MagicMock()
        mock_comments.__iter__ = Mock(return_value=iter([mock_comment]))
        mock_submission.comments = mock_comments
        mock_reddit.submission.return_value = mock_submission
        mock_reddit_client._ensure_connected.return_value = mock_reddit

        collector = CommentCollector(mock_reddit_client)
        collector.get_post_comments("abc123", replace_more_limit=10)

        mock_comments.replace_more.assert_called_once_with(limit=10)

    def test_get_subreddit_comments(self, mock_reddit_client, mock_comment):
        """get_subreddit_comments가 댓글 리스트를 반환하는지 테스트."""
        mock_subreddit = MagicMock()
        mock_subreddit.comments.return_value = [mock_comment, mock_comment]
        mock_reddit_client.get_subreddit.return_value = mock_subreddit

        collector = CommentCollector(mock_reddit_client)
        comments = collector.get_subreddit_comments("test_subreddit", limit=100)

        assert len(comments) == 2
        assert all(isinstance(c, Comment) for c in comments)
        mock_subreddit.comments.assert_called_once_with(limit=100)

    def test_convert_comment(self, mock_reddit_client, mock_comment):
        """_convert_comment가 Comment 모델을 올바르게 생성하는지 테스트."""
        collector = CommentCollector(mock_reddit_client)
        comment = collector._convert_comment(mock_comment)

        assert isinstance(comment, Comment)
        assert comment.id == "xyz789"
        assert comment.body == "This is a test comment"
        assert comment.author == "commenter"
        assert comment.subreddit == "test_subreddit"
        assert comment.score == 10
        assert comment.post_id == "abc123"

    def test_flatten_comment_tree(self, mock_reddit_client, mock_comment):
        """_flatten_comment_tree가 MoreComments를 제외하고 평탄화하는지 테스트."""
        collector = CommentCollector(mock_reddit_client)

        # body 속성이 있는 comment mock
        comment1 = MagicMock()
        comment1.body = "Comment 1"

        comment2 = MagicMock()
        comment2.body = "Comment 2"

        # MoreComments mock (body 속성 없음)
        more_comments = MagicMock(spec=[])

        mock_forest = MagicMock()
        mock_forest.__iter__ = Mock(
            return_value=iter([comment1, more_comments, comment2])
        )

        result = collector._flatten_comment_tree(mock_forest)

        assert len(result) == 2
        assert result[0] == comment1
        assert result[1] == comment2

    def test_deleted_author_handling(self, mock_reddit_client):
        """삭제된 작성자 처리 테스트."""
        mock_comment = MagicMock()
        mock_comment.id = "deleted123"
        mock_comment.body = "Deleted user comment"
        mock_comment.author = None  # 삭제된 작성자
        mock_comment.subreddit.display_name = "test"
        mock_comment.score = 5
        mock_comment.created_utc = 1704067200.0
        mock_comment.parent_id = "t3_test"
        mock_comment.link_id = "t3_test"

        collector = CommentCollector(mock_reddit_client)
        comment = collector._convert_comment(mock_comment)

        assert comment.author == "[deleted]"


# ============================================================================
# Integration Tests (RedditClient + Collectors)
# ============================================================================


class TestRedditClientCollectorIntegration:
    """RedditClient와 Collector 통합 테스트."""

    def test_posts_property_lazy_init(self, mock_reddit_client):
        """posts 프로퍼티가 lazy initialization되는지 테스트."""
        from reddit_insight.reddit.client import RedditClient

        # Mock settings
        with patch("reddit_insight.reddit.client.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                reddit_client_id=None,
                reddit_client_secret=None,
                reddit_user_agent=None,
            )
            client = RedditClient()

            assert client._post_collector is None
            _ = client.posts
            assert client._post_collector is not None
            assert isinstance(client._post_collector, PostCollector)

    def test_comments_property_lazy_init(self, mock_reddit_client):
        """comments 프로퍼티가 lazy initialization되는지 테스트."""
        from reddit_insight.reddit.client import RedditClient

        with patch("reddit_insight.reddit.client.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                reddit_client_id=None,
                reddit_client_secret=None,
                reddit_user_agent=None,
            )
            client = RedditClient()

            assert client._comment_collector is None
            _ = client.comments
            assert client._comment_collector is not None
            assert isinstance(client._comment_collector, CommentCollector)
