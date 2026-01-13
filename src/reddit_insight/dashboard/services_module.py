"""대시보드 데이터 서비스.

분석 모듈과 대시보드 UI를 연결하여 요약 데이터와 분석 기록을 제공한다.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class DashboardSummary:
    """대시보드 요약 데이터.

    Attributes:
        total_posts_analyzed: 분석된 총 게시물 수
        trending_keywords_count: 트렌딩 키워드 수
        demands_found: 발견된 수요 패턴 수
        insights_generated: 생성된 인사이트 수
    """

    total_posts_analyzed: int = 0
    trending_keywords_count: int = 0
    demands_found: int = 0
    insights_generated: int = 0


@dataclass
class AnalysisRecord:
    """분석 기록.

    Attributes:
        id: 분석 ID
        subreddit: 분석 대상 서브레딧
        analyzed_at: 분석 일시
        post_count: 분석된 게시물 수
        insight_count: 생성된 인사이트 수
    """

    id: str
    subreddit: str
    analyzed_at: datetime
    post_count: int = 0
    insight_count: int = 0


class DashboardService:
    """대시보드 데이터 서비스.

    분석 모듈에서 데이터를 가져와 대시보드에 필요한 형태로 변환한다.
    """

    def __init__(self) -> None:
        """DashboardService를 초기화한다."""
        # 추후 분석 모듈 의존성 주입
        self._analyses: list[AnalysisRecord] = []

    def get_summary(self) -> DashboardSummary:
        """대시보드 요약 데이터를 반환한다.

        Returns:
            DashboardSummary: 요약 데이터
        """
        # 분석 기록에서 집계
        total_posts = sum(a.post_count for a in self._analyses)
        total_insights = sum(a.insight_count for a in self._analyses)

        return DashboardSummary(
            total_posts_analyzed=total_posts,
            trending_keywords_count=0,  # 추후 트렌드 분석 모듈 연동
            demands_found=0,  # 추후 수요 분석 모듈 연동
            insights_generated=total_insights,
        )

    def get_recent_analyses(self, limit: int = 10) -> list[AnalysisRecord]:
        """최근 분석 기록을 반환한다.

        Args:
            limit: 반환할 최대 기록 수

        Returns:
            list[AnalysisRecord]: 최근 분석 기록 목록 (최신순)
        """
        sorted_analyses = sorted(
            self._analyses,
            key=lambda a: a.analyzed_at,
            reverse=True,
        )
        return sorted_analyses[:limit]

    def add_analysis_record(self, record: AnalysisRecord) -> None:
        """분석 기록을 추가한다.

        Args:
            record: 추가할 분석 기록
        """
        self._analyses.append(record)

    def get_analysis_by_id(self, analysis_id: str) -> Optional[AnalysisRecord]:
        """ID로 분석 기록을 조회한다.

        Args:
            analysis_id: 조회할 분석 ID

        Returns:
            Optional[AnalysisRecord]: 분석 기록 (없으면 None)
        """
        for analysis in self._analyses:
            if analysis.id == analysis_id:
                return analysis
        return None


# 싱글톤 인스턴스 (추후 의존성 주입으로 변경 가능)
_dashboard_service: Optional[DashboardService] = None


def get_dashboard_service() -> DashboardService:
    """DashboardService 싱글톤 인스턴스를 반환한다.

    Returns:
        DashboardService: 대시보드 서비스 인스턴스
    """
    global _dashboard_service
    if _dashboard_service is None:
        _dashboard_service = DashboardService()
    return _dashboard_service
