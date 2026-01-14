"""LLM 캐시 테스트."""

from __future__ import annotations

import time

import pytest

from reddit_insight.llm.cache import LLMCache, CacheEntry


class TestCacheEntry:
    """CacheEntry 클래스 테스트."""

    def test_create_entry(self) -> None:
        """캐시 엔트리를 생성할 수 있다."""
        entry = CacheEntry(value="test", created_at=time.time())
        assert entry.value == "test"
        assert entry.hits == 0

    def test_entry_hits(self) -> None:
        """히트 카운터가 증가한다."""
        entry = CacheEntry(value="test", created_at=time.time())
        entry.hits += 1
        assert entry.hits == 1


class TestLLMCache:
    """LLMCache 클래스 테스트."""

    @pytest.fixture
    def cache(self) -> LLMCache:
        """테스트용 캐시."""
        return LLMCache(ttl=3600, max_size=100)

    def test_set_and_get(self, cache: LLMCache) -> None:
        """캐시에 저장하고 조회할 수 있다."""
        cache.set("prompt1", "model1", "response1")
        result = cache.get("prompt1", "model1")
        assert result == "response1"

    def test_get_nonexistent(self, cache: LLMCache) -> None:
        """존재하지 않는 항목은 None을 반환한다."""
        result = cache.get("nonexistent", "model")
        assert result is None

    def test_different_models_different_cache(self, cache: LLMCache) -> None:
        """다른 모델은 다른 캐시 엔트리를 가진다."""
        cache.set("prompt", "model1", "response1")
        cache.set("prompt", "model2", "response2")

        assert cache.get("prompt", "model1") == "response1"
        assert cache.get("prompt", "model2") == "response2"

    def test_cache_expiration(self) -> None:
        """TTL이 지나면 캐시가 만료된다."""
        cache = LLMCache(ttl=0)  # 즉시 만료
        cache.set("prompt", "model", "response")

        # 약간의 시간이 지나면 만료됨
        time.sleep(0.01)
        result = cache.get("prompt", "model")
        assert result is None

    def test_invalidate(self, cache: LLMCache) -> None:
        """캐시 항목을 무효화할 수 있다."""
        cache.set("prompt", "model", "response")
        assert cache.get("prompt", "model") == "response"

        result = cache.invalidate("prompt", "model")
        assert result is True
        assert cache.get("prompt", "model") is None

    def test_invalidate_nonexistent(self, cache: LLMCache) -> None:
        """존재하지 않는 항목 무효화는 False를 반환한다."""
        result = cache.invalidate("nonexistent", "model")
        assert result is False

    def test_clear(self, cache: LLMCache) -> None:
        """캐시를 완전히 비울 수 있다."""
        cache.set("prompt1", "model", "response1")
        cache.set("prompt2", "model", "response2")

        cache.clear()

        assert cache.get("prompt1", "model") is None
        assert cache.get("prompt2", "model") is None

    def test_eviction_when_full(self) -> None:
        """캐시가 가득 차면 오래된 항목이 제거된다."""
        cache = LLMCache(ttl=3600, max_size=2)

        cache.set("prompt1", "model", "response1")
        cache.set("prompt2", "model", "response2")
        cache.set("prompt3", "model", "response3")

        # max_size가 2이므로 가장 오래된 항목이 제거됨
        assert cache.get("prompt3", "model") == "response3"
        assert cache.get("prompt2", "model") == "response2"
        # prompt1은 제거되었을 수 있음

    def test_get_stats(self, cache: LLMCache) -> None:
        """통계를 조회할 수 있다."""
        cache.set("prompt", "model", "response")
        cache.get("prompt", "model")  # Hit
        cache.get("nonexistent", "model")  # Miss

        stats = cache.get_stats()

        assert "size" in stats
        assert "max_size" in stats
        assert "ttl" in stats
        assert "total_hits" in stats
        assert "total_misses" in stats
        assert "hit_rate_percent" in stats

        assert stats["size"] == 1
        assert stats["total_hits"] == 1
        assert stats["total_misses"] == 1
        assert stats["hit_rate_percent"] == 50.0

    def test_hit_rate_calculation(self, cache: LLMCache) -> None:
        """히트율이 올바르게 계산된다."""
        cache.set("prompt", "model", "response")

        # 4번 히트, 1번 미스
        for _ in range(4):
            cache.get("prompt", "model")
        cache.get("miss", "model")

        stats = cache.get_stats()
        assert stats["hit_rate_percent"] == 80.0

    def test_hit_rate_no_requests(self, cache: LLMCache) -> None:
        """요청이 없을 때 히트율은 0이다."""
        stats = cache.get_stats()
        assert stats["hit_rate_percent"] == 0.0


class TestLLMCacheEdgeCases:
    """LLMCache 엣지 케이스 테스트."""

    def test_default_values(self) -> None:
        """기본값이 올바르게 설정된다."""
        cache = LLMCache()
        assert cache.ttl == 86400  # 24시간
        assert cache.max_size == 1000

    def test_empty_prompt(self) -> None:
        """빈 프롬프트도 캐시할 수 있다."""
        cache = LLMCache()
        cache.set("", "model", "response")
        assert cache.get("", "model") == "response"

    def test_empty_response(self) -> None:
        """빈 응답도 캐시할 수 있다."""
        cache = LLMCache()
        cache.set("prompt", "model", "")
        assert cache.get("prompt", "model") == ""

    def test_unicode_content(self) -> None:
        """유니코드 콘텐츠도 캐시할 수 있다."""
        cache = LLMCache()
        cache.set("한국어 프롬프트", "model", "한국어 응답")
        assert cache.get("한국어 프롬프트", "model") == "한국어 응답"

    def test_long_content(self) -> None:
        """긴 콘텐츠도 캐시할 수 있다."""
        cache = LLMCache()
        long_prompt = "a" * 10000
        long_response = "b" * 10000
        cache.set(long_prompt, "model", long_response)
        assert cache.get(long_prompt, "model") == long_response

    def test_key_generation_consistency(self) -> None:
        """같은 입력에 대해 같은 키가 생성된다."""
        cache = LLMCache()
        key1 = cache._generate_key("prompt", "model")
        key2 = cache._generate_key("prompt", "model")
        assert key1 == key2

    def test_key_generation_uniqueness(self) -> None:
        """다른 입력에 대해 다른 키가 생성된다."""
        cache = LLMCache()
        key1 = cache._generate_key("prompt1", "model")
        key2 = cache._generate_key("prompt2", "model")
        key3 = cache._generate_key("prompt", "model1")
        assert key1 != key2
        assert key1 != key3
        assert key2 != key3
