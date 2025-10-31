from __future__ import annotations

import asyncio
import base64
import logging
import os
import re
import time
import wave
from pathlib import Path
from typing import Optional

import numpy as np
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from config import (
    DEFAULT_STREAMER_PERSONA,
    LLM_MODEL,
    LLM_SYSTEM_PROMPT,
    MODIFY_SCRIPT_PROMPT_TEMPLATE,
    OUTPUT_AUDIO_DIR,
    PERSONA_REFERENCES,
    SAVE_TTS_WAV,
    TTS_MODEL,
)
from services.clients import get_boson_client

logger = logging.getLogger(__name__)


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
            logger.info("Using cached best audio for line %s.", line_index)
            return audio_b64

    system_prompt = (
        "Generate audio following instruction. Speak consistently, naturally, and continuously.\n"
        "<|scene_desc_start|>\n"
        f"{persona_info['scene_desc']}\n"
        "<|scene_desc_end|>"
    )

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
            scores = await asyncio.gather(
                *[aget_valid_score(audio_b64s[i], script) for i in range(n)]
            )
            logger.info("%s", {"scores": scores})
            best_idx = int(np.argmax(scores))
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


def save_audio_with_line_index(
    audio_b64: str, persona_key: str, line_index: Optional[int] = None
) -> None:
    if not SAVE_TTS_WAV:
        return

    OUTPUT_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    if line_index is None:
        wav_path = OUTPUT_AUDIO_DIR / f"{persona_key}_{int(time.time() * 1000)}.wav"
    else:
        existing_wavs = [
            f
            for f in os.listdir(OUTPUT_AUDIO_DIR)
            if f.startswith(f"{persona_key}_{line_index}_")
        ]
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
    logger.info("Saved audio for line %s to %s.", line_index, wav_path)


def calculate_wer(ref: str, hyp: str):
    # simple normalization

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
