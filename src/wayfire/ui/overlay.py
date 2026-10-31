"""Transparent fullscreen Wayland Layer Shell overlay window for WayFire.

Provides dynamic Cairo input regions:
- Game Mode: empty input region for 100% click pass-through to Waydroid (D-01).
- Suspended Mode: input region restricted only to top status pill banner (D-01, D-02).
- Edit Mode: fullscreen input region for keymapping canvas (D-01).
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

import cairo
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

try:
    gi.require_version("Gtk4LayerShell", "1.0")
    from gi.repository import Gtk4LayerShell

    HAS_LAYER_SHELL = True
except (ValueError, ImportError):
    Gtk4LayerShell = None  # type: ignore[assignment]
    HAS_LAYER_SHELL = False

from gi.repository import Adw, Gdk, GLib, Gtk

from wayfire.ui.status_pill import AimState, StatusPill


class OverlayMode(Enum):
    """Interaction mode of the WayFire overlay surface."""

    GAME_LOCKED = "game_locked"
    GAME_SUSPENDED = "game_suspended"
    EDIT_MODE = "edit_mode"


class WayFireOverlayWindow(Gtk.ApplicationWindow):
    """Transparent fullscreen overlay window anchored via Gtk4LayerShell."""

    def __init__(
        self,
        app: Optional[Gtk.Application] = None,
        enable_layer_shell: bool = True,
    ) -> None:
        if app is not None:
            super().__init__(application=app)
        else:
            super().__init__()

        self.set_title("WayFire Overlay")
        self.add_css_class("wayfire-overlay-window")

        self.mode: OverlayMode = OverlayMode.GAME_LOCKED
        self.is_layer_shell_active: bool = False
        self._pill_rect: Optional[cairo.RectangleInt] = None

        self._init_styles()

        # Initialize Gtk4LayerShell before window realization/mapping (D-04)
        if HAS_LAYER_SHELL and enable_layer_shell and self._can_use_layer_shell():
            Gtk4LayerShell.init_for_window(self)
            Gtk4LayerShell.set_layer(self, Gtk4LayerShell.Layer.OVERLAY)
            Gtk4LayerShell.set_namespace(self, "wayfire-overlay")
            Gtk4LayerShell.set_exclusive_zone(self, -1)
            for edge in (
                Gtk4LayerShell.Edge.TOP,
                Gtk4LayerShell.Edge.BOTTOM,
                Gtk4LayerShell.Edge.LEFT,
                Gtk4LayerShell.Edge.RIGHT,
            ):
                Gtk4LayerShell.set_anchor(self, edge, True)
            Gtk4LayerShell.set_keyboard_mode(self, Gtk4LayerShell.KeyboardMode.NONE)
            self.is_layer_shell_active = True
        else:
            # Fallback to standard fullscreen window when Layer Shell is unavailable
            self.fullscreen()

        # Build overlay hierarchy
        self._overlay_container = Gtk.Overlay()
        self.set_child(self._overlay_container)

        # Base canvas for HUD and key widgets
        self.canvas = Gtk.Fixed()
        self._overlay_container.set_child(self.canvas)

        # Status Pill positioned at top-center
        self.status_pill = StatusPill(on_edit_requested=self.set_edit_mode)
        self.status_pill.set_valign(Gtk.Align.START)
        self.status_pill.set_halign(Gtk.Align.CENTER)
        self.status_pill.set_margin_top(8)
        self._overlay_container.add_overlay(self.status_pill)

        self.connect("realize", self._on_realize)

    def _init_styles(self) -> None:
        """Inject transparent window styling."""
        try:
            display = Gdk.Display.get_default()
            if display is not None:
                provider = Gtk.CssProvider()
                css_data = """
                    .wayfire-overlay-window {
                        background-color: transparent;
                        background: none;
                    }
                    .status-pill {
                        background-color: rgba(20, 20, 25, 0.85);
                        border-radius: 18px;
                        padding: 4px 16px;
                        border: 1px solid rgba(255, 255, 255, 0.2);
                        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
                    }
                    .pill-locked {
                        color: #00e676;
                    }
                    .pill-suspended {
                        color: #ffd600;
                    }
                    .pill-edit-button {
                        background: rgba(255, 255, 255, 0.15);
                        color: #ffffff;
                        border-radius: 12px;
                        padding: 2px 10px;
                        font-weight: bold;
                        border: none;
                    }
                    .pill-edit-button:hover {
                        background: rgba(255, 255, 255, 0.3);
                    }
                """
                if hasattr(provider, "load_from_string"):
                    provider.load_from_string(css_data)
                else:
                    provider.load_from_data(css_data.encode("utf-8"))
                Gtk.StyleContext.add_provider_for_display(
                    display,
                    provider,
                    Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
                )
        except Exception:
            pass

    def _can_use_layer_shell(self) -> bool:
        """Safely test whether Layer Shell protocol is supported by compositor."""
        if not HAS_LAYER_SHELL or Gtk4LayerShell is None:
            return False
        try:
            display = Gdk.Display.get_default()
            if display is None:
                return False
            return bool(Gtk4LayerShell.is_supported())
        except Exception:
            return False

    def _on_realize(self, _widget: Gtk.Widget) -> None:
        self._apply_input_region()

    def set_mode(self, mode: OverlayMode) -> None:
        """Switch interaction mode and configure Layer Shell keyboard/input regions."""
        self.mode = mode

        if self.is_layer_shell_active and Gtk4LayerShell is not None:
            if mode == OverlayMode.EDIT_MODE:
                Gtk4LayerShell.set_keyboard_mode(
                    self, Gtk4LayerShell.KeyboardMode.ON_DEMAND
                )
            else:
                Gtk4LayerShell.set_keyboard_mode(
                    self, Gtk4LayerShell.KeyboardMode.NONE
                )

        self._apply_input_region()

    def set_game_mode(
        self,
        suspended: bool = False,
        pill_rect: Optional[cairo.RectangleInt] = None,
    ) -> None:
        """Convenience method to set game mode (locked or suspended with pill rect)."""
        self._pill_rect = pill_rect
        if suspended:
            self.set_mode(OverlayMode.GAME_SUSPENDED)
        else:
            self.set_mode(OverlayMode.GAME_LOCKED)

    def set_edit_mode(self) -> None:
        """Switch overlay to Edit Mode for keymapping interaction."""
        self.set_mode(OverlayMode.EDIT_MODE)

    def toggle_edit_mode(self) -> OverlayMode:
        """Toggle between Edit Mode and Game Mode (preserving suspension state)."""
        if self.mode == OverlayMode.EDIT_MODE:
            if self._pill_rect is not None:
                self.set_mode(OverlayMode.GAME_SUSPENDED)
            else:
                self.set_mode(OverlayMode.GAME_LOCKED)
        else:
            self.set_mode(OverlayMode.EDIT_MODE)
        return self.mode

    def set_aim_locked(self, locked: bool) -> None:
        """Update aim lock state, forwarding state to StatusPill and Layer Shell."""
        if locked:
            if self.status_pill is not None:
                self.status_pill.set_aim_state(AimState.LOCKED)
            self.set_game_mode(suspended=False, pill_rect=None)
        else:
            rect = None
            if self.status_pill is not None:
                self.status_pill.set_aim_state(AimState.SUSPENDED)
                width = self.get_width()
                screen_width = width if width > 0 else 1920
                rect = self.status_pill.get_pill_rectangle(screen_width)
            self.set_game_mode(suspended=True, pill_rect=rect)

    def compute_input_region_description(self) -> str:
        """Return human-readable input region description for testing and inspection."""
        if self.mode == OverlayMode.GAME_LOCKED:
            return "EMPTY"
        elif self.mode == OverlayMode.GAME_SUSPENDED:
            return "PILL_ONLY" if self._pill_rect is not None else "EMPTY"
        elif self.mode == OverlayMode.EDIT_MODE:
            return "FULLSCREEN"
        return "UNKNOWN"

    def _apply_input_region(self) -> None:
        """Apply dynamic cairo input region to surface based on current mode."""
        native = self.get_native()
        surface = native.get_surface() if native is not None else None
        if surface is None:
            return

        if self.mode == OverlayMode.GAME_LOCKED:
            empty_region = cairo.Region()
            surface.set_input_region(empty_region)
        elif self.mode == OverlayMode.GAME_SUSPENDED:
            if self._pill_rect is not None:
                pill_region = cairo.Region(self._pill_rect)
                surface.set_input_region(pill_region)
            else:
                surface.set_input_region(cairo.Region())
        elif self.mode == OverlayMode.EDIT_MODE:
            surface.set_input_region(None)
