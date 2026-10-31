"""Waydroid lifecycle controller, stretched resolutions, hardware spoofing, and command execution."""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Optional, Protocol, runtime_checkable

ROG_PHONE_PROPS: dict[str, str] = {
    "ro.product.brand": "asus",
    "ro.product.manufacturer": "asus",
    "ro.product.model": "ASUS_I005D",
    "ro.product.name": "ASUS_I005D",
    "ro.product.device": "ASUS_I005D",
}

PACKAGE_REGEX = re.compile(r"^[a-zA-Z0-9._-]+$")


class ResolutionPreset(Enum):
    """Competitive resolution presets for Waydroid container."""

    NATIVE_1080P = (1920, 1080)
    STRETCHED_4_3 = (1440, 1080)
    STRETCHED_LIGHT = (1024, 768)


def get_clean_env() -> dict[str, str]:
    """Return environment variables cleaned of virtualenv pollution.

    Removes VIRTUAL_ENV, PYTHONHOME, PYTHONPATH and strips any virtualenv
    paths from PATH so host tools (like waydroid) run with system Python and libraries.
    """
    clean_env = os.environ.copy()
    clean_env.pop("VIRTUAL_ENV", None)
    clean_env.pop("PYTHONHOME", None)
    clean_env.pop("PYTHONPATH", None)

    current_path = clean_env.get("PATH", "")
    if current_path:
        filtered_parts = [
            part
            for part in current_path.split(os.pathsep)
            if not ("venv" in part.lower() or ".virtualenvs" in part.lower() or "/.venv/" in part)
        ]
        clean_env["PATH"] = os.pathsep.join(filtered_parts)

    return clean_env


@runtime_checkable
class CommandRunner(Protocol):
    """Decoupled interface for executing system commands."""

    def run(
        self,
        cmd: list[str],
        check: bool = False,
        capture_output: bool = True,
        text: bool = True,
        env: Optional[dict[str, str]] = None,
    ) -> subprocess.CompletedProcess[str]:
        """Execute a command synchronously."""
        ...

    def popen(
        self,
        cmd: list[str],
        env: Optional[dict[str, str]] = None,
        **kwargs: Any,
    ) -> subprocess.Popen[Any]:
        """Execute a command asynchronously in background."""
        ...


class SystemCommandRunner(CommandRunner):
    """Concrete CommandRunner executing real subprocess calls with sanitized environment."""

    def run(
        self,
        cmd: list[str],
        check: bool = False,
        capture_output: bool = True,
        text: bool = True,
        env: Optional[dict[str, str]] = None,
    ) -> subprocess.CompletedProcess[str]:
        actual_env = env if env is not None else get_clean_env()
        return subprocess.run(
            cmd,
            check=check,
            capture_output=capture_output,
            text=text,
            env=actual_env,
        )

    def popen(
        self,
        cmd: list[str],
        env: Optional[dict[str, str]] = None,
        **kwargs: Any,
    ) -> subprocess.Popen[Any]:
        actual_env = env if env is not None else get_clean_env()
        return subprocess.Popen(
            cmd,
            env=actual_env,
            **kwargs,
        )


class MockPopen:
    """Mock process object for MockCommandRunner."""

    def __init__(self, cmd: list[str], pid: int = 12345) -> None:
        self.cmd = cmd
        self.pid = pid
        self.returncode: Optional[int] = None
        self._terminated = False

    def poll(self) -> Optional[int]:
        return self.returncode

    def wait(self, timeout: Optional[float] = None) -> int:
        return self.returncode or 0

    def terminate(self) -> None:
        self._terminated = True
        self.returncode = 0

    def kill(self) -> None:
        self._terminated = True
        self.returncode = -9


class MockCommandRunner(CommandRunner):
    """Hermetic command runner for unit tests with scripted responses and call tracking."""

    def __init__(self) -> None:
        self.recorded_calls: list[list[str]] = []
        self.recorded_envs: list[Optional[dict[str, str]]] = []
        self.scripted_outputs: dict[str, tuple[int, str, str]] = {}
        self.mock_popens: list[MockPopen] = []
        self.on_run: Optional[Any] = None
        self.on_popen: Optional[Any] = None

    def set_scripted_output(self, cmd_key: str, returncode: int = 0, stdout: str = "", stderr: str = "") -> None:
        """Register a scripted output for an exact command or command prefix."""
        self.scripted_outputs[cmd_key] = (returncode, stdout, stderr)

    def run(
        self,
        cmd: list[str],
        check: bool = False,
        capture_output: bool = True,
        text: bool = True,
        env: Optional[dict[str, str]] = None,
    ) -> subprocess.CompletedProcess[str]:
        self.recorded_calls.append(list(cmd))
        self.recorded_envs.append(env)

        if self.on_run is not None:
            self.on_run(cmd)

        cmd_str = " ".join(cmd)
        rc, out, err = 0, "", ""

        # Exact match check
        if cmd_str in self.scripted_outputs:
            rc, out, err = self.scripted_outputs[cmd_str]
        else:
            # Prefix match check
            matched = False
            for key, val in self.scripted_outputs.items():
                if cmd_str.startswith(key):
                    rc, out, err = val
                    matched = True
                    break
            if not matched:
                rc, out, err = 0, "", ""

        completed = subprocess.CompletedProcess(args=cmd, returncode=rc, stdout=out, stderr=err)
        if check and rc != 0:
            raise subprocess.CalledProcessError(returncode=rc, cmd=cmd, output=out, stderr=err)
        return completed

    def popen(
        self,
        cmd: list[str],
        env: Optional[dict[str, str]] = None,
        **kwargs: Any,
    ) -> subprocess.Popen[Any]:
        self.recorded_calls.append(list(cmd))
        self.recorded_envs.append(env)

        if self.on_popen is not None:
            self.on_popen(cmd)

        proc = MockPopen(cmd=cmd)
        self.mock_popens.append(proc)
        return proc  # type: ignore[return-value]


@dataclass
class WaydroidStatus:
    """Waydroid session and container operational state."""

    session: str = "STOPPED"
    container: str = "STOPPED"

    @property
    def is_ready(self) -> bool:
        """True only if both session and container are RUNNING."""
        return self.session == "RUNNING" and self.container == "RUNNING"


class WaydroidController:
    """Manages Waydroid container service, graphics session, resolutions, and spoofing."""

    def __init__(
        self,
        runner: Optional[CommandRunner] = None,
        backup_path: Optional[Path | str] = None,
    ) -> None:
        self.runner: CommandRunner = runner if runner is not None else SystemCommandRunner()
        self.backup_path: Path = (
            Path(backup_path) if backup_path else Path.home() / ".config" / "wayfire" / "device_backup.json"
        )

    def get_status(self) -> WaydroidStatus:
        """Parse status output of `waydroid status`."""
        res = self.runner.run(["waydroid", "status"])
        session = "STOPPED"
        container = "STOPPED"

        session_match = re.search(r"Session:\s*([A-Za-z]+)", res.stdout)
        if session_match:
            session = session_match.group(1).upper()

        container_match = re.search(r"Container:\s*([A-Za-z]+)", res.stdout)
        if container_match:
            container = container_match.group(1).upper()

        return WaydroidStatus(session=session, container=container)

    def is_container_active(self) -> bool:
        """Check if waydroid-container service is running via systemctl or status fallback."""
        try:
            res = self.runner.run(["systemctl", "is-active", "waydroid-container.service"])
            if res.returncode == 0 and "active" in res.stdout.strip():
                return True
        except (subprocess.SubprocessError, OSError):
            pass

        # Fallback to status parsing
        return self.get_status().container == "RUNNING"

    def ensure_container_active(self) -> bool:
        """Ensure waydroid-container.service is active; attempt start if necessary."""
        if self.is_container_active():
            return True

        # Attempt starting via systemctl or pkexec
        res = self.runner.run(["systemctl", "start", "waydroid-container.service"])
        if res.returncode == 0 and self.is_container_active():
            return True

        res_pk = self.runner.run(["pkexec", "systemctl", "start", "waydroid-container.service"])
        if res_pk.returncode == 0 and self.is_container_active():
            return True

        raise RuntimeError(
            "O serviço do contêiner Waydroid está parado. Inicie-o manualmente com: "
            "sudo systemctl start waydroid-container.service"
        )

    def start_session(self, timeout: float = 30.0, poll_interval: float = 0.5) -> bool:
        """Start Waydroid graphical session asynchronously and poll until RUNNING."""
        if self.get_status().session == "RUNNING":
            return True

        self.runner.popen(["waydroid", "session", "start"])

        start_time = time.monotonic()
        while time.monotonic() - start_time < timeout:
            time.sleep(poll_interval)
            if self.get_status().session == "RUNNING":
                return True

        raise TimeoutError(f"Tempo limite ({timeout}s) atingido aguardando inicialização da sessão Waydroid.")

    def stop_session(self, wait_stopped: bool = True, timeout: float = 10.0) -> bool:
        """Stop Waydroid graphical session."""
        self.runner.run(["waydroid", "session", "stop"])
        if not wait_stopped:
            return True

        start_time = time.monotonic()
        while time.monotonic() - start_time < timeout:
            if self.get_status().session == "STOPPED":
                return True
            time.sleep(0.2)
        return False

    def restart_session(self, timeout: float = 30.0) -> bool:
        """Restart Waydroid graphics session, waiting for full cycle."""
        self.stop_session(wait_stopped=True)
        return self.start_session(timeout=timeout)

    def detect_freefire_package(self, preferred_package: Optional[str] = None) -> str:
        """Detect installed Free Fire package (Standard or MAX) or return preferred/fallback."""
        if preferred_package and preferred_package.strip():
            candidate = preferred_package.strip()
            if not PACKAGE_REGEX.match(candidate):
                raise ValueError(f"Nome de pacote inválido: {candidate}")
            return candidate

        res = self.runner.run(["waydroid", "app", "list"])
        if "com.dts.freefiremax" in res.stdout:
            return "com.dts.freefiremax"
        if "com.dts.freefireth" in res.stdout:
            return "com.dts.freefireth"

        return "com.dts.freefireth"

    def launch_app(self, package: Optional[str] = None) -> bool:
        """Launch specified Android application package in Waydroid."""
        pkg = self.detect_freefire_package(package)
        if not PACKAGE_REGEX.match(pkg):
            raise ValueError(f"Nome de pacote inválido: {pkg}")
        res = self.runner.run(["waydroid", "app", "launch", pkg])
        return res.returncode == 0

    def stop_app(self, package: Optional[str] = None, full: bool = False) -> bool:
        """Gracefully stop Android application via am force-stop, optionally stopping session."""
        pkg = self.detect_freefire_package(package)
        if not PACKAGE_REGEX.match(pkg):
            raise ValueError(f"Nome de pacote inválido: {pkg}")
        res = self.runner.run(["waydroid", "shell", "am", "force-stop", pkg])
        if full:
            self.stop_session()
        return res.returncode == 0

    def get_current_resolution(self) -> tuple[int, int]:
        """Read persist.waydroid.width and persist.waydroid.height properties."""
        res_w = self.runner.run(["waydroid", "prop", "get", "persist.waydroid.width"])
        res_h = self.runner.run(["waydroid", "prop", "get", "persist.waydroid.height"])

        try:
            w = int(res_w.stdout.strip())
            h = int(res_h.stdout.strip())
            if w > 0 and h > 0:
                return (w, h)
        except ValueError:
            pass

        return (1920, 1080)

    def set_resolution(self, width: int, height: int, restart_if_running: bool = True) -> bool:
        """Set persist.waydroid resolution idempotently, restarting session if requested."""
        width = int(width)
        height = int(height)
        curr_w, curr_h = self.get_current_resolution()

        if curr_w == width and curr_h == height:
            return False

        self.runner.run(["waydroid", "prop", "set", "persist.waydroid.width", str(width)])
        self.runner.run(["waydroid", "prop", "set", "persist.waydroid.height", str(height)])

        if restart_if_running and self.get_status().session == "RUNNING":
            self.restart_session()

        return True

    def is_spoofing_applied(self) -> bool:
        """Check if ro.product.model is set to ASUS_I005D."""
        res = self.runner.run(["waydroid", "prop", "get", "ro.product.model"])
        return res.stdout.strip() == "ASUS_I005D"

    def apply_spoofing(self) -> bool:
        """Backup original properties if not present and apply ASUS ROG Phone 5 spoofing."""
        if self.is_spoofing_applied():
            return True

        if not self.backup_path.exists():
            backup_dict: dict[str, str] = {}
            for prop in ROG_PHONE_PROPS:
                val = self.runner.run(["waydroid", "prop", "get", prop]).stdout.strip()
                backup_dict[prop] = val

            self.backup_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.backup_path, "w", encoding="utf-8") as f:
                json.dump(backup_dict, f, indent=2)

        for prop, val in ROG_PHONE_PROPS.items():
            self.runner.run(["waydroid", "prop", "set", prop, val])

        return True

    def restore_spoofing(self) -> bool:
        """Restore original container properties from backup file."""
        if not self.backup_path.exists():
            raise FileNotFoundError(f"Arquivo de backup não encontrado em {self.backup_path}")

        with open(self.backup_path, "r", encoding="utf-8") as f:
            props = json.load(f)

        for prop, val in props.items():
            self.runner.run(["waydroid", "prop", "set", prop, str(val)])

        return True
