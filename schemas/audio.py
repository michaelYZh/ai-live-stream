from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field, model_validator
from services.audio import AudioKind


class AudioEnqueueRequest(BaseModel):
    kind: AudioKind = Field(description="Category of audio being enqueued.")
    audio_base64: str = Field(description="Base64-encoded audio chunk.")
    transcript: str = Field(description="Text transcript associated with the audio chunk.")


class AudioChunk(BaseModel):
    chunk_id: str = Field(description="Identifier of the audio chunk.")
    kind: AudioKind = Field(description="Category of the audio chunk.")
    audio_base64: str = Field(description="Base64-encoded audio data.")
    transcript: str = Field(description="Transcript associated with the audio chunk.")


class AudioFetchResponse(BaseModel):
    chunks: List[AudioChunk] = Field(
        default_factory=list,
        description="Ordered collection of pending audio chunks ready for playback.",
    )


class InterruptRequest(BaseModel):
    kind: AudioKind = Field(
        description="Type of interrupt to trigger (superchat or gift).")
    persona: Optional[str] = Field(
        default=None,
        description="Persona voice identifier to use when synthesizing the interrupt.",
    )
    message: Optional[str] = Field(
        default=None,
        description="Text content for the interrupt (required for superchats).",
    )

    @model_validator(mode="after")
    def validate_superchat(cls, values: "InterruptRequest") -> "InterruptRequest":
        if values.kind == AudioKind.GENERAL:
            raise ValueError("kind must be superchat or gift for interrupts")
        if values.kind == AudioKind.SUPERCHAT:
            if not values.message:
                raise ValueError("message is required when kind is superchat")
            if not values.persona:
                raise ValueError("persona is required when kind is superchat")
        return values


class InterruptResponse(BaseModel):
    interrupt_id: str = Field(
        description="Identifier assigned to the registered interrupt.")
    kind: AudioKind = Field(description="Kind of interrupt that was queued.")
    status: str = Field(
        description="Current status of the interrupt request (e.g. queued).")
