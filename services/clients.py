from functools import lru_cache
from openai import OpenAI
from config import BOSON_API_KEY, BOSON_BASE_URL, REDIS_URL
import redis


@lru_cache()
def get_boson_client() -> OpenAI:
    """Return a shared OpenAI-compatible client for Boson API calls."""
    return OpenAI(api_key=BOSON_API_KEY, base_url=BOSON_BASE_URL)


@lru_cache()
def get_redis_client() -> "Redis":
    """Return a shared Redis client for caching audio and interrupts."""
    return redis.Redis.from_url(REDIS_URL, decode_responses=True)
