"""Retractable floating top toolbar for Keymap Edit Mode in WayFire.

Provides quick-add buttons for D-Pad, Aim, Fire, and Tap widgets,
along with OSD opacity adjustment and an exit/finish action (D-05, D-10).
"""

from __future__ import annotations

from typing import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk


class FloatingTopBar(Gtk.Box):
    """Floating toolbar docked at the top center of the edit overlay."""

    def __init__(
        self,
        on_add_widget: Callable[[str], None],
        on_opacity_changed: Callable[[float], None],
        on_close_requested: Callable[[], None],
    ) -> None:
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        self.on_add_widget = on_add_widget
        self.on_opacity_changed = on_opacity_changed
        self.on_close_requested = on_close_requested

        self.set_halign(Gtk.Align.CENTER)
        self.set_valign(Gtk.Align.START)
        self.set_margin_top(8)
        self.add_css_class("floating-top-bar")

        # Action buttons for special widgets per D-05
        self.btn_dpad = Gtk.Button(label="🕹️ D-Pad")
        self.btn_dpad.add_css_class("flat")
        self.btn_dpad.connect("clicked", lambda _b: self.on_add_widget("dpad"))
        self.append(self.btn_dpad)

        self.btn_aim = Gtk.Button(label="🎯 Mira FPS")
        self.btn_aim.add_css_class("flat")
        self.btn_aim.connect("clicked", lambda _b: self.on_add_widget("aim"))
        self.append(self.btn_aim)

        self.btn_fire = Gtk.Button(label="🔥 Tiro")
        self.btn_fire.add_css_class("flat")
        self.btn_fire.connect("clicked", lambda _b: self.on_add_widget("fire"))
        self.append(self.btn_fire)

        self.btn_tap = Gtk.Button(label="+ Botão")
        self.btn_tap.add_css_class("flat")
        self.btn_tap.connect("clicked", lambda _b: self.on_add_widget("tap"))
        self.append(self.btn_tap)

        # Separator
        sep1 = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        self.append(sep1)

        # OSD Opacity Control per D-10
        self.lbl_opacity = Gtk.Label(label="Opacidade:")
        self.lbl_opacity.add_css_class("dim-label")
        self.append(self.lbl_opacity)

        self.scale_opacity = Gtk.Scale.new_with_range(
            Gtk.Orientation.HORIZONTAL, 0.0, 1.0, 0.05
        )
        self.scale_opacity.set_value(0.7)
        self.scale_opacity.set_size_request(100, -1)
        self.scale_opacity.connect("value-changed", self._on_scale_value_changed)
        self.append(self.scale_opacity)

        # Separator
        sep2 = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        self.append(sep2)

        # Close / Done Button
        self.btn_close = Gtk.Button(label="✖ Concluir")
        self.btn_close.add_css_class("suggested-action")
        self.btn_close.connect("clicked", lambda _b: self.on_close_requested())
        self.append(self.btn_close)

    def _on_scale_value_changed(self, scale: Gtk.Scale) -> None:
        value = float(scale.get_value())
        self.on_opacity_changed(value)

    def set_opacity_value(self, val: float) -> None:
        """Update scale widget value without re-triggering signal callback excessively."""
        clamped = max(0.0, min(1.0, val))
        self.scale_opacity.set_value(clamped)
