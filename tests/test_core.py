"""Tests for microevents core functionality."""

import asyncio

import pytest

from microevents import (
    EventBus,
    clear,
    emit,
    emit_sync,
    list_receivers,
    off,
    on,
    receiver,
)


def test_sync_and_async_handlers():
    """Test sync and async handlers."""
    clear()
    out = []

    @receiver("evt")
    def a(event, x):  # pylint: disable=unused-argument
        out.append(("a", x))

    @receiver("evt")
    async def b(event, x):  # pylint: disable=unused-argument
        await asyncio.sleep(0)
        out.append(("b", x))

    emit_sync("evt", 1)
    assert ("a", 1) in out and ("b", 1) in out


@pytest.mark.asyncio
async def test_emit_async():
    """Test emit() async function."""
    clear()
    out = []

    @receiver("evt2")
    async def h(event, x):  # pylint: disable=unused-argument
        out.append(("h", x))

    await emit("evt2", 7)
    assert out == [("h", 7)]


def test_priority_and_once():
    """Test priority and once parameters."""
    clear()
    out = []

    on("p", lambda e: out.append(1), priority=0)
    on("p", lambda e: out.append(2), priority=10)
    on("p", lambda e: out.append(3), priority=10, once=True)

    emit_sync("p")
    # Priority 10 first, preserving registration order among same priority
    assert out[:2] == [2, 3]
    # 'once' handler removed
    out.clear()
    emit_sync("p")
    assert out == [2, 1]


def test_receiver_decorator_with_bus():
    """Test receiver decorator with bus parameter."""
    clear()
    another_bus = EventBus()
    out = []

    @receiver("evt")  # Registered on default bus
    def handle_default_bus(event, x):  # pylint: disable=unused-argument
        out.append("default_bus")
        out.append(x)

    @receiver("evt", bus=another_bus)  # Registered on another bus
    def handle_another_bus(event, x):  # pylint: disable=unused-argument
        out.append("another_bus")
        out.append(x)

    emit_sync("evt", 1)  # Should only be called on default bus
    assert out == ["default_bus", 1]
    out.clear()
    another_bus.emit_sync("evt", 2)  # Should only be called on another bus
    assert out == ["another_bus", 2]


def test_off_and_list():
    """Test off() and list_receivers()."""
    clear()

    def h(e): ...  # pylint: disable=unused-argument

    on("x", h)
    assert h in list_receivers("x")
    removed = off("x", h)
    assert removed == 1
    assert h not in list_receivers("x")


def test_event_bus_isolation():
    """Test event bus isolation."""
    bus1, bus2 = EventBus(), EventBus()
    out = []

    def h1(e):
        out.append(("b1", e))

    def h2(e):
        out.append(("b2", e))

    bus1.on("e", h1)
    bus2.on("e", h2)

    bus1.emit_sync("e")
    bus2.emit_sync("e")
    assert (
        ("b1", "e") in out
        and ("b2", "e") in out
        and out.count(("b1", "e")) == 1
        and out.count(("b2", "e")) == 1
    )


def test_on_with_all_parameters():
    """Test on() function with all parameters."""
    clear()
    out = []

    def handler(event, x):  # pylint: disable=unused-argument
        out.append(x)

    on("evt", handler, priority=10, once=True)
    emit_sync("evt", 42)
    emit_sync("evt", 99)

    # Should only be called once
    assert out == [42]


def test_off_removes_specific_handler():
    """Test off() removes only the specified handler."""
    clear()
    out = []

    def h1(e):  # pylint: disable=unused-argument
        out.append(1)

    def h2(e):  # pylint: disable=unused-argument
        out.append(2)

    on("evt", h1)
    on("evt", h2)

    removed = off("evt", h1)
    assert removed == 1

    emit_sync("evt")
    assert out == [2]


def test_off_removes_all_handlers():
    """Test off() with None removes all handlers."""
    clear()
    out = []

    on("evt", lambda e: out.append(1))
    on("evt", lambda e: out.append(2))

    removed = off("evt", None)
    assert removed == 2

    emit_sync("evt")
    assert not out


def test_clear_removes_all_events():
    """Test clear() removes all handlers from all events."""
    clear()
    out = []

    on("evt1", lambda e: out.append(1))
    on("evt2", lambda e: out.append(2))

    clear()

    emit_sync("evt1")
    emit_sync("evt2")

    assert not out


def test_list_receivers_returns_handlers():
    """Test list_receivers() returns registered handlers."""
    clear()

    def h1(e): ...  # pylint: disable=unused-argument

    def h2(e): ...  # pylint: disable=unused-argument

    on("evt", h1)
    on("evt", h2)

    receivers = list_receivers("evt")
    assert len(receivers) == 2
    assert h1 in receivers
    assert h2 in receivers


def test_list_receivers_empty_event():
    """Test list_receivers() for non-existent event."""
    clear()
    receivers = list_receivers("nonexistent")
    assert receivers == []


def test_receiver_decorator_basic():
    """Test receiver decorator basic functionality."""
    clear()
    out = []

    @receiver("evt")
    def handler(event, x):  # pylint: disable=unused-argument
        out.append(x)

    emit_sync("evt", 100)
    assert out == [100]


def test_receiver_decorator_with_priority():
    """Test receiver decorator with priority parameter."""
    clear()
    out = []

    @receiver("evt", priority=10)
    def high_priority(event):  # pylint: disable=unused-argument
        out.append("high")

    @receiver("evt", priority=1)
    def low_priority(event):  # pylint: disable=unused-argument
        out.append("low")

    emit_sync("evt")
    assert out == ["high", "low"]


def test_receiver_decorator_with_once():
    """Test receiver decorator with once parameter."""
    clear()
    out = []

    @receiver("evt", once=True)
    def handler(event):  # pylint: disable=unused-argument
        out.append("called")

    emit_sync("evt")
    emit_sync("evt")

    assert out == ["called"]


def test_receiver_decorator_with_all_params():
    """Test receiver decorator with all parameters."""
    clear()
    out = []

    @receiver("evt", priority=5, once=True)
    def handler(event, x):  # pylint: disable=unused-argument
        out.append(x)

    emit_sync("evt", "test")
    emit_sync("evt", "test2")

    assert out == ["test"]


@pytest.mark.asyncio
async def test_emit_async_basic():
    """Test emit() async function."""
    clear()
    out = []

    async def handler(event, x):  # pylint: disable=unused-argument
        await asyncio.sleep(0)
        out.append(x)

    on("evt", handler)
    await emit("evt", 42)

    assert out == [42]


@pytest.mark.asyncio
async def test_emit_with_multiple_args():
    """Test emit() with multiple positional arguments."""
    clear()
    result = {}

    async def handler(event, a, b, c):  # pylint: disable=unused-argument, # noqa: S7503
        result["a"] = a
        result["b"] = b
        result["c"] = c

    on("evt", handler)
    await emit("evt", 1, 2, 3)

    assert result == {"a": 1, "b": 2, "c": 3}


@pytest.mark.asyncio
async def test_emit_with_kwargs():
    """Test emit() with keyword arguments."""
    clear()
    result = {}

    async def handler(event, x=None, y=None):  # pylint: disable=unused-argument, # noqa: S7503
        result["x"] = x
        result["y"] = y

    on("evt", handler)
    await emit("evt", x=10, y=20)

    assert result == {"x": 10, "y": 20}


@pytest.mark.asyncio
async def test_emit_with_args_and_kwargs():
    """Test emit() with both args and kwargs."""
    clear()
    result = {}

    async def handler(event, a, b, c=None):  # pylint: disable=unused-argument, # noqa: S7503
        result["a"] = a
        result["b"] = b
        result["c"] = c

    on("evt", handler)
    await emit("evt", 1, 2, c=3)

    assert result == {"a": 1, "b": 2, "c": 3}


def test_emit_sync_basic():
    """Test emit_sync() basic functionality."""
    clear()
    out = []

    def handler(event, x):  # pylint: disable=unused-argument
        out.append(x)

    on("evt", handler)
    emit_sync("evt", 42)

    assert out == [42]


def test_emit_sync_with_multiple_args():
    """Test emit_sync() with multiple arguments."""
    clear()
    result = {}

    def handler(event, a, b, c):  # pylint: disable=unused-argument
        result["a"] = a
        result["b"] = b
        result["c"] = c

    on("evt", handler)
    emit_sync("evt", 1, 2, 3)

    assert result == {"a": 1, "b": 2, "c": 3}


def test_emit_sync_with_kwargs():
    """Test emit_sync() with keyword arguments."""
    clear()
    result = {}

    def handler(event, x=None, y=None):  # pylint: disable=unused-argument
        result["x"] = x
        result["y"] = y

    on("evt", handler)
    emit_sync("evt", x=10, y=20)

    assert result == {"x": 10, "y": 20}


def test_emit_sync_with_async_handler():
    """Test emit_sync() with async handler (no loop running)."""
    clear()
    out = []

    async def handler(event):  # pylint: disable=unused-argument
        await asyncio.sleep(0)
        out.append("async")

    on("evt", handler)
    result = emit_sync("evt")

    assert out == ["async"]
    assert result is None


@pytest.mark.asyncio
async def test_emit_sync_inside_loop():
    """Test emit_sync() when called inside an event loop."""
    clear()
    out = []

    async def handler(event):  # pylint: disable=unused-argument
        await asyncio.sleep(0.01)
        out.append("called")

    on("evt", handler)

    # Call emit_sync while loop is running
    task = emit_sync("evt")
    assert not out

    assert isinstance(task, asyncio.Task)
    await task
    assert out == ["called"]


def test_multiple_events_isolation():
    """Test that different events are isolated."""
    clear()
    out = []

    on("evt1", lambda e: out.append("evt1"))
    on("evt2", lambda e: out.append("evt2"))

    emit_sync("evt1")
    assert out == ["evt1"]

    emit_sync("evt2")
    assert out == ["evt1", "evt2"]
