"""검색 서비스.

검색 기능을 제공하는 서비스 레이어.
키워드, 엔티티, 인사이트, 수요를 통합 검색한다.
"""

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any


# =============================================================================
# SEARCH RESULT DATA STRUCTURES
# =============================================================================


@dataclass
class KeywordResult:
    """키워드 검색 결과.

    Attributes:
        keyword: 키워드 문자열
        frequency: 출현 빈도
        trend: 트렌드 방향 (up/down/stable)
    """

    keyword: str
    frequency: int
    trend: str

    @property
    def trend_icon(self) -> str:
        """트렌드 아이콘 클래스를 반환한다."""
        icon_map = {
            "up": "text-green-500",
            "down": "text-red-500",
            "stable": "text-gray-500",
        }
        return icon_map.get(self.trend, "text-gray-500")

    @property
    def trend_arrow(self) -> str:
        """트렌드 화살표를 반환한다."""
        arrow_map = {
            "up": "^",
            "down": "v",
            "stable": "-",
        }
        return arrow_map.get(self.trend, "-")


@dataclass
class EntityResult:
    """엔티티 검색 결과.

    Attributes:
        name: 엔티티 이름
        entity_type: 엔티티 유형 (product/company/brand)
        sentiment: 감성 점수 (-1 ~ 1)
    """

    name: str
    entity_type: str
    sentiment: float

    @property
    def sentiment_display(self) -> str:
        """감성 점수를 표시용 문자열로 변환한다."""
        if self.sentiment > 0.2:
            return "Positive"
        elif self.sentiment < -0.2:
            return "Negative"
        return "Neutral"

    @property
    def sentiment_color(self) -> str:
        """감성 점수에 따른 색상 클래스를 반환한다."""
        if self.sentiment > 0.2:
            return "text-green-600"
        elif self.sentiment < -0.2:
            return "text-red-600"
        return "text-gray-600"

    @property
    def type_display(self) -> str:
        """유형을 표시용 문자열로 변환한다."""
        type_map = {
            "product": "Product",
            "company": "Company",
            "brand": "Brand",
            "service": "Service",
        }
        return type_map.get(self.entity_type, self.entity_type.title())


@dataclass
class InsightResult:
    """인사이트 검색 결과.

    Attributes:
        id: 인사이트 ID
        title: 인사이트 제목
        insight_type: 인사이트 유형
        confidence: 신뢰도 (0-1)
    """

    id: str
    title: str
    insight_type: str
    confidence: float

    @property
    def confidence_percent(self) -> int:
        """신뢰도를 백분율로 반환한다."""
        return int(self.confidence * 100)

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


@dataclass
class DemandResult:
    """수요 검색 결과.

    Attributes:
        id: 수요 ID
        text: 수요 텍스트
        category: 수요 카테고리
        priority: 우선순위 (0-100)
    """

    id: str
    text: str
    category: str
    priority: float

    @property
    def priority_display(self) -> str:
        """우선순위를 표시용 문자열로 변환한다."""
        if self.priority >= 80:
            return "High"
        elif self.priority >= 50:
            return "Medium"
        return "Low"

    @property
    def priority_color(self) -> str:
        """우선순위에 따른 색상 클래스를 반환한다."""
        if self.priority >= 80:
            return "text-red-600"
        elif self.priority >= 50:
            return "text-yellow-600"
        return "text-gray-600"

    @property
    def category_display(self) -> str:
        """카테고리를 표시용 문자열로 변환한다."""
        return self.category.replace("_", " ").title()


@dataclass
class SearchResults:
    """통합 검색 결과.

    Attributes:
        query: 검색어
        total_count: 총 결과 수
        keywords: 키워드 결과 목록
        entities: 엔티티 결과 목록
        insights: 인사이트 결과 목록
        demands: 수요 결과 목록
    """

    query: str
    total_count: int = 0
    keywords: list[KeywordResult] = field(default_factory=list)
    entities: list[EntityResult] = field(default_factory=list)
    insights: list[InsightResult] = field(default_factory=list)
    demands: list[DemandResult] = field(default_factory=list)

    @property
    def has_results(self) -> bool:
        """결과가 있는지 확인한다."""
        return self.total_count > 0

    @property
    def keywords_count(self) -> int:
        """키워드 결과 수를 반환한다."""
        return len(self.keywords)

    @property
    def entities_count(self) -> int:
        """엔티티 결과 수를 반환한다."""
        return len(self.entities)

    @property
    def insights_count(self) -> int:
        """인사이트 결과 수를 반환한다."""
        return len(self.insights)

    @property
    def demands_count(self) -> int:
        """수요 결과 수를 반환한다."""
        return len(self.demands)


# =============================================================================
# SEARCH SERVICE
# =============================================================================


class SearchService:
    """검색 서비스.

    대시보드에서 사용할 검색 기능을 제공한다.
    키워드, 엔티티, 인사이트, 수요를 통합 검색한다.
    현재는 데모용 목 데이터를 사용한다.

    Example:
        >>> service = SearchService()
        >>> results = service.search("productivity", limit=10)
        >>> print(f"Found {results.total_count} results")
    """

    def __init__(self) -> None:
        """서비스 초기화."""
        # 데모용 목 데이터
        self._mock_keywords = self._generate_mock_keywords()
        self._mock_entities = self._generate_mock_entities()
        self._mock_insights = self._generate_mock_insights()
        self._mock_demands = self._generate_mock_demands()

    def search(
        self,
        query: str,
        search_type: str | None = None,
        limit: int = 20,
    ) -> SearchResults:
        """통합 검색을 수행한다.

        Args:
            query: 검색어
            search_type: 검색 유형 필터 (keywords/entities/insights/demands)
            limit: 결과 수 제한

        Returns:
            SearchResults: 통합 검색 결과
        """
        query_lower = query.lower()
        per_type_limit = limit // 4 if search_type is None else limit

        keywords = []
        entities = []
        insights = []
        demands = []

        # 유형별 검색
        if search_type is None or search_type == "keywords":
            keywords = self._search_keywords(query_lower, per_type_limit)

        if search_type is None or search_type == "entities":
            entities = self._search_entities(query_lower, per_type_limit)

        if search_type is None or search_type == "insights":
            insights = self._search_insights(query_lower, per_type_limit)

        if search_type is None or search_type == "demands":
            demands = self._search_demands(query_lower, per_type_limit)

        total_count = len(keywords) + len(entities) + len(insights) + len(demands)

        return SearchResults(
            query=query,
            total_count=total_count,
            keywords=keywords,
            entities=entities,
            insights=insights,
            demands=demands,
        )

    def get_suggestions(self, query: str, limit: int = 5) -> list[str]:
        """자동완성 제안을 반환한다.

        Args:
            query: 검색어
            limit: 제안 수 제한

        Returns:
            제안 문자열 목록
        """
        query_lower = query.lower()
        suggestions = []

        # 키워드에서 제안
        for kw in self._mock_keywords:
            if query_lower in kw.keyword.lower():
                suggestions.append(kw.keyword)
                if len(suggestions) >= limit:
                    break

        # 엔티티 이름에서 제안
        if len(suggestions) < limit:
            for entity in self._mock_entities:
                if query_lower in entity.name.lower():
                    suggestions.append(entity.name)
                    if len(suggestions) >= limit:
                        break

        # 인사이트 제목에서 제안
        if len(suggestions) < limit:
            for insight in self._mock_insights:
                if query_lower in insight.title.lower():
                    # 제목에서 관련 단어 추출
                    words = insight.title.split()
                    for word in words:
                        if query_lower in word.lower() and word not in suggestions:
                            suggestions.append(word)
                            if len(suggestions) >= limit:
                                break

        return suggestions[:limit]

    def _search_keywords(self, query: str, limit: int) -> list[KeywordResult]:
        """키워드를 검색한다."""
        results = []
        for kw in self._mock_keywords:
            if query in kw.keyword.lower():
                results.append(kw)
                if len(results) >= limit:
                    break
        return results

    def _search_entities(self, query: str, limit: int) -> list[EntityResult]:
        """엔티티를 검색한다."""
        results = []
        for entity in self._mock_entities:
            if query in entity.name.lower() or query in entity.entity_type.lower():
                results.append(entity)
                if len(results) >= limit:
                    break
        return results

    def _search_insights(self, query: str, limit: int) -> list[InsightResult]:
        """인사이트를 검색한다."""
        results = []
        for insight in self._mock_insights:
            if query in insight.title.lower() or query in insight.insight_type.lower():
                results.append(insight)
                if len(results) >= limit:
                    break
        return results

    def _search_demands(self, query: str, limit: int) -> list[DemandResult]:
        """수요를 검색한다."""
        results = []
        for demand in self._mock_demands:
            if query in demand.text.lower() or query in demand.category.lower():
                results.append(demand)
                if len(results) >= limit:
                    break
        return results

    # ==========================================================================
    # MOCK DATA GENERATORS (데모용)
    # ==========================================================================

    def _generate_mock_keywords(self) -> list[KeywordResult]:
        """데모용 키워드 목 데이터를 생성한다."""
        return [
            KeywordResult(keyword="productivity", frequency=450, trend="up"),
            KeywordResult(keyword="automation", frequency=380, trend="up"),
            KeywordResult(keyword="AI tools", frequency=520, trend="up"),
            KeywordResult(keyword="note-taking", frequency=290, trend="stable"),
            KeywordResult(keyword="collaboration", frequency=410, trend="up"),
            KeywordResult(keyword="privacy", frequency=320, trend="up"),
            KeywordResult(keyword="integration", frequency=280, trend="stable"),
            KeywordResult(keyword="offline", frequency=150, trend="down"),
            KeywordResult(keyword="sync", frequency=340, trend="stable"),
            KeywordResult(keyword="calendar", frequency=260, trend="stable"),
            KeywordResult(keyword="task management", frequency=380, trend="up"),
            KeywordResult(keyword="workflow", frequency=290, trend="up"),
            KeywordResult(keyword="cloud storage", frequency=220, trend="stable"),
            KeywordResult(keyword="mobile app", frequency=310, trend="up"),
            KeywordResult(keyword="desktop app", frequency=180, trend="down"),
        ]

    def _generate_mock_entities(self) -> list[EntityResult]:
        """데모용 엔티티 목 데이터를 생성한다."""
        return [
            EntityResult(name="Notion", entity_type="product", sentiment=0.65),
            EntityResult(name="Slack", entity_type="product", sentiment=0.45),
            EntityResult(name="Obsidian", entity_type="product", sentiment=0.78),
            EntityResult(name="Microsoft", entity_type="company", sentiment=0.32),
            EntityResult(name="Google", entity_type="company", sentiment=0.28),
            EntityResult(name="Todoist", entity_type="product", sentiment=0.55),
            EntityResult(name="Trello", entity_type="product", sentiment=0.42),
            EntityResult(name="Asana", entity_type="product", sentiment=0.38),
            EntityResult(name="Linear", entity_type="product", sentiment=0.72),
            EntityResult(name="ClickUp", entity_type="product", sentiment=0.35),
            EntityResult(name="Roam Research", entity_type="product", sentiment=0.68),
            EntityResult(name="Logseq", entity_type="product", sentiment=0.75),
            EntityResult(name="Apple", entity_type="company", sentiment=0.52),
        ]

    def _generate_mock_insights(self) -> list[InsightResult]:
        """데모용 인사이트 목 데이터를 생성한다."""
        return [
            InsightResult(
                id="insight_001",
                title="Market gap in offline note-taking applications",
                insight_type="market_gap",
                confidence=0.87,
            ),
            InsightResult(
                id="insight_002",
                title="High demand for better Slack integration",
                insight_type="improvement_opportunity",
                confidence=0.82,
            ),
            InsightResult(
                id="insight_003",
                title="Rising interest in AI-powered productivity tools",
                insight_type="emerging_trend",
                confidence=0.91,
            ),
            InsightResult(
                id="insight_004",
                title="Competitor X showing declining user satisfaction",
                insight_type="competitive_weakness",
                confidence=0.75,
            ),
            InsightResult(
                id="insight_005",
                title="Users willing to pay for real-time collaboration",
                insight_type="unmet_need",
                confidence=0.88,
            ),
            InsightResult(
                id="insight_006",
                title="No solution for cross-platform bookmark sync",
                insight_type="market_gap",
                confidence=0.79,
            ),
            InsightResult(
                id="insight_007",
                title="Growing demand for privacy-focused alternatives",
                insight_type="emerging_trend",
                confidence=0.84,
            ),
            InsightResult(
                id="insight_008",
                title="Calendar apps need better task management",
                insight_type="improvement_opportunity",
                confidence=0.76,
            ),
        ]

    def _generate_mock_demands(self) -> list[DemandResult]:
        """데모용 수요 목 데이터를 생성한다."""
        return [
            DemandResult(
                id="demand_001",
                text="Need offline mode for note-taking app",
                category="feature_request",
                priority=85.0,
            ),
            DemandResult(
                id="demand_002",
                text="Better integration with calendar apps",
                category="integration",
                priority=78.0,
            ),
            DemandResult(
                id="demand_003",
                text="AI-powered summarization feature",
                category="feature_request",
                priority=92.0,
            ),
            DemandResult(
                id="demand_004",
                text="Real-time collaboration like Google Docs",
                category="collaboration",
                priority=88.0,
            ),
            DemandResult(
                id="demand_005",
                text="End-to-end encryption for privacy",
                category="security",
                priority=82.0,
            ),
            DemandResult(
                id="demand_006",
                text="Cross-platform sync without cloud dependency",
                category="feature_request",
                priority=75.0,
            ),
            DemandResult(
                id="demand_007",
                text="Better mobile app experience",
                category="ux_improvement",
                priority=70.0,
            ),
            DemandResult(
                id="demand_008",
                text="Automatic backup and versioning",
                category="feature_request",
                priority=68.0,
            ),
            DemandResult(
                id="demand_009",
                text="Plugin ecosystem for extensibility",
                category="platform",
                priority=65.0,
            ),
            DemandResult(
                id="demand_010",
                text="Dark mode support across all platforms",
                category="ux_improvement",
                priority=55.0,
            ),
        ]


# =============================================================================
# DEPENDENCY INJECTION
# =============================================================================


@lru_cache(maxsize=1)
def get_search_service() -> SearchService:
    """SearchService 싱글톤 인스턴스를 반환한다.

    Returns:
        SearchService 인스턴스
    """
    return SearchService()
