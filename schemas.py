from typing import Optional

from pydantic import BaseModel, Field


class TalkRequest(BaseModel):
    script: Optional[str] = Field(
        default=None,
        description="Custom script to convert to speech. Defaults to the Peter Griffin voiceover.",
    )

    model_config = {
        "json_schema_extra": {"examples": [{}]}
    }


class TalkResponse(BaseModel):
    script: str = Field(description="Script used for speech synthesis.")
    audio_base64: str = Field(description="Base64-encoded audio of the generated speech.")
    mime_type: str = Field(default="audio/wav", description="MIME type of the generated audio.")
