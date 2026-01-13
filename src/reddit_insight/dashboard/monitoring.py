"""모니터링 및 로깅 모듈.

애플리케이션 상태, 요청 로그, 성능 메트릭을 추적한다.
"""

import logging
import os
import time
from datetime import UTC, datetime, timedelta
from typing import Any, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from reddit_insight.dashboard.database import RequestLog, SessionLocal, init_db

# 로깅 설정
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# 로거 설정
logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT)
logger = logging.getLogger("reddit_insight")


def setup_logging(log_file: str | None = None) -> None:
    """로깅을 설정한다.

    Args:
        log_file: 로그 파일 경로 (None이면 콘솔만)
    """
    handlers: list[logging.Handler] = [logging.StreamHandler()]

    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
        handlers.append(file_handler)

    logging.basicConfig(
        level=LOG_LEVEL,
        format=LOG_FORMAT,
        handlers=handlers,
        force=True,
    )


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """HTTP 요청을 로깅하는 미들웨어."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """요청을 처리하고 로그를 기록한다."""
        start_time = time.time()

        # 클라이언트 IP 추출
        client_ip = request.client.host if request.client else "unknown"
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()

        # 요청 처리
        response = await call_next(request)

        # 응답 시간 계산
        process_time = (time.time() - start_time) * 1000  # ms

        # 로그 기록
        logger.info(
            f"{request.method} {request.url.path} "
            f"- Status: {response.status_code} "
            f"- Time: {process_time:.2f}ms "
            f"- IP: {client_ip}"
        )

        # 데이터베이스에 기록 (비동기로 실행해도 됨)
        try:
            self._save_request_log(
                ip_address=client_ip,
                endpoint=str(request.url.path),
                method=request.method,
                status_code=response.status_code,
                response_time_ms=process_time,
            )
        except Exception as e:
            logger.warning(f"Failed to save request log: {e}")

        # 응답 헤더에 처리 시간 추가
        response.headers["X-Process-Time"] = f"{process_time:.2f}ms"

        return response

    def _save_request_log(
        self,
        ip_address: str,
        endpoint: str,
        method: str,
        status_code: int,
        response_time_ms: float,
    ) -> None:
        """요청 로그를 데이터베이스에 저장한다."""
        # 정적 파일 요청은 제외
        if endpoint.startswith("/static"):
            return

        try:
            init_db()
            db = SessionLocal()
            try:
                log = RequestLog(
                    ip_address=ip_address,
                    endpoint=endpoint,
                    method=method,
                    status_code=status_code,
                    response_time_ms=response_time_ms,
                )
                db.add(log)
                db.commit()
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"Failed to save request log: {e}")


# ============================================================================
# Metrics
# ============================================================================


def get_request_stats(hours: int = 24) -> dict[str, Any]:
    """요청 통계를 반환한다.

    Args:
        hours: 통계 기간 (시간)

    Returns:
        통계 딕셔너리
    """
    try:
        init_db()
    except Exception:
        return {}

    db = SessionLocal()
    try:
        since = datetime.now(UTC) - timedelta(hours=hours)

        # 총 요청 수
        total_requests = (
            db.query(RequestLog)
            .filter(RequestLog.created_at >= since)
            .count()
        )

        # 상태 코드별 요청 수
        from sqlalchemy import func

        status_counts = (
            db.query(RequestLog.status_code, func.count(RequestLog.id))
            .filter(RequestLog.created_at >= since)
            .group_by(RequestLog.status_code)
            .all()
        )

        # 평균 응답 시간
        avg_response_time = (
            db.query(func.avg(RequestLog.response_time_ms))
            .filter(RequestLog.created_at >= since)
            .scalar()
        )

        # 엔드포인트별 요청 수
        endpoint_counts = (
            db.query(RequestLog.endpoint, func.count(RequestLog.id))
            .filter(RequestLog.created_at >= since)
            .group_by(RequestLog.endpoint)
            .order_by(func.count(RequestLog.id).desc())
            .limit(10)
            .all()
        )

        return {
            "period_hours": hours,
            "total_requests": total_requests,
            "status_codes": {str(code): count for code, count in status_counts},
            "avg_response_time_ms": round(avg_response_time or 0, 2),
            "top_endpoints": [
                {"endpoint": ep, "count": count} for ep, count in endpoint_counts
            ],
        }

    except Exception as e:
        logger.error(f"Error getting request stats: {e}")
        return {}
    finally:
        db.close()


def get_error_logs(limit: int = 50) -> list[dict[str, Any]]:
    """오류 로그를 반환한다.

    Args:
        limit: 반환할 최대 로그 수

    Returns:
        오류 로그 목록
    """
    try:
        init_db()
    except Exception:
        return []

    db = SessionLocal()
    try:
        logs = (
            db.query(RequestLog)
            .filter(RequestLog.status_code >= 400)
            .order_by(RequestLog.created_at.desc())
            .limit(limit)
            .all()
        )

        return [
            {
                "id": log.id,
                "ip_address": log.ip_address,
                "endpoint": log.endpoint,
                "method": log.method,
                "status_code": log.status_code,
                "response_time_ms": log.response_time_ms,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in logs
        ]

    except Exception as e:
        logger.error(f"Error getting error logs: {e}")
        return []
    finally:
        db.close()


def get_system_health() -> dict[str, Any]:
    """시스템 상태를 반환한다."""
    import platform

    try:
        import psutil

        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
    except ImportError:
        cpu_percent = None
        memory = None
        disk = None

    health = {
        "status": "healthy",
        "timestamp": datetime.now(UTC).isoformat(),
        "platform": {
            "system": platform.system(),
            "python_version": platform.python_version(),
        },
    }

    if cpu_percent is not None:
        health["resources"] = {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent if memory else None,
            "memory_used_gb": round(memory.used / (1024**3), 2) if memory else None,
            "disk_percent": disk.percent if disk else None,
        }

    # 데이터베이스 연결 확인
    try:
        from sqlalchemy import text
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        health["database"] = "connected"
    except Exception as e:
        health["database"] = f"error: {str(e)}"
        health["status"] = "degraded"

    return health


# ============================================================================
# CLI
# ============================================================================


def cli_show_stats(hours: int = 24) -> None:
    """CLI에서 통계를 출력한다."""
    stats = get_request_stats(hours)
    if not stats:
        print("No statistics available.")
        return

    print(f"\n=== Request Statistics (Last {hours} hours) ===")
    print(f"Total Requests: {stats['total_requests']}")
    print(f"Average Response Time: {stats['avg_response_time_ms']}ms")

    print("\nStatus Codes:")
    for code, count in stats.get("status_codes", {}).items():
        print(f"  {code}: {count}")

    print("\nTop Endpoints:")
    for ep in stats.get("top_endpoints", []):
        print(f"  {ep['endpoint']}: {ep['count']}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python -m reddit_insight.dashboard.monitoring stats [hours]")
        print("  python -m reddit_insight.dashboard.monitoring errors [limit]")
        print("  python -m reddit_insight.dashboard.monitoring health")
        sys.exit(1)

    command = sys.argv[1]

    if command == "stats":
        hours = int(sys.argv[2]) if len(sys.argv) > 2 else 24
        cli_show_stats(hours)

    elif command == "errors":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 50
        errors = get_error_logs(limit)
        print(f"\n=== Error Logs (Last {limit}) ===")
        for e in errors:
            print(f"  [{e['created_at']}] {e['method']} {e['endpoint']} - {e['status_code']}")

    elif command == "health":
        health = get_system_health()
        import json

        print(json.dumps(health, indent=2))

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
