"""
================================================================================
main.py — Application Entry Point
================================================================================
Purpose:
    Provide an interactive menu that lets the user explore the three demo modes.
    This file has NO API logic and NO configuration — it only calls the gemini
    package and renders results to the terminal.

What does "entry point" mean?
    The entry point is the file you run directly: `python main.py`.
    It's the "front door" of the application. By keeping it thin (only
    presentation logic), we make it easy to swap the UI later — for example,
    replacing this terminal menu with a web interface or a CLI tool without
    touching any API code.

Provider-agnostic design:
    Notice that this file imports from the `gemini` package, but contains
    no Gemini-specific logic itself. If you later add an `anthropic` package
    with the same function names, you could switch providers by changing one
    import line.

Usage:
    python main.py
================================================================================
"""

# What is `from gemini import ...`?
#   This imports specific names from the gemini/ package (the folder with __init__.py).
#   Python runs gemini/__init__.py first, which in turn imports from the sub-modules.
#   The caller (this file) doesn't need to know which internal file each function
#   lives in — the package exposes a clean public interface.
from gemini import safe_chat, safe_stream_chat, safe_multi_turn_chat


# ── Presentation helpers ──────────────────────────────────────────────────────
# These two small functions exist to avoid repeating the same print formatting
# code in every demo. This is the DRY principle: "Don't Repeat Yourself."

def header(title: str) -> None:
    """Print a formatted section header to the terminal."""
    print(f"\n{'=' * 60}\n  {title}\n{'=' * 60}")
    # What is an f-string?
    #   f"..." is a "formatted string literal". Expressions inside {} are
    #   evaluated and inserted into the string at runtime.
    #   {'=' * 60} repeats the '=' character 60 times.


def footer(info: str = "") -> None:
    """Print a formatted section footer, with an optional info message."""
    if info:
        print(f"\n  ℹ {info}")
    print("─" * 60)
    # `info: str = ""` is a parameter with a DEFAULT VALUE.
    # If the caller doesn't pass `info`, it defaults to an empty string.
    # `if info:` is True for any non-empty string, False for "".


# ════════════════════════════════════════════════════════════════════════════════
# DEMO 1 — Simple Chat
# ════════════════════════════════════════════════════════════════════════════════

def demo_simple_chat() -> None:
    """
    Interactive loop for one-off questions with no conversation context.

    Each question is sent independently — the model doesn't remember what
    was asked before. This maps to simple_chat() → safe_chat() under the hood.

    What is a while True loop?
        An infinite loop that runs until explicitly stopped. Here we stop it
        with `break` when the user types /bye. This is the standard pattern
        for "keep doing something until the user says stop."

    What does .strip().lower() do?
        .strip() removes leading/trailing whitespace (spaces, newlines, tabs).
        .lower() converts the string to lowercase.
        Chained together: "  /BYE  ".strip().lower() → "/bye"
        This makes the exit command work regardless of spacing or capitalization.
    """
    header("DEMO 1 — Simple Chat")

    while True:
        prompt = input("\nYour question (or /bye to exit): ")
        if prompt.strip().lower() == "/bye":
            break

        result = safe_chat(prompt)

        # Accessing dict values: result["success"] reads the "success" key.
        if result["success"]:
            print(f"\nResponse:\n{result['response']}")
        else:
            print(f"\nError [{result['error_type']}]: {result['response']}")

    footer()


# ════════════════════════════════════════════════════════════════════════════════
# DEMO 2 — Streaming
# ════════════════════════════════════════════════════════════════════════════════

def demo_streaming() -> None:
    """
    Interactive loop where response tokens appear progressively as they arrive.

    The user experience difference vs Demo 1:
        Demo 1: you wait (sometimes several seconds), then the full text appears.
        Demo 2: text starts appearing almost immediately, token by token.

    For long responses, streaming feels much more responsive. This is why
    all major LLM chat interfaces (ChatGPT, Claude.ai, Gemini.com) use streaming.

    Notice that safe_stream_chat() prints tokens directly inside the function
    (via the default callback behavior). So we don't need to print result["response"]
    — the output has already been shown to the user during generation.
    We only need to check for errors AFTER the streaming finishes.
    """
    header("DEMO 2 — Streaming")

    while True:
        prompt = input("\nYour question (or /bye to exit): ")
        if prompt.strip().lower() == "/bye":
            break

        print("\nResponse (streaming):\n")
        result = safe_stream_chat(prompt)

        if not result["success"]:
            print(f"\nError [{result['error_type']}]: {result['response']}")
        else:
            print()   # add a blank line after the streamed output

    footer()


# ════════════════════════════════════════════════════════════════════════════════
# DEMO 3 — Multi-turn Chat
# ════════════════════════════════════════════════════════════════════════════════

def demo_multi_turn() -> None:
    """
    Conversational loop where the model remembers the full conversation.

    Key behaviors to observe while testing:
        - Ask a question, then follow up with "Can you elaborate on the first point?"
          The model knows what "the first point" refers to.
        - On error, the history is NOT corrupted — you can retry the same message.

    history = [] initializes an empty list.
        This list grows with each turn, holding all types.Content objects.
        It's passed into safe_multi_turn_chat() and the updated version is
        stored back in `history = result["history"]` after each successful turn.

    Why `history = result["history"]` instead of just reading history directly?
        safe_multi_turn_chat() works on a copy of the history internally.
        The updated history is returned in the result dict. We need to
        assign it back to our local `history` variable to keep it up to date.
    """
    header("DEMO 3 — Multi-turn Chat")
    print("\nStarting conversation. Type /bye to exit.\n")

    history = []   # starts empty; grows with each turn

    while True:
        prompt = input("You: ")
        if prompt.strip().lower() == "/bye":
            break

        result = safe_multi_turn_chat(history, prompt)

        if result["success"]:
            history = result["history"]   # update local history with new turns
            print(f"Gemini: {result['response']}\n")
        else:
            # history is NOT updated on failure — safe to retry the same prompt
            print(f"Error [{result['error_type']}]: {result['response']}\n")

    footer(f"Conversation ended. Total messages in history: {len(history)}")
    # len(history) returns the number of items in the list.
    # Each turn adds 2 items (one user + one model), so 6 turns = 12 items.


# ════════════════════════════════════════════════════════════════════════════════
# ENTRY POINT — if __name__ == "__main__"
# ════════════════════════════════════════════════════════════════════════════════

# What does if __name__ == "__main__" do?
#   Every Python file has a built-in variable called __name__.
#   When you RUN a file directly (python main.py), Python sets __name__ = "__main__".
#   When a file is IMPORTED by another module, __name__ is set to the module name.
#
#   This check means: "only run this block if the user ran THIS file directly."
#   It prevents the menu from popping up when main.py is imported as a module.
#   This is a universal Python convention — you'll see it in virtually every
#   Python script meant to be run directly.

if __name__ == "__main__":

    print("\n" + "=" * 60)
    print("  GEMINI API CLIENT — MODULAR DEMO")
    print("=" * 60)

    print("\nSelect a demo:")
    print("  1. Simple Chat     — single question, full response")
    print("  2. Streaming       — single question, token-by-token output")
    print("  3. Multi-turn Chat — conversation with accumulated context")

    choice = input("\nEnter the demo number: ").strip()

    # Dict-based dispatch — an alternative to if/elif chains.
    #
    # What is happening here?
    #   `demos` is a dictionary where keys are strings ("1", "2", "3") and
    #   VALUES are FUNCTION REFERENCES (not function calls — no parentheses).
    #   demo_simple_chat is the function itself; demo_simple_chat() would call it.
    #
    # Why use this instead of if/elif?
    #   - Adding a new demo means adding one line to the dict and one print() above.
    #   - No risk of forgetting an `elif` or misspelling a condition.
    #   - The dict lookup is O(1) — constant time regardless of how many options exist.
    #
    # demos[choice]() — how does this call a function?
    #   demos["1"] returns the demo_simple_chat function object.
    #   Adding () at the end calls it: demos["1"]()  ≡  demo_simple_chat()

    demos = {
        "1": demo_simple_chat,
        "2": demo_streaming,
        "3": demo_multi_turn,
    }

    if choice in demos:
        demos[choice]()   # look up the function and call it
    else:
        print(f"Invalid choice: '{choice}'. Please enter 1, 2, or 3.")

    print("\nDone.\n")
