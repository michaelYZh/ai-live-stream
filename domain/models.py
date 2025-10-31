"""Pydantic models shared across API layers (domain level)."""

from __future__ import annotations

from datetime import datetime
from enum import Enum, StrEnum
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class APIModel(BaseModel):
    """Base model that keeps field aliases aligned with the frontend."""

    model_config = ConfigDict(populate_by_name=True)


class MessageType(str, Enum):
    """Enumerates the supported chat message variants."""
    NORMAL = "normal"
    SUPERCHAT = "superchat"
    GIFT = "gift"


class Gift(APIModel):
    gift_key: str = Field(..., alias="giftKey")
    gift_name: str = Field(..., alias="giftName")
    value: int
    quantity: int


class Message(APIModel):
    id: str
    created_at: datetime = Field(..., alias="createdAt")
    username: str
    avatar_color: str = Field(..., alias="avatarColor")
    type: MessageType
    content: Optional[str] = None
    amount: Optional[float] = None
    pinned: Optional[bool] = None
    gift: Optional[Gift] = None


class AudioKind(StrEnum):
    GENERAL = "general"
    SUPERCHAT = "superchat"
    GIFT = "gift"


class AudioChunk(APIModel):
    """Represents an audio payload queued for playback."""

    chunk_id: str = Field(description="Identifier of the audio chunk.")
    kind: AudioKind = Field(description="Category of the audio chunk.")
    transcript: str = Field(description="Transcript associated with the audio chunk.")
    speaker: str = Field(description="Persona voice associated with the audio chunk.")
    audio_base64: str = Field(description="Base64-encoded audio data.")
