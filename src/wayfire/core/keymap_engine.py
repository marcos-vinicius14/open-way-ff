"""Low-latency keymap event dispatcher and multi-touch uinput translator.

Processes evdev events with <1ms latency, mapping physical keys and peripheral mouse buttons
to uinput touches (multi-touch slots 2–9, D-Pad 8-way directional vector, and sequential macros).
Marshals UI feedback safely to the GTK main loop via GLib.idle_add (D-09, D-11, D-16, MAP-02).
"""

from __future__ import annotations

import logging
import math
import time
from typing import Callable, Optional

from evdev import ecodes
import gi

gi.require_version("GLib", "2.0")
from gi.repository import GLib

from wayfire.config.profile import WayFireProfile
from wayfire.config.widgets import (
    AimWidget,
    BaseWidget,
    DPadWidget,
    FireWidget,
    MacroWidget,
    TapWidget,
)
from wayfire.core.macro_scheduler import NonBlockingMacroScheduler
from wayfire.core.touch_injector import TouchInjector
from wayfire.ui.key_codes import EVDEV_TO_CANONICAL, is_reserved_key

logger = logging.getLogger(__name__)


class KeymapEngine:
    """Dispatches physical hardware events to uinput multi-touch slots."""

    def __init__(
        self,
        profile: WayFireProfile,
        injector: TouchInjector,
        on_key_state_change: Optional[Callable[[str, bool], None]] = None,
    ) -> None:
        self.profile = profile
        self.injector = injector
        self.on_key_state_change = on_key_state_change

        self.macro_scheduler = NonBlockingMacroScheduler(injector=injector)

        # Active state tracking
        self.active_dpad_keys: set[str] = set()
        self.horizontal_history: list[str] = []
        self.vertical_history: list[str] = []
        self.active_widget_touches: dict[str, int] = {}  # widget_id -> slot
        # Dynamic tap slots (Slot 0 is Aim, Slot 1 is Fire, Slot 2 is DPad)
        self.tap_slots: list[int] = [3, 4, 5, 6, 7, 8, 9]

    def handle_key_event(self, code: int, value: int) -> bool:
        """Handle physical keyboard key event (1=press, 0=release, 2=repeat).

        Returns True if the event was processed by a mapped widget.
        """
        canonical = EVDEV_TO_CANONICAL.get(code)
        if not canonical:
            return False

        # Ignore repeat events (value == 2) for edge-triggered actions
        if value not in (0, 1):
            return False

        is_pressed = bool(value == 1)

        # Notify visual HUD safely on GTK thread per D-11 and CWE-362
        if self.on_key_state_change is not None:
            GLib.idle_add(self.on_key_state_change, canonical, is_pressed)

        # 1. Check D-Pad analog keys
        dpad = next((w for w in self.profile.widgets if isinstance(w, DPadWidget)), None)
        if dpad is not None:
            direction_matched = None
            for direction, dpad_key in dpad.keys.items():
                if dpad_key.upper() == canonical.upper():
                    direction_matched = direction
                    break

            if direction_matched is not None:
                if is_pressed:
                    if direction_matched in ("left", "right"):
                        if direction_matched in self.horizontal_history:
                            self.horizontal_history.remove(direction_matched)
                        self.horizontal_history.append(direction_matched)
                    elif direction_matched in ("up", "down"):
                        if direction_matched in self.vertical_history:
                            self.vertical_history.remove(direction_matched)
                        self.vertical_history.append(direction_matched)
                    self.active_dpad_keys.add(direction_matched)
                else:
                    if direction_matched in self.horizontal_history:
                        self.horizontal_history.remove(direction_matched)
                    if direction_matched in self.vertical_history:
                        self.vertical_history.remove(direction_matched)
                    self.active_dpad_keys.discard(direction_matched)
                self._update_dpad_vector(dpad)
                return True

        # 2. Check TapWidget and MacroWidget bindings (supports multi-touch per D-16)
        handled = False
        for widget in self.profile.widgets:
            if isinstance(widget, TapWidget) and widget.key.upper() == canonical.upper():
                if is_pressed:
                    if widget.id not in self.active_widget_touches and self.tap_slots:
                        slot = self.tap_slots.pop(0)
                        self.active_widget_touches[widget.id] = slot
                        self.injector.touch_down(slot, widget.x, widget.y)
                        handled = True
                else:
                    if widget.id in self.active_widget_touches:
                        slot = self.active_widget_touches.pop(widget.id)
                        self.injector.touch_up(slot)
                        if slot not in self.tap_slots:
                            self.tap_slots.append(slot)
                        handled = True

            elif isinstance(widget, MacroWidget) and widget.key.upper() == canonical.upper():
                if is_pressed:
                    self.macro_scheduler.trigger_macro(widget)
                    handled = True

        return handled

    def _update_dpad_vector(self, dpad: DPadWidget) -> None:
        """Calculate 8-directional analog movement vector with SOCD Last Win on slot 2."""
        dx = 0.0
        dy = 0.0

        if self.horizontal_history:
            dx = -1.0 if self.horizontal_history[-1] == "left" else 1.0
        if self.vertical_history:
            dy = -1.0 if self.vertical_history[-1] == "up" else 1.0

        slot = 2  # Dedicated analog slot

        if dx == 0.0 and dy == 0.0:
            if "dpad" in self.active_widget_touches:
                self.active_widget_touches.pop("dpad")
                self.injector.touch_up(slot)
        else:
            length = math.hypot(dx, dy)
            nx = dx / length
            ny = dy / length

            target_x = dpad.x + nx * dpad.radius
            target_y = dpad.y + ny * dpad.radius

            self.active_widget_touches["dpad"] = slot
            self.injector.touch_down(slot, target_x, target_y)

    def reset_dpad(self) -> None:
        """Release analog touch on slot 2 and clear all directional history per D-09."""
        self.active_dpad_keys.clear()
        self.horizontal_history.clear()
        self.vertical_history.clear()
        if "dpad" in self.active_widget_touches:
            self.active_widget_touches.pop("dpad")
        self.injector.touch_up(2)

    def recenter_dpad(self, dpad: Optional[DPadWidget] = None) -> None:
        """Inject 1ms micro-pulse at virtual D-Pad center per D-10."""
        target_dpad = dpad or next((w for w in self.profile.widgets if isinstance(w, DPadWidget)), None)
        if target_dpad is not None:
            self.injector.touch_down(2, target_dpad.x, target_dpad.y)
            time.sleep(0.001)  # 1ms micro-pulse
            self.injector.touch_up(2)

    def panic_reset(self) -> None:
        """Release all touch slots (0-9), reset dynamic slots and recenter analog per D-11."""
        for slot in range(10):
            self.injector.touch_up(slot)
        self.active_widget_touches.clear()
        self.tap_slots = [3, 4, 5, 6, 7, 8, 9]
        self.reset_dpad()
        self.recenter_dpad()

    def handle_mouse_button(self, code: int, value: int) -> bool:
        """Handle physical mouse button click (BTN_LEFT, BTN_RIGHT, BTN_SIDE, etc.)."""
        canonical = EVDEV_TO_CANONICAL.get(code)
        if not canonical:
            return False

        if value not in (0, 1):
            return False

        is_pressed = bool(value == 1)

        # Notify visual HUD safely on GTK thread per D-11
        if self.on_key_state_change is not None:
            GLib.idle_add(self.on_key_state_change, canonical, is_pressed)

        # 1. Check dedicated Fire button (Slot 1)
        fire = next((w for w in self.profile.widgets if isinstance(w, FireWidget)), None)
        if fire is not None and fire.key.upper() == canonical.upper():
            slot = 1
            if is_pressed:
                self.active_widget_touches[fire.id] = slot
                self.injector.touch_down(slot, fire.x, fire.y)
            else:
                if fire.id in self.active_widget_touches:
                    self.active_widget_touches.pop(fire.id)
                self.injector.touch_up(slot)
            return True

        # 2. Check Tap and Macro bindings for mouse buttons (e.g. M4, M5, RMB)
        handled = False
        for widget in self.profile.widgets:
            if isinstance(widget, TapWidget) and widget.key.upper() == canonical.upper():
                if is_pressed:
                    if widget.id not in self.active_widget_touches and self.tap_slots:
                        slot = self.tap_slots.pop(0)
                        self.active_widget_touches[widget.id] = slot
                        self.injector.touch_down(slot, widget.x, widget.y)
                        handled = True
                else:
                    if widget.id in self.active_widget_touches:
                        slot = self.active_widget_touches.pop(widget.id)
                        self.injector.touch_up(slot)
                        if slot not in self.tap_slots:
                            self.tap_slots.append(slot)
                        handled = True

            elif isinstance(widget, MacroWidget) and widget.key.upper() == canonical.upper():
                if is_pressed:
                    self.macro_scheduler.trigger_macro(widget)
                    handled = True

        return handled

    def poll_tick(self) -> None:
        """Periodic tick to advance scheduled macro touch steps."""
        self.macro_scheduler.process_scheduled()
