"""
================================================================================
api_client.py — Gemini API Communication Layer
================================================================================
SDK: google-genai (new, 2024+) — replaces the deprecated google.generativeai

    pip install google-genai

Purpose:
    Encapsulate all API communication logic. This module knows nothing about
    presentation or business rules — it only makes requests and returns results.

SDK migration reference (old → new):
    Authentication  : genai.configure(api_key=)    → genai.Client(api_key=)
    Content call    : model.generate_content()      → client.models.generate_content()
    Streaming       : model.generate_content(stream=True) → client.models.generate_content_stream()
    Error module    : google.api_core.exceptions    → google.genai.errors (built-in)

Module structure — three layers:
    Layer 1 · Factories
        create_client()   → authenticated genai.Client
        create_config()   → reusable GenerateContentConfig

    Layer 2 · Core operations (stateless, raise on error)
        simple_chat()     → single message, full response
        stream_chat()     → single message, token-by-token
        multi_turn_chat() → multi-message with accumulated history

    Layer 3 · Error-handled wrappers (return structured dict, never raise)
        safe_chat()
        safe_stream_chat()
        safe_multi_turn_chat()

Error hierarchy (google.genai.errors):
    APIError (base)
    ├── ClientError  → 4xx: 400 bad request, 403 auth, 429 rate limit
    └── ServerError  → 5xx: 503 service unavailable
================================================================================
"""

from google import genai
from google.genai import types
from google.genai import errors as gemini_errors

from config import API_KEY, MODEL, MAX_TOKENS, TEMPERATURE, SYSTEM_PROMPT


# ════════════════════════════════════════════════════════════════════════════════
# LAYER 1 — FACTORIES
# ════════════════════════════════════════════════════════════════════════════════

def create_client() -> genai.Client:
    """
    Instantiate and return an authenticated Gemini client.

    The new SDK uses an explicit client object instead of global configuration:
        Old: genai.configure(api_key=API_KEY)       # global side-effect
        New: client = genai.Client(api_key=API_KEY)  # explicit, testable

    Using a factory function keeps authentication in one place — if the auth
    mechanism changes (e.g. OAuth, secrets manager), only this function changes.
    """
    return genai.Client(api_key=API_KEY)


def create_config(**overrides) -> types.GenerateContentConfig:
    """
    Build and return a reusable GenerateContentConfig object.

    In the new SDK, generation parameters (temperature, max_output_tokens,
    system_instruction) are bundled into GenerateContentConfig and passed as
    config= in each API call — not as separate arguments.

    Parameters:
        **overrides : Optional keyword arguments to override config.py defaults.
                      E.g. create_config(temperature=0.9) for a creative call.

    Returns:
        types.GenerateContentConfig ready for use in generate_content().
    """
    return types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        temperature=overrides.get("temperature", TEMPERATURE),
        max_output_tokens=overrides.get("max_output_tokens", MAX_TOKENS),
    )


# ════════════════════════════════════════════════════════════════════════════════
# LAYER 2 — CORE OPERATIONS
# ════════════════════════════════════════════════════════════════════════════════

def simple_chat(prompt: str) -> str:
    """
    Send a single message and wait for the complete response.

    Use when: one-off queries with no prior context.
    Avoid when: you need the user to see partial output as it generates.

    The API call is synchronous — execution blocks until the full response
    arrives. response.text is a shortcut for:
        response.candidates[0].content.parts[0].text

    Other useful fields on the response object:
        response.usage_metadata.prompt_token_count     → input tokens consumed
        response.usage_metadata.candidates_token_count → output tokens generated
        response.candidates[0].finish_reason           → STOP | MAX_TOKENS | SAFETY

    Raises: gemini_errors.ClientError / ServerError on API failure.
    """
    client = create_client()
    config = create_config()

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=config,
    )
    return response.text


def stream_chat(prompt: str, callback=None) -> str:
    """
    Send a single message and receive tokens progressively (streaming).

    Use when: long responses, real-time chat UIs, or WebSocket delivery.

    How it works:
        The HTTP connection stays open. The server sends token chunks via
        Server-Sent Events (SSE) as the model generates them. Each chunk
        arrives as an object with a .text attribute.

    Parameters:
        prompt   : User message string.
        callback : Optional function called with each token chunk.
                   Signature: callback(chunk: str) -> None
                   If None, chunks are printed to stdout directly.

    Returns:
        Full accumulated response text.

    Raises: gemini_errors.ClientError / ServerError on API failure.
    """
    client = create_client()
    config = create_config()
    full_text = ""

    for chunk in client.models.generate_content_stream(
        model=MODEL,
        contents=prompt,
        config=config,
    ):
        full_text += chunk.text
        if callback:
            callback(chunk.text)
        else:
            print(chunk.text, end="", flush=True)

    return full_text


def multi_turn_chat(history: list, new_message: str) -> tuple[str, list]:
    """
    Send a message within an ongoing conversation, returning the updated history.

    Stateless API — why we resend the full history:
        The Gemini API has no server-side session memory. Each call is
        independent. To simulate memory, the client must include every previous
        turn in the contents= field of each request.

        Turn 1: contents = [user_msg_1]
        Turn 2: contents = [user_msg_1, model_reply_1, user_msg_2]
        Turn N: contents = [all previous turns + new_message]

    History format (types.Content objects):
        Each turn is a types.Content with a role and a list of parts:
            types.Content(role="user",  parts=[types.Part(text="...")])
            types.Content(role="model", parts=[types.Part(text="...")])

        Note: Gemini uses "model" (not "assistant" like OpenAI / Anthropic).

    Token cost implication:
        Every new turn bills ALL accumulated history + new message. For very
        long conversations (50+ turns), consider summarizing older context to
        reduce costs and stay within the model's context window.

    Parameters:
        history     : List of types.Content from previous turns. Pass [] to start.
        new_message : New user message string.

    Returns:
        (response_text, updated_history)
        updated_history includes the new user turn and the model reply appended.

    Raises: gemini_errors.ClientError / ServerError on API failure.
    """
    client = create_client()
    config = create_config()

    history.append(
        types.Content(role="user", parts=[types.Part(text=new_message)])
    )

    response = client.models.generate_content(
        model=MODEL,
        contents=history,
        config=config,
    )

    response_text = response.text
    history.append(
        types.Content(role="model", parts=[types.Part(text=response_text)])
    )

    return response_text, history


# ════════════════════════════════════════════════════════════════════════════════
# LAYER 3 — ERROR-HANDLED WRAPPERS
# ════════════════════════════════════════════════════════════════════════════════
# Each wrapper calls its Layer 2 counterpart inside a try/except block and
# returns a structured dict instead of raising. This keeps error handling out
# of the presentation layer (main.py).
#
# Return schema:
#   { "success": bool, "response": str, "error_type": str | None }
# Multi-turn also includes:
#   { ..., "history": list }

def _handle_error(error: Exception) -> dict:
    """
    Shared error classifier — maps gemini_errors to user-facing messages.
    Used internally by all safe_* wrappers to avoid repeating the same logic.
    """
    if isinstance(error, gemini_errors.ClientError):
        code = str(error)
        if "403" in code or "PERMISSION_DENIED" in code:
            return {
                "success": False,
                "response": "Authentication error: check your API_KEY in config.py.",
                "error_type": "ClientError_403"
            }
        if "429" in code or "RESOURCE_EXHAUSTED" in code:
            return {
                "success": False,
                "response": (
                    "Rate limit or quota reached. Wait a few seconds and retry.\n"
                    "Monitor usage at https://ai.dev/rate-limit"
                ),
                "error_type": "ClientError_429"
            }
        return {
            "success": False,
            "response": f"Request error (4xx): {error}",
            "error_type": "ClientError"
        }

    if isinstance(error, gemini_errors.ServerError):
        return {
            "success": False,
            "response": (
                f"Google server error (5xx): {error}\n"
                "Check status at https://status.cloud.google.com"
            ),
            "error_type": "ServerError"
        }

    return {
        "success": False,
        "response": f"Unexpected error: {error}",
        "error_type": "UnexpectedError"
    }


def safe_chat(prompt: str) -> dict:
    """Calls simple_chat() with structured error handling. Never raises."""
    try:
        return {"success": True, "response": simple_chat(prompt), "error_type": None}
    except Exception as e:
        return _handle_error(e)


def safe_stream_chat(prompt: str, callback=None) -> dict:
    """Calls stream_chat() with structured error handling. Never raises."""
    try:
        text = stream_chat(prompt, callback)
        return {"success": True, "response": text, "error_type": None}
    except Exception as e:
        return _handle_error(e)


def safe_multi_turn_chat(history: list, new_message: str) -> dict:
    """
    Calls multi_turn_chat() with structured error handling.

    On error, history is NOT modified — the caller's history remains consistent
    and they can retry the same turn.

    Returns:
        { "success": bool, "response": str, "history": list, "error_type": str|None }
    """
    try:
        response_text, updated_history = multi_turn_chat(history, new_message)
        return {
            "success": True,
            "response": response_text,
            "history": updated_history,
            "error_type": None
        }
    except Exception as e:
        result = _handle_error(e)
        result["history"] = history   # return original history unchanged
        return result
