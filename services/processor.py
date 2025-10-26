from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import time
import wave
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Optional

import numpy as np
from openai import max_retries
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from config import (
    DEFAULT_GIFT_PROMPT,
    DEFAULT_SCRIPT,
    DEFAULT_STREAMER_PERSONA,
    LLM_MODEL,
    OUTPUT_AUDIO_DIR,
    PERSONA_REFERENCES,
    SAVE_TTS_WAV,
    TTS_MODEL,
    LLM_SYSTEM_PROMPT,
    MODIFY_SCRIPT_PROMPT_TEMPLATE,
)
from services.audio import AudioKind, enqueue_audio_chunk, reset_audio_queue
from services.clients import get_boson_client, get_redis_client
from services.interrupts import (
    InterruptRecord,
    mark_interrupt_processed,
    pop_next_interrupt,
    requeue_interrupt,
    reset_interrupt_state,
)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

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


SCRIPT_QUEUE_KEY = "stream:script:queue"
HISTORY_KEY = "stream:history"


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
        self.redis.delete(HISTORY_KEY)
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
        self._append_history(history_record)

        history_snapshot = self._history_snapshot()
        remaining_script = self._remaining_script_text()
        new_script = generate_script_with_llm(history_snapshot, message, remaining_script, persona)
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
        history_snapshot = self._history_snapshot()
        remaining_script = self._remaining_script_text()
        new_script = generate_script_with_llm(history_snapshot, DEFAULT_GIFT_PROMPT, remaining_script)
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
        self._append_history(history_record)

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

    def _append_history(self, record: HistoryRecord) -> None:
        self.redis.rpush(HISTORY_KEY, record.to_json())
        logger.debug("Appended history entry for persona %s.", record.persona)

    def _history_snapshot(self, limit: int = 50) -> str:
        start = -limit if limit > 0 else 0
        payloads = self.redis.lrange(HISTORY_KEY, start, -1)
        records = [
            HistoryRecord.from_json(p.decode("utf-8") if isinstance(p, bytes) else p)
            for p in payloads
        ]
        history_text = "".join(f"{record.to_str()}\n" for record in records)
        logger.debug(
            "Retrieved %d history entries for snapshot (limit=%d).",
            len(records),
            limit,
        )
        return history_text

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


@retry(
    stop=stop_after_attempt(10000),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((Exception,)),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def generate_audio_with_reference(
    reference_audio_path,
    reference_transcript,
    system_prompt,
    user_prompt,
    max_completion_tokens: int = 1024,
    temperature: float = 1.0,
    top_p: float = 0.95,
    top_k: int = 50,
    ras_win_len: int = None,
    raw_win_max_num_repeat: int = None,
):
    reference_audio_path = Path(reference_audio_path)
    reference_transcript = reference_transcript.strip()

    client = get_boson_client()
    reference_b64 = base64.b64encode(reference_audio_path.read_bytes()).decode("utf-8")

    response = client.chat.completions.create(
        model=TTS_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": reference_transcript},
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "input_audio",
                        "input_audio": {
                            "data": reference_b64,
                            "format": reference_audio_path.suffix.lstrip("."),
                        },
                    }
                ],
            },
            {"role": "user", "content": user_prompt},
        ],
        modalities=["text", "audio"],
        max_completion_tokens=max_completion_tokens,
        temperature=temperature,
        top_p=top_p,
        stream=False,
        stop=["<|eot_id|>", "<|end_of_text|>", "<|audio_eos|>"],
        extra_body={
            "top_k": top_k,
            "ras_win_len": ras_win_len,
            "raw_win_max_num_repeat": raw_win_max_num_repeat,
        },
        timeout=30,
    )

    audio_b64 = response.choices[0].message.audio.data
    return audio_b64


async def agenerate_audio_with_reference(
    reference_audio_path,
    reference_transcript,
    system_prompt,
    user_prompt,
    max_completion_tokens: int = 1024,
    temperature: float = 1.0,
    top_p: float = 0.95,
    top_k: int = 50,
    ras_win_len: int = None,
    raw_win_max_num_repeat: int = None,
):
    return await asyncio.to_thread(
        generate_audio_with_reference,
        reference_audio_path,
        reference_transcript,
        system_prompt,
        user_prompt,
        max_completion_tokens,
        temperature,
        top_p,
        top_k,
        ras_win_len,
        raw_win_max_num_repeat,
    )


async def agenerate_audio_with_persona(
    persona: str,
    script: str,
    *,
    max_completion_tokens: int,
    temperature: float,
    top_p: float,
    top_k: int,
    ras_win_len: int,
    raw_win_max_num_repeat: int,
    reference_transcript: Optional[str] = None,
    reference_audio_path: Optional[Path] = None,
    valid_sampling: Optional[int] = None,
    line_index: Optional[int] = None,
    n: Optional[int] = None,
) -> str:
    """Generate audio for the given persona and script."""
    persona_key = persona.lower().replace(" ", "_")
    persona_info = PERSONA_REFERENCES.get(persona_key)

    if persona_info is None:
        persona_info = PERSONA_REFERENCES.get(DEFAULT_STREAMER_PERSONA)
        persona_key = DEFAULT_STREAMER_PERSONA

    if persona_info is None:
        raise ValueError(f"No persona reference configured for '{persona}'.")

    reference_path = Path(reference_audio_path or persona_info["path"])
    reference_transcript = (reference_transcript or persona_info["transcript"]).strip()

    if not reference_path.exists():
        raise FileNotFoundError(
            f"Reference audio not found for persona '{persona_key}': {reference_path}"
        )

    if line_index is not None:
        potential_wav = Path("assets") / "bests" / f"{persona_key}_{line_index}_best.wav"
        if potential_wav.exists():
            audio_b64 = base64.b64encode(potential_wav.read_bytes()).decode("utf-8")
            logger.info(f"Using cached best audio for line {line_index}.")
            return audio_b64

    system_prompt = f"Generate audio following instruction. Speak consistently, naturally, and continuously.\n<|scene_desc_start|>\n{persona_info['scene_desc']}\n<|scene_desc_end|>"

    if valid_sampling is not None or n is not None:
        n = valid_sampling or n
        futures = [
            agenerate_audio_with_reference(
                reference_path,
                reference_transcript,
                system_prompt,
                script,
                max_completion_tokens,
                temperature,
                top_p,
                top_k,
                ras_win_len,
                raw_win_max_num_repeat,
            )
            for _ in range(n)
        ]
        audio_b64s = await asyncio.gather(*futures)
        if valid_sampling is not None:
            scores = [
                aget_valid_score(audio_b64s[i], script) for i in range(n)
            ]
            scores = await asyncio.gather(*scores)
            logger.info(f"{scores = }")
            best_idx = np.argmax(scores)
            audio_b64 = audio_b64s[best_idx]
        else:
            audio_b64 = audio_b64s[0]
            for i in range(1, n):
                save_audio_with_line_index(audio_b64s[i], persona_key, line_index)
    else:
        audio_b64 = await agenerate_audio_with_reference(
            reference_path,
            reference_transcript,
            system_prompt,
            script,
            max_completion_tokens,
            temperature,
            top_p,
            top_k,
            ras_win_len,
            raw_win_max_num_repeat,
        )

    save_audio_with_line_index(audio_b64, persona_key, line_index)

    return audio_b64


def save_audio_with_line_index(audio_b64, persona_key: str, line_index: Optional[int] = None):
    if SAVE_TTS_WAV:
        OUTPUT_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
        if line_index is None:
            wav_path = OUTPUT_AUDIO_DIR / f"{persona_key}_{int(time.time() * 1000)}.wav"
        else:
            existing_wavs = [f for f in os.listdir(OUTPUT_AUDIO_DIR) if f.startswith(f"{persona_key}_{line_index}_")]
            if not existing_wavs:
                last_file_idx = -1
            else:
                existing_wavs.sort(key=lambda x: int(x.split("_")[-1].split(".")[0]))
                last_file_idx = int(existing_wavs[-1].split("_")[-1].split(".")[0])
            wav_path = OUTPUT_AUDIO_DIR / f"{persona_key}_{line_index}_{last_file_idx + 1}.wav"
        audio_bytes = base64.b64decode(audio_b64)
        with wave.open(str(wav_path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(24000)
            wf.writeframes(audio_bytes)
        logger.info(f"Saved audio for line {line_index} to {wav_path}.")


def calculate_wer(ref: str, hyp: str):
    # simple normalization
    import re

    def norm(s):
        return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", "", s.lower())).strip()

    r = norm(ref).split()
    h = norm(hyp).split()
    # DP edit distance with backtrace counts
    m, n = len(r), len(h)
    dp = [[(0, 0, 0, 0) for _ in range(n + 1)] for __ in range(m + 1)]  # (cost,S,D,I)
    for i in range(1, m + 1):
        dp[i][0] = (i, 0, i, 0)
    for j in range(1, n + 1):
        dp[0][j] = (j, 0, 0, j)
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if r[i - 1] == h[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                ins = dp[i][j - 1]
                ins = (ins[0] + 1, ins[1], ins[2], ins[3] + 1)
                dele = dp[i - 1][j]
                dele = (dele[0] + 1, dele[1], dele[2] + 1, dele[3])
                sub = dp[i - 1][j - 1]
                sub = (sub[0] + 1, sub[1] + 1, sub[2], sub[3])
                dp[i][j] = min(ins, dele, sub, key=lambda x: x[0])
    cost, S, D, I = dp[m][n]
    wer = cost / max(1, m)
    return {"WER": wer, "S": S, "D": D, "I": I, "N": m}


async def aget_valid_score(audio_b64, reference_transcript: str) -> float:
    # TODO: make it aysnc
    if audio_b64 is None:
        raise RuntimeError("Audio data is None.")

    client = get_boson_client()
    response = client.chat.completions.create(
        model="higgs-audio-understanding-Hackathon",
        messages=[
            {"role": "system", "content": "Transcribe this audio."},
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_audio",
                        "input_audio": {
                            "data": audio_b64,
                            "format": "wav",
                        },
                    },
                ],
            },
        ],
        max_completion_tokens=1024,
        temperature=0.0,
    )
    transcription = response.choices[0].message.content
    wer_score = calculate_wer(transcription, reference_transcript)["WER"]
    return 1 - wer_score


def generate_script_with_llm(  # pragma: no cover - stub for integration
    history: str,
    input_text: str,
    remaining_script: str,
    persona: str = None,
) -> str:
    """Generate a new script based on recent history, incoming context, and queued script."""
    streamer_persona_info = PERSONA_REFERENCES.get(DEFAULT_STREAMER_PERSONA)
    user_prompt = MODIFY_SCRIPT_PROMPT_TEMPLATE.format(
        streamer=DEFAULT_STREAMER_PERSONA,
        stramer_persona=streamer_persona_info["scene_desc"],
        speech_history=history,
        remaining_lines=remaining_script,
        superchat_sender=persona,
        superchat_message=input_text,
    )
    client = get_boson_client()
    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": LLM_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        stream=False,
        max_tokens=4096,
        temperature=0.7,
    )
    new_script = response.choices[0].message.content
    return new_script
