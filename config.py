import os
import discord
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gpt-oss:120b")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "https://ollama.com/api")

COMMAND_PREFIX = os.getenv("COMMAND_PREFIX", "!")
ASK_MAX_CHARS = int(os.getenv("ASK_MAX_CHARS", "1500"))
ASK_COOLDOWN_SECONDS = int(os.getenv("ASK_COOLDOWN_SECONDS", "10"))
ASK_MAX_CONCURRENT = int(os.getenv("ASK_MAX_CONCURRENT", "3"))

DELETE_AFTER_SECONDS = int(os.getenv("DELETE_AFTER_SECONDS", "15"))

NUMBER_GUESS_MIN = int(os.getenv("NUMBER_GUESS_MIN", "1"))
NUMBER_GUESS_MAX = int(os.getenv("NUMBER_GUESS_MAX", "100"))
NUMBER_GUESS_TIMEOUT_MINUTES = int(os.getenv("NUMBER_GUESS_TIMEOUT_MINUTES", "30"))

ADMIN_USER_IDS = {
    int(x.strip())
    for x in os.getenv("ADMIN_USER_IDS", "").split(",")
    if x.strip().isdigit()
}

TRANSLATE_REACTIONS = {
    "🇬🇧": {"lang": "en", "label": "English"},
    "🇬🇷": {"lang": "el", "label": "Greek"},
    "🇨🇿": {"lang": "cs", "label": "Czech"},
    "🇩🇪": {"lang": "de", "label": "German"},
    "🇫🇷": {"lang": "fr", "label": "French"},
    "🇪🇸": {"lang": "es", "label": "Spanish"},
    "🇮🇹": {"lang": "it", "label": "Italian"},
}

DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
GUESS_STATS_FILE = DATA_DIR / "guess_stats.json"

INTENTS = discord.Intents.default()
INTENTS.message_content = True
INTENTS.guilds = True
INTENTS.messages = True
INTENTS.reactions = True
INTENTS.members = True
