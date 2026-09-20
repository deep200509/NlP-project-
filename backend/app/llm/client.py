"""
One small door to the language model. The rest of the project only calls generate().

Provider is chosen in backend/.env:
    LLM_PROVIDER=gemini   (default, needs GEMINI_API_KEY and internet)
    LLM_PROVIDER=ollama   (offline, needs Ollama running on this computer)
"""
import httpx

from app.config import GEMINI_API_KEY, GEMINI_MODEL, LLM_PROVIDER, OLLAMA_MODEL, OLLAMA_URL

TIMEOUT_SECONDS = 180


class LLMError(Exception):
    """Anything that stops us from getting an answer: no key, no internet, quota, bad reply."""


def _gemini(system: str, prompt: str) -> str:
    if not GEMINI_API_KEY:
        raise LLMError("GEMINI_API_KEY is missing. Put it in backend/.env and restart the server.")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
    body = {"system_instruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}]}
    # the key travels in a header, never in the URL (URLs end up in logs)
    response = httpx.post(url, json=body, headers={"x-goog-api-key": GEMINI_API_KEY}, timeout=TIMEOUT_SECONDS)
    if response.status_code != 200:
        try:
            message = response.json()["error"]["message"]
        except Exception:
            message = response.text[:300]
        raise LLMError(f"Gemini answered {response.status_code}: {message}")
    try:
        parts = response.json()["candidates"][0]["content"]["parts"]
        return "".join(part.get("text", "") for part in parts)
    except (KeyError, IndexError, TypeError):
        raise LLMError("Gemini returned no text (the answer may have been blocked or empty).")


def _ollama(system: str, prompt: str) -> str:
    body = {"model": OLLAMA_MODEL, "system": system, "prompt": prompt, "stream": False}
    response = httpx.post(f"{OLLAMA_URL}/api/generate", json=body, timeout=TIMEOUT_SECONDS * 3)
    if response.status_code != 200:
        raise LLMError(f"Ollama answered {response.status_code}: {response.text[:300]}")
    return response.json().get("response", "")


def generate(system: str, prompt: str) -> str:
    try:
        return _ollama(system, prompt) if LLM_PROVIDER == "ollama" else _gemini(system, prompt)
    except httpx.HTTPError as err:
        raise LLMError(f"Could not reach the language model ({LLM_PROVIDER}): {err}")


def describe() -> dict:
    return {"provider": LLM_PROVIDER, "model": OLLAMA_MODEL if LLM_PROVIDER == "ollama" else GEMINI_MODEL,
            "key_configured": bool(GEMINI_API_KEY) if LLM_PROVIDER != "ollama" else None}