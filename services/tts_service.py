import asyncio
from pathlib import Path
import uuid

import edge_tts


TEMP_DIR = Path("data/tts")
TEMP_DIR.mkdir(parents=True, exist_ok=True)


def pick_voice(text: str) -> str:
    greek_chars = "αβγδεζηθικλμνξοπρστυφχψωάέήίόύώϊϋΐΰ"
    if any(ch.lower() in greek_chars for ch in text):
        return "el-GR-AthinaNeural"
    return "en-US-AriaNeural"


async def synthesize_tts(text: str, voice: str | None = None) -> str:
    voice = voice or pick_voice(text)
    out_file = TEMP_DIR / f"{uuid.uuid4().hex}.mp3"

    communicate = edge_tts.Communicate(text=text, voice=voice)
    await communicate.save(str(out_file))

    return str(out_file)


async def cleanup_file_later(path: str, delay: int = 10) -> None:
    await asyncio.sleep(delay)
    try:
        Path(path).unlink(missing_ok=True)
    except Exception:
        pass
