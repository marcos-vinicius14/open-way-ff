"""Unit tests for CLI argument parsing, TUI rendering, and live calibration hotkeys."""

import io
from pathlib import Path
from unittest.mock import patch
from evdev import ecodes
from wayfire.config.profile import WayFireProfile
from wayfire.core.aim_engine import AimProcessor
from wayfire.cli.main import build_parser, handle_calibration_hotkey, main
from wayfire.ui.terminal_hud import TerminalHUD


def test_cli_argument_parsing() -> None:
    """Verify CLI parser handles run and test subcommands and flags."""
    parser = build_parser()

    # Test run subcommand
    run_args = parser.parse_args(["run", "--profile", "my_profile.json", "--width", "1920", "--height", "1080"])
    assert run_args.command == "run"
    assert run_args.profile == "my_profile.json"
    assert run_args.width == 1920
    assert run_args.height == 1080

    # Test test subcommand
    test_args = parser.parse_args(["test", "--devices", "--interactive"])
    assert test_args.command == "test"
    assert test_args.devices is True
    assert test_args.interactive is True


def test_live_sensitivity_adjustment(tmp_path: Path) -> None:
    """Verify F7..F10 hotkeys adjust sensitivity in steps of 0.05 and persist to profile."""
    profile_path = tmp_path / "live_profile.json"
    profile = WayFireProfile(sens_x=1.50, sens_y=3.00)
    profile.save(profile_path)

    processor = AimProcessor(sens_x=1.50, sens_y=3.00, smoothing=False)

    # F7: decrement Sens X by 0.05 -> 1.45
    changed = handle_calibration_hotkey(ecodes.KEY_F7, processor, profile, profile_path)
    assert changed is True
    assert processor.sens_x == 1.45
    assert profile.sens_x == 1.45

    # F8: increment Sens X by 0.05 -> 1.50
    changed = handle_calibration_hotkey(ecodes.KEY_F8, processor, profile, profile_path)
    assert changed is True
    assert processor.sens_x == 1.50

    # F9: decrement Sens Y by 0.05 -> 2.95
    changed = handle_calibration_hotkey(ecodes.KEY_F9, processor, profile, profile_path)
    assert changed is True
    assert processor.sens_y == 2.95
    assert profile.sens_y == 2.95

    # F10: increment Sens Y by 0.05 -> 3.00
    changed = handle_calibration_hotkey(ecodes.KEY_F10, processor, profile, profile_path)
    assert changed is True
    assert processor.sens_y == 3.00

    # Verify persisted to file
    reloaded = WayFireProfile.load(profile_path)
    assert reloaded.sens_x == 1.50
    assert reloaded.sens_y == 3.00


def test_live_sensitivity_clamped_at_minimum(tmp_path: Path) -> None:
    """Verify sensitivity adjustment does not drop below 0.05 safety floor."""
    profile = WayFireProfile(sens_x=0.08, sens_y=0.06)
    processor = AimProcessor(sens_x=0.08, sens_y=0.06, smoothing=False)

    handle_calibration_hotkey(ecodes.KEY_F7, processor, profile)
    # 0.08 - 0.05 = 0.03 -> clamped to 0.05
    assert processor.sens_x == 0.05


def test_terminal_hud_ansi_rendering() -> None:
    """Verify TerminalHUD formats both locked and suspended single-line ANSI status."""
    stream = io.StringIO()
    hud = TerminalHUD(stream=stream)

    # Render suspended
    hud.render(is_locked=False, sens_x=1.45, sens_y=3.20, force=True)
    out_suspended = stream.getvalue()
    assert "[🟡 SUSPENDED]" in out_suspended
    assert "Sens X: 1.45" in out_suspended
    assert "Sens Y: 3.20" in out_suspended

    # Render locked
    stream.truncate(0)
    stream.seek(0)
    hud.render(is_locked=True, sens_x=1.50, sens_y=3.25, dx=12, dy=-8, reset_count=4, force=True)
    out_locked = stream.getvalue()
    assert "[🟢 AIM LOCKED]" in out_locked
    assert "dx: +12" in out_locked
    assert "dy: -08" in out_locked
    assert "Resets: 4" in out_locked


def test_cmd_test_devices_execution() -> None:
    """Verify wayfire test --devices runs cleanly."""
    with patch("wayfire.cli.main.detect_input_devices", return_value=("/dev/input/event1", "/dev/input/event2")):
        ret = main(["test", "--devices"])
        assert ret == 0


def test_cmd_test_interactive_simulation() -> None:
    """Verify wayfire test --interactive runs simulation loop without errors."""
    ret = main(["test", "--interactive"])
    assert ret == 0
