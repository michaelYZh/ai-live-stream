from __future__ import annotations

import json
from enum import StrEnum
from typing import List, Tuple
from uuid import uuid4

from services.clients import get_redis_client


class AudioKind(StrEnum):
    GENERAL = "general"
    SUPERCHAT = "superchat"
    GIFT = "gift"


def _queue_key(kind: AudioKind) -> str:
    return f"stream:audio:{kind.value}"


def enqueue_audio_chunk(kind: AudioKind, audio_base64: str) -> str:
    """Store an audio chunk into Redis for later playback and return its identifier."""

    client = get_redis_client()
    chunk_id = uuid4().hex
    payload = json.dumps({"chunk_id": chunk_id, "audio_base64": audio_base64})
    client.rpush(_queue_key(kind), payload)
    return chunk_id


def fetch_audio_chunks(kind: AudioKind) -> List[Tuple[str, str]]:
    """Fetch and remove pending audio chunks for the given kind."""

    client = get_redis_client()
    key = _queue_key(kind)
    chunks: List[Tuple[str, str]] = []

    while True:
        payload = client.lpop(key)
        if payload is None:
            break
        data = json.loads(payload)
        chunks.append((data["chunk_id"], data["audio_base64"]))

    return chunks
