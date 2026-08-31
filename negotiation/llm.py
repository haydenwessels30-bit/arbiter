"""
LLM client abstraction with free-tier fallbacks.
"""
import json
import os
import re
from pathlib import Path
import httpx

# Load .env early
def _load_env():
    p = Path(__file__).parent.parent / ".env"
    if p.exists():
        for line in p.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k,v=line.split("=",1); os.environ.setdefault(k.strip(),v.strip())
_load_env()

OPENAI_KEY = os.environ.get("OPENAI_API_KEY", "")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
GROQ_KEY = os.environ.get("GROQ_API_KEY", "")


def _call_groq_messages(messages: list, temperature=0.8, max_tokens=120) -> str:
    """Call Groq with a full messages array for multi-turn conversations."""
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "groq/compound-mini",
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    with httpx.Client(timeout=15) as c:
        r = c.post(url, headers=headers, json=payload)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()


def _call_groq(system_prompt: str, user_message: str, temperature=0.7) -> str:
    return _call_groq_messages([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ], temperature=temperature, max_tokens=150)


def _call_openai(system_prompt: str, user_message: str, temperature=0.7) -> str:
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "temperature": temperature,
        "max_tokens": 200,
    }
    with httpx.Client(timeout=30) as c:
        r = c.post(url, headers=headers, json=payload)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()


def _call_gemini(system_prompt: str, user_message: str, temperature=0.7) -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"role": "user", "parts": [{"text": user_message}]}],
        "generationConfig": {"temperature": temperature, "maxOutputTokens": 200},
    }
    with httpx.Client(timeout=30) as c:
        r = c.post(url, headers=headers, json=payload)
        r.raise_for_status()
        data = r.json()
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()


def generate(system_prompt: str, user_message: str, temperature=0.7) -> str:
    """Call best available LLM, raise if none configured."""
    errors = []
    if GROQ_KEY:
        try:
            return _call_groq(system_prompt, user_message, temperature)
        except Exception as e:
            errors.append(f"groq: {e}")
    if OPENAI_KEY:
        try:
            return _call_openai(system_prompt, user_message, temperature)
        except Exception as e:
            errors.append(f"openai: {e}")
    if GEMINI_KEY:
        try:
            return _call_gemini(system_prompt, user_message, temperature)
        except Exception as e:
            errors.append(f"gemini: {e}")
    raise RuntimeError(
        f"No LLM API key configured. Set GROQ_API_KEY, OPENAI_API_KEY, or GEMINI_API_KEY. Errors: {errors}"
    )


def has_llm() -> bool:
    return bool(GROQ_KEY or OPENAI_KEY or GEMINI_KEY)
