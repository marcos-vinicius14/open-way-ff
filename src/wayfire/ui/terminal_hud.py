"""Real-time ANSI VT100 interactive Terminal HUD for WayFire."""

from __future__ import annotations

import sys
import time
from typing import TextIO


class TerminalHUD:
    """Renders in-place terminal status and telemetry with minimal overhead."""

    def __init__(self, stream: TextIO = sys.stdout, min_interval_sec: float = 0.016) -> None:
        self.stream = stream
        self.min_interval_sec = min_interval_sec
        self._last_render_time: float = 0.0

    @staticmethod
    def format_line(
        is_locked: bool,
        sens_x: float,
        sens_y: float,
        dx: int = 0,
        dy: int = 0,
        reset_count: int = 0,
    ) -> str:
        """Format single-line ANSI string representing current engine state."""
        if is_locked:
            return (
                f"\r\033[K[🟢 AIM LOCKED]  Sens X: {sens_x:.2f}  Sens Y: {sens_y:.2f}  "
                f"Mouse: [dx: {dx:+03d}, dy: {dy:+03d}]  Resets: {reset_count:d}  "
                f"(F1: Suspender | F7/F8: Sens X | F9/F10: Sens Y)"
            )
        return (
            f"\r\033[K[🟡 SUSPENDED]   Sens X: {sens_x:.2f}  Sens Y: {sens_y:.2f}  "
            f"(Pressione F1 para travar a mira e jogar)"
        )

    def render(
        self,
        is_locked: bool,
        sens_x: float,
        sens_y: float,
        dx: int = 0,
        dy: int = 0,
        reset_count: int = 0,
        force: bool = False,
    ) -> None:
        """Render status to terminal stream, throttled to 60 FPS unless forced."""
        now = time.perf_counter()
        if not force and (now - self._last_render_time) < self.min_interval_sec:
            return

        line = self.format_line(is_locked, sens_x, sens_y, dx, dy, reset_count)
        self.stream.write(line)
        self.stream.flush()
        self._last_render_time = now
