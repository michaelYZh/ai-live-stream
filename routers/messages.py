"""API router exposing message-related endpoints."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, status
from domain import Message
from schemas import (
    AIMessageRequest,
    AIMessageResponse,
    MessageCreate,
    RevenueBreakdown,
    RevenueResponse,
    ViewCountResponse,
)
from services.messages import (
    create_ai_message,
    create_message,
    list_messages,
    revenue_totals,
    view_count,
)

router = APIRouter(prefix="/api/v1", tags=["messages"])


@router.get("/messages", response_model=List[Message])
def fetch_messages_endpoint() -> List[Message]:
    """Return previously stored chat messages."""

    return list_messages()


@router.post("/messages", response_model=Message, status_code=status.HTTP_201_CREATED)
def create_message_endpoint(payload: MessageCreate) -> Message:
    """Store a new chat message from a viewer submission."""

    return create_message(payload)


@router.get("/revenue", response_model=RevenueResponse)
def get_revenue_endpoint() -> RevenueResponse:
    """Return livestream revenue totals and breakdown."""

    total, superchat_total, gift_total = revenue_totals()
    return RevenueResponse(
        total=total,
        breakdown=RevenueBreakdown(superchat=superchat_total, gifts=gift_total),
    )


@router.get("/view-count", response_model=ViewCountResponse)
def get_view_count_endpoint() -> ViewCountResponse:
    """Return the current estimated livestream view count."""

    return ViewCountResponse(viewCount=view_count())


@router.post("/ai/messages/", response_model=AIMessageResponse, status_code=status.HTTP_202_ACCEPTED)
def create_ai_message_endpoint(payload: AIMessageRequest) -> AIMessageResponse:
    """Generate an AI-authored message and enqueue it into the chat log."""

    message = create_ai_message(payload.prompt)
    return AIMessageResponse(message=message.content or "")
