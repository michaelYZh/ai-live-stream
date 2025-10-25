import base64

from typing import Optional

from fastapi import APIRouter, Body, HTTPException, status
from fastapi.responses import StreamingResponse

from schemas import (
    InterruptionAckRequest,
    InterruptionAckResponse,
    InterruptionPlanResponse,
    InterruptionRequest,
    StreamerAudioRequest,
    TalkRequest,
    TalkResponse,
)
from services import live_stream, pipeline

router = APIRouter(prefix="/talk", tags=["talk"])


@router.post("", response_model=TalkResponse)
async def talk(request: TalkRequest) -> TalkResponse:
    """Generate audio and return it as base64."""
    try:
        result = pipeline.run(request)
    except NotImplementedError as exc:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(exc)
        ) from exc

    return TalkResponse(
        script=result["script"],
        audio_base64=base64.b64encode(result["audio_bytes"]).decode("utf-8"),
        mime_type=result["mime_type"],
    )


@router.post("/stream")
async def talk_stream(request: TalkRequest) -> StreamingResponse:
    """Generate audio and stream it back to the caller."""
    try:
        result = pipeline.run(request)
    except NotImplementedError as exc:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(exc)
        ) from exc

    def iter_audio():
        yield result["audio_bytes"]

    headers = {"X-Generated-Script": result["script"]}

    return StreamingResponse(iter_audio(), media_type=result["mime_type"], headers=headers)


@router.post("/streamer/audio")
async def streamer_audio(request: StreamerAudioRequest) -> StreamingResponse:
    """Stream the main script audio for the performer."""

    try:
        result = live_stream.stream_main_script(
            block_id=request.block_id, offset_seconds=request.offset_seconds
        )
    except NotImplementedError as exc:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(exc)
        ) from exc

    def iter_audio():
        yield result["audio_bytes"]

    headers = {
        "X-Stream-Block-Id": result.get("block_id", request.block_id),
        "X-Stream-Offset": str(result.get("offset_seconds", request.offset_seconds)),
        "X-Stream-Script": result.get("script", ""),
    }

    return StreamingResponse(iter_audio(), media_type=result.get("mime_type", "audio/wav"), headers=headers)


@router.post("/interruption", response_model=InterruptionPlanResponse)
async def register_interruption(request: InterruptionRequest) -> InterruptionPlanResponse:
    """Register a superchat or gift interruption request."""

    try:
        result = live_stream.register_interruption(request)
    except NotImplementedError as exc:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(exc)
        ) from exc

    return InterruptionPlanResponse(**result)


@router.get("/interruption/{interruption_id}/audio")
async def interruption_audio(interruption_id: str) -> StreamingResponse:
    """Stream generated audio for an interruption."""

    try:
        result = live_stream.generate_interruption_audio(interruption_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Interruption {interruption_id} was not found.",
        ) from exc
    except NotImplementedError as exc:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(exc)
        ) from exc

    def iter_audio():
        yield result["audio_bytes"]

    headers = {
        "X-Interruption-Id": result.get("interruption_id", interruption_id),
        "X-Interruption-Script": result.get("script", ""),
    }

    return StreamingResponse(iter_audio(), media_type=result.get("mime_type", "audio/wav"), headers=headers)


@router.post(
    "/interruption/{interruption_id}/ack",
    response_model=InterruptionAckResponse,
)
async def acknowledge_interruption(
    interruption_id: str,
    request: Optional[InterruptionAckRequest] = Body(default=None),
) -> InterruptionAckResponse:
    """Mark an interruption as fully played back on the client."""

    try:
        result = live_stream.acknowledge_interruption(interruption_id, request)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Interruption {interruption_id} was not found.",
        ) from exc
    except NotImplementedError as exc:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(exc)
        ) from exc

    return InterruptionAckResponse(**result)
