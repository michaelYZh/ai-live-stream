"""In-memory persistence utilities for chat messages."""

from __future__ import annotations

from typing import Iterable, List

from type import Gift, Message, MessageType


_MESSAGES: List[Message] = []


def _copy_message(message: Message) -> Message:
    """Return a deep copy so callers cannot mutate stored state."""

    return message.copy(deep=True)  # type: ignore[call-arg]


def init_db() -> None:  # pragma: no cover - retained for compatibility
    """Initialize the in-memory store (no-op for compatibility)."""

    # Nothing to do—store lives for the process lifetime.


def insert_message(message: Message) -> None:
    """Persist a message instance in memory."""

    _MESSAGES.append(_copy_message(message))


def fetch_messages() -> list[Message]:
    """Return messages ordered by creation time."""

    return sorted((_copy_message(msg) for msg in _MESSAGES), key=lambda m: m.created_at)


def message_count() -> int:
    """Return total number of stored messages."""

    return len(_MESSAGES)


def calculate_revenue() -> tuple[float, float, float]:
    """Return total, superchat total, gift total revenue values."""

    superchat_total = sum((msg.amount or 0.0) for msg in _MESSAGES if msg.type == MessageType.SUPERCHAT)
    gift_total = 0.0
    for msg in _MESSAGES:
        if msg.type == MessageType.GIFT and msg.gift is not None:
            gift: Gift = msg.gift
            gift_total += float(gift.value or 0) * float(gift.quantity or 0)

    total = float(superchat_total) + float(gift_total)
    return float(total), float(superchat_total), float(gift_total)


def seed_if_empty(messages: Iterable[Message]) -> None:
    """Populate the store with defaults if it is empty."""

    if _MESSAGES:
        return

    for message in messages:
        insert_message(message)


__all__ = [
    "calculate_revenue",
    "fetch_messages",
    "init_db",
    "insert_message",
    "message_count",
    "seed_if_empty",
]
