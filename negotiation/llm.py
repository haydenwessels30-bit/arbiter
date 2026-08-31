"""
LLM client abstraction with free-tier fallbacks.

Priority order:
1. OPENAI_API_KEY (GPT-4o-mini is cheap and great for this)
2. GEMINI_API_KEY (Google Gemini, free tier — 15 RPM)
3. Fallback to scripted responses (no API key needed — behaves like the demo)

In production, this drives BOTH sides of our simulated negotiation (for demos)
and just the Arbiter side during real calls (the other side is a human rep).
"""
import json
import os
import re
import httpx

OPENAI_KEY = os.environ.get("OPENAI_API_KEY", "")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")


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
        f"No LLM API key configured. Set OPENAI_API_KEY or GEMINI_API_KEY. Errors: {errors}"
    )


def has_llm() -> bool:
    return bool(OPENAI_KEY or GEMINI_KEY)
