from __future__ import annotations

from enum import StrEnum
from typing import List, Tuple


class AudioKind(StrEnum):
    GENERAL = "general"
    SUPERCHAT = "superchat"
    GIFT = "gift"


def enqueue_audio_chunk(kind: AudioKind, audio_base64: str) -> str:
    """Store an audio chunk into Redis for later playback and return its identifier."""
    raise NotImplementedError("enqueue_audio_chunk is not implemented yet.")


def fetch_audio_chunks(kind: AudioKind) -> List[Tuple[str, str]]:
    """Fetch and remove pending audio chunks for the given kind."""
    raise NotImplementedError("fetch_audio_chunks is not implemented yet.")
