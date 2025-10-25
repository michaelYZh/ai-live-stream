"""Domain models shared with the FastAPI backend."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

try:  # Pydantic v2 introduces ConfigDict
    from pydantic import ConfigDict
except ImportError:  # pragma: no cover - fallback for v1
    ConfigDict = None


class APIModel(BaseModel):
    """Base model that keeps field aliases aligned with the frontend."""

    if ConfigDict is not None:  # pragma: no branch - best effort compatibility
        model_config = ConfigDict(populate_by_name=True)
    else:  # pragma: no cover - fallback for pydantic v1
        class Config:  # type: ignore[override]
            allow_population_by_field_name = True


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


__all__ = ["APIModel", "Gift", "Message", "MessageType"]
