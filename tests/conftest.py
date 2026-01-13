"""Pytest fixtures and configuration for Reddit Insight tests.

이 파일은 모든 테스트에서 공유되는 fixtures를 정의합니다.
테스트 픽스처 파일 로더와 샘플 데이터 생성 함수를 포함합니다.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

# 테스트에서 rate limiting 비활성화 (모든 테스트에 적용)
os.environ["RATE_LIMIT_PER_MINUTE"] = "10000"

if TYPE_CHECKING:
    from reddit_insight.reddit.models import Comment, Post

# 픽스처 디렉토리 경로
FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> dict[str, Any] | list[dict[str, Any]]:
    """JSON 픽스처 파일을 로드한다.

    Args:
        name: 픽스처 파일 이름 (확장자 제외)

    Returns:
        파싱된 JSON 데이터

    Raises:
        FileNotFoundError: 픽스처 파일이 존재하지 않는 경우
    """
    fixture_path = FIXTURES_DIR / f"{name}.json"
    if not fixture_path.exists():
        raise FileNotFoundError(f"Fixture not found: {fixture_path}")
    return json.loads(fixture_path.read_text(encoding="utf-8"))


def create_sample_posts(count: int = 5) -> list["Post"]:
    """샘플 Post 객체 리스트를 생성한다.

    Args:
        count: 생성할 Post 수 (최대 10개)

    Returns:
        Post 객체 리스트
    """
    from reddit_insight.reddit.models import Post

    posts_data = load_fixture("sample_posts")
    if not isinstance(posts_data, list):
        raise TypeError("Expected list of posts in fixture")

    posts = []
    for i, data in enumerate(posts_data[:count]):
        created_utc = datetime.fromisoformat(
            data["created_utc"].replace("Z", "+00:00")
        )
        posts.append(
            Post(
                id=data["id"],
                title=data["title"],
                selftext=data.get("selftext", ""),
                author=data["author"],
                subreddit=data["subreddit"],
                score=data["score"],
                num_comments=data["num_comments"],
                created_utc=created_utc,
                url=data["url"],
                permalink=data["permalink"],
                is_self=True,
            )
        )
    return posts


def create_sample_comments(count: int = 10) -> list["Comment"]:
    """샘플 Comment 객체 리스트를 생성한다.

    Args:
        count: 생성할 Comment 수 (최대 15개)

    Returns:
        Comment 객체 리스트
    """
    from reddit_insight.reddit.models import Comment

    comments_data = load_fixture("sample_comments")
    if not isinstance(comments_data, list):
        raise TypeError("Expected list of comments in fixture")

    comments = []
    for data in comments_data[:count]:
        created_utc = datetime.fromisoformat(
            data["created_utc"].replace("Z", "+00:00")
        )
        comments.append(
            Comment(
                id=data["id"],
                body=data["body"],
                author=data["author"],
                subreddit=data["subreddit"],
                score=data["score"],
                created_utc=created_utc,
                parent_id=data["parent_id"],
                post_id=data["post_id"],
            )
        )
    return comments


# ============================================================================
# Basic Fixtures
# ============================================================================


@pytest.fixture
def sample_post_data() -> dict[str, Any]:
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
def sample_comment_data() -> dict[str, Any]:
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


# ============================================================================
# Model Fixtures
# ============================================================================


@pytest.fixture
def sample_posts() -> list["Post"]:
    """샘플 Post 객체 리스트를 반환한다."""
    return create_sample_posts(10)


@pytest.fixture
def sample_comments() -> list["Comment"]:
    """샘플 Comment 객체 리스트를 반환한다."""
    return create_sample_comments(15)


@pytest.fixture
def sample_texts() -> list[str]:
    """분석용 샘플 텍스트 리스트를 반환한다."""
    posts = create_sample_posts(10)
    texts = []
    for post in posts:
        texts.append(f"{post.title} {post.selftext}")

    comments = create_sample_comments(15)
    for comment in comments:
        texts.append(comment.body)

    return texts


# ============================================================================
# Analysis Result Fixtures
# ============================================================================


@pytest.fixture
def expected_trends() -> dict[str, Any]:
    """예상 트렌드 분석 결과를 반환한다."""
    return load_fixture("expected_trends")


@pytest.fixture
def expected_demands() -> dict[str, Any]:
    """예상 수요 분석 결과를 반환한다."""
    return load_fixture("expected_demands")


# ============================================================================
# Analysis Module Fixtures
# ============================================================================


@pytest.fixture
def keyword_extractor():
    """UnifiedKeywordExtractor 인스턴스를 반환한다."""
    from reddit_insight.analysis import UnifiedKeywordExtractor

    return UnifiedKeywordExtractor()


@pytest.fixture
def trend_analyzer():
    """KeywordTrendAnalyzer 인스턴스를 반환한다."""
    from reddit_insight.analysis import KeywordTrendAnalyzer

    return KeywordTrendAnalyzer()


@pytest.fixture
def demand_detector():
    """DemandDetector 인스턴스를 반환한다."""
    from reddit_insight.analysis import DemandDetector

    return DemandDetector()


@pytest.fixture
def demand_analyzer():
    """DemandAnalyzer 인스턴스를 반환한다."""
    from reddit_insight.analysis import DemandAnalyzer

    return DemandAnalyzer()


@pytest.fixture
def competitive_analyzer():
    """CompetitiveAnalyzer 인스턴스를 반환한다."""
    from reddit_insight.analysis import CompetitiveAnalyzer

    return CompetitiveAnalyzer()


@pytest.fixture
def sentiment_analyzer():
    """RuleBasedSentimentAnalyzer 인스턴스를 반환한다."""
    from reddit_insight.analysis import RuleBasedSentimentAnalyzer

    return RuleBasedSentimentAnalyzer()


@pytest.fixture
def entity_recognizer():
    """EntityRecognizer 인스턴스를 반환한다."""
    from reddit_insight.analysis import EntityRecognizer

    return EntityRecognizer()


# ============================================================================
# Insight Module Fixtures
# ============================================================================


@pytest.fixture
def rules_engine():
    """RulesEngine 인스턴스를 반환한다."""
    from reddit_insight.insights import RulesEngine

    engine = RulesEngine()
    engine.load_default_rules()
    return engine


@pytest.fixture
def opportunity_scorer():
    """OpportunityScorer 인스턴스를 반환한다."""
    from reddit_insight.insights import OpportunityScorer

    return OpportunityScorer()


@pytest.fixture
def feasibility_analyzer():
    """FeasibilityAnalyzer 인스턴스를 반환한다."""
    from reddit_insight.insights import FeasibilityAnalyzer

    return FeasibilityAnalyzer()


# ============================================================================
# Report Module Fixtures
# ============================================================================


@pytest.fixture
def template_registry():
    """TemplateRegistry 인스턴스를 반환한다."""
    from reddit_insight.reports import TemplateRegistry

    registry = TemplateRegistry()
    registry.load_defaults()
    return registry


@pytest.fixture
def report_generator():
    """ReportGenerator 인스턴스를 반환한다."""
    from reddit_insight.reports import ReportGenerator

    return ReportGenerator()


# ============================================================================
# Dashboard Test Fixtures
# ============================================================================


@pytest.fixture
def test_client():
    """FastAPI TestClient를 반환한다."""
    from fastapi.testclient import TestClient

    from reddit_insight.dashboard.app import app

    return TestClient(app)
