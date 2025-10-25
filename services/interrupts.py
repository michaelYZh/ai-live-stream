from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from services.audio import AudioKind


@dataclass
class InterruptResult:
    """Metadata about how the backend handled an interrupt request."""

    interrupt_id: str
    kind: AudioKind
    status: str = "queued"


def register_interrupt(
    *,
    kind: AudioKind,
    persona: Optional[str],
    message: Optional[str],
) -> InterruptResult:
    """Queue a new interrupt (superchat or gift) for processing."""
    raise NotImplementedError("register_interrupt is not implemented yet.")
