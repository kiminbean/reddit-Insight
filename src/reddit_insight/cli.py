"""Reddit Insight CLI.

데이터 수집, 분석, 리포트 생성, 대시보드를 위한 명령줄 인터페이스.
argparse와 rich를 사용하여 사용자 친화적인 CLI를 제공한다.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path
from typing import Sequence

from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.table import Table

from reddit_insight.pipeline.collector import Collector, CollectorConfig

console = Console()

# =============================================================================
# LOGGING SETUP
# =============================================================================


def setup_logging(debug: bool = False) -> None:
    """로깅 설정.

    Args:
        debug: 디버그 모드 여부
    """
    level = logging.DEBUG if debug else logging.INFO

    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[
            RichHandler(
                console=console,
                show_path=debug,
                rich_tracebacks=True,
            )
        ],
    )

    # 외부 라이브러리 로그 레벨 조정
    if not debug:
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)
        logging.getLogger("sqlalchemy").setLevel(logging.WARNING)


# =============================================================================
# ERROR HANDLING
# =============================================================================


def print_error(message: str, hint: str | None = None) -> None:
    """친화적인 에러 메시지 출력.

    Args:
        message: 에러 메시지
        hint: 복구 힌트 (선택)
    """
    console.print(f"\n[bold red]Error:[/bold red] {message}")
    if hint:
        console.print(f"[yellow]Hint:[/yellow] {hint}")


def print_success(message: str) -> None:
    """성공 메시지 출력.

    Args:
        message: 성공 메시지
    """
    console.print(f"\n[bold green]Success:[/bold green] {message}")


def print_warning(message: str) -> None:
    """경고 메시지 출력.

    Args:
        message: 경고 메시지
    """
    console.print(f"\n[bold yellow]Warning:[/bold yellow] {message}")


# =============================================================================
# PROGRESS BARS
# =============================================================================


def create_progress() -> Progress:
    """표준 진행률 표시 바 생성."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=console,
    )


def create_simple_progress() -> Progress:
    """간단한 진행률 표시 바 생성."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        console=console,
    )


# =============================================================================
# COLLECT COMMANDS
# =============================================================================


async def cmd_collect(args: argparse.Namespace) -> int:
    """단일 서브레딧 수집.

    Args:
        args: 명령줄 인자

    Returns:
        종료 코드 (0: 성공, 1: 실패)
    """
    config = CollectorConfig(
        subreddit=args.subreddit,
        sort=args.sort,
        limit=args.limit,
        include_comments=args.comments,
        comment_limit=args.comment_limit,
        time_filter=args.time_filter,
    )

    console.print(
        Panel(
            f"[bold blue]r/{config.subreddit}[/bold blue] 서브레딧 수집\n"
            f"정렬: {config.sort} | 게시물 수: {config.limit} | "
            f"댓글 수집: {'예' if config.include_comments else '아니오'}",
            title="[bold]데이터 수집[/bold]",
            border_style="blue",
        )
    )

    with create_progress() as progress:
        task = progress.add_task(f"r/{config.subreddit} 수집 중...", total=None)

        async with Collector() as collector:
            result = await collector.collect_subreddit(config)

        progress.update(task, completed=100, total=100)

    # 결과 테이블 출력
    table = Table(title=f"r/{config.subreddit} 수집 결과", show_header=True)
    table.add_column("항목", style="cyan")
    table.add_column("값", style="green")

    table.add_row("새 게시물", str(result.posts_result.new))
    table.add_row("중복 게시물", str(result.posts_result.duplicates))
    table.add_row("필터링됨", str(result.posts_result.filtered))

    if result.comments_result:
        table.add_row("새 댓글", str(result.comments_result.new))
        table.add_row("중복 댓글", str(result.comments_result.duplicates))

    table.add_row("소요 시간", f"{result.duration_seconds:.2f}초")
    table.add_row("수집 시각", result.collected_at.strftime("%Y-%m-%d %H:%M:%S"))

    console.print(table)

    if result.error:
        print_error(
            result.error,
            hint="네트워크 연결을 확인하거나 잠시 후 다시 시도하세요.",
        )
        return 1

    print_success("데이터 수집이 완료되었습니다!")
    return 0


def read_subreddit_list(file_path: str | None) -> list[str]:
    """서브레딧 목록 파일 또는 stdin에서 읽기.

    Args:
        file_path: 파일 경로. None이면 stdin에서 읽음

    Returns:
        서브레딧 이름 목록
    """
    lines: list[str] = []

    if file_path:
        path = Path(file_path)
        if not path.exists():
            print_error(
                f"파일을 찾을 수 없습니다: {file_path}",
                hint="파일 경로가 올바른지 확인하세요.",
            )
            return []
        lines = path.read_text().strip().split("\n")
    else:
        # stdin에서 읽기
        if sys.stdin.isatty():
            console.print(
                "[yellow]서브레딧 목록을 입력하세요 (한 줄에 하나, Ctrl+D로 종료):[/yellow]"
            )
        lines = sys.stdin.read().strip().split("\n")

    # 빈 줄과 주석 제거
    subreddits = []
    for line in lines:
        line = line.strip()
        if line and not line.startswith("#"):
            # 앞에 r/ 있으면 제거
            if line.lower().startswith("r/"):
                line = line[2:]
            subreddits.append(line)

    return subreddits


async def cmd_collect_list(args: argparse.Namespace) -> int:
    """서브레딧 목록 수집.

    Args:
        args: 명령줄 인자

    Returns:
        종료 코드 (0: 성공, 1: 실패)
    """
    subreddits = read_subreddit_list(args.file)

    if not subreddits:
        print_error(
            "수집할 서브레딧이 없습니다.",
            hint="파일에 서브레딧 이름을 한 줄에 하나씩 입력하세요.",
        )
        return 1

    console.print(
        Panel(
            f"[bold]{len(subreddits)}개[/bold] 서브레딧 수집\n"
            f"정렬: {args.sort} | 게시물 수: {args.limit}",
            title="[bold]일괄 수집[/bold]",
            border_style="blue",
        )
    )

    for subreddit in subreddits:
        console.print(f"  - r/{subreddit}")

    console.print()

    results = []

    with create_simple_progress() as progress:
        task = progress.add_task("수집 중...", total=len(subreddits))

        async with Collector() as collector:
            for subreddit in subreddits:
                progress.update(task, description=f"r/{subreddit} 수집 중...")

                config = CollectorConfig(
                    subreddit=subreddit,
                    sort=args.sort,
                    limit=args.limit,
                    include_comments=args.comments,
                    comment_limit=args.comment_limit,
                    time_filter=args.time_filter,
                )
                result = await collector.collect_subreddit(config)
                results.append(result)

                progress.advance(task)

    # 결과 테이블 출력
    table = Table(title="수집 결과 요약", show_header=True)
    table.add_column("서브레딧", style="cyan")
    table.add_column("새 게시물", style="green", justify="right")
    table.add_column("중복", style="yellow", justify="right")
    table.add_column("소요 시간", justify="right")
    table.add_column("상태", justify="center")

    for result in results:
        status = "[green]성공[/green]" if result.success else "[red]실패[/red]"
        table.add_row(
            f"r/{result.subreddit}",
            str(result.posts_result.new),
            str(result.posts_result.duplicates),
            f"{result.duration_seconds:.2f}초",
            status,
        )

    console.print(table)

    # 통계
    total_new = sum(r.posts_result.new for r in results)
    total_time = sum(r.duration_seconds for r in results)
    success_count = sum(1 for r in results if r.success)

    console.print(
        f"\n[bold]총 {success_count}/{len(results)} 성공, "
        f"새 게시물 {total_new}개, "
        f"총 {total_time:.2f}초[/bold]"
    )

    if success_count == len(results):
        print_success("모든 서브레딧 수집이 완료되었습니다!")
        return 0
    else:
        print_warning("일부 서브레딧 수집에 실패했습니다.")
        return 1


# =============================================================================
# ANALYZE COMMANDS
# =============================================================================


async def cmd_analyze_full(args: argparse.Namespace) -> int:
    """전체 분석 파이프라인 실행.

    Args:
        args: 명령줄 인자

    Returns:
        종료 코드 (0: 성공, 1: 실패)
    """
    from sqlalchemy import select

    from reddit_insight.analysis.competitive import CompetitiveAnalyzer
    from reddit_insight.analysis.demand_analyzer import DemandAnalyzer
    from reddit_insight.analysis.keywords import UnifiedKeywordExtractor
    from reddit_insight.analysis.trends import KeywordTrendAnalyzer
    from reddit_insight.reddit.models import Post
    from reddit_insight.storage.database import Database
    from reddit_insight.storage.models import PostModel, SubredditModel

    console.print(
        Panel(
            f"[bold blue]r/{args.subreddit}[/bold blue] 전체 분석 실행\n"
            "트렌드 분석, 수요 분석, 경쟁 분석을 순차적으로 수행합니다.",
            title="[bold]전체 분석[/bold]",
            border_style="green",
        )
    )

    # 데이터베이스에서 게시물 가져오기
    posts: list[Post] = []

    with create_progress() as progress:
        task = progress.add_task("데이터베이스에서 게시물 로드 중...", total=None)

        async with Database() as db:
            async with db.session() as session:
                # 서브레딧 ID 조회
                subreddit_result = await session.execute(
                    select(SubredditModel).where(
                        SubredditModel.name == args.subreddit.lower()
                    )
                )
                subreddit = subreddit_result.scalar_one_or_none()

                if not subreddit:
                    print_error(
                        f"서브레딧 r/{args.subreddit}를 찾을 수 없습니다.",
                        hint="먼저 'reddit-insight collect' 명령으로 데이터를 수집하세요.",
                    )
                    return 1

                # 게시물 조회
                posts_result = await session.execute(
                    select(PostModel)
                    .where(PostModel.subreddit_id == subreddit.id)
                    .order_by(PostModel.created_utc.desc())
                    .limit(args.limit)
                )
                post_models = posts_result.scalars().all()

                # 모델을 Post 객체로 변환
                for pm in post_models:
                    posts.append(pm.to_domain())

        progress.update(task, completed=100, total=100)

    if not posts:
        print_error(
            f"r/{args.subreddit}에서 분석할 게시물이 없습니다.",
            hint="먼저 데이터를 수집하세요: reddit-insight collect " + args.subreddit,
        )
        return 1

    console.print(f"\n[green]{len(posts)}개[/green] 게시물을 분석합니다.\n")

    # 분석 실행
    results = {}

    with create_progress() as progress:
        # 1. 키워드 추출
        task1 = progress.add_task("키워드 추출 중...", total=100)
        extractor = UnifiedKeywordExtractor()
        keyword_result = extractor.extract_from_posts(posts, num_keywords=20)
        results["keywords"] = keyword_result
        progress.update(task1, completed=100)

        # 2. 트렌드 분석
        task2 = progress.add_task("트렌드 분석 중...", total=100)
        trend_analyzer = KeywordTrendAnalyzer()
        keywords = [kw.keyword for kw in keyword_result.keywords[:10]]
        trend_results = trend_analyzer.analyze_multiple_keywords(posts, keywords)
        results["trends"] = trend_results
        progress.update(task2, completed=100)

        # 3. 수요 분석
        task3 = progress.add_task("수요 분석 중...", total=100)
        demand_analyzer = DemandAnalyzer()
        demand_report = demand_analyzer.analyze(posts)
        results["demand"] = demand_report
        progress.update(task3, completed=100)

        # 4. 경쟁 분석
        task4 = progress.add_task("경쟁 분석 중...", total=100)
        competitive_analyzer = CompetitiveAnalyzer()
        competitive_report = competitive_analyzer.analyze(posts)
        results["competitive"] = competitive_report
        progress.update(task4, completed=100)

    # 결과 출력
    console.print("\n")

    # 키워드 테이블
    table = Table(title="상위 키워드", show_header=True)
    table.add_column("순위", style="cyan", justify="right")
    table.add_column("키워드", style="green")
    table.add_column("점수", justify="right")

    for i, kw in enumerate(keyword_result.keywords[:10], 1):
        table.add_row(str(i), kw.keyword, f"{kw.combined_score:.2f}")

    console.print(table)
    console.print()

    # 트렌드 테이블
    table = Table(title="키워드 트렌드", show_header=True)
    table.add_column("키워드", style="cyan")
    table.add_column("방향", justify="center")
    table.add_column("변화율", justify="right")

    for tr in trend_results[:10]:
        direction_emoji = {
            "rising": "[green]상승[/green]",
            "falling": "[red]하락[/red]",
            "stable": "[yellow]안정[/yellow]",
            "volatile": "[magenta]변동[/magenta]",
        }.get(tr.metrics.direction.value, "-")
        table.add_row(
            tr.keyword,
            direction_emoji,
            f"{tr.metrics.change_rate:+.1%}",
        )

    console.print(table)
    console.print()

    # 수요 요약
    console.print(
        Panel(
            f"총 수요 신호: [bold]{demand_report.total_demands}[/bold]개\n"
            f"클러스터 수: [bold]{demand_report.total_clusters}[/bold]개\n"
            f"상위 기회: [bold]{len(demand_report.top_opportunities)}[/bold]개",
            title="[bold]수요 분석 요약[/bold]",
            border_style="yellow",
        )
    )

    # 경쟁 분석 요약
    console.print(
        Panel(
            f"분석된 엔티티: [bold]{competitive_report.entities_analyzed}[/bold]개\n"
            f"주요 불만: [bold]{len(competitive_report.top_complaints)}[/bold]개\n"
            f"대체 패턴: [bold]{len(competitive_report.popular_switches)}[/bold]개",
            title="[bold]경쟁 분석 요약[/bold]",
            border_style="magenta",
        )
    )

    print_success(f"r/{args.subreddit} 전체 분석이 완료되었습니다!")
    return 0


# =============================================================================
# REPORT COMMANDS
# =============================================================================


async def cmd_report_generate(args: argparse.Namespace) -> int:
    """마크다운 리포트 생성.

    Args:
        args: 명령줄 인자

    Returns:
        종료 코드 (0: 성공, 1: 실패)
    """
    from sqlalchemy import select

    from reddit_insight.analysis.competitive import CompetitiveAnalyzer
    from reddit_insight.analysis.demand_analyzer import DemandAnalyzer
    from reddit_insight.analysis.keywords import UnifiedKeywordExtractor
    from reddit_insight.analysis.trends import KeywordTrendAnalyzer
    from reddit_insight.insights.feasibility import InsightGenerator
    from reddit_insight.reddit.models import Post
    from reddit_insight.reports.generator import (
        ReportConfig,
        ReportDataCollector,
        ReportGenerator,
        TrendReportData,
    )
    from reddit_insight.storage.database import Database
    from reddit_insight.storage.models import PostModel, SubredditModel

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    console.print(
        Panel(
            f"리포트 출력 디렉토리: [bold]{output_dir}[/bold]\n"
            f"서브레딧: [bold blue]r/{args.subreddit}[/bold blue]",
            title="[bold]리포트 생성[/bold]",
            border_style="cyan",
        )
    )

    # 데이터베이스에서 게시물 가져오기
    posts: list[Post] = []

    with create_progress() as progress:
        task = progress.add_task("데이터 로드 중...", total=None)

        async with Database() as db:
            async with db.session() as session:
                subreddit_result = await session.execute(
                    select(SubredditModel).where(
                        SubredditModel.name == args.subreddit.lower()
                    )
                )
                subreddit = subreddit_result.scalar_one_or_none()

                if not subreddit:
                    print_error(
                        f"서브레딧 r/{args.subreddit}를 찾을 수 없습니다.",
                        hint="먼저 데이터를 수집하세요.",
                    )
                    return 1

                posts_result = await session.execute(
                    select(PostModel)
                    .where(PostModel.subreddit_id == subreddit.id)
                    .order_by(PostModel.created_utc.desc())
                    .limit(args.limit)
                )
                post_models = posts_result.scalars().all()

                for pm in post_models:
                    posts.append(pm.to_domain())

        progress.update(task, completed=100, total=100)

    if not posts:
        print_error("분석할 게시물이 없습니다.")
        return 1

    # 분석 실행 및 리포트 데이터 수집
    with create_progress() as progress:
        # 키워드 및 트렌드
        task1 = progress.add_task("키워드/트렌드 분석 중...", total=100)
        extractor = UnifiedKeywordExtractor()
        keyword_result = extractor.extract_from_posts(posts, num_keywords=20)

        trend_analyzer = KeywordTrendAnalyzer()
        keywords = [kw.keyword for kw in keyword_result.keywords[:10]]
        trend_results = trend_analyzer.analyze_multiple_keywords(posts, keywords)

        # TrendReportData 생성
        trend_data = TrendReportData(
            title=f"r/{args.subreddit} Trend Report",
            summary=f"Analyzed {len(posts)} posts from r/{args.subreddit}",
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
        progress.update(task1, completed=100)

        # 수요 분석
        task2 = progress.add_task("수요 분석 중...", total=100)
        demand_analyzer = DemandAnalyzer()
        demand_report = demand_analyzer.analyze(posts)
        progress.update(task2, completed=100)

        # 경쟁 분석
        task3 = progress.add_task("경쟁 분석 중...", total=100)
        competitive_analyzer = CompetitiveAnalyzer()
        competitive_report = competitive_analyzer.analyze(posts)
        progress.update(task3, completed=100)

        # 인사이트 생성
        task4 = progress.add_task("인사이트 생성 중...", total=100)
        insight_generator = InsightGenerator()
        insight_report = insight_generator.generate_insights(
            demand_report=demand_report,
            competitive_report=competitive_report,
        )
        progress.update(task4, completed=100)

        # 리포트 생성
        task5 = progress.add_task("리포트 생성 중...", total=100)

        collector = ReportDataCollector(
            trend_report=trend_data,
            demand_report=demand_report,
            competitive_report=competitive_report,
            insight_report=insight_report,
            metadata={"subreddit": args.subreddit, "post_count": len(posts)},
        )

        config = ReportConfig(
            title=f"Reddit Insight Report - r/{args.subreddit}",
            author="Reddit Insight",
        )
        generator = ReportGenerator(config=config)
        exported_files = generator.export_all(collector, output_dir)
        progress.update(task5, completed=100)

    # 결과 출력
    table = Table(title="생성된 리포트", show_header=True)
    table.add_column("파일", style="cyan")
    table.add_column("크기", justify="right")

    for file_path in exported_files:
        size = file_path.stat().st_size
        size_str = f"{size:,} bytes"
        if size > 1024:
            size_str = f"{size / 1024:.1f} KB"
        table.add_row(file_path.name, size_str)

    console.print(table)

    print_success(f"리포트가 {output_dir}에 생성되었습니다!")
    return 0


# =============================================================================
# DASHBOARD COMMANDS
# =============================================================================


def cmd_dashboard_start(args: argparse.Namespace) -> int:
    """대시보드 서버 시작.

    Args:
        args: 명령줄 인자

    Returns:
        종료 코드 (0: 성공, 1: 실패)
    """
    try:
        import uvicorn
    except ImportError:
        print_error(
            "uvicorn이 설치되어 있지 않습니다.",
            hint="pip install uvicorn 명령으로 설치하세요.",
        )
        return 1

    console.print(
        Panel(
            f"대시보드 서버 시작\n"
            f"주소: [bold]http://{args.host}:{args.port}[/bold]\n"
            f"API 문서: [bold]http://{args.host}:{args.port}/api/docs[/bold]",
            title="[bold]Reddit Insight Dashboard[/bold]",
            border_style="green",
        )
    )
    console.print("\n[yellow]서버를 종료하려면 Ctrl+C를 누르세요.[/yellow]\n")

    uvicorn.run(
        "reddit_insight.dashboard.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info" if not args.debug else "debug",
    )

    return 0


# =============================================================================
# STATUS COMMAND
# =============================================================================


async def cmd_status(args: argparse.Namespace) -> int:
    """데이터베이스 상태 조회.

    Args:
        args: 명령줄 인자

    Returns:
        종료 코드
    """
    from sqlalchemy import func, select

    from reddit_insight.storage.database import Database
    from reddit_insight.storage.models import CommentModel, PostModel, SubredditModel

    console.print(
        Panel(
            "데이터베이스에 저장된 데이터 통계를 표시합니다.",
            title="[bold]데이터베이스 상태[/bold]",
            border_style="blue",
        )
    )

    async with Database() as db:
        async with db.session() as session:
            # 서브레딧 수
            subreddit_count = await session.scalar(
                select(func.count()).select_from(SubredditModel)
            )

            # 게시물 수
            post_count = await session.scalar(
                select(func.count()).select_from(PostModel)
            )

            # 댓글 수
            comment_count = await session.scalar(
                select(func.count()).select_from(CommentModel)
            )

            # 서브레딧별 게시물 수 (상위 10개)
            stmt = (
                select(
                    SubredditModel.name,
                    func.count(PostModel.id).label("post_count"),
                )
                .join(PostModel, SubredditModel.id == PostModel.subreddit_id)
                .group_by(SubredditModel.id)
                .order_by(func.count(PostModel.id).desc())
                .limit(10)
            )
            subreddit_stats = await session.execute(stmt)
            subreddit_list = subreddit_stats.fetchall()

    # 전체 통계 테이블
    table = Table(title="전체 통계", show_header=True)
    table.add_column("항목", style="cyan")
    table.add_column("개수", style="green", justify="right")

    table.add_row("서브레딧", str(subreddit_count))
    table.add_row("게시물", str(post_count))
    table.add_row("댓글", str(comment_count))

    console.print(table)

    # 서브레딧별 통계 테이블
    if subreddit_list:
        console.print()
        stats_table = Table(title="서브레딧별 게시물 (상위 10개)", show_header=True)
        stats_table.add_column("서브레딧", style="cyan")
        stats_table.add_column("게시물 수", style="green", justify="right")

        for name, count in subreddit_list:
            stats_table.add_row(f"r/{name}", str(count))

        console.print(stats_table)

    return 0


# =============================================================================
# ARGUMENT PARSER
# =============================================================================


def create_parser() -> argparse.ArgumentParser:
    """인자 파서 생성."""
    parser = argparse.ArgumentParser(
        prog="reddit-insight",
        description="Reddit 데이터 수집 및 분석 도구",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # 단일 서브레딧 수집
  reddit-insight collect python -l 100

  # 여러 서브레딧 수집
  reddit-insight collect-list subreddits.txt

  # 전체 분석 실행
  reddit-insight analyze full python

  # 리포트 생성
  reddit-insight report generate ./reports -s python

  # 대시보드 시작
  reddit-insight dashboard start

  # 데이터베이스 상태 확인
  reddit-insight status
""",
    )
    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="디버그 모드 활성화",
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version="%(prog)s 0.1.0",
    )

    subparsers = parser.add_subparsers(dest="command", help="사용 가능한 명령")

    # =========================================================================
    # collect 명령 그룹
    # =========================================================================

    collect_parser = subparsers.add_parser(
        "collect",
        help="단일 서브레딧 수집",
        description="지정된 서브레딧에서 게시물을 수집합니다.",
    )
    collect_parser.add_argument(
        "subreddit",
        help="수집할 서브레딧 이름 (예: python)",
    )
    collect_parser.add_argument(
        "-s",
        "--sort",
        choices=["hot", "new", "top"],
        default="hot",
        help="정렬 방식 (기본: hot)",
    )
    collect_parser.add_argument(
        "-l",
        "--limit",
        type=int,
        default=100,
        help="수집할 게시물 수 (기본: 100)",
    )
    collect_parser.add_argument(
        "-c",
        "--comments",
        action="store_true",
        help="댓글도 수집",
    )
    collect_parser.add_argument(
        "--comment-limit",
        type=int,
        default=50,
        help="게시물당 수집할 댓글 수 (기본: 50)",
    )
    collect_parser.add_argument(
        "-t",
        "--time-filter",
        choices=["hour", "day", "week", "month", "year", "all"],
        default="week",
        help="top 정렬 시 기간 필터 (기본: week)",
    )

    # collect-list 명령
    collect_list_parser = subparsers.add_parser(
        "collect-list",
        help="서브레딧 목록 수집",
        description="파일 또는 stdin에서 서브레딧 목록을 읽어 수집합니다.",
    )
    collect_list_parser.add_argument(
        "file",
        nargs="?",
        default=None,
        help="서브레딧 목록 파일 (생략 시 stdin)",
    )
    collect_list_parser.add_argument(
        "-s",
        "--sort",
        choices=["hot", "new", "top"],
        default="hot",
        help="정렬 방식 (기본: hot)",
    )
    collect_list_parser.add_argument(
        "-l",
        "--limit",
        type=int,
        default=100,
        help="수집할 게시물 수 (기본: 100)",
    )
    collect_list_parser.add_argument(
        "-c",
        "--comments",
        action="store_true",
        help="댓글도 수집",
    )
    collect_list_parser.add_argument(
        "--comment-limit",
        type=int,
        default=50,
        help="게시물당 수집할 댓글 수 (기본: 50)",
    )
    collect_list_parser.add_argument(
        "-t",
        "--time-filter",
        choices=["hour", "day", "week", "month", "year", "all"],
        default="week",
        help="top 정렬 시 기간 필터 (기본: week)",
    )

    # =========================================================================
    # analyze 명령 그룹
    # =========================================================================

    analyze_parser = subparsers.add_parser(
        "analyze",
        help="데이터 분석",
        description="수집된 데이터를 분석합니다.",
    )
    analyze_subparsers = analyze_parser.add_subparsers(
        dest="analyze_command", help="분석 명령"
    )

    # analyze full
    analyze_full_parser = analyze_subparsers.add_parser(
        "full",
        help="전체 분석 실행",
        description="트렌드, 수요, 경쟁 분석을 모두 실행합니다.",
    )
    analyze_full_parser.add_argument(
        "subreddit",
        help="분석할 서브레딧 이름",
    )
    analyze_full_parser.add_argument(
        "-l",
        "--limit",
        type=int,
        default=500,
        help="분석할 최대 게시물 수 (기본: 500)",
    )

    # =========================================================================
    # report 명령 그룹
    # =========================================================================

    report_parser = subparsers.add_parser(
        "report",
        help="리포트 생성",
        description="분석 결과를 리포트로 생성합니다.",
    )
    report_subparsers = report_parser.add_subparsers(
        dest="report_command", help="리포트 명령"
    )

    # report generate
    report_generate_parser = report_subparsers.add_parser(
        "generate",
        help="마크다운 리포트 생성",
        description="분석 결과를 마크다운 파일로 저장합니다.",
    )
    report_generate_parser.add_argument(
        "output_dir",
        help="리포트 출력 디렉토리",
    )
    report_generate_parser.add_argument(
        "-s",
        "--subreddit",
        required=True,
        help="분석할 서브레딧 이름",
    )
    report_generate_parser.add_argument(
        "-l",
        "--limit",
        type=int,
        default=500,
        help="분석할 최대 게시물 수 (기본: 500)",
    )

    # =========================================================================
    # dashboard 명령 그룹
    # =========================================================================

    dashboard_parser = subparsers.add_parser(
        "dashboard",
        help="웹 대시보드",
        description="웹 대시보드를 관리합니다.",
    )
    dashboard_subparsers = dashboard_parser.add_subparsers(
        dest="dashboard_command", help="대시보드 명령"
    )

    # dashboard start
    dashboard_start_parser = dashboard_subparsers.add_parser(
        "start",
        help="대시보드 서버 시작",
        description="웹 대시보드 서버를 시작합니다.",
    )
    dashboard_start_parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="서버 호스트 (기본: 127.0.0.1)",
    )
    dashboard_start_parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="서버 포트 (기본: 8000)",
    )
    dashboard_start_parser.add_argument(
        "--reload",
        action="store_true",
        help="개발 모드 (코드 변경 시 자동 재시작)",
    )

    # =========================================================================
    # status 명령
    # =========================================================================

    subparsers.add_parser(
        "status",
        help="데이터베이스 상태 조회",
        description="저장된 데이터 통계를 표시합니다.",
    )

    return parser


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================


def main(argv: Sequence[str] | None = None) -> int:
    """CLI 진입점.

    Args:
        argv: 명령줄 인자. None이면 sys.argv 사용

    Returns:
        종료 코드
    """
    parser = create_parser()
    args = parser.parse_args(argv)

    # 명령이 지정되지 않은 경우
    if args.command is None:
        console.print(
            Panel(
                "[bold]Reddit Insight[/bold] - Reddit 데이터 수집 및 분석 도구\n\n"
                "사용법: reddit-insight <command> [options]\n\n"
                "주요 명령:\n"
                "  [cyan]collect[/cyan]     서브레딧 데이터 수집\n"
                "  [cyan]analyze[/cyan]     데이터 분석 실행\n"
                "  [cyan]report[/cyan]      리포트 생성\n"
                "  [cyan]dashboard[/cyan]   웹 대시보드 시작\n"
                "  [cyan]status[/cyan]      데이터베이스 상태 확인\n\n"
                "자세한 도움말: reddit-insight --help",
                title="[bold blue]Reddit Insight v0.1.0[/bold blue]",
                border_style="blue",
            )
        )
        return 0

    # 로깅 설정
    debug_mode = getattr(args, "debug", False)
    setup_logging(debug_mode)

    # 명령 실행
    try:
        if args.command == "collect":
            return asyncio.run(cmd_collect(args))

        elif args.command == "collect-list":
            return asyncio.run(cmd_collect_list(args))

        elif args.command == "analyze":
            if not hasattr(args, "analyze_command") or args.analyze_command is None:
                print_error(
                    "분석 명령을 지정하세요.",
                    hint="예: reddit-insight analyze full python",
                )
                return 1
            if args.analyze_command == "full":
                return asyncio.run(cmd_analyze_full(args))
            else:
                print_error(f"알 수 없는 분석 명령: {args.analyze_command}")
                return 1

        elif args.command == "report":
            if not hasattr(args, "report_command") or args.report_command is None:
                print_error(
                    "리포트 명령을 지정하세요.",
                    hint="예: reddit-insight report generate ./reports -s python",
                )
                return 1
            if args.report_command == "generate":
                return asyncio.run(cmd_report_generate(args))
            else:
                print_error(f"알 수 없는 리포트 명령: {args.report_command}")
                return 1

        elif args.command == "dashboard":
            if (
                not hasattr(args, "dashboard_command")
                or args.dashboard_command is None
            ):
                print_error(
                    "대시보드 명령을 지정하세요.",
                    hint="예: reddit-insight dashboard start",
                )
                return 1
            if args.dashboard_command == "start":
                args.debug = debug_mode
                return cmd_dashboard_start(args)
            else:
                print_error(f"알 수 없는 대시보드 명령: {args.dashboard_command}")
                return 1

        elif args.command == "status":
            return asyncio.run(cmd_status(args))

        else:
            print_error(f"알 수 없는 명령: {args.command}")
            parser.print_help()
            return 1

    except KeyboardInterrupt:
        console.print("\n[yellow]사용자에 의해 중단되었습니다.[/yellow]")
        return 130

    except Exception as e:
        print_error(
            str(e),
            hint="--debug 옵션을 사용하면 상세한 오류 정보를 볼 수 있습니다.",
        )
        if debug_mode:
            console.print_exception()
        return 1


if __name__ == "__main__":
    sys.exit(main())
