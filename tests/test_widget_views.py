"""Tests for HUD widget views, GG Mouse Pro styling, pressed feedback, and OSD opacity."""

from __future__ import annotations

import pytest

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from wayfire.ui.widget_views import (
    AimWidgetView,
    DPadWidgetView,
    FireWidgetView,
    MacroSequenceView,
    TapWidgetView,
)


@pytest.fixture(autouse=True)
def ensure_gtk():
    Gtk.init_check()


def test_widget_view_opacity_and_pressed_feedback():
    """Verify continuous opacity control and glowing press feedback behavior (D-10, D-11)."""
    view = TapWidgetView(widget_id="tap_test", key="Space")

    # Initial state with default opacity
    assert view.label.get_text() == "SPC"
    assert view.has_css_class("pressed") is False

    # Opacity 0.6
    view.set_opacity_level(0.6)
    assert view.osd_opacity == 0.6
    assert abs(view.get_opacity() - 0.6) < 0.01
    assert view.get_visible() is True

    # Press feedback active
    view.set_pressed(True)
    assert view.has_css_class("pressed") is True

    view.set_pressed(False)
    assert view.has_css_class("pressed") is False

    # Opacity 0.0: Full invisibility per D-10 & Prohibition 3
    view.set_opacity_level(0.0)
    assert view.osd_opacity == 0.0
    assert view.get_visible() is False

    # When opacity is 0, pressing a key must not display visual feedback
    view.set_pressed(True)
    assert view.has_css_class("pressed") is False


def test_widget_view_listening_mode():
    """Verify listening state toggles cyan pulse [ ? ] and restores compact label (D-05, D-13, D-14)."""
    view = TapWidgetView(widget_id="tap_m4", key="Mouse_4")
    assert view.label.get_text() == "M4"

    # Activate listening
    view.set_listening(True)
    assert view.label.get_text() == "[ ? ]"
    assert view.has_css_class("listening") is True

    # Cancel/Finish listening
    view.set_listening(False)
    assert view.label.get_text() == "M4"
    assert view.has_css_class("listening") is False


def test_special_widget_views():
    """Verify instantiation and properties of DPad, Aim, Fire, and Macro views."""
    dpad = DPadWidgetView(widget_id="dpad_1", radius=80.0)
    assert dpad.widget_type == "dpad"
    assert dpad.radius == 80.0

    aim = AimWidgetView(widget_id="aim_1", width=350.0, height=350.0)
    assert aim.widget_type == "aim"
    assert aim.width == 350.0

    fire = FireWidgetView(widget_id="fire_1")
    assert fire.widget_type == "fire"

    macro = MacroSequenceView(widget_id="macro_1", key="G", step_count=3)
    assert macro.widget_type == "macro"
    assert "G #3" in macro.label.get_text()
