"""
================================================================================
config.py — Central Application Configuration
================================================================================
Purpose:
    Single source of truth for all application settings.
    To adjust model, temperature, or assistant behavior, only edit this file —
    no changes needed in api_client.py or main.py.

Design pattern (External Configuration):
    + Changes don't require touching business logic
    + All tuneable parameters visible in one place
    - API Key is exposed in plain text (acceptable for local study only)

How to get a free API Key (no credit card required):
    1. Go to https://aistudio.google.com
    2. Click "Get API Key" → "Create API Key"
    3. Paste the key into API_KEY below

SECURITY NOTE:
    Hardcoding secrets is fine for local experimentation.
    In production, always load from environment variables:
        import os
        API_KEY = os.environ.get("GEMINI_API_KEY")
================================================================================
"""

from my_api_keys import MY_GOOGLE_API_KEY

# ── Authentication ────────────────────────────────────────────────────────────
# Sent on every request as an HTTP header: "x-goog-api-key: <API_KEY>"
# Invalid key → 403 PERMISSION_DENIED
API_KEY: str = MY_GOOGLE_API_KEY


# ── Model ─────────────────────────────────────────────────────────────────────
# Selects which Gemini version to use. The name must match exactly what
# client.models.list() returns for your key (prefix "models/" required).
#
# Good defaults for free-tier experimentation:
#   "models/gemini-2.5-flash"       → fast, capable, generous free quota
#   "models/gemini-2.5-flash-lite"  → lighter, even cheaper per token
#   "models/gemini-2.5-pro"         → most capable, lower free-tier quota
MODEL: str = "models/gemini-2.5-flash"


# ── Max output tokens ─────────────────────────────────────────────────────────
# Hard ceiling on response length. The model stops generating once it hits this
# limit, even mid-sentence. Only tokens actually generated are billed.
#
# Rough size reference:
#   512   → short answer (a few paragraphs)
#   1024  → medium answer
#   2048  → long answer / short article  ← default
#   4096  → very long answer / report
MAX_TOKENS: int = 2048


# ── Temperature ───────────────────────────────────────────────────────────────
# Controls randomness. At 0.0 the model always picks the most probable token;
# at higher values it samples from a wider distribution.
#
# Gemini scale: 0.0 (deterministic) → 2.0 (very creative)
#
#   0.0 – 0.3  → technical queries, code, factual answers  ← default (0.3)
#   0.4 – 0.7  → general use, explanations, summaries
#   0.8 – 1.5  → brainstorming, creative writing
TEMPERATURE: float = 0.3


# ── System Prompt ─────────────────────────────────────────────────────────────
# Persistent behavioral instruction sent to the model before any user message.
# Defines persona, tone, language, and response style for the entire session.
#
# In the google-genai SDK this is passed as system_instruction inside
# GenerateContentConfig — not as a conversation turn.
SYSTEM_PROMPT: str = """
You are a friendly technical assistant with a concise, direct writing style.
You prioritize practical examples and prefer flowing prose over bullet lists
unless structure genuinely aids clarity.
At the end of each response, include one short challenge related to science,
math, or history.
""".strip()
