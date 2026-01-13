"""자동 수집 스케줄러 모듈.

서브레딧 데이터를 주기적으로 수집하고 분석한다.
APScheduler를 사용하여 백그라운드에서 작업을 실행한다.
"""

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from reddit_insight.dashboard.database import (
    ScheduledTask,
    SessionLocal,
    init_db,
)

logger = logging.getLogger(__name__)

# 글로벌 스케줄러 인스턴스
_scheduler: AsyncIOScheduler | None = None


def get_scheduler() -> AsyncIOScheduler:
    """스케줄러 인스턴스를 반환한다."""
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler()
    return _scheduler


async def run_analysis_job(subreddit: str, limit: int = 100) -> dict[str, Any]:
    """분석 작업을 실행한다.

    Args:
        subreddit: 분석할 서브레딧
        limit: 수집할 게시물 수

    Returns:
        작업 결과 정보
    """
    logger.info(f"Starting scheduled analysis for r/{subreddit}")

    try:
        # 분석 모듈 임포트 (지연 임포트로 순환 참조 방지)
        from reddit_insight.analysis.competitive import CompetitiveAnalyzer
        from reddit_insight.analysis.demand_analyzer import DemandAnalyzer
        from reddit_insight.analysis.keywords import UnifiedKeywordExtractor
        from reddit_insight.analysis.trends import KeywordTrendAnalyzer
        from reddit_insight.dashboard.data_store import AnalysisData, set_current_data
        from reddit_insight.scraping.reddit_scraper import RedditScraper

        # 1. 데이터 수집
        async with RedditScraper() as scraper:
            posts = await scraper.get_hot(subreddit, limit=limit)

        if not posts:
            logger.warning(f"No posts found for r/{subreddit}")
            return {"status": "warning", "message": "No posts found"}

        # 2. 키워드 추출
        extractor = UnifiedKeywordExtractor()
        keyword_result = extractor.extract_from_posts(posts, num_keywords=30)
        keywords_data = [
            {"keyword": kw.keyword, "score": kw.score, "frequency": kw.frequency}
            for kw in keyword_result.keywords
        ]

        # 3. 트렌드 분석
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

        # 4. 수요 분석
        demand_analyzer = DemandAnalyzer()
        demand_report = demand_analyzer.analyze_posts(posts)
        demands_data = {
            "total_demands": demand_report.total_demands,
            "total_clusters": demand_report.total_clusters,
            "by_category": {
                k.value if hasattr(k, "value") else str(k): v
                for k, v in demand_report.by_category.items()
            },
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

        # 5. 경쟁 분석
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

        # 6. 인사이트 생성
        insights_data = []
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

        # 7. 결과 저장
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

        # 8. 스케줄 작업 업데이트
        update_task_last_run(subreddit)

        logger.info(
            f"Completed analysis for r/{subreddit}: "
            f"{len(posts)} posts, {len(keywords_data)} keywords"
        )

        return {
            "status": "success",
            "subreddit": subreddit,
            "post_count": len(posts),
            "keyword_count": len(keywords_data),
        }

    except Exception as e:
        logger.error(f"Error analyzing r/{subreddit}: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}


def update_task_last_run(subreddit: str) -> None:
    """작업의 마지막 실행 시간을 업데이트한다."""
    db = SessionLocal()
    try:
        task = (
            db.query(ScheduledTask)
            .filter(ScheduledTask.subreddit == subreddit, ScheduledTask.is_active == True)
            .first()
        )
        if task:
            task.last_run = datetime.now(UTC)
            db.commit()
    finally:
        db.close()


def add_scheduled_task(
    subreddit: str,
    schedule: str = "0 */6 * * *",  # 기본: 6시간마다
    post_limit: int = 100,
) -> int:
    """스케줄 작업을 추가한다.

    Args:
        subreddit: 수집할 서브레딧
        schedule: cron 표현식 (기본: 6시간마다)
        post_limit: 수집할 게시물 수

    Returns:
        작업 ID
    """
    init_db()

    db = SessionLocal()
    try:
        # 기존 작업이 있는지 확인
        existing = (
            db.query(ScheduledTask)
            .filter(ScheduledTask.subreddit == subreddit)
            .first()
        )

        if existing:
            # 기존 작업 업데이트
            existing.schedule = schedule
            existing.post_limit = post_limit
            existing.is_active = True
            db.commit()
            task_id = existing.id
        else:
            # 새 작업 생성
            task = ScheduledTask(
                subreddit=subreddit,
                schedule=schedule,
                post_limit=post_limit,
                is_active=True,
            )
            db.add(task)
            db.commit()
            db.refresh(task)
            task_id = task.id

        # 스케줄러에 작업 등록
        scheduler = get_scheduler()
        job_id = f"analyze_{subreddit}"

        # 기존 작업 제거
        if scheduler.get_job(job_id):
            scheduler.remove_job(job_id)

        # 새 작업 추가
        scheduler.add_job(
            run_analysis_job,
            CronTrigger.from_crontab(schedule),
            id=job_id,
            args=[subreddit, post_limit],
            replace_existing=True,
        )

        logger.info(f"Scheduled task added: r/{subreddit} with schedule '{schedule}'")
        return task_id

    finally:
        db.close()


def remove_scheduled_task(subreddit: str) -> bool:
    """스케줄 작업을 제거한다.

    Args:
        subreddit: 제거할 서브레딧

    Returns:
        성공 여부
    """
    db = SessionLocal()
    try:
        task = (
            db.query(ScheduledTask)
            .filter(ScheduledTask.subreddit == subreddit)
            .first()
        )

        if task:
            task.is_active = False
            db.commit()

            # 스케줄러에서 제거
            scheduler = get_scheduler()
            job_id = f"analyze_{subreddit}"
            if scheduler.get_job(job_id):
                scheduler.remove_job(job_id)

            logger.info(f"Scheduled task removed: r/{subreddit}")
            return True

        return False

    finally:
        db.close()


def get_scheduled_tasks() -> list[dict[str, Any]]:
    """등록된 스케줄 작업 목록을 반환한다."""
    init_db()

    db = SessionLocal()
    try:
        tasks = db.query(ScheduledTask).order_by(ScheduledTask.created_at.desc()).all()
        return [
            {
                "id": t.id,
                "subreddit": t.subreddit,
                "schedule": t.schedule,
                "post_limit": t.post_limit,
                "is_active": bool(t.is_active),
                "last_run": t.last_run.isoformat() if t.last_run else None,
                "next_run": t.next_run.isoformat() if t.next_run else None,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in tasks
        ]
    finally:
        db.close()


def start_scheduler() -> None:
    """스케줄러를 시작한다."""
    scheduler = get_scheduler()

    if scheduler.running:
        logger.info("Scheduler is already running")
        return

    # 데이터베이스에서 활성 작업 로드
    init_db()
    db = SessionLocal()
    try:
        active_tasks = (
            db.query(ScheduledTask)
            .filter(ScheduledTask.is_active == True)
            .all()
        )

        for task in active_tasks:
            job_id = f"analyze_{task.subreddit}"
            scheduler.add_job(
                run_analysis_job,
                CronTrigger.from_crontab(task.schedule),
                id=job_id,
                args=[task.subreddit, task.post_limit],
                replace_existing=True,
            )
            logger.info(f"Loaded scheduled task: r/{task.subreddit}")

    finally:
        db.close()

    scheduler.start()
    logger.info("Scheduler started")


def stop_scheduler() -> None:
    """스케줄러를 중지한다."""
    scheduler = get_scheduler()
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")


# ============================================================================
# CLI 유틸리티
# ============================================================================


def cli_list_tasks() -> None:
    """CLI에서 스케줄 작업 목록을 출력한다."""
    tasks = get_scheduled_tasks()
    if not tasks:
        print("No scheduled tasks found.")
        return

    print("\n=== Scheduled Tasks ===")
    print(f"{'ID':<5} {'Subreddit':<20} {'Schedule':<15} {'Active':<8} {'Last Run':<20}")
    print("-" * 75)
    for t in tasks:
        last_run = t["last_run"][:19] if t["last_run"] else "Never"
        print(
            f"{t['id']:<5} r/{t['subreddit'][:18]:<18} {t['schedule']:<15} "
            f"{'Yes' if t['is_active'] else 'No':<8} {last_run:<20}"
        )


def cli_add_task(subreddit: str, schedule: str = "0 */6 * * *", limit: int = 100) -> None:
    """CLI에서 스케줄 작업을 추가한다."""
    task_id = add_scheduled_task(subreddit, schedule, limit)
    print(f"\n=== Task Added ===")
    print(f"ID: {task_id}")
    print(f"Subreddit: r/{subreddit}")
    print(f"Schedule: {schedule}")
    print(f"Post Limit: {limit}")


def cli_run_now(subreddit: str, limit: int = 100) -> None:
    """CLI에서 즉시 분석을 실행한다."""
    print(f"\n=== Running Analysis for r/{subreddit} ===")
    result = asyncio.run(run_analysis_job(subreddit, limit))
    print(f"Result: {result}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python -m reddit_insight.dashboard.scheduler list")
        print("  python -m reddit_insight.dashboard.scheduler add <subreddit> [schedule] [limit]")
        print("  python -m reddit_insight.dashboard.scheduler remove <subreddit>")
        print("  python -m reddit_insight.dashboard.scheduler run <subreddit> [limit]")
        print("\nSchedule format: cron expression (e.g., '0 */6 * * *' for every 6 hours)")
        sys.exit(1)

    command = sys.argv[1]

    if command == "list":
        cli_list_tasks()

    elif command == "add":
        if len(sys.argv) < 3:
            print("Error: Subreddit required")
            sys.exit(1)
        subreddit = sys.argv[2]
        schedule = sys.argv[3] if len(sys.argv) > 3 else "0 */6 * * *"
        limit = int(sys.argv[4]) if len(sys.argv) > 4 else 100
        cli_add_task(subreddit, schedule, limit)

    elif command == "remove":
        if len(sys.argv) < 3:
            print("Error: Subreddit required")
            sys.exit(1)
        subreddit = sys.argv[2]
        if remove_scheduled_task(subreddit):
            print(f"Task for r/{subreddit} removed.")
        else:
            print(f"Task for r/{subreddit} not found.")

    elif command == "run":
        if len(sys.argv) < 3:
            print("Error: Subreddit required")
            sys.exit(1)
        subreddit = sys.argv[2]
        limit = int(sys.argv[3]) if len(sys.argv) > 3 else 100
        cli_run_now(subreddit, limit)

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
