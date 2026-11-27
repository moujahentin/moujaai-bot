import requests

from config import GROQ_API_KEY, GROQ_BASE_URL, GROQ_MODEL


def ask_groq(prompt: str) -> str:
    if not GROQ_API_KEY:
        raise RuntimeError("Groq API key is not configured")

    url = f"{GROQ_BASE_URL.rstrip('/')}/chat/completions"

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": GROQ_MODEL,
        "stream": False,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are MoujaAI, a Discord AI assistant. "
                    "Your configured provider is Groq. "
                    f"Your configured model is {GROQ_MODEL}. "
                    "When asked who you are, identify yourself as MoujaAI. "
                    "When asked which model or provider you use, report the configured values accurately. "
                    "Never claim to be ChatGPT, GPT-4, or another model. "
                    "Answer clearly and directly, preferably in the user's language. "
                    "Keep answers reasonably short unless the user asks for detail."
                ),
            },
            {"role": "user", "content": prompt},
        ],
    }

    response = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=60,
    )

    response.raise_for_status()
    data = response.json()

    choices = data.get("choices", [])

    if choices:
        content = choices[0].get("message", {}).get("content")
        if isinstance(content, str) and content.strip():
            return content.strip()

    raise RuntimeError("Unexpected Groq response format")
