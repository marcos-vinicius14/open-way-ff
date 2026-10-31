"""Aim mathematical engine with independent X/Y sensitivity, EMA smoothing, and subpixel accumulator."""

from __future__ import annotations

import math
from typing import Optional


class AimProcessor:
    """Mathematical processor converting raw mouse deltas to scaled, smoothed aim movements."""

    def __init__(
        self,
        sens_x: float = 1.45,
        sens_y: float = 3.20,
        smoothing: bool = True,
        alpha: float = 0.80,
        invert_y: bool = False,
    ) -> None:
        self.sens_x: float = max(0.05, float(sens_x))
        self.sens_y: float = max(0.05, float(sens_y))
        self.smoothing: bool = smoothing
        self.alpha: float = max(0.01, min(1.0, float(alpha)))
        self.invert_y: bool = invert_y

        self.prev_dx: float = 0.0
        self.prev_dy: float = 0.0
        self.acc_x: float = 0.0
        self.acc_y: float = 0.0

    def process_delta(self, raw_dx: int, raw_dy: int) -> tuple[int, int]:
        """Process raw mouse movement deltas into integer aim steps.

        Applies:
        1. Vertical axis inversion (if enabled)
        2. Exponential Moving Average (EMA) smoothing for high-DPI jitter reduction
        3. Independent horizontal and vertical sensitivity scaling (Sens_X, Sens_Y)
        4. Fractional subpixel accumulation to prevent pixel-skipping on micro-aim
        """
        # 1. Invert Y if configured
        dy_in = -raw_dy if self.invert_y else raw_dy

        # 2. EMA smoothing filter
        if self.smoothing:
            filtered_dx = self.alpha * float(raw_dx) + (1.0 - self.alpha) * self.prev_dx
            filtered_dy = self.alpha * float(dy_in) + (1.0 - self.alpha) * self.prev_dy
            self.prev_dx = filtered_dx
            self.prev_dy = filtered_dy
        else:
            filtered_dx = float(raw_dx)
            filtered_dy = float(dy_in)

        # 3. Independent sensitivity scaling
        scaled_dx = filtered_dx * self.sens_x
        scaled_dy = filtered_dy * self.sens_y

        # 4. Subpixel fractional accumulator
        self.acc_x += scaled_dx
        self.acc_y += scaled_dy

        # 5. Extract integer steps (truncating toward zero)
        step_x = math.trunc(self.acc_x)
        step_y = math.trunc(self.acc_y)

        # 6. Preserve remainder in subpixel accumulator
        self.acc_x -= step_x
        self.acc_y -= step_y

        return step_x, step_y

    def set_sensitivity(
        self,
        sens_x: Optional[float] = None,
        sens_y: Optional[float] = None,
    ) -> None:
        """Dynamically update sensitivity multipliers with a lower safety bound of 0.05."""
        if sens_x is not None:
            self.sens_x = max(0.05, float(sens_x))
        if sens_y is not None:
            self.sens_y = max(0.05, float(sens_y))

    def reset_state(self) -> None:
        """Reset internal accumulator and smoothing history."""
        self.prev_dx = 0.0
        self.prev_dy = 0.0
        self.acc_x = 0.0
        self.acc_y = 0.0
