import base64
from pathlib import Path
from typing import Tuple

from config import TTS_MODEL
from .clients import get_boson_client


def synthesize_with_reference(
    script: str,
    *,
    system_prompt: str,
    reference_transcript: str,
    reference_audio_path: Path,
) -> Tuple[str, bytes]:
    """Call Boson AI to turn the script into cloned speech."""
    client = get_boson_client()

    if not reference_audio_path.exists():
        raise FileNotFoundError(f"Reference audio not found: {reference_audio_path}")

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
                        "input_audio": {"data": reference_b64, "format": "wav"},
                    }
                ],
            },
            {"role": "user", "content": script},
        ],
        modalities=["text", "audio"],
        max_completion_tokens=4096,
        temperature=1.0,
        top_p=0.95,
        stream=False,
        stop=["<|eot_id|>", "<|end_of_text|>", "<|audio_eos|>"],
        extra_body={"top_k": 50},
    )

    message = response.choices[0].message
    if not message.audio or not message.audio.data:
        raise RuntimeError("TTS response did not include audio data.")

    audio_bytes = base64.b64decode(message.audio.data)

    audio_format = getattr(message.audio, "format", None)
    mime_type_attr = getattr(message.audio, "mime_type", None)

    if audio_format and audio_format.lower() == "pcm":
        mime_type = "audio/pcm"
    elif mime_type_attr:
        mime_type = mime_type_attr
    elif audio_format:
        mime_type = audio_format if "/" in audio_format else f"audio/{audio_format}"
    else:
        mime_type = "audio/wav"

    return mime_type, audio_bytes
