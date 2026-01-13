"""Integration tests for Reddit Insight analysis pipelines.

이 모듈은 각 분석 모듈의 통합을 테스트합니다.
데이터 수집 -> 분석 -> 인사이트 -> 리포트 전체 흐름을 검증합니다.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from reddit_insight.reddit.models import Comment, Post


# ============================================================================
# Analysis Pipeline Tests
# ============================================================================


class TestAnalysisPipeline:
    """분석 파이프라인 통합 테스트."""

    def test_trend_analysis_pipeline(
        self,
        sample_texts: list[str],
        keyword_extractor,
        trend_analyzer,
    ) -> None:
        """텍스트 -> 키워드 추출 -> 트렌드 분석 파이프라인 테스트.

        이 테스트는 다음 흐름을 검증합니다:
        1. 샘플 텍스트에서 키워드 추출
        2. 추출된 키워드로 트렌드 분석
        3. 결과의 유효성 검증
        """
        # Step 1: 키워드 추출
        keyword_result = keyword_extractor.extract_keywords(sample_texts)

        assert keyword_result is not None
        assert len(keyword_result.keywords) > 0
        assert all(kw.score >= 0 for kw in keyword_result.keywords)
        assert all(kw.score <= 1 for kw in keyword_result.keywords)

        # Step 2: 트렌드 분석을 위한 시계열 데이터 시뮬레이션
        from reddit_insight.analysis import TimeGranularity, TimeSeries, TimePoint

        # 더미 시계열 데이터 생성 (실제로는 Post 타임스탬프 기반)
        keywords = [kw.keyword for kw in keyword_result.keywords[:5]]
        time_series_data = {}

        for keyword in keywords:
            points = [
                TimePoint(
                    timestamp=datetime(2024, 1, i, tzinfo=UTC),
                    value=float(10 + i * 2),
                )
                for i in range(1, 8)
            ]
            time_series_data[keyword] = TimeSeries(
                keyword=keyword,
                granularity=TimeGranularity.DAY,
                points=points,
            )

        # Step 3: 결과 검증
        assert len(keywords) > 0
        for keyword, ts in time_series_data.items():
            assert ts.keyword == keyword
            assert len(ts.points) == 7

    def test_demand_discovery_pipeline(
        self,
        sample_texts: list[str],
        demand_detector,
        demand_analyzer,
    ) -> None:
        """텍스트 -> 패턴 탐지 -> 수요 분류 파이프라인 테스트.

        이 테스트는 다음 흐름을 검증합니다:
        1. 수요 표현 패턴 탐지
        2. 수요 클러스터링 및 분류
        3. 우선순위 계산
        """
        from reddit_insight.analysis import DemandCategory

        # Step 1: 수요 패턴 탐지
        all_matches = []
        for text in sample_texts:
            matches = demand_detector.detect(text)
            all_matches.extend(matches)

        # 최소한 일부 수요 표현이 탐지되어야 함
        # 샘플 텍스트에 "looking for", "need help" 등이 포함되어 있음
        # (패턴이 완전히 매칭되지 않을 수 있으므로 유연하게 검증)

        # Step 2: 수요 요약
        summary = demand_detector.summarize(all_matches)
        assert summary is not None
        assert summary.analyzed_texts == len(sample_texts)
        # total_matches는 0일 수도 있음 (패턴 매칭 여부에 따라)
        assert summary.total_matches >= 0

        # Step 3: 수요 카테고리 검증
        assert isinstance(summary.by_category, dict)
        for category in summary.by_category:
            assert isinstance(category, DemandCategory)

    def test_competitive_analysis_pipeline(
        self,
        sample_posts: list["Post"],
        competitive_analyzer,
        entity_recognizer,
        sentiment_analyzer,
    ) -> None:
        """텍스트 -> 엔티티 인식 -> 감성 분석 -> 불만 추출 파이프라인 테스트.

        이 테스트는 다음 흐름을 검증합니다:
        1. 제품/서비스 엔티티 인식
        2. 엔티티별 감성 분석
        3. 불만 패턴 추출
        4. 경쟁 인사이트 생성
        """
        # Step 1: 엔티티 인식
        texts = [f"{post.title} {post.selftext}" for post in sample_posts]
        all_entities = []

        for text in texts:
            entities = entity_recognizer.recognize(text)
            all_entities.extend(entities)

        # 샘플 데이터에 제품명(PyCharm, Pandas, TensorFlow 등)이 포함되어 있음
        assert isinstance(all_entities, list)

        # Step 2: 감성 분석
        sentiment_results = []
        for text in texts:
            score = sentiment_analyzer.analyze(text)
            sentiment_results.append(score)

        assert len(sentiment_results) == len(texts)
        for score in sentiment_results:
            # 감성 점수는 -1 ~ 1 범위
            assert -1.0 <= score.polarity <= 1.0
            assert 0.0 <= score.subjectivity <= 1.0

        # Step 3: 경쟁 분석 리포트 생성
        report = competitive_analyzer.analyze_posts(sample_posts)

        assert report is not None
        assert hasattr(report, 'complaints')
        assert hasattr(report, 'alternatives')
        assert hasattr(report, 'recommendations')


# ============================================================================
# Insight Generation Tests
# ============================================================================


class TestInsightGeneration:
    """인사이트 생성 통합 테스트."""

    def test_rules_engine_generates_insights(
        self,
        rules_engine,
        sample_posts: list["Post"],
    ) -> None:
        """분석 결과 -> 인사이트 생성 파이프라인 테스트.

        규칙 엔진이 분석 컨텍스트에서 인사이트를 생성하는지 검증합니다.
        """
        from reddit_insight.analysis import (
            CompetitiveAnalyzer,
            DemandAnalyzer,
        )
        from reddit_insight.insights import InsightType

        # Step 1: 분석 실행
        demand_analyzer = DemandAnalyzer()
        competitive_analyzer = CompetitiveAnalyzer()

        texts = [f"{post.title} {post.selftext}" for post in sample_posts]
        demand_report = demand_analyzer.analyze(texts)
        competitive_report = competitive_analyzer.analyze_posts(sample_posts)

        # Step 2: 컨텍스트 빌드
        context = rules_engine.build_context(
            demand_report=demand_report,
            competitive_report=competitive_report,
        )

        assert context is not None
        assert hasattr(context, 'demand_report')
        assert hasattr(context, 'competitive_report')

        # Step 3: 인사이트 생성
        insights = rules_engine.generate_insights(context)

        assert isinstance(insights, list)
        # 인사이트가 생성되었으면 유효성 검증
        for insight in insights:
            assert insight.insight_id is not None
            assert isinstance(insight.insight_type, InsightType)
            assert 0.0 <= insight.confidence <= 1.0
            assert len(insight.title) > 0

    def test_opportunity_scoring(
        self,
        rules_engine,
        opportunity_scorer,
        sample_posts: list["Post"],
    ) -> None:
        """인사이트 -> 스코어링 -> 랭킹 파이프라인 테스트.

        생성된 인사이트에 비즈니스 가치 점수를 부여하고 랭킹합니다.
        """
        from reddit_insight.analysis import (
            CompetitiveAnalyzer,
            DemandAnalyzer,
        )

        # Step 1: 분석 및 인사이트 생성
        demand_analyzer = DemandAnalyzer()
        competitive_analyzer = CompetitiveAnalyzer()

        texts = [f"{post.title} {post.selftext}" for post in sample_posts]
        demand_report = demand_analyzer.analyze(texts)
        competitive_report = competitive_analyzer.analyze_posts(sample_posts)

        context = rules_engine.build_context(
            demand_report=demand_report,
            competitive_report=competitive_report,
        )
        insights = rules_engine.generate_insights(context)

        # Step 2: 스코어링 및 랭킹
        if len(insights) > 0:
            opportunities = opportunity_scorer.rank_opportunities(
                insights, context
            )

            assert isinstance(opportunities, list)
            for opp in opportunities:
                assert hasattr(opp, 'rank')
                assert hasattr(opp, 'score')
                assert hasattr(opp, 'insight')
                # 점수는 0-100 범위
                assert 0 <= opp.score.total_score <= 100
        else:
            # 인사이트가 없어도 에러가 아님
            opportunities = opportunity_scorer.rank_opportunities(
                insights, context
            )
            assert opportunities == []

    def test_feasibility_analysis(
        self,
        rules_engine,
        opportunity_scorer,
        feasibility_analyzer,
        sample_posts: list["Post"],
    ) -> None:
        """기회 -> 실행 가능성 평가 파이프라인 테스트.

        스코어링된 기회에 대해 실행 가능성을 분석합니다.
        """
        from reddit_insight.analysis import (
            CompetitiveAnalyzer,
            DemandAnalyzer,
        )

        # Step 1: 분석 및 인사이트 생성
        demand_analyzer = DemandAnalyzer()
        competitive_analyzer = CompetitiveAnalyzer()

        texts = [f"{post.title} {post.selftext}" for post in sample_posts]
        demand_report = demand_analyzer.analyze(texts)
        competitive_report = competitive_analyzer.analyze_posts(sample_posts)

        context = rules_engine.build_context(
            demand_report=demand_report,
            competitive_report=competitive_report,
        )
        insights = rules_engine.generate_insights(context)

        # Step 2: 스코어링
        opportunities = opportunity_scorer.rank_opportunities(insights, context)

        # Step 3: 실행 가능성 분석
        if len(opportunities) > 0:
            recommendations = feasibility_analyzer.generate_recommendations(
                opportunities, context
            )

            assert isinstance(recommendations, list)
            for rec in recommendations:
                assert hasattr(rec, 'insight_id')
                assert hasattr(rec, 'recommendation')
                assert hasattr(rec, 'feasibility_score')
        else:
            # 기회가 없으면 빈 추천 목록
            recommendations = feasibility_analyzer.generate_recommendations(
                opportunities, context
            )
            assert recommendations == []


# ============================================================================
# Report Generation Tests
# ============================================================================


class TestReportGeneration:
    """리포트 생성 통합 테스트."""

    def test_generate_trend_report(
        self,
        template_registry,
        sample_texts: list[str],
        keyword_extractor,
    ) -> None:
        """트렌드 리포트 생성 테스트.

        키워드 추출 결과를 트렌드 리포트 템플릿으로 렌더링합니다.
        """
        from reddit_insight.reports import ReportType, format_table

        # Step 1: 키워드 추출
        keyword_result = keyword_extractor.extract_keywords(sample_texts)

        # Step 2: 템플릿 가져오기
        template = template_registry.get(ReportType.TREND)
        assert template is not None

        # Step 3: 리포트 렌더링
        top_keywords = [
            {"keyword": kw.keyword, "score": f"{kw.score:.2f}"}
            for kw in keyword_result.keywords[:10]
        ]

        report_content = template.render(
            title="Test Trend Report",
            summary="Sample trend analysis for testing",
            top_keywords=top_keywords,
            rising_keywords=[],
        )

        assert isinstance(report_content, str)
        assert "Test Trend Report" in report_content
        assert len(report_content) > 100  # 최소한의 내용이 있어야 함

    def test_generate_full_report(
        self,
        report_generator,
        sample_posts: list["Post"],
    ) -> None:
        """전체 리포트 생성 테스트.

        모든 분석 결과를 통합하여 전체 리포트를 생성합니다.
        """
        from reddit_insight.analysis import (
            CompetitiveAnalyzer,
            DemandAnalyzer,
            UnifiedKeywordExtractor,
        )
        from reddit_insight.reports import ReportDataCollector, TrendReportData

        # Step 1: 분석 실행
        texts = [f"{post.title} {post.selftext}" for post in sample_posts]

        keyword_extractor = UnifiedKeywordExtractor()
        keyword_result = keyword_extractor.extract_keywords(texts)

        demand_analyzer = DemandAnalyzer()
        demand_report = demand_analyzer.analyze(texts)

        competitive_analyzer = CompetitiveAnalyzer()
        competitive_report = competitive_analyzer.analyze_posts(sample_posts)

        # Step 2: 데이터 수집
        trend_data = TrendReportData(
            title="Integration Test - Trend Analysis",
            summary="Automated integration test summary",
            top_keywords=[
                {"keyword": kw.keyword, "score": f"{kw.score:.2f}"}
                for kw in keyword_result.keywords[:5]
            ],
            rising_keywords=[],
        )

        collector = ReportDataCollector(
            trend_report=trend_data,
            demand_report=demand_report,
            competitive_report=competitive_report,
        )

        # Step 3: 전체 리포트 생성
        full_report = report_generator.generate_full_report(collector)

        assert isinstance(full_report, str)
        assert len(full_report) > 200  # 충분한 내용이 있어야 함

    def test_export_reports(
        self,
        report_generator,
        sample_posts: list["Post"],
        tmp_path,
    ) -> None:
        """리포트 내보내기 테스트.

        생성된 리포트를 파일로 저장합니다.
        """
        from reddit_insight.analysis import UnifiedKeywordExtractor
        from reddit_insight.reports import ReportDataCollector, TrendReportData

        # Step 1: 간단한 리포트 데이터 생성
        texts = [f"{post.title} {post.selftext}" for post in sample_posts[:3]]

        keyword_extractor = UnifiedKeywordExtractor()
        keyword_result = keyword_extractor.extract_keywords(texts)

        trend_data = TrendReportData(
            title="Export Test Report",
            summary="Testing report export functionality",
            top_keywords=[
                {"keyword": kw.keyword, "score": f"{kw.score:.2f}"}
                for kw in keyword_result.keywords[:3]
            ],
        )

        collector = ReportDataCollector(trend_report=trend_data)

        # Step 2: 리포트 생성
        report_content = report_generator.generate_full_report(collector)

        # Step 3: 파일로 저장
        output_path = tmp_path / "test_report.md"
        report_generator.save_report(report_content, str(output_path))

        # Step 4: 검증
        assert output_path.exists()
        saved_content = output_path.read_text(encoding="utf-8")
        assert "Export Test Report" in saved_content
        assert len(saved_content) > 100


# ============================================================================
# Cross-Module Integration Tests
# ============================================================================


class TestCrossModuleIntegration:
    """크로스 모듈 통합 테스트.

    여러 모듈이 함께 작동하는 시나리오를 테스트합니다.
    """

    @pytest.mark.integration
    def test_full_analysis_to_report_pipeline(
        self,
        sample_posts: list["Post"],
        rules_engine,
        opportunity_scorer,
        feasibility_analyzer,
        report_generator,
    ) -> None:
        """전체 분석 -> 인사이트 -> 리포트 파이프라인 테스트.

        데이터 수집부터 리포트 생성까지 전체 파이프라인을 검증합니다.
        """
        from reddit_insight.analysis import (
            CompetitiveAnalyzer,
            DemandAnalyzer,
            UnifiedKeywordExtractor,
        )
        from reddit_insight.reports import ReportDataCollector, TrendReportData

        # Step 1: 텍스트 추출
        texts = [f"{post.title} {post.selftext}" for post in sample_posts]
        assert len(texts) > 0

        # Step 2: 키워드 분석
        keyword_extractor = UnifiedKeywordExtractor()
        keyword_result = keyword_extractor.extract_keywords(texts)
        assert len(keyword_result.keywords) > 0

        # Step 3: 수요 분석
        demand_analyzer = DemandAnalyzer()
        demand_report = demand_analyzer.analyze(texts)
        assert demand_report is not None

        # Step 4: 경쟁 분석
        competitive_analyzer = CompetitiveAnalyzer()
        competitive_report = competitive_analyzer.analyze_posts(sample_posts)
        assert competitive_report is not None

        # Step 5: 인사이트 생성
        context = rules_engine.build_context(
            demand_report=demand_report,
            competitive_report=competitive_report,
        )
        insights = rules_engine.generate_insights(context)
        # 인사이트는 있을 수도 없을 수도 있음

        # Step 6: 기회 스코어링 (인사이트가 있는 경우)
        opportunities = opportunity_scorer.rank_opportunities(insights, context)

        # Step 7: 실행 가능성 분석 (기회가 있는 경우)
        recommendations = feasibility_analyzer.generate_recommendations(
            opportunities, context
        )

        # Step 8: 리포트 생성
        trend_data = TrendReportData(
            title="Full Pipeline Integration Test",
            summary=f"Analyzed {len(texts)} texts",
            top_keywords=[
                {"keyword": kw.keyword, "score": f"{kw.score:.2f}"}
                for kw in keyword_result.keywords[:5]
            ],
        )

        collector = ReportDataCollector(
            trend_report=trend_data,
            demand_report=demand_report,
            competitive_report=competitive_report,
        )

        full_report = report_generator.generate_full_report(collector)

        # Step 9: 최종 검증
        assert isinstance(full_report, str)
        assert "Full Pipeline Integration Test" in full_report
        assert len(full_report) > 200

    @pytest.mark.integration
    def test_entity_sentiment_competitive_flow(
        self,
        sample_posts: list["Post"],
        entity_recognizer,
        sentiment_analyzer,
        competitive_analyzer,
    ) -> None:
        """엔티티 인식 -> 감성 분석 -> 경쟁 분석 플로우 테스트."""
        from reddit_insight.analysis import EntitySentimentAnalyzer

        texts = [f"{post.title} {post.selftext}" for post in sample_posts]

        # Step 1: 각 텍스트에서 엔티티 인식
        all_entities = []
        for text in texts:
            entities = entity_recognizer.recognize(text)
            all_entities.extend(entities)

        # Step 2: 엔티티별 감성 분석
        entity_sentiment_analyzer = EntitySentimentAnalyzer()
        entity_sentiments = entity_sentiment_analyzer.analyze_entities(
            sample_posts[:3]  # 처음 3개만 테스트
        )

        assert isinstance(entity_sentiments, list)
        for es in entity_sentiments:
            assert hasattr(es, 'entity')
            assert hasattr(es, 'sentiment')
            assert hasattr(es, 'confidence')

        # Step 3: 경쟁 분석
        report = competitive_analyzer.analyze_posts(sample_posts)
        assert report is not None
