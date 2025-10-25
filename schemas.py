from typing import Literal, Optional

from pydantic import BaseModel, Field


class TalkRequest(BaseModel):
    script: Optional[str] = Field(
        default=None,
        description="Custom script to convert to speech.",
    )

    model_config = {
        "json_schema_extra": {"examples": [{}]}
    }


class TalkResponse(BaseModel):
    script: str = Field(description="Script used for speech synthesis.")
    audio_base64: str = Field(description="Base64-encoded audio of the generated speech.")
    mime_type: str = Field(default="audio/wav", description="MIME type of the generated audio.")


class StreamerAudioRequest(BaseModel):
    block_id: str = Field(..., description="Identifier of the script block currently requested.")
    offset_seconds: float = Field(
        0.0, ge=0.0, description="Playback offset into the block in seconds where streaming should resume."
    )


class InterruptionRequest(BaseModel):
    type: Literal["superchat", "gift"] = Field(description="Kind of interruption being enqueued.")
    persona: Optional[str] = Field(
        default=None, description="Persona voice to use for the interruption (for superchats)."
    )
    message: Optional[str] = Field(default=None, description="Text to be spoken for the interruption.")
    gift_id: Optional[str] = Field(
        default=None, description="Identifier of the gift, when type is gift."
    )
    urgency: Optional[int] = Field(
        default=None,
        ge=0,
        le=10,
        description="Optional numeric urgency indicator to help prioritise interruptions.",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "type": "superchat",
                    "persona": "chinese_trump",
                    "message": "Thanks for the dono!",
                    "urgency": 5,
                }
            ]
        }
    }


class InterruptionPlanResponse(BaseModel):
    interruption_id: str = Field(description="Server-generated identifier for the interruption request.")
    type: Literal["superchat", "gift"] = Field(description="Echo of the interruption type.")
    priority: int = Field(description="Priority assigned by the backend. Lower means higher priority.")
    estimated_duration_seconds: float = Field(
        description="Estimated audio duration that will be streamed for this interruption."
    )


class InterruptionAckRequest(BaseModel):
    played_duration_seconds: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="How much audio the client actually played before acknowledging.",
    )


class InterruptionAckResponse(BaseModel):
    interruption_id: str = Field(description="Identifier of the acknowledged interruption.")
    status: Literal["acknowledged"] = Field(description="Current status for the interruption.")
