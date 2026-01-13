"""Pytest fixtures and configuration for Reddit Insight tests.

이 파일은 모든 테스트에서 공유되는 fixtures를 정의합니다.
"""

import pytest


@pytest.fixture
def sample_post_data() -> dict:
    """샘플 Reddit 게시물 데이터를 반환합니다.

    Returns:
        dict: Reddit API 형식의 샘플 게시물 데이터
    """
    return {
        "id": "test123",
        "title": "Sample Reddit Post",
        "selftext": "This is the body of a sample post.",
        "author": "test_user",
        "subreddit": "test",
        "score": 100,
        "num_comments": 25,
        "created_utc": 1704067200.0,  # 2024-01-01 00:00:00 UTC
        "url": "https://reddit.com/r/test/comments/test123/sample_reddit_post/",
        "permalink": "/r/test/comments/test123/sample_reddit_post/",
    }


@pytest.fixture
def sample_comment_data() -> dict:
    """샘플 Reddit 댓글 데이터를 반환합니다.

    Returns:
        dict: Reddit API 형식의 샘플 댓글 데이터
    """
    return {
        "id": "comment123",
        "body": "This is a sample comment.",
        "author": "commenter",
        "score": 10,
        "created_utc": 1704153600.0,  # 2024-01-02 00:00:00 UTC
        "parent_id": "t3_test123",
        "link_id": "t3_test123",
    }
