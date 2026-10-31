"""Unit tests for WayFireLauncherWindow."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
import pytest

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib, Gtk

from wayfire.config.profile import WayFireProfile
from wayfire.config.profile_manager import ProfileManager
from wayfire.core.session_coordinator import GameSessionCoordinator, SessionState
from wayfire.ui.launcher_window import WayFireLauncherWindow
from wayfire.waydroid.controller import MockCommandRunner, WaydroidController


@pytest.fixture(autouse=True)
def ensure_gtk():
    """Ensure GTK/Adwaita is initialized."""
    Gtk.init_check()
    Adw.init()


@pytest.fixture
def launcher_fixture(tmp_path):
    """Hermetic fixture for WayFireLauncherWindow."""
    runner = MockCommandRunner()
    runner.set_scripted_output("waydroid status", returncode=0, stdout="Session: STOPPED\nContainer: RUNNING\n")
    runner.set_scripted_output("systemctl is-active", returncode=0, stdout="active\n")
    runner.set_scripted_output("waydroid prop get ro.product.model", returncode=0, stdout="ASUS_I005D\n")
    runner.set_scripted_output("waydroid prop get persist.waydroid.width", returncode=0, stdout="1920\n")
    runner.set_scripted_output("waydroid prop get persist.waydroid.height", returncode=0, stdout="1080\n")

    controller = WaydroidController(runner=runner, backup_path=tmp_path / "backup.json")
    pm = ProfileManager(profiles_dir=tmp_path / "profiles", active_file=tmp_path / "active")

    profile = WayFireProfile(name="default_freefire")
    profile.sens_x = 1.00
    profile.sens_y = 2.50
    profile.screen_width = 1920
    profile.screen_height = 1080
    pm.save_profile(profile, "default_freefire")
    pm.set_active_profile("default_freefire")

    coordinator = MagicMock(spec=GameSessionCoordinator)
    coordinator.profile_manager = pm
    coordinator.waydroid_controller = controller
    coordinator.state = SessionState.STOPPED
    coordinator.set_sensitivity = MagicMock()
    coordinator.set_resolution_preset = MagicMock()
    coordinator.start_session_async = MagicMock()
    coordinator.stop_session = MagicMock()

    win = WayFireLauncherWindow(coordinator=coordinator, profile_manager=pm, auto_poll_health=False)
    return win, coordinator, pm


def test_launcher_window_initialization(launcher_fixture):
    """Verify WayFireLauncherWindow initializes with all essential controls and Dark Theme (D-01, D-04)."""
    win, _, _ = launcher_fixture

    assert win.get_title() == "WayFire 🔥 - Central de Jogos"
    assert win.play_button is not None
    assert "JOGAR FREE FIRE" in win.play_button.get_label()
    assert win.scale_x is not None
    assert win.scale_y is not None
    assert win.capa_badge is not None
    assert win.btn_1080p is not None
    assert win.btn_1440p is not None
    assert win.btn_768p is not None
    assert win.profile_combo is not None
    assert win.row_waydroid is not None

    win.destroy()


def test_sensitivity_sliders_and_spinbuttons_sync(launcher_fixture):
    """Verify Scale and SpinButton sync bidirectionally with precision of 0.05 (D-02, D-08)."""
    win, coordinator, _ = launcher_fixture

    # 1. Update scale X -> updates spin X and calls coordinator
    win.scale_x.set_value(1.80)
    assert abs(win.spin_x.get_value() - 1.80) < 0.001
    coordinator.set_sensitivity.assert_called_with(sens_x=1.80, sens_y=2.50)

    # 2. Update spin Y -> updates scale Y and calls coordinator
    coordinator.set_sensitivity.reset_mock()
    win.spin_y.set_value(4.20)
    assert abs(win.scale_y.get_value() - 4.20) < 0.001
    coordinator.set_sensitivity.assert_called_with(sens_x=1.80, sens_y=4.20)

    win.destroy()


def test_capa_badge_calculation(launcher_fixture):
    """Verify Capa ratio badge classifies high (>=2.0x), mid, and low ratios (D-02)."""
    win, _, _ = launcher_fixture

    # High ratio (Y/X = 4.00 / 1.50 = 2.67x) -> badge-capa-high
    win.scale_x.set_value(1.50)
    win.scale_y.set_value(4.00)
    assert "Ideal para Subir Capa" in win.capa_badge.get_label()
    assert win.capa_badge.has_css_class("badge-capa-high")

    # Mid ratio (Y/X = 2.40 / 1.50 = 1.60x) -> badge-capa-mid
    win.scale_y.set_value(2.40)
    assert "Equilibrada" in win.capa_badge.get_label()
    assert win.capa_badge.has_css_class("badge-capa-mid")

    # Low ratio (Y/X = 1.50 / 1.50 = 1.00x) -> badge-capa-low
    win.scale_y.set_value(1.50)
    assert "Padrão" in win.capa_badge.get_label()
    assert win.capa_badge.has_css_class("badge-capa-low")

    win.destroy()


def test_resolution_pill_selection_updates_profile(launcher_fixture):
    """Verify clicking resolution pills highlights button and updates resolution preset (D-03)."""
    win, coordinator, _ = launcher_fixture

    # Click 1440x1080 Esticado [Comp]
    win.btn_1440p.emit("clicked")
    assert win.btn_1440p.has_css_class("pill-button-selected")
    assert not win.btn_1080p.has_css_class("pill-button-selected")
    coordinator.set_resolution_preset.assert_called_with(1440, 1080)

    # Click 1024x768 Esticado
    win.btn_768p.emit("clicked")
    assert win.btn_768p.has_css_class("pill-button-selected")
    assert not win.btn_1440p.has_css_class("pill-button-selected")
    coordinator.set_resolution_preset.assert_called_with(1024, 768)

    win.destroy()


def test_action_button_state_transitions(launcher_fixture):
    """Verify action button toggles Play and Stop sessions (D-01, D-06)."""
    win, coordinator, _ = launcher_fixture

    # 1. Click Play while STOPPED
    coordinator.state = SessionState.STOPPED
    win.play_button.emit("clicked")
    coordinator.start_session_async.assert_called_once()
    assert win.boot_spinner.get_visible() is True

    # 2. Simulate RUNNING state transition from coordinator
    win._on_coordinator_state_change(SessionState.RUNNING, "Jogo em execução")
    # Drain GLib idle queue
    for _ in range(10):
        if not GLib.main_context_default().iteration(False):
            break

    assert "PARAR JOGO" in win.play_button.get_label()
    assert win.play_button.has_css_class("wayfire-stop-btn")
    assert win.boot_spinner.get_visible() is False

    # 3. Click Stop while RUNNING
    coordinator.state = SessionState.RUNNING
    win.play_button.emit("clicked")
    coordinator.stop_session.assert_called_once()

    win.destroy()


def test_window_hides_on_play_and_restores_on_stop(launcher_fixture):
    """Verify window hides upon RUNNING and restores upon STOPPED (D-05)."""
    win, _, _ = launcher_fixture

    win.set_visible(True)
    assert win.get_visible() is True

    # Transition to RUNNING -> window hides
    win._on_coordinator_state_change(SessionState.RUNNING, "Partida iniciada")
    for _ in range(10):
        if not GLib.main_context_default().iteration(False):
            break

    assert win.get_visible() is False

    # Transition to STOPPED -> window restores
    win._on_coordinator_state_change(SessionState.STOPPED, "Partida encerrada")
    for _ in range(10):
        if not GLib.main_context_default().iteration(False):
            break

    assert win.get_visible() is True

    win.destroy()
