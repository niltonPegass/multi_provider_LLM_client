"""
================================================================================
main.py — Entry Point and Orchestration
================================================================================
Purpose:
    Run the three API demos interactively. This module has no API logic and no
    configuration — it only calls api_client.py and renders results.

    This file is intentionally provider-agnostic: swapping Gemini for another
    LLM only requires changing the imports below, not any logic here.

Demos:
    1. Simple Chat    — single question, full response
    2. Streaming      — single question, token-by-token output
    3. Multi-turn     — conversation with accumulated context

Usage:
    python main.py
================================================================================
"""

from api_client import (
    safe_chat,
    safe_stream_chat,
    safe_multi_turn_chat,
)


# ── Presentation helpers ──────────────────────────────────────────────────────

def header(title: str) -> None:
    print(f"\n{'=' * 60}\n  {title}\n{'=' * 60}")


def footer(info: str = "") -> None:
    if info:
        print(f"\n  ℹ {info}")
    print("─" * 60)


# ════════════════════════════════════════════════════════════════════════════════
# DEMO 1 — Simple Chat
# ════════════════════════════════════════════════════════════════════════════════

def demo_simple_chat() -> None:
    """
    Interactive loop for one-off questions. Each question is independent —
    the model has no memory of previous turns in this mode.
    Type /bye to exit.
    """
    header("DEMO 1 — Simple Chat")

    while True:
        prompt = input("\nYour question (or /bye to exit): ")
        if prompt.strip().lower() == "/bye":
            break

        result = safe_chat(prompt)

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
    Interactive loop with token-by-token streaming output.
    Tokens are printed to the terminal as they arrive via SSE.
    Type /bye to exit.
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
            print()  # newline after streaming output

    footer()


# ════════════════════════════════════════════════════════════════════════════════
# DEMO 3 — Multi-turn Chat
# ════════════════════════════════════════════════════════════════════════════════

def demo_multi_turn() -> None:
    """
    Conversational loop with accumulated context.

    The full conversation history is resent on every API call (stateless API).
    Token cost grows with each turn. On error, history is not modified so the
    same turn can be retried safely.
    Type /bye to exit.
    """
    header("DEMO 3 — Multi-turn Chat")
    print("\nStarting conversation. Type /bye to exit.\n")

    history = []

    while True:
        prompt = input("You: ")
        if prompt.strip().lower() == "/bye":
            break

        result = safe_multi_turn_chat(history, prompt)

        if result["success"]:
            history = result["history"]
            print(f"Gemini: {result['response']}\n")
        else:
            print(f"Error [{result['error_type']}]: {result['response']}\n")

    footer(f"Conversation ended. Total messages in history: {len(history)}")


# ════════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ════════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    """
    if __name__ == "__main__" ensures this block only runs when the file is
    executed directly (python main.py), not when it is imported as a module.
    This allows demo_* functions to be reused in other scripts without
    triggering the menu.
    """
    print("\n" + "=" * 60)
    print("  GEMINI API CLIENT — MODULAR DEMO")
    print("=" * 60)

    print("\nSelect a demo:")
    print("  1. Simple Chat       — single question, full response")
    print("  2. Streaming         — single question, token-by-token output")
    print("  3. Multi-turn Chat   — conversation with context")

    choice = input("\nEnter the demo number: ").strip()

    # Dict-based dispatch: maps input string to function reference.
    # Cleaner than if/elif chains and trivially extensible.
    demos = {
        "1": demo_simple_chat,
        "2": demo_streaming,
        "3": demo_multi_turn,
    }

    if choice in demos:
        demos[choice]()
    else:
        print("Invalid choice.")

    print("\nDone.\n")
