"""LLM 응답 캐시 모듈.

프롬프트 해시 기반으로 LLM 응답을 캐싱하여 중복 API 호출을 방지한다.
"""

from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """캐시 엔트리."""

    value: str
    created_at: float
    hits: int = 0


@dataclass
class LLMCache:
    """LLM 응답 캐시.

    프롬프트와 모델을 기반으로 응답을 캐싱한다.
    TTL(Time To Live)이 지난 항목은 자동으로 만료된다.
    """

    ttl: int = 86400  # 기본 24시간
    max_size: int = 1000  # 최대 캐시 항목 수
    _cache: dict[str, CacheEntry] = field(default_factory=dict)
    _total_hits: int = 0
    _total_misses: int = 0

    def _generate_key(self, prompt: str, model: str) -> str:
        """캐시 키를 생성한다.

        Args:
            prompt: 프롬프트 텍스트
            model: 모델 이름

        Returns:
            해시 기반 캐시 키
        """
        combined = f"{model}:{prompt}"
        return hashlib.sha256(combined.encode("utf-8")).hexdigest()

    def _is_expired(self, entry: CacheEntry) -> bool:
        """항목이 만료되었는지 확인한다.

        Args:
            entry: 캐시 엔트리

        Returns:
            만료 여부
        """
        return (time.time() - entry.created_at) > self.ttl

    def _evict_if_needed(self) -> None:
        """캐시가 가득 차면 오래된 항목을 제거한다."""
        if len(self._cache) >= self.max_size:
            # 가장 오래된 항목 제거 (LRU가 아닌 FIFO)
            oldest_key = min(self._cache, key=lambda k: self._cache[k].created_at)
            del self._cache[oldest_key]
            logger.debug("Evicted cache entry: %s", oldest_key[:16])

    def _cleanup_expired(self) -> None:
        """만료된 캐시 항목을 정리한다."""
        current_time = time.time()
        expired_keys = [
            key
            for key, entry in self._cache.items()
            if (current_time - entry.created_at) > self.ttl
        ]

        for key in expired_keys:
            del self._cache[key]

        if expired_keys:
            logger.debug("Cleaned up %d expired cache entries", len(expired_keys))

    def get(self, prompt: str, model: str) -> str | None:
        """캐시에서 응답을 조회한다.

        Args:
            prompt: 프롬프트 텍스트
            model: 모델 이름

        Returns:
            캐시된 응답 또는 None
        """
        key = self._generate_key(prompt, model)
        entry = self._cache.get(key)

        if entry is None:
            self._total_misses += 1
            return None

        if self._is_expired(entry):
            del self._cache[key]
            self._total_misses += 1
            return None

        entry.hits += 1
        self._total_hits += 1
        logger.debug("Cache hit for key: %s", key[:16])
        return entry.value

    def set(self, prompt: str, model: str, response: str) -> None:
        """응답을 캐시에 저장한다.

        Args:
            prompt: 프롬프트 텍스트
            model: 모델 이름
            response: LLM 응답
        """
        self._evict_if_needed()

        key = self._generate_key(prompt, model)
        self._cache[key] = CacheEntry(
            value=response,
            created_at=time.time(),
        )
        logger.debug("Cached response for key: %s", key[:16])

    def invalidate(self, prompt: str, model: str) -> bool:
        """특정 캐시 항목을 무효화한다.

        Args:
            prompt: 프롬프트 텍스트
            model: 모델 이름

        Returns:
            삭제 성공 여부
        """
        key = self._generate_key(prompt, model)
        if key in self._cache:
            del self._cache[key]
            logger.debug("Invalidated cache entry: %s", key[:16])
            return True
        return False

    def clear(self) -> None:
        """캐시를 완전히 비운다."""
        count = len(self._cache)
        self._cache.clear()
        logger.debug("Cleared %d cache entries", count)

    def get_stats(self) -> dict[str, int | float]:
        """캐시 통계를 반환한다.

        Returns:
            통계 정보 딕셔너리
        """
        self._cleanup_expired()

        total_requests = self._total_hits + self._total_misses
        hit_rate = (self._total_hits / total_requests * 100) if total_requests > 0 else 0.0

        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "ttl": self.ttl,
            "total_hits": self._total_hits,
            "total_misses": self._total_misses,
            "hit_rate_percent": round(hit_rate, 2),
        }
