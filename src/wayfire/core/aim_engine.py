from __future__ import annotations

import math
from typing import TYPE_CHECKING, Optional

from evdev import ecodes

if TYPE_CHECKING:
    from wayfire.core.touch_injector import TouchInjector


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


class AimEngine:
    """Coordinates aim positioning, 360° anti-border 1ms reset cycles, and fire button injection."""

    def __init__(
        self,
        processor: AimProcessor,
        screen_width: int = 1920,
        screen_height: int = 1080,
        anchor_norm_x: float = 0.65,
        anchor_norm_y: float = 0.50,
        radius_norm: float = 0.20,
        fire_button_norm: tuple[float, float] = (0.80, 0.75),
        threshold_ratio: float = 0.75,
    ) -> None:
        self.processor = processor
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.anchor_norm_x = anchor_norm_x
        self.anchor_norm_y = anchor_norm_y
        self.radius_norm = radius_norm
        self.fire_button_norm = fire_button_norm
        self.threshold_ratio = threshold_ratio

        self.anchor_px = (
            int(self.anchor_norm_x * self.screen_width),
            int(self.anchor_norm_y * self.screen_height),
        )
        self.radius_px = int(self.radius_norm * min(self.screen_width, self.screen_height))
        self.max_dist_sq = (self.radius_px * self.threshold_ratio) ** 2

        self.current_x: int = self.anchor_px[0]
        self.current_y: int = self.anchor_px[1]
        self.reset_count: int = 0
        self.is_aim_active: bool = False
        self.fire_slot: int = 1

    def set_screen_dimensions(self, width: int, height: int) -> None:
        """Dynamically update active screen resolution and recalculate pixel anchor/radius."""
        self.screen_width = max(1, int(width))
        self.screen_height = max(1, int(height))
        self.anchor_px = (
            int(self.anchor_norm_x * self.screen_width),
            int(self.anchor_norm_y * self.screen_height),
        )
        self.radius_px = int(self.radius_norm * min(self.screen_width, self.screen_height))
        self.max_dist_sq = (self.radius_px * self.threshold_ratio) ** 2
        self.current_x = self.anchor_px[0]
        self.current_y = self.anchor_px[1]

    def start_aim(self, injector: TouchInjector) -> None:
        """Initiate aim tracking by placing touch on Slot 0 at anchor position."""
        if not self.is_aim_active:
            injector.touch_down(slot=0, x=self.anchor_px[0], y=self.anchor_px[1])
            self.current_x = self.anchor_px[0]
            self.current_y = self.anchor_px[1]
            self.is_aim_active = True

    def stop_aim(self, injector: TouchInjector) -> None:
        """Stop aim tracking, releasing Slot 0 and resetting smoothing/subpixel residue."""
        if self.is_aim_active:
            injector.touch_up(slot=0)
            self.processor.reset_state()
            self.is_aim_active = False

    def update_aim(
        self,
        raw_dx: int,
        raw_dy: int,
        injector: TouchInjector,
    ) -> tuple[int, int, bool]:
        """Update aim location with delta, executing 1ms invisible reset when crossing 75% boundary.

        Returns (current_x, current_y, reset_occurred).
        """
        if not self.is_aim_active:
            self.start_aim(injector)

        step_x, step_y = self.processor.process_delta(raw_dx, raw_dy)
        if step_x == 0 and step_y == 0:
            return self.current_x, self.current_y, False

        cand_x = self.current_x + step_x
        cand_y = self.current_y + step_y

        dist_sq = (cand_x - self.anchor_px[0]) ** 2 + (cand_y - self.anchor_px[1]) ** 2

        if dist_sq >= self.max_dist_sq:
            # 75% boundary reached -> execute atomic 1ms reset cycle per D-05 and D-06
            injector.reset_slot_cycle(
                slot=0,
                anchor_x=self.anchor_px[0],
                anchor_y=self.anchor_px[1],
                pause_sec=0.001,
            )
            self.reset_count += 1
            self.current_x = self.anchor_px[0]
            self.current_y = self.anchor_px[1]
            self.processor.reset_state()
            return self.current_x, self.current_y, True

        injector.touch_move(slot=0, x=cand_x, y=cand_y)
        self.current_x = cand_x
        self.current_y = cand_y
        return self.current_x, self.current_y, False

    def handle_mouse_button(
        self,
        code: int,
        value: int,
        injector: TouchInjector,
    ) -> None:
        """Handle mouse clicks, mapping left-click (BTN_LEFT) to fire button on Slot 1."""
        if code == ecodes.BTN_LEFT:
            if value == 1:
                fire_x = int(self.fire_button_norm[0] * self.screen_width)
                fire_y = int(self.fire_button_norm[1] * self.screen_height)
                injector.touch_down(slot=self.fire_slot, x=fire_x, y=fire_y)
            elif value == 0:
                injector.touch_up(slot=self.fire_slot)

