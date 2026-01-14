"""멀티 서브레딧 비교 분석기.

여러 서브레딧 간의 비교 분석을 수행한다:
- 공통/고유 키워드 식별
- 감성 비교
- 활동량 비교
- 키워드 오버랩 유사도 행렬
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from reddit_insight.dashboard.data_store import AnalysisData


@dataclass
class SubredditMetrics:
    """서브레딧 메트릭 데이터.

    Attributes:
        subreddit: 서브레딧 이름
        post_count: 게시물 수
        avg_score: 평균 점수
        avg_comments: 평균 댓글 수
        top_keywords: 상위 키워드 목록
        sentiment_distribution: 감성 분포 (positive, negative, neutral 비율)
        keyword_set: 키워드 집합 (내부 사용)
    """

    subreddit: str
    post_count: int = 0
    avg_score: float = 0.0
    avg_comments: float = 0.0
    top_keywords: list[str] = field(default_factory=list)
    sentiment_distribution: dict[str, float] = field(default_factory=dict)
    keyword_set: set[str] = field(default_factory=set, repr=False)

    def to_dict(self) -> dict[str, Any]:
        """딕셔너리로 변환한다."""
        return {
            "subreddit": self.subreddit,
            "post_count": self.post_count,
            "avg_score": round(self.avg_score, 2),
            "avg_comments": round(self.avg_comments, 2),
            "top_keywords": self.top_keywords,
            "sentiment_distribution": {
                k: round(v, 2) for k, v in self.sentiment_distribution.items()
            },
        }


@dataclass
class ComparisonResult:
    """비교 분석 결과.

    Attributes:
        subreddits: 비교 대상 서브레딧 목록
        metrics: 서브레딧별 메트릭
        common_keywords: 모든 서브레딧에 공통으로 나타나는 키워드
        unique_keywords: 서브레딧별 고유 키워드 (다른 곳에 없는)
        keyword_overlap_matrix: 키워드 Jaccard 유사도 행렬
        sentiment_comparison: 감성 비교 데이터
    """

    subreddits: list[str]
    metrics: list[SubredditMetrics]
    common_keywords: list[str] = field(default_factory=list)
    unique_keywords: dict[str, list[str]] = field(default_factory=dict)
    keyword_overlap_matrix: list[list[float]] = field(default_factory=list)
    sentiment_comparison: dict[str, dict[str, float]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """딕셔너리로 변환한다."""
        return {
            "subreddits": self.subreddits,
            "metrics": [m.to_dict() for m in self.metrics],
            "common_keywords": self.common_keywords,
            "unique_keywords": self.unique_keywords,
            "keyword_overlap_matrix": [
                [round(v, 3) for v in row] for row in self.keyword_overlap_matrix
            ],
            "sentiment_comparison": {
                k: {sk: round(sv, 2) for sk, sv in v.items()}
                for k, v in self.sentiment_comparison.items()
            },
        }


class ComparisonAnalyzer:
    """서브레딧 비교 분석기.

    여러 서브레딧의 분석 데이터를 비교하여 공통점과 차이점을 파악한다.

    Attributes:
        data_sources: 분석할 AnalysisData 목록

    Example:
        >>> analyzer = ComparisonAnalyzer([data1, data2, data3])
        >>> result = analyzer.compare()
        >>> print(result.common_keywords)
        ['python', 'machine learning']
    """

    def __init__(self, data_sources: list[AnalysisData]) -> None:
        """ComparisonAnalyzer를 초기화한다.

        Args:
            data_sources: 비교할 AnalysisData 목록 (2-5개)

        Raises:
            ValueError: 데이터 소스가 2개 미만이거나 5개 초과인 경우
        """
        if len(data_sources) < 2:
            raise ValueError("비교 분석에는 최소 2개의 서브레딧이 필요합니다.")
        if len(data_sources) > 5:
            raise ValueError("비교 분석은 최대 5개의 서브레딧까지만 지원합니다.")

        self.data_sources = data_sources
        self._metrics: list[SubredditMetrics] = []

    def compare(self) -> ComparisonResult:
        """여러 서브레딧 비교 분석을 실행한다.

        Returns:
            ComparisonResult: 비교 분석 결과
        """
        # 1. 각 서브레딧의 메트릭 추출
        self._metrics = [self._extract_metrics(data) for data in self.data_sources]

        # 2. 서브레딧 목록
        subreddits = [m.subreddit for m in self._metrics]

        # 3. 키워드 오버랩 계산
        overlap_matrix = self.calculate_keyword_overlap()

        # 4. 공통 및 고유 키워드 찾기
        common_keywords = self.find_common_keywords()
        unique_keywords = self.find_unique_keywords()

        # 5. 감성 비교 데이터
        sentiment_comparison = self._build_sentiment_comparison()

        return ComparisonResult(
            subreddits=subreddits,
            metrics=self._metrics,
            common_keywords=common_keywords,
            unique_keywords=unique_keywords,
            keyword_overlap_matrix=overlap_matrix,
            sentiment_comparison=sentiment_comparison,
        )

    def _extract_metrics(self, data: AnalysisData) -> SubredditMetrics:
        """AnalysisData에서 메트릭을 추출한다.

        Args:
            data: 분석 데이터

        Returns:
            SubredditMetrics
        """
        # 키워드 추출 (상위 20개)
        top_keywords = []
        keyword_set = set()

        if data.keywords:
            for kw in data.keywords[:20]:
                if isinstance(kw, dict):
                    keyword = kw.get("keyword", "")
                else:
                    keyword = str(kw)
                if keyword:
                    top_keywords.append(keyword)
                    keyword_set.add(keyword.lower())

        # 감성 분포 추출
        sentiment_dist = {"positive": 0.33, "neutral": 0.34, "negative": 0.33}

        if data.competition:
            # competition 데이터에서 감성 추출
            sentiment_data = data.competition.get("sentiment_summary", {})
            if sentiment_data:
                total = (
                    sentiment_data.get("positive", 0)
                    + sentiment_data.get("neutral", 0)
                    + sentiment_data.get("negative", 0)
                )
                if total > 0:
                    sentiment_dist = {
                        "positive": sentiment_data.get("positive", 0) / total,
                        "neutral": sentiment_data.get("neutral", 0) / total,
                        "negative": sentiment_data.get("negative", 0) / total,
                    }

        return SubredditMetrics(
            subreddit=data.subreddit,
            post_count=data.post_count,
            avg_score=self._calculate_avg_score(data),
            avg_comments=self._calculate_avg_comments(data),
            top_keywords=top_keywords,
            sentiment_distribution=sentiment_dist,
            keyword_set=keyword_set,
        )

    def _calculate_avg_score(self, data: AnalysisData) -> float:
        """평균 점수를 계산한다.

        Args:
            data: 분석 데이터

        Returns:
            평균 점수
        """
        # trends에서 점수 데이터 추출
        if data.trends:
            for trend in data.trends:
                if isinstance(trend, dict):
                    # trend 데이터에서 평균 계산
                    if "scores" in trend:
                        scores = trend["scores"]
                        if scores:
                            return sum(scores) / len(scores)

        # 간단한 추정치 (게시물 수 기반)
        if data.post_count > 0:
            return 100.0  # 기본값
        return 0.0

    def _calculate_avg_comments(self, data: AnalysisData) -> float:
        """평균 댓글 수를 계산한다.

        Args:
            data: 분석 데이터

        Returns:
            평균 댓글 수
        """
        # trends에서 댓글 데이터 추출
        if data.trends:
            for trend in data.trends:
                if isinstance(trend, dict):
                    if "comments" in trend:
                        comments = trend["comments"]
                        if comments:
                            return sum(comments) / len(comments)

        # 간단한 추정치
        if data.post_count > 0:
            return 10.0  # 기본값
        return 0.0

    def calculate_keyword_overlap(self) -> list[list[float]]:
        """키워드 Jaccard 유사도 행렬을 계산한다.

        각 서브레딧 쌍의 키워드 집합 간 Jaccard 유사도를 계산한다.

        Returns:
            NxN 유사도 행렬 (N = 서브레딧 수)
        """
        n = len(self._metrics)
        matrix = [[0.0] * n for _ in range(n)]

        for i in range(n):
            for j in range(n):
                if i == j:
                    matrix[i][j] = 1.0
                else:
                    matrix[i][j] = self._jaccard_similarity(
                        self._metrics[i].keyword_set,
                        self._metrics[j].keyword_set,
                    )

        return matrix

    def _jaccard_similarity(self, set1: set[str], set2: set[str]) -> float:
        """두 집합의 Jaccard 유사도를 계산한다.

        Args:
            set1: 첫 번째 집합
            set2: 두 번째 집합

        Returns:
            Jaccard 유사도 (0.0 ~ 1.0)
        """
        if not set1 or not set2:
            return 0.0

        intersection = len(set1 & set2)
        union = len(set1 | set2)

        if union == 0:
            return 0.0

        return intersection / union

    def find_common_keywords(self, min_overlap: int = 2) -> list[str]:
        """N개 이상 서브레딧에서 공통으로 나타나는 키워드를 찾는다.

        Args:
            min_overlap: 최소 등장 서브레딧 수 (기본 2)

        Returns:
            공통 키워드 목록
        """
        if not self._metrics:
            return []

        # 모든 키워드의 등장 횟수 계산
        keyword_counts: dict[str, int] = {}

        for metrics in self._metrics:
            for keyword in metrics.keyword_set:
                keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1

        # min_overlap 이상 등장하는 키워드 추출
        common = [kw for kw, count in keyword_counts.items() if count >= min_overlap]

        # 등장 횟수 기준 정렬 (많이 등장할수록 앞에)
        common.sort(key=lambda k: -keyword_counts[k])

        return common

    def find_unique_keywords(self) -> dict[str, list[str]]:
        """각 서브레딧의 고유 키워드를 찾는다.

        다른 어느 서브레딧에도 나타나지 않는 키워드만 추출한다.

        Returns:
            서브레딧별 고유 키워드 딕셔너리
        """
        if not self._metrics:
            return {}

        result: dict[str, list[str]] = {}

        # 모든 키워드 집합 합집합
        all_keywords = set()
        for metrics in self._metrics:
            all_keywords |= metrics.keyword_set

        for metrics in self._metrics:
            # 다른 서브레딧들의 키워드 합집합
            other_keywords = set()
            for other in self._metrics:
                if other.subreddit != metrics.subreddit:
                    other_keywords |= other.keyword_set

            # 현재 서브레딧에만 있는 키워드
            unique = metrics.keyword_set - other_keywords
            result[metrics.subreddit] = sorted(list(unique))

        return result

    def _build_sentiment_comparison(self) -> dict[str, dict[str, float]]:
        """감성 비교 데이터를 구축한다.

        Returns:
            서브레딧별 감성 분포 딕셔너리
        """
        return {
            metrics.subreddit: metrics.sentiment_distribution
            for metrics in self._metrics
        }


def compare_subreddits(data_sources: list[AnalysisData]) -> ComparisonResult:
    """서브레딧 비교 분석을 수행하는 헬퍼 함수.

    Args:
        data_sources: 비교할 AnalysisData 목록

    Returns:
        ComparisonResult
    """
    analyzer = ComparisonAnalyzer(data_sources)
    return analyzer.compare()
