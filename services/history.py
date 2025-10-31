from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Iterable

from domain import AudioKind
from services.clients import get_redis_client

HISTORY_KEY = "stream:history"


@dataclass
class HistoryRecord:
    """Represents a single line that has been spoken on stream."""

    persona: str
    text: str
    kind: AudioKind
    chunk_id: str
    timestamp: float

    def to_json(self) -> str:
        data = asdict(self)
        data["kind"] = self.kind.value
        return json.dumps(data)

    def to_str(self) -> str:
        """Render record text for LLM consumption."""
        return f"[{self.persona}] {self.text}"

    @classmethod
    def from_json(cls, payload: str) -> "HistoryRecord":
        data = json.loads(payload)
        data["kind"] = AudioKind(data["kind"])
        return cls(**data)


def reset_history() -> None:
    """Clear all stored history entries."""

    redis = get_redis_client()
    redis.delete(HISTORY_KEY)


def append_history(record: HistoryRecord) -> None:
    """Append a history record to the Redis-backed log."""

    redis = get_redis_client()
    redis.rpush(HISTORY_KEY, record.to_json())


def history_snapshot(*, limit: int = 50) -> str:
    """Return a textual snapshot of the most recent history entries."""

    redis = get_redis_client()
    start = -limit if limit > 0 else 0
    payloads: Iterable[str] = redis.lrange(HISTORY_KEY, start, -1)
    records = [
        HistoryRecord.from_json(p.decode("utf-8") if isinstance(p, bytes) else p)
        for p in payloads
    ]
    return "".join(f"{record.to_str()}\n" for record in records)
