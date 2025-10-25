from __future__ import annotations

import base64
import json
import time
import wave
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional

from config import (
    DEFAULT_GIFT_PROMPT,
    DEFAULT_SCRIPT,
    DEFAULT_STREAMER_PERSONA,
    OUTPUT_AUDIO_DIR,
    PERSONA_REFERENCES,
    SAVE_TTS_WAV,
    TTS_MODEL,
)
from services.audio import AudioKind, enqueue_audio_chunk
from services.clients import get_boson_client, get_redis_client
from services.interrupts import (
    InterruptRecord,
    mark_interrupt_processed,
    pop_next_interrupt,
)


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

    @classmethod
    def from_json(cls, payload: str) -> "HistoryRecord":
        data = json.loads(payload)
        data["kind"] = AudioKind(data["kind"])
        return cls(**data)


SCRIPT_QUEUE_KEY = "stream:script:queue"
HISTORY_KEY = "stream:history"


class StreamProcessor:
    """Core loop that converts scripts and interrupts into audio chunks."""

    def __init__(self) -> None:
        self.redis = get_redis_client()

    def process_once(self) -> Optional[Dict[str, object]]:
        """Process the next unit of work (interrupt or script line)."""

        interrupt = pop_next_interrupt()
        if interrupt:
            return self._handle_interrupt(interrupt)

        return self._handle_script_line()

    def _handle_interrupt(self, record: InterruptRecord) -> Dict[str, object]:
        if record.kind == AudioKind.SUPERCHAT:
            return self._process_superchat(record)
        if record.kind == AudioKind.GIFT:
            return self._process_gift(record)
        raise ValueError(f"Unsupported interrupt kind: {record.kind}")

    def _process_superchat(self, record: InterruptRecord) -> Dict[str, object]:
        message = record.message or ""
        persona = record.persona or DEFAULT_STREAMER_PERSONA

        audio_base64 = generate_audio_with_persona(
            persona,
            message,
            max_completion_tokens=1024,
            temperature=1.1,
            ras_win_len=100,
            raw_win_max_num_repeat=20,
        )
        chunk_id = enqueue_audio_chunk(AudioKind.SUPERCHAT, audio_base64)
        history_record = HistoryRecord(
            persona=persona,
            text=message,
            kind=AudioKind.SUPERCHAT,
            chunk_id=chunk_id,
            timestamp=time.time(),
        )
        self._append_history(history_record)

        new_script = generate_script_with_llm(self._history_snapshot(), message)
        if new_script:
            self._replace_script(new_script, AudioKind.GENERAL)

        mark_interrupt_processed(record.interrupt_id, status="processed")

        return {
            "type": AudioKind.SUPERCHAT.value,
            "chunk_id": chunk_id,
            "persona": persona,
            "text": message,
        }

    def _process_gift(self, record: InterruptRecord) -> Dict[str, object]:
        # Generate a follow-up script reacting to the gift.
        new_script = generate_script_with_llm(self._history_snapshot(), DEFAULT_GIFT_PROMPT)
        if new_script:
            self._replace_script(new_script, AudioKind.GIFT)

        mark_interrupt_processed(record.interrupt_id, status="queued_script")

        return {
            "type": AudioKind.GIFT.value,
            "script_enqueued": bool(new_script),
        }

    def _handle_script_line(self) -> Optional[Dict[str, object]]:
        entry = self._pop_next_script_entry()
        if entry is None:
            # Reload the default script and try again.
            self._replace_script(DEFAULT_SCRIPT, AudioKind.GENERAL)
            entry = self._pop_next_script_entry()
            if entry is None:
                return None

        line = entry.get("line", "").strip()
        if not line:
            return None

        kind = AudioKind(entry.get("kind", AudioKind.GENERAL.value))
        persona = entry.get("persona") or DEFAULT_STREAMER_PERSONA

        audio_base64 = generate_audio_with_persona(
            persona,
            line,
            max_completion_tokens=1024,
            temperature=1.1,
            ras_win_len=100,
            raw_win_max_num_repeat=20,
        )
        chunk_id = enqueue_audio_chunk(kind, audio_base64)

        history_record = HistoryRecord(
            persona=persona,
            text=line,
            kind=kind,
            chunk_id=chunk_id,
            timestamp=time.time(),
        )
        self._append_history(history_record)

        return {
            "type": kind.value,
            "chunk_id": chunk_id,
            "persona": persona,
            "text": line,
        }

    def _replace_script(self, script: str, default_kind: AudioKind) -> None:
        self.redis.delete(SCRIPT_QUEUE_KEY)
        lines = [line.strip() for line in script.splitlines() if line.strip()]
        if not lines:
            return

        for line in lines:
            entry = {
                "line": line,
                "kind": default_kind.value,
                "persona": DEFAULT_STREAMER_PERSONA,
            }
            self.redis.rpush(SCRIPT_QUEUE_KEY, json.dumps(entry))

    def _pop_next_script_entry(self) -> Optional[Dict[str, object]]:
        payload = self.redis.lpop(SCRIPT_QUEUE_KEY)
        if payload is None:
            return None
        return json.loads(payload)

    def _append_history(self, record: HistoryRecord) -> None:
        self.redis.rpush(HISTORY_KEY, record.to_json())

    def _history_snapshot(self, limit: int = 50) -> List[HistoryRecord]:
        start = -limit if limit > 0 else 0
        payloads = self.redis.lrange(HISTORY_KEY, start, -1)
        return [HistoryRecord.from_json(p) for p in payloads]


def generate_audio_with_persona(
    persona: str,
    script: str,
    *,
    max_completion_tokens: int,
    temperature: float,
    ras_win_len: int,
    raw_win_max_num_repeat: int,
    reference_transcript: Optional[str] = None,
    reference_audio_path: Optional[Path] = None,
) -> str:
    """Generate audio for the given persona and script."""
    persona_key = persona.lower().replace(" ", "_")
    persona_info = PERSONA_REFERENCES.get(persona_key)

    if persona_info is None:
        persona_info = PERSONA_REFERENCES.get(DEFAULT_STREAMER_PERSONA)
        persona_key = DEFAULT_STREAMER_PERSONA

    if persona_info is None:
        raise ValueError(f"No persona reference configured for '{persona}'.")

    reference_path = Path(
        reference_audio_path or persona_info["path"]
    )
    transcript = (reference_transcript or persona_info["transcript"]).strip()

    if not reference_path.exists():
        raise FileNotFoundError(f"Reference audio not found for persona '{persona_key}': {reference_path}")

    client = get_boson_client()
    reference_b64 = base64.b64encode(reference_path.read_bytes()).decode("utf-8")

    response = client.chat.completions.create(
        model=TTS_MODEL,
        messages=[
            {"role": "user", "content": transcript},
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "input_audio",
                        "input_audio": {"data": reference_b64, "format": "wav"},
                    }
                ],
            },
            {"role": "user", "content": script},
        ],
        modalities=["text", "audio"],
        max_completion_tokens=max_completion_tokens,
        temperature=temperature,
        top_p=0.95,
        stream=False,
        stop=["<|eot_id|>", "<|end_of_text|>", "<|audio_eos|>"],
        extra_body={
            "top_k": 50,
            "ras_win_len": ras_win_len,
            "raw_win_max_num_repeat": raw_win_max_num_repeat,
        },
    )

    message = response.choices[0].message
    if not getattr(message, "audio", None) or not message.audio.data:
        raise RuntimeError("TTS response did not include audio data.")

    audio_b64 = message.audio.data

    if SAVE_TTS_WAV:
        OUTPUT_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
        wav_path = OUTPUT_AUDIO_DIR / f"{persona_key}_{int(time.time() * 1000)}.wav"
        audio_bytes = base64.b64decode(audio_b64)
        with wave.open(str(wav_path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(24000)
            wf.writeframes(audio_bytes)

    return audio_b64


def generate_script_with_llm(  # pragma: no cover - stub for integration
    history: List[HistoryRecord],
    input_text: str,
) -> str:
    """Generate a new script based on history and incoming context."""
    raise NotImplementedError("generate_script_with_llm must be implemented with LLM logic.")
