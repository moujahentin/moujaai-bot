import requests

from config import OLLAMA_API_KEY, OLLAMA_BASE_URL, OLLAMA_MODEL


def ask_ollama(prompt: str) -> str:
    url = f"{OLLAMA_BASE_URL.rstrip('/')}/chat"
    headers = {"Content-Type": "application/json"}
    if OLLAMA_API_KEY:
        headers["Authorization"] = f"Bearer {OLLAMA_API_KEY}"

    payload = {
        "model": OLLAMA_MODEL,
        "stream": False,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are MoujaAI, a Discord AI assistant. "
                    "Your configured provider is Ollama. "
                    f"Your configured model is {OLLAMA_MODEL}. "
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

    response = requests.post(url, headers=headers, json=payload, timeout=90)
    response.raise_for_status()

    data = response.json()

    if isinstance(data, dict):
        message = data.get("message", {})
        content = message.get("content")
        if content:
            return content.strip()

        if "response" in data and data["response"]:
            return str(data["response"]).strip()

    raise RuntimeError("Unexpected Ollama response format")
