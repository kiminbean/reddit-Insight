"""데이터베이스 연결 및 모델 정의.

SQLAlchemy를 사용하여 분석 결과를 영구 저장한다.
기본적으로 SQLite를 사용하며, DATABASE_URL 환경변수로 PostgreSQL 전환 가능.
"""

import os
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    sessionmaker,
)

# 데이터베이스 URL (기본: SQLite)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./data/reddit_insight.db"
)

# PostgreSQL URL 형식 변환 (Heroku 등에서 사용)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# 엔진 생성
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    echo=False,
)

# 세션 팩토리
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """SQLAlchemy 기본 클래스."""

    pass


class AnalysisResult(Base):
    """분석 결과 모델."""

    __tablename__ = "analysis_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    subreddit: Mapped[str] = mapped_column(String(100), index=True)
    analyzed_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC)
    )
    post_count: Mapped[int] = mapped_column(Integer, default=0)

    # JSON 필드로 복잡한 데이터 저장
    keywords: Mapped[dict[str, Any]] = mapped_column(JSON, default=list)
    trends: Mapped[dict[str, Any]] = mapped_column(JSON, default=list)
    demands: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    competition: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    insights: Mapped[dict[str, Any]] = mapped_column(JSON, default=list)

    def __repr__(self) -> str:
        """문자열 표현."""
        return f"<AnalysisResult(id={self.id}, subreddit='{self.subreddit}')>"


class APIKey(Base):
    """API 키 모델."""

    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC)
    )
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(Integer, default=True)
    rate_limit: Mapped[int] = mapped_column(Integer, default=100)  # 분당 요청 수

    def __repr__(self) -> str:
        """문자열 표현."""
        return f"<APIKey(id={self.id}, name='{self.name}')>"


class RequestLog(Base):
    """요청 로그 모델 (Rate Limiting용)."""

    __tablename__ = "request_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    api_key_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    ip_address: Mapped[str] = mapped_column(String(45), index=True)  # IPv6 지원
    endpoint: Mapped[str] = mapped_column(String(200))
    method: Mapped[str] = mapped_column(String(10))
    status_code: Mapped[int] = mapped_column(Integer)
    response_time_ms: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), index=True
    )

    def __repr__(self) -> str:
        """문자열 표현."""
        return f"<RequestLog(id={self.id}, endpoint='{self.endpoint}')>"


class ScheduledTask(Base):
    """예약 작업 모델."""

    __tablename__ = "scheduled_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    subreddit: Mapped[str] = mapped_column(String(100))
    schedule: Mapped[str] = mapped_column(String(50))  # cron 표현식
    last_run: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    next_run: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(Integer, default=True)
    post_limit: Mapped[int] = mapped_column(Integer, default=100)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC)
    )

    def __repr__(self) -> str:
        """문자열 표현."""
        return f"<ScheduledTask(id={self.id}, subreddit='{self.subreddit}')>"


def init_db() -> None:
    """데이터베이스 테이블을 생성한다."""
    # data 디렉토리 생성
    import os
    from pathlib import Path

    data_dir = Path("./data")
    data_dir.mkdir(parents=True, exist_ok=True)

    Base.metadata.create_all(bind=engine)


def get_db() -> Session:
    """데이터베이스 세션을 반환한다."""
    db = SessionLocal()
    try:
        return db
    except Exception:
        db.close()
        raise


def get_db_context():
    """FastAPI 의존성 주입용 제너레이터."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
