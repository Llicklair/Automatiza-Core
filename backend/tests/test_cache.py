"""Tests del wrapper de caché Redis con degradación silenciosa.

Sin Redis disponible (caso por defecto en tests), las operaciones deben
ser no-op y el código de aplicación debe ejecutarse normalmente.
"""

import pytest

from app.services import cache


@pytest.fixture(autouse=True)
def _reset_redis_state(monkeypatch):
    """Resetea el cliente lazy entre tests para que cada uno parta limpio."""
    monkeypatch.setattr(cache, "_redis_client", None)
    monkeypatch.setattr(cache, "_redis_init_attempted", False)
    yield


async def test_cache_get_returns_none_without_redis(monkeypatch):
    monkeypatch.setattr(cache.settings, "REDIS_URL", None)
    assert await cache.cache_get("any:key") is None


async def test_cache_set_returns_false_without_redis(monkeypatch):
    monkeypatch.setattr(cache.settings, "REDIS_URL", None)
    assert await cache.cache_set("any:key", {"x": 1}, ttl_seconds=60) is False


async def test_cached_json_calls_original_when_no_cache(monkeypatch):
    monkeypatch.setattr(cache.settings, "REDIS_URL", None)

    calls = {"n": 0}

    @cache.cached_json(key=lambda *a, **k: "test:1", ttl_seconds=60)
    async def expensive():
        calls["n"] += 1
        return {"result": 42}

    # Sin caché, cada llamada ejecuta la función original.
    assert await expensive() == {"result": 42}
    assert await expensive() == {"result": 42}
    assert calls["n"] == 2


async def test_cached_json_uses_cached_value_on_hit(monkeypatch):
    """Simula un hit de caché parcheando _get_redis para devolver un fake."""

    class FakeRedis:
        def __init__(self):
            self.store: dict[str, str] = {"test:hit": '{"result": "from_cache"}'}

        async def get(self, key):
            return self.store.get(key)

        async def set(self, key, value, ex=None):
            self.store[key] = value

    fake = FakeRedis()
    monkeypatch.setattr(cache, "_get_redis", lambda: fake)

    calls = {"n": 0}

    @cache.cached_json(key=lambda *a, **k: "test:hit", ttl_seconds=60)
    async def expensive():
        calls["n"] += 1
        return {"result": "fresh"}

    # Hit: devuelve el valor cacheado, NO ejecuta la función.
    assert await expensive() == {"result": "from_cache"}
    assert calls["n"] == 0


async def test_cached_json_writes_on_miss(monkeypatch):
    """En miss, ejecuta la función y guarda el resultado."""

    class FakeRedis:
        def __init__(self):
            self.store: dict[str, str] = {}

        async def get(self, key):
            return self.store.get(key)

        async def set(self, key, value, ex=None):
            self.store[key] = value

    fake = FakeRedis()
    monkeypatch.setattr(cache, "_get_redis", lambda: fake)

    @cache.cached_json(key=lambda *a, **k: "test:miss", ttl_seconds=60)
    async def expensive():
        return {"result": "fresh"}

    # Primera llamada: miss → ejecuta y guarda.
    assert await expensive() == {"result": "fresh"}
    # El store debería tener la key con el JSON serializado.
    assert "test:miss" in fake.store
    assert '"result"' in fake.store["test:miss"]


async def test_cached_json_handles_redis_failure_gracefully(monkeypatch):
    """Si Redis lanza al hacer get, el wrapper debe ejecutar la función."""

    class BrokenRedis:
        async def get(self, key):
            raise ConnectionError("redis caído")

        async def set(self, key, value, ex=None):
            raise ConnectionError("redis caído")

    monkeypatch.setattr(cache, "_get_redis", lambda: BrokenRedis())

    @cache.cached_json(key=lambda *a, **k: "test:broken", ttl_seconds=60)
    async def expensive():
        return {"result": "fresh"}

    # No debe lanzar; degrada a comportamiento sin caché.
    assert await expensive() == {"result": "fresh"}
