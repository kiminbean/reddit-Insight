"""인사이트 서비스.

인사이트 뷰 데이터를 제공하는 서비스 레이어.
RulesEngine, OpportunityScorer, FeasibilityAnalyzer를 통합하여 대시보드에 필요한 데이터를 제공한다.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any

from reddit_insight.dashboard.data_store import get_current_data

# =============================================================================
# VIEW DATA STRUCTURES
# =============================================================================


@dataclass
class InsightView:
    """인사이트 뷰 데이터.

    인사이트 목록 표시용 경량 데이터 구조.

    Attributes:
        id: 인사이트 ID
        insight_type: 인사이트 유형 문자열
        title: 인사이트 제목
        confidence: 신뢰도 (0-1)
        priority: 우선순위 (0-100)
        evidence_count: 근거 데이터 수
    """

    id: str
    insight_type: str
    title: str
    confidence: float
    priority: float
    evidence_count: int

    @property
    def confidence_percent(self) -> int:
        """신뢰도를 백분율로 반환한다."""
        return int(self.confidence * 100)

    @property
    def type_display(self) -> str:
        """유형을 표시용 문자열로 변환한다."""
        type_map = {
            "market_gap": "Market Gap",
            "improvement_opportunity": "Improvement Opportunity",
            "emerging_trend": "Emerging Trend",
            "competitive_weakness": "Competitive Weakness",
            "unmet_need": "Unmet Need",
        }
        return type_map.get(self.insight_type, self.insight_type.replace("_", " ").title())

    @property
    def type_color(self) -> str:
        """유형별 색상 클래스를 반환한다."""
        color_map = {
            "market_gap": "bg-purple-100 text-purple-800",
            "improvement_opportunity": "bg-blue-100 text-blue-800",
            "emerging_trend": "bg-green-100 text-green-800",
            "competitive_weakness": "bg-orange-100 text-orange-800",
            "unmet_need": "bg-red-100 text-red-800",
        }
        return color_map.get(self.insight_type, "bg-gray-100 text-gray-800")

    @property
    def type_icon(self) -> str:
        """유형별 아이콘 SVG 경로를 반환한다."""
        icon_map = {
            "market_gap": "M13 10V3L4 14h7v7l9-11h-7z",  # lightning bolt
            "improvement_opportunity": "M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z",  # sparkles
            "emerging_trend": "M13 7h8m0 0v8m0-8l-8 8-4-4-6 6",  # trending up
            "competitive_weakness": "M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z",  # target
            "unmet_need": "M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z",  # dollar sign
        }
        return icon_map.get(self.insight_type, "M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z")


@dataclass
class InsightDetail(InsightView):
    """인사이트 상세 데이터.

    인사이트 상세 페이지용 확장 데이터 구조.

    Attributes:
        description: 상세 설명
        evidence: 근거 문자열 목록
        related_entities: 관련 엔티티 목록
        related_demands: 관련 수요 목록
        created_at: 생성 시간
    """

    description: str = ""
    evidence: list[str] = field(default_factory=list)
    related_entities: list[str] = field(default_factory=list)
    related_demands: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def created_at_display(self) -> str:
        """생성 시간을 표시용 문자열로 변환한다."""
        return self.created_at.strftime("%Y-%m-%d %H:%M UTC")


@dataclass
class RecommendationView:
    """추천 뷰 데이터.

    추천 카드 표시용 데이터 구조.

    Attributes:
        rank: 순위
        insight_id: 인사이트 ID
        insight_title: 인사이트 제목
        insight_type: 인사이트 유형
        business_score: 비즈니스 점수 (0-100)
        feasibility_score: 실행 가능성 점수 (0-100)
        final_score: 종합 점수 (0-100)
        grade: 등급 (A/B/C/D/F)
        risk_level: 리스크 수준 (LOW/MEDIUM/HIGH)
        action_items: 실행 항목 목록
    """

    rank: int
    insight_id: str
    insight_title: str
    insight_type: str
    business_score: float
    feasibility_score: float
    final_score: float
    grade: str
    risk_level: str
    action_items: list[str] = field(default_factory=list)

    @property
    def grade_color(self) -> str:
        """등급별 색상 클래스를 반환한다."""
        color_map = {
            "A": "bg-green-100 text-green-800 border-green-200",
            "B": "bg-blue-100 text-blue-800 border-blue-200",
            "C": "bg-yellow-100 text-yellow-800 border-yellow-200",
            "D": "bg-orange-100 text-orange-800 border-orange-200",
            "F": "bg-red-100 text-red-800 border-red-200",
        }
        return color_map.get(self.grade, "bg-gray-100 text-gray-800 border-gray-200")

    @property
    def risk_color(self) -> str:
        """리스크 수준별 색상 클래스를 반환한다."""
        color_map = {
            "LOW": "text-green-600",
            "MEDIUM": "text-yellow-600",
            "HIGH": "text-red-600",
        }
        return color_map.get(self.risk_level, "text-gray-600")

    @property
    def type_display(self) -> str:
        """유형을 표시용 문자열로 변환한다."""
        type_map = {
            "market_gap": "Market Gap",
            "improvement_opportunity": "Improvement",
            "emerging_trend": "Trend",
            "competitive_weakness": "Competition",
            "unmet_need": "Unmet Need",
        }
        return type_map.get(self.insight_type, self.insight_type.replace("_", " ").title())


@dataclass
class OpportunityView:
    """기회 뷰 데이터.

    기회 랭킹 테이블 표시용 데이터 구조.

    Attributes:
        rank: 순위
        insight_id: 인사이트 ID
        insight_title: 인사이트 제목
        market_size_score: 시장 규모 점수 (0-100)
        competition_score: 경쟁 강도 점수 (0-100, 높을수록 기회)
        urgency_score: 긴급성 점수 (0-100)
        total_score: 종합 점수 (0-100)
        grade: 등급 (A/B/C/D/F)
    """

    rank: int
    insight_id: str
    insight_title: str
    market_size_score: float
    competition_score: float
    urgency_score: float
    total_score: float
    grade: str

    @property
    def grade_color(self) -> str:
        """등급별 색상 클래스를 반환한다."""
        color_map = {
            "A": "bg-green-100 text-green-800",
            "B": "bg-blue-100 text-blue-800",
            "C": "bg-yellow-100 text-yellow-800",
            "D": "bg-orange-100 text-orange-800",
            "F": "bg-red-100 text-red-800",
        }
        return color_map.get(self.grade, "bg-gray-100 text-gray-800")

    @property
    def market_size_bar_width(self) -> int:
        """시장 규모 점수를 바 너비 백분율로 반환한다."""
        return max(0, min(100, int(self.market_size_score)))

    @property
    def competition_bar_width(self) -> int:
        """경쟁 점수를 바 너비 백분율로 반환한다."""
        return max(0, min(100, int(self.competition_score)))

    @property
    def urgency_bar_width(self) -> int:
        """긴급성 점수를 바 너비 백분율로 반환한다."""
        return max(0, min(100, int(self.urgency_score)))


# =============================================================================
# INSIGHT SERVICE
# =============================================================================


class InsightService:
    """인사이트 서비스.

    대시보드에서 사용할 인사이트 관련 데이터를 제공한다.
    실제 구현에서는 RulesEngine, OpportunityScorer, FeasibilityAnalyzer를 사용한다.
    현재는 데모용 목 데이터를 반환한다.

    Example:
        >>> service = InsightService()
        >>> insights = service.get_insights(limit=10)
        >>> for insight in insights:
        ...     print(f"{insight.title}: {insight.confidence_percent}%")
    """

    def __init__(self) -> None:
        """서비스 초기화."""
        # mock 데이터 사용 금지 - 실제 데이터만 사용
        pass

    def get_insights(
        self,
        insight_type: str | None = None,
        min_confidence: float = 0.0,
        limit: int = 20,
    ) -> list[InsightView]:
        """인사이트 목록을 조회한다.

        Args:
            insight_type: 필터링할 인사이트 유형 (None이면 전체)
            min_confidence: 최소 신뢰도 (0-1)
            limit: 최대 반환 수

        Returns:
            InsightView 목록
        """
        # 실제 데이터에서 인사이트 가져오기
        data = get_current_data()
        if data and data.insights:
            insights = []
            for i, insight_data in enumerate(data.insights):
                insights.append(
                    InsightView(
                        id=f"insight_{i:03d}",
                        insight_type=insight_data.get("type", "emerging_trend"),
                        title=insight_data.get("title", ""),
                        confidence=insight_data.get("confidence", 0.7),
                        priority=insight_data.get("confidence", 0.7) * 100,
                        evidence_count=1,
                    )
                )

            # 유형 필터
            if insight_type:
                insights = [ins for ins in insights if ins.insight_type == insight_type]

            # 신뢰도 필터
            insights = [ins for ins in insights if ins.confidence >= min_confidence]

            # 우선순위 내림차순 정렬
            insights = sorted(insights, key=lambda x: x.priority, reverse=True)

            if insights:
                return insights[:limit]

        # 실제 데이터가 없으면 빈 결과 반환 (mock 데이터 사용 금지)
        return []

    def get_insight_detail(self, insight_id: str) -> InsightDetail | None:
        """인사이트 상세 정보를 조회한다.

        Args:
            insight_id: 인사이트 ID

        Returns:
            InsightDetail 또는 None (찾지 못한 경우)
        """
        # 실제 데이터에서 인사이트 찾기
        data = get_current_data()
        if data and data.insights:
            for i, insight_data in enumerate(data.insights):
                if f"insight_{i:03d}" == insight_id:
                    confidence = insight_data.get("confidence", 0.7)
                    return InsightDetail(
                        id=insight_id,
                        insight_type=insight_data.get("type", "emerging_trend"),
                        title=insight_data.get("title", ""),
                        confidence=confidence,
                        priority=confidence * 100,
                        evidence_count=len(insight_data.get("evidence", [])),
                        description=insight_data.get("description", ""),
                        evidence=insight_data.get("evidence", []),
                        related_entities=insight_data.get("related_entities", []),
                        related_demands=insight_data.get("related_demands", []),
                        created_at=datetime.now(UTC),
                    )
        return None

    def get_recommendations(self, top_n: int = 10) -> list[RecommendationView]:
        """추천 목록을 조회한다.

        Args:
            top_n: 반환할 최대 추천 수

        Returns:
            RecommendationView 목록 (종합 점수 내림차순)
        """
        # 실제 데이터에서 추천 생성
        data = get_current_data()
        if data and data.demands and data.demands.get("top_opportunities"):
            recommendations = []
            for i, opp in enumerate(data.demands["top_opportunities"][:top_n]):
                score = opp.get("priority_score", 50)
                grade = "A" if score >= 80 else "B" if score >= 60 else "C" if score >= 40 else "D"
                recommendations.append(
                    RecommendationView(
                        rank=i + 1,
                        insight_id=f"opp_{i:03d}",
                        insight_title=opp.get("representative", "")[:50],
                        insight_type="unmet_need",
                        business_score=score,
                        feasibility_score=score * 0.8,
                        final_score=score * 0.9,
                        grade=grade,
                        risk_level="LOW" if score >= 70 else "MEDIUM" if score >= 50 else "HIGH",
                        action_items=data.demands.get("recommendations", [])[:3],
                    )
                )
            if recommendations:
                return recommendations

        # 실제 데이터가 없으면 빈 결과 반환 (mock 데이터 사용 금지)
        return []

    def get_opportunity_ranking(self, limit: int = 20) -> list[OpportunityView]:
        """기회 랭킹을 조회한다.

        Args:
            limit: 최대 반환 수

        Returns:
            OpportunityView 목록 (종합 점수 내림차순)
        """
        # 실제 데이터에서 기회 생성
        data = get_current_data()
        if data and data.demands and data.demands.get("top_opportunities"):
            opportunities = []
            for i, opp in enumerate(data.demands["top_opportunities"][:limit]):
                score = opp.get("priority_score", 50)
                grade = "A" if score >= 80 else "B" if score >= 60 else "C" if score >= 40 else "D"
                opportunities.append(
                    OpportunityView(
                        rank=i + 1,
                        insight_id=f"opp_{i:03d}",
                        insight_title=opp.get("representative", "")[:50],
                        market_size_score=score * 0.9,
                        competition_score=score * 0.7,
                        urgency_score=score * 0.8,
                        total_score=score,
                        grade=grade,
                    )
                )
            if opportunities:
                return opportunities

        # 실제 데이터가 없으면 빈 결과 반환 (mock 데이터 사용 금지)
        return []

    def get_insight_types(self) -> list[dict[str, str]]:
        """사용 가능한 인사이트 유형 목록을 반환한다.

        Returns:
            유형 정보 딕셔너리 목록 (value, label)
        """
        return [
            {"value": "market_gap", "label": "Market Gap"},
            {"value": "improvement_opportunity", "label": "Improvement Opportunity"},
            {"value": "emerging_trend", "label": "Emerging Trend"},
            {"value": "competitive_weakness", "label": "Competitive Weakness"},
            {"value": "unmet_need", "label": "Unmet Need"},
        ]

    def get_insight_score_breakdown(self, insight_id: str) -> dict[str, Any] | None:
        """인사이트 스코어 breakdown 데이터를 반환한다.

        Args:
            insight_id: 인사이트 ID

        Returns:
            스코어 데이터 딕셔너리 또는 None
        """
        # 실제 데이터에서 인사이트 찾기
        data = get_current_data()
        if data and data.insights:
            for i, insight_data in enumerate(data.insights):
                if f"insight_{i:03d}" == insight_id:
                    confidence = insight_data.get("confidence", 0.7)
                    base_score = confidence * 100
                    return {
                        "labels": ["Confidence", "Relevance", "Impact", "Trend", "Feasibility"],
                        "scores": [
                            base_score,
                            base_score * 0.9,
                            base_score * 0.85,
                            base_score * 0.8,
                            base_score * 0.75,
                        ],
                    }
        return None

    def get_grade_distribution(self) -> dict[str, int]:
        """등급 분포를 반환한다.

        Returns:
            등급별 개수 딕셔너리
        """
        distribution = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}

        # 실제 데이터에서 등급 분포 계산
        data = get_current_data()
        if data and data.demands and data.demands.get("top_opportunities"):
            for opp in data.demands["top_opportunities"]:
                score = opp.get("priority_score", 50)
                grade = "A" if score >= 80 else "B" if score >= 60 else "C" if score >= 40 else "D" if score >= 20 else "F"
                if grade in distribution:
                    distribution[grade] += 1
            if sum(distribution.values()) > 0:
                return distribution

        # 실제 데이터가 없으면 빈 분포 반환 (mock 데이터 사용 금지)
        return distribution

    # ==========================================================================
    # MOCK DATA GENERATORS (데모용)
    # ==========================================================================

    def _generate_mock_insights(self) -> list[InsightView]:
        """데모용 인사이트 목 데이터를 생성한다."""
        return [
            InsightView(
                id="insight_001",
                insight_type="market_gap",
                title="Market gap in offline note-taking applications",
                confidence=0.87,
                priority=85.0,
                evidence_count=5,
            ),
            InsightView(
                id="insight_002",
                insight_type="improvement_opportunity",
                title="High demand for better Slack integration",
                confidence=0.82,
                priority=78.0,
                evidence_count=4,
            ),
            InsightView(
                id="insight_003",
                insight_type="emerging_trend",
                title="Rising interest in AI-powered productivity tools",
                confidence=0.91,
                priority=92.0,
                evidence_count=7,
            ),
            InsightView(
                id="insight_004",
                insight_type="competitive_weakness",
                title="Competitor X showing declining user satisfaction",
                confidence=0.75,
                priority=68.0,
                evidence_count=3,
            ),
            InsightView(
                id="insight_005",
                insight_type="unmet_need",
                title="Users willing to pay for real-time collaboration",
                confidence=0.88,
                priority=89.0,
                evidence_count=6,
            ),
            InsightView(
                id="insight_006",
                insight_type="market_gap",
                title="No solution for cross-platform bookmark sync",
                confidence=0.79,
                priority=72.0,
                evidence_count=4,
            ),
            InsightView(
                id="insight_007",
                insight_type="emerging_trend",
                title="Growing demand for privacy-focused alternatives",
                confidence=0.84,
                priority=81.0,
                evidence_count=5,
            ),
            InsightView(
                id="insight_008",
                insight_type="improvement_opportunity",
                title="Calendar apps need better task management",
                confidence=0.76,
                priority=65.0,
                evidence_count=3,
            ),
        ]

    def _generate_mock_recommendations(self) -> list[RecommendationView]:
        """데모용 추천 목 데이터를 생성한다."""
        return [
            RecommendationView(
                rank=1,
                insight_id="insight_003",
                insight_title="AI-powered productivity tools",
                insight_type="emerging_trend",
                business_score=88.5,
                feasibility_score=75.0,
                final_score=83.1,
                grade="A",
                risk_level="LOW",
                action_items=[
                    "Conduct detailed market research",
                    "Build MVP with core AI features",
                    "Target early adopter communities",
                ],
            ),
            RecommendationView(
                rank=2,
                insight_id="insight_005",
                insight_title="Real-time collaboration features",
                insight_type="unmet_need",
                business_score=85.0,
                feasibility_score=70.0,
                final_score=79.0,
                grade="B",
                risk_level="MEDIUM",
                action_items=[
                    "Validate willingness to pay",
                    "Define pricing strategy",
                    "Build collaboration prototype",
                ],
            ),
            RecommendationView(
                rank=3,
                insight_id="insight_001",
                insight_title="Offline note-taking applications",
                insight_type="market_gap",
                business_score=82.0,
                feasibility_score=68.0,
                final_score=76.4,
                grade="B",
                risk_level="LOW",
                action_items=[
                    "Research offline sync technologies",
                    "Design MVP feature set",
                    "Build prototype for testing",
                ],
            ),
            RecommendationView(
                rank=4,
                insight_id="insight_002",
                insight_title="Slack integration improvements",
                insight_type="improvement_opportunity",
                business_score=78.0,
                feasibility_score=82.0,
                final_score=79.6,
                grade="B",
                risk_level="LOW",
                action_items=[
                    "Analyze competitor integrations",
                    "Design improved workflow",
                    "Create comparison landing page",
                ],
            ),
            RecommendationView(
                rank=5,
                insight_id="insight_007",
                insight_title="Privacy-focused alternatives",
                insight_type="emerging_trend",
                business_score=75.0,
                feasibility_score=65.0,
                final_score=71.0,
                grade="B",
                risk_level="MEDIUM",
                action_items=[
                    "Monitor privacy regulation changes",
                    "Identify privacy-conscious communities",
                    "Build privacy-first MVP",
                ],
            ),
        ]

    def _generate_mock_opportunities(self) -> list[OpportunityView]:
        """데모용 기회 목 데이터를 생성한다."""
        return [
            OpportunityView(
                rank=1,
                insight_id="insight_003",
                insight_title="AI-powered productivity tools",
                market_size_score=85.0,
                competition_score=75.0,
                urgency_score=82.0,
                total_score=80.7,
                grade="A",
            ),
            OpportunityView(
                rank=2,
                insight_id="insight_005",
                insight_title="Real-time collaboration features",
                market_size_score=80.0,
                competition_score=68.0,
                urgency_score=88.0,
                total_score=78.7,
                grade="B",
            ),
            OpportunityView(
                rank=3,
                insight_id="insight_001",
                insight_title="Offline note-taking applications",
                market_size_score=72.0,
                competition_score=85.0,
                urgency_score=70.0,
                total_score=75.7,
                grade="B",
            ),
            OpportunityView(
                rank=4,
                insight_id="insight_002",
                insight_title="Slack integration improvements",
                market_size_score=75.0,
                competition_score=55.0,
                urgency_score=78.0,
                total_score=69.3,
                grade="B",
            ),
            OpportunityView(
                rank=5,
                insight_id="insight_007",
                insight_title="Privacy-focused alternatives",
                market_size_score=68.0,
                competition_score=72.0,
                urgency_score=65.0,
                total_score=68.3,
                grade="B",
            ),
            OpportunityView(
                rank=6,
                insight_id="insight_004",
                insight_title="Competitor X weakness",
                market_size_score=60.0,
                competition_score=80.0,
                urgency_score=55.0,
                total_score=65.0,
                grade="C",
            ),
            OpportunityView(
                rank=7,
                insight_id="insight_006",
                insight_title="Cross-platform bookmark sync",
                market_size_score=55.0,
                competition_score=70.0,
                urgency_score=50.0,
                total_score=58.3,
                grade="C",
            ),
            OpportunityView(
                rank=8,
                insight_id="insight_008",
                insight_title="Calendar task management",
                market_size_score=50.0,
                competition_score=45.0,
                urgency_score=55.0,
                total_score=50.0,
                grade="C",
            ),
        ]


# =============================================================================
# DEPENDENCY INJECTION
# =============================================================================


@lru_cache(maxsize=1)
def get_insight_service() -> InsightService:
    """InsightService 싱글톤 인스턴스를 반환한다.

    Returns:
        InsightService 인스턴스
    """
    return InsightService()
