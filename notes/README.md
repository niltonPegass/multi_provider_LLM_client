# Building LLM API Clients in Python — A Hands-on Guide

A study e-book built alongside a real modular Python project that integrates
the Google Gemini API directly via the official SDK. Covers everything from
HTTP fundamentals to software design principles — written for someone with
a programming and ML background who wants to understand what happens at the
SDK and architecture level.

---

## How to use this material

Read the parts in order on your first pass — each one builds on the previous.
On review, use the chapter summaries at the end of each part as a quick
reference. The goal is not just to understand the project, but to be able to
rebuild it from scratch.

---

## Part 1 — Foundations
**File:** `ebook_part1_foundations.md`

The conceptual ground everything else stands on. No SDK code yet — just the
vocabulary and mental models you need to reason about API integration.

| Chapter | Topics |
|---|---|
| 1 · How LLMs and APIs Work | Tokens and why they matter (billing, context windows, `max_tokens`). HTTP in depth: methods (GET/POST), status codes (2xx/4xx/5xx), headers. JSON as the data format for APIs. REST architecture and the statelessness property. SDKs vs. raw HTTP — what the SDK is actually doing for you. |
| 2 · Python Project Structure | Modules vs. packages, `__init__.py`. The three import styles: full module, specific names, relative. Separation of Concerns as a design principle. The project file tree explained with its dependency flow. Why a single flat file doesn't scale. |
| 3 · Configuration and Secrets | Why configuration should be separate from logic. What a secret is and why an exposed API key is dangerous. The `my_api_keys.py` + `.gitignore` pattern. The production pattern: environment variables with `os.environ`. Type hints: what they are, what they are not, and when to use them. The `.strip()` string method. |

---

## Part 2 — The Gemini SDK
**File:** `ebook_part2_gemini_sdk.md`

Authentication, model parameters, and the anatomy of an API call — explained
from the HTTP layer up to the response object.

| Chapter | Topics |
|---|---|
| 4 · Authentication and the Client Object | Authentication vs. authorization. How the API key travels as an HTTP header. The old SDK (`genai.configure()`) vs. the new SDK (`genai.Client()`) and why the change matters. The factory function pattern: what it is, why it exists, three scenarios that justify it. The `genai.Client` object and its namespaced sub-resources. What happens when authentication fails (403). |
| 5 · Generation Parameters | `GenerateContentConfig` as a parameter bundle. Model naming: why the `models/` prefix is required. Temperature explained technically (probability distribution over vocabulary) and practically (table by use case). `max_output_tokens`: what it is, what it is not, all `finish_reason` values. System prompts: how they differ from conversation turns, and how to write effective ones. The `**overrides` + `.get(key, default)` pattern in depth. |
| 6 · Making Your First API Call | The full request lifecycle traced through every layer. The response object: `response.text`, `candidates`, `parts`, `usage_metadata`. Token usage logging. `list_models.py` explained including the iterator concept. Synchronous vs. asynchronous calls. One client per call vs. shared client — the trade-off explained. |

---

## Part 3 — Communication Patterns
**File:** `ebook_part3_communication_patterns.md`

The three ways to communicate with the API: one-shot, streaming, and
multi-turn — each explained at the protocol level and dissected line by line.

| Chapter | Topics |
|---|---|
| 7 · Synchronous Calls | What "synchronous" and "blocking" mean. The request-response cycle traced to the TCP level. `simple_chat()` dissected: why we return `str` not the raw response object (encapsulation). All useful fields on the response object with a diagnostic wrapper. When synchronous is the right choice. |
| 8 · Streaming and Server-Sent Events | The problem streaming solves (perceived vs. actual latency). SSE explained as a protocol with connection diagrams. How the SDK wraps SSE in a Python iterator. `stream_chat()` dissected: `full_text += chunk.text`, `end=""`, `flush=True` and why buffering matters. The callback pattern: what a callback is, why it decouples delivery from display, three usage examples including the `fn` vs `fn()` distinction. |
| 9 · Multi-turn Conversations | What a "turn" is. The stateless API problem and why history must be resent. The `types.Content` structure: `role` and `parts`, and why not plain dicts. `multi_turn_chat()` dissected: list mutation, `.append()`, passing by reference. The full history growth traced turn-by-turn with concrete code. Token cost implications and three mitigation strategies. The shallow copy in `safe_multi_turn_chat()` and why it protects history on failure. |

---

## Part 4 — Writing Robust Code
**File:** `ebook_part4_robust_code.md`

Exception hierarchies, the safe wrapper pattern, and the software design
principles that make the project maintainable.

| Chapter | Topics |
|---|---|
| 10 · Error Handling and Exception Hierarchy | What an exception is and how to read a traceback (bottom to top). Python's built-in exception hierarchy and inheritance. The Gemini error hierarchy: `ClientError` (4xx) vs `ServerError` (5xx) and what each implies for retry logic. `try/except` syntax with multiple clauses and `as e`. `isinstance()` vs. `type() ==` — why `isinstance` is always preferred. String inspection for HTTP status subtypes. Exponential backoff implementation with `2 ** attempt` and bare `raise`. |
| 11 · The Safe Wrapper Pattern | Why operations and error handling are in separate layers. The two-layer design: operations raise, wrappers catch. The Result dict pattern as a Python approximation of a Result type. `_handle_error()`: the DRY pivot point, the underscore convention, `type(error).__name__`, f-strings with expressions. The three safe wrappers compared — what each adds beyond the previous. Adding keys to existing dicts after construction. |
| 12 · Factory Functions and Design Principles | Single Responsibility Principle with the project responsibility table. DRY with the `_handle_error()` example vs. triplication. Factory pattern: simple vs. parameterized, and a real scenario where it pays off. Separation of Concerns vs. cohesion — finding the balance. The dependency direction rule and why circular imports happen. `__all__` and the underscore convention as interface communication tools. The full call chain annotated with which design principle each layer represents. |

---

## Part 5 — Python Concepts Used in This Project
**File:** `ebook_part5_python_concepts.md`

A focused tour of the intermediate Python features used in the project —
explained from first principles for someone who knows the basics but hasn't
encountered these patterns before.

| Chapter | Topics |
|---|---|
| 13 · Type Hints and Return Annotations | Dynamic typing vs. type hints — what Python actually enforces. Basic annotation syntax for variables, parameters, and return types. The four primitive types. Container types: `list[str]`, `dict[str, int]`, `tuple[str, list]`. `None` as a return type and as a parameter default. Union types (`str \| None`). `Callable[[str], None]` for function parameters. Complete inventory of all annotations in the project. When to annotate and when not to. |
| 14 · Dictionaries, Dispatch Tables, and **kwargs | Dict operations: creation, access, `.get()`, `in`, iteration, `.keys()`, `.values()`. The Result dict vs. dataclass trade-off. Dispatch tables: mapping string keys to function objects for clean branching. First-class functions — `fn` vs `fn()`. Dict lookup as O(1) vs `if/elif` as O(n). `*args` collecting positional arguments into a tuple. `**kwargs` collecting keyword arguments into a dict. `**dict` unpacking in function calls. `.get(key, default)` vs `[key]` — when to use each. |
| 15 · Packages, __init__.py, and Relative Imports | The Python import system: `sys.path`, `sys.modules`, search order. What `__init__.py` does — what breaks without it and what it enables. `__all__`: controls `import *`, documents the public API, does not restrict direct access. Absolute vs. relative imports: syntax, when to use each, and why relative imports are preferred inside packages. The complete cascading import chain of the project traced step by step. The package as an abstraction boundary — encapsulation at the module level. |
| 16 · if __name__ == "__main__" | The `__name__` variable: `"__main__"` when run directly, module name when imported. What breaks without the guard (side effects during import). Dunder names table: `__name__`, `__init__`, `__all__`, `__str__`, `__len__`. Entry points as a concept. Module-level code: runs on import — when side effects at module level are acceptable vs. problematic. Full annotated reading of `main.py` showing all Part 5 concepts in context. |

---

## Part 6 — Putting It All Together
**File:** `ebook_part6_putting_together.md`

A complete walkthrough of the finished project, four concrete extensions with
working code, and a roadmap for what to build next.

| Chapter | Topics |
|---|---|
| 17 · Reading the Full Project | Why reading your own code from scratch matters. Dependency reading order. Each file read in sequence: what it is, what to notice, one interview talking point per file. The complete system diagram: terminal → main.py → gemini/ package → HTTP → Google API. |
| 18 · How to Extend This Project | **Adding a second provider (Anthropic):** mirroring the `gemini/` structure, handling API differences (method names, role names, streaming interface), switching providers with one import line. **Function calling / tool use:** declaring tools, handling `function_call` in the response, sending results back. **FastAPI web interface:** `BaseModel`, `@app.post`, `HTTPException`, running with `uvicorn`. **Persistent history:** `pathlib.Path`, `json.dumps` / `json.loads`, serializing and deserializing `types.Content` objects. |
| 19 · What to Study Next | **Async Python:** coroutines, `async def`, `await`, the Gemini SDK's `client.aio` namespace. **FastAPI:** endpoints, Pydantic validation, async handlers, `uvicorn`. **LangChain / LangGraph:** what it adds over direct SDK, when to use it, what transfers from this project. **RAG from scratch:** embeddings, vector databases, chunking, retrieval, prompt injection. **MLOps for LLMs:** mapping classical ML tracking (hyperparameters, model versions) to LLM equivalents (prompts, temperature, response quality). **Docker:** Dockerfile for the project, secrets via environment variables at runtime. Suggested 10-week learning sequence. Interview talking points you can now defend. A final reflection on the real measure of learning. |

---

## Quick reference — concepts by file

| File | Key concepts covered |
|---|---|
| `my_api_keys.py` | Secret isolation, `.gitignore` |
| `config.py` | External configuration, `UPPER_SNAKE_CASE`, `.strip()`, type hints |
| `gemini/client.py` | Factory functions, `genai.Client`, `GenerateContentConfig`, `**kwargs` |
| `gemini/operations.py` | Sync calls, streaming, SSE, iterators, callbacks, multi-turn, `types.Content` |
| `gemini/errors.py` | Exception hierarchy, `try/except`, `isinstance()`, Result dict, DRY |
| `gemini/__init__.py` | Packages, `__init__.py`, `__all__`, re-exports, abstraction boundary |
| `main.py` | Entry point, `__name__`, dispatch table, first-class functions, interactive loops |
| `list_models.py` | Module-level side effects, iterators, utility scripts |

---

## Files in this collection

```
ebook_README.md                      ← this file
ebook_part1_foundations.md           ← Chapters 1–3
ebook_part2_gemini_sdk.md            ← Chapters 4–6
ebook_part3_communication_patterns.md ← Chapters 7–9
ebook_part4_robust_code.md           ← Chapters 10–12
ebook_part5_python_concepts.md       ← Chapters 13–16
ebook_part6_putting_together.md      ← Chapters 17–19
```
