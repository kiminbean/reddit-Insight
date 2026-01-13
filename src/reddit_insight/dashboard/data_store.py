"""대시보드 데이터 저장소.

분석 결과를 데이터베이스에 저장하고 서비스들이 접근할 수 있게 한다.
SQLite/PostgreSQL을 지원하며, 메모리 캐시를 통해 성능을 최적화한다.
"""

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from reddit_insight.dashboard.database import (
    AnalysisResult,
    SessionLocal,
    init_db,
)

# 레거시 JSON 파일 경로 (마이그레이션용)
DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
DATA_FILE = DATA_DIR / "analysis_results.json"


@dataclass
class AnalysisData:
    """분석 데이터 컨테이너."""

    subreddit: str = ""
    analyzed_at: str = ""
    post_count: int = 0

    # 키워드 데이터
    keywords: list[dict[str, Any]] = field(default_factory=list)

    # 트렌드 데이터
    trends: list[dict[str, Any]] = field(default_factory=list)

    # 수요 데이터
    demands: dict[str, Any] = field(default_factory=dict)

    # 경쟁 분석 데이터
    competition: dict[str, Any] = field(default_factory=dict)

    # 인사이트 데이터
    insights: list[dict[str, Any]] = field(default_factory=list)


# 메모리 캐시 (성능 최적화)
_current_data: AnalysisData | None = None
_cache_subreddit: str | None = None


def get_current_data(subreddit: str | None = None) -> AnalysisData | None:
    """현재 저장된 분석 데이터를 반환한다.

    Args:
        subreddit: 특정 서브레딧 데이터 요청 (None이면 최신 데이터)

    Returns:
        AnalysisData 또는 None
    """
    global _current_data, _cache_subreddit

    # 캐시 확인
    if _current_data is not None:
        if subreddit is None or subreddit == _cache_subreddit:
            return _current_data

    # 데이터베이스에서 로드
    data = load_from_database(subreddit)
    if data:
        _current_data = data
        _cache_subreddit = data.subreddit
        return data

    # 레거시 JSON 파일에서 로드 시도
    data = load_from_file()
    if data:
        _current_data = data
        _cache_subreddit = data.subreddit
        # 데이터베이스로 마이그레이션
        save_to_database(data)
        return data

    return None


def set_current_data(data: AnalysisData) -> None:
    """분석 데이터를 저장한다."""
    global _current_data, _cache_subreddit

    _current_data = data
    _cache_subreddit = data.subreddit

    # 데이터베이스에 저장
    save_to_database(data)

    # 레거시 JSON 파일에도 저장 (호환성)
    save_to_file(data)


def save_to_database(data: AnalysisData) -> int:
    """분석 데이터를 데이터베이스에 저장한다.

    Returns:
        저장된 레코드의 ID
    """
    init_db()  # 테이블이 없으면 생성

    db = SessionLocal()
    try:
        result = AnalysisResult(
            subreddit=data.subreddit,
            analyzed_at=datetime.fromisoformat(data.analyzed_at.replace("Z", "+00:00"))
            if data.analyzed_at
            else datetime.now(UTC),
            post_count=data.post_count,
            keywords=data.keywords,
            trends=data.trends,
            demands=data.demands,
            competition=data.competition,
            insights=data.insights,
        )
        db.add(result)
        db.commit()
        db.refresh(result)
        return result.id
    finally:
        db.close()


def load_from_database(subreddit: str | None = None) -> AnalysisData | None:
    """데이터베이스에서 분석 데이터를 로드한다.

    Args:
        subreddit: 특정 서브레딧 (None이면 최신 데이터)

    Returns:
        AnalysisData 또는 None
    """
    try:
        init_db()
    except Exception:
        return None

    db = SessionLocal()
    try:
        query = db.query(AnalysisResult)

        if subreddit:
            query = query.filter(AnalysisResult.subreddit == subreddit)

        result = query.order_by(AnalysisResult.analyzed_at.desc()).first()

        if result is None:
            return None

        return AnalysisData(
            subreddit=result.subreddit,
            analyzed_at=result.analyzed_at.isoformat() if result.analyzed_at else "",
            post_count=result.post_count,
            keywords=result.keywords or [],
            trends=result.trends or [],
            demands=result.demands or {},
            competition=result.competition or {},
            insights=result.insights or [],
        )
    except Exception:
        return None
    finally:
        db.close()


def get_all_subreddits() -> list[str]:
    """분석된 모든 서브레딧 목록을 반환한다."""
    try:
        init_db()
    except Exception:
        return []

    db = SessionLocal()
    try:
        results = (
            db.query(AnalysisResult.subreddit)
            .distinct()
            .order_by(AnalysisResult.subreddit)
            .all()
        )
        return [r[0] for r in results]
    except Exception:
        return []
    finally:
        db.close()


def get_analysis_history(
    subreddit: str | None = None, limit: int = 10
) -> list[dict[str, Any]]:
    """분석 이력을 반환한다."""
    try:
        init_db()
    except Exception:
        return []

    db = SessionLocal()
    try:
        query = db.query(AnalysisResult)

        if subreddit:
            query = query.filter(AnalysisResult.subreddit == subreddit)

        results = query.order_by(AnalysisResult.analyzed_at.desc()).limit(limit).all()

        return [
            {
                "id": r.id,
                "subreddit": r.subreddit,
                "analyzed_at": r.analyzed_at.isoformat() if r.analyzed_at else "",
                "post_count": r.post_count,
                "keyword_count": len(r.keywords) if r.keywords else 0,
                "insight_count": len(r.insights) if r.insights else 0,
            }
            for r in results
        ]
    except Exception:
        return []
    finally:
        db.close()


def save_to_file(data: AnalysisData) -> None:
    """분석 데이터를 JSON 파일에 저장한다 (레거시 호환성)."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(asdict(data), f, ensure_ascii=False, indent=2, default=str)


def load_from_file() -> AnalysisData | None:
    """JSON 파일에서 분석 데이터를 로드한다 (레거시 호환성)."""
    if not DATA_FILE.exists():
        return None

    try:
        with open(DATA_FILE, encoding="utf-8") as f:
            data = json.load(f)
        return AnalysisData(**data)
    except (json.JSONDecodeError, TypeError):
        return None


def clear_data() -> None:
    """저장된 데이터를 삭제한다."""
    global _current_data, _cache_subreddit

    _current_data = None
    _cache_subreddit = None

    if DATA_FILE.exists():
        DATA_FILE.unlink()


def clear_cache() -> None:
    """메모리 캐시를 초기화한다."""
    global _current_data, _cache_subreddit

    _current_data = None
    _cache_subreddit = None


def load_analysis_by_id(analysis_id: int) -> AnalysisData | None:
    """특정 ID의 분석 결과를 데이터베이스에서 로드한다.

    Args:
        analysis_id: 조회할 분석 결과 ID

    Returns:
        AnalysisData 또는 None (존재하지 않는 경우)
    """
    try:
        init_db()
    except Exception:
        return None

    db = SessionLocal()
    try:
        result = db.query(AnalysisResult).filter(AnalysisResult.id == analysis_id).first()

        if result is None:
            return None

        return AnalysisData(
            subreddit=result.subreddit,
            analyzed_at=result.analyzed_at.isoformat() if result.analyzed_at else "",
            post_count=result.post_count,
            keywords=result.keywords or [],
            trends=result.trends or [],
            demands=result.demands or {},
            competition=result.competition or {},
            insights=result.insights or [],
        )
    except Exception:
        return None
    finally:
        db.close()
