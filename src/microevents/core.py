"""
microevents.core
----------------

A tiny, dependency-free event system supporting sync + async handlers.
"""

from typing import Any, Callable, List, Optional

from .event_bus import EventBus, HandlerFunc, _SupportsEventSignature

# -------------------- module-level default bus --------------------

_default_bus = EventBus()


# Registration
def on(
    event: str,
    handler: _SupportsEventSignature,
    *,
    priority: int = 0,
    once: bool = False,
) -> None:
    """
    Register a handler for an event.
    Higher priority handlers run first. For equal priority, registration order is preserved.

    Args:
        event (str): The event to register the handler for.
        handler (_SupportsEventSignature): The handler to register.
        priority (int, optional): The priority of the handler.
                                  Defaults to 0. Higher priority handlers run first.
                                  For equal priority, registration order is preserved.
        once (bool, optional): Whether the handler should be called only once.
                               Defaults to False.
    """
    _default_bus.on(event, handler, priority=priority, once=once)


def off(event: str, handler: Optional[HandlerFunc] = None) -> int:
    """
    Unregister handlers. If `handler` is None, remove all handlers for `event`.
    Returns the number of removed handlers.

    Args:
        event (str): The event to unregister handlers for.
        handler (Optional[HandlerFunc], optional): The handler to unregister.
                                                  Defaults to None.

    Returns:
        int: The number of removed handlers.
    """
    return _default_bus.off(event, handler)


def clear() -> None:
    """
    Remove all handlers from the bus.

    Returns:
        None
    """
    _default_bus.clear()


def list_receivers(event: str) -> List[HandlerFunc]:
    """
    Return the list of functions registered for `event` (no order guaranteed).

    Args:
        event (str): The event to list receivers for.

    Returns:
        List[HandlerFunc]: The list of functions registered for `event`.
    """

    return _default_bus.list_receivers(event)


def _get_bus(bus: Optional[EventBus] = None) -> EventBus:
    return bus or _default_bus


# Decorator
def receiver(
    event: str,
    *,
    priority: int = 0,
    once: bool = False,
    bus: Optional[EventBus] = None,
) -> Callable[[HandlerFunc], HandlerFunc]:
    """
    Decorator to register a function as a handler for `event`.
    Handler signature: handler(event: str, *args, **kwargs).

    Args:
        event (str): The event to register the handler for.
        priority (int, optional): The priority of the handler.
                                  Defaults to 0. Higher priority handlers run first.
                                  For equal priority, registration order is preserved.
        once (bool, optional): Whether the handler should be called only once. Defaults to False.
        bus (EventBus, optional): The event bus to register the handler for.
                                  Defaults to None. If None, the default bus is used.

    Returns:
        Callable[[HandlerFunc], HandlerFunc]: The decorator function.

    Example:
    @receiver("my_event", priority=1, once=True)
    def my_handler(event, *args, **kwargs):
        print("my_handler called with args: ", args, "kwargs: ", kwargs)
    """
    return _get_bus(bus).receiver(event, priority=priority, once=once)


# Dispatch
async def emit(event: str, *args: Any, **kwargs: Any) -> None:
    """
    Dispatch `event` to all registered handlers (ordered by priority, then registration order).
    Awaits async handlers; calls sync handlers directly.
    Exceptions raised by handlers will propagate.

    Args:
        event (str): The event to dispatch.
        *args: Positional arguments to pass to the handlers.
        **kwargs: Keyword arguments to pass to the handlers.

    Returns:
        None

    Example:
    await emit("my_event", arg1, arg2)
    """
    await _default_bus.emit(event, *args, **kwargs)


def emit_sync(event: str, *args: Any, **kwargs: Any):
    """
    Convenience to use emit(...) from sync code.

    - If no loop is running, it blocks until done.
    - If a loop is running, schedules and returns an asyncio.Task (fire-and-forget).

    Args:
        event (str): The event to dispatch.
        *args: Positional arguments to pass to the handlers.
        **kwargs: Keyword arguments to pass to the handlers.

    Returns:
        None if no loop is running, otherwise an asyncio.Task

    Example:
    emit_sync("my_event", arg1, arg2)
    """
    return _default_bus.emit_sync(event, *args, **kwargs)
