"""Low-level peripheral capture and exclusive mouse grab management via evdev/selectors."""

from __future__ import annotations

import selectors
import signal
import sys
from typing import Any, Callable, Optional
import evdev
from evdev import InputDevice, ecodes


def detect_input_devices(
    device_paths: Optional[list[str]] = None,
) -> tuple[Optional[str], Optional[str]]:
    """Intelligently detect physical mouse and keyboard devices in /dev/input/event*.

    Ignores touchpads, trackpoints and graphics tablets containing EV_ABS.
    """
    paths = device_paths if device_paths is not None else evdev.list_devices()
    mouse_path: Optional[str] = None
    keyboard_path: Optional[str] = None

    for path in paths:
        try:
            dev = InputDevice(path)
            caps = dev.capabilities(verbose=False)
        except (OSError, PermissionError):
            continue

        rel_caps = caps.get(ecodes.EV_REL, [])
        key_caps = caps.get(ecodes.EV_KEY, [])
        has_abs = ecodes.EV_ABS in caps

        # Detect physical mouse (REL_X, REL_Y, BTN_LEFT and NO EV_ABS)
        if mouse_path is None and not has_abs:
            has_rel_xy = ecodes.REL_X in rel_caps and ecodes.REL_Y in rel_caps
            has_btn_left = ecodes.BTN_LEFT in key_caps
            if has_rel_xy and has_btn_left:
                mouse_path = path

        # Detect keyboard (KEY_A and KEY_SPACE)
        if keyboard_path is None:
            if ecodes.KEY_A in key_caps and ecodes.KEY_SPACE in key_caps:
                keyboard_path = path

        if mouse_path is not None and keyboard_path is not None:
            break

    return mouse_path, keyboard_path


class InputCaptureManager:
    """Manages low-level mouse and keyboard event multiplexing and cursor grab."""

    def __init__(
        self,
        mouse_dev: Optional[Any] = None,
        keyboard_dev: Optional[Any] = None,
        suspend_key: int = ecodes.KEY_F1,
        selector: Optional[selectors.BaseSelector] = None,
    ) -> None:
        self.mouse_dev = mouse_dev
        self.keyboard_dev = keyboard_dev
        self.suspend_key = suspend_key

        self.is_aim_locked: bool = False
        self.is_grabbed: bool = False

        self.on_mouse_move: Optional[Callable[[int, int], None]] = None
        self.on_mouse_button: Optional[Callable[[int, int], None]] = None
        self.on_hotkey: Optional[Callable[[int], None]] = None
        self.on_keyboard_event: Optional[Callable[[int, int], None]] = None
        self.on_lock_changed: Optional[Callable[[bool], None]] = None

        self._selector: selectors.BaseSelector = (
            selector if selector is not None else selectors.DefaultSelector()
        )
        self._registered_fds: set[int] = set()
        self._setup_selector()

    def _setup_selector(self) -> None:
        """Register device file descriptors with epoll selector."""
        if self.mouse_dev is not None and hasattr(self.mouse_dev, "fd"):
            fd = self.mouse_dev.fd
            try:
                self._selector.register(fd, selectors.EVENT_READ, data=("mouse", self.mouse_dev))
                self._registered_fds.add(fd)
            except (OSError, PermissionError):
                pass

        if self.keyboard_dev is not None and hasattr(self.keyboard_dev, "fd"):
            fd = self.keyboard_dev.fd
            try:
                self._selector.register(fd, selectors.EVENT_READ, data=("keyboard", self.keyboard_dev))
                self._registered_fds.add(fd)
            except (OSError, PermissionError):
                pass

    def grab_mouse(self) -> None:
        """Exclusively grab mouse device via ioctl EVIOCGRAB."""
        if self.mouse_dev is not None and not self.is_grabbed:
            try:
                self.mouse_dev.grab()
            except (OSError, PermissionError):
                pass
            self.is_grabbed = True

    def ungrab_mouse(self) -> None:
        """Release exclusive grab on mouse device."""
        if self.mouse_dev is not None and self.is_grabbed:
            try:
                self.mouse_dev.ungrab()
            except (OSError, PermissionError):
                pass
            self.is_grabbed = False

    def toggle_aim_lock(self) -> bool:
        """Toggle aim lock state and update hardware mouse grab accordingly."""
        self.is_aim_locked = not self.is_aim_locked
        if self.is_aim_locked:
            self.grab_mouse()
        else:
            self.ungrab_mouse()

        if self.on_lock_changed is not None:
            self.on_lock_changed(self.is_aim_locked)
        return self.is_aim_locked

    def poll_events(self, timeout: float = 0.001) -> list[tuple[str, Any]]:
        """Poll input events via selector and dispatch callbacks."""
        selected = self._selector.select(timeout=timeout)
        processed: list[tuple[str, Any]] = []

        for key, _mask in selected:
            device_type, dev = key.data
            try:
                events = dev.read()
            except (OSError, BlockingIOError):
                continue

            dx, dy = 0, 0
            has_rel = False

            for ev in events:
                processed.append((device_type, ev))

                if device_type == "keyboard" and ev.type == ecodes.EV_KEY:
                    if self.on_keyboard_event is not None:
                        self.on_keyboard_event(ev.code, ev.value)
                    if ev.value == 1:  # Key press
                        if ev.code == self.suspend_key:
                            self.toggle_aim_lock()
                        elif self.on_hotkey is not None:
                            self.on_hotkey(ev.code)

                elif device_type == "mouse":
                    if ev.type == ecodes.EV_REL:
                        if ev.code == ecodes.REL_X:
                            dx += ev.value
                            has_rel = True
                        elif ev.code == ecodes.REL_Y:
                            dy += ev.value
                            has_rel = True
                    elif ev.type == ecodes.EV_KEY:
                        if self.on_mouse_button is not None:
                            self.on_mouse_button(ev.code, ev.value)

            if has_rel and self.is_aim_locked and self.on_mouse_move is not None:
                self.on_mouse_move(dx, dy)

        return processed

    def setup_signal_handlers(self) -> None:
        """Register SIGINT/SIGTERM handlers to ensure cursor ungrab on exit."""
        def _handler(signum: int, frame: Any) -> None:
            self.cleanup()
            sys.exit(0)

        signal.signal(signal.SIGINT, _handler)
        signal.signal(signal.SIGTERM, _handler)

    def cleanup(self) -> None:
        """Release mouse grab, unregister selector and close resources."""
        self.ungrab_mouse()
        for fd in list(self._registered_fds):
            try:
                self._selector.unregister(fd)
            except (KeyError, ValueError):
                pass
        self._registered_fds.clear()
        self._selector.close()

    def __enter__(self) -> InputCaptureManager:
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        self.cleanup()
