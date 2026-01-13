"""서브레딧 탐색 및 메타데이터 수집.

관심 있는 서브레딧을 발견하고 메타데이터를 수집하는 기능을 제공한다.
키워드 검색, 인기 서브레딧 조회, 활성도 메트릭 분석 등을 지원한다.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from reddit_insight.reddit.models import SubredditInfo

if TYPE_CHECKING:
    from reddit_insight.reddit.client import RedditClient

logger = logging.getLogger(__name__)


class SubredditExplorer:
    """서브레딧 탐색기.

    RedditClient를 사용하여 서브레딧을 검색하고
    메타데이터를 수집하는 기능을 제공한다.

    Attributes:
        client: RedditClient 인스턴스

    Example:
        >>> client = RedditClient()
        >>> explorer = SubredditExplorer(client)
        >>> results = explorer.search("python programming")
        >>> for sub in results:
        ...     print(f"{sub.display_name}: {sub.subscribers:,} subscribers")
    """

    def __init__(self, client: RedditClient) -> None:
        """SubredditExplorer 초기화.

        Args:
            client: RedditClient 인스턴스
        """
        self._client = client

    def _convert_subreddit(self, subreddit) -> SubredditInfo:
        """PRAW Subreddit 객체를 SubredditInfo로 변환.

        Args:
            subreddit: PRAW Subreddit 객체

        Returns:
            SubredditInfo: 변환된 SubredditInfo 모델
        """
        return SubredditInfo.from_praw(subreddit)

    def search(self, query: str, limit: int = 25) -> list[SubredditInfo]:
        """키워드로 서브레딧 검색.

        Reddit의 서브레딧 검색 기능을 사용하여
        키워드와 관련된 서브레딧을 검색한다.

        Args:
            query: 검색 키워드
            limit: 최대 결과 수 (기본: 25)

        Returns:
            list[SubredditInfo]: 검색된 서브레딧 목록

        Example:
            >>> results = explorer.search("machine learning", limit=10)
            >>> print(len(results))
            10
        """
        reddit = self._client._ensure_connected()
        subreddits = reddit.subreddits.search(query, limit=limit)
        results = []
        for sub in subreddits:
            try:
                results.append(self._convert_subreddit(sub))
            except Exception as e:
                logger.warning("서브레딧 변환 실패 (%s): %s", getattr(sub, "display_name", "unknown"), e)
        return results

    def search_by_name(
        self, query: str, include_nsfw: bool = False
    ) -> list[SubredditInfo]:
        """이름으로 서브레딧 검색 (자동완성 스타일).

        서브레딧 이름 접두사로 검색하여 자동완성에 적합한 결과를 반환한다.
        Reddit의 search_by_name API를 사용한다.

        Args:
            query: 서브레딧 이름 접두사
            include_nsfw: NSFW 서브레딧 포함 여부 (기본: False)

        Returns:
            list[SubredditInfo]: 검색된 서브레딧 목록

        Example:
            >>> results = explorer.search_by_name("pyth")
            >>> for sub in results:
            ...     print(sub.display_name)
            Python
            pythoncoding
            pythonlearning
        """
        reddit = self._client._ensure_connected()
        subreddits = reddit.subreddits.search_by_name(
            query, include_nsfw=include_nsfw
        )
        results = []
        for sub in subreddits:
            try:
                results.append(self._convert_subreddit(sub))
            except Exception as e:
                logger.warning("서브레딧 변환 실패 (%s): %s", getattr(sub, "display_name", "unknown"), e)
        return results

    def get_info(self, name: str) -> SubredditInfo | None:
        """단일 서브레딧 상세 정보 조회.

        서브레딧 이름으로 상세 정보를 조회한다.
        존재하지 않는 서브레딧인 경우 None을 반환한다.

        Args:
            name: 서브레딧 이름 (예: "python", "datascience")

        Returns:
            SubredditInfo | None: 서브레딧 정보 또는 None

        Example:
            >>> info = explorer.get_info("python")
            >>> if info:
            ...     print(f"{info.display_name}: {info.subscribers:,}")
        """
        try:
            subreddit = self._client.get_subreddit(name)
            # 실제 데이터를 로드하기 위해 속성에 접근
            _ = subreddit.subscribers
            return self._convert_subreddit(subreddit)
        except Exception as e:
            logger.warning("서브레딧 정보 조회 실패 (%s): %s", name, e)
            return None

    def get_info_batch(self, names: list[str]) -> list[SubredditInfo]:
        """여러 서브레딧 일괄 조회.

        여러 서브레딧의 정보를 한 번에 조회한다.
        존재하지 않는 서브레딧은 결과에서 제외된다.

        Args:
            names: 서브레딧 이름 목록

        Returns:
            list[SubredditInfo]: 조회된 서브레딧 정보 목록

        Example:
            >>> infos = explorer.get_info_batch(["python", "datascience", "MachineLearning"])
            >>> print(len(infos))
            3
        """
        results = []
        for name in names:
            info = self.get_info(name)
            if info is not None:
                results.append(info)
        return results
