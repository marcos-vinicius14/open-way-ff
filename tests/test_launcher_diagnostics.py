"""Unit tests for WayFireLauncherWindow health card diagnostics and package selection."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch
import pytest

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk

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
def diagnostics_fixture(tmp_path):
    runner = MockCommandRunner()
    runner.set_scripted_output("waydroid status", returncode=0, stdout="Session: RUNNING\nContainer: RUNNING\n")
    runner.set_scripted_output("systemctl is-active", returncode=0, stdout="active\n")
    runner.set_scripted_output("waydroid prop get ro.product.model", returncode=0, stdout="ASUS_I005D\n")
    runner.set_scripted_output("waydroid prop get persist.waydroid.width", returncode=0, stdout="1440\n")
    runner.set_scripted_output("waydroid prop get persist.waydroid.height", returncode=0, stdout="1080\n")
    runner.set_scripted_output("waydroid app list", returncode=0, stdout="com.dts.freefireth\ncom.dts.freefiremax\n")

    controller = WaydroidController(runner=runner, backup_path=tmp_path / "backup.json")
    pm = ProfileManager(profiles_dir=tmp_path / "profiles", active_file=tmp_path / "active")

    coordinator = MagicMock(spec=GameSessionCoordinator)
    coordinator.profile_manager = pm
    coordinator.waydroid_controller = controller
    coordinator.state = SessionState.STOPPED

    with patch("os.access", return_value=True):
        win = WayFireLauncherWindow(coordinator=coordinator, profile_manager=pm, auto_poll_health=False)

    return win, controller, runner


def test_health_card_pillars_status_green(diagnostics_fixture):
    """Verify health card displays green status badges when all 4 pillars are healthy (D-13)."""
    win, _, _ = diagnostics_fixture

    with patch("os.access", return_value=True):
        win.poll_system_health()

    assert win.badge_waydroid.get_label() == "Ativo"
    assert win.badge_waydroid.has_css_class("badge-status-green")
    assert win.btn_fix_waydroid.get_visible() is False

    assert win.badge_uinput.get_label() == "Liberado"
    assert win.badge_uinput.has_css_class("badge-status-green")
    assert win.btn_help_uinput.get_visible() is False

    assert "Ativo" in win.badge_spoof.get_label()
    assert win.badge_spoof.has_css_class("badge-status-green")
    assert win.btn_fix_spoof.get_visible() is False

    assert win.badge_res_status.get_label() == "1440x1080"

    win.destroy()


def test_health_card_waydroid_inactive_shows_auto_fix(diagnostics_fixture):
    """Verify inactive waydroid container triggers red badge and Auto-Fix button (D-14)."""
    win, controller, runner = diagnostics_fixture

    # Script inactive container
    runner.set_scripted_output("systemctl is-active", returncode=3, stdout="inactive\n")
    runner.set_scripted_output("waydroid status", returncode=0, stdout="Session: STOPPED\nContainer: STOPPED\n")

    win.poll_system_health()

    assert win.badge_waydroid.get_label() == "Inativo"
    assert win.badge_waydroid.has_css_class("badge-status-red")
    assert win.btn_fix_waydroid.get_visible() is True

    # Click auto-fix
    controller.ensure_container_active = MagicMock()
    win.btn_fix_waydroid.emit("clicked")
    controller.ensure_container_active.assert_called_once()

    win.destroy()


def test_health_card_uinput_permission_shows_instructions_dialog(diagnostics_fixture):
    """Verify missing uinput permission triggers red badge and shows instructions dialog (D-14)."""
    win, _, _ = diagnostics_fixture

    with patch("os.access", return_value=False):
        win.poll_system_health()

    assert win.badge_uinput.get_label() == "Sem Permissão"
    assert win.badge_uinput.has_css_class("badge-status-red")
    assert win.btn_help_uinput.get_visible() is True

    with patch.object(win, "_show_instructions_dialog") as mock_dialog:
        win.btn_help_uinput.emit("clicked")
        mock_dialog.assert_called_once()
        assert "sudo usermod -aG input" in mock_dialog.call_args[1]["command"]

    win.destroy()


def test_detect_both_packages_enables_package_selector(diagnostics_fixture):
    """Verify package dropdown offers selection between Standard and MAX (D-15)."""
    win, _, _ = diagnostics_fixture

    assert win.package_row.get_model().get_n_items() == 2
    # Select MAX
    win.package_row.set_selected(1)
    assert win.package_row.get_selected() == 1

    win.destroy()
