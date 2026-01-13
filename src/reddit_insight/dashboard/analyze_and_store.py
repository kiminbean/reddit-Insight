"""데이터 수집 및 분석 후 대시보드 데이터 저장소에 저장.

Usage:
    python -m reddit_insight.dashboard.analyze_and_store <subreddit> [--limit N]
"""

import argparse
import asyncio
from datetime import UTC, datetime

from reddit_insight.analysis.competitive import CompetitiveAnalyzer
from reddit_insight.analysis.demand_analyzer import DemandAnalyzer
from reddit_insight.analysis.keywords import UnifiedKeywordExtractor
from reddit_insight.analysis.trends import KeywordTrendAnalyzer
from reddit_insight.dashboard.data_store import AnalysisData, set_current_data
from reddit_insight.scraping.reddit_scraper import RedditScraper


async def collect_and_analyze(subreddit: str, limit: int = 100) -> AnalysisData:
    """서브레딧 데이터를 수집하고 분석한다."""
    print(f"=== r/{subreddit} 데이터 수집 및 분석 ===\n")

    # 1. 데이터 수집
    print("1. 데이터 수집 중...")
    async with RedditScraper() as scraper:
        posts = await scraper.get_hot(subreddit, limit=limit)
    print(f"   수집된 게시물: {len(posts)}개\n")

    # 2. 키워드 추출
    print("2. 키워드 분석 중...")
    extractor = UnifiedKeywordExtractor()
    keyword_result = extractor.extract_from_posts(posts, num_keywords=30)
    keywords_data = [
        {"keyword": kw.keyword, "score": kw.score, "frequency": kw.frequency}
        for kw in keyword_result.keywords
    ]
    print(f"   추출된 키워드: {len(keywords_data)}개\n")

    # 3. 트렌드 분석
    print("3. 트렌드 분석 중...")
    trend_analyzer = KeywordTrendAnalyzer()
    top_keywords = [kw.keyword for kw in keyword_result.keywords[:10]]
    trend_results = trend_analyzer.analyze_multiple_keywords(posts, top_keywords)
    trends_data = [
        {
            "keyword": tr.keyword,
            "direction": tr.metrics.direction.value,
            "change_rate": tr.metrics.change_rate,
            "volatility": tr.metrics.volatility,
            "data_points": len(tr.series.points),
        }
        for tr in trend_results
    ]
    print(f"   분석된 트렌드: {len(trends_data)}개\n")

    # 4. 수요 분석
    print("4. 수요 분석 중...")
    demand_analyzer = DemandAnalyzer()
    demand_report = demand_analyzer.analyze_posts(posts)
    demands_data = {
        "total_demands": demand_report.total_demands,
        "total_clusters": demand_report.total_clusters,
        "by_category": {k.value if hasattr(k, 'value') else str(k): v for k, v in demand_report.by_category.items()},
        "top_opportunities": [
            {
                "representative": opp.cluster.representative,
                "size": opp.cluster.frequency,
                "priority_score": opp.priority.total_score,
                "business_potential": opp.business_potential,
            }
            for opp in demand_report.top_opportunities[:10]
        ],
        "recommendations": demand_report.recommendations,
    }
    print(f"   발견된 수요: {demand_report.total_demands}개\n")

    # 5. 경쟁 분석
    print("5. 경쟁 분석 중...")
    competitive_analyzer = CompetitiveAnalyzer()
    competitive_report = competitive_analyzer.analyze_posts(posts)
    competition_data = {
        "entities_analyzed": competitive_report.entities_analyzed,
        "insights": [
            {
                "entity_name": insight.entity.name,
                "entity_type": insight.entity.entity_type.value,
                "mention_count": insight.entity.mentions,
                "sentiment_compound": insight.overall_sentiment.compound,
                "sentiment_positive": insight.overall_sentiment.positive_score,
                "sentiment_negative": insight.overall_sentiment.negative_score,
                "top_complaints": [c.text for c in insight.top_complaints[:3]],
            }
            for insight in competitive_report.insights[:20]
        ],
        "top_complaints": [
            {"text": c.text, "severity": c.severity}
            for c in competitive_report.top_complaints[:10]
        ],
        "popular_switches": [
            {"from": s[0], "to": s[1], "count": s[2]}
            for s in competitive_report.popular_switches[:10]
        ],
        "recommendations": competitive_report.recommendations,
    }
    print(f"   분석된 엔티티: {competitive_report.entities_analyzed}개\n")

    # 6. 인사이트 생성
    print("6. 인사이트 생성 중...")
    insights_data = []

    # 키워드 기반 인사이트
    for kw in keyword_result.keywords[:5]:
        insights_data.append(
            {
                "type": "trend",
                "title": f"'{kw.keyword}' 키워드 주목",
                "description": f"r/{subreddit}에서 '{kw.keyword}'가 높은 관심을 받고 있습니다.",
                "confidence": kw.score,
                "source": "keyword_analysis",
            }
        )

    # 수요 기반 인사이트
    for opp in demand_report.top_opportunities[:3]:
        insights_data.append(
            {
                "type": "opportunity",
                "title": f"비즈니스 기회: {opp.cluster.representative[:40]}...",
                "description": f"우선순위 점수 {opp.priority.total_score:.0f}점의 기회가 발견되었습니다.",
                "confidence": min(opp.priority.total_score / 100, 1.0),
                "source": "demand_analysis",
            }
        )

    # 경쟁 기반 인사이트
    for complaint in competitive_report.top_complaints[:3]:
        insights_data.append(
            {
                "type": "pain_point",
                "title": f"사용자 불만: {complaint.text[:40]}",
                "description": f"사용자들이 '{complaint.text}'에 대해 불만을 표시하고 있습니다.",
                "confidence": 0.7,
                "source": "competitive_analysis",
            }
        )

    print(f"   생성된 인사이트: {len(insights_data)}개\n")

    # 결과 저장
    data = AnalysisData(
        subreddit=subreddit,
        analyzed_at=datetime.now(UTC).isoformat(),
        post_count=len(posts),
        keywords=keywords_data,
        trends=trends_data,
        demands=demands_data,
        competition=competition_data,
        insights=insights_data,
    )

    set_current_data(data)
    print("=== 분석 완료 및 저장됨 ===")

    return data


def main() -> None:
    """메인 함수."""
    parser = argparse.ArgumentParser(description="서브레딧 분석 및 대시보드 데이터 저장")
    parser.add_argument("subreddit", help="분석할 서브레딧")
    parser.add_argument("--limit", type=int, default=100, help="수집할 게시물 수")

    args = parser.parse_args()

    asyncio.run(collect_and_analyze(args.subreddit, args.limit))


if __name__ == "__main__":
    main()
