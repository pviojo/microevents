"""Tests for EventBus functionality."""

import asyncio

import pytest

from microevents import EventBus


def test_event_bus_on_invalid_handler():
    """Test that on() raises TypeError for non-callable handlers."""
    bus = EventBus()
    with pytest.raises(TypeError, match="handler must be callable"):
        bus.on("event", "not_callable")


def test_event_bus_off_all_handlers():
    """Test removing all handlers for an event with off(event, None)."""
    bus = EventBus()
    out = []

    def h1(e):  # pylint: disable=unused-argument
        out.append(1)

    def h2(e):  # pylint: disable=unused-argument
        out.append(2)

    def h3(e):  # pylint: disable=unused-argument
        out.append(3)

    bus.on("evt", h1)
    bus.on("evt", h2)
    bus.on("evt", h3)

    # Remove all handlers
    removed = bus.off("evt", None)
    assert removed == 3

    bus.emit_sync("evt")
    assert not out


def test_event_bus_off_nonexistent_event():
    """Test that off() returns 0 for non-existent events."""
    bus = EventBus()
    removed = bus.off("nonexistent")
    assert removed == 0


def test_event_bus_off_nonexistent_handler():
    """Test that off() returns 0 when handler is not registered."""
    bus = EventBus()

    def h1(e): ...  # pylint: disable=unused-argument

    def h2(e): ...  # pylint: disable=unused-argument

    bus.on("evt", h1)
    removed = bus.off("evt", h2)
    assert removed == 0


def test_event_bus_clear():
    """Test that clear() removes all handlers from all events."""
    bus = EventBus()
    out = []

    bus.on("evt1", lambda e: out.append(1))
    bus.on("evt2", lambda e: out.append(2))
    bus.on("evt3", lambda e: out.append(3))

    bus.clear()

    bus.emit_sync("evt1")
    bus.emit_sync("evt2")
    bus.emit_sync("evt3")

    assert not out


def test_event_bus_list_receivers():
    """Test list_receivers returns all registered handlers."""
    bus = EventBus()

    def h1(e): ...  # pylint: disable=unused-argument

    def h2(e): ...  # pylint: disable=unused-argument

    def h3(e): ...  # pylint: disable=unused-argument

    bus.on("evt", h1)
    bus.on("evt", h2)
    bus.on("evt", h3)

    receivers = bus.list_receivers("evt")
    assert len(receivers) == 3
    assert h1 in receivers
    assert h2 in receivers
    assert h3 in receivers


def test_event_bus_list_receivers_empty():
    """Test list_receivers returns empty list for non-existent event."""
    bus = EventBus()
    receivers = bus.list_receivers("nonexistent")
    assert receivers == []


def test_event_bus_receiver_decorator():
    """Test the receiver decorator on EventBus."""
    bus = EventBus()
    out = []

    @bus.receiver("evt", priority=5)
    def handler(event, x):  # pylint: disable=unused-argument
        out.append(x)

    bus.emit_sync("evt", 42)
    assert out == [42]


def test_event_bus_receiver_decorator_once():
    """Test the receiver decorator with once=True."""
    bus = EventBus()
    out = []

    @bus.receiver("evt", once=True)
    def handler(event):  # pylint: disable=unused-argument
        out.append("called")

    bus.emit_sync("evt")
    bus.emit_sync("evt")

    assert out == ["called"]


@pytest.mark.asyncio
async def test_event_bus_emit_with_args_kwargs():
    """Test emit passes args and kwargs correctly."""
    bus = EventBus()
    result = {}

    async def handler(event, a, b, c=None):  # noqa: S7503
        result["event"] = event
        result["a"] = a
        result["b"] = b
        result["c"] = c

    bus.on("evt", handler)
    await bus.emit("evt", 1, 2, c=3)

    assert result == {"event": "evt", "a": 1, "b": 2, "c": 3}


def test_event_bus_emit_sync_with_args_kwargs():
    """Test emit_sync passes args and kwargs correctly."""
    bus = EventBus()
    result = {}

    def handler(event, a, b, c=None):
        result["event"] = event
        result["a"] = a
        result["b"] = b
        result["c"] = c

    bus.on("evt", handler)
    bus.emit_sync("evt", 1, 2, c=3)

    assert result == {"event": "evt", "a": 1, "b": 2, "c": 3}


@pytest.mark.asyncio
async def test_event_bus_mixed_sync_async_handlers():
    """Test that both sync and async handlers work together."""
    bus = EventBus()
    out = []

    def sync_handler(event):  # pylint: disable=unused-argument
        out.append("sync")

    async def async_handler(event):  # pylint: disable=unused-argument
        await asyncio.sleep(0)
        out.append("async")

    bus.on("evt", sync_handler)
    bus.on("evt", async_handler)

    await bus.emit("evt")

    assert "sync" in out
    assert "async" in out


def test_event_bus_priority_ordering():
    """Test that handlers are called in priority order."""
    bus = EventBus()
    out = []

    bus.on("evt", lambda e: out.append(1), priority=1)
    bus.on("evt", lambda e: out.append(2), priority=10)
    bus.on("evt", lambda e: out.append(3), priority=5)

    bus.emit_sync("evt")

    # Should be called in order: 10, 5, 1
    assert out == [2, 3, 1]


def test_event_bus_registration_order_same_priority():
    """Test that handlers with same priority maintain registration order."""
    bus = EventBus()
    out = []

    bus.on("evt", lambda e: out.append(1), priority=0)
    bus.on("evt", lambda e: out.append(2), priority=0)
    bus.on("evt", lambda e: out.append(3), priority=0)

    bus.emit_sync("evt")

    assert out == [1, 2, 3]


@pytest.mark.asyncio
async def test_event_bus_handler_exception_propagates():
    """Test that exceptions in handlers propagate."""
    bus = EventBus()

    async def failing_handler(event):  # pylint: disable=unused-argument
        raise ValueError("test error")

    bus.on("evt", failing_handler)

    with pytest.raises(ValueError, match="test error"):
        await bus.emit("evt")


def test_event_bus_emit_sync_no_loop():
    """Test emit_sync when no event loop is running."""
    bus = EventBus()
    out = []

    async def handler(event):  # pylint: disable=unused-argument, # noqa: S7503
        out.append("called")

    bus.on("evt", handler)
    result = bus.emit_sync("evt")

    assert out == ["called"]
    assert result is None


@pytest.mark.asyncio
async def test_event_bus_emit_sync_with_loop():
    """Test emit_sync when event loop is running returns a Task."""
    bus = EventBus()
    out = []

    async def handler(event):  # pylint: disable=unused-argument
        await asyncio.sleep(0.01)
        out.append("called")

    bus.on("evt", handler)

    # Call emit_sync while loop is running
    task = bus.emit_sync("evt")

    assert isinstance(task, asyncio.Task)
    await task
    assert out == ["called"]


def test_event_bus_multiple_off_calls():
    """Test that multiple off() calls work correctly."""
    bus = EventBus()

    def h(e): ...  # pylint: disable=unused-argument

    bus.on("evt", h)

    removed1 = bus.off("evt", h)
    assert removed1 == 1

    removed2 = bus.off("evt", h)
    assert removed2 == 0


def test_event_bus_once_handler_removed_after_call():
    """Test that once handlers are removed after being called."""
    bus = EventBus()
    out = []

    def handler(event):  # pylint: disable=unused-argument
        out.append("called")

    bus.on("evt", handler, once=True)

    # First call
    bus.emit_sync("evt")
    assert out == ["called"]

    # Handler should be removed
    receivers = bus.list_receivers("evt")
    assert handler not in receivers

    # Second call should not trigger handler
    bus.emit_sync("evt")
    assert out == ["called"]  # Still just one call
