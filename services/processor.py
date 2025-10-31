from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Dict, Optional

from config import DEFAULT_GIFT_PROMPT, DEFAULT_SCRIPT, DEFAULT_STREAMER_PERSONA
from domain import AudioKind
from services.audio import enqueue_audio_chunk, reset_audio_queue
from services.clients import get_redis_client
from services.generation import agenerate_audio_with_persona, generate_script_with_llm
from services.interrupts import (
    InterruptRecord,
    mark_interrupt_processed,
    pop_next_interrupt,
    requeue_interrupt,
    reset_interrupt_state,
)
from services.history import HistoryRecord, append_history, history_snapshot, reset_history

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

SCRIPT_QUEUE_KEY = "stream:script:queue"


class StreamProcessor:
    """Core loop that converts scripts and interrupts into audio chunks."""

    def __init__(self) -> None:
        self.redis = get_redis_client()
        self.line_index = 0

    def reset_state(self) -> None:
        """Clear existing script/history entries and load defaults."""
        logger.info("Resetting stream processor state.")
        reset_audio_queue()
        reset_interrupt_state()
        reset_history()
        self._replace_script(DEFAULT_SCRIPT, AudioKind.GENERAL)
        logger.info("Stream processor state reset complete.")

    def process_once(self) -> Optional[Dict[str, object]]:
        """Process the next unit of work (interrupt or script line)."""

        interrupt = pop_next_interrupt()
        if interrupt:
            logger.info(
                "Processing interrupt %s (%s)",
                interrupt.interrupt_id,
                interrupt.kind.value,
            )
            try:
                return self._handle_interrupt(interrupt)
            except Exception:
                logger.exception(
                    "Error handling interrupt %s; requeueing.",
                    interrupt.interrupt_id,
                )
                requeue_interrupt(interrupt)
                return None
        else:
            logger.info("StreamProcessor cycle: no interrupts pending; processing script queue.")

        logger.debug("No interrupts pending; attempting to process script queue.")
        return self._handle_script_line()

    def _handle_interrupt(self, record: InterruptRecord) -> Dict[str, object]:
        if record.kind == AudioKind.SUPERCHAT:
            return self._process_superchat(record)
        if record.kind == AudioKind.GIFT:
            return self._process_gift(record)
        raise ValueError(f"Unsupported interrupt kind: {record.kind}")

    def _process_superchat(self, record: InterruptRecord) -> Dict[str, object]:
        message = record.message
        persona = record.persona

        logger.info(
            "Generating superchat audio for interrupt %s with persona %s",
            record.interrupt_id,
            persona or DEFAULT_STREAMER_PERSONA,
        )

        audio_base64 = asyncio.run(
            agenerate_audio_with_persona(
                persona,
                message,
                max_completion_tokens=1024,
                temperature=1.1,
                top_p=0.95,
                top_k=50,
                ras_win_len=None,
                raw_win_max_num_repeat=None,
            )
        )
        if message is None:
            raise ValueError("Superchat interrupt missing message transcript.")

        chunk_id = enqueue_audio_chunk(
            AudioKind.SUPERCHAT,
            audio_base64,
            transcript=message,
            speaker=persona,
        )

        logger.info("Superchat audio chunk ready: %s", chunk_id)

        history_record = HistoryRecord(
            persona=persona,
            text=message,
            kind=AudioKind.SUPERCHAT,
            chunk_id=chunk_id,
            timestamp=time.time(),
        )
        append_history(history_record)

        history_snapshot_text = history_snapshot()
        remaining_script = self._remaining_script_text()
        new_script = generate_script_with_llm(
            history_snapshot_text, message, remaining_script, persona
        )
        if new_script:
            logger.info("LLM returned new script in response to superchat interrupt.")
            self._replace_script(new_script, AudioKind.GENERAL)
        else:
            logger.info("LLM returned no follow-up script for superchat interrupt.")

        mark_interrupt_processed(record.interrupt_id, status="processed")

        return {
            "type": AudioKind.SUPERCHAT.value,
            "chunk_id": chunk_id,
            "persona": persona,
            "text": message,
        }

    def _process_gift(self, record: InterruptRecord) -> Dict[str, object]:
        # Generate a follow-up script reacting to the gift.
        history_snapshot_text = history_snapshot()
        remaining_script = self._remaining_script_text()
        new_script = generate_script_with_llm(
            history_snapshot_text, DEFAULT_GIFT_PROMPT, remaining_script
        )
        if new_script:
            logger.info(
                "LLM generated gift follow-up script for interrupt %s",
                record.interrupt_id,
            )
            self._replace_script(new_script, AudioKind.GIFT)
        else:
            logger.info(
                "LLM returned no script for gift interrupt %s",
                record.interrupt_id,
            )

        mark_interrupt_processed(record.interrupt_id, status="queued_script")

        return {
            "type": AudioKind.GIFT.value,
            "script_enqueued": bool(new_script),
        }

    def _handle_script_line(self) -> Optional[Dict[str, object]]:
        entry = self._pop_next_script_entry()
        if entry is None:
            return None

        line = entry.get("line", "").strip()
        if not line:
            return None

        speaker = line.split("[")[1].split("]")[0].strip().lower()
        line = line.split("]")[1].strip()

        logger.info(f"[{entry.get('persona')}][{speaker}] {line}")

        kind = AudioKind(entry.get("kind", AudioKind.GENERAL.value))
        persona = entry.get("persona") or DEFAULT_STREAMER_PERSONA
        # TODO: temporary
        persona = speaker

        audio_base64 = asyncio.run(
            agenerate_audio_with_persona(
                persona,
                line,
                max_completion_tokens=1024,
                temperature=1.1,
                top_p=0.95,
                top_k=50,
                ras_win_len=None,
                raw_win_max_num_repeat=None,
                valid_sampling=None,
                line_index=self.line_index,
                n=5,
            )
        )
        chunk_id = enqueue_audio_chunk(
            kind,
            audio_base64,
            transcript=line,
            speaker=persona,
        )

        history_record = HistoryRecord(
            persona=persona,
            text=line,
            kind=kind,
            chunk_id=chunk_id,
            timestamp=time.time(),
        )
        append_history(history_record)

        logger.info(
            "Generated script line audio chunk %s (%s persona %s)",
            chunk_id,
            kind.value,
            persona,
        )
        
        self.line_index += 1

        return {
            "type": kind.value,
            "chunk_id": chunk_id,
            "persona": persona,
            "text": line,
        }

    def _replace_script(self, script: str, default_kind: AudioKind) -> None:
        self.line_index = 0
        self.redis.delete(SCRIPT_QUEUE_KEY)
        lines = [line.strip() for line in script.splitlines() if line.strip()]
        if not lines:
            logger.info("Received empty script; script queue cleared.")
            return

        for line in lines:
            entry = {
                "line": line,
                "kind": default_kind.value,
                "persona": DEFAULT_STREAMER_PERSONA,
            }
            self.redis.rpush(SCRIPT_QUEUE_KEY, json.dumps(entry))

        logger.info(
            "Loaded %d lines into script queue with kind %s.",
            len(lines),
            default_kind.value,
        )

    def _pop_next_script_entry(self) -> Optional[Dict[str, object]]:
        payload = self.redis.lpop(SCRIPT_QUEUE_KEY)
        if payload is None:
            return None
        return json.loads(payload)

    def _remaining_script_text(self) -> str:
        payloads = self.redis.lrange(SCRIPT_QUEUE_KEY, 0, -1)
        lines = []
        for payload in payloads:
            entry = json.loads(payload.decode("utf-8") if isinstance(payload, bytes) else payload)
            line = entry.get("line", "").strip()
            if line:
                lines.append(line)
        logger.debug("Collected %d script lines from queue.", len(lines))
        return "\n".join(lines)
