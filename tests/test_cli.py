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


def test_cli_launch_stop_spoof_argument_parsing() -> None:
    """Verify CLI parser handles launch, stop, and spoof subcommands with all flags."""
    parser = build_parser()

    # Launch args
    l_args = parser.parse_args(["launch", "--stretched", "--package", "com.dts.freefiremax", "--no-spoof"])
    assert l_args.command == "launch"
    assert l_args.stretched is True
    assert l_args.package == "com.dts.freefiremax"
    assert l_args.no_spoof is True

    # Stop args
    s_args = parser.parse_args(["stop", "--full", "--package", "com.custom.ff"])
    assert s_args.command == "stop"
    assert s_args.full is True
    assert s_args.package == "com.custom.ff"

    # Spoof args
    sp_status = parser.parse_args(["spoof", "--status"])
    assert sp_status.command == "spoof"
    assert sp_status.status is True

    sp_apply = parser.parse_args(["spoof", "--apply"])
    assert sp_apply.command == "spoof"
    assert sp_apply.apply is True

    sp_restore = parser.parse_args(["spoof", "--restore"])
    assert sp_restore.command == "spoof"
    assert sp_restore.restore is True


def test_cmd_launch_execution_order() -> None:
    """Verify cmd_launch executes operations in proper sequence: container -> res -> spoof -> session -> launch."""
    from unittest.mock import MagicMock
    from wayfire.cli.main import cmd_launch

    mock_ctrl = MagicMock()
    mock_ctrl.ensure_container_active.return_value = True
    mock_ctrl.detect_freefire_package.return_value = "com.dts.freefireth"
    mock_ctrl.launch_app.return_value = True

    parser = build_parser()
    args = parser.parse_args(["launch", "--stretched"])

    ret = cmd_launch(args, controller=mock_ctrl)
    assert ret == 0

    mock_ctrl.ensure_container_active.assert_called_once()
    mock_ctrl.set_resolution.assert_called_once_with(1440, 1080)
    mock_ctrl.apply_spoofing.assert_called_once()
    mock_ctrl.start_session.assert_called_once()
    mock_ctrl.launch_app.assert_called_once_with("com.dts.freefireth")


def test_cmd_stop_execution() -> None:
    """Verify cmd_stop handles standard stop and full session stop."""
    from unittest.mock import MagicMock
    from wayfire.cli.main import cmd_stop

    mock_ctrl = MagicMock()

    # Standard stop
    parser = build_parser()
    args_normal = parser.parse_args(["stop"])
    assert cmd_stop(args_normal, controller=mock_ctrl) == 0
    mock_ctrl.stop_app.assert_called_with("com.dts.freefireth", full=False)

    # Full stop
    args_full = parser.parse_args(["stop", "--full", "--package", "com.dts.freefiremax"])
    assert cmd_stop(args_full, controller=mock_ctrl) == 0
    mock_ctrl.stop_app.assert_called_with("com.dts.freefiremax", full=True)


def test_cmd_spoof_execution(tmp_path: Path) -> None:
    """Verify cmd_spoof handles --status, --apply, and --restore."""
    from unittest.mock import MagicMock
    from wayfire.cli.main import cmd_spoof

    mock_ctrl = MagicMock()
    mock_ctrl.backup_path = tmp_path / "device_backup.json"

    parser = build_parser()

    # Status
    mock_ctrl.is_spoofing_applied.return_value = True
    args_status = parser.parse_args(["spoof", "--status"])
    assert cmd_spoof(args_status, controller=mock_ctrl) == 0

    # Apply
    args_apply = parser.parse_args(["spoof", "--apply"])
    assert cmd_spoof(args_apply, controller=mock_ctrl) == 0
    mock_ctrl.apply_spoofing.assert_called_once()

    # Restore
    args_restore = parser.parse_args(["spoof", "--restore"])
    assert cmd_spoof(args_restore, controller=mock_ctrl) == 0
    mock_ctrl.restore_spoofing.assert_called_once()


def test_cli_profile_subcommands(tmp_path: Path) -> None:
    """Verify wayfire profile list, active, show, import, export, delete."""
    from unittest.mock import MagicMock
    from wayfire.cli.main import cmd_profile

    mock_mgr = MagicMock()
    mock_mgr.list_profiles.return_value = ["default_freefire", "custom_1"]
    mock_mgr.get_active_profile_name.return_value = "default_freefire"

    parser = build_parser()

    # 1. profile list
    args_list = parser.parse_args(["profile", "list"])
    assert cmd_profile(args_list, manager=mock_mgr) == 0
    mock_mgr.list_profiles.assert_called_once()

    # 2. profile active (get)
    args_active_get = parser.parse_args(["profile", "active"])
    assert cmd_profile(args_active_get, manager=mock_mgr) == 0

    # 3. profile active (--set)
    args_active_set = parser.parse_args(["profile", "active", "--set", "custom_1"])
    assert cmd_profile(args_active_set, manager=mock_mgr) == 0
    mock_mgr.set_active_profile.assert_called_once_with("custom_1")

    # 4. profile show
    from wayfire.config.profile import create_default_profile

    mock_mgr.load_profile.return_value = create_default_profile()
    args_show = parser.parse_args(["profile", "show", "default_freefire"])
    assert cmd_profile(args_show, manager=mock_mgr) == 0
    mock_mgr.load_profile.assert_called_with("default_freefire")

    # 5. profile import
    args_import = parser.parse_args(["profile", "import", "/tmp/source.json", "--name", "new_p"])
    assert cmd_profile(args_import, manager=mock_mgr) == 0
    mock_mgr.import_profile.assert_called_once_with("/tmp/source.json", name="new_p")

    # 6. profile export
    args_export = parser.parse_args(["profile", "export", "default_freefire", "/tmp/dest.json"])
    assert cmd_profile(args_export, manager=mock_mgr) == 0
    mock_mgr.export_profile.assert_called_once_with("default_freefire", "/tmp/dest.json")

    # 7. profile delete
    mock_mgr.delete_profile.return_value = True
    args_delete = parser.parse_args(["profile", "delete", "custom_1"])
    assert cmd_profile(args_delete, manager=mock_mgr) == 0
    mock_mgr.delete_profile.assert_called_once_with("custom_1")


def test_cli_launcher_subcommand_and_default() -> None:
    """Verify 'wayfire launcher' and 'wayfire' (no subcommand) route to cmd_launcher."""
    from unittest.mock import patch
    parser = build_parser()

    args_launcher = parser.parse_args(["launcher"])
    assert args_launcher.command == "launcher"

    args_default = parser.parse_args([])
    assert args_default.command is None

    with patch("wayfire.cli.main.cmd_launcher", return_value=0) as mock_launch:
        assert main(["launcher"]) == 0
        mock_launch.assert_called_once()

    with patch("wayfire.cli.main.cmd_launcher", return_value=0) as mock_launch:
        assert main([]) == 0
        mock_launch.assert_called_once()



