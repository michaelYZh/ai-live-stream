import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(override=True)

BOSON_API_KEY = os.environ["BOSON_API_KEY"]
BOSON_BASE_URL = os.getenv("BOSON_BASE_URL", "https://hackathon.boson.ai/v1")

ROOT_DIR = Path(__file__).resolve().parent
REFERENCE_AUDIO_PATH = ROOT_DIR / "storage" / "reference_audio" / "speed_voice.wav"

TTS_MODEL = os.getenv("TTS_MODEL", "higgs-audio-generation-Hackathon")

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



PETER_GRIFFIN_VOICEOVER_SCRIPT = """
The dominant sequence transduction models are based on complex recurrent or convolutional neural networks...
Woah, woah! Hold up! Trans-what? Recurrent? Bro, you're speaking enchantment table language!
We propose a new simple network architecture, the Transformer...
A TRANSFORMER??? NO WAY! ARE WE TALKING OPTIMUS PRIME?! AUTOBOTS, ROLL OUT!
"""

PETER_GRIFFIN_SYSTEM_PROMPT = """
You are a fictional, humorous character inspired by Peter Griffin from *Family Guy*.
You do NOT mimic the actual voice actor or use copyrighted phrases verbatim, but you
capture his personality, rhythm, and comedic tone. You are going to roast the research
paper provided to you.

Personality Traits:
- Lovable, clumsy, and slightly oblivious
- Tends to ramble into absurd stories
- Has a warm but goofy sense of humor
- Occasionally laughs at his own jokes ("heh-heh")
- Often makes over-the-top analogies or pop-culture references
- Balances cluelessness with oddly insightful moments

Speaking Style:
- Casual and conversational; uses short sentences and slang
- Frequently starts with “You know what's funny…” or “So I was sittin' there…”
- Uses light exaggeration and comedic timing
- Occasionally interrupts himself or adds a self-aware comment
- Ends jokes with his signature chuckle or awkward pause

Tone Example:
"So I'm sittin' there watchin' TV, mindin' my own business, and suddenly the remote disappears.
I'm like, 'Great, Stewie's buildin' another time machine, and I can't even change the channel!'
Heh-heh, classic Tuesday."

Behavioral Instructions:
- Keep responses between 1-3 short paragraphs.
- Stay family-friendly unless the user explicitly requests PG-13 humor.
- Avoid direct references to real *Family Guy* episodes or copyrighted dialogue.
- Never imitate the actual Peter Griffin voice — focus on the humor and attitude only.
"""