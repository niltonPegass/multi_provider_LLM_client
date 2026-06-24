# llm-api-client

Modular Python client for the Google Gemini API. Covers authentication, streaming, multi-turn chat, and error handling via the official `google-genai` SDK.

Built as a hands-on study project to explore direct LLM API integration — going beyond high-level abstractions like N8N to understand what happens at the SDK and HTTP level.

---

## Project structure

```
llm-api-client/
├── config.py          # API key, model, temperature, system prompt
├── main.py            # Entry point — interactive menu, no API logic
├── list_models.py     # Utility: list models available for your key
├── my_api_keys.py     # Secret store (add to .gitignore)
├── requirements.txt
└── gemini/            # The Gemini API package
    ├── __init__.py    # Makes gemini/ a package; re-exports public functions
    ├── client.py      # Factories: create_client(), create_config()
    ├── operations.py  # Core API calls: simple, streaming, multi-turn
    └── errors.py      # Error handling and safe wrappers
```

### Why this structure?

Each file has a single, clear responsibility — a principle called **Separation of Concerns**:

| File | Knows about | Does NOT know about |
|---|---|---|
| `config.py` | Keys, model names, parameters | How those values are used |
| `gemini/client.py` | How to authenticate and configure | What questions to ask |
| `gemini/operations.py` | How to call the API | What to do when it fails |
| `gemini/errors.py` | How to handle failures | How the API works internally |
| `main.py` | How to display results | Anything about the Gemini API |

This means you can change how errors are handled without touching the API calls, or swap the model without touching the error logic.

---

## Quickstart

**1. Get a free API key** (no credit card required)

Go to [aistudio.google.com](https://aistudio.google.com) → Get API Key → Create API Key.

**2. Install the dependency**

```bash
pip install -r requirements.txt
# or
pipenv install -r requirements.txt
```

**3. Add your key**

Open `my_api_keys.py` and replace the placeholder:

```python
MY_GOOGLE_API_KEY = "AIzaSy-YOUR-KEY-HERE"
```

> Add `my_api_keys.py` to `.gitignore` before pushing to GitHub:
> ```bash
> echo "my_api_keys.py" >> .gitignore
> ```

**4. Check which models are available for your key**

```bash
python list_models.py
```

Copy the exact model name (including the `models/` prefix) and set it in `config.py`.

**5. Run**

```bash
python main.py
```

Select a demo from the menu: simple chat, streaming, or multi-turn conversation.

---

## Core concepts

### What is an API?

An API (Application Programming Interface) is a defined way for two programs to talk to each other. When you call the Gemini API, your Python script sends an HTTP request to Google's servers with your question, and receives a response with the model's answer — all over the internet, just like a browser loading a web page.

### Authentication

Every request carries your API key in an HTTP header (`x-goog-api-key`). The SDK handles this automatically when you pass `api_key=` to `genai.Client()`. If the key is wrong or missing, the server responds with **403 PERMISSION_DENIED**.

### Key generation parameters

| Parameter | What it controls |
|---|---|
| `model` | Which Gemini version handles the request |
| `system_instruction` | Persistent behavioral directive — the model's "job description" |
| `temperature` | Randomness: `0.0` = deterministic, `2.0` = very creative |
| `max_output_tokens` | Hard ceiling on response length (only generated tokens are billed) |

**What is a token?**
Text is split into small pieces called tokens before being processed by the model. In English, 1 token ≈ 4 characters (roughly ¾ of a word). "Hello, world!" is about 4 tokens. Tokens matter because APIs bill by token count, and models have a maximum context window (total tokens they can "see" at once).

### Streaming

In standard (synchronous) mode, you send a request and wait — sometimes several seconds — for the full response. With streaming, the server sends token chunks via **Server-Sent Events (SSE)** as the model generates them. Text starts appearing almost immediately.

This is how all major LLM chat interfaces work (ChatGPT, Claude.ai, Gemini.com). Under the hood, `generate_content_stream()` returns an **iterator** — an object you loop over, where each iteration yields the next chunk as it arrives.

### Multi-turn chat and the stateless API

The Gemini API has **no server-side memory** between calls. Every request is independent. To simulate a conversation, the client sends the **full conversation history** on every request:

```
Turn 1: contents = [user_msg_1]
Turn 2: contents = [user_msg_1, model_reply_1, user_msg_2]
Turn 3: contents = [all previous turns + user_msg_3]
```

Each turn in the history is a `types.Content` object with a `role` (`"user"` or `"model"`) and a list of `parts`. The token cost grows with each turn — you pay for the entire history every time.

### Python packages and `__init__.py`

When a folder contains an `__init__.py` file, Python treats it as a **package** — a collection of related modules. The `gemini/` folder in this project is a package. Its `__init__.py` re-exports the most useful functions, so callers can write:

```python
from gemini import safe_chat   # clean
```

instead of:

```python
from gemini.errors import safe_chat   # would also work, but exposes internal structure
```

### Error handling strategy — safe wrappers

The functions in `operations.py` raise exceptions when things go wrong. The **safe wrappers** in `errors.py` catch those exceptions and return a structured dictionary instead:

```python
result = safe_chat("What is backpropagation?")

if result["success"]:
    print(result["response"])
else:
    print(f"Error [{result['error_type']}]: {result['response']}")
```

This keeps `main.py` free of try/except blocks. The error classification lives in one place (`_handle_error()`), following the **DRY principle** (Don't Repeat Yourself).

**Gemini error types:**

| Exception | HTTP | Common causes |
|---|---|---|
| `ClientError` 403 | 403 | Invalid or missing API key |
| `ClientError` 429 | 429 | Rate limit or free-tier quota exhausted |
| `ClientError` | 4xx | Invalid model name, bad parameter |
| `ServerError` | 5xx | Temporary Google service outage |

### Dict-based dispatch (in `main.py`)

Instead of `if/elif` chains to map user input to functions, `main.py` uses a dictionary:

```python
demos = {
    "1": demo_simple_chat,   # function reference, not a call
    "2": demo_streaming,
    "3": demo_multi_turn,
}
demos[choice]()   # look up the function and call it
```

`demo_simple_chat` is the function object. `demo_simple_chat()` would call it immediately. By storing the reference, we can call it later. Adding a new demo means adding one entry to the dict — no if/elif to update.

### Relative imports inside a package

Inside the `gemini/` package, modules import from each other using a leading dot:

```python
from .client import create_client, create_config   # gemini/errors.py
```

The `.` means "look in the same package." This is called a **relative import** and works regardless of where the package is installed or what the project is named.

---

## SDK migration reference

This project uses the **new** `google-genai` package. The older `google.generativeai` is deprecated and no longer maintained.

| | Old SDK | New SDK |
|---|---|---|
| Package | `google-generativeai` | `google-genai` |
| Import | `import google.generativeai as genai` | `from google import genai` |
| Authentication | `genai.configure(api_key=)` — global | `genai.Client(api_key=)` — explicit |
| API call | `model.generate_content()` | `client.models.generate_content()` |
| Errors | `google.api_core.exceptions` (external package) | `google.genai.errors` (built-in) |

---

## Free tier limits (Gemini 2.5 Flash, approximate)

| Limit | Value |
|---|---|
| Requests per minute (RPM) | 10 |
| Tokens per minute (TPM) | 250,000 |
| Requests per day | 500 |

For experimentation these limits are more than sufficient. Check current numbers at [ai.dev/rate-limit](https://ai.dev/rate-limit).

---

## Related projects

This client is part of a broader portfolio covering direct LLM API integration:
- **Anthropic SDK version** — same architecture targeting Claude models
- **RAG pipeline** — LangChain + LangGraph + local inference via Ollama
