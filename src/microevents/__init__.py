"""
Microevents
-----------

Tiny sync+async event signals for Python.

Features:

- Decorator-based API with `@receiver(event: str)`
- `emit(event, *args, **kwargs)` is **async**: awaits async handlers and calls sync ones.
- `emit_sync(...)` helper to use from sync code.
- Programmatic `on()`, `off()`, `clear()`, and `list_receivers()`.
- Optional **EventBus** class for isolated buses (tests, plugins, etc.).
- Handler options: `priority` (higher runs first), `once` (auto-unsubscribe after 1 call).
- Thread-safe registration/dispatch; preserves registration order when priorities tie.
- MIT licensed. No dependencies.
"""

from .core import (
    clear,
    emit,
    emit_sync,
    list_receivers,
    off,
    on,
    receiver,
)
from .event_bus import EventBus

__all__ = [
    "receiver",
    "emit",
    "emit_sync",
    "on",
    "off",
    "clear",
    "list_receivers",
    "EventBus",
]
