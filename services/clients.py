from __future__ import annotations
import random
from functools import lru_cache
from typing import List

import redis

from openai import OpenAI

from config import BOSON_API_KEYS, BOSON_BASE_URL, REDIS_URL

_boson_clients: List[OpenAI] = [
    OpenAI(api_key=key, base_url=BOSON_BASE_URL) for key in BOSON_API_KEYS
]


def get_boson_client() -> OpenAI:
    """Return a randomly selected cached Boson client."""
    return random.choice(_boson_clients)


@lru_cache()
def get_redis_client():
    """Return a shared Redis client for caching audio and interrupts."""
    return redis.Redis.from_url(REDIS_URL, decode_responses=True)
