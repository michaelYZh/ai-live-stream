from __future__ import annotations

import json
from enum import StrEnum
from typing import Dict, List

from services.clients import get_redis_client


class AudioKind(StrEnum):
    GENERAL = "general"
    SUPERCHAT = "superchat"
    GIFT = "gift"


AUDIO_QUEUE_KEY = "stream:audio:queue"
AUDIO_CHUNK_COUNTER_KEY = "stream:audio:next_chunk_id"


def enqueue_audio_chunk(
    kind: AudioKind,
    audio_base64: str,
    transcript: str,
    speaker: str,
) -> str:
    """Store an audio chunk into Redis for later playback and return its identifier."""

    client = get_redis_client()
    chunk_id = str(client.incr(AUDIO_CHUNK_COUNTER_KEY))
    payload = json.dumps(
        {
            "chunk_id": chunk_id,
            "audio_base64": audio_base64,
            "kind": kind.value,
            "transcript": transcript,
            "speaker": speaker,
        }
    )
    client.rpush(AUDIO_QUEUE_KEY, payload)
    return chunk_id


def fetch_audio_chunks() -> List[Dict[str, object]]:
    """Fetch and remove pending audio chunks in chronological order."""

    client = get_redis_client()
    chunks: List[Dict[str, object]] = []

    while True:
        payload = client.lpop(AUDIO_QUEUE_KEY)
        if payload is None:
            break

        data = json.loads(payload)
        transcript = data.get("transcript")
        if transcript is None:
            raise ValueError("Audio chunk payload missing transcript.")

        speaker = data.get("speaker")
        if speaker is None:
            raise ValueError("Audio chunk payload missing speaker.")

        try:
            kind = AudioKind(data.get("kind", AudioKind.GENERAL.value))
        except ValueError:
            kind = AudioKind.GENERAL

        chunk_id = data.get("chunk_id")
        if chunk_id is None:
            raise ValueError("Audio chunk payload missing chunk_id.")

        chunks.append(
            {
                "chunk_id": str(chunk_id),
                "audio_base64": data.get("audio_base64", ""),
                "kind": kind,
                "transcript": transcript,
                "speaker": speaker,
            }
        )

    return chunks


def count_audio_chunks() -> int:
    """Return the number of pending audio chunks without modifying the queue."""

    client = get_redis_client()
    return client.llen(AUDIO_QUEUE_KEY)


def reset_audio_queue() -> None:
    """Remove any pending audio chunks from the queue."""

    client = get_redis_client()
    client.delete(AUDIO_QUEUE_KEY, AUDIO_CHUNK_COUNTER_KEY)
