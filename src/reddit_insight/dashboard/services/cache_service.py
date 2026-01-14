"""캐시 서비스 모듈.

메모리 기반 캐시 서비스로 대시보드 성능을 최적화한다.
ML 분석 결과, 예측 결과, 토픽 모델링 결과 등을 캐싱하여 재계산을 방지한다.
"""

import hashlib
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, TypeVar

T = TypeVar("T")


@dataclass
class CacheEntry:
    """캐시 엔트리.

    Attributes:
        value: 캐시된 값
        expires_at: 만료 시각 (Unix timestamp)
        created_at: 생성 시각 (Unix timestamp)
    """

    value: Any
    expires_at: float
    created_at: float = field(default_factory=time.time)


class CacheService:
    """메모리 기반 캐시 서비스.

    TTL 기반 만료를 지원하는 간단한 캐시 서비스다.
    분석 결과, ML 예측 결과 등 계산 비용이 높은 데이터를 캐싱한다.

    Key Patterns:
        - analysis:{subreddit} : 분석 결과
        - prediction:{keyword} : 트렌드 예측 결과
        - topics:{hash} : 토픽 모델링 결과
        - anomaly:{keyword}:{method} : 이상 탐지 결과

    Attributes:
        _cache: 캐시 저장소
        _default_ttl: 기본 TTL (초)
        _max_entries: 최대 엔트리 수 (메모리 제한)
    """

    def __init__(self, default_ttl: int = 300, max_entries: int = 1000) -> None:
        """CacheService를 초기화한다.

        Args:
            default_ttl: 기본 TTL (초), 기본값 300초 (5분)
            max_entries: 최대 엔트리 수, 기본값 1000
        """
        self._cache: dict[str, CacheEntry] = {}
        self._default_ttl = default_ttl
        self._max_entries = max_entries

    def get(self, key: str) -> Any | None:
        """캐시에서 값을 조회한다.

        만료된 엔트리는 자동으로 삭제한다.

        Args:
            key: 캐시 키

        Returns:
            캐시된 값 또는 None (없거나 만료된 경우)
        """
        entry = self._cache.get(key)

        if entry is None:
            return None

        # 만료 확인
        if time.time() > entry.expires_at:
            del self._cache[key]
            return None

        return entry.value

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """캐시에 값을 저장한다.

        최대 엔트리 수를 초과하면 가장 오래된 엔트리를 삭제한다.

        Args:
            key: 캐시 키
            value: 저장할 값
            ttl: TTL (초), None이면 기본값 사용
        """
        # 최대 엔트리 수 확인
        if len(self._cache) >= self._max_entries and key not in self._cache:
            self._evict_oldest()

        # 만료 시각 계산
        effective_ttl = ttl if ttl is not None else self._default_ttl
        expires_at = time.time() + effective_ttl

        self._cache[key] = CacheEntry(value=value, expires_at=expires_at)

    def delete(self, key: str) -> bool:
        """캐시에서 키를 삭제한다.

        Args:
            key: 삭제할 캐시 키

        Returns:
            삭제 성공 여부
        """
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    def clear(self) -> int:
        """모든 캐시 엔트리를 삭제한다.

        Returns:
            삭제된 엔트리 수
        """
        count = len(self._cache)
        self._cache.clear()
        return count

    def get_or_set(
        self,
        key: str,
        factory: Callable[[], T],
        ttl: int | None = None,
    ) -> T:
        """캐시에서 조회하거나 없으면 생성하여 저장한다.

        Args:
            key: 캐시 키
            factory: 값을 생성하는 함수
            ttl: TTL (초), None이면 기본값 사용

        Returns:
            캐시된 값 또는 새로 생성된 값
        """
        value = self.get(key)

        if value is not None:
            return value

        # 새 값 생성
        new_value = factory()
        self.set(key, new_value, ttl)
        return new_value

    def delete_pattern(self, pattern: str) -> int:
        """패턴과 일치하는 모든 키를 삭제한다.

        간단한 prefix 매칭을 지원한다.
        예: "analysis:*" -> "analysis:"로 시작하는 모든 키 삭제

        Args:
            pattern: 패턴 (예: "analysis:*")

        Returns:
            삭제된 엔트리 수
        """
        if pattern.endswith("*"):
            prefix = pattern[:-1]
            keys_to_delete = [key for key in self._cache if key.startswith(prefix)]
        else:
            keys_to_delete = [pattern] if pattern in self._cache else []

        for key in keys_to_delete:
            del self._cache[key]

        return len(keys_to_delete)

    def stats(self) -> dict[str, Any]:
        """캐시 통계를 반환한다.

        Returns:
            캐시 통계 딕셔너리
        """
        now = time.time()
        expired = sum(1 for entry in self._cache.values() if now > entry.expires_at)

        return {
            "total_entries": len(self._cache),
            "expired_entries": expired,
            "active_entries": len(self._cache) - expired,
            "max_entries": self._max_entries,
            "default_ttl": self._default_ttl,
        }

    def cleanup(self) -> int:
        """만료된 엔트리를 정리한다.

        Returns:
            삭제된 엔트리 수
        """
        now = time.time()
        expired_keys = [key for key, entry in self._cache.items() if now > entry.expires_at]

        for key in expired_keys:
            del self._cache[key]

        return len(expired_keys)

    def _evict_oldest(self) -> None:
        """가장 오래된 엔트리를 삭제한다 (LRU-like)."""
        if not self._cache:
            return

        # 생성 시각이 가장 오래된 엔트리 찾기
        oldest_key = min(self._cache, key=lambda k: self._cache[k].created_at)
        del self._cache[oldest_key]


# =============================================================================
# KEY GENERATION UTILITIES
# =============================================================================


def make_analysis_key(subreddit: str) -> str:
    """분석 결과 캐시 키를 생성한다.

    Args:
        subreddit: 서브레딧 이름

    Returns:
        캐시 키
    """
    return f"analysis:{subreddit.lower()}"


def make_prediction_key(keyword: str, days: int = 7) -> str:
    """예측 결과 캐시 키를 생성한다.

    Args:
        keyword: 키워드
        days: 예측 기간

    Returns:
        캐시 키
    """
    return f"prediction:{keyword.lower()}:{days}"


def make_topics_key(texts_hash: str) -> str:
    """토픽 모델링 결과 캐시 키를 생성한다.

    Args:
        texts_hash: 텍스트 목록의 해시

    Returns:
        캐시 키
    """
    return f"topics:{texts_hash}"


def make_anomaly_key(keyword: str, method: str = "auto") -> str:
    """이상 탐지 결과 캐시 키를 생성한다.

    Args:
        keyword: 키워드
        method: 탐지 방법

    Returns:
        캐시 키
    """
    return f"anomaly:{keyword.lower()}:{method}"


def hash_texts(texts: list[str]) -> str:
    """텍스트 목록의 해시를 생성한다.

    토픽 모델링 등 텍스트 목록 기반 캐싱에 사용한다.

    Args:
        texts: 텍스트 목록

    Returns:
        MD5 해시 (16자)
    """
    content = "".join(sorted(texts[:100]))  # 처음 100개만 사용
    return hashlib.md5(content.encode()).hexdigest()[:16]


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_cache_service: CacheService | None = None


def get_cache_service() -> CacheService:
    """CacheService 싱글톤 인스턴스를 반환한다.

    Returns:
        CacheService 인스턴스
    """
    global _cache_service
    if _cache_service is None:
        # 기본 TTL: 5분, 최대 1000개 엔트리
        _cache_service = CacheService(default_ttl=300, max_entries=1000)
    return _cache_service


def reset_cache_service() -> None:
    """캐시 서비스를 리셋한다 (테스트용)."""
    global _cache_service
    _cache_service = None
