from config import AI_PROVIDER, AI_MODEL

from services.groq_client import ask_groq
from services.ollama_client import ask_ollama


def ask_ai(prompt: str) -> str:
    if AI_PROVIDER == "groq":
        return ask_groq(prompt)

    if AI_PROVIDER == "ollama":
        return ask_ollama(prompt)

    raise RuntimeError(f"Unsupported AI provider: {AI_PROVIDER}")


def get_ai_info() -> dict:
    return {
        "provider": AI_PROVIDER,
        "model": AI_MODEL,
    }
