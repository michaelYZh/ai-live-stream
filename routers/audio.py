from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status
from schemas.audio import (AudioChunk, AudioEnqueueRequest, AudioFetchResponse,
                           InterruptRequest, InterruptResponse)
from services.audio import AudioKind, enqueue_audio_chunk, fetch_audio_chunks
from services.interrupts import InterruptResult, register_interrupt

router = APIRouter(prefix="/audio", tags=["audio"])


@router.get("", response_model=AudioFetchResponse)
async def pull_audio(kind: AudioKind = Query(default=AudioKind.GENERAL)) -> AudioFetchResponse:
    """Return queued audio chunks for the requested category."""

    try:
        chunks = fetch_audio_chunks(kind)
    except NotImplementedError as exc:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(exc)) from exc

    chunk_models = [
        AudioChunk(chunk_id=chunk_id, audio_base64=audio)
        for chunk_id, audio in chunks
    ]

    return AudioFetchResponse(kind=kind, chunks=chunk_models)


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def push_audio(request: AudioEnqueueRequest) -> dict:
    """Accept a new audio chunk and enqueue it for later playback."""

    try:
        chunk_id = enqueue_audio_chunk(request.kind, request.audio_base64)
    except NotImplementedError as exc:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(exc)) from exc

    return {"status": "accepted", "chunk_id": chunk_id}


@router.post("/interrupt", response_model=InterruptResponse)
async def trigger_interrupt(request: InterruptRequest) -> InterruptResponse:
    """Register an interrupt such as a superchat or gift reaction."""

    try:
        result: InterruptResult = register_interrupt(
            kind=request.kind,
            persona=request.persona,
            message=request.message,
        )
    except NotImplementedError as exc:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(exc)) from exc

    return InterruptResponse(
        interrupt_id=result.interrupt_id,
        kind=result.kind,
        status=result.status,
    )
