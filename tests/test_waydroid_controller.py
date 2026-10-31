"""Hermetic tests for WaydroidController lifecycle, resolutions, spoofing and clean env."""

import os
import subprocess
from pathlib import Path
import pytest

from wayfire.waydroid.controller import (
    MockCommandRunner,
    ROG_PHONE_PROPS,
    ResolutionPreset,
    WaydroidController,
    WaydroidStatus,
    get_clean_env,
)


def test_get_clean_env_strips_virtualenv(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure get_clean_env removes virtualenv variables and PATH segments."""
    monkeypatch.setenv("VIRTUAL_ENV", "/home/user/project/.venv")
    monkeypatch.setenv("PYTHONHOME", "/home/user/project/.venv")
    monkeypatch.setenv("PYTHONPATH", "/home/user/project/src")
    monkeypatch.setenv(
        "PATH",
        "/home/user/project/.venv/bin:/usr/local/bin:/usr/bin:/home/user/.virtualenvs/test/bin",
    )

    clean = get_clean_env()
    assert "VIRTUAL_ENV" not in clean
    assert "PYTHONHOME" not in clean
    assert "PYTHONPATH" not in clean

    parts = clean["PATH"].split(os.pathsep)
    assert "/usr/local/bin" in parts
    assert "/usr/bin" in parts
    assert not any("venv" in p.lower() or ".virtualenvs" in p.lower() for p in parts)


def test_waydroid_status_is_ready() -> None:
    """Ensure WaydroidStatus.is_ready requires both session and container RUNNING."""
    s = WaydroidStatus(session="STOPPED", container="STOPPED")
    assert not s.is_ready

    s = WaydroidStatus(session="RUNNING", container="STOPPED")
    assert not s.is_ready

    s = WaydroidStatus(session="STOPPED", container="RUNNING")
    assert not s.is_ready

    s = WaydroidStatus(session="RUNNING", container="RUNNING")
    assert s.is_ready


def test_tracer_waydroid_controller_lifecycle() -> None:
    """Tracer test validating end-to-end lifecycle orchestration hermetically."""
    runner = MockCommandRunner()

    # Initial state: container active, session stopped
    runner.set_scripted_output("systemctl is-active waydroid-container.service", 0, "active\n")
    runner.set_scripted_output(
        "waydroid status",
        0,
        "Session: STOPPED\nContainer: RUNNING\nWaydroid IP: 192.168.240.112\n",
    )
    runner.set_scripted_output(
        "waydroid app list",
        0,
        "com.android.settings\ncom.dts.freefireth\norg.lineageos.jelly\n",
    )
    runner.set_scripted_output("waydroid app launch com.dts.freefireth", 0, "Launching app...\n")
    runner.set_scripted_output("waydroid shell am force-stop com.dts.freefireth", 0, "")

    def _on_popen(cmd: list[str]) -> None:
        if cmd == ["waydroid", "session", "start"]:
            runner.set_scripted_output(
                "waydroid status",
                0,
                "Session: RUNNING\nContainer: RUNNING\nWaydroid IP: 192.168.240.112\n",
            )

    runner.on_popen = _on_popen

    controller = WaydroidController(runner=runner)

    # 1. Check & ensure container
    assert controller.ensure_container_active() is True

    # 2. Start session (invokes popen, transitions status to RUNNING via hook)
    assert controller.start_session(timeout=2.0, poll_interval=0.01) is True

    # 3. Detect package
    pkg = controller.detect_freefire_package()
    assert pkg == "com.dts.freefireth"

    # 4. Launch app
    assert controller.launch_app(pkg) is True

    # 5. Stop app gracefully
    assert controller.stop_app(pkg, full=False) is True

    # Validate recorded calls
    flattened_calls = [" ".join(call) for call in runner.recorded_calls]
    assert "systemctl is-active waydroid-container.service" in flattened_calls
    assert "waydroid app launch com.dts.freefireth" in flattened_calls
    assert "waydroid shell am force-stop com.dts.freefireth" in flattened_calls
    assert len(runner.mock_popens) == 1
    assert runner.mock_popens[0].cmd == ["waydroid", "session", "start"]


def test_ensure_container_raises_on_failure() -> None:
    """Ensure RuntimeError is raised when container service cannot be started."""
    runner = MockCommandRunner()
    runner.set_scripted_output("systemctl is-active waydroid-container.service", 3, "inactive\n")
    runner.set_scripted_output("waydroid status", 0, "Session: STOPPED\nContainer: STOPPED\n")
    runner.set_scripted_output("systemctl start waydroid-container.service", 1, "Failed\n")
    runner.set_scripted_output("pkexec systemctl start waydroid-container.service", 1, "Failed\n")

    controller = WaydroidController(runner=runner)
    with pytest.raises(RuntimeError, match="O serviço do contêiner Waydroid está parado"):
        controller.ensure_container_active()


def test_detect_freefire_package_precedence() -> None:
    """Validate package detection prefers override, then MAX, then Standard, then fallback."""
    runner = MockCommandRunner()
    controller = WaydroidController(runner=runner)

    # 1. Override
    assert controller.detect_freefire_package("com.custom.ff") == "com.custom.ff"

    # 2. MAX installed
    runner.set_scripted_output(
        "waydroid app list",
        0,
        "com.dts.freefiremax\ncom.dts.freefireth\n",
    )
    assert controller.detect_freefire_package() == "com.dts.freefiremax"

    # 3. Only Standard installed
    runner.set_scripted_output(
        "waydroid app list",
        0,
        "com.android.settings\ncom.dts.freefireth\n",
    )
    assert controller.detect_freefire_package() == "com.dts.freefireth"

    # 4. Fallback when none found
    runner.set_scripted_output("waydroid app list", 0, "com.android.settings\n")
    assert controller.detect_freefire_package() == "com.dts.freefireth"

    # 5. Invalid name raises ValueError (T-02-02)
    with pytest.raises(ValueError, match="Nome de pacote inválido"):
        controller.detect_freefire_package("invalid; rm -rf /")


def test_set_resolution_idempotent() -> None:
    """Ensure set_resolution does nothing when dimensions already match."""
    runner = MockCommandRunner()
    runner.set_scripted_output("waydroid prop get persist.waydroid.width", 0, "1440\n")
    runner.set_scripted_output("waydroid prop get persist.waydroid.height", 0, "1080\n")

    controller = WaydroidController(runner=runner)
    changed = controller.set_resolution(1440, 1080)
    assert changed is False

    # Should only have read width and height, no prop set
    flattened_calls = [" ".join(call) for call in runner.recorded_calls]
    assert not any("set" in c for c in flattened_calls)


def test_set_resolution_restart_when_running() -> None:
    """Ensure set_resolution sets properties and restarts session if RUNNING."""
    runner = MockCommandRunner()
    runner.set_scripted_output("waydroid prop get persist.waydroid.width", 0, "1920\n")
    runner.set_scripted_output("waydroid prop get persist.waydroid.height", 0, "1080\n")
    runner.set_scripted_output("waydroid prop set persist.waydroid.width 1440", 0, "")
    runner.set_scripted_output("waydroid prop set persist.waydroid.height 1080", 0, "")
    runner.set_scripted_output("waydroid status", 0, "Session: RUNNING\nContainer: RUNNING\n")
    runner.set_scripted_output("waydroid session stop", 0, "")

    def _on_run(cmd: list[str]) -> None:
        if cmd == ["waydroid", "session", "stop"]:
            runner.set_scripted_output("waydroid status", 0, "Session: STOPPED\nContainer: RUNNING\n")

    def _on_popen(cmd: list[str]) -> None:
        if cmd == ["waydroid", "session", "start"]:
            runner.set_scripted_output("waydroid status", 0, "Session: RUNNING\nContainer: RUNNING\n")

    runner.on_run = _on_run
    runner.on_popen = _on_popen

    controller = WaydroidController(runner=runner)

    changed = controller.set_resolution(1440, 1080, restart_if_running=True)
    assert changed is True

    flattened_calls = [" ".join(call) for call in runner.recorded_calls]
    assert "waydroid prop set persist.waydroid.width 1440" in flattened_calls
    assert "waydroid prop set persist.waydroid.height 1080" in flattened_calls
    assert "waydroid session stop" in flattened_calls


def test_spoofing_backup_and_apply(tmp_path: Path) -> None:
    """Ensure apply_spoofing backs up original props and injects 5 ROG Phone props."""
    backup_file = tmp_path / "device_backup.json"
    runner = MockCommandRunner()

    runner.set_scripted_output("waydroid prop get ro.product.model", 0, "Redmi Note 8\n")
    runner.set_scripted_output("waydroid prop get ro.product.brand", 0, "Xiaomi\n")
    runner.set_scripted_output("waydroid prop get ro.product.manufacturer", 0, "Xiaomi\n")
    runner.set_scripted_output("waydroid prop get ro.product.name", 0, "ginkgo\n")
    runner.set_scripted_output("waydroid prop get ro.product.device", 0, "ginkgo\n")

    controller = WaydroidController(runner=runner, backup_path=backup_file)
    assert controller.is_spoofing_applied() is False

    res = controller.apply_spoofing()
    assert res is True
    assert backup_file.exists()

    # Check backup content
    import json

    with open(backup_file, "r") as f:
        data = json.load(f)
    assert data["ro.product.model"] == "Redmi Note 8"
    assert data["ro.product.brand"] == "Xiaomi"

    # Check that ROG phone props were set
    flattened_calls = [" ".join(call) for call in runner.recorded_calls]
    for prop, val in ROG_PHONE_PROPS.items():
        assert f"waydroid prop set {prop} {val}" in flattened_calls


def test_spoofing_skipped_if_already_asus(tmp_path: Path) -> None:
    """Ensure apply_spoofing is a no-op if model is already ASUS_I005D."""
    backup_file = tmp_path / "device_backup.json"
    runner = MockCommandRunner()
    runner.set_scripted_output("waydroid prop get ro.product.model", 0, "ASUS_I005D\n")

    controller = WaydroidController(runner=runner, backup_path=backup_file)
    assert controller.is_spoofing_applied() is True

    res = controller.apply_spoofing()
    assert res is True
    assert not backup_file.exists()


def test_restore_spoofing(tmp_path: Path) -> None:
    """Ensure restore_spoofing writes original properties back."""
    backup_file = tmp_path / "device_backup.json"
    import json

    backup_data = {
        "ro.product.brand": "google",
        "ro.product.manufacturer": "Google",
        "ro.product.model": "Pixel 5",
        "ro.product.name": "redfin",
        "ro.product.device": "redfin",
    }
    with open(backup_file, "w") as f:
        json.dump(backup_data, f)

    runner = MockCommandRunner()
    controller = WaydroidController(runner=runner, backup_path=backup_file)
    assert controller.restore_spoofing() is True

    flattened_calls = [" ".join(call) for call in runner.recorded_calls]
    assert "waydroid prop set ro.product.model Pixel 5" in flattened_calls
    assert "waydroid prop set ro.product.brand google" in flattened_calls


def test_restore_spoofing_raises_when_no_backup(tmp_path: Path) -> None:
    """Ensure FileNotFoundError is raised when backup is missing."""
    backup_file = tmp_path / "non_existent.json"
    runner = MockCommandRunner()
    controller = WaydroidController(runner=runner, backup_path=backup_file)

    with pytest.raises(FileNotFoundError, match="Arquivo de backup não encontrado"):
        controller.restore_spoofing()
