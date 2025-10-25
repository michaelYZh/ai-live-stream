"""Placeholder handlers for live streaming workflows."""

from __future__ import annotations

import time
import uuid
from typing import Dict, Optional

from schemas import InterruptionAckRequest, InterruptionRequest, TalkRequest

from . import pipeline


_INTERRUPTIONS: Dict[str, Dict[str, object]] = {}


def stream_main_script(block_id: str, offset_seconds: float) -> Dict[str, object]:
    """Return placeholder audio for the main streamer script."""

    # In a real implementation this would seek into the script timeline. For now we
    # just synthesize the default script via the existing pipeline helper.
    result = pipeline.run(TalkRequest())

    return {
        "block_id": block_id,
        "offset_seconds": offset_seconds,
        "mime_type": result["mime_type"],
        "audio_bytes": result["audio_bytes"],
        "script": result["script"],
    }


def register_interruption(request: InterruptionRequest) -> Dict[str, object]:
    """Register a pending interruption and return scheduling metadata."""

    interruption_id = str(uuid.uuid4())
    priority = 0 if request.type == "gift" else 5
    estimated_duration_seconds = 5.0 if request.message else 2.0

    record = {
        "id": interruption_id,
        "type": request.type,
        "persona": request.persona,
        "message": request.message,
        "gift_id": request.gift_id,
        "urgency": request.urgency,
        "priority": priority,
        "estimated_duration_seconds": estimated_duration_seconds,
        "status": "queued",
        "created_at": time.time(),
    }
    _INTERRUPTIONS[interruption_id] = record

    return {
        "interruption_id": interruption_id,
        "type": request.type,
        "priority": priority,
        "estimated_duration_seconds": estimated_duration_seconds,
    }


def generate_interruption_audio(interruption_id: str) -> Dict[str, object]:
    """Generate placeholder audio for an interruption."""

    record = _INTERRUPTIONS.get(interruption_id)
    if record is None:
        raise KeyError(interruption_id)

    if record.get("status") == "acknowledged":
        # If already acknowledged we simply yield no audio.
        return {
            "interruption_id": interruption_id,
            "mime_type": "audio/wav",
            "audio_bytes": b"",
            "script": "",
        }

    script = record.get("message")
    if not script:
        gift_label = record.get("gift_id") or "gift"
        script = f"Thanks for the {gift_label}!"

    result = pipeline.run(TalkRequest(script=script))
    record.update(
        {
            "status": "rendered",
            "estimated_duration_seconds": record.get("estimated_duration_seconds", 0.0)
            or 5.0,
        }
    )

    return {
        "interruption_id": interruption_id,
        "mime_type": result["mime_type"],
        "audio_bytes": result["audio_bytes"],
        "script": result["script"],
    }


def acknowledge_interruption(
    interruption_id: str, request: Optional[InterruptionAckRequest]
) -> Dict[str, object]:
    """Acknowledge that an interruption finished playback."""

    record = _INTERRUPTIONS.get(interruption_id)
    if record is None:
        raise KeyError(interruption_id)

    record.update(
        {
            "status": "acknowledged",
            "played_duration_seconds": request.played_duration_seconds if request else None,
            "acknowledged_at": time.time(),
        }
    )

    return {
        "interruption_id": interruption_id,
        "status": "acknowledged",
    }
