"""Reddit Insight CLI.

데이터 수집 및 관리를 위한 명령줄 인터페이스.
argparse와 rich를 사용한다.
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
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table

from reddit_insight.pipeline.collector import Collector, CollectorConfig

console = Console()


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


# ========== collect 명령 ==========


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
        f"\n[bold blue]r/{config.subreddit}[/bold blue] 수집 시작 "
        f"(sort={config.sort}, limit={config.limit})"
    )

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
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
        console.print(f"\n[bold red]오류:[/bold red] {result.error}")
        return 1

    console.print("\n[bold green]수집 완료![/bold green]")
    return 0


# ========== collect-list 명령 ==========


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
            console.print(f"[bold red]파일을 찾을 수 없습니다: {file_path}[/bold red]")
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
        console.print("[bold red]수집할 서브레딧이 없습니다.[/bold red]")
        return 1

    console.print(
        f"\n[bold blue]{len(subreddits)}개 서브레딧 수집 시작[/bold blue] "
        f"(sort={args.sort}, limit={args.limit})"
    )

    for subreddit in subreddits:
        console.print(f"  - r/{subreddit}")

    console.print()

    results = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
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
        console.print("\n[bold green]모든 수집 완료![/bold green]")
        return 0
    else:
        console.print("\n[bold yellow]일부 수집 실패[/bold yellow]")
        return 1


# ========== status 명령 ==========


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

    console.print("\n[bold blue]데이터베이스 상태[/bold blue]\n")

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


# ========== 메인 함수 ==========


def create_parser() -> argparse.ArgumentParser:
    """인자 파서 생성."""
    parser = argparse.ArgumentParser(
        prog="reddit-insight",
        description="Reddit 데이터 수집 및 분석 도구",
    )
    parser.add_argument(
        "-d", "--debug",
        action="store_true",
        help="디버그 모드 활성화",
    )
    parser.add_argument(
        "-v", "--version",
        action="version",
        version="%(prog)s 0.1.0",
    )

    subparsers = parser.add_subparsers(dest="command", help="사용 가능한 명령")

    # collect 명령
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
        "-s", "--sort",
        choices=["hot", "new", "top"],
        default="hot",
        help="정렬 방식 (기본: hot)",
    )
    collect_parser.add_argument(
        "-l", "--limit",
        type=int,
        default=100,
        help="수집할 게시물 수 (기본: 100)",
    )
    collect_parser.add_argument(
        "-c", "--comments",
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
        "-t", "--time-filter",
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
        "-s", "--sort",
        choices=["hot", "new", "top"],
        default="hot",
        help="정렬 방식 (기본: hot)",
    )
    collect_list_parser.add_argument(
        "-l", "--limit",
        type=int,
        default=100,
        help="수집할 게시물 수 (기본: 100)",
    )
    collect_list_parser.add_argument(
        "-c", "--comments",
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
        "-t", "--time-filter",
        choices=["hour", "day", "week", "month", "year", "all"],
        default="week",
        help="top 정렬 시 기간 필터 (기본: week)",
    )

    # status 명령
    subparsers.add_parser(
        "status",
        help="데이터베이스 상태 조회",
        description="저장된 데이터 통계를 표시합니다.",
    )

    return parser


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
        parser.print_help()
        return 0

    # 로깅 설정
    setup_logging(args.debug)

    # 명령 실행
    try:
        if args.command == "collect":
            return asyncio.run(cmd_collect(args))
        elif args.command == "collect-list":
            return asyncio.run(cmd_collect_list(args))
        elif args.command == "status":
            return asyncio.run(cmd_status(args))
        else:
            parser.print_help()
            return 1
    except KeyboardInterrupt:
        console.print("\n[yellow]중단됨[/yellow]")
        return 130
    except Exception as e:
        console.print(f"\n[bold red]오류:[/bold red] {e}")
        if args.debug:
            console.print_exception()
        return 1


if __name__ == "__main__":
    sys.exit(main())
