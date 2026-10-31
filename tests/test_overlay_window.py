"""Tests for WayFireOverlayWindow, Layer Shell input regions, and StatusPill."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
import pytest
import cairo

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gtk

from wayfire.ui.overlay import OverlayMode, WayFireOverlayWindow
from wayfire.ui.status_pill import AimState, StatusPill


@pytest.fixture(autouse=True)
def ensure_gtk():
    """Ensure GTK is initialized before running tests."""
    Gtk.init_check()


class DummySurface:
    """Mock Gdk surface to capture set_input_region calls."""

    def __init__(self):
        self.last_region = None

    def set_input_region(self, region):
        self.last_region = region


class DummyNative:
    """Mock GtkNative providing dummy surface."""

    def __init__(self, surface):
        self._surface = surface

    def get_surface(self):
        return self._surface


def test_tracer_overlay_pass_through_and_modes():
    """Verify WayFireOverlayWindow switches modes and calculates cairo input regions correctly."""
    with patch("wayfire.ui.overlay.WayFireOverlayWindow._can_use_layer_shell", return_value=True), \
         patch("wayfire.ui.overlay.Gtk4LayerShell") as mock_layer_shell:

        mock_layer_shell.is_supported.return_value = True

        window = WayFireOverlayWindow(enable_layer_shell=True)
        dummy_surface = DummySurface()
        dummy_native = DummyNative(dummy_surface)

        with patch.object(window, "get_native", return_value=dummy_native):
            # 1. Default mode: GAME_LOCKED
            assert window.mode == OverlayMode.GAME_LOCKED
            assert window.compute_input_region_description() == "EMPTY"
            window._apply_input_region()
            assert isinstance(dummy_surface.last_region, cairo.Region)
            assert dummy_surface.last_region.is_empty()

            # 2. Suspended Game Mode with StatusPill rect
            pill_rect = cairo.RectangleInt(820, 8, 280, 36)
            window.set_game_mode(suspended=True, pill_rect=pill_rect)
            assert window.mode == OverlayMode.GAME_SUSPENDED
            assert window.compute_input_region_description() == "PILL_ONLY"
            window._apply_input_region()
            assert isinstance(dummy_surface.last_region, cairo.Region)
            assert not dummy_surface.last_region.is_empty()

            # 3. Edit Mode
            window.set_edit_mode()
            assert window.mode == OverlayMode.EDIT_MODE
            assert window.compute_input_region_description() == "FULLSCREEN"
            window._apply_input_region()
            assert dummy_surface.last_region is None

            # 4. Toggle back from Edit Mode (should return to suspended because pill_rect is set)
            toggled = window.toggle_edit_mode()
            assert toggled == OverlayMode.GAME_SUSPENDED
            assert window.compute_input_region_description() == "PILL_ONLY"

            # 5. Toggle to Edit Mode again
            toggled_again = window.toggle_edit_mode()
            assert toggled_again == OverlayMode.EDIT_MODE
            assert window.compute_input_region_description() == "FULLSCREEN"


def test_overlay_fallback_when_layer_shell_unavailable():
    """Verify graceful fullscreen fallback when Layer Shell is unavailable."""
    with patch("wayfire.ui.overlay.WayFireOverlayWindow._can_use_layer_shell", return_value=False):
        window = WayFireOverlayWindow(enable_layer_shell=True)
        assert window.is_layer_shell_active is False
        assert window.mode == OverlayMode.GAME_LOCKED
        assert window.compute_input_region_description() == "EMPTY"

    window_disabled = WayFireOverlayWindow(enable_layer_shell=False)
    assert window_disabled.is_layer_shell_active is False


def test_status_pill_state_transitions():
    """Verify StatusPill label, css class, button visibility and timeout handling."""
    pill = StatusPill()

    # Initial state should be LOCKED
    assert pill.current_state == AimState.LOCKED
    assert "🎯 MIRA TRAVADA" in pill.label.get_text()
    assert pill.edit_button.get_visible() is False
    assert pill.get_visible() is True
    assert pill._fadeout_source_id is not None

    # Switch to SUSPENDED
    pill.set_aim_state(AimState.SUSPENDED)
    assert pill.current_state == AimState.SUSPENDED
    assert "🔓 MOUSE LIVRE [F1]" in pill.label.get_text()
    assert pill.edit_button.get_visible() is True
    assert pill.get_visible() is True
    assert pill._fadeout_source_id is None

    # Switch back to LOCKED
    pill.set_aim_state(AimState.LOCKED)
    assert pill.current_state == AimState.LOCKED
    assert pill.edit_button.get_visible() is False
    assert pill._fadeout_source_id is not None

    # Simulate fadeout timeout
    result = pill._on_fadeout_timeout()
    assert result == GLib.SOURCE_REMOVE
    assert pill.get_visible() is False
    assert pill._fadeout_source_id is None


def test_status_pill_cairo_bounding_box():
    """Verify rectangular coordinate calculations for the status pill."""
    pill = StatusPill()
    rect_1080p = pill.get_pill_rectangle(screen_width=1920)
    assert rect_1080p.width == 280
    assert rect_1080p.height == 36
    assert rect_1080p.y == 8
    assert rect_1080p.x == (1920 - 280) // 2

    rect_720p = pill.get_pill_rectangle(screen_width=1280)
    assert rect_720p.x == (1280 - 280) // 2
    assert rect_720p.y == 8


def test_pill_edit_button_triggers_edit_mode():
    """Verify clicking the edit button invokes on_edit_requested callback."""
    called = []

    def on_edit():
        called.append(True)

    pill = StatusPill(on_edit_requested=on_edit)
    pill.set_aim_state(AimState.SUSPENDED)
    pill.edit_button.emit("clicked")

    assert len(called) == 1


def test_set_aim_locked_integration():
    """Verify WayFireOverlayWindow.set_aim_locked synchronizes pill and input region."""
    window = WayFireOverlayWindow(enable_layer_shell=False)

    # Aim locked (game active): pill is LOCKED, input region is EMPTY
    window.set_aim_locked(True)
    assert window.status_pill.current_state == AimState.LOCKED
    assert window.mode == OverlayMode.GAME_LOCKED
    assert window.compute_input_region_description() == "EMPTY"

    # Aim unlocked (mouse suspended): pill is SUSPENDED, input region is PILL_ONLY
    window.set_aim_locked(False)
    assert window.status_pill.current_state == AimState.SUSPENDED
    assert window.mode == OverlayMode.GAME_SUSPENDED
    assert window.compute_input_region_description() == "PILL_ONLY"

    # Toggle to edit mode from pill button
    window.status_pill.edit_button.emit("clicked")
    assert window.mode == OverlayMode.EDIT_MODE
    assert window.compute_input_region_description() == "FULLSCREEN"
