"""Floating status pill widget for WayFire overlay.

Displays aim lock state (LOCKED with 1.5s fadeout vs SUSPENDED permanent)
and provides quick access button to Keymap Edit Mode.
"""

from __future__ import annotations

from enum import Enum
from typing import Callable, Optional

import cairo
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib, Gtk


class AimState(Enum):
    """Aim engine state reflected in the status pill."""

    LOCKED = "locked"
    SUSPENDED = "suspended"


class StatusPill(Gtk.Box):
    """Floating HUD pill displaying aim status and edit button."""

    def __init__(
        self,
        on_edit_requested: Optional[Callable[[], None]] = None,
    ) -> None:
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        self.set_halign(Gtk.Align.CENTER)
        self.set_valign(Gtk.Align.START)
        self.add_css_class("status-pill")

        self.label = Gtk.Label(label="🎯 MIRA TRAVADA")
        self.label.add_css_class("pill-label")
        self.append(self.label)

        self.on_edit_requested = on_edit_requested
        self.edit_button = Gtk.Button(label="⚙️ Editar Teclas")
        self.edit_button.add_css_class("pill-edit-button")
        if self.on_edit_requested is not None:
            self.edit_button.connect("clicked", self._on_edit_button_clicked)
        self.append(self.edit_button)
        self.edit_button.set_visible(False)

        self._fadeout_source_id: Optional[int] = None
        self._state: AimState = AimState.LOCKED
        self.set_aim_state(AimState.LOCKED)

    def _on_edit_button_clicked(self, _btn: Gtk.Button) -> None:
        if self.on_edit_requested is not None:
            self.on_edit_requested()

    def set_aim_state(self, state: AimState) -> None:
        """Update pill appearance and behavior according to aim state.

        - LOCKED: Shows '🎯 MIRA TRAVADA' in green, hides edit button, fades out after 1.5s (D-12).
        - SUSPENDED: Shows '🔓 MOUSE LIVRE [F1]' in yellow, shows edit button permanently (D-02, D-12).
        """
        if self._fadeout_source_id is not None:
            GLib.source_remove(self._fadeout_source_id)
            self._fadeout_source_id = None

        self._state = state

        if state == AimState.LOCKED:
            self.label.set_text("🎯 MIRA TRAVADA")
            self.add_css_class("pill-locked")
            self.remove_css_class("pill-suspended")
            self.edit_button.set_visible(False)
            self.set_visible(True)
            self.set_opacity(1.0)
            self._fadeout_source_id = GLib.timeout_add(1500, self._on_fadeout_timeout)
        elif state == AimState.SUSPENDED:
            self.label.set_text("🔓 MOUSE LIVRE [F1]")
            self.add_css_class("pill-suspended")
            self.remove_css_class("pill-locked")
            self.edit_button.set_visible(True)
            self.set_visible(True)
            self.set_opacity(1.0)

    def _on_fadeout_timeout(self) -> bool:
        self.set_visible(False)
        self._fadeout_source_id = None
        return GLib.SOURCE_REMOVE

    def get_pill_rectangle(self, screen_width: int = 1920) -> cairo.RectangleInt:
        """Compute the bounding box of the status pill for Wayland input region.

        Centered horizontally at the top of the screen (D-01, D-02).
        """
        width = 280
        height = 36
        x = max(0, (screen_width - width) // 2)
        y = 8
        return cairo.RectangleInt(x, y, width, height)

    @property
    def current_state(self) -> AimState:
        return self._state
