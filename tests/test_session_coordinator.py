"""Unit tests for GameSessionCoordinator lifecycle, boot sequence, and hot-reload."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch
import pytest

from wayfire.config.profile import WayFireProfile
from wayfire.config.profile_manager import ProfileManager
from wayfire.core.session_coordinator import GameSessionCoordinator, SessionState
from wayfire.core.touch_injector import MockUInputSink, TouchInjector
from wayfire.waydroid.controller import MockCommandRunner, WaydroidController


@pytest.fixture
def mock_env(tmp_path):
    """Hermetic test environment with mocked system commands, profile manager, and uinput."""
    runner = MockCommandRunner()
    # Script status output so session starts immediately
    runner.set_scripted_output(
        "waydroid status",
        returncode=0,
        stdout="Session: RUNNING\nContainer: RUNNING\n",
    )
    runner.set_scripted_output("systemctl is-active", returncode=0, stdout="active\n")
    runner.set_scripted_output("waydroid prop get ro.product.model", returncode=0, stdout="ASUS_I005D\n")
    runner.set_scripted_output("waydroid prop get persist.waydroid.width", returncode=0, stdout="1920\n")
    runner.set_scripted_output("waydroid prop get persist.waydroid.height", returncode=0, stdout="1080\n")
    runner.set_scripted_output("waydroid app list", returncode=0, stdout="com.dts.freefireth\n")
    runner.set_scripted_output("waydroid app launch", returncode=0, stdout="")
    runner.set_scripted_output("waydroid shell am force-stop", returncode=0, stdout="")

    controller = WaydroidController(runner=runner, backup_path=tmp_path / "backup.json")
    pm = ProfileManager(profiles_dir=tmp_path / "profiles", active_file=tmp_path / "active")

    profile = WayFireProfile(name="test_coordinator_profile")
    profile.sens_x = 1.5
    profile.sens_y = 3.0
    pm.save_profile(profile, "test_coordinator_profile")
    pm.set_active_profile("test_coordinator_profile")

    sink = MockUInputSink()
    injector_factory = lambda w, h: TouchInjector(sink=sink, width=w, height=h)
    device_detector = lambda: (None, None)

    coordinator = GameSessionCoordinator(
        profile_manager=pm,
        waydroid_controller=controller,
        injector_factory=injector_factory,
        device_detector=device_detector,
        sync_callbacks=True,
    )
    return coordinator, runner, sink, pm


def test_coordinator_supervised_boot_sequence_calls(mock_env):
    """Verify supervised boot sequence executes all 5 steps in the exact specified order (D-07)."""
    coordinator, runner, sink, pm = mock_env

    progress_events = []
    state_events = []
    coordinator.on_progress = lambda s, t, msg: progress_events.append((s, t, msg))
    coordinator.on_state_change = lambda st, msg: state_events.append((st, msg))

    completed = threading_event = MagicMock()

    coordinator.start_session_async(
        package="com.dts.freefireth",
        enable_overlay=False,
        on_completed=lambda ok, err: completed(ok, err),
    )

    coordinator.worker_thread.join(timeout=3.0)

    assert coordinator.state == SessionState.RUNNING
    assert completed.call_count == 1
    assert completed.call_args[0] == (True, None)

    # Verify progress notifications: exactly 5 steps in sequence
    assert len(progress_events) == 5
    assert progress_events[0][0] == 1
    assert "contêiner" in progress_events[0][2].lower()
    assert progress_events[1][0] == 2
    assert "resolução" in progress_events[1][2].lower()
    assert progress_events[2][0] == 3
    assert "spoofing" in progress_events[2][2].lower()
    assert progress_events[3][0] == 4
    assert "sessão" in progress_events[3][2].lower()
    assert progress_events[4][0] == 5
    assert "lançando" in progress_events[4][2].lower()

    # Verify command execution order in runner
    calls_flattened = [" ".join(c) for c in runner.recorded_calls]

    # Step 1: container check
    assert any("systemctl is-active waydroid-container.service" in c for c in calls_flattened)
    # Step 4: waydroid session
    assert any("waydroid status" in c for c in calls_flattened)
    # Step 5: launch app
    assert any("waydroid app launch com.dts.freefireth" in c for c in calls_flattened)

    # Motors must be active
    assert coordinator.injector is not None
    assert coordinator.aim_processor is not None
    assert coordinator.aim_engine is not None
    assert coordinator.keymap_engine is not None
    assert coordinator.capture_manager is not None

    coordinator.stop_session()


def test_coordinator_hot_reload_sensitivity_updates_live_processor(mock_env):
    """Verify set_sensitivity dynamically updates live AimProcessor and persists to profile (D-08)."""
    coordinator, runner, sink, pm = mock_env

    done = MagicMock()
    coordinator.start_session_async(enable_overlay=False, on_completed=done)
    coordinator.worker_thread.join(timeout=3.0)

    assert coordinator.aim_processor.sens_x == 1.5
    assert coordinator.aim_processor.sens_y == 3.0

    # Hot-reload sensitivity
    coordinator.set_sensitivity(sens_x=2.25, sens_y=4.50)

    # Live processor updated immediately
    assert coordinator.aim_processor.sens_x == 2.25
    assert coordinator.aim_processor.sens_y == 4.50

    # Profile saved to disk
    reloaded = pm.load_profile("test_coordinator_profile")
    assert reloaded.sens_x == 2.25
    assert reloaded.sens_y == 4.50

    coordinator.stop_session()


def test_coordinator_stop_session_cleans_up_devices_and_app(mock_env):
    """Verify stop_session cleans up resources and sends am force-stop to app (D-06)."""
    coordinator, runner, sink, pm = mock_env

    done = MagicMock()
    coordinator.start_session_async(
        package="com.dts.freefireth",
        enable_overlay=False,
        on_completed=done,
    )
    coordinator.worker_thread.join(timeout=3.0)

    assert coordinator.state == SessionState.RUNNING

    stopped = coordinator.stop_session()
    assert stopped is True
    assert coordinator.state == SessionState.STOPPED
    assert coordinator.injector is None
    assert coordinator.capture_manager is None

    # Check am force-stop was invoked
    calls_flattened = [" ".join(c) for c in runner.recorded_calls]
    assert any("waydroid shell am force-stop com.dts.freefireth" in c for c in calls_flattened)


def test_coordinator_lock_change_hooks_dpad_reset_and_recenter(mock_env):
    """Verify toggling aim lock hooks reset_dpad (suspension) and recenter_dpad (aim lock) (D-09, D-10)."""
    coordinator, runner, sink, pm = mock_env

    done = MagicMock()
    coordinator.start_session_async(enable_overlay=False, on_completed=done)
    coordinator.worker_thread.join(timeout=3.0)

    keymap_mock = coordinator.keymap_engine
    keymap_mock.recenter_dpad = MagicMock()
    keymap_mock.reset_dpad = MagicMock()

    # Simulate locking aim
    coordinator._on_lock_changed(True)
    assert keymap_mock.recenter_dpad.call_count == 1
    assert keymap_mock.reset_dpad.call_count == 0

    # Simulate suspending aim
    coordinator._on_lock_changed(False)
    assert keymap_mock.recenter_dpad.call_count == 1
    assert keymap_mock.reset_dpad.call_count == 1

    coordinator.stop_session()


def test_coordinator_panic_hook_triggers_panic_reset(mock_env):
    """Verify emergency panic callback triggers panic_reset on keymap and resets aim processor (D-11)."""
    coordinator, runner, sink, pm = mock_env

    done = MagicMock()
    coordinator.start_session_async(enable_overlay=False, on_completed=done)
    coordinator.worker_thread.join(timeout=3.0)

    coordinator.keymap_engine.panic_reset = MagicMock()
    coordinator.aim_processor.reset_state = MagicMock()

    coordinator._on_panic()

    assert coordinator.keymap_engine.panic_reset.call_count == 1
    assert coordinator.aim_processor.reset_state.call_count == 1

    coordinator.stop_session()


def test_coordinator_cannot_start_twice(mock_env):
    """Verify starting an already running session raises RuntimeError."""
    coordinator, _, _, _ = mock_env
    coordinator.state = SessionState.RUNNING

    with pytest.raises(RuntimeError, match="Sessão já em andamento"):
        coordinator.start_session_async()
