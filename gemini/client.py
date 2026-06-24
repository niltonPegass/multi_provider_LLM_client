"""
================================================================================
gemini/client.py — Authentication and Configuration Factories
================================================================================
Responsibility:
    Create the two objects that every API call in this project depends on:
      1. genai.Client       — the authenticated connection to the Gemini API
      2. GenerateContentConfig — the bundle of generation parameters

What is a "factory function"?
    A factory function is a regular function whose job is to BUILD and RETURN
    an object. Instead of creating the object directly wherever you need it,
    you call the factory and get a ready-to-use instance back.

    Why bother?
    - If the way you build the object ever changes (different auth method,
      new parameter), you fix it in ONE place — the factory — not everywhere
      the object is used.
    - It makes testing easier: you can replace the factory with a fake version
      during tests without touching the rest of the code.

What is **kwargs?
    A special Python syntax that lets a function accept any number of keyword
    arguments without listing them explicitly.

    def create_config(**overrides):
        ...
    create_config(temperature=0.9)   # overrides = {"temperature": 0.9}
    create_config()                  # overrides = {}  (empty dict)

    Inside the function, `overrides` is just a regular dictionary.
    `.get("key", default)` returns the value if the key exists, or `default`.
================================================================================
"""

from google import genai
from google.genai import types

# What does `from config import ...` do?
#   It looks for a file called config.py in the Python path (in this case,
#   the project root) and imports only the listed names from it.
#   This avoids importing the entire file when we only need a few values.
from config import API_KEY, SYSTEM_PROMPT, TEMPERATURE, MAX_TOKENS


def create_client() -> genai.Client:
    """
    Instantiate and return an authenticated Gemini API client.

    What is genai.Client?
        It's the main object from the google-genai SDK. All API calls go
        through it (client.models.generate_content, client.models.list, etc.).
        Passing api_key= here tells the SDK which account to bill and authenticate.

    Return type annotation -> genai.Client:
        The arrow notation after the closing parenthesis declares what type
        this function returns. It's documentation — Python doesn't enforce it
        at runtime, but editors use it for autocomplete and type checkers use
        it to catch bugs.

    Old SDK vs new SDK:
        Old (deprecated): genai.configure(api_key=API_KEY)  ← sets a global variable
        New:              genai.Client(api_key=API_KEY)      ← explicit object

        The old approach modified global state, which makes testing harder and
        can cause unexpected behavior when multiple parts of a program try to
        use different keys. The new approach is explicit and self-contained.
    """
    return genai.Client(api_key=API_KEY)


def create_config(**overrides) -> types.GenerateContentConfig:
    """
    Build and return a GenerateContentConfig with generation parameters.

    What is GenerateContentConfig?
        An object that bundles all the "how should the model respond?" settings
        into a single package that gets passed to every generate_content() call.
        Think of it as the model's instruction sheet for a single request.

    Why not just pass temperature= and max_output_tokens= directly?
        The new google-genai SDK groups them into a config object. This makes
        the API call signature cleaner and the config reusable across calls.

    The **overrides pattern in practice:
        Default call (uses config.py values):
            create_config()

        Override temperature for one creative call:
            create_config(temperature=1.2)

        Override multiple parameters:
            create_config(temperature=0.0, max_output_tokens=512)

    Parameters:
        **overrides : Any keyword argument overrides config.py defaults.

    Returns:
        A types.GenerateContentConfig ready to pass as config= in API calls.
    """
    return types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        temperature=overrides.get("temperature", TEMPERATURE),
        max_output_tokens=overrides.get("max_output_tokens", MAX_TOKENS),
    )
