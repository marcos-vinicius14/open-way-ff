"""Non-blocking macro scheduler for sequential multi-touch actions.

Enqueues ordered touch steps with monotonic timestamps and dispatches via TouchInjector
without blocking the input polling thread with time.sleep (D-16, MAP-02).
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from wayfire.config.widgets import MacroWidget
    from wayfire.core.touch_injector import TouchInjector


class NonBlockingMacroScheduler:
    """Schedules and executes sequential macro touches without thread blocking."""

    def __init__(
        self,
        injector: TouchInjector,
        slot_start: int = 4,
        slot_end: int = 9,
    ) -> None:
        self.injector = injector
        self.available_slots: list[int] = list(range(slot_start, slot_end + 1))
        # Items: (fire_at_timestamp, action, slot, x, y)
        self.queue: list[tuple[float, str, int, int, int]] = []

    def trigger_macro(self, macro: MacroWidget) -> Optional[int]:
        """Enqueue all steps of a sequential macro using an allocated uinput slot."""
        if not self.available_slots or not macro.steps:
            return None

        slot = self.available_slots.pop(0)
        now = time.monotonic()
        accumulated_delay = 0.0

        for step in macro.steps:
            touch_down_time = now + accumulated_delay
            touch_up_time = touch_down_time + 0.015  # 15ms pulse

            self.queue.append((touch_down_time, "down", slot, int(step.x), int(step.y)))
            self.queue.append((touch_up_time, "up", slot, int(step.x), int(step.y)))

            step_delay = (step.delay_ms or macro.delay_ms or 30) / 1000.0
            accumulated_delay += step_delay

        # Schedule recycling of the uinput slot after last pulse completes
        self.queue.append((now + accumulated_delay + 0.010, "release_slot", slot, 0, 0))
        self.queue.sort(key=lambda item: item[0])
        return slot

    def process_scheduled(self) -> int:
        """Process any touch actions whose scheduled timestamps have elapsed.

        Returns the number of actions executed during this tick.
        """
        now = time.monotonic()
        ready: list[tuple[float, str, int, int, int]] = []
        pending: list[tuple[float, str, int, int, int]] = []

        for item in self.queue:
            if item[0] <= now:
                ready.append(item)
            else:
                pending.append(item)

        self.queue = pending

        for _fire_at, action, slot, x, y in ready:
            if action == "down":
                self.injector.touch_down(slot, x, y)
            elif action == "up":
                self.injector.touch_up(slot)
            elif action == "release_slot":
                if slot not in self.available_slots:
                    self.available_slots.append(slot)

        return len(ready)

    @property
    def has_pending_actions(self) -> bool:
        return len(self.queue) > 0
