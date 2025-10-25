"""Service layer for message-related operations."""

from __future__ import annotations

import os
import random
from datetime import datetime, timedelta, timezone
from typing import Iterable, List
from uuid import uuid4

import openai
from db import (calculate_revenue, fetch_messages, insert_message,
                message_count, seed_if_empty)
from schemas.messages import MessageCreate
from type import Gift, Message, MessageType

GIFT_CATALOG: dict[str, tuple[str, int]] = {
    "spark": ("Quantum Spark", 5),
    "heart": ("Neural Heart", 12),
    "rocket": ("Attention Rocket", 20),
}

USERNAME_COLORS = [
    "#F472B6",
    "#60A5FA",
    "#34D399",
    "#FBBF24",
    "#A855F7",
    "#F87171",
]

AI_VIEWER_NAMES = [
    "NeuralVibes",
    "TokenTide",
    "GradientGuru",
    "AttentionAddict",
    "MatrixMuse",
    "PromptPal",
]


class MessageServiceError(RuntimeError):
    """Raised when the message service cannot complete an operation."""


def build_gift(gift_key: str, quantity: int) -> Gift:
    """Return the Gift model for a given catalog entry."""
    try:
        name, value = GIFT_CATALOG[gift_key]
    except KeyError as exc:  # pragma: no cover - defensive guard
        raise MessageServiceError(f"Unknown gift type: {gift_key}") from exc
    return Gift(gift_key=gift_key, gift_name=name, value=value, quantity=quantity)


def _seed_messages(now: datetime) -> List[Message]:
    """Create the initial set of messages shown on a fresh database."""
    return [
        Message(
            id="m1",
            created_at=now - timedelta(minutes=8),
            username="transformerFan",
            avatar_color=USERNAME_COLORS[0],
            type=MessageType.SUPERCHAT,
            amount=50,
            pinned=True,
            content="Hype for the attention deep dive!",
        ),
        Message(
            id="m2",
            created_at=now - timedelta(minutes=7),
            username="grad_descent",
            avatar_color=USERNAME_COLORS[1],
            type=MessageType.NORMAL,
            content="Gradient flow is looking smooth tonight.",
        ),
        Message(
            id="m3",
            created_at=now - timedelta(minutes=6),
            username="layer_norm",
            avatar_color=USERNAME_COLORS[2],
            type=MessageType.GIFT,
            gift=build_gift("spark", 5),
            content="Layer_norm sent some sparks!",
        ),
        Message(
            id="m4",
            created_at=now - timedelta(minutes=5),
            username="token_talker",
            avatar_color=USERNAME_COLORS[3],
            type=MessageType.NORMAL,
            content="Residuals keeping the party alive.",
        ),
        Message(
            id="m5",
            created_at=now - timedelta(minutes=3),
            username="multi_head",
            avatar_color=USERNAME_COLORS[4],
            type=MessageType.SUPERCHAT,
            amount=120,
            pinned=True,
            content="Multi-head supremacy!",
        ),
        Message(
            id="m6",
            created_at=now - timedelta(minutes=2),
            username="beamSearch",
            avatar_color=USERNAME_COLORS[5],
            type=MessageType.NORMAL,
            content="Who's ready for decoding after party?",
        ),
    ]


def seed_initial_messages() -> None:
    """Populate the backing store with seed content if it is empty."""
    now = datetime.now(tz=timezone.utc)
    seed_if_empty(_seed_messages(now))


def list_messages() -> List[Message]:
    """Return all stored messages ordered as provided by the data layer."""
    return fetch_messages()


def create_message(payload: MessageCreate) -> Message:
    """Persist a user-submitted message and return the stored model."""
    message = Message(
        id=str(uuid4()),
        created_at=datetime.now(tz=timezone.utc),
        username=payload.username,
        avatar_color=payload.avatarColor,
        type=payload.type,
        content=payload.content,
        amount=payload.amount,
        pinned=payload.pinned,
        gift=payload.gift,
    )
    insert_message(message)
    return message


def revenue_totals() -> tuple[float, float, float]:
    """Return total revenue plus the superchat and gift breakdown."""
    return calculate_revenue()


def view_count(base_viewers: int = 1200, per_message: int = 5) -> int:
    """Estimate livestream view count using stored message totals."""
    additional_viewers = message_count() * per_message
    return base_viewers + additional_viewers


def _build_ai_payload(prompt: str) -> list[dict[str, str]]:
    system_prompt = (
        "You are an excitable viewer in an AI livestream chat. "
        "Reply with a single, upbeat line (max 18 words)."
    )
    user_prompt = (
        "Livestream topic: {topic}. Respond with a natural chat message reacting to the moment. "
        "Avoid emojis unless they feel essential."
    ).format(topic=prompt)
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def _extract_text(content: str | list[dict[str, str]]) -> str:
    if isinstance(content, list):
        parts: Iterable[str] = (
            part.get("text", "") for part in content if isinstance(part, dict)
        )
        return " ".join(parts).strip()
    return str(content).strip()


def _generate_ai_content(topic_prompt: str) -> str:
    api_key = os.getenv("BOSON_API_KEY")
    base_url = os.getenv("BOSON_BASE_URL", "https://hackathon.boson.ai/v1")

    if not api_key:
        return ""

    try:
        client = openai.Client(api_key=api_key, base_url=base_url)
        response = client.chat.completions.create(
            model="Qwen3-32B-non-thinking-Hackathon",
            messages=_build_ai_payload(topic_prompt),
            max_tokens=80,
            temperature=0.7,
        )
    except Exception as exc:  # pragma: no cover - guard against SDK errors
        raise MessageServiceError("Failed to generate AI message") from exc

    ai_content = response.choices[0].message.content
    return _extract_text(ai_content)


def create_ai_message(prompt: str) -> Message:
    """Generate an AI-authored message and store it alongside chat history."""
    topic_prompt = prompt.strip()

    try:
        content_text = _generate_ai_content(topic_prompt)
    except MessageServiceError:
        content_text = ""

    if not content_text:
        content_text = f"{topic_prompt} hype!" if topic_prompt else "This stream is lit!"

    username = f"{random.choice(AI_VIEWER_NAMES)}{random.randint(100, 999)}"
    avatar_color = random.choice(USERNAME_COLORS)

    message = Message(
        id=str(uuid4()),
        created_at=datetime.now(tz=timezone.utc),
        username=username,
        avatar_color=avatar_color,
        type=MessageType.NORMAL,
        content=content_text,
        amount=None,
        pinned=False,
        gift=None,
    )
    insert_message(message)

    return message


__all__ = [
    "AI_VIEWER_NAMES",
    "GIFT_CATALOG",
    "USERNAME_COLORS",
    "MessageServiceError",
    "build_gift",
    "create_ai_message",
    "create_message",
    "list_messages",
    "revenue_totals",
    "seed_initial_messages",
    "view_count",
]
