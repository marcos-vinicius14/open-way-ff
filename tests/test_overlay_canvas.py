"""Tests for OverlayCanvas gestures, key capture, singletons, and deletions."""

from __future__ import annotations

from unittest.mock import MagicMock
import pytest

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gtk

from wayfire.config.profile import WayFireProfile, create_default_profile
from wayfire.config.profile_manager import ProfileManager
from wayfire.config.widgets import AimWidget, DPadWidget, TapWidget
from wayfire.ui.debounce_saver import ProfileDebounceSaver
from wayfire.ui.overlay_canvas import OverlayCanvas


@pytest.fixture(autouse=True)
def ensure_gtk():
    Gtk.init_check()


@pytest.fixture
def canvas_setup(tmp_path):
    manager = ProfileManager(profiles_dir=tmp_path)
    profile = WayFireProfile(name="test_canvas_profile")
    profile.widgets = []  # Start with empty widgets for deterministic tests
    saver = ProfileDebounceSaver(manager, debounce_ms=10)
    toast_overlay = MagicMock(spec=Adw.ToastOverlay)

    canvas = OverlayCanvas(
        profile=profile,
        debounce_saver=saver,
        toast_overlay=toast_overlay,
    )
    return canvas, profile, saver, toast_overlay


def test_canvas_double_click_creates_listening_tap(canvas_setup):
    """Verify double click with button 1 creates a new TapWidget with key '?'."""
    canvas, profile, saver, _ = canvas_setup

    mock_gesture = MagicMock(spec=Gtk.GestureClick)
    mock_gesture.get_current_button.return_value = 1

    # Simulate double click at (350, 420)
    canvas._on_canvas_pressed(mock_gesture, n_press=2, x=350.0, y=420.0)

    assert len(profile.widgets) == 1
    widget = profile.widgets[0]
    assert isinstance(widget, TapWidget)
    assert widget.key == "?"
    assert widget.x == 350.0
    assert widget.y == 420.0
    assert canvas.active_listening_widget == widget
    assert canvas.widget_views[widget.id].get_label() == "[ ? ]"


def test_canvas_key_capture_and_escape_cancel(canvas_setup):
    """Verify key pressing captures normal keys and Escape cancels the listening widget."""
    canvas, profile, saver, _ = canvas_setup

    # 1. Create a listening tap
    tap = canvas.create_listening_tap(200.0, 300.0)
    assert canvas.active_listening_widget == tap

    # Press 'Space' (Gdk.KEY_space)
    controller = MagicMock(spec=Gtk.EventControllerKey)
    handled = canvas._on_key_pressed(controller, Gdk.KEY_space, 0, 0)
    assert handled is True
    assert tap.key == "Space"
    assert canvas.active_listening_widget is None

    # 2. Create another tap and press 'Escape' to cancel
    tap2 = canvas.create_listening_tap(500.0, 600.0)
    assert len(profile.widgets) == 2
    assert canvas.active_listening_widget == tap2

    handled_esc = canvas._on_key_pressed(controller, Gdk.KEY_Escape, 0, 0)
    assert handled_esc is True
    assert len(profile.widgets) == 1
    assert canvas.active_listening_widget is None
    assert tap2.id not in canvas.widget_views


def test_canvas_blocks_system_hotkeys(canvas_setup):
    """Verify that mapping F1, F2 or F3 is rejected with a toast per D-15."""
    canvas, profile, saver, toast_overlay = canvas_setup

    tap = canvas.create_listening_tap(100.0, 100.0)
    controller = MagicMock(spec=Gtk.EventControllerKey)

    for f_key in (Gdk.KEY_F1, Gdk.KEY_F2, Gdk.KEY_F3):
        toast_overlay.reset_mock()
        handled = canvas._on_key_pressed(controller, f_key, 0, 0)
        assert handled is True
        # Key must not be assigned to F1/F2/F3
        assert tap.key == "?"
        assert canvas.active_listening_widget == tap
        assert toast_overlay.add_toast.called


def test_canvas_mouse_button_capture(canvas_setup):
    """Verify peripheral mouse buttons (M4, M5, RMB, MMB) bind to active widget per D-13."""
    canvas, profile, saver, _ = canvas_setup

    tap = canvas.create_listening_tap(150.0, 150.0)
    mock_gesture = MagicMock(spec=Gtk.GestureClick)

    # Simulate RMB click (button 3)
    mock_gesture.get_current_button.return_value = 3
    canvas._on_canvas_pressed(mock_gesture, n_press=1, x=150.0, y=150.0)

    assert tap.key == "Mouse_Right"
    assert canvas.active_listening_widget is None

    # Simulate M4 click (button 8)
    tap2 = canvas.create_listening_tap(250.0, 250.0)
    mock_gesture.get_current_button.return_value = 8
    canvas._on_canvas_pressed(mock_gesture, n_press=1, x=250.0, y=250.0)

    assert tap2.key == "Mouse_4"
    assert canvas.active_listening_widget is None


def test_canvas_singleton_dpad_and_aim(canvas_setup):
    """Verify that adding a second DPad or Aim repositions the existing one per D-08."""
    canvas, profile, saver, toast_overlay = canvas_setup

    # 1. Add first DPad
    canvas.add_special_widget("dpad", target_x=200.0, target_y=300.0)
    assert len([w for w in profile.widgets if w.type == "dpad"]) == 1
    dpad = next(w for w in profile.widgets if w.type == "dpad")
    assert dpad.x == 200.0
    assert dpad.y == 300.0

    # Try adding second DPad at new coordinates
    toast_overlay.reset_mock()
    canvas.add_special_widget("dpad", target_x=450.0, target_y=550.0)
    assert len([w for w in profile.widgets if w.type == "dpad"]) == 1
    assert dpad.x == 450.0
    assert dpad.y == 550.0
    assert toast_overlay.add_toast.called

    # 2. Add first Aim
    canvas.add_special_widget("aim", target_x=700.0, target_y=500.0)
    assert len([w for w in profile.widgets if w.type == "aim"]) == 1
    aim = next(w for w in profile.widgets if w.type == "aim")
    assert aim.x == 700.0
    assert aim.y == 500.0

    # Try adding second Aim
    toast_overlay.reset_mock()
    canvas.add_special_widget("aim", target_x=800.0, target_y=600.0)
    assert len([w for w in profile.widgets if w.type == "aim"]) == 1
    assert aim.x == 800.0
    assert aim.y == 600.0
    assert toast_overlay.add_toast.called


def test_canvas_delete_and_resize(canvas_setup):
    """Verify widget deletion (D-07) and area resizing (D-06)."""
    canvas, profile, saver, _ = canvas_setup

    canvas.add_special_widget("dpad", target_x=200.0, target_y=200.0)
    canvas.add_special_widget("aim", target_x=600.0, target_y=400.0)
    assert len(profile.widgets) == 2

    # Resize DPad radius
    canvas.resize_widget_area("dpad_main", new_radius=120.0)
    dpad = next(w for w in profile.widgets if w.id == "dpad_main")
    assert dpad.radius == 120.0

    # Resize Aim width and height
    canvas.resize_widget_area("aim_main", new_width=500.0, new_height=350.0)
    aim = next(w for w in profile.widgets if w.id == "aim_main")
    assert aim.width == 500.0
    assert aim.height == 350.0

    # Delete DPad via method
    canvas.delete_widget("dpad_main")
    assert len(profile.widgets) == 1
    assert "dpad_main" not in canvas.widget_views

    # Select Aim and delete via Delete key
    canvas.selected_widget = aim
    controller = MagicMock(spec=Gtk.EventControllerKey)
    handled = canvas._on_key_pressed(controller, Gdk.KEY_Delete, 0, 0)
    assert handled is True
    assert len(profile.widgets) == 0
    assert "aim_main" not in canvas.widget_views
