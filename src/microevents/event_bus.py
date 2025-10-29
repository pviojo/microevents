"""
Event bus implementation.
"""

from __future__ import annotations

import asyncio
import inspect
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Protocol, Tuple

HandlerFunc = Callable[..., Any]
MaybeAwaitable = Any  # result of handler call; may be awaitable


class _SupportsEventSignature(Protocol):
    """
    Protocol for event handlers.
    """

    def __call__(self, event: str, *args: Any, **kwargs: Any) -> Any: ...


@dataclass(order=True)
class _Handler:
    # Sorting fields (priority descending, then order ascending)
    sort_index: Tuple[int, int] = field(init=False, repr=False)
    priority: int
    order: int
    func: HandlerFunc = field(compare=False)
    once: bool = field(default=False, compare=False)

    def __post_init__(self) -> None:
        """
        Initialize the handler.
        """
        # sort_index is negative priority to get higher numbers first when sorted ascending
        self.sort_index = (-self.priority, self.order)

    def call(self, event: str, *args: Any, **kwargs: Any) -> MaybeAwaitable:
        """
        Call the handler with the given event and arguments.
        """
        return self.func(event, *args, **kwargs)


class EventBus:
    """
    An isolated event bus. Thread-safe registration and dispatch.
    """

    def __init__(self) -> None:
        """
        Initialize a new EventBus instance.
        """
        self._lock = threading.RLock()
        self._handlers: Dict[str, List[_Handler]] = {}
        self._counter = 0  # registration order

    # -------------------- registration API --------------------
    def on(
        self,
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

        Returns:
            None
        """
        if not callable(handler):
            raise TypeError("handler must be callable")

        with self._lock:
            self._counter += 1
            h = _Handler(
                priority=priority, order=self._counter, func=handler, once=once
            )
            self._handlers.setdefault(event, []).append(h)

    def off(self, event: str, handler: Optional[HandlerFunc] = None) -> int:
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
        with self._lock:
            lst = self._handlers.get(event, [])
            if not lst:
                return 0
            if handler is None:
                removed = len(lst)
                self._handlers[event] = []
                return removed
            before = len(lst)
            self._handlers[event] = [h for h in lst if h.func is not handler]
            return before - len(self._handlers[event])

    def clear(self) -> None:
        """Remove all handlers from the bus."""
        with self._lock:
            self._handlers.clear()

    def list_receivers(self, event: str) -> List[HandlerFunc]:
        """Return the list of functions registered for `event` (no order guaranteed)."""
        with self._lock:
            return [h.func for h in self._handlers.get(event, [])]

    # -------------------- decorator --------------------
    def receiver(self, event: str, *, priority: int = 0, once: bool = False):
        """
        Decorator to register a function as a handler for `event`.
        Handler signature: handler(event: str, *args, **kwargs).

        Args:
            event (str): The event to register the handler for.
            priority (int, optional): The priority of the handler.
                                      Defaults to 0. Higher priority handlers run first.
                                      For equal priority, registration order is preserved.
            once (bool, optional): Whether the handler should be called only once.
                                   Defaults to False.

        Returns:
            Callable[[HandlerFunc], HandlerFunc]: The decorator function.
        """

        def wrapper(func: _SupportsEventSignature):
            self.on(event, func, priority=priority, once=once)
            return func

        return wrapper

    # -------------------- dispatch --------------------
    async def emit(self, event: str, *args: Any, **kwargs: Any) -> None:
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
        """
        # snapshot handlers to avoid holding the lock during callbacks
        with self._lock:
            handlers = list(self._handlers.get(event, []))

        # sort by priority desc / order asc using dataclass ordering
        handlers.sort()

        # Call each handler; await if necessary
        to_remove: List[_Handler] = []
        for h in handlers:
            result = h.call(event, *args, **kwargs)
            if inspect.isawaitable(result):
                await result

            if h.once:
                to_remove.append(h)

        # Remove once-handlers after dispatch
        if to_remove:
            with self._lock:
                current = self._handlers.get(event, [])
                # Remove by identity
                self._handlers[event] = [x for x in current if x not in to_remove]

    def emit_sync(self, event: str, *args: Any, **kwargs: Any):
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
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(self.emit(event, *args, **kwargs))
            return None
        else:
            return loop.create_task(self.emit(event, *args, **kwargs))
