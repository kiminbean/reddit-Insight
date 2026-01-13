"""대시보드 데이터 통합 테스트.

분석 파이프라인 → data_store → 대시보드 서비스 데이터 흐름을 검증한다.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from reddit_insight.dashboard.data_store import (
    AnalysisData,
    clear_cache,
    get_analysis_history,
    get_current_data,
    load_analysis_by_id,
    save_to_database,
    set_current_data,
)
from reddit_insight.dashboard.routers.competition import (
    CompetitionService,
    get_competition_service,
)
from reddit_insight.dashboard.routers.demands import (
    DemandService,
    get_demand_service,
)


# =============================================================================
# TEST FIXTURES
# =============================================================================


@pytest.fixture(autouse=True)
def reset_cache():
    """테스트 전후로 캐시를 초기화한다."""
    clear_cache()
    yield
    clear_cache()


@pytest.fixture
def sample_analysis_data() -> AnalysisData:
    """테스트용 분석 데이터를 생성한다."""
    return AnalysisData(
        subreddit="test_subreddit",
        analyzed_at=datetime.now(UTC).isoformat(),
        post_count=100,
        keywords=[
            {"keyword": "python", "score": 0.95, "frequency": 50},
            {"keyword": "machine learning", "score": 0.85, "frequency": 30},
            {"keyword": "automation", "score": 0.75, "frequency": 20},
        ],
        trends=[
            {
                "keyword": "python",
                "direction": "up",
                "change_rate": 0.15,
                "volatility": 0.1,
                "data_points": 7,
            },
            {
                "keyword": "machine learning",
                "direction": "stable",
                "change_rate": 0.02,
                "volatility": 0.05,
                "data_points": 7,
            },
        ],
        demands={
            "total_demands": 25,
            "total_clusters": 5,
            "by_category": {
                "feature_request": 10,
                "pain_point": 8,
                "unmet_need": 5,
                "willingness_to_pay": 2,
            },
            "top_opportunities": [
                {
                    "representative": "Need better documentation for API integration",
                    "size": 15,
                    "priority_score": 85.5,
                    "business_potential": "high",
                },
                {
                    "representative": "Looking for automated testing solutions",
                    "size": 12,
                    "priority_score": 72.3,
                    "business_potential": "medium",
                },
                {
                    "representative": "Wish there was a simpler way to deploy",
                    "size": 8,
                    "priority_score": 65.0,
                    "business_potential": "high",
                },
            ],
            "recommendations": [
                "Focus on improving API documentation",
                "Consider building automated testing tools",
                "Simplify deployment process",
            ],
        },
        competition={
            "entities_analyzed": 10,
            "insights": [
                {
                    "entity_name": "CompetitorA",
                    "entity_type": "product",
                    "mention_count": 45,
                    "sentiment_compound": 0.35,
                    "sentiment_positive": 0.55,
                    "sentiment_negative": 0.15,
                    "top_complaints": [
                        "Pricing is too high",
                        "Customer support is slow",
                    ],
                },
                {
                    "entity_name": "CompetitorB",
                    "entity_type": "service",
                    "mention_count": 30,
                    "sentiment_compound": -0.15,
                    "sentiment_positive": 0.25,
                    "sentiment_negative": 0.40,
                    "top_complaints": [
                        "Interface is confusing",
                        "Lacks essential features",
                        "Poor mobile experience",
                    ],
                },
                {
                    "entity_name": "CompetitorC",
                    "entity_type": "product",
                    "mention_count": 20,
                    "sentiment_compound": 0.02,
                    "sentiment_positive": 0.35,
                    "sentiment_negative": 0.30,
                    "top_complaints": [
                        "Setup is complicated",
                    ],
                },
            ],
            "top_complaints": [
                {"text": "Pricing is too high across all products", "severity": 0.85},
                {"text": "Customer support response time", "severity": 0.75},
                {"text": "Mobile experience needs improvement", "severity": 0.65},
            ],
            "popular_switches": [
                {"from": "CompetitorA", "to": "CompetitorB", "count": 15},
                {"from": "CompetitorB", "to": "CompetitorC", "count": 8},
            ],
            "recommendations": [
                "Address pricing concerns",
                "Improve customer support response time",
                "Enhance mobile experience",
            ],
        },
        insights=[
            {
                "type": "trend",
                "title": "'python' keyword trending",
                "description": "Python is gaining attention in this community.",
                "confidence": 0.95,
                "source": "keyword_analysis",
            },
        ],
    )


# =============================================================================
# DATA STORE TESTS
# =============================================================================


class TestDataStoreIntegration:
    """data_store 모듈 통합 테스트."""

    def test_set_and_get_current_data(self, sample_analysis_data: AnalysisData):
        """set_current_data 후 get_current_data로 데이터를 조회할 수 있다."""
        # When
        set_current_data(sample_analysis_data)
        result = get_current_data()

        # Then
        assert result is not None
        assert result.subreddit == "test_subreddit"
        assert result.post_count == 100
        assert len(result.keywords) == 3
        assert len(result.demands.get("top_opportunities", [])) == 3

    def test_data_persists_in_database(self, sample_analysis_data: AnalysisData):
        """데이터가 데이터베이스에 저장된다."""
        # When
        set_current_data(sample_analysis_data)

        # 캐시를 초기화하고 DB에서 다시 로드
        clear_cache()
        result = get_current_data()

        # Then
        assert result is not None
        assert result.subreddit == "test_subreddit"

    def test_get_analysis_history(self, sample_analysis_data: AnalysisData):
        """분석 이력을 조회할 수 있다."""
        # When
        set_current_data(sample_analysis_data)
        history = get_analysis_history(limit=10)

        # Then
        assert len(history) >= 1
        latest = history[0]
        assert latest["subreddit"] == "test_subreddit"
        assert latest["post_count"] == 100

    def test_load_analysis_by_id(self, sample_analysis_data: AnalysisData):
        """ID로 특정 분석 결과를 조회할 수 있다."""
        # Given: 데이터 저장 후 ID 확인
        set_current_data(sample_analysis_data)
        history = get_analysis_history(limit=1)
        analysis_id = history[0]["id"]

        # When
        result = load_analysis_by_id(analysis_id)

        # Then
        assert result is not None
        assert result.subreddit == "test_subreddit"
        assert result.post_count == 100
        assert len(result.keywords) == 3

    def test_load_analysis_by_id_not_found(self):
        """존재하지 않는 ID 조회 시 None을 반환한다."""
        # When
        result = load_analysis_by_id(99999)

        # Then
        assert result is None


# =============================================================================
# DEMAND SERVICE INTEGRATION TESTS
# =============================================================================


class TestDemandServiceIntegration:
    """DemandService 데이터 통합 테스트."""

    def test_get_demands_returns_stored_data(self, sample_analysis_data: AnalysisData):
        """set_current_data 후 DemandService.get_demands()가 데이터를 반환한다."""
        # Given
        set_current_data(sample_analysis_data)
        service = DemandService()

        # When
        demands = service.get_demands(limit=10)

        # Then
        assert len(demands) >= 1
        first_demand = demands[0]
        assert first_demand.priority_score == 85.5
        assert first_demand.business_potential == "high"
        assert "documentation" in first_demand.text.lower() or "api" in first_demand.text.lower()

    def test_get_demands_respects_min_priority(self, sample_analysis_data: AnalysisData):
        """최소 우선순위 필터가 작동한다."""
        # Given
        set_current_data(sample_analysis_data)
        service = DemandService()

        # When
        high_priority_demands = service.get_demands(min_priority=70.0)
        all_demands = service.get_demands(min_priority=0.0)

        # Then
        assert len(high_priority_demands) <= len(all_demands)
        for demand in high_priority_demands:
            assert demand.priority_score >= 70.0

    def test_get_category_stats_returns_stored_data(
        self, sample_analysis_data: AnalysisData
    ):
        """set_current_data 후 카테고리 통계를 조회할 수 있다."""
        # Given
        set_current_data(sample_analysis_data)
        service = DemandService()

        # When
        stats = service.get_category_stats()

        # Then
        assert stats.get("feature_request") == 10
        assert stats.get("pain_point") == 8
        assert stats.get("unmet_need") == 5
        assert stats.get("willingness_to_pay") == 2

    def test_get_recommendations_returns_stored_data(
        self, sample_analysis_data: AnalysisData
    ):
        """set_current_data 후 권장사항을 조회할 수 있다."""
        # Given
        set_current_data(sample_analysis_data)
        service = DemandService()

        # When
        recommendations = service.get_recommendations()

        # Then
        assert len(recommendations) == 3
        assert "documentation" in recommendations[0].lower()

    def test_get_demand_detail_returns_stored_data(
        self, sample_analysis_data: AnalysisData
    ):
        """set_current_data 후 수요 상세 정보를 조회할 수 있다."""
        # Given
        set_current_data(sample_analysis_data)
        service = DemandService()

        # When
        detail = service.get_demand_detail("demand_000")

        # Then
        assert detail is not None
        assert detail.demand.priority_score == 85.5
        assert detail.demand.business_potential == "high"


# =============================================================================
# COMPETITION SERVICE INTEGRATION TESTS
# =============================================================================


class TestCompetitionServiceIntegration:
    """CompetitionService 데이터 통합 테스트."""

    def test_get_entities_returns_stored_data(self, sample_analysis_data: AnalysisData):
        """set_current_data 후 CompetitionService.get_entities()가 데이터를 반환한다."""
        # Given
        set_current_data(sample_analysis_data)
        service = CompetitionService()

        # When
        entities = service.get_entities(limit=10)

        # Then
        assert len(entities) >= 1
        first_entity = entities[0]
        assert first_entity.name == "CompetitorA"
        assert first_entity.entity_type == "product"
        assert first_entity.mention_count == 45
        assert first_entity.sentiment_score == 0.35
        assert first_entity.sentiment_label == "positive"

    def test_get_entities_with_negative_sentiment(
        self, sample_analysis_data: AnalysisData
    ):
        """부정적 감성을 가진 엔티티를 올바르게 처리한다."""
        # Given
        set_current_data(sample_analysis_data)
        service = CompetitionService()

        # When
        entities = service.get_entities(limit=10)

        # Then
        competitor_b = next((e for e in entities if e.name == "CompetitorB"), None)
        assert competitor_b is not None
        assert competitor_b.sentiment_score == -0.15
        assert competitor_b.sentiment_label == "negative"

    def test_get_top_complaints_returns_stored_data(
        self, sample_analysis_data: AnalysisData
    ):
        """set_current_data 후 상위 불만을 조회할 수 있다."""
        # Given
        set_current_data(sample_analysis_data)
        service = CompetitionService()

        # When
        complaints = service.get_top_complaints(limit=10)

        # Then
        assert len(complaints) == 3
        first_complaint = complaints[0]
        assert "pricing" in first_complaint.text.lower()
        assert first_complaint.severity == 0.85

    def test_get_sentiment_distribution_returns_correct_values(
        self, sample_analysis_data: AnalysisData
    ):
        """set_current_data 후 감성 분포를 올바르게 계산한다."""
        # Given
        set_current_data(sample_analysis_data)
        service = CompetitionService()

        # When
        distribution = service.get_sentiment_distribution()

        # Then
        # 3개 엔티티 중 1개 positive, 1개 negative, 1개 neutral
        assert distribution["positive"] == pytest.approx(100 / 3, abs=0.1)
        assert distribution["negative"] == pytest.approx(100 / 3, abs=0.1)
        assert distribution["neutral"] == pytest.approx(100 / 3, abs=0.1)

    def test_get_popular_switches_returns_stored_data(
        self, sample_analysis_data: AnalysisData
    ):
        """set_current_data 후 제품 전환 데이터를 조회할 수 있다."""
        # Given
        set_current_data(sample_analysis_data)
        service = CompetitionService()

        # When
        switches = service.get_popular_switches()

        # Then
        assert len(switches) == 2
        first_switch = switches[0]
        assert first_switch["from"] == "CompetitorA"
        assert first_switch["to"] == "CompetitorB"
        assert first_switch["count"] == 15

    def test_get_entity_detail_returns_stored_data(
        self, sample_analysis_data: AnalysisData
    ):
        """set_current_data 후 엔티티 상세 정보를 조회할 수 있다."""
        # Given
        set_current_data(sample_analysis_data)
        service = CompetitionService()

        # When
        detail = service.get_entity_detail("CompetitorA")

        # Then
        assert detail is not None
        assert detail.entity.name == "CompetitorA"
        assert detail.entity.mention_count == 45
        assert len(detail.top_complaints) == 2

    def test_get_recommendations_returns_stored_data(
        self, sample_analysis_data: AnalysisData
    ):
        """set_current_data 후 경쟁 분석 권장사항을 조회할 수 있다."""
        # Given
        set_current_data(sample_analysis_data)
        service = CompetitionService()

        # When
        recommendations = service.get_recommendations()

        # Then
        assert len(recommendations) == 3
        assert "pricing" in recommendations[0].lower()


# =============================================================================
# END-TO-END DATA FLOW TESTS
# =============================================================================


class TestEndToEndDataFlow:
    """전체 데이터 흐름 E2E 테스트."""

    def test_full_data_pipeline(self, sample_analysis_data: AnalysisData):
        """전체 데이터 파이프라인이 올바르게 작동한다.

        분석 데이터 저장 → 서비스 조회 → 데이터 일치 확인
        """
        # Given: 분석 데이터 저장
        set_current_data(sample_analysis_data)

        # When: 각 서비스에서 데이터 조회
        demand_service = DemandService()
        competition_service = CompetitionService()

        demands = demand_service.get_demands()
        demand_stats = demand_service.get_category_stats()
        demand_recommendations = demand_service.get_recommendations()

        entities = competition_service.get_entities()
        complaints = competition_service.get_top_complaints()
        switches = competition_service.get_popular_switches()
        competition_recommendations = competition_service.get_recommendations()

        # Then: 데이터 정합성 확인
        # Demands 검증
        assert len(demands) == 3
        assert sum(demand_stats.values()) == 25  # total_demands와 일치
        assert len(demand_recommendations) == 3

        # Competition 검증
        assert len(entities) == 3
        assert len(complaints) == 3
        assert len(switches) == 2
        assert len(competition_recommendations) == 3

    def test_data_isolation_between_analyses(self):
        """서로 다른 분석 데이터가 올바르게 격리된다."""
        # Given: 첫 번째 분석 데이터
        first_data = AnalysisData(
            subreddit="first_subreddit",
            analyzed_at=datetime.now(UTC).isoformat(),
            post_count=50,
            demands={
                "total_demands": 10,
                "top_opportunities": [
                    {
                        "representative": "First opportunity",
                        "size": 5,
                        "priority_score": 90.0,
                        "business_potential": "high",
                    }
                ],
                "by_category": {"feature_request": 10},
                "recommendations": ["First recommendation"],
            },
            competition={
                "insights": [
                    {
                        "entity_name": "FirstCompetitor",
                        "entity_type": "product",
                        "mention_count": 20,
                        "sentiment_compound": 0.5,
                        "top_complaints": [],
                    }
                ],
                "top_complaints": [],
                "popular_switches": [],
                "recommendations": [],
            },
        )

        # When: 첫 번째 데이터 저장
        set_current_data(first_data)
        demand_service_1 = DemandService()
        demands_1 = demand_service_1.get_demands()

        # Given: 두 번째 분석 데이터로 덮어쓰기
        second_data = AnalysisData(
            subreddit="second_subreddit",
            analyzed_at=datetime.now(UTC).isoformat(),
            post_count=100,
            demands={
                "total_demands": 20,
                "top_opportunities": [
                    {
                        "representative": "Second opportunity",
                        "size": 10,
                        "priority_score": 80.0,
                        "business_potential": "medium",
                    }
                ],
                "by_category": {"pain_point": 20},
                "recommendations": ["Second recommendation"],
            },
            competition={
                "insights": [
                    {
                        "entity_name": "SecondCompetitor",
                        "entity_type": "service",
                        "mention_count": 30,
                        "sentiment_compound": -0.3,
                        "top_complaints": [],
                    }
                ],
                "top_complaints": [],
                "popular_switches": [],
                "recommendations": [],
            },
        )

        # When: 두 번째 데이터 저장
        set_current_data(second_data)
        demand_service_2 = DemandService()
        demands_2 = demand_service_2.get_demands()

        competition_service = CompetitionService()
        entities = competition_service.get_entities()

        # Then: 두 번째 데이터만 조회되어야 함
        assert len(demands_2) == 1
        assert "Second opportunity" in demands_2[0].text

        assert len(entities) == 1
        assert entities[0].name == "SecondCompetitor"

    def test_empty_data_handling(self):
        """빈 데이터를 올바르게 처리한다."""
        # Given: 빈 분석 데이터
        empty_data = AnalysisData(
            subreddit="empty_subreddit",
            analyzed_at=datetime.now(UTC).isoformat(),
            post_count=0,
            demands={},
            competition={},
        )

        # When
        set_current_data(empty_data)
        demand_service = DemandService()
        competition_service = CompetitionService()

        demands = demand_service.get_demands()
        entities = competition_service.get_entities()

        # Then: 빈 리스트 반환
        assert demands == []
        assert entities == []
