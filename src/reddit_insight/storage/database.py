"""데이터베이스 연결 관리.

SQLAlchemy async 엔진과 세션 관리를 제공한다.
SQLite와 PostgreSQL 모두 지원하도록 설계되었다.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from reddit_insight.config import get_settings
from reddit_insight.storage.models import Base


class Database:
    """비동기 데이터베이스 연결 관리 클래스.

    SQLAlchemy 2.0 스타일의 async 엔진과 세션 팩토리를 관리한다.
    컨텍스트 매니저 패턴을 지원하여 리소스 자동 정리를 보장한다.

    Example:
        >>> async with Database() as db:
        ...     async with db.session() as session:
        ...         result = await session.execute(...)

        >>> # 또는 명시적 연결/해제
        >>> db = Database()
        >>> await db.connect()
        >>> try:
        ...     async with db.session() as session:
        ...         ...
        ... finally:
        ...     await db.disconnect()
    """

    def __init__(self, url: str | None = None) -> None:
        """데이터베이스 인스턴스 초기화.

        Args:
            url: 데이터베이스 연결 URL. None이면 Settings에서 가져옴.
                 SQLite 예: sqlite+aiosqlite:///./data/reddit_insight.db
                 PostgreSQL 예: postgresql+asyncpg://user:pass@host/db
        """
        self._url = url or self._convert_url(get_settings().database_url)
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None

    @staticmethod
    def _convert_url(url: str) -> str:
        """동기 URL을 비동기 URL로 변환.

        sqlite:// -> sqlite+aiosqlite://
        postgresql:// -> postgresql+asyncpg://

        Args:
            url: 원본 데이터베이스 URL

        Returns:
            비동기 드라이버가 포함된 URL
        """
        if url.startswith("sqlite://") and "+aiosqlite" not in url:
            return url.replace("sqlite://", "sqlite+aiosqlite://")
        if url.startswith("postgresql://") and "+asyncpg" not in url:
            return url.replace("postgresql://", "postgresql+asyncpg://")
        return url

    @property
    def url(self) -> str:
        """데이터베이스 URL."""
        return self._url

    @property
    def engine(self) -> AsyncEngine:
        """AsyncEngine 인스턴스.

        Raises:
            RuntimeError: 연결되지 않은 상태에서 접근 시
        """
        if self._engine is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self._engine

    async def connect(self) -> None:
        """데이터베이스 연결 및 테이블 생성.

        SQLite 사용 시 데이터베이스 파일 디렉토리를 자동 생성한다.
        """
        if self._engine is not None:
            return  # 이미 연결됨

        # SQLite 파일 경로 디렉토리 생성
        self._ensure_sqlite_directory()

        # 디버그 모드에서만 SQL 로깅
        settings = get_settings()
        echo = settings.debug

        self._engine = create_async_engine(
            self._url,
            echo=echo,
            pool_pre_ping=True,  # 연결 상태 확인
        )

        self._session_factory = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,  # 커밋 후에도 객체 사용 가능
        )

        # 테이블 생성
        await self.create_tables()

    async def disconnect(self) -> None:
        """데이터베이스 연결 해제."""
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None

    def _ensure_sqlite_directory(self) -> None:
        """SQLite 데이터베이스 파일 디렉토리 생성."""
        if "sqlite" not in self._url:
            return

        # URL에서 파일 경로 추출
        # sqlite+aiosqlite:///./data/reddit_insight.db -> ./data/reddit_insight.db
        # sqlite+aiosqlite:////absolute/path/db.sqlite -> /absolute/path/db.sqlite
        parts = self._url.split("///")
        if len(parts) != 2:
            return

        db_path = parts[1]
        if db_path.startswith("/"):
            # 절대 경로: sqlite+aiosqlite:////absolute/path
            db_file = Path(db_path)
        else:
            # 상대 경로: sqlite+aiosqlite:///./relative/path
            db_file = Path(db_path)

        # 디렉토리 생성
        db_file.parent.mkdir(parents=True, exist_ok=True)

    async def create_tables(self) -> None:
        """모든 테이블 생성.

        Base.metadata에 정의된 모든 테이블을 생성한다.
        이미 존재하는 테이블은 무시된다.
        """
        if self._engine is None:
            raise RuntimeError("Database not connected. Call connect() first.")

        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def drop_tables(self) -> None:
        """모든 테이블 삭제.

        주의: 개발/테스트 환경에서만 사용해야 한다.
        프로덕션 데이터가 모두 삭제된다.
        """
        if self._engine is None:
            raise RuntimeError("Database not connected. Call connect() first.")

        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        """세션 컨텍스트 매니저.

        자동으로 커밋/롤백을 처리하며, 세션을 적절히 닫는다.

        Yields:
            AsyncSession: 데이터베이스 세션

        Raises:
            RuntimeError: 연결되지 않은 상태에서 호출 시

        Example:
            >>> async with db.session() as session:
            ...     session.add(model)
            ...     await session.commit()
        """
        if self._session_factory is None:
            raise RuntimeError("Database not connected. Call connect() first.")

        session = self._session_factory()
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    async def __aenter__(self) -> Database:
        """비동기 컨텍스트 매니저 진입."""
        await self.connect()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object | None,
    ) -> None:
        """비동기 컨텍스트 매니저 종료."""
        await self.disconnect()
