"""
================================================================================
gemini/errors.py — Error Handling and Safe Wrappers
================================================================================
Responsibility:
    Catch exceptions from the API operations and convert them into structured
    dictionaries that the presentation layer (main.py) can use safely.

Why separate error handling from operations?
    The functions in operations.py raise exceptions when something goes wrong.
    That's clean and simple — they do one thing. But main.py doesn't want to
    surround every API call with try/except blocks. So this file provides
    "safe" versions of each operation that never raise — they always return
    a dict with a "success" field.

    This pattern is sometimes called a "Result type" or "Either type" in
    other programming languages. In Python we simulate it with a dict.

What is try/except?
    A way to handle errors gracefully instead of crashing.

    try:
        risky_operation()     # if this raises an exception...
    except SomeError as e:    # ...execution jumps here
        handle_the_error(e)   # and we decide what to do

    Without try/except, any exception propagates up the call stack until
    something catches it — or the program crashes with a traceback.

What is isinstance()?
    isinstance(error, SomeClass) returns True if `error` is an instance of
    SomeClass or any of its subclasses.

    We use it in _handle_error() to identify what TYPE of error occurred:
        isinstance(error, gemini_errors.ClientError)  → True for 4xx errors
        isinstance(error, gemini_errors.ServerError)  → True for 5xx errors

    This is safer than checking error codes in strings, but since Gemini
    uses the same ClientError class for 403, 429, and 400, we also inspect
    the string representation to distinguish them.

Return schema used by all safe_* functions:
    {
        "success"    : bool        → True if the API call succeeded
        "response"   : str         → the model's text, or an error message
        "error_type" : str | None  → None on success, error class name on failure
    }
    safe_multi_turn_chat() adds:
        "history"    : list        → the (possibly unchanged) conversation history
================================================================================
"""

from google.genai import errors as gemini_errors

# Relative imports from sibling modules within the gemini/ package
from .operations import simple_chat, stream_chat, multi_turn_chat


# ── Private helper ────────────────────────────────────────────────────────────
# The leading underscore in _handle_error is a Python convention that signals
# "this is an internal helper, not meant to be called from outside this module."
# It's not enforced by the language — it's just a naming agreement.

def _handle_error(error: Exception) -> dict:
    """
    Classify a Gemini API exception and return a user-facing error dict.

    Why centralize this logic?
        All three safe_* functions need to handle errors the same way. Without
        this helper, we'd have three identical if/elif blocks — duplicated code
        that would need to be updated in three places whenever error handling
        logic changes. One function, one place to maintain.

    Error hierarchy in google.genai.errors:
        APIError (base class — catches everything)
        ├── ClientError → HTTP 4xx: the REQUEST had a problem
        │     • 400 → bad parameter (e.g., invalid model name)
        │     • 403 → authentication failed (bad API key)
        │     • 429 → too many requests (rate limit or quota exhausted)
        └── ServerError → HTTP 5xx: the SERVER had a problem
              • 503 → Google's service is temporarily unavailable

    Why inspect str(error) for "403" and "429"?
        Both are ClientErrors, but we want to give different messages for each.
        The SDK bundles the HTTP status code into the exception's string
        representation, so checking if "403" or "429" appears in str(error)
        is a reliable way to distinguish them.

    Parameters:
        error : The caught exception object.

    Returns:
        A dict with "success": False, "response": <message>, "error_type": <str>.
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
                    "Monitor usage: https://ai.dev/rate-limit"
                ),
                "error_type": "ClientError_429"
            }
        # Any other 4xx (e.g., 400 bad request, 404 model not found)
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
                "Check service status: https://status.cloud.google.com"
            ),
            "error_type": "ServerError"
        }

    # Catch-all for anything unexpected (network timeout, import error, etc.)
    return {
        "success": False,
        "response": f"Unexpected error ({type(error).__name__}): {error}",
        "error_type": "UnexpectedError"
    }


# ── Safe wrappers ─────────────────────────────────────────────────────────────

def safe_chat(prompt: str) -> dict:
    """
    Safe wrapper around simple_chat(). Never raises — always returns a dict.

    What is `except Exception as e`?
        `Exception` is the base class for almost all Python errors. By catching
        it here, we ensure that NO exception — whether from the API, the network,
        or anything unexpected — can crash the program. `as e` binds the caught
        exception object to the variable `e` so we can inspect it.

    Parameters:
        prompt : The user's message.

    Returns:
        { "success": bool, "response": str, "error_type": str | None }
    """
    try:
        return {
            "success": True,
            "response": simple_chat(prompt),
            "error_type": None
        }
    except Exception as e:
        return _handle_error(e)


def safe_stream_chat(prompt: str, callback=None) -> dict:
    """
    Safe wrapper around stream_chat(). Never raises — always returns a dict.

    Note on streaming errors:
        If an error occurs partway through streaming, some tokens may have
        already been printed/sent to the callback before the exception fires.
        The returned dict will have success=False, but partial output may
        have already been delivered. This is a known trade-off with streaming.

    Parameters:
        prompt   : The user's message.
        callback : Optional function called with each token chunk.

    Returns:
        { "success": bool, "response": str, "error_type": str | None }
    """
    try:
        text = stream_chat(prompt, callback)
        return {"success": True, "response": text, "error_type": None}
    except Exception as e:
        return _handle_error(e)


def safe_multi_turn_chat(history: list, new_message: str) -> dict:
    """
    Safe wrapper around multi_turn_chat(). Never raises — always returns a dict.

    Important: history safety on error.
        multi_turn_chat() appends the new user message to `history` BEFORE
        making the API call. If the call then fails, the history list already
        has the user message in it — but no model reply.

        To avoid leaving history in an inconsistent state, this wrapper
        passes a COPY of the history to multi_turn_chat(). If the call
        fails, the original history is returned unchanged, and the caller
        can retry safely.

    What is list() for copying?
        `list(history)` creates a SHALLOW COPY of the list — a new list object
        with the same elements. Modifying the copy doesn't affect the original.

        Why "shallow"? The list items themselves (types.Content objects) are
        not duplicated — the copy just holds references to the same objects.
        For our use case, this is sufficient.

    Parameters:
        history     : List of types.Content from previous turns.
        new_message : The new user message.

    Returns:
        { "success": bool, "response": str, "history": list, "error_type": str | None }
        On success: history is the updated list (with new turns appended).
        On failure: history is the original list unchanged.
    """
    history_copy = list(history)   # work on a copy so errors don't corrupt history

    try:
        response_text, updated_history = multi_turn_chat(history_copy, new_message)
        return {
            "success": True,
            "response": response_text,
            "history": updated_history,
            "error_type": None
        }
    except Exception as e:
        result = _handle_error(e)
        result["history"] = history   # return the original, unmodified history
        return result
