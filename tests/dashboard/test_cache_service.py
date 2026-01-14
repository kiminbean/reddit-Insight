"""CacheService 단위 테스트."""

import time

import pytest

from reddit_insight.dashboard.services.cache_service import (
    CacheService,
    get_cache_service,
    hash_texts,
    make_analysis_key,
    make_anomaly_key,
    make_prediction_key,
    make_topics_key,
    reset_cache_service,
)


class TestCacheService:
    """CacheService 테스트 스위트."""

    @pytest.fixture
    def cache(self) -> CacheService:
        """테스트용 캐시 인스턴스를 생성한다."""
        return CacheService(default_ttl=60, max_entries=10)

    def test_set_and_get(self, cache: CacheService) -> None:
        """값을 저장하고 조회할 수 있다."""
        cache.set("key1", "value1")

        result = cache.get("key1")

        assert result == "value1"

    def test_get_nonexistent_key_returns_none(self, cache: CacheService) -> None:
        """존재하지 않는 키를 조회하면 None을 반환한다."""
        result = cache.get("nonexistent")

        assert result is None

    def test_set_with_custom_ttl(self, cache: CacheService) -> None:
        """커스텀 TTL로 값을 저장할 수 있다."""
        cache.set("key1", "value1", ttl=1)  # 1초 TTL

        # 즉시 조회하면 값이 있음
        assert cache.get("key1") == "value1"

        # 2초 후 조회하면 만료됨
        time.sleep(1.1)
        assert cache.get("key1") is None

    def test_delete_key(self, cache: CacheService) -> None:
        """키를 삭제할 수 있다."""
        cache.set("key1", "value1")

        result = cache.delete("key1")

        assert result is True
        assert cache.get("key1") is None

    def test_delete_nonexistent_key(self, cache: CacheService) -> None:
        """존재하지 않는 키를 삭제하면 False를 반환한다."""
        result = cache.delete("nonexistent")

        assert result is False

    def test_clear_cache(self, cache: CacheService) -> None:
        """모든 캐시를 삭제할 수 있다."""
        cache.set("key1", "value1")
        cache.set("key2", "value2")

        count = cache.clear()

        assert count == 2
        assert cache.get("key1") is None
        assert cache.get("key2") is None

    def test_get_or_set_returns_cached_value(self, cache: CacheService) -> None:
        """캐시에 값이 있으면 factory를 호출하지 않는다."""
        cache.set("key1", "existing")
        factory_called = False

        def factory() -> str:
            nonlocal factory_called
            factory_called = True
            return "new"

        result = cache.get_or_set("key1", factory)

        assert result == "existing"
        assert factory_called is False

    def test_get_or_set_creates_new_value(self, cache: CacheService) -> None:
        """캐시에 값이 없으면 factory를 호출하여 값을 생성한다."""

        def factory() -> str:
            return "new_value"

        result = cache.get_or_set("key1", factory)

        assert result == "new_value"
        assert cache.get("key1") == "new_value"

    def test_delete_pattern_with_prefix(self, cache: CacheService) -> None:
        """패턴과 일치하는 키를 삭제할 수 있다."""
        cache.set("analysis:python", "val1")
        cache.set("analysis:javascript", "val2")
        cache.set("prediction:python", "val3")

        count = cache.delete_pattern("analysis:*")

        assert count == 2
        assert cache.get("analysis:python") is None
        assert cache.get("analysis:javascript") is None
        assert cache.get("prediction:python") == "val3"

    def test_max_entries_eviction(self) -> None:
        """최대 엔트리 수를 초과하면 가장 오래된 엔트리가 삭제된다."""
        cache = CacheService(default_ttl=60, max_entries=3)

        cache.set("key1", "val1")
        time.sleep(0.01)
        cache.set("key2", "val2")
        time.sleep(0.01)
        cache.set("key3", "val3")
        time.sleep(0.01)
        cache.set("key4", "val4")  # 이 시점에 key1이 삭제됨

        assert cache.get("key1") is None
        assert cache.get("key2") == "val2"
        assert cache.get("key3") == "val3"
        assert cache.get("key4") == "val4"

    def test_stats(self, cache: CacheService) -> None:
        """캐시 통계를 조회할 수 있다."""
        cache.set("key1", "val1")
        cache.set("key2", "val2", ttl=0)  # 즉시 만료

        stats = cache.stats()

        assert stats["total_entries"] == 2
        assert stats["expired_entries"] == 1
        assert stats["active_entries"] == 1
        assert stats["max_entries"] == 10
        assert stats["default_ttl"] == 60

    def test_cleanup(self, cache: CacheService) -> None:
        """만료된 엔트리를 정리할 수 있다."""
        cache.set("key1", "val1", ttl=0)  # 즉시 만료
        cache.set("key2", "val2")  # 기본 TTL

        count = cache.cleanup()

        assert count == 1
        assert cache.get("key1") is None
        assert cache.get("key2") == "val2"


class TestKeyGenerators:
    """캐시 키 생성 함수 테스트."""

    def test_make_analysis_key(self) -> None:
        """분석 결과 캐시 키가 올바르게 생성된다."""
        key = make_analysis_key("Python")

        assert key == "analysis:python"

    def test_make_prediction_key(self) -> None:
        """예측 결과 캐시 키가 올바르게 생성된다."""
        key = make_prediction_key("Python", days=14)

        assert key == "prediction:python:14"

    def test_make_topics_key(self) -> None:
        """토픽 캐시 키가 올바르게 생성된다."""
        key = make_topics_key("abc123")

        assert key == "topics:abc123"

    def test_make_anomaly_key(self) -> None:
        """이상 탐지 캐시 키가 올바르게 생성된다."""
        key = make_anomaly_key("Python", method="zscore")

        assert key == "anomaly:python:zscore"

    def test_hash_texts(self) -> None:
        """텍스트 목록의 해시가 일관되게 생성된다."""
        texts = ["hello", "world"]

        hash1 = hash_texts(texts)
        hash2 = hash_texts(texts)

        assert hash1 == hash2
        assert len(hash1) == 16

    def test_hash_texts_different_for_different_texts(self) -> None:
        """다른 텍스트 목록은 다른 해시를 생성한다."""
        texts1 = ["hello", "world"]
        texts2 = ["foo", "bar"]

        hash1 = hash_texts(texts1)
        hash2 = hash_texts(texts2)

        assert hash1 != hash2


class TestSingleton:
    """싱글톤 인스턴스 테스트."""

    def setup_method(self) -> None:
        """각 테스트 전에 캐시를 리셋한다."""
        reset_cache_service()

    def test_get_cache_service_returns_same_instance(self) -> None:
        """동일한 인스턴스가 반환된다."""
        service1 = get_cache_service()
        service2 = get_cache_service()

        assert service1 is service2

    def test_reset_cache_service(self) -> None:
        """캐시 서비스를 리셋할 수 있다."""
        service1 = get_cache_service()
        service1.set("key", "value")

        reset_cache_service()

        service2 = get_cache_service()
        assert service1 is not service2
        assert service2.get("key") is None
