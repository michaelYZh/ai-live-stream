import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(override=True)

BOSON_API_KEY = os.environ["BOSON_API_KEY"]
BOSON_BASE_URL = os.getenv("BOSON_BASE_URL", "https://hackathon.boson.ai/v1")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

ROOT_DIR = Path(__file__).resolve().parent
ASSETS_DIR = ROOT_DIR / "assets"
REFERENCE_AUDIO_DIR = ASSETS_DIR / "reference_audio"

TTS_MODEL = os.getenv("TTS_MODEL", "higgs-audio-generation-Hackathon")
LLM_MODEL = os.getenv("LLM_MODEL", "Qwen3-32B-non-thinking-Hackathon")
DEFAULT_STREAMER_PERSONA = os.getenv("DEFAULT_STREAMER_PERSONA", "speed")
DEFAULT_GIFT_PROMPT = os.getenv(
    "DEFAULT_GIFT_PROMPT",
    "A viewer just sent a gift during the livestream. React with excitement and keep the energy high!",
)

PETER_GRIFFIN_REFERENCE_TRANSCRIPT = """
I walked into the kitchen and sat down at the table. I looked with a Grimace at the questionable meal Lois
had placed in front of me. Of course I'd never tell her how disgusted I was with her cooking, but somehow I think she knew.
Lois had always been full of energy and life, but lately I had begun to grow more aware of her aging. The bright exuberant
eyes that I had fallen in love with were now beginning to grow dull and listless with the long fatigue of a weary life.
"""

SPEED_REFERENCE_TRANSCRIPT = """
This is our first China stream, y'all! We are, bro chat, we actually here, bro! We are actually here. 
Chat, when I told y'all, bro, when I tell y'all I've been wanting to go to China since I was a kid, bro! 
So Chat, this is honestly crazy cuz Chat, we learned so much about China at school.
"""

CHINESE_TRUMP_REFERENCE_TRANSCRIPT = """
They tried to steal my account, they tried to silence me, they want me gone, they want me disappear. 
But guess what? They almost hit me. That was a close one, but they always miss. 
Now I'm back! Stronger, louder, and funnier than ever.
"""

SPONGEBOB_REFERENCE_TRANSCRIPT = """
All right! Ooops! I guess I rip my pants again. I'm on my way! Ready for another great day together, friend.
Hey, guys! Better pack some ice. It's gonna be a hot one. What is that smell.
"""

DEFAULT_SCRIPT = """
Yo chat, this dude built like a Wi-Fi signal, bruh. 
Strong for two seconds, then start laggin' outta nowhere, man! 
Like bro, sit yo goofy self down before the webcam file for trauma insurance, dawg!
"""

PERSONA_REFERENCES = {
    "speed": {
        "path": REFERENCE_AUDIO_DIR / "speed_voice.wav",
        "transcript": SPEED_REFERENCE_TRANSCRIPT,
    },
    "chinese_trump": {
        "path": REFERENCE_AUDIO_DIR / "chinese_trump_voice.wav",
        "transcript": CHINESE_TRUMP_REFERENCE_TRANSCRIPT,
    },
    "peter_griffin": {
        "path": REFERENCE_AUDIO_DIR / "peter_griffin_voice.wav",
        "transcript": PETER_GRIFFIN_REFERENCE_TRANSCRIPT,
    },
    "spongebob": {
        "path": REFERENCE_AUDIO_DIR / "spongebob_voice.wav",
        "transcript": SPONGEBOB_REFERENCE_TRANSCRIPT,
    },
}
