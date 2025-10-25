from typing import Dict

from config import (
    PETER_GRIFFIN_REFERENCE_TRANSCRIPT,
    PETER_GRIFFIN_SYSTEM_PROMPT,
    PETER_GRIFFIN_VOICEOVER_SCRIPT,
    REFERENCE_AUDIO_PATH,
)
from schemas import TalkRequest
from .tts import synthesize_with_reference


def run(request: TalkRequest) -> Dict[str, object]:
    """Process a talk request and return the generated audio bytes."""
    script = (request.script or PETER_GRIFFIN_VOICEOVER_SCRIPT).strip()

    mime_type, audio_bytes = synthesize_with_reference(
        script,
        system_prompt=PETER_GRIFFIN_SYSTEM_PROMPT,
        reference_transcript=PETER_GRIFFIN_REFERENCE_TRANSCRIPT,
        reference_audio_path=REFERENCE_AUDIO_PATH,
    )

    return {
        "script": script,
        "mime_type": mime_type,
        "audio_bytes": audio_bytes,
    }
