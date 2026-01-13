# API Guide

Reddit Insight를 Python 코드에서 직접 사용하는 방법입니다.

## 목차

1. [설치 및 임포트](#설치-및-임포트)
2. [데이터 수집](#데이터-수집)
3. [키워드 분석](#키워드-분석)
4. [트렌드 분석](#트렌드-분석)
5. [수요 분석](#수요-분석)
6. [경쟁 분석](#경쟁-분석)
7. [인사이트 생성](#인사이트-생성)
8. [리포트 생성](#리포트-생성)
9. [데이터베이스 직접 접근](#데이터베이스-직접-접근)

---

## 설치 및 임포트

```python
# 패키지 설치
# pip install -e .

# 기본 임포트
from reddit_insight import Settings, get_settings
from reddit_insight.pipeline.collector import Collector, CollectorConfig
from reddit_insight.analysis.keywords import UnifiedKeywordExtractor
from reddit_insight.analysis.trends import KeywordTrendAnalyzer
from reddit_insight.analysis.demand_analyzer import DemandAnalyzer
from reddit_insight.analysis.competitive import CompetitiveAnalyzer
```

---

## 데이터 수집

### Collector 사용

```python
import asyncio
from reddit_insight.pipeline.collector import Collector, CollectorConfig

async def collect_subreddit_data():
    """서브레딧 데이터 수집 예제."""

    # 수집 설정
    config = CollectorConfig(
        subreddit="python",
        sort="hot",           # hot, new, top
        limit=100,            # 수집할 게시물 수
        include_comments=True,
        comment_limit=50,
        time_filter="week",   # top 정렬 시 사용
    )

    # 데이터 수집
    async with Collector() as collector:
        result = await collector.collect_subreddit(config)

    # 결과 확인
    print(f"새 게시물: {result.posts_result.new}")
    print(f"중복: {result.posts_result.duplicates}")
    print(f"소요 시간: {result.duration_seconds:.2f}초")

    return result

# 실행
result = asyncio.run(collect_subreddit_data())
```

### CollectorConfig 옵션

```python
from reddit_insight.pipeline.collector import CollectorConfig

config = CollectorConfig(
    subreddit="python",       # 서브레딧 이름 (필수)
    sort="hot",               # 정렬: hot, new, top
    limit=100,                # 게시물 수 제한
    include_comments=False,   # 댓글 수집 여부
    comment_limit=50,         # 게시물당 댓글 수
    time_filter="week",       # 기간: hour, day, week, month, year, all
)
```

---

## 키워드 분석

### UnifiedKeywordExtractor

TF-IDF와 YAKE를 결합한 키워드 추출기입니다.

```python
from reddit_insight.analysis.keywords import UnifiedKeywordExtractor

def extract_keywords(posts):
    """게시물에서 키워드 추출."""

    extractor = UnifiedKeywordExtractor()

    # 게시물 목록에서 키워드 추출
    result = extractor.extract_from_posts(
        posts,
        num_keywords=20,
    )

    # 키워드 출력
    for kw in result.keywords:
        print(f"{kw.keyword}: {kw.combined_score:.2f}")

    return result
```

### KeywordResult 구조

```python
@dataclass
class KeywordResult:
    keywords: list[RankedKeyword]  # 순위별 키워드
    extraction_method: str         # 추출 방법

@dataclass
class RankedKeyword:
    keyword: str          # 키워드 텍스트
    combined_score: float # 종합 점수
    tfidf_score: float    # TF-IDF 점수
    yake_score: float     # YAKE 점수
    frequency: int        # 출현 빈도
```

---

## 트렌드 분석

### KeywordTrendAnalyzer

시간에 따른 키워드 변화를 분석합니다.

```python
from reddit_insight.analysis.trends import KeywordTrendAnalyzer
from reddit_insight.analysis.time_series import TimeGranularity

def analyze_trends(posts):
    """키워드 트렌드 분석."""

    analyzer = KeywordTrendAnalyzer()

    # 자동으로 트렌딩 키워드 탐지
    trending = analyzer.find_trending_keywords(
        posts,
        num_keywords=10,
        granularity=TimeGranularity.DAY,
    )

    for result in trending:
        direction = result.metrics.direction.value
        change = result.metrics.change_rate
        print(f"{result.keyword}: {direction} ({change:+.1%})")

    return trending

# 특정 키워드 분석
def analyze_specific_keyword(posts, keyword):
    """특정 키워드의 트렌드 분석."""

    analyzer = KeywordTrendAnalyzer()

    result = analyzer.analyze_keyword_trend(
        posts,
        keyword=keyword,
        granularity=TimeGranularity.DAY,
    )

    print(f"키워드: {result.keyword}")
    print(f"방향: {result.metrics.direction.value}")
    print(f"변화율: {result.metrics.change_rate:+.1%}")
    print(f"기울기: {result.metrics.slope:.4f}")
    print(f"변동성: {result.metrics.volatility:.2f}")

    return result
```

### TrendMetrics 구조

```python
@dataclass
class TrendMetrics:
    direction: TrendDirection  # rising, falling, stable, volatile
    change_rate: float         # 변화율 (-1.0 ~ 1.0+)
    slope: float               # 선형 회귀 기울기
    volatility: float          # 변동성 (0 ~ 1)
    momentum: float            # 모멘텀
```

---

## 수요 분석

### DemandAnalyzer

사용자 요구사항 패턴을 탐지합니다.

```python
from reddit_insight.analysis.demand_analyzer import DemandAnalyzer

def analyze_demand(posts):
    """수요 분석."""

    analyzer = DemandAnalyzer()
    report = analyzer.analyze(posts)

    # 요약 정보
    print(f"총 수요 신호: {report.total_demands}")
    print(f"클러스터 수: {report.total_clusters}")

    # 카테고리별 분포
    print("\n카테고리별 분포:")
    for category, count in report.by_category.items():
        print(f"  {category.value}: {count}")

    # 상위 기회
    print("\n상위 기회:")
    for opp in report.top_opportunities[:5]:
        print(f"  - {opp.cluster.representative[:50]}...")
        print(f"    우선순위: {opp.priority.total_score:.1f}")

    return report
```

### DemandReport 구조

```python
@dataclass
class DemandReport:
    total_demands: int                      # 총 수요 신호 수
    total_clusters: int                     # 클러스터 수
    by_category: dict[DemandCategory, int]  # 카테고리별 분포
    top_opportunities: list[PrioritizedDemand]  # 상위 기회
```

### DemandCategory 종류

```python
class DemandCategory(Enum):
    FEATURE_REQUEST = "feature_request"     # 기능 요청
    PROBLEM_SOLUTION = "problem_solution"   # 문제 해결
    TOOL_RECOMMENDATION = "tool_recommendation"  # 도구 추천
    PRICING_VALUE = "pricing_value"         # 가격/가치
    COMPARISON = "comparison"               # 비교
    INTEGRATION = "integration"             # 통합
    LEARNING = "learning"                   # 학습
    OTHER = "other"                         # 기타
```

---

## 경쟁 분석

### CompetitiveAnalyzer

제품/서비스 언급과 감성을 분석합니다.

```python
from reddit_insight.analysis.competitive import CompetitiveAnalyzer

def analyze_competition(posts):
    """경쟁 분석."""

    analyzer = CompetitiveAnalyzer()
    report = analyzer.analyze(posts)

    # 요약 정보
    print(f"분석된 엔티티: {report.entities_analyzed}")

    # 주요 인사이트
    print("\n엔티티별 인사이트:")
    for insight in report.insights[:5]:
        sentiment = insight.overall_sentiment.compound
        sentiment_label = "긍정" if sentiment > 0.1 else ("부정" if sentiment < -0.1 else "중립")
        print(f"  {insight.entity.name}: {sentiment_label} ({sentiment:+.2f})")

    # 주요 불만
    print("\n주요 불만:")
    for complaint in report.top_complaints[:5]:
        print(f"  - [{complaint.complaint_type.value}] {complaint.context[:50]}...")

    # 대체 패턴
    print("\n인기 대체 패턴:")
    for from_name, to_name, count in report.popular_switches[:5]:
        print(f"  {from_name} -> {to_name} ({count}회)")

    return report
```

### CompetitiveReport 구조

```python
@dataclass
class CompetitiveReport:
    entities_analyzed: int                # 분석된 엔티티 수
    insights: list[EntityInsight]         # 엔티티별 인사이트
    top_complaints: list[Complaint]       # 주요 불만
    popular_switches: list[tuple]         # 대체 패턴 (from, to, count)
```

---

## 인사이트 생성

### InsightGenerator

분석 결과를 비즈니스 인사이트로 변환합니다.

```python
from reddit_insight.insights.feasibility import InsightGenerator

def generate_insights(demand_report, competitive_report):
    """인사이트 생성."""

    generator = InsightGenerator()

    report = generator.generate_insights(
        demand_report=demand_report,
        competitive_report=competitive_report,
    )

    # 요약
    print(f"총 인사이트: {report.total_insights}")
    print(f"총 기회: {report.total_opportunities}")

    # 권고사항
    print("\n권고사항:")
    for rec in report.recommendations[:5]:
        print(f"\n  [{rec.final_rank}] {rec.insight.title}")
        print(f"      점수: {rec.combined_score:.1f}")
        print(f"      등급: {rec.business_score.grade}")
        print(f"      실행 항목:")
        for action in rec.action_items[:3]:
            print(f"        - {action}")

    return report
```

---

## 리포트 생성

### ReportGenerator

분석 결과를 마크다운 리포트로 생성합니다.

```python
from pathlib import Path
from reddit_insight.reports.generator import (
    ReportGenerator,
    ReportConfig,
    ReportDataCollector,
    TrendReportData,
)

def generate_reports(
    trend_data,
    demand_report,
    competitive_report,
    insight_report,
    output_dir: str = "./reports",
):
    """리포트 생성."""

    # 설정
    config = ReportConfig(
        title="Reddit Insight Report",
        author="Reddit Insight",
        max_items_per_section=10,
    )

    # 데이터 수집
    collector = ReportDataCollector(
        trend_report=trend_data,
        demand_report=demand_report,
        competitive_report=competitive_report,
        insight_report=insight_report,
        metadata={"subreddit": "python"},
    )

    # 생성기 초기화
    generator = ReportGenerator(config=config)

    # 모든 리포트 내보내기
    output_path = Path(output_dir)
    exported_files = generator.export_all(collector, output_path)

    print("생성된 파일:")
    for file_path in exported_files:
        print(f"  - {file_path}")

    return exported_files
```

### TrendReportData 생성

```python
def create_trend_data(keyword_result, trend_results):
    """트렌드 리포트 데이터 생성."""

    return TrendReportData(
        title="Trend Report",
        summary="Keyword trend analysis",
        top_keywords=[
            {"keyword": kw.keyword, "score": kw.combined_score}
            for kw in keyword_result.keywords[:10]
        ],
        rising_keywords=[
            {"keyword": tr.keyword, "change_rate": tr.metrics.change_rate}
            for tr in trend_results
            if tr.metrics.direction.value == "rising"
        ][:5],
    )
```

---

## 데이터베이스 직접 접근

### Database 클래스 사용

```python
import asyncio
from sqlalchemy import select
from reddit_insight.storage.database import Database
from reddit_insight.storage.models import PostModel, SubredditModel

async def query_posts(subreddit_name: str, limit: int = 100):
    """데이터베이스에서 게시물 조회."""

    async with Database() as db:
        async with db.session() as session:
            # 서브레딧 조회
            result = await session.execute(
                select(SubredditModel).where(
                    SubredditModel.name == subreddit_name.lower()
                )
            )
            subreddit = result.scalar_one_or_none()

            if not subreddit:
                return []

            # 게시물 조회
            posts_result = await session.execute(
                select(PostModel)
                .where(PostModel.subreddit_id == subreddit.id)
                .order_by(PostModel.created_utc.desc())
                .limit(limit)
            )
            post_models = posts_result.scalars().all()

            # 도메인 객체로 변환
            return [pm.to_domain() for pm in post_models]

# 실행
posts = asyncio.run(query_posts("python", 100))
```

### Repository 패턴 사용

```python
from reddit_insight.storage.repository import Repository

async def use_repository():
    """Repository를 통한 데이터 접근."""

    async with Database() as db:
        repo = Repository(db)

        # 서브레딧별 게시물 수 조회
        stats = await repo.get_subreddit_stats()
        for name, count in stats:
            print(f"r/{name}: {count} posts")
```

---

## 전체 파이프라인 예제

```python
import asyncio
from reddit_insight.pipeline.collector import Collector, CollectorConfig
from reddit_insight.analysis.keywords import UnifiedKeywordExtractor
from reddit_insight.analysis.trends import KeywordTrendAnalyzer
from reddit_insight.analysis.demand_analyzer import DemandAnalyzer
from reddit_insight.analysis.competitive import CompetitiveAnalyzer
from reddit_insight.insights.feasibility import InsightGenerator

async def full_analysis_pipeline(subreddit: str):
    """전체 분석 파이프라인."""

    # 1. 데이터 수집
    print(f"1. r/{subreddit} 데이터 수집 중...")
    config = CollectorConfig(subreddit=subreddit, limit=200)
    async with Collector() as collector:
        result = await collector.collect_subreddit(config)
    print(f"   새 게시물: {result.posts_result.new}")

    # 2. 데이터베이스에서 게시물 로드
    print("2. 게시물 로드 중...")
    from reddit_insight.storage.database import Database
    from reddit_insight.storage.models import PostModel, SubredditModel
    from sqlalchemy import select

    posts = []
    async with Database() as db:
        async with db.session() as session:
            sub_result = await session.execute(
                select(SubredditModel).where(
                    SubredditModel.name == subreddit.lower()
                )
            )
            sub = sub_result.scalar_one()

            posts_result = await session.execute(
                select(PostModel)
                .where(PostModel.subreddit_id == sub.id)
                .limit(500)
            )
            posts = [pm.to_domain() for pm in posts_result.scalars().all()]
    print(f"   로드된 게시물: {len(posts)}")

    # 3. 키워드 추출
    print("3. 키워드 추출 중...")
    extractor = UnifiedKeywordExtractor()
    keyword_result = extractor.extract_from_posts(posts, num_keywords=20)
    print(f"   추출된 키워드: {len(keyword_result.keywords)}")

    # 4. 트렌드 분석
    print("4. 트렌드 분석 중...")
    trend_analyzer = KeywordTrendAnalyzer()
    keywords = [kw.keyword for kw in keyword_result.keywords[:10]]
    trend_results = trend_analyzer.analyze_multiple_keywords(posts, keywords)
    rising = [r for r in trend_results if r.metrics.direction.value == "rising"]
    print(f"   상승 키워드: {len(rising)}")

    # 5. 수요 분석
    print("5. 수요 분석 중...")
    demand_analyzer = DemandAnalyzer()
    demand_report = demand_analyzer.analyze(posts)
    print(f"   수요 신호: {demand_report.total_demands}")

    # 6. 경쟁 분석
    print("6. 경쟁 분석 중...")
    competitive_analyzer = CompetitiveAnalyzer()
    competitive_report = competitive_analyzer.analyze(posts)
    print(f"   분석된 엔티티: {competitive_report.entities_analyzed}")

    # 7. 인사이트 생성
    print("7. 인사이트 생성 중...")
    insight_generator = InsightGenerator()
    insight_report = insight_generator.generate_insights(
        demand_report=demand_report,
        competitive_report=competitive_report,
    )
    print(f"   생성된 인사이트: {insight_report.total_insights}")

    print("\n완료!")
    return {
        "keywords": keyword_result,
        "trends": trend_results,
        "demand": demand_report,
        "competitive": competitive_report,
        "insights": insight_report,
    }

# 실행
results = asyncio.run(full_analysis_pipeline("python"))
```
