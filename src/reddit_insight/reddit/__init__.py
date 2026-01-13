"""Reddit API 클라이언트 및 데이터 모델.

PRAW 기반 Reddit API 클라이언트와 Pydantic 데이터 모델을 제공한다.
OAuth2 인증을 지원하며, 자격증명이 없는 경우 read-only 모드로 동작한다.
"""

from reddit_insight.reddit.auth import AuthenticationError, RedditAuth, get_user_agent
from reddit_insight.reddit.client import RedditClient, get_reddit_client
from reddit_insight.reddit.collectors import CommentCollector, PostCollector
from reddit_insight.reddit.models import Comment, Post, SubredditInfo

__all__ = [
    # Client
    "RedditClient",
    "get_reddit_client",
    # Collectors
    "PostCollector",
    "CommentCollector",
    # Models
    "Post",
    "Comment",
    "SubredditInfo",
    # Auth
    "RedditAuth",
    "AuthenticationError",
    "get_user_agent",
]
