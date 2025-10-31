"""Request and response schemas for the HTTP API."""

from __future__ import annotations

from domain import APIModel, Gift, MessageType


class MessageCreate(APIModel):
    username: str
    avatarColor: str
    type: MessageType
    content: str | None = None
    amount: float | None = None
    pinned: bool | None = None
    gift: Gift | None = None


class RevenueBreakdown(APIModel):
    superchat: float
    gifts: float


class RevenueResponse(APIModel):
    total: float
    breakdown: RevenueBreakdown


class ViewCountResponse(APIModel):
    viewCount: int


class AIMessageRequest(APIModel):
    prompt: str


class AIMessageResponse(APIModel):
    message: str

