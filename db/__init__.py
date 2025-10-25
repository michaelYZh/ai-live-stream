"""Database access layer for the Fake Stream backend."""

from .storage import (
    calculate_revenue,
    fetch_messages,
    init_db,
    insert_message,
    message_count,
    seed_if_empty,
)

__all__ = [
    "calculate_revenue",
    "fetch_messages",
    "init_db",
    "insert_message",
    "message_count",
    "seed_if_empty",
]
