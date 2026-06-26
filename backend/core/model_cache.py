"""Model cache with TTL, LRU eviction, and circuit breaker pattern.

FAANG-grade model serving requires:
- Cache models to avoid redundant loads
- Circuit breaker to fail fast when models are down
- TTL-based cache invalidation
- Graceful degradation when models unavailable
"""

import logging
import time
from collections.abc import Callable
from threading import Lock
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CircuitBreaker:
    """Circuit breaker pattern: trips after N failures, resets after timeout."""

    def __init__(self, name: str, failure_threshold: int = 3, reset_timeout: float = 30.0):
        self._name = name
        self._failure_threshold = failure_threshold
        self._reset_timeout = reset_timeout
        self._failure_count = 0
        self._state = "closed"  # closed, open, half-open
        self._last_failure_time = 0.0
        self._lock = Lock()

    def call(self, fn: Callable[..., T], *args, **kwargs) -> tuple[bool, T | None, str | None]:
        with self._lock:
            if self._state == "open":
                if time.monotonic() - self._last_failure_time > self._reset_timeout:
                    self._state = "half-open"
                    logger.info(f"Circuit breaker '{self._name}' half-open, attempting reset")
                else:
                    return False, None, f"Circuit breaker '{self._name}' is OPEN"

        try:
            result = fn(*args, **kwargs)
            with self._lock:
                self._failure_count = 0
                if self._state == "half-open":
                    self._state = "closed"
                    logger.info(f"Circuit breaker '{self._name}' reset to closed")
            return True, result, None
        except Exception as e:
            with self._lock:
                self._failure_count += 1
                self._last_failure_time = time.monotonic()
                if self._failure_count >= self._failure_threshold:
                    self._state = "open"
                    logger.warning(f"Circuit breaker '{self._name}' TRIPPED (failures={self._failure_count})")
            return False, None, str(e)


class ModelCache:
    """Thread-safe LRU cache with TTL for loaded ML models.

    Usage:
        cache = ModelCache(max_size=10, default_ttl=300)
        model = cache.get_or_load("bed_model", lambda: joblib.load("bed_model.pkl"))
    """

    def __init__(self, max_size: int = 10, default_ttl: float = 300.0):
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._cache: dict[str, tuple[Any, float, float]] = {}  # key -> (value, expiry, size)
        self._lock = Lock()

    def get(self, key: str) -> Any | None:
        with self._lock:
            if key not in self._cache:
                return None
            value, expiry, _ = self._cache[key]
            if time.monotonic() > expiry:
                del self._cache[key]
                logger.info(f"Cache expired: {key}")
                return None
            return value

    def set(self, key: str, value: Any, ttl: float | None = None):
        ttl = ttl or self._default_ttl
        expiry = time.monotonic() + ttl
        with self._lock:
            if len(self._cache) >= self._max_size:
                oldest = min(self._cache.keys(), key=lambda k: self._cache[k][1])
                del self._cache[oldest]
                logger.info(f"Cache evicted: {oldest} (max_size={self._max_size})")
            self._cache[key] = (value, expiry, 1)

    def get_or_load(self, key: str, loader: Callable[[], Any], ttl: float | None = None) -> Any:
        cached = self.get(key)
        if cached is not None:
            return cached
        value = loader()
        self.set(key, value, ttl)
        return value

    def invalidate(self, key: str):
        with self._lock:
            self._cache.pop(key, None)

    def clear(self):
        with self._lock:
            self._cache.clear()

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._cache)

    @property
    def keys(self) -> list:
        with self._lock:
            return list(self._cache.keys())


# Global singleton
_cache: ModelCache | None = None
_circuit_breakers: dict[str, CircuitBreaker] = {}


def get_model_cache() -> ModelCache:
    global _cache
    if _cache is None:
        _cache = ModelCache(max_size=20, default_ttl=600)
    return _cache


def get_circuit_breaker(name: str) -> CircuitBreaker:
    if name not in _circuit_breakers:
        _circuit_breakers[name] = CircuitBreaker(name)
    return _circuit_breakers[name]
