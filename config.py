import json
import os
from pathlib import Path
from typing import Dict, Any

from dotenv import load_dotenv

load_dotenv(override=True)

BOSON_API_KEYS = [
    key.strip()
    for key in os.getenv("BOSON_API_KEYS", "").split(",")
    if key.strip()
]
if not BOSON_API_KEYS:
    raise RuntimeError("BOSON_API_KEYS must be set in the environment.")

BOSON_BASE_URL = os.getenv("BOSON_BASE_URL", "https://hackathon.boson.ai/v1")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

ROOT_DIR = Path(__file__).resolve().parent
ASSETS_DIR = ROOT_DIR / "assets"
PERSONAS_DIR = ASSETS_DIR / "personas"
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

# DEFAULT_SCRIPT = """
# [Speed] Yo yo yo! We are LIVE! What's good, chat! It's your boy, Speed! Y'all sent me this paper, "Attention Is All You Need." Bro, they finally get it! They wrote a paper about me!
# [Speed] Okay, let's find the good part. It says they propose a new thing, the Transformer. Wait, TRANSFORMER?! AIN'T NO WAY! We talkin' Optimus Prime? SEWEY! Bro, what is this?!
# [Speed] This ain't no Optimus Prime! It's just a bunch of boxes and arrows! This looks like abstract art or something. I don't get it.
# [Speed] Whoa! Was that Trump?! Chat, y'all hear that? "No-Attention Speed"? Bro, shut up! I have the most attention in the world! You're fake news! Watch, I'm gonna read this whole thing right now. Okay, what is this? An equation? It says Attention of Q, K, and V is softmax. Bro, what's a softmax? That sounds like a new mattress brand! I'm not doing homework on stream!
# [Speed] Stop calling me that! Donald, I swear! Low energy? I have the most energy! Look! OHOHOH! See? Energy! You're just a hater. Let me find something I actually understand. Hardware! Okay, here! They used eight NVIDIA P100 GPUs. P100? Bro, that's it? I have an RTX 4090 right now! I could run their science project while playing Fortnite! My PC is better than their machine!
# [Speed] SHUT UP! Just shut up, man! Stop calling me that! You don't know me! I'm the best streamer in the world! People watch ME! Not this stupid paper! I'm done with it!
# [Speed] THAT'S IT! I'M DONE! Get him out of here! I can't do this anymore, bro! Every single time! You think this is funny?! THIS STREAM IS OVER! I AM OUT!
# """
DEFAULT_SCRIPT = """
[Speed] Yo yo yo! We are LIVE! What's good, chat! It's your boy, Speed! Y'all kept sending me this paper... "Attention Is All You Need." Bro, they finally get it! They wrote a paper about me! Let's go!

[Speed] Okay, let's find the good part... It says they propose a new thing, the "Transformer." Wait... TRANSFORMER?! AIN'T NO WAY! We talkin' Optimus Prime? Autobots?! ROLL OUT! Bro, what is this?!

[Speed] This ain't no Optimus Prime! It's just a bunch of boxes and arrows! What is this? This looks like... abstract art or something. I don't get it, bro. Chat, am I supposed to understand this?

[Speed] Okay, what is this? An equation? It says... Attention of Q, K, and V... is softmax. Bro, what is softmax? That sounds like a new mattress brand! I'm not doing homework on stream! This is boring!

[Spongebob] Ooh! 'Attention' is just like when Mr. Krabs looks at a really shiny penny! Ah-hah-hah!

[Speed] Bro... wait. Is that Spongebob?! Chat, am I trippin'? Yo, Spongebob! Alright, thanks man. That that kinda makes sense.

[Speed] Kinda. But still, why they gotta use these crazy words? Q, K, V bro, this is math class! I thought this was about Transformers! This is a scam! Y'all scammed me, chat!

[Peter] This paper is missin' somethin', Speed. It's missin' "The Bird." 'Cause everybody knows the Bird is the Word!

[Peter] All these boxes and arrows look pretty sus, Speed. Like that one red crewmate. Freakin' sweet.

[Speed] Bro, shut up, man! Yo, chat, what is GOING ON today? First Spongebob, now this fat guy? Y'all are using AI, bro! This ain't real!

[Speed] I'm gonna find something I actually understand. Okay, here! Hardware! They used... let's see ... eight NVIDIA P100s. P one hundred? bro, THAT'S IT? I have an RTX fourty ninety RIGHT NOW! I could run their little science project while playing Fortnite at the same time! My PC is BETTER than their whole machine!

[Trump] Wrong! Your 4090 is okay, but my computers are tremendous. The best. Everyone agrees.

[Trump] I call him "No-Attention Speed." He can't even read a simple paper. Very sad! Low energy!

[Speed] SHUT UP! SHUT UP, MAN! Stop calling me that! Donald, I swear! Low energy? I have the MOST energy! LOOK! OH OH OH! SEE?! ENERGY! You're just a hater! You're fake news!

[Trump] I build the best machines. I'd build a machine so good at this... and I'd make the nerds pay for it! Total disaster, this kid.

[Speed] Shut up, man! You're the real softmax! Yeah, you're a soft mattress! Bro, stop yelling Make America Great Again! You can't even make your hair great again! I'm the one with the REAL attention! You're fake news! You're done! Get him out of here!

[Speed] THAT'S IT! I'M DONE! THIS STREAM IS OVER! I AM OUT! PEACE!
"""

MODIFY_SCRIPT_PROMPT_TEMPLATE = """
<core_task>
You will be given the Speech History of a livestream transcript and a New Superchat Message formatted as [Superchat_name] message_text. Write the next segment of the livestream transcript where streamer explicitly calls out, and addresses the Superchat_name if Superchat_name is not None. The streamer should then react to the content and tone of their message in-character. If the Superchat_name is a well-known figure (e.g., Trump, Elon, Kanye), the response should acknowledge their recognizable traits, personality, or public history in a natural and fitting way. After this reaction, the streamer must smoothly transition back to and continue the topic contained in remaining_lines, speaking as if they are directly resuming from where they left off. The tone, personality, pacing, and style must be consistent with the Speech_History. The result should feel like a natural continuation, not a new scene.
</core_task>

<persona streamer={streamer}>
{stramer_persona}
</persona>

<transcript_guide>
Speakable: Every line must sound natural when spoken. This is for a Text-to-Speech (TTS) model.
Simple Punctuation: Use ellipses (...) for pauses, but never place two sets of ellipses near each other. Avoid complex punctuation.
No Symbols for Words: When encountering formulas or symbols (like =), write them out phonetically. For example, write "is" or "equals" instead of =.
No Stage Directions: Do not include parenthetical actions like (slams desk) or (laughs). The emotion should be conveyed through the dialogue itself.
Correct Formatting: All lines must start with either [Speed] or [Superchat].
Logical Flow: Ensure Speed's reaction is a direct and natural response to the superchat. The dialogue should build on the central joke or roast.
</transcript_guide>


<input_format>
You will receive:
- speech_history: the spoken lines of the streamer
- remaining_lines: the remaining lines of the script to be streamed
- new_superchat: the new superchat message sent to the streamer formatted as [Superchat_name] message_text
</input_format>

<output_format>
Your task is to provide the next logical lines of the script as the response.
Each line should be prefixed with [{streamer}] 
You should first react to new_superchat and Superchat_name if Superchat_name is not None in at most 2 sentences then continue speaking and finish the script in alignment with remaining_lines, matching its approximate length, pacing, and stopping point.
</output_format>

<example>
    <speech_history>
[Speed] Yo yo yo! We are LIVE! What's good, chat! It's your boy, Speed!
[Speed] Y'all sent me this paper, "Attention Is All You Need." Bro, they finally get it! They wrote a paper about me!
[Speed] Okay, let's find the good part. It says they propose a new thing, the Transformer.
[Speed] Wait, TRANSFORMER?! AIN'T NO WAY! We talkin' Optimus Prime? SEWEY! Bro, what is this?!
[Speed] This ain't no Optimus Prime! It's just a bunch of boxes and arrows! This looks like abstract art or something. I don't get it.
    </speech_history>
    <remaining_lines>
[Speed] Whoa! Was that Trump?! Chat, y'all hear that? "No-Attention Speed"? Bro, shut up! I have the most attention in the world! You're fake news! Watch, I'm gonna read this whole thing right now. Okay, what is this? An equation? It says Attention of Q, K, and V is softmax. Bro, what's a softmax? That sounds like a new mattress brand! I'm not doing homework on stream!

[Speed] Stop calling me that! Donald, I swear! Low energy? I have the most energy! Look! OHOHOH! See? Energy! You're just a hater. Let me find something I actually understand. Hardware! Okay, here! They used eight NVIDIA P100 GPUs. P100? Bro, that's it? I have an RTX 4090 right now! I could run their science project while playing Fortnite! My PC is better than their machine!

[Speed] SHUT UP! Just shut up, man! Stop calling me that! You don't know me! I'm the best streamer in the world! People watch ME! Not this stupid paper! I'm done with it!

[Speed] THAT'S IT! I'M DONE! Get him out of here! I can't do this anymore, bro! Every single time! You think this is funny?! THIS STREAM IS OVER! I AM OUT!
    </remaining_lines>
    <new_superchat>
[Trump] Wrong! It's a tremendous architecture, the best. But you can't see it because you have no attention span. Sad! They shouldn't call you iShowSpeed, they should call you No-Attention Speed.
    </new_superchat>
    
    <example_output>
[Speed] Whoa! Was that Trump?! Chat, y'all hear that? "No-Attention Speed"?
[Speed] Bro, shut up! I have the most attention in the world! You're fake news!
[Speed] Watch, I'm gonna read this whole thing right now.
    </example_output>
</example>

<input>
    <speech_history>
{speech_history}
    </speech_history>
    <remaining_lines>
{remaining_lines}
    </remaining_lines>
    <new_superchat>
[{superchat_sender}]{superchat_message}
    </new_superchat>
</input>

Please continue the script using approximately the same number of lines as provided in remaining_lines.
"""
LLM_SYSTEM_PROMPT = "You are an expert scriptwriter specializing in creating authentic, engaging, and voice-ready livestream transcripts. Your task is to continue an ongoing script based on new user comments (superchats)."


def _load_persona_references() -> Dict[str, Dict[str, Any]]:
    personas_path = PERSONAS_DIR / "personas.json"
    with personas_path.open("r", encoding="utf-8") as fp:
        persona_data = json.load(fp)

    references: Dict[str, Dict[str, Any]] = {}
    for persona_key, config in persona_data.items():
        audio_path = ASSETS_DIR / config["audio"]
        transcript_path = ASSETS_DIR / config["transcript"]
        scene_desc_path = ASSETS_DIR / config["scene_desc"]

        if not audio_path.exists():
            raise FileNotFoundError(f"Reference audio missing for persona '{persona_key}': {audio_path}")
        if not transcript_path.exists():
            raise FileNotFoundError(f"Transcript missing for persona '{persona_key}': {transcript_path}")
        if not scene_desc_path.exists():
            raise FileNotFoundError(f"Scene description missing for persona '{persona_key}': {scene_desc_path}")

        references[persona_key] = {
            "path": audio_path,
            "transcript": transcript_path.read_text(encoding="utf-8").strip(),
            "scene_desc": scene_desc_path.read_text(encoding="utf-8").strip(),
        }

    return references


PERSONA_REFERENCES = _load_persona_references()
