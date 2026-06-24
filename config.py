"""
================================================================================
config.py — Central Application Configuration
================================================================================
Purpose:
    Single source of truth for all application settings.
    To adjust model, temperature, or assistant behavior, only edit this file —
    no changes needed anywhere else.

Design pattern — "Separation of Configuration from Logic":
    config.py holds WHAT the app uses (keys, values, prompts).
    The other modules hold HOW the app behaves (functions, logic).
    Keeping them separate means you can tune the app without touching code.

How to get a free API Key (no credit card required):
    1. Go to https://aistudio.google.com
    2. Click "Get API Key" → "Create API Key"
    3. Paste the key into my_api_keys.py

SECURITY NOTE:
    Hardcoding secrets is acceptable for local experiments.
    In production, always load from environment variables:

        import os
        API_KEY = os.environ.get("GEMINI_API_KEY")

    And never commit my_api_keys.py to a public repository.
    Add it to .gitignore:
        echo "my_api_keys.py" >> .gitignore
================================================================================
"""

# ── What is an import? ───────────────────────────────────────────────────────
# `from my_api_keys import MY_GOOGLE_API_KEY` reads the variable MY_GOOGLE_API_KEY
# from the file my_api_keys.py (which lives in the same folder).
# This way the actual secret never appears in this file.
from my_api_keys import MY_GOOGLE_API_KEY


# ── Type annotations ──────────────────────────────────────────────────────────
# The `: str`, `: int`, `: float` after each variable name are type hints.
# They don't affect how Python runs the code — they're documentation for
# humans (and tools like linters) that say "this variable should be a string".


# ── Authentication ────────────────────────────────────────────────────────────
# Every request to the Gemini API carries this key in an HTTP header:
#   x-goog-api-key: <API_KEY>
# The SDK handles that automatically when you pass api_key= to genai.Client().
# Invalid key → the server responds with 403 PERMISSION_DENIED.
API_KEY: str = MY_GOOGLE_API_KEY


# ── Model ─────────────────────────────────────────────────────────────────────
# Selects which Gemini version handles your requests.
# The name must match exactly what list_models.py outputs (prefix "models/" included).
#
# Good starting points for free-tier use:
#   "models/gemini-2.5-flash"       → fast, capable, generous free quota  ← default
#   "models/gemini-2.5-flash-lite"  → lighter version, cheaper per token
#   "models/gemini-2.5-pro"         → most capable, lower free-tier quota
MODEL: str = "models/gemini-2.5-flash"


# ── Max output tokens ─────────────────────────────────────────────────────────
# What is a token?
#   Text is broken into small pieces called tokens before being processed.
#   1 token ≈ 4 characters in English (roughly 3/4 of a word).
#   "Hello, world!" = ~4 tokens. A full paragraph = ~60–100 tokens.
#
# MAX_TOKENS is the hard ceiling on how many tokens the model can generate
# in a single response. If the model hasn't finished when it hits this limit,
# it stops mid-sentence. Only tokens actually generated are billed.
#
# Size reference:
#   512   → short answer (a paragraph or two)
#   1024  → medium answer
#   2048  → long answer / short article  ← default
#   4096  → detailed report or long explanation
MAX_TOKENS: int = 2048


# ── Temperature ───────────────────────────────────────────────────────────────
# Controls how "creative" (random) the model's responses are.
#
# Under the hood, the model assigns a probability to every possible next token.
# At temperature 0.0, it always picks the most probable one (deterministic).
# As temperature rises, it samples from a wider distribution — less predictable,
# more varied, potentially more interesting, but also more prone to errors.
#
# Gemini scale: 0.0 (deterministic) → 2.0 (very creative)
#
#   0.0 – 0.3  → technical queries, code, factual answers     ← default (0.3)
#   0.4 – 0.7  → general use, explanations, summaries
#   0.8 – 1.5  → brainstorming, creative writing
TEMPERATURE: float = 0.9


# ── System Prompt ─────────────────────────────────────────────────────────────
# What is a system prompt?
#   It's a special instruction delivered to the model BEFORE any user message.
#   Think of it as the "job description" you give the AI. It shapes tone,
#   persona, language, and what the model should or shouldn't do throughout
#   the entire conversation — even though the user never sees this text.
#
# In the google-genai SDK, this is passed as `system_instruction` inside
# GenerateContentConfig — it is NOT a regular conversation turn.
SYSTEM_PROMPT: str = """
You are a friendly assistant. You prioritize practical examples and prefer flowing prose over bullet lists
unless structure genuinely aids clarity.
At the end of each response, include one short curiosity or challenge related to science, math, or history.
""".strip()
# What does .strip() do?
#   Removes leading and trailing whitespace (spaces, newlines) from the string.
#   The triple-quoted string above starts with a newline after the opening """,
#   so .strip() cleans that up before sending to the API.
