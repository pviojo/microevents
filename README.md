# microevents

Tiny **sync + async** event signals for Python with a decorator-based API.

- `@receiver(event: str)` decorator to register handlers.
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

or

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
from microevents import on, off, list_receivers, EventBus

def log(event, *a, **k): print("LOG", event, a, k)

on("ping", log, priority=10)

emit_sync("ping")

bus = EventBus()
bus.on("my_event", log, once=True)

bus.emit_sync("my_event")  # second call does nothing
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

## Testing

```bash
pip install -U pytest
pytest
```

## Development

Minimum Python version: 3.8

```bash
uv venv --python 3.8 .venv
source .venv/bin/activate

uv sync
uv run pytest
```

## License

MIT © Pablo Viojo
