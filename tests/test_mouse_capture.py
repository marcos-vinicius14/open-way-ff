"""Unit tests for low-level peripheral input capture and grab management."""

from typing import Any
from unittest.mock import MagicMock, patch
from evdev import ecodes
from wayfire.core.mouse_capture import InputCaptureManager, detect_input_devices


class FakeEvent:
    def __init__(self, etype: int, code: int, value: int) -> None:
        self.type = etype
        self.code = code
        self.value = value


class FakeInputDevice:
    def __init__(self, name: str, fd: int, caps: dict[int, list[int]]) -> None:
        self.name = name
        self.fd = fd
        self._caps = caps
        self.grab_called = False
        self.ungrab_called = False
        self._queue: list[list[FakeEvent]] = []

    def capabilities(self, verbose: bool = False) -> dict[int, list[int]]:
        return self._caps

    def grab(self) -> None:
        self.grab_called = True
        self.ungrab_called = False

    def ungrab(self) -> None:
        self.ungrab_called = True
        self.grab_called = False

    def read(self) -> list[FakeEvent]:
        if self._queue:
            return self._queue.pop(0)
        return []

    def push_events(self, events: list[FakeEvent]) -> None:
        self._queue.append(events)


def test_detect_input_devices_filters_touchpads() -> None:
    """Ensure detect_input_devices ignores touchpads (with EV_ABS) and selects physical mouse."""
    touchpad_caps = {
        ecodes.EV_REL: [ecodes.REL_X, ecodes.REL_Y],
        ecodes.EV_KEY: [ecodes.BTN_LEFT, ecodes.BTN_TOOL_FINGER],
        ecodes.EV_ABS: [ecodes.ABS_X, ecodes.ABS_Y],  # Has EV_ABS
    }
    mouse_caps = {
        ecodes.EV_REL: [ecodes.REL_X, ecodes.REL_Y],
        ecodes.EV_KEY: [ecodes.BTN_LEFT, ecodes.BTN_RIGHT],
    }
    keyboard_caps = {
        ecodes.EV_KEY: [ecodes.KEY_A, ecodes.KEY_SPACE, ecodes.KEY_F1],
    }

    mock_devices = {
        "/dev/input/event0": FakeInputDevice("Touchpad", 10, touchpad_caps),
        "/dev/input/event1": FakeInputDevice("Gaming Mouse", 11, mouse_caps),
        "/dev/input/event2": FakeInputDevice("Mechanical Keyboard", 12, keyboard_caps),
    }

    with patch("wayfire.core.mouse_capture.InputDevice", side_effect=lambda p: mock_devices[p]):
        mouse_path, kbd_path = detect_input_devices(["/dev/input/event0", "/dev/input/event1", "/dev/input/event2"])
        assert mouse_path == "/dev/input/event1"
        assert kbd_path == "/dev/input/event2"


def test_initial_state_is_suspended() -> None:
    """Motor must strictly start in suspended state per D-04."""
    mouse = FakeInputDevice("Mouse", 10, {})
    kbd = FakeInputDevice("Keyboard", 11, {})

    manager = InputCaptureManager(mouse_dev=mouse, keyboard_dev=kbd)
    assert manager.is_aim_locked is False
    assert manager.is_grabbed is False
    assert mouse.grab_called is False
    manager.cleanup()


def test_f1_toggle_grab_ungrab() -> None:
    """F1 press toggles lock state and triggers hardware grab / ungrab."""
    mouse = FakeInputDevice("Mouse", 10, {})
    kbd = FakeInputDevice("Keyboard", 11, {})
    manager = InputCaptureManager(mouse_dev=mouse, keyboard_dev=kbd)

    lock_states = []
    manager.on_lock_changed = lambda locked: lock_states.append(locked)

    # First toggle: Locks aim and grabs mouse
    locked = manager.toggle_aim_lock()
    assert locked is True
    assert manager.is_aim_locked is True
    assert manager.is_grabbed is True
    assert mouse.grab_called is True

    # Second toggle: Suspends aim and ungrabs mouse
    locked = manager.toggle_aim_lock()
    assert locked is False
    assert manager.is_aim_locked is False
    assert manager.is_grabbed is False
    assert mouse.ungrab_called is True

    assert lock_states == [True, False]
    manager.cleanup()


def test_mouse_deltas_ignored_when_suspended() -> None:
    """Mouse movements must not be dispatched when in suspended state."""
    mouse = FakeInputDevice("Mouse", 10, {})
    kbd = FakeInputDevice("Keyboard", 11, {})
    manager = InputCaptureManager(mouse_dev=mouse, keyboard_dev=kbd)

    received_deltas = []
    manager.on_mouse_move = lambda dx, dy: received_deltas.append((dx, dy))

    # Push mouse movement while suspended
    mouse.push_events([FakeEvent(ecodes.EV_REL, ecodes.REL_X, 10), FakeEvent(ecodes.EV_REL, ecodes.REL_Y, -5)])

    # Patch selector so select returns the ready mouse
    with patch.object(manager._selector, "select", return_value=[(MagicMock(data=("mouse", mouse)), 1)]):
        manager.poll_events(timeout=0)

    # Must be ignored because is_aim_locked is False
    assert len(received_deltas) == 0

    # Now lock aim and poll again
    manager.toggle_aim_lock()
    mouse.push_events([FakeEvent(ecodes.EV_REL, ecodes.REL_X, 15), FakeEvent(ecodes.EV_REL, ecodes.REL_Y, -8)])
    with patch.object(manager._selector, "select", return_value=[(MagicMock(data=("mouse", mouse)), 1)]):
        manager.poll_events(timeout=0)

    assert received_deltas == [(15, -8)]
    manager.cleanup()


def test_cleanup_guarantees_ungrab() -> None:
    """Cleanup must release mouse grab if active."""
    mouse = FakeInputDevice("Mouse", 10, {})
    manager = InputCaptureManager(mouse_dev=mouse)

    manager.grab_mouse()
    assert manager.is_grabbed is True
    assert mouse.grab_called is True

    manager.cleanup()
    assert manager.is_grabbed is False
    assert mouse.ungrab_called is True
