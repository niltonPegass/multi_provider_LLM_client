"""
================================================================================
gemini/__init__.py — Package Initializer
================================================================================
What is __init__.py?
    When Python sees a folder that contains an __init__.py file, it treats that
    folder as a "package" — a collection of related modules that can be imported
    together.

    Without this file, `from gemini import safe_chat` would fail because Python
    wouldn't know that the gemini/ folder is meant to be a package.

What does this file do here?
    It re-exports the most commonly used names from the sub-modules so that
    callers (like main.py) can write:

        from gemini import safe_chat, safe_stream_chat, safe_multi_turn_chat

    instead of having to know which internal file each function lives in:

        from gemini.errors import safe_chat          # more verbose
        from gemini.errors import safe_stream_chat
        from gemini.errors import safe_multi_turn_chat

    This is the standard pattern for Python packages: internal structure can
    change without breaking code that imports from the package.

What is __all__?
    A list that explicitly declares which names are part of the package's
    public API. When someone writes `from gemini import *`, only the names
    in __all__ are imported. It also helps editors and linters understand
    what the package intentionally exposes.
================================================================================
"""

from gemini.errors import safe_chat, safe_stream_chat, safe_multi_turn_chat
from gemini.operations import simple_chat, stream_chat, multi_turn_chat
from gemini.client import create_client, create_config

__all__ = [
    # Safe wrappers (recommended for most use cases — never raise exceptions)
    "safe_chat",
    "safe_stream_chat",
    "safe_multi_turn_chat",
    # Core operations (raise on error — useful when you want full control)
    "simple_chat",
    "stream_chat",
    "multi_turn_chat",
    # Factories (useful if you need direct access to the client or config)
    "create_client",
    "create_config",
]
