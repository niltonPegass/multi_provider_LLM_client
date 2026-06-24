"""
================================================================================
gemini/operations.py — Core API Operations
================================================================================
Responsibility:
    Implement the three fundamental ways to communicate with the Gemini API:
      1. simple_chat()     → one message, wait for full response
      2. stream_chat()     → one message, receive tokens as they arrive
      3. multi_turn_chat() → ongoing conversation with history

Design decision — no error handling here:
    These functions let exceptions propagate to the caller. This is intentional.
    Error handling lives in errors.py (the safe_* wrappers), keeping each file
    focused on a single responsibility.

    This follows the principle of "Separation of Concerns":
    operations.py  → knows HOW to call the API
    errors.py      → knows WHAT to do when things go wrong

What is a "tuple" return type?  tuple[str, list]
    A tuple is an ordered, immutable collection of values.
    `tuple[str, list]` means this function returns TWO values at once:
    the first is a string, the second is a list.

    In Python you can "unpack" a tuple directly:
        response_text, updated_history = multi_turn_chat(history, message)
    Both variables are assigned in a single line.

What does -> None mean?
    It means the function returns nothing (no return statement with a value).
    Used for functions that only produce side effects, like printing to screen.
================================================================================
"""

from google.genai import types

# Relative import: the leading dot means "look in the same package (gemini/)".
# `from .client import ...` is equivalent to `from gemini.client import ...`
# but works regardless of how the package is installed or where it is on disk.
from .client import create_client, create_config
from config import MODEL


def simple_chat(prompt: str) -> str:
    """
    Send a single message and return the complete response text.

    This is the most straightforward API pattern: send → wait → receive.
    The HTTP connection stays open until the server sends the full response,
    then closes. This is called a "synchronous" or "blocking" call.

    When to use:
        One-off questions, scripts that process a batch of prompts, or any
        situation where you don't need the user to see partial output.

    When NOT to use:
        Long responses where the user would benefit from seeing text appear
        progressively — use stream_chat() for that.

    About response.text:
        The full response object (response) contains a lot of metadata.
        response.text is a convenient shortcut provided by the SDK that
        extracts just the text content. Under the hood it accesses:
            response.candidates[0].content.parts[0].text

        Other useful fields you can explore:
            response.usage_metadata.prompt_token_count     → tokens in your prompt
            response.usage_metadata.candidates_token_count → tokens in the response
            response.candidates[0].finish_reason  → why generation stopped:
                STOP       = model finished naturally
                MAX_TOKENS = hit the max_output_tokens limit
                SAFETY     = content was blocked by safety filters

    Parameters:
        prompt : The user's message as a plain string.

    Returns:
        The model's response as a plain string.

    Raises:
        gemini_errors.ClientError → on 4xx errors (auth, rate limit, bad request)
        gemini_errors.ServerError → on 5xx errors (Google service issues)
    """
    client = create_client()
    config = create_config()

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,   # for a single message, a plain string works fine
        config=config,
    )
    return response.text


def stream_chat(prompt: str, callback=None) -> str:
    """
    Send a single message and receive tokens progressively (streaming).

    How streaming works under the hood:
        Instead of waiting for the full response, the HTTP connection stays
        open and the server continuously sends small data packets called
        "chunks" as the model generates each token. This technique is called
        Server-Sent Events (SSE).

        The SDK's generate_content_stream() returns an ITERATOR — an object
        you can loop over with `for chunk in ...`. Each iteration gives you
        the next chunk as it arrives from the server.

    What is an iterator?
        An object that produces values one at a time, on demand. You've seen
        this pattern before: `for line in file` reads lines lazily, one by one,
        without loading the entire file into memory. Same idea here.

    What is `end=""` in print()?
        By default, print() adds a newline (\n) after each call.
        `end=""` overrides that, so tokens are printed side by side on the
        same line — simulating the "typing" effect you see in chat interfaces.

    What is `flush=True`?
        Python buffers print output for efficiency, which means it might hold
        characters in memory and print them in batches. `flush=True` forces
        the buffer to be emptied immediately after each chunk, so the user
        sees each token the moment it arrives.

    The callback parameter — what is a "callback"?
        A callback is a function you pass as an argument to another function,
        to be called at a specific moment. Here, callback is called once per
        chunk. This lets callers decide what to DO with each chunk:
            - Print to terminal (default behavior)
            - Send to a WebSocket for a browser UI
            - Append to a log file
            - Anything else

        If no callback is provided (None), the function falls back to printing.
        None is Python's way of saying "no value" / "optional, not provided".

    Parameters:
        prompt   : The user's message as a plain string.
        callback : Optional function with signature callback(chunk: str) -> None.

    Returns:
        The full accumulated response text (all chunks joined).

    Raises:
        gemini_errors.ClientError / ServerError on API failure.
    """
    client = create_client()
    config = create_config()
    full_text = ""

    for chunk in client.models.generate_content_stream(
        model=MODEL,
        contents=prompt,
        config=config,
    ):
        # chunk.text contains the fragment of text received in this iteration
        full_text += chunk.text   # += appends to the string (same as full_text = full_text + chunk.text)

        if callback:
            callback(chunk.text)
        else:
            print(chunk.text, end="", flush=True)

    return full_text


def multi_turn_chat(history: list, new_message: str) -> tuple[str, list]:
    """
    Send a message within an ongoing conversation and return the updated history.

    The stateless API problem — and how we solve it:
        The Gemini API has NO server-side memory between calls. Every request
        is completely independent, like the server sees you for the first time.

        To simulate a conversation (where the model "remembers" what was said),
        we send the ENTIRE conversation history on every request.

        Turn 1: contents = [user_msg_1]
        Turn 2: contents = [user_msg_1, model_reply_1, user_msg_2]
        Turn 3: contents = [user_msg_1, model_reply_1, user_msg_2, model_reply_2, user_msg_3]

        This means token cost grows with each turn — you're paying for all
        previous messages every time. For very long conversations (50+ turns),
        consider summarizing older context.

    What is types.Content?
        Each turn in the history is a types.Content object. It has two fields:
            role  : WHO sent this message. Either "user" or "model".
                    Note: Gemini uses "model", while OpenAI and Anthropic use "assistant".
            parts : A LIST of content pieces. For plain text, it's one Part with .text.
                    The list structure exists because a message could contain both
                    text and an image, for example.

        So a single user turn looks like:
            types.Content(
                role="user",
                parts=[types.Part(text="What is machine learning?")]
            )

    Why does this function return a tuple?
        It returns BOTH the response text AND the updated history.
        The caller (main.py or errors.py) needs the updated history to pass
        into the next turn. Returning both avoids the caller having to
        re-construct the history themselves.

    list.append() — what does it do?
        Adds one item to the END of a list, modifying it in place.
        history.append(item) changes the history list directly — it doesn't
        create a new list. This is called a "mutation" or "side effect".

    Parameters:
        history     : List of types.Content from previous turns. Pass [] to start.
        new_message : The new user message as a plain string.

    Returns:
        (response_text, updated_history) as a tuple.
        updated_history has the new user turn and model reply appended.

    Raises:
        gemini_errors.ClientError / ServerError on API failure.
    """
    client = create_client()
    config = create_config()

    # Add the new user message to the history before sending
    history.append(
        types.Content(role="user", parts=[types.Part(text=new_message)])
    )

    response = client.models.generate_content(
        model=MODEL,
        contents=history,   # the full history is sent here
        config=config,
    )

    response_text = response.text

    # Add the model's reply so the next call has the full context
    history.append(
        types.Content(role="model", parts=[types.Part(text=response_text)])
    )

    return response_text, history
