from __future__ import annotations

import logging

from fastapi import APIRouter, status

from schemas import AudioEnqueueRequest, AudioFetchResponse, InterruptRequest, InterruptResponse
from services.audio import AudioKind, enqueue_audio_chunk, fetch_audio_chunks
from services.interrupts import InterruptResult, register_interrupt

router = APIRouter(prefix="/audio", tags=["audio"])
logger = logging.getLogger(__name__)


@router.get("", response_model=AudioFetchResponse)
async def pull_audio() -> AudioFetchResponse:
    """Return queued audio chunks in playback order."""

    chunks = fetch_audio_chunks()
    logger.info("Fetched %d audio chunks from queue.", len(chunks))

    return AudioFetchResponse(chunks=chunks)


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def push_audio(request: AudioEnqueueRequest) -> dict:
    """Accept a new audio chunk and enqueue it for later playback."""

    chunk_id = enqueue_audio_chunk(request.kind, request.audio_base64)
    logger.info("Received audio chunk %s via push for kind %s.", chunk_id, request.kind.value)

    return {"status": "accepted", "chunk_id": chunk_id}


@router.post("/interrupt", response_model=InterruptResponse)
async def trigger_interrupt(request: InterruptRequest) -> InterruptResponse:
    """Register an interrupt such as a superchat or gift reaction."""

    result: InterruptResult = register_interrupt(
        kind=request.kind,
        persona=request.persona,
        message=request.message,
    )
    logger.info(
        "Registered %s interrupt %s for persona %s.",
        request.kind.value,
        result.interrupt_id,
        request.persona or "default",
    )

    return InterruptResponse(
        interrupt_id=result.interrupt_id,
        kind=result.kind,
        status=result.status,
    )
