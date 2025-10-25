import base64

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from schemas import TalkRequest, TalkResponse
from services import pipeline

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
