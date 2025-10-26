import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(override=True)

BOSON_API_KEYS = os.getenv("BOSON_API_KEYS", "").split(",")
if not BOSON_API_KEYS:
    raise RuntimeError(
        "BOSON_API_KEYS must be set in the environment."
    )
BOSON_BASE_URL = os.getenv("BOSON_BASE_URL", "https://hackathon.boson.ai/v1")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

ROOT_DIR = Path(__file__).resolve().parent
ASSETS_DIR = ROOT_DIR / "assets"
REFERENCE_AUDIO_DIR = ASSETS_DIR / "reference_audio"
OUTPUT_AUDIO_DIR = ROOT_DIR / "output"

TTS_MODEL = os.getenv("TTS_MODEL", "higgs-audio-generation-Hackathon")
LLM_MODEL = os.getenv("LLM_MODEL", "Qwen3-32B-non-thinking-Hackathon")
DEFAULT_STREAMER_PERSONA = os.getenv("DEFAULT_STREAMER_PERSONA", "speed")
DEFAULT_GIFT_PROMPT = os.getenv(
    "DEFAULT_GIFT_PROMPT",
    "A viewer just sent a gift during the livestream. React with excitement and keep the energy high!",
)
SAVE_TTS_WAV = os.getenv("SAVE_TTS_WAV", "false").lower() in {"1", "true", "yes"}
PROCESSOR_LOOP_INTERVAL = float(os.getenv("PROCESSOR_LOOP_INTERVAL", "0.5"))

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
[Speed] Yo yo yo! We are LIVE! What's good, chat! It's your boy, Speed!
[Speed] Y'all sent me this paper, "Attention Is All You Need." Bro, they finally get it! They wrote a paper about me!
[Speed] Okay, let's find the good part. It says they propose a new thing, the Transformer.
[Speed] Wait, TRANSFORMER?! AIN'T NO WAY! We talkin' Optimus Prime? SEWEY! Bro, what is this?!
[Speed] This ain't no Optimus Prime! It's just a bunch of boxes and arrows! This looks like abstract art or something. I don't get it.

[Speed] Whoa! Was that Trump?! Chat, y'all hear that? "No-Attention Speed"? Bro, shut up! I have the most attention in the world! You're fake news! Watch, I'm gonna read this whole thing right now. Okay, what is this? An equation? It says Attention of Q, K, and V is softmax. Bro, what's a softmax? That sounds like a new mattress brand! I'm not doing homework on stream!

[Speed] Stop calling me that! Donald, I swear! Low energy? I have the most energy! Look! OHOHOH! See? Energy! You're just a hater. Let me find something I actually understand. Hardware! Okay, here! They used eight NVIDIA P100 GPUs. P100? Bro, that's it? I have an RTX 4090 right now! I could run their science project while playing Fortnite! My PC is better than their machine!

[Speed] SHUT UP! Just shut up, man! Stop calling me that! You don't know me! I'm the best streamer in the world! People watch ME! Not this stupid paper! I'm done with it!

[Speed] THAT'S IT! I'M DONE! Get him out of here! I can't do this anymore, bro! Every single time! You think this is funny?! THIS STREAM IS OVER! I AM OUT!
"""

PERSONA_REFERENCES = {
    "speed": {
        "path": REFERENCE_AUDIO_DIR / "speed_voice.wav",
        "transcript": SPEED_REFERENCE_TRANSCRIPT,
        "scene_desc": "The tone is extremely high-energy and excited. The speaker talks fast and loudly.",
    },
    "chinese_trump": {
        "path": REFERENCE_AUDIO_DIR / "chinese_trump_voice.wav",
        "transcript": CHINESE_TRUMP_REFERENCE_TRANSCRIPT,
        "scene_desc": """
In this audio, the person is impersonating Donald Trump's voice. The pacing is measured, with strategic pauses to let insults land. The delivery should feel like a series of dismissive proclamations, consistently patronizing the streamer and methodically building up the roast with each message. The speaker is in a quiet room with NO music.
""",
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
