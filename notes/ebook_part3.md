# Building LLM API Clients in Python — A Hands-on Guide

## Part 3 — Communication Patterns

> Chapters 7, 8, and 9
> Covers: synchronous calls in depth, streaming via SSE, and multi-turn conversations

---

# Chapter 7: Synchronous Calls

## 7.1 What "Synchronous" Really Means

The word **synchronous** comes from Greek: *syn* (together) + *chronos* (time). In programming, synchronous means "things happen in sequence, one at a time, in order."

When Python executes a synchronous function call, it:
1. Calls the function
2. Waits — doing nothing else — until the function returns
3. Continues to the next line

For most operations this is invisible — functions return in microseconds. But network calls are different. A Gemini API call typically takes between 0.5 and 5 seconds. During that entire window, a synchronous program is frozen.

```python
print("Sending request...")
response = client.models.generate_content(...)   # ← program is frozen here
print("Response received!")                       # ← only runs after full response
```

This is called **blocking** — the call blocks execution until it completes.

For a learning project and for scripts, blocking is perfectly fine. For a web server handling many simultaneous users, it becomes a problem (covered in Part 6). Understanding the distinction now will make async patterns much easier to grasp when you encounter them.

---

## 7.2 The Request-Response Cycle in Detail

Every synchronous call goes through these stages:

```
Your script                    Network                    Google's servers
─────────────────────────────────────────────────────────────────────────
1. Build request object
2. Serialize to JSON
3. Open TCP connection   ──────────────────────────────►  4. Accept connection
                                                          5. Authenticate API key
                                                          6. Validate parameters
                                                          7. Route to model
                                                          8. Generate tokens (time-consuming)
                                                          9. Serialize response to JSON
10. Receive response     ◄──────────────────────────────  10. Send response
11. Deserialize JSON
12. Build response object
13. Return response.text
```

Steps 3 through 10 happen over the network — everything else is local Python execution. The vast majority of your waiting time is step 8 (token generation).

---

## 7.3 simple_chat() Dissected

Here is `simple_chat()` with granular commentary on every decision:

```python
def simple_chat(prompt: str) -> str:
    client = create_client()
    config = create_config()

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=config,
    )
    return response.text
```

**Why `contents=prompt` accepts a plain string:**

The `contents` parameter is flexible. The SDK accepts:

```python
# A plain string (simplest — what we use for single messages)
contents="What is a neural network?"

# A list of strings (multiple user messages without role info)
contents=["context sentence", "actual question"]

# A list of types.Content objects (full structured conversation)
contents=[
    types.Content(role="user",  parts=[types.Part(text="Hello")]),
    types.Content(role="model", parts=[types.Part(text="Hi!")]),
    types.Content(role="user",  parts=[types.Part(text="What is ML?")]),
]
```

For `simple_chat()`, a plain string is converted internally by the SDK into the full `types.Content` structure. This convenience conversion is why we can write `contents=prompt` instead of the more verbose form.

**Why we return `response.text` and not the full response:**

`simple_chat()` is a focused function that does one thing: get the text of a response. Returning the raw response object would expose internal SDK types to callers, creating a tighter coupling between `main.py` and the SDK. By returning a plain `str`, we keep the interface clean — the caller doesn't need to know anything about `GenerateContentResponse`, `candidates`, or `parts`.

This is called **encapsulation** — hiding internal complexity behind a simple interface.

---

## 7.4 Useful Fields on the Response Object

Even though we only use `response.text` in the project, the full response object is rich with information. These are worth knowing as you build more sophisticated applications:

```python
response = client.models.generate_content(
    model=MODEL,
    contents="Explain the bias-variance tradeoff in three sentences.",
    config=config,
)

# ── The text ──────────────────────────────────────────────────────────────────
response.text
# → "The bias-variance tradeoff describes..."

# ── Token accounting ──────────────────────────────────────────────────────────
response.usage_metadata.prompt_token_count
# → 14  (tokens in your prompt)

response.usage_metadata.candidates_token_count
# → 89  (tokens in the response)

response.usage_metadata.total_token_count
# → 103  (prompt + response)

# ── Why generation stopped ────────────────────────────────────────────────────
response.candidates[0].finish_reason
# → "STOP"     — finished naturally
# → "MAX_TOKENS" — cut off at max_output_tokens limit
# → "SAFETY"   — content blocked by safety filters
# → "RECITATION" — contained too much copyrighted material

# ── Safety ratings (per category) ─────────────────────────────────────────────
response.candidates[0].safety_ratings
# → list of SafetyRating objects, one per harm category
#   (HARM_CATEGORY_HARASSMENT, SEXUALLY_EXPLICIT, DANGEROUS_CONTENT, etc.)

# ── The full structured content ───────────────────────────────────────────────
response.candidates[0].content.parts[0].text
# → same as response.text, the long way
```

**A diagnostic wrapper you can add to your own experiments:**

```python
def simple_chat_verbose(prompt: str) -> str:
    client = create_client()
    config = create_config()

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=config,
    )

    u = response.usage_metadata
    print(f"  finish : {response.candidates[0].finish_reason}")
    print(f"  tokens : {u.prompt_token_count} in / "
          f"{u.candidates_token_count} out / "
          f"{u.total_token_count} total")

    return response.text
```

Run this during development to get a feel for how many tokens your prompts and responses consume.

---

## 7.5 When Synchronous is the Right Choice

Synchronous calls are appropriate when:

- **You are writing a script**, not a server. Scripts run one task at a time by nature.
- **The caller can afford to wait.** A terminal interaction where the user types and waits is fine.
- **You are processing a batch sequentially.** Running 50 prompts one after another with `for prompt in prompts: result = simple_chat(prompt)` is simple, readable, and correct.
- **You are learning.** Synchronous code is significantly easier to reason about than asynchronous code.

Synchronous calls become a problem when:
- A web server needs to handle many users simultaneously.
- You want to process a large batch as fast as possible in parallel.
- You want to do other work while waiting for the API response.

For now, synchronous is the right mental model. When you are ready for async, the concepts from this chapter will transfer directly — the difference is syntactic (`await` in front of the call), not conceptual.

---

# Chapter 8: Streaming and Server-Sent Events

## 8.1 The Problem Streaming Solves

Imagine asking the model a complex question that requires a 500-token response. At a typical generation speed of 50–100 tokens per second, that's 5–10 seconds of waiting before you see a single character.

Now imagine a chat interface where you watch the response being "typed" in real time, starting almost immediately. That is streaming — and it is the difference between a frustrating and a fluid user experience.

Streaming does not make the model faster. It makes latency *perceived* as lower by delivering tokens to the user as they are generated, rather than waiting for the complete response.

---

## 8.2 Server-Sent Events (SSE)

The technical mechanism behind streaming is **Server-Sent Events (SSE)** — a standard protocol for servers to push data to clients over a persistent HTTP connection.

In a normal HTTP exchange:
```
Client → sends request → Server
Client ← receives full response ← Server
Connection closes
```

With SSE:
```
Client → sends request → Server
Client ← chunk 1 ← Server (connection stays open)
Client ← chunk 2 ← Server
Client ← chunk 3 ← Server
...
Client ← final chunk ← Server
Connection closes
```

The connection stays open and the server "streams" chunks of data as they become available. Each chunk is a small piece of the eventual full response — in our case, a few tokens of generated text.

SSE is a one-way protocol: the server pushes data to the client, but the client does not send anything back after the initial request. This is different from WebSockets, which allow bidirectional real-time communication.

---

## 8.3 How the SDK Handles SSE

The SDK hides the SSE complexity behind a clean Python interface. Internally it:

1. Sends the HTTP request with streaming enabled
2. Keeps the connection open
3. Parses incoming SSE data packets
4. Yields each parsed chunk as a Python object

From our perspective, we just iterate:

```python
for chunk in client.models.generate_content_stream(
    model=MODEL,
    contents=prompt,
    config=config,
):
    print(chunk.text, end="", flush=True)
```

Each time the `for` loop asks for the next item, Python resumes the SDK's internal iterator, which waits for the next SSE chunk from the server, parses it, and returns it as a chunk object.

---

## 8.4 Iterators: The Python Concept Behind Streaming

To understand streaming at the Python level, you need to understand **iterators**.

An **iterable** is any object you can loop over — lists, strings, files, ranges:

```python
for item in [1, 2, 3]:     # list is iterable
    print(item)

for char in "hello":        # string is iterable
    print(char)

for line in open("file.txt"):  # file is iterable
    print(line)
```

An **iterator** is an object that knows how to produce the next value on demand. Under the hood, `for item in something` calls `iter(something)` to get an iterator, then repeatedly calls `next(iterator)` until it raises `StopIteration`.

The streaming response from `generate_content_stream()` is an iterator. Each call to `next()` (which happens implicitly in the `for` loop) does the following:

1. Checks if there is already a buffered chunk
2. If not, waits for the next SSE packet from the network
3. Parses it into a chunk object
4. Returns it

This is why the loop "pauses" naturally between chunks — it is literally waiting for the next piece of data to arrive from Google's servers.

---

## 8.5 stream_chat() Dissected

```python
def stream_chat(prompt: str, callback=None) -> str:
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
```

**`full_text = ""`**

We initialize an empty string before the loop. Inside the loop, `full_text += chunk.text` appends each chunk to it. After the loop, `full_text` contains the entire response. We return it so the caller has access to the complete text even though it was already printed chunk by chunk.

**`chunk.text`**

Each chunk object has a `.text` attribute containing the fragment of text received in this iteration. It might be a single word, a partial word, or a few words — the granularity depends on the model and the network.

**`end=""` in `print()`**

By default, `print()` appends a newline character (`\n`) after each call:

```python
print("hello")
print("world")
# Output:
# hello
# world
```

With `end=""`, the newline is suppressed:

```python
print("hello", end="")
print("world", end="")
# Output:
# helloworld
```

This is what makes tokens appear side by side on the same line — simulating the "typing" effect.

**`flush=True`**

Python's print output goes to a **buffer** — a temporary memory region that collects characters before writing them to the terminal. Buffering is an optimization: writing to the terminal (or a file) is slow, so Python batches writes.

For streaming, buffering is counterproductive — we want to display each token immediately. `flush=True` forces the buffer to be written to the terminal after every `print()` call, ensuring tokens appear as soon as they arrive.

**The `callback` parameter**

```python
if callback:
    callback(chunk.text)
else:
    print(chunk.text, end="", flush=True)
```

`callback` is an **optional function** — a function passed as an argument, to be called at a specific point.

`if callback:` is True when a function was passed, False when `None` was passed (the default). In Python, `None` is falsy — `if None:` evaluates to `False`.

Why offer a callback?

The terminal is only one possible destination for streamed tokens. In a web application, you might want to send each token over a WebSocket. In a logging system, you might write to a file. The callback makes `stream_chat()` adaptable without modification:

```python
# Default: prints to terminal
stream_chat("What is DBSCAN?")

# Custom: sends to a WebSocket
def send_to_websocket(chunk: str):
    websocket.send(chunk)

stream_chat("What is DBSCAN?", callback=send_to_websocket)

# Custom: appends to a file
chunks = []
stream_chat("What is DBSCAN?", callback=chunks.append)
```

Note the last example: `chunks.append` is a method reference — passing the method itself, not calling it. `chunks.append(chunk.text)` would call it immediately; `chunks.append` passes it as a callable for `stream_chat()` to call later. This is the same distinction as `demo_simple_chat` vs. `demo_simple_chat()` in `main.py`'s dispatch table.

---

## 8.6 Streaming vs. Synchronous: When to Use Each

| Situation | Use |
|---|---|
| Terminal script, user watches response build | `stream_chat()` |
| Batch processing, result stored in variable | `simple_chat()` |
| Web UI (browser watching text appear) | `stream_chat()` with callback |
| Testing or automated comparison of responses | `simple_chat()` |
| Long response where user might cancel mid-way | `stream_chat()` |
| Short responses (< 1 second total) | Either — difference is imperceptible |

---

## 8.7 A Note on Streaming Errors

If an error occurs partway through streaming — for example, hitting the rate limit after the first few chunks have already been sent — partial output has already been delivered (printed to terminal or sent via callback) before the exception fires.

This is a known trade-off with streaming. In `safe_stream_chat()`, the error dict is returned with `success=False`, but the user may have already seen partial text. For most interactive use cases this is acceptable. For applications where partial output is problematic, consider buffering the full streamed response before displaying it — at which point you might as well use `simple_chat()`.

---

# Chapter 9: Multi-turn Conversations and Stateless APIs

## 9.1 What is a "Turn"?

In a conversation, a **turn** is one exchange: one party speaks, the other responds. In the context of LLM APIs:

- **User turn:** a message with `role="user"`
- **Model turn:** a response with `role="model"` (Gemini) or `role="assistant"` (OpenAI, Anthropic)

A conversation is an alternating sequence of turns:

```
Turn 1: user   → "What is gradient descent?"
Turn 2: model  → "Gradient descent is an optimization algorithm..."
Turn 3: user   → "Can you give a concrete example?"
Turn 4: model  → "Sure. Imagine you're trying to minimize..."
```

---

## 9.2 The Stateless API Problem

This is one of the most important concepts in API development. The Gemini API (like virtually all REST APIs) is **stateless**: the server stores no memory of previous requests.

From the server's perspective, every request is from a stranger it has never met.

This means that after Turn 2, if you send Turn 3's question by itself:

```python
response = client.models.generate_content(
    model=MODEL,
    contents="Can you give a concrete example?",  # ← server has no context
    config=config,
)
```

The model has no idea what "a concrete example" refers to. It might answer generically, ask for clarification, or produce a confused response.

**The solution: send the full history with every request.**

```python
# Turn 3 must include all previous turns
response = client.models.generate_content(
    model=MODEL,
    contents=[
        types.Content(role="user",  parts=[types.Part(text="What is gradient descent?")]),
        types.Content(role="model", parts=[types.Part(text="Gradient descent is...")]),
        types.Content(role="user",  parts=[types.Part(text="Can you give a concrete example?")]),
    ],
    config=config,
)
```

The model processes all three turns together and generates Turn 4's response with full context.

---

## 9.3 The types.Content Structure

Each turn in the conversation history is represented as a `types.Content` object:

```python
types.Content(
    role="user",                         # who sent this message
    parts=[types.Part(text="Hello")]     # list of content pieces
)
```

**`role`** — two valid values in Gemini:
- `"user"` — messages from the human
- `"model"` — messages from the AI

Note: OpenAI and Anthropic use `"assistant"` instead of `"model"`. This is a common source of bugs when adapting code between providers.

**`parts`** — a list of `types.Part` objects. For text conversations, this is always a single-element list:

```python
parts=[types.Part(text="Your message here")]
```

The list structure exists because a message can contain multiple content types simultaneously — text plus an image, or text plus a function call result. For plain text, one Part is always sufficient.

**Why not just use a dict?**

You could imagine using plain dictionaries:
```python
{"role": "user", "content": "Hello"}
```

The `types.Content` object provides:
- **Type safety:** your editor knows what fields are valid
- **Validation:** the SDK can catch malformed content before sending
- **Future compatibility:** if the Content structure gains new fields, the object's interface handles it cleanly

---

## 9.4 multi_turn_chat() Dissected

```python
def multi_turn_chat(history: list, new_message: str) -> tuple[str, list]:
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
```

**`history: list`**

The type hint `list` says this parameter expects a list. In `main.py`, we start with `history = []` (an empty list) and pass it into `multi_turn_chat()` on every turn.

**`history.append(...)`**

`list.append(item)` adds `item` to the end of the list, **modifying the list in place**. This is called a **mutation** — the original list object is changed, not replaced.

```python
history = []
history.append("a")   # history is now ["a"]
history.append("b")   # history is now ["a", "b"]
```

Because lists are mutable and Python passes them by reference, the `history` variable in `main.py` and the `history` parameter inside `multi_turn_chat()` point to the same underlying list object. When we call `history.append()` inside the function, we are modifying the same list that `main.py` holds.

This is why in `safe_multi_turn_chat()`, we make a copy before calling `multi_turn_chat()`:

```python
history_copy = list(history)   # create a new list with the same contents
```

If the API call fails, `history_copy` was modified (the user turn was appended) but `history` — the original in `main.py` — was not. The caller's history remains consistent and the turn can be retried.

**`return response_text, history`**

This returns two values at once as a **tuple**. In Python, you can return multiple values by separating them with commas:

```python
return response_text, history
# equivalent to:
return (response_text, history)
```

The caller unpacks it:
```python
response_text, updated_history = multi_turn_chat(history, message)
```

This single line assigns both returned values to separate variables simultaneously.

---

## 9.5 How History Grows with Each Turn

Let's trace a three-turn conversation to make the growing history concrete:

**Initial state:**
```python
history = []
```

**Turn 1:** User asks "What is XGBoost?"

```python
# Before API call — after first append:
history = [
    Content(role="user", parts=[Part(text="What is XGBoost?")])
]

# After API call — after second append:
history = [
    Content(role="user",  parts=[Part(text="What is XGBoost?")]),
    Content(role="model", parts=[Part(text="XGBoost is a gradient boosting...")])
]
```

**Turn 2:** User asks "How does it differ from Random Forest?"

```python
# Before API call — after first append:
history = [
    Content(role="user",  parts=[Part(text="What is XGBoost?")]),
    Content(role="model", parts=[Part(text="XGBoost is a gradient boosting...")]),
    Content(role="user",  parts=[Part(text="How does it differ from Random Forest?")])
]

# API receives ALL THREE turns — model has full context
# After API call — after second append:
history = [
    Content(role="user",  parts=[Part(text="What is XGBoost?")]),
    Content(role="model", parts=[Part(text="XGBoost is a gradient boosting...")]),
    Content(role="user",  parts=[Part(text="How does it differ from Random Forest?")]),
    Content(role="model", parts=[Part(text="While both are ensemble methods...")])
]
```

**Turn 3:** User asks "Which should I use for tabular data?"

The API now receives five turns (all previous + new). The model can refer back to everything discussed earlier.

---

## 9.6 Token Cost Implication

Because the full history is sent with every request, token consumption grows with each turn:

| Turn | Tokens sent (approximate) |
|---|---|
| 1 | prompt_tokens (Turn 1 only) |
| 2 | prompt_tokens (Turns 1–2) |
| 3 | prompt_tokens (Turns 1–3) |
| N | prompt_tokens (all N turns) |

For short conversations (5–10 turns), this is negligible. For long conversations (50+ turns with detailed responses), the cumulative context can become expensive and eventually hit the model's context window limit.

**Strategies for long conversations:**

1. **Summarization:** Periodically ask the model to summarize the conversation so far, replace the history with that summary, and continue. This compresses the context.

2. **Sliding window:** Keep only the last N turns in history, discarding older ones. The model loses early context but stays within token limits.

3. **Selective retention:** Identify which turns are important (key facts, decisions) and keep only those.

For a learning project, you will not hit these limits. But understanding them is essential before building production applications.

---

## 9.7 The safe_multi_turn_chat() Wrapper and the Copy Problem

In `gemini/errors.py`:

```python
def safe_multi_turn_chat(history: list, new_message: str) -> dict:
    history_copy = list(history)

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
        result["history"] = history   # original, unmodified
        return result
```

**The problem this solves:**

`multi_turn_chat()` appends the user message to `history` **before** making the API call:

```python
history.append(Content(role="user", ...))   # ← modifies history

response = client.models.generate_content(...)   # ← might fail here

history.append(Content(role="model", ...))   # ← if API fails, never reaches here
```

If the API call fails, history is in an inconsistent state — it has the user's message but no model reply. The next call would send a malformed conversation (ending with a user turn that was never answered).

**The solution:**

```python
history_copy = list(history)
```

`list(iterable)` creates a new list containing the same elements. We pass `history_copy` to `multi_turn_chat()`. If it fails, `history_copy` is the corrupted one — `history` (the original in `main.py`) is untouched.

**Shallow copy vs. deep copy:**

`list(history)` creates a **shallow copy** — a new list object, but the elements inside are still the same objects (same references in memory).

```python
original = [obj_a, obj_b]
copy = list(original)

# copy is a different list object
copy is original   # → False

# but the elements are the same objects
copy[0] is original[0]   # → True
```

For our use case, this is sufficient. We never modify the `types.Content` objects themselves — we only append new ones to the list. So shallow copying the list protects us.

If we were modifying the objects inside the list, we would need `copy.deepcopy()` — but that situation does not arise here.

---

## 9.8 How main.py Manages History

In `demo_multi_turn()`:

```python
history = []

while True:
    prompt = input("You: ")
    if prompt.strip().lower() == "/bye":
        break

    result = safe_multi_turn_chat(history, prompt)

    if result["success"]:
        history = result["history"]   # ← update history with new turns
        print(f"Gemini: {result['response']}\n")
    else:
        # history is NOT updated on failure
        print(f"Error [{result['error_type']}]: {result['response']}\n")
```

On each successful turn, `history = result["history"]` replaces the local `history` variable with the updated list returned by `safe_multi_turn_chat()`. On failure, we skip this assignment — `history` retains its last known good state, and the user can retry the same prompt.

This is a clean state management pattern for a simple interactive loop. In more complex applications (web servers, async systems), you would store history in a database or session store rather than a local variable.

---

## Part 3 Summary

| Concept | One-line summary |
|---|---|
| Synchronous call | Execution blocks until the full response arrives |
| Blocking | A call that prevents other code from running while it waits |
| Request-response cycle | Client sends request, server processes, client receives response |
| Encapsulation | Hiding complexity behind a simple interface (returning `str` not raw response) |
| Streaming | Delivering tokens progressively via a persistent HTTP connection |
| Server-Sent Events (SSE) | Protocol for servers to push data chunks to clients over HTTP |
| Iterator | Object that yields values one at a time on demand |
| `end=""` in print() | Suppresses the automatic newline after each print call |
| `flush=True` | Forces buffered output to be written to the terminal immediately |
| Callback | A function passed as an argument, called at a specific moment |
| Stateless API | Server stores no memory between requests |
| `types.Content` | Structured object representing one conversation turn |
| `role` | `"user"` or `"model"` — identifies who sent a turn |
| `list.append()` | Adds an item to the end of a list, modifying it in place |
| Mutation | Changing an object in place (vs. creating a new one) |
| Tuple return | Returning multiple values at once: `return a, b` |
| Shallow copy | New list object, same element references: `list(original)` |
| Token cost growth | Each turn bills ALL accumulated history — cost grows with conversation length |

---

*Next: Part 4 — Writing Robust Code (Chapters 10, 11, and 12)*
*Exception hierarchy, the safe wrapper pattern, and software design principles.*

