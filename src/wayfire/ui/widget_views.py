"""Visual representation of keymap widgets on the HUD (GG Mouse Pro style).

Provides:
- 48x48px translucent circular buttons with fine border and bold compact labels (D-09)
- Continuous opacity control (0% to 100%) with complete invisibility at 0.0 (D-10)
- Smooth press feedback (.pressed) with competitive glow (#ff5000) during key hold (D-11)
- Specialized views for D-Pad, FPS Aim Area, Fire Trigger, and Macro Sequences
"""

from __future__ import annotations

from typing import Optional

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from wayfire.ui.key_codes import canonical_to_osd


class BaseWidgetView(Gtk.Box):
    """Base visual container for HUD widgets."""

    def __init__(self, widget_id: str, widget_type: str, x: float = 0.0, y: float = 0.0) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.widget_id = widget_id
        self.widget_type = widget_type
        self.x = x
        self.y = y
        self._osd_opacity: float = 0.70
        self._is_pressed: bool = False

        self.add_css_class("base-widget-view")

    def set_opacity_level(self, opacity: float) -> None:
        """Set visual opacity between 0.0 (fully transparent) and 1.0 (fully opaque) per D-10."""
        self._osd_opacity = max(0.0, min(1.0, opacity))
        self.set_opacity(self._osd_opacity)
        if self._osd_opacity <= 0.0:
            self.set_visible(False)
        else:
            self.set_visible(True)

    @property
    def osd_opacity(self) -> float:
        return self._osd_opacity


class TapWidgetView(BaseWidgetView):
    """Translucent circular tap button inspired by GG Mouse Pro (D-09)."""

    def __init__(
        self,
        widget_id: str,
        key: str = "",
        x: float = 0.0,
        y: float = 0.0,
    ) -> None:
        super().__init__(widget_id=widget_id, widget_type="tap", x=x, y=y)

        self.set_size_request(48, 48)
        self.add_css_class("tap-widget-view")
        self.add_css_class("gg-circle")

        self.label = Gtk.Label()
        self.label.add_css_class("widget-label")
        self.append(self.label)

        self.set_key_label(key)

    def set_key_label(self, key: str) -> None:
        """Set compact 1-3 char label using canonical to OSD converter (D-14)."""
        self.raw_key = key
        osd_text = canonical_to_osd(key)
        self.label.set_text(osd_text)

    def set_listening(self, listening: bool) -> None:
        """Toggle cyan pulsing listening state [ ? ] (D-05, D-13)."""
        if listening:
            self.label.set_text("[ ? ]")
            self.add_css_class("listening")
        else:
            self.remove_css_class("listening")
            self.set_key_label(self.raw_key)

    def set_pressed(self, pressed: bool) -> None:
        """Toggle active press feedback with glow (.pressed) per D-11.

        Guaranteed: Remains 100% invisible if OSD opacity is 0.0 (D-10, D-11).
        """
        self._is_pressed = pressed
        if self._osd_opacity <= 0.0:
            return

        if pressed:
            self.add_css_class("pressed")
        else:
            self.remove_css_class("pressed")


class DPadWidgetView(BaseWidgetView):
    """Virtual analog WASD display with directional indicators."""

    def __init__(
        self,
        widget_id: str,
        radius: float = 90.0,
        x: float = 0.0,
        y: float = 0.0,
    ) -> None:
        super().__init__(widget_id=widget_id, widget_type="dpad", x=x, y=y)
        self.radius = radius
        size = int(radius * 2)
        self.set_size_request(size, size)
        self.add_css_class("dpad-widget-view")

        self.label = Gtk.Label(label="WASD")
        self.label.set_halign(Gtk.Align.CENTER)
        self.label.set_valign(Gtk.Align.CENTER)
        self.append(self.label)


class AimWidgetView(BaseWidgetView):
    """FPS camera view and aim rectangle with center crosshair."""

    def __init__(
        self,
        widget_id: str,
        width: float = 400.0,
        height: float = 400.0,
        x: float = 0.0,
        y: float = 0.0,
    ) -> None:
        super().__init__(widget_id=widget_id, widget_type="aim", x=x, y=y)
        self.width = width
        self.height = height
        self.set_size_request(int(width), int(height))
        self.add_css_class("aim-widget-view")

        self.crosshair = Gtk.Label(label="➕")
        self.crosshair.set_halign(Gtk.Align.CENTER)
        self.crosshair.set_valign(Gtk.Align.CENTER)
        self.append(self.crosshair)


class FireWidgetView(BaseWidgetView):
    """Weapon trigger button mapped to mouse click."""

    def __init__(
        self,
        widget_id: str,
        x: float = 0.0,
        y: float = 0.0,
    ) -> None:
        super().__init__(widget_id=widget_id, widget_type="fire", x=x, y=y)
        self.set_size_request(52, 52)
        self.add_css_class("fire-widget-view")
        self.add_css_class("gg-circle")

        self.icon = Gtk.Label(label="🔥")
        self.append(self.icon)


class MacroSequenceView(BaseWidgetView):
    """Visual sequence of numbered circles for macro steps (D-16)."""

    def __init__(
        self,
        widget_id: str,
        key: str = "",
        step_count: int = 1,
        x: float = 0.0,
        y: float = 0.0,
    ) -> None:
        super().__init__(widget_id=widget_id, widget_type="macro", x=x, y=y)
        self.key = key
        self.step_count = step_count
        self.add_css_class("macro-sequence-view")

        self.label = Gtk.Label(label=f"{canonical_to_osd(key)} #{step_count}")
        self.append(self.label)
