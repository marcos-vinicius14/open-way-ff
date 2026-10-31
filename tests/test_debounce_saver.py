"""Tests for ProfileDebounceSaver and FloatingTopBar."""

from __future__ import annotations

import time
from unittest.mock import MagicMock
import pytest

import gi
gi.require_version("GLib", "2.0")
gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gtk

from wayfire.config.profile import WayFireProfile
from wayfire.config.profile_manager import ProfileManager
from wayfire.ui.debounce_saver import ProfileDebounceSaver
from wayfire.ui.floating_bar import FloatingTopBar


@pytest.fixture(autouse=True)
def ensure_gtk():
    Gtk.init_check()


@pytest.fixture
def mock_profile_manager(tmp_path):
    manager = ProfileManager(profiles_dir=tmp_path)
    return manager


@pytest.fixture
def sample_profile():
    return WayFireProfile(name="test_profile")


def test_debounce_saver_coalesces_rapid_calls(mock_profile_manager, sample_profile):
    """Verify that multiple rapid request_save calls coalesce into 1 actual save after timeout."""
    save_mock = MagicMock()
    mock_profile_manager.save_profile = save_mock

    saver = ProfileDebounceSaver(mock_profile_manager, debounce_ms=50)

    # Dispatch 10 rapid save requests
    for i in range(10):
        sample_profile.ui_settings.osd_opacity = 0.05 * i
        saver.request_save(sample_profile)

    assert saver.has_pending_save is True
    assert save_mock.call_count == 0

    # Pump GLib main loop until timer executes
    context = GLib.MainContext.default()
    start_time = time.time()
    while saver.has_pending_save and time.time() - start_time < 0.5:
        context.iteration(False)
        time.sleep(0.01)

    assert saver.has_pending_save is False
    assert save_mock.call_count == 1
    assert saver.save_count == 1


def test_debounce_saver_flush_commits_immediately(mock_profile_manager, sample_profile):
    """Verify that flush() executes pending save immediately without waiting for GLib timer."""
    save_mock = MagicMock()
    mock_profile_manager.save_profile = save_mock

    saver = ProfileDebounceSaver(mock_profile_manager, debounce_ms=5000)

    saver.request_save(sample_profile)
    assert saver.has_pending_save is True
    assert save_mock.call_count == 0

    # Flush immediately
    saver.flush()

    assert saver.has_pending_save is False
    assert save_mock.call_count == 1
    assert saver.save_count == 1


def test_floating_top_bar_actions():
    """Verify FloatingTopBar action buttons and opacity slider callbacks."""
    added_widgets = []
    opacity_values = []
    closed = []

    bar = FloatingTopBar(
        on_add_widget=lambda w: added_widgets.append(w),
        on_opacity_changed=lambda v: opacity_values.append(v),
        on_close_requested=lambda: closed.append(True),
    )

    bar.btn_dpad.emit("clicked")
    bar.btn_aim.emit("clicked")
    bar.btn_fire.emit("clicked")
    bar.btn_tap.emit("clicked")

    assert added_widgets == ["dpad", "aim", "fire", "tap"]

    bar.scale_opacity.set_value(0.4)
    assert len(opacity_values) >= 1
    assert abs(opacity_values[-1] - 0.4) < 0.01

    bar.btn_close.emit("clicked")
    assert len(closed) == 1
