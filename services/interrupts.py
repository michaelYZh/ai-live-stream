from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from typing import Optional
from uuid import uuid4

from services.audio import AudioKind
from services.clients import get_redis_client


@dataclass
class InterruptResult:
    """Metadata about how the backend handled an interrupt request."""

    interrupt_id: str
    kind: AudioKind
    status: str = "queued"


@dataclass
class InterruptRecord:
    """Full record describing an interrupt awaiting processing."""

    interrupt_id: str
    kind: AudioKind
    persona: Optional[str]
    message: Optional[str]
    created_at: float
    status: str


_INTERRUPT_QUEUE_KEY = "stream:interrupts:queue"
_INTERRUPT_DATA_KEY = "stream:interrupts:data"

logger = logging.getLogger(__name__)


def register_interrupt(
    *,
    kind: AudioKind,
    persona: Optional[str],
    message: Optional[str],
) -> InterruptResult:
    """Queue a new interrupt (superchat or gift) for processing."""

    if kind == AudioKind.GENERAL:
        raise ValueError("Interrupts must be either superchat or gift.")

    client = get_redis_client()
    interrupt_id = uuid4().hex
    created_at = time.time()

    record = {
        "interrupt_id": interrupt_id,
        "kind": kind.value,
        "persona": persona,
        "message": message,
        "status": "queued",
        "created_at": created_at,
    }

    client.hset(_INTERRUPT_DATA_KEY, interrupt_id, json.dumps(record))
    client.rpush(_INTERRUPT_QUEUE_KEY, interrupt_id)
    queue_length = client.llen(_INTERRUPT_QUEUE_KEY)
    logger.info("Interrupt queue length after enqueue: %d", queue_length)

    logger.info(
        "Queued interrupt %s of kind %s for persona=%s.",
        interrupt_id,
        kind.value,
        persona or "default",
    )

    return InterruptResult(interrupt_id=interrupt_id, kind=kind, status="queued")


def pop_next_interrupt() -> Optional[InterruptRecord]:
    """Pop the next pending interrupt from the queue for processing."""

    client = get_redis_client()
    queue_length = client.llen(_INTERRUPT_QUEUE_KEY)
    logger.info("Interrupt queue length before pop: %d", queue_length)
    interrupt_id = client.lpop(_INTERRUPT_QUEUE_KEY)
    if interrupt_id is None:
        logger.debug("No pending interrupts found in queue.")
        return None

    payload = client.hget(_INTERRUPT_DATA_KEY, interrupt_id)
    if payload is None:
        logger.warning(
            "Interrupt %s missing payload in data store; skipping.",
            interrupt_id,
        )
        return None

    data = json.loads(payload)
    data["status"] = "processing"
    data["started_at"] = time.time()
    client.hset(_INTERRUPT_DATA_KEY, interrupt_id, json.dumps(data))

    logger.info(
        "Dequeued interrupt %s of kind %s for processing.",
        interrupt_id,
        data.get("kind"),
    )

    return InterruptRecord(
        interrupt_id=interrupt_id,
        kind=AudioKind(data["kind"]),
        persona=data.get("persona"),
        message=data.get("message"),
        created_at=data.get("created_at", time.time()),
        status="processing",
    )


def mark_interrupt_processed(interrupt_id: str, *, status: str = "processed") -> None:
    """Update an interrupt record to reflect completion or another terminal state."""

    client = get_redis_client()
    payload = client.hget(_INTERRUPT_DATA_KEY, interrupt_id)
    if payload is None:
        logger.debug("Interrupt %s completed but record missing in data store.", interrupt_id)
        return

    data = json.loads(payload)
    data["status"] = status
    data["completed_at"] = time.time()
    client.hset(_INTERRUPT_DATA_KEY, interrupt_id, json.dumps(data))
    logger.info("Marked interrupt %s as %s.", interrupt_id, status)


def requeue_interrupt(record: InterruptRecord) -> None:
    """Place an interrupt back onto the queue for retry."""

    client = get_redis_client()

    payload = {
        "interrupt_id": record.interrupt_id,
        "kind": record.kind.value,
        "persona": record.persona,
        "message": record.message,
        "status": record.status,
        "created_at": record.created_at,
        "retry_at": time.time(),
    }
    client.hset(_INTERRUPT_DATA_KEY, record.interrupt_id, json.dumps(payload))
    client.rpush(_INTERRUPT_QUEUE_KEY, record.interrupt_id)
    logger.info("Requeued interrupt %s onto queue.", record.interrupt_id)
