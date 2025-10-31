# Microevents for Python

[![codecov](https://codecov.io/github/pviojo/microevents/branch/main/graph/badge.svg?token=CVTS3VP5OS)](https://codecov.io/github/pviojo/microevents)
[![PyPI](https://img.shields.io/pypi/v/microevents.svg)](https://pypi.org/project/microevents/)
[![Python Versions](https://img.shields.io/pypi/pyversions/microevents.svg)](https://pypi.org/project/microevents/)

Tiny **sync + async** event signals for Python with a decorator-based API.

- `@receiver(event: str, bus: EventBus | None = None, priority: int = 0, once: bool = False)` decorator to register handlers.
- `emit(event, *args, **kwargs)` is **async**: awaits async handlers and calls sync ones.
- `emit_sync(...)` helper to use from non-async code.
- Programmatic `on()`, `off()`, `clear()`, and `list_receivers()`.
- Optional **EventBus** class for isolated buses (tests, plugins, etc.).
- Handler options: `priority` (higher runs first), `once` (auto-unsubscribe after 1 call).
- Thread-safe registration/dispatch; preserves registration order when priorities tie.
- MIT licensed. No dependencies.

## Installation

```bash
pip install microevents
```

or

```bash
uv add microevents
```

## Quick start

```python
from microevents import receiver, emit, emit_sync

@receiver("user_registered")
def welcome(event, user_id, **kw):
    print(f"[{event}] Welcome {user_id}")

@receiver("user_registered")
async def track(event, user_id, **kw):
    import asyncio
    await asyncio.sleep(0.05)
    print(f"[{event}] Tracked {user_id}")

# In async code:
# await emit("user_registered", user_id=42)

# From sync code:
emit_sync("user_registered", user_id=42)
```

## Programmatic registration & EventBus

```python
from microevents import on, off, list_receivers, EventBus, emit_sync


def log(event, *a, **k):
    print("LOG", event, a, k)


on("ping", log, priority=10)

emit_sync("ping")

bus = EventBus()
bus.on("my_event", log, once=True)  # auto-unsubscribed after first call

bus.emit_sync(
    "my_event", 1, 2, 3, a=1, b=2
)  # prints LOG my_event (1, 2, 3) {'a': 1, 'b': 2}
bus.emit_sync("my_event")  # second call does nothing because it was unsubscribed
```

## API

### Decorators & functions (module-level global bus)

- `@receiver(event: str, *, priority: int = 0, once: bool = False)`
- `async def emit(event: str, *args, **kwargs) -> None`
- `def emit_sync(event: str, *args, **kwargs) -> None | asyncio.Task`
- `def on(event: str, handler, *, priority: int = 0, once: bool = False) -> None`
- `def off(event: str, handler = None) -> int` (returns removed count; if `handler` is None, removes all)
- `def list_receivers(event: str) -> list`
- `def clear() -> None`

### EventBus (isolated)

- Same API as above, as instance methods.

### Errors

Any exception raised by a handler will propagate (fail-fast). If you prefer to isolate failures,
wrap your handler or create a small wrapper that catches/logs exceptions.

## 🔧 Advanced Usage

### Handler priority
Handlers can be given a **priority**. Higher numbers run first.
Within the same priority, registration order is preserved.

```python
from microevents import on, emit_sync

def handler_low(event, *a, **k):
    print("low priority")

def handler_high(event, *a, **k):
    print("high priority")

on("task_done", handler_low, priority=0)
on("task_done", handler_high, priority=10)

emit_sync("task_done")
# Output:
# high priority
# low priority
```

---

### Once-only handlers
Set `once=True` to make a handler automatically unsubscribe after being called once.

```python
from microevents import on, emit_sync

def only_once(event, *a, **k):
    print("This will only run once")

on("hello", only_once, once=True)

emit_sync("hello")
emit_sync("hello")  # no effect second time
```

---

### Isolated `EventBus`
By default, all events use a global bus.
You can also create independent buses — useful for **plugins, tests, or multiple apps**.

```python
from microevents import EventBus

bus1 = EventBus()
bus2 = EventBus()

def handler1(event, *a, **k): print("bus1")
def handler2(event, *a, **k): print("bus2")

bus1.on("ping", handler1)
bus2.on("ping", handler2)

bus1.emit_sync("ping")  # prints "bus1"
bus2.emit_sync("ping")  # prints "bus2"
```

---

### Dynamic registration & removal
You can programmatically register/unregister handlers.

```python
from microevents import on, off, list_receivers, emit_sync

def log(event, *a, **k): print("log handler")

on("debug", log)
print(list_receivers("debug"))
# [<function log at ...>]

emit_sync("debug")  # log handler runs

removed = off("debug", log)
print("removed:", removed)  # 1
```

---

### Async + sync mixed
Both **sync** and **async** handlers can listen to the same event.
Async handlers are awaited when using `await emit(...)`,
and run in fire-and-forget mode with `emit_sync(...)` (scheduled if a loop is running).

```python
import asyncio
from microevents import receiver, emit_sync

@receiver("mix")
def sync_handler(event):
    print("sync handler")

@receiver("mix")
async def async_handler(event):
    await asyncio.sleep(0.1)
    print("async handler")

emit_sync("mix")
# Output order:
# sync handler
# async handler   (slightly later)
```

---

### 🛡️ Error handling strategies

By default, **exceptions raised by handlers propagate** and will stop dispatch.
Choose one of the following strategies if you want to **isolate failures** so that one bad handler doesn’t break others.

#### 1) Wrap handlers when registering (simple & explicit)
Wrap each handler with a try/except so failures are contained and logged.

```python
import logging
from microevents import on, emit_sync

log = logging.getLogger("microevents.demo")

def safe(handler):
    def wrapped(event, *args, **kwargs):
        try:
            return handler(event, *args, **kwargs)
        except Exception as exc:
            log.exception("Handler %r failed on event %r", handler, event)
    return wrapped

def fragile(event, x):
    raise RuntimeError("boom")

def robust(event, x):
    print("robust:", x)

on("calc", safe(fragile))
on("calc", safe(robust))
emit_sync("calc", 42)
```

Pros: explicit, minimal.
Cons: you must remember to wrap each handler.

#### 2) Use a custom EventBus that isolates errors (centralized control)
Subclass `EventBus` and override `emit` to catch and aggregate exceptions.
This keeps handler code clean while ensuring dispatch continues.

```python
import asyncio
import inspect
from microevents import EventBus

class SafeEventBus(EventBus):
    async def emit(self, event: str, *args, **kwargs):
        errors: list[BaseException] = []
        # copy and order handlers like the base class does
        handlers = sorted(self._handlers.get(event, []))
        to_remove = []
        for h in handlers:
            try:
                result = h.call(event, *args, **kwargs)
                if inspect.isawaitable(result):
                    await result
                if h.once:
                    to_remove.append(h)
            except BaseException as exc:
                errors.append(exc)

        if to_remove:
            current = self._handlers.get(event, [])
            self._handlers[event] = [x for x in current if x not in to_remove]

        if errors:
            # Choose a policy: raise first error, raise a combined error, or just log.
            # Here we re-raise the first one after dispatch finishes.
            raise errors[0]

bus = SafeEventBus()

def ok(event): print("ok ran")
def bad(event): raise ValueError("bad")

bus.on("e", bad)
bus.on("e", ok)

try:
    bus.emit_sync("e")
except Exception as e:
    print("caught:", e)
# Output:
# ok ran
# caught: bad
```

Policy options you can implement:
- **Log and continue** (don’t re-raise).
- **Aggregate and raise** (like above).
- **Send errors to a separate event** (`bus.emit("error", ...)`) to create observability hooks.

#### 3) Defensive handlers (per-handler isolation)
When a particular handler is expected to be flaky, surround just that handler’s critical section with try/except and decide what to do (retry, fallback, etc.).

```python
@receiver("fetch")
def maybe_unreliable(event, url):
    try:
        fetch(url)  # your code
    except TimeoutError:
        schedule_retry(url)
```

Tip: If you need **full concurrency** and isolation, you can also dispatch each handler in its own `asyncio.create_task` and `await asyncio.gather(..., return_exceptions=True)`. This changes execution semantics (handlers run concurrently) and is best implemented in a custom `EventBus` variant for explicitness.


## Development

Minimum Python version: 3.8

```bash
uv venv --python 3.8 .venv
source .venv/bin/activate

uv sync
```

### Pre-commit hooks

Install pre-commit hooks to run tests and linting before each commit:

```bash
# Install dependencies (includes pre-commit)
uv sync

# Install the git hooks
uv run pre-commit install

# (Optional) Run hooks on all files
uv run pre-commit run --all-files
```

Now every commit will automatically:
- Run tests (must pass with 90%+ coverage)
- Format code with ruff
- Check for common issues

To bypass hooks (not recommended):
```bash
git commit --no-verify
```

## Testing

```bash
uv run pytest
```


## License

MIT © Pablo Viojo
