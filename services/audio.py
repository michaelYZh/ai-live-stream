from __future__ import annotations

import json
from enum import StrEnum
from typing import List
from uuid import uuid4

from services.clients import get_redis_client


class AudioKind(StrEnum):
    GENERAL = "general"
    SUPERCHAT = "superchat"
    GIFT = "gift"


AUDIO_QUEUE_KEY = "stream:audio:queue"


def enqueue_audio_chunk(kind: AudioKind, audio_base64: str) -> str:
    """Store an audio chunk into Redis for later playback and return its identifier."""

    client = get_redis_client()
    chunk_id = uuid4().hex
    payload = json.dumps(
        {"chunk_id": chunk_id, "audio_base64": audio_base64, "kind": kind.value}
    )
    client.rpush(AUDIO_QUEUE_KEY, payload)
    return chunk_id


def fetch_audio_chunks() -> List[str]:
    """Fetch and remove pending audio chunks in chronological order."""

    client = get_redis_client()
    chunks: List[str] = []

    while True:
        payload = client.lpop(AUDIO_QUEUE_KEY)
        if payload is None:
            break
        data = json.loads(payload)
        chunks.append(data["audio_base64"])

    return chunks
