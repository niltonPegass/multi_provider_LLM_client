# llm-api-client

Modular Python client for Anthropic Claude and Google Gemini APIs. Covers authentication, streaming, multi-turn chat, and error handling via official SDKs.

Built as a hands-on study project to explore direct LLM API integration — going beyond high-level abstractions like N8N to understand what happens at the SDK level.

---

## Project structure

```
llm-api-client/
├── config.py          # API key, model name, temperature, system prompt
├── api_client.py      # All API communication logic (the only file that talks to Gemini)
├── main.py            # Entry point — interactive menu, no API logic
├── list_models.py     # Utility: list models available for your API key
├── my_api_keys.py     # Secret store (git-ignored)
└── requirements.txt   # Dependencies
```

`main.py` is intentionally provider-agnostic — it only calls functions from `api_client.py`. Swapping Gemini for another provider only requires changing the imports.

---

## Quickstart

**1. Get a free API key**

Go to [aistudio.google.com](https://aistudio.google.com) → Get API Key → Create API Key. No credit card required.

**2. Install the dependency**

```bash
pip install google-genai
# or with pipenv
pipenv install google-genai
```

**3. Configure**

Paste your key into `my_api_keys.py`:

```python
MY_GOOGLE_API_KEY = "AIzaSy-YOUR-KEY-HERE"
```

> For production use, load from an environment variable instead:
> `API_KEY = os.environ.get("GEMINI_API_KEY")`

**4. (Optional) Check available models**

```bash
python list_models.py
```

Use the exact model name (including the `models/` prefix) in `config.py`.

**5. Run**

```bash
python main.py
```

Select a demo from the menu.

---

## Core concepts covered

### Authentication

Every request is authenticated via an API key sent in the HTTP header `x-goog-api-key`. The SDK handles this automatically when you pass `api_key=` to `genai.Client()`. An invalid key returns a `403 PERMISSION_DENIED` error.

### Key parameters

| Parameter | What it controls |
|---|---|
| `model` | Which LLM version to use |
| `system_instruction` | Persistent behavioral directive (persona, tone, language) |
| `temperature` | Randomness: `0.0` = deterministic, `2.0` = very creative |
| `max_output_tokens` | Hard ceiling on response length (only generated tokens are billed) |

### Streaming

Instead of waiting for the full response, the server sends token chunks via **Server-Sent Events (SSE)** as the model generates them. The SDK exposes this through `client.models.generate_content_stream()`, which returns an iterable of chunks. Each chunk has a `.text` attribute.

Use streaming for chat interfaces or long responses where perceived latency matters.

### Multi-turn chat and stateless APIs

The Gemini API has no server-side session memory — every call is independent. To simulate a conversation, the client must resend the **full conversation history** on each request.

```
Turn 1: contents = [user_msg_1]
Turn 2: contents = [user_msg_1, model_reply_1, user_msg_2]
Turn N: contents = [all previous turns + new_message]
```

Each turn in the history is a `types.Content` object with a `role` (`"user"` or `"model"`) and a list of `parts`. Note: Gemini uses `"model"` where OpenAI and Anthropic use `"assistant"`.

Token cost grows with each turn since the full history is billed every time.

### Error handling

The `google.genai.errors` module (built into the SDK) provides two main exception types:

| Exception | HTTP codes | Common causes |
|---|---|---|
| `ClientError` | 4xx | Invalid key (403), rate limit (429), bad parameter (400) |
| `ServerError` | 5xx | Temporary Google service outage (503) |

The `safe_*` wrapper functions in `api_client.py` catch these and return a structured dict so the presentation layer never has to handle exceptions directly:

```python
result = safe_chat("What is a transformer model?")

if result["success"]:
    print(result["response"])
else:
    print(f"Error [{result['error_type']}]: {result['response']}")
```

### SDK migration note

This project uses the **new** `google-genai` package (2024+). The older `google.generativeai` package is deprecated and no longer receives updates.

| | Old SDK | New SDK |
|---|---|---|
| Package | `google-generativeai` | `google-genai` |
| Auth | `genai.configure(api_key=)` global | `genai.Client(api_key=)` explicit |
| Call | `model.generate_content()` | `client.models.generate_content()` |
| Errors | `google.api_core.exceptions` (external) | `google.genai.errors` (built-in) |

---

## Free tier limits (Gemini 2.5 Flash)

| Limit | Value |
|---|---|
| Requests per minute (RPM) | 10 |
| Tokens per minute (TPM) | 250,000 |
| Requests per day | 500 |

For experimentation and study this is more than sufficient. Check current limits at [ai.dev/rate-limit](https://ai.dev/rate-limit).

---

## Requirements

```
google-genai>=1.0.0
```

---

## Related projects

This client is part of a broader portfolio covering direct LLM API integration:
- **Anthropic SDK version** — same architecture targeting Claude models
- **RAG pipeline** — LangChain + LangGraph + local inference via Ollama
