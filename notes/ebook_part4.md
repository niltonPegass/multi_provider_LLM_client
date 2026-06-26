# Building LLM API Clients in Python — A Hands-on Guide

## Part 4 — Writing Robust Code

> Chapters 10, 11, and 12
> Covers: exception hierarchy, the safe wrapper pattern, and software design principles

---

# Chapter 10: Error Handling and Exception Hierarchy

## 10.1 What is an Exception?

When something goes wrong in Python, the interpreter raises an **exception** — a special object that represents an error condition. If the exception is not caught, it propagates up the call stack until it either reaches a handler or crashes the program with a traceback.

You have seen tracebacks in this project:

```
Traceback (most recent call last):
  File "gemini_main.py", line 117, in <module>
    demo_streaming()
  File "gemini_main.py", line 79, in demo_streaming
    chat_streaming(pergunta)
  File "gemini_api_client.py", line 133, in chat_streaming
    for chunk in model.generate_content(pergunta, stream=True):
google.api_core.exceptions.ResourceExhausted: 429 You exceeded your current quota
```

Reading a traceback from bottom to top:
- The **bottom line** tells you what went wrong: `ResourceExhausted: 429 ...`
- The lines above trace **where** the error propagated through: `chat_streaming` → `demo_streaming` → `__main__`
- The **top line** is the outermost call that eventually reached the error

Tracebacks are not failures to be feared — they are precise diagnostic tools. Learning to read them is one of the highest-leverage debugging skills you can develop.

---

## 10.2 The Exception Class Hierarchy

In Python, exceptions are classes organized into an inheritance hierarchy. Understanding the hierarchy lets you catch errors at the right level of specificity.

**Python's built-in hierarchy (simplified):**

```
BaseException
└── Exception
    ├── ValueError         ← invalid value (e.g., int("hello"))
    ├── TypeError          ← wrong type (e.g., 1 + "a")
    ├── KeyError           ← missing dict key (e.g., d["missing"])
    ├── IndexError         ← list index out of range
    ├── AttributeError     ← object has no such attribute
    ├── FileNotFoundError  ← file does not exist
    ├── OSError            ← operating system error
    └── ... (many more)
```

**What is inheritance?**

When class B inherits from class A, B is a more specific kind of A. `isinstance(obj, A)` returns True for both A instances and B instances.

```python
class Animal:
    pass

class Dog(Animal):
    pass

dog = Dog()
isinstance(dog, Dog)     # → True
isinstance(dog, Animal)  # → True  (Dog IS an Animal)
```

This matters for exception handling because `except Animal` would catch both `Animal` and `Dog` exceptions.

---

## 10.3 The Gemini Error Hierarchy

The `google.genai.errors` module defines its own hierarchy:

```
Exception
└── google.genai.errors.APIError        ← base for all Gemini API errors
    ├── ClientError                      ← HTTP 4xx: problem with the request
    │     • 400 Bad Request             ← invalid parameter, malformed request
    │     • 403 Permission Denied       ← bad API key, insufficient permissions
    │     • 404 Not Found               ← model name doesn't exist
    │     • 429 Resource Exhausted      ← rate limit or quota exceeded
    └── ServerError                      ← HTTP 5xx: problem on Google's side
          • 500 Internal Server Error   ← unexpected server failure
          • 503 Service Unavailable     ← server overloaded or under maintenance
```

**Why two categories?**

The 4xx/5xx split maps to who is responsible for the error:

- **4xx (ClientError):** The client (your code) sent a request the server could not fulfill. Retrying the same request will likely fail again unless you fix the underlying issue (bad key, invalid model name, exceeded quota).

- **5xx (ServerError):** The server failed for reasons unrelated to your request. The same request might succeed if you retry after a short wait.

This distinction should directly influence your retry logic:
- On `ClientError`, investigate and fix before retrying.
- On `ServerError`, wait and retry with exponential backoff.

---

## 10.4 try/except: The Syntax of Error Handling

```python
try:
    result = risky_operation()
except SomeException as e:
    handle_the_problem(e)
```

**How it works:**

1. Python executes the `try` block.
2. If no exception occurs, the `except` block is skipped.
3. If an exception occurs, Python checks whether it matches `SomeException` (or any of its subclasses).
4. If it matches, execution jumps to the `except` block. The exception object is bound to `e`.
5. If it doesn't match, the exception propagates upward.

**Multiple except clauses:**

```python
try:
    response = client.models.generate_content(...)
except gemini_errors.ClientError as e:
    # handle 4xx errors
except gemini_errors.ServerError as e:
    # handle 5xx errors
except Exception as e:
    # catch anything else unexpected
```

Python checks clauses in order. The first matching clause executes; others are skipped. More specific exceptions should come before more general ones — otherwise the general clause would always match first.

**The `as e` clause:**

`as e` binds the caught exception object to the variable `e`. This gives you access to:

```python
except gemini_errors.ClientError as e:
    print(str(e))        # human-readable error message
    print(type(e))       # <class 'google.genai.errors.ClientError'>
    print(e.status_code) # 429 (if the SDK exposes this attribute)
```

**`except Exception` as a catch-all:**

`Exception` is the base class of almost all Python errors. Using it as a final `except` clause catches anything not handled by more specific clauses. We use this in `_handle_error()` and in all `safe_*` wrappers:

```python
except Exception as e:
    return _handle_error(e)
```

This prevents any unexpected error from crashing the program — the caller always gets a dict back, never an uncaught exception.

---

## 10.5 isinstance(): Checking Types at Runtime

In `_handle_error()`:

```python
def _handle_error(error: Exception) -> dict:
    if isinstance(error, gemini_errors.ClientError):
        ...
    if isinstance(error, gemini_errors.ServerError):
        ...
```

**`isinstance(object, class)`** returns `True` if `object` is an instance of `class` or any of its subclasses.

Why use `isinstance()` instead of `type(error) == gemini_errors.ClientError`?

```python
# Fragile — only matches the exact class, not subclasses
type(error) == gemini_errors.ClientError

# Correct — matches ClientError and any future subclass
isinstance(error, gemini_errors.ClientError)
```

If the SDK introduces a more specific `AuthenticationError(ClientError)` in a future version, `isinstance(error, gemini_errors.ClientError)` will still catch it. `type(error) == gemini_errors.ClientError` would miss it.

Always prefer `isinstance()` over exact type comparison for exception handling.

---

## 10.6 String Inspection for HTTP Status Codes

Because `ClientError` covers all 4xx errors, we need a secondary check to distinguish them:

```python
if isinstance(error, gemini_errors.ClientError):
    code = str(error)
    if "403" in code or "PERMISSION_DENIED" in code:
        ...
    if "429" in code or "RESOURCE_EXHAUSTED" in code:
        ...
```

**Why not use `error.status_code`?**

The `google.genai` SDK does not consistently expose a `.status_code` attribute across all versions. The error message string, however, always contains the HTTP status code as part of the error description. Checking `str(error)` is a pragmatic approach that works across SDK versions.

**What does `"403" in code` do?**

The `in` operator on strings checks whether the left string is a substring of the right string:

```python
"403" in "ClientError: 403 PERMISSION_DENIED"  # → True
"403" in "ClientError: 429 RESOURCE_EXHAUSTED" # → False
```

This is a simple but effective pattern when you need to classify errors based on message content rather than class hierarchy.

---

## 10.7 Rate Limits and What to Do When You Hit Them

A **rate limit** is a server-enforced constraint on how many requests a client can make in a given time window.

The Gemini free tier enforces:
- RPM (Requests Per Minute): typically 10–15 for flash models
- TPM (Tokens Per Minute): the total tokens across all requests per minute
- RPD (Requests Per Day): total daily request cap

When you exceed any of these, the server returns `429 RESOURCE_EXHAUSTED`.

**Why rate limits exist:**

Rate limits protect the service from being overwhelmed by any single client, ensuring fair access for all users and preventing runaway code from generating unexpected costs.

**What to do when you hit a rate limit:**

The HTTP response to a 429 sometimes includes a `Retry-After` header or (as we saw in the project's traceback) a `retry_delay` in the error body:

```
retry_delay {
  seconds: 11
}
```

The correct response is **exponential backoff**: wait, then retry, with increasing wait times on repeated failures:

```python
import time

def simple_chat_with_retry(prompt: str, max_attempts: int = 3) -> str:
    for attempt in range(max_attempts):
        try:
            return simple_chat(prompt)
        except gemini_errors.ClientError as e:
            if "429" not in str(e):
                raise   # not a rate limit error — re-raise immediately
            if attempt == max_attempts - 1:
                raise   # last attempt — give up
            wait = 2 ** attempt   # 1s, 2s, 4s
            print(f"Rate limited. Retrying in {wait}s...")
            time.sleep(wait)
```

**`2 ** attempt`** is Python's exponentiation operator. `2 ** 0 = 1`, `2 ** 1 = 2`, `2 ** 2 = 4` — this creates the exponential progression.

**`raise` with no argument** inside an `except` block re-raises the current exception, preserving its original traceback. Use this when you want to handle the error partially (logging, waiting) but still propagate it upward.

---

# Chapter 11: The Safe Wrapper Pattern

## 11.1 Two Layers of Functions

The project separates API operations into two layers:

**Layer 2 — Core operations** (in `operations.py`): pure, focused functions that do one thing and raise exceptions on failure:

```python
def simple_chat(prompt: str) -> str:
    ...
    return response.text   # or raises ClientError / ServerError
```

**Layer 3 — Safe wrappers** (in `errors.py`): functions that call Layer 2 inside a try/except and always return a structured dict:

```python
def safe_chat(prompt: str) -> dict:
    try:
        return {"success": True, "response": simple_chat(prompt), "error_type": None}
    except Exception as e:
        return _handle_error(e)
```

This two-layer design is a deliberate choice. Let's examine why.

---

## 11.2 Why Two Layers?

**Option A: Handle errors inside the operation.**

```python
def simple_chat(prompt: str) -> dict:
    try:
        client = create_client()
        ...
        return {"success": True, "response": response.text, "error_type": None}
    except Exception as e:
        return _handle_error(e)
```

Problems with this approach:
- `simple_chat()` now does two unrelated things: make API calls AND handle errors.
- If you want to test the raw API behavior without error wrapping, you cannot.
- If you want to use `simple_chat()` in a context where you want exceptions (e.g., inside a retry loop), the dict interface fights you.

**Option B: Let operations raise, add wrappers separately.**

This is what the project does. The benefits:

- `simple_chat()` is minimal and focused — easy to read, test, and understand.
- `safe_chat()` is also minimal — just a try/except wrapper.
- You can use either depending on your needs: raw exceptions for scripts that handle errors themselves, safe wrappers for interactive UIs.
- Error handling logic lives in one place (`_handle_error()`), not scattered across every operation.

---

## 11.3 The Result Dict Pattern

```python
{
    "success": True,
    "response": "The model's answer here.",
    "error_type": None
}

# On failure:
{
    "success": False,
    "response": "Rate limit reached. Wait and retry.",
    "error_type": "ClientError_429"
}
```

This pattern simulates what some languages call a **Result type** or **Either type** — a value that is either a success (containing the result) or a failure (containing error information), but never raises an exception.

**Benefits in interactive applications:**

```python
# main.py never needs try/except
result = safe_chat(prompt)

if result["success"]:
    print(result["response"])
else:
    print(f"Error [{result['error_type']}]: {result['response']}")
```

`main.py` is clean. It handles the two cases (success/failure) with a simple `if` — no exception handling machinery, no `try/except`, no risk of an unhandled exception crashing the program.

**The tradeoff:**

The dict approach is less idiomatic Python than exceptions. Python is designed around the "ask forgiveness, not permission" philosophy — try the operation, catch exceptions if they occur. The Result dict pattern is more common in languages like Rust or Haskell.

For a learning project, the explicit dict makes the success/failure distinction visible and easy to reason about. In production Python code, you might see either approach depending on team conventions.

---

## 11.4 _handle_error(): The Private Helper

```python
def _handle_error(error: Exception) -> dict:
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

    return {
        "success": False,
        "response": f"Unexpected error ({type(error).__name__}): {error}",
        "error_type": "UnexpectedError"
    }
```

**The leading underscore convention:**

`_handle_error` starts with an underscore. In Python, a leading underscore signals "this is intended for internal use within this module." It is a convention, not enforced by the language — you can still call `_handle_error()` from outside `errors.py`. But the underscore tells readers "this is an implementation detail, not part of the public API."

**`type(error).__name__`:**

In the catch-all case, we use `type(error).__name__` to get the exception's class name as a string:

```python
e = ValueError("something went wrong")
type(e)           # → <class 'ValueError'>
type(e).__name__  # → "ValueError"
```

This produces a more informative error message for unexpected exceptions without requiring us to import every possible exception class.

**f-strings with expressions:**

```python
f"Unexpected error ({type(error).__name__}): {error}"
```

Inside an f-string, `{}` can contain any Python expression, not just variable names. `type(error).__name__` is evaluated and inserted. `{error}` calls `str(error)` implicitly — f-strings convert expressions to strings using `str()`.

---

## 11.5 The Three Safe Wrappers Compared

**`safe_chat()` — simplest:**

```python
def safe_chat(prompt: str) -> dict:
    try:
        return {"success": True, "response": simple_chat(prompt), "error_type": None}
    except Exception as e:
        return _handle_error(e)
```

Nothing special — one try/except, always returns a dict. The entire function body is five lines.

**`safe_stream_chat()` — slightly more complex:**

```python
def safe_stream_chat(prompt: str, callback=None) -> dict:
    try:
        text = stream_chat(prompt, callback)
        return {"success": True, "response": text, "error_type": None}
    except Exception as e:
        return _handle_error(e)
```

The `callback` parameter is passed through to `stream_chat()`. If streaming fails midway, partial output may have already been delivered — this is documented in the code but not something we can prevent in a simple wrapper.

**`safe_multi_turn_chat()` — adds history management:**

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
        result["history"] = history
        return result
```

Three differences from the others:
1. Creates `history_copy` before the try block — the copy must exist whether or not an exception occurs.
2. Returns `"history"` in both success and failure cases — the caller always gets a usable history back.
3. On failure, returns the **original** `history`, not `history_copy` (which may have been partially modified).

**`result["history"] = history` — adding a key to an existing dict:**

After `_handle_error(e)` returns a dict without a `"history"` key, we add one:

```python
result = _handle_error(e)    # result has "success", "response", "error_type"
result["history"] = history  # now result also has "history"
return result
```

Dict keys can be added at any time. This is more concise than constructing the entire dict from scratch.

---

# Chapter 12: Factory Functions and Separation of Concerns

## 12.1 Design Principles in Practice

The code we have written embodies several software design principles. Understanding these principles — not just the code — is what enables you to design your own systems well.

This chapter names the principles explicitly and shows where they appear in the project.

---

## 12.2 Single Responsibility Principle (SRP)

**Definition:** Each module, class, or function should have one primary responsibility and one reason to change.

In this project:

| Component | Single responsibility |
|---|---|
| `config.py` | Define configuration values |
| `gemini/client.py` | Create authenticated clients and configs |
| `gemini/operations.py` | Execute API calls |
| `gemini/errors.py` | Handle errors from API calls |
| `main.py` | Present results to the user |

If you need to change how errors are presented, you change `errors.py`. That change does not touch `operations.py` or `main.py`. If you need to change the model, you change `config.py`. That change does not touch anything else.

**Violation example:**

The original flat `api_client.py` in the early project iteration had `create_client()`, `simple_chat()`, `stream_chat()`, `multi_turn_chat()`, `_handle_error()`, and `safe_chat()` all in one file. It worked, but each concern was not separated — a change to error handling required opening the same file that contained API call logic.

**SRP does not mean one function per file.** It means each unit of code has a coherent focus. `gemini/operations.py` has three functions, but they are all variations of the same concern: making API calls.

---

## 12.3 DRY — Don't Repeat Yourself

**Definition:** Every piece of knowledge should have a single, authoritative representation in the system.

**Where DRY appears in this project:**

1. **`config.py`:** `TEMPERATURE`, `MAX_TOKENS`, `MODEL` are defined once and referenced everywhere. If you want to change the model, you change one line — not ten.

2. **`_handle_error()`:** Error classification logic lives in one function. All three `safe_*` wrappers call it. If a new error type needs handling, you add it once to `_handle_error()`.

3. **`create_config()`:** The parameter bundle is assembled once. If `GenerateContentConfig` gains a new required parameter, you add it once to `create_config()`.

**DRY violation example:**

Imagine error handling were duplicated in each wrapper:

```python
def safe_chat(prompt):
    try:
        ...
    except gemini_errors.ClientError as e:
        if "403" in str(e):
            return {"success": False, "response": "Auth error...", "error_type": "ClientError_403"}
        if "429" in str(e):
            return {"success": False, "response": "Rate limit...", "error_type": "ClientError_429"}
        ...

def safe_stream_chat(prompt, callback=None):
    try:
        ...
    except gemini_errors.ClientError as e:
        if "403" in str(e):              # ← duplicated
            return {...}
        if "429" in str(e):              # ← duplicated
            return {...}
        ...
```

Now if you want to improve the rate limit message, you must update three functions. You will inevitably forget one. `_handle_error()` eliminates this.

---

## 12.4 The Factory Pattern in Depth

We introduced factory functions in Chapter 4. Here we examine the pattern more carefully.

**Basic factory:**

```python
def create_client() -> genai.Client:
    return genai.Client(api_key=API_KEY)
```

This is a **simple factory** — a function that creates and returns one specific type of object.

**Parameterized factory:**

```python
def create_config(**overrides) -> types.GenerateContentConfig:
    return types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        temperature=overrides.get("temperature", TEMPERATURE),
        max_output_tokens=overrides.get("max_output_tokens", MAX_TOKENS),
    )
```

This is a **parameterized factory** — it accepts arguments that customize the object being created, while providing sensible defaults.

**Why factories matter more as projects grow:**

Consider adding support for a second Gemini account (for example, one for development, one for production):

```python
# config.py
DEV_API_KEY  = "AIzaSy-dev-key..."
PROD_API_KEY = "AIzaSy-prod-key..."

# client.py
def create_client(environment: str = "dev") -> genai.Client:
    key = PROD_API_KEY if environment == "prod" else DEV_API_KEY
    return genai.Client(api_key=key)
```

Every caller that uses `create_client()` now has access to both environments by passing one argument. Without the factory, you would search the codebase for every `genai.Client(api_key=...)` and update them individually.

---

## 12.5 Separation of Concerns vs. Cohesion

These two principles work together and must be balanced:

**Separation of Concerns:** Different concerns should be in different places.

**Cohesion:** Related things should be together.

Too much separation produces a project where a single logical operation is scattered across dozens of tiny files, making it impossible to follow the code. Too little separation produces monolithic files where every concern is tangled with every other.

In this project, the balance point is:
- **Separation at the module level:** config, client, operations, errors, main are separate.
- **Cohesion within modules:** all three operation functions (`simple_chat`, `stream_chat`, `multi_turn_chat`) live together in `operations.py` because they are all variations of the same concern.

A useful heuristic: if you find yourself constantly opening multiple files to understand or change one behavior, separation has gone too far. If one file is doing too many unrelated things, it needs to be split.

---

## 12.6 The Dependency Direction Rule

In well-structured Python projects, imports flow in one direction only — from higher-level to lower-level:

```
main.py
  imports from → gemini/ (via __init__.py)

gemini/errors.py
  imports from → gemini/operations.py

gemini/operations.py
  imports from → gemini/client.py

gemini/client.py
  imports from → config.py

config.py
  imports from → my_api_keys.py
```

Notice: no file imports from a file above it in this chain. `operations.py` does not import from `errors.py`. `client.py` does not import from `operations.py`. `config.py` does not import from anything in `gemini/`.

**Why this matters:**

If `operations.py` imported from `errors.py` and `errors.py` imported from `operations.py`, you would have a **circular import** — Python would get stuck trying to load each file before the other is ready, resulting in an `ImportError`.

Beyond avoiding circular imports, one-directional dependencies mean you can understand any module by only reading the modules it imports — never the modules that import it.

---

## 12.7 Public vs. Private Interface: __all__ and Naming Conventions

In `gemini/__init__.py`:

```python
from gemini.errors import safe_chat, safe_stream_chat, safe_multi_turn_chat
from gemini.operations import simple_chat, stream_chat, multi_turn_chat
from gemini.client import create_client, create_config

__all__ = [
    "safe_chat",
    "safe_stream_chat",
    "safe_multi_turn_chat",
    "simple_chat",
    "stream_chat",
    "multi_turn_chat",
    "create_client",
    "create_config",
]
```

**`__all__`** is a list of strings that defines the package's public interface. When someone writes `from gemini import *`, only names in `__all__` are imported.

More importantly, `__all__` is documentation. It explicitly says: "these are the functions I intend for external callers to use." Everything not in `__all__` is an implementation detail.

**The underscore convention (naming):**

```python
def _handle_error(error: Exception) -> dict:   # ← leading underscore
```

The underscore before `_handle_error` signals: "this function is internal to `errors.py` — do not call it from outside this module." Python does not enforce this — the function is technically accessible from anywhere — but the convention is universally understood by Python developers.

**Dunder names (double underscore):**

Names like `__init__`, `__all__`, `__name__` have double underscores on both sides. These are **dunder** (double underscore) names — Python's reserved convention for special built-in attributes and methods. Never create your own `__x__` names; that namespace belongs to Python.

---

## 12.8 Putting It Together: Reading the Full Call Chain

Here is the complete call chain for `demo_multi_turn()` processing one user input, annotated with which design principle each layer represents:

```
main.py: demo_multi_turn()
  │
  │  [Presentation layer — knows nothing about the API]
  │  [Separation of Concerns]
  │
  ▼
gemini/__init__.py: safe_multi_turn_chat()   ← re-exported from errors.py
  │
  │  [Public interface of the package]
  │  [__all__ and the package abstraction]
  │
  ▼
gemini/errors.py: safe_multi_turn_chat()
  │
  │  [Error handling layer — never raises]
  │  [Safe wrapper pattern / Result type]
  │
  ├── list(history)   ← defensive copy
  │   [Protecting caller's state — SRP: this layer handles error safety]
  │
  ▼
gemini/operations.py: multi_turn_chat()
  │
  │  [API call layer — may raise, does one thing]
  │  [Single Responsibility Principle]
  │
  ├── create_client()    ← factory
  ├── create_config()    ← factory
  │   [Factory pattern — change in one place]
  │   [DRY principle]
  │
  ▼
gemini/client.py: genai.Client(api_key=API_KEY)
  │
  │  [Authentication layer]
  │  [Factory function]
  │
  ▼
config.py: API_KEY, MODEL, TEMPERATURE, MAX_TOKENS, SYSTEM_PROMPT
  │
  │  [Configuration layer — all values in one place]
  │  [Separation of configuration from logic]
  │
  ▼
my_api_keys.py: MY_GOOGLE_API_KEY
  │
  │  [Secret store — isolated from version control]
  │  [Security principle: secrets never in logic files]
```

Every layer in this chain has exactly one reason to exist and one reason to change. That is the practical result of applying the principles discussed in this chapter.

---

## Part 4 Summary

| Concept | One-line summary |
|---|---|
| Exception | An object representing an error condition; propagates until caught |
| Traceback | Read bottom-to-top: what went wrong, then where it propagated |
| Exception hierarchy | Classes organized by inheritance; catch at the right specificity |
| `ClientError` (4xx) | Problem with the request — fix the request before retrying |
| `ServerError` (5xx) | Problem on the server — retry after a wait |
| `try/except` | Execute risky code; catch and handle exceptions if they occur |
| `as e` | Binds the exception object to a variable for inspection |
| `isinstance()` | Checks type including subclasses — preferred over `==` |
| `"403" in str(e)` | String substring check to distinguish 4xx subtypes |
| Exponential backoff | Retry strategy: wait 1s, 2s, 4s... after repeated failures |
| `raise` (bare) | Re-raises the current exception with its original traceback |
| Safe wrapper pattern | Catches exceptions, returns structured dict — never raises |
| Result dict | `{"success": bool, "response": str, "error_type": str\|None}` |
| `_handle_error()` | Single point of error classification — DRY in action |
| Leading underscore | Convention: this is internal, not part of the public interface |
| `__all__` | Declares the package's intended public API |
| Single Responsibility | Each unit does one thing and has one reason to change |
| DRY | Every piece of knowledge has one authoritative representation |
| Factory pattern | Function that builds and returns an object — centralizes construction |
| Separation of Concerns | Different concerns live in different modules |
| Dependency direction | Imports flow one way only — no circular dependencies |

---

*Next: Part 5 — Python Concepts Used in This Project (Chapters 13, 14, 15, and 16)*
*Type hints, dictionaries and dispatch tables, packages and relative imports, and entry points.*

