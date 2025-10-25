"""SQLite-backed persistence utilities for chat messages."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterable, Iterator

from type import Gift, Message, MessageType

DB_PATH = Path(__file__).resolve().parent.parent / "messages.db"


@contextmanager
def _connection() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    """Ensure the messages table exists."""

    with _connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                username TEXT NOT NULL,
                avatar_color TEXT NOT NULL,
                type TEXT NOT NULL,
                content TEXT,
                amount REAL,
                pinned INTEGER,
                gift_key TEXT,
                gift_name TEXT,
                gift_value INTEGER,
                gift_quantity INTEGER
            )
            """
        )


def insert_message(message: Message) -> None:
    """Persist a message instance."""

    gift = message.gift
    with _connection() as conn:
        conn.execute(
            """
            INSERT INTO messages (
                id, created_at, username, avatar_color, type, content, amount, pinned,
                gift_key, gift_name, gift_value, gift_quantity
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                message.id,
                message.created_at.isoformat(),
                message.username,
                message.avatar_color,
                message.type.value,
                message.content,
                message.amount,
                int(message.pinned) if message.pinned is not None else None,
                gift.gift_key if gift else None,
                gift.gift_name if gift else None,
                gift.value if gift else None,
                gift.quantity if gift else None,
            ),
        )


def fetch_messages() -> list[Message]:
    """Return messages ordered by creation time."""

    with _connection() as conn:
        rows = conn.execute(
            "SELECT * FROM messages ORDER BY datetime(created_at)"
        ).fetchall()

    results: list[Message] = []
    for row in rows:
        gift = None
        if row["gift_key"]:
            gift = Gift(
                gift_key=row["gift_key"],
                gift_name=row["gift_name"],
                value=row["gift_value"],
                quantity=row["gift_quantity"],
            )

        results.append(
            Message(
                id=row["id"],
                created_at=datetime.fromisoformat(row["created_at"]),
                username=row["username"],
                avatar_color=row["avatar_color"],
                type=MessageType(row["type"]),
                content=row["content"],
                amount=row["amount"],
                pinned=bool(
                    row["pinned"]) if row["pinned"] is not None else None,
                gift=gift,
            )
        )

    return results


def message_count() -> int:
    with _connection() as conn:
        (count,) = conn.execute("SELECT COUNT(*) FROM messages").fetchone()
    return int(count)


def calculate_revenue() -> tuple[float, float, float]:
    """Return total, superchat total, gift total revenue values."""

    with _connection() as conn:
        (superchat_total,) = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM messages WHERE type = ?",
            (MessageType.SUPERCHAT.value,),
        ).fetchone()
        (gift_total,) = conn.execute(
            """
            SELECT COALESCE(SUM(gift_value * gift_quantity), 0)
            FROM messages WHERE type = ? AND gift_value IS NOT NULL
            """,
            (MessageType.GIFT.value,),
        ).fetchone()

    total = float(superchat_total or 0) + float(gift_total or 0)
    return total, float(superchat_total or 0), float(gift_total or 0)


def seed_if_empty(messages: Iterable[Message]) -> None:
    with _connection() as conn:
        (count,) = conn.execute("SELECT COUNT(*) FROM messages").fetchone()
    if count:
        return

    for message in messages:
        insert_message(message)
