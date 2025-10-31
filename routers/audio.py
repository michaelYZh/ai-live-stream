from __future__ import annotations

import logging

from fastapi import APIRouter, status

from schemas import (
    AudioFetchResponse,
    InterruptRequest,
    InterruptResponse,
)
from services.audio import count_audio_chunks, fetch_audio_chunks
from services.interrupts import InterruptResult, register_interrupt

router = APIRouter(prefix="/api/v1", tags=["audio"])
logger = logging.getLogger(__name__)


@router.get("/audio", response_model=AudioFetchResponse, status_code=status.HTTP_200_OK)
async def pull_audio() -> AudioFetchResponse:
    """Return queued audio chunks in playback order."""

    raw_chunks = fetch_audio_chunks()
    logger.info("Fetched %d audio chunks from queue.", len(raw_chunks))

    return AudioFetchResponse(chunks=raw_chunks)


@router.get("/count", status_code=status.HTTP_200_OK)
async def audio_queue_count() -> dict:
    """Return the number of pending audio chunks."""

    count = count_audio_chunks()
    logger.info("Audio queue count requested: %d", count)
    return {"count": count}


@router.post(
    "/interrupt",
    response_model=InterruptResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
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
