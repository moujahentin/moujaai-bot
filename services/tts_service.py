import asyncio
import logging
from pathlib import Path
import uuid

import edge_tts

logger = logging.getLogger(__name__)

VOICE_FALLBACKS = {
    "el-GR-AthinaNeural": "el-GR-NestorasNeural",
    "el-GR-NestorasNeural": "el-GR-AthinaNeural",
    "en-US-AriaNeural": "en-US-GuyNeural",
    "en-US-GuyNeural": "en-US-AriaNeural",
}


TEMP_DIR = Path("data/tts")
TEMP_DIR.mkdir(parents=True, exist_ok=True)


def pick_voice(text: str) -> str:
    greek_chars = "αβγδεζηθικλμνξοπρστυφχψωάέήίόύώϊϋΐΰ"
    if any(ch.lower() in greek_chars for ch in text):
        return "el-GR-AthinaNeural"
    return "en-US-AriaNeural"


async def synthesize_tts(text: str, voice: str | None = None) -> str:
    text = text.strip()
    if not text:
        raise ValueError("TTS text cannot be empty")

    primary = voice or pick_voice(text)
    voices = [primary]

    if primary in VOICE_FALLBACKS:
        voices.append(VOICE_FALLBACKS[primary])

    last_error = None

    for attempt in range(2):
        for selected_voice in voices:
            out_file = TEMP_DIR / f"{uuid.uuid4().hex}.mp3"

            try:
                communicate = edge_tts.Communicate(
                    text=text, voice=selected_voice
                )
                await asyncio.wait_for(
                    communicate.save(str(out_file)), timeout=20
                )

                if out_file.stat().st_size == 0:
                    raise RuntimeError("Empty TTS audio file")

                logger.info("TTS success: voice=%s", selected_voice)
                return str(out_file)

            except asyncio.CancelledError:
                out_file.unlink(missing_ok=True)
                raise

            except Exception as exc:
                last_error = exc
                out_file.unlink(missing_ok=True)
                logger.warning(
                    "TTS failed: voice=%s attempt=%d error=%s",
                    selected_voice, attempt + 1, type(exc).__name__
                )

        if attempt == 0:
            await asyncio.sleep(2)

    raise RuntimeError("All TTS attempts failed") from last_error


async def cleanup_file_later(path: str, delay: int = 10) -> None:
    await asyncio.sleep(delay)
    try:
        Path(path).unlink(missing_ok=True)
    except Exception:
        pass
