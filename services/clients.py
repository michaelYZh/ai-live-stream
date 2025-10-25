import os
from functools import lru_cache
from typing import TYPE_CHECKING, Any

from openai import OpenAI

from config import BOSON_API_KEY, BOSON_BASE_URL

try:
    import redis
except ImportError:  # pragma: no cover - handled at runtime
    redis = None  # type: ignore[assignment]

if TYPE_CHECKING:  # pragma: no cover - typing only
    from redis import Redis
else:  # pragma: no cover - typing only
    Redis = Any


@lru_cache()
def get_boson_client() -> OpenAI:
    """Return a shared OpenAI-compatible client for Boson API calls."""
    return OpenAI(api_key=BOSON_API_KEY, base_url=BOSON_BASE_URL)


@lru_cache()
def get_redis_client() -> "Redis":
    """Return a shared Redis client for caching audio and interrupts."""

    if redis is None:
        raise RuntimeError("redis package is required. Install 'redis' to enable caching.")

    url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    return redis.Redis.from_url(url, decode_responses=True)
