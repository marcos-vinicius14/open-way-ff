"""Interactive mapping canvas for WayFire keymap editor (GG Mouse Pro style).

Provides:
- Double click anywhere on canvas to create a new listening TapWidget [ ? ] (D-05, D-13)
- Unified key and mouse peripheral capture (M4, M5, RMB, MMB) with ESC cancel (D-13)
- Friendly system hotkey blocking (F1, F2, F3) with Adw.Toast alerts (D-15)
- Strict singleton validation for AimWidget and DPadWidget with repositioning and toast (D-08)
- Widget drag positioning, resize handles, and deletion (Delete / Backspace / trash) (D-06, D-07)
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Optional

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gtk

from wayfire.config.profile import WayFireProfile
from wayfire.config.widgets import (
    AimWidget,
    BaseWidget,
    DPadWidget,
    FireWidget,
    TapWidget,
)
from wayfire.ui.debounce_saver import ProfileDebounceSaver

logger = logging.getLogger(__name__)

RESERVED_SYSTEM_HOTKEYS = {"F1", "F2", "F3"}


def canonical_key_name(keyval: int) -> str:
    """Convert Gdk keyval to canonical schema key string."""
    name = Gdk.keyval_name(keyval)
    if not name:
        return "?"

    mapping = {
        "space": "Space",
        "Return": "Enter",
        "Escape": "Escape",
        "BackSpace": "BackSpace",
        "Delete": "Delete",
        "Tab": "Tab",
        "Shift_L": "Shift_L",
        "Shift_R": "Shift_R",
        "Control_L": "Control_L",
        "Control_R": "Control_R",
        "Alt_L": "Alt_L",
        "Alt_R": "Alt_R",
    }
    if name in mapping:
        return mapping[name]

    if len(name) == 1:
        return name.upper()

    return name


def mouse_button_to_key_name(button: int) -> str:
    """Convert X11/Wayland mouse button numbers to canonical schema strings."""
    mapping = {
        2: "Mouse_Middle",
        3: "Mouse_Right",
        8: "Mouse_4",
        9: "Mouse_5",
    }
    return mapping.get(button, f"Mouse_{button}")


class OverlayCanvas(Gtk.Fixed):
    """Absolute layout canvas implementing GG Mouse Pro interactive keymapping."""

    def __init__(
        self,
        profile: WayFireProfile,
        debounce_saver: ProfileDebounceSaver,
        toast_overlay: Optional[Adw.ToastOverlay] = None,
    ) -> None:
        super().__init__()

        self.profile = profile
        self.debounce_saver = debounce_saver
        self.toast_overlay = toast_overlay

        self.add_css_class("overlay-canvas")

        self.active_listening_widget: Optional[BaseWidget] = None
        self.selected_widget: Optional[BaseWidget] = None
        self.widget_views: dict[str, Gtk.Widget] = {}

        # Click gesture capturing all mouse buttons (button 0)
        self.click_gesture = Gtk.GestureClick.new()
        self.click_gesture.set_button(0)
        self.click_gesture.connect("pressed", self._on_canvas_pressed)
        self.add_controller(self.click_gesture)

        # Keyboard event controller for key capture and shortcuts
        self.key_controller = Gtk.EventControllerKey.new()
        self.key_controller.connect("key-pressed", self._on_key_pressed)
        self.add_controller(self.key_controller)

        self.refresh_views()

    def _show_toast(self, message: str) -> None:
        """Display an informational toast banner."""
        if self.toast_overlay is not None:
            toast = Adw.Toast(title=message)
            self.toast_overlay.add_toast(toast)
        else:
            logger.info("Toast: %s", message)

    def _on_canvas_pressed(
        self,
        gesture: Gtk.GestureClick,
        n_press: int,
        x: float,
        y: float,
    ) -> None:
        button = gesture.get_current_button()

        # If a widget is currently listening for a key [ ? ]
        if self.active_listening_widget is not None:
            # Capture secondary/extra mouse buttons (D-13)
            if button in (2, 3, 8, 9):
                mouse_key = mouse_button_to_key_name(button)
                self.active_listening_widget.key = mouse_key
                self.active_listening_widget = None
                self.debounce_saver.request_save(self.profile)
                self.refresh_views()
                return

        # Double click with Left Mouse Button creates a new TapWidget (D-05)
        if n_press == 2 and button == 1:
            self.create_listening_tap(x, y)

    def create_listening_tap(self, x: float, y: float) -> TapWidget:
        """Create a new tap button at (x, y) in listening state [ ? ] (D-05, D-13)."""
        if self.active_listening_widget is not None:
            self.cancel_listening_widget()

        widget_id = f"tap_{int(x)}_{int(y)}"
        tap = TapWidget(id=widget_id, key="?", x=x, y=y, mode="single")
        self.profile.widgets.append(tap)
        self.active_listening_widget = tap
        self.selected_widget = tap
        self.refresh_views()
        return tap

    def _on_key_pressed(
        self,
        _controller: Gtk.EventControllerKey,
        keyval: int,
        _keycode: int,
        _state: Gdk.ModifierType,
    ) -> bool:
        # 1. Active Listening Mode: capture key for widget [ ? ]
        if self.active_listening_widget is not None:
            if keyval == Gdk.KEY_Escape:
                self.cancel_listening_widget()
                return True

            canonical_name = canonical_key_name(keyval)

            # System Hotkey Protection (D-15)
            if canonical_name in RESERVED_SYSTEM_HOTKEYS:
                self._show_toast(
                    f"A tecla {canonical_name} é reservada para controle do sistema (Mira F1, Editor F2 e OSD F3)."
                )
                return True

            self.active_listening_widget.key = canonical_name
            self.active_listening_widget = None
            self.debounce_saver.request_save(self.profile)
            self.refresh_views()
            return True

        # 2. Selected Widget Mode: deletion via Delete or BackSpace (D-07)
        if self.selected_widget is not None:
            if keyval in (Gdk.KEY_Delete, Gdk.KEY_BackSpace):
                self.delete_widget(self.selected_widget.id)
                return True

        return False

    def cancel_listening_widget(self) -> None:
        """Cancel and remove the currently listening widget if it has no key (D-13)."""
        if self.active_listening_widget is not None:
            target = self.active_listening_widget
            self.profile.widgets = [w for w in self.profile.widgets if w.id != target.id]
            if self.selected_widget == target:
                self.selected_widget = None
            self.active_listening_widget = None
            self.refresh_views()

    def add_special_widget(
        self,
        widget_type: str,
        target_x: float = 720.0,
        target_y: float = 540.0,
    ) -> None:
        """Add special widget or reposition existing singleton widget (D-08)."""
        # Singleton check for AimWidget and DPadWidget per D-08
        if widget_type in ("aim", "dpad"):
            existing = next(
                (w for w in self.profile.widgets if w.type == widget_type),
                None,
            )
            if existing is not None:
                existing.x = target_x
                existing.y = target_y
                label = "Analógico WASD" if widget_type == "dpad" else "Mira FPS"
                self._show_toast(
                    f"Apenas um {label} é permitido. O componente existente foi reposicionado."
                )
                self.selected_widget = existing
                self.debounce_saver.request_save(self.profile)
                self.refresh_views()
                return

        new_widget: BaseWidget
        if widget_type == "dpad":
            new_widget = DPadWidget(
                id="dpad_main",
                x=target_x,
                y=target_y,
                radius=90.0,
            )
        elif widget_type == "aim":
            new_widget = AimWidget(
                id="aim_main",
                x=target_x,
                y=target_y,
                width=400.0,
                height=400.0,
            )
        elif widget_type == "fire":
            new_widget = FireWidget(
                id=f"fire_{int(target_x)}",
                x=target_x,
                y=target_y,
            )
        elif widget_type == "tap":
            self.create_listening_tap(target_x, target_y)
            return
        else:
            logger.warning("Unknown widget type requested: %s", widget_type)
            return

        self.profile.widgets.append(new_widget)
        self.selected_widget = new_widget
        self.debounce_saver.request_save(self.profile)
        self.refresh_views()

    def delete_widget(self, widget_id: str) -> None:
        """Remove a widget from the profile and remove its view from canvas (D-07)."""
        self.profile.widgets = [w for w in self.profile.widgets if w.id != widget_id]
        if self.selected_widget is not None and self.selected_widget.id == widget_id:
            self.selected_widget = None
        if self.active_listening_widget is not None and self.active_listening_widget.id == widget_id:
            self.active_listening_widget = None

        self.debounce_saver.request_save(self.profile)
        self.refresh_views()

    def resize_widget_area(
        self,
        widget_id: str,
        new_radius: Optional[float] = None,
        new_width: Optional[float] = None,
        new_height: Optional[float] = None,
    ) -> None:
        """Update dimensions/radius of AimWidget or DPadWidget (D-06)."""
        widget = next((w for w in self.profile.widgets if w.id == widget_id), None)
        if widget is None:
            return

        if isinstance(widget, DPadWidget) and new_radius is not None:
            widget.radius = max(30.0, new_radius)
        elif isinstance(widget, AimWidget):
            if new_width is not None:
                widget.width = max(100.0, new_width)
            if new_height is not None:
                widget.height = max(100.0, new_height)

        self.debounce_saver.request_save(self.profile)
        self.refresh_views()

    def refresh_views(self) -> None:
        """Synchronize Gtk.Fixed visual representations with self.profile.widgets."""
        current_ids = {w.id for w in self.profile.widgets}

        # Remove deleted views
        for wid in list(self.widget_views.keys()):
            if wid not in current_ids:
                view = self.widget_views.pop(wid)
                self.remove(view)

        # Update or add views
        for widget in self.profile.widgets:
            if widget.id in self.widget_views:
                view = self.widget_views[widget.id]
                self.move(view, int(widget.x), int(widget.y))
                self._update_view_state(view, widget)
            else:
                view = self._create_view_for_widget(widget)
                self.widget_views[widget.id] = view
                self.put(view, int(widget.x), int(widget.y))

    def _create_view_for_widget(self, widget: BaseWidget) -> Gtk.Widget:
        """Construct visual GTK widget container representing the mapping element."""
        btn = Gtk.Button()
        btn.add_css_class("widget-view")
        self._update_view_state(btn, widget)

        # Connect drag gesture to move widget around canvas
        drag = Gtk.GestureDrag.new()
        drag_state = {"orig_x": widget.x, "orig_y": widget.y}

        def on_drag_begin(_gesture, _x, _y):
            drag_state["orig_x"] = widget.x
            drag_state["orig_y"] = widget.y
            self.selected_widget = widget

        def on_drag_update(_gesture, offset_x, offset_y):
            new_x = max(0.0, drag_state["orig_x"] + offset_x)
            new_y = max(0.0, drag_state["orig_y"] + offset_y)
            widget.x = new_x
            widget.y = new_y
            self.move(btn, int(new_x), int(new_y))

        def on_drag_end(_gesture, _offset_x, _offset_y):
            self.debounce_saver.request_save(self.profile)

        drag.connect("drag-begin", on_drag_begin)
        drag.connect("drag-update", on_drag_update)
        drag.connect("drag-end", on_drag_end)
        btn.add_controller(drag)

        return btn

    def _update_view_state(self, view: Gtk.Widget, widget: BaseWidget) -> None:
        """Update label and CSS classes of widget view."""
        if isinstance(view, Gtk.Button):
            if isinstance(widget, TapWidget):
                if self.active_listening_widget == widget:
                    view.set_label("[ ? ]")
                    view.add_css_class("listening")
                else:
                    view.set_label(widget.key)
                    view.remove_css_class("listening")
            elif isinstance(widget, DPadWidget):
                view.set_label("🕹️ D-Pad")
            elif isinstance(widget, AimWidget):
                view.set_label("🎯 Mira FPS")
            elif isinstance(widget, FireWidget):
                view.set_label("🔥 Tiro")
            else:
                view.set_label(getattr(widget, "key", widget.type))
