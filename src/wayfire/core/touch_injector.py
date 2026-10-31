"""Kernel-level virtual multitouch screen injector using Linux /dev/uinput."""

from __future__ import annotations

import time
from typing import Optional, Protocol, runtime_checkable
from evdev import AbsInfo, UInput, ecodes


@runtime_checkable
class UInputSink(Protocol):
    """Protocol abstraction for UInput device sink to allow hermetic testing."""

    def write(self, etype: int, code: int, value: int) -> None:
        """Write an input event."""
        ...

    def syn(self) -> None:
        """Synchronize input events."""
        ...

    def close(self) -> None:
        """Close the underlying device."""
        ...


class MockUInputSink(UInputSink):
    """Hermetic mock sink for unit testing without kernel uinput access."""

    def __init__(self) -> None:
        self.recorded_events: list[tuple[int, int, int]] = []
        self.syn_count: int = 0
        self.is_closed: bool = False

    def write(self, etype: int, code: int, value: int) -> None:
        self.recorded_events.append((etype, code, value))

    def syn(self) -> None:
        self.syn_count += 1

    def close(self) -> None:
        self.is_closed = True


class TouchInjector:
    """Virtual touchscreen injector using Linux Kernel uinput with Multi-Touch Type B."""

    CAMERA_SLOT: int = 0
    MAX_SLOTS: int = 10
    DYNAMIC_SLOT_RANGE: range = range(1, 10)

    def __init__(
        self,
        sink: Optional[UInputSink] = None,
        width: int = 1920,
        height: int = 1080,
    ) -> None:
        self.width = width
        self.height = height
        self.sink: UInputSink = sink if sink is not None else self._create_real_uinput(width, height)
        self.active_slots: set[int] = set()
        self._next_tracking_id: int = 1

    def _create_real_uinput(self, width: int, height: int) -> UInput:
        """Instantiate real Linux /dev/uinput device with direct touchscreen props."""
        capabilities = {
            ecodes.EV_KEY: [ecodes.BTN_TOUCH],
            ecodes.EV_ABS: [
                (ecodes.ABS_X, AbsInfo(value=0, min=0, max=width, fuzz=0, flat=0, resolution=0)),
                (ecodes.ABS_Y, AbsInfo(value=0, min=0, max=height, fuzz=0, flat=0, resolution=0)),
                (ecodes.ABS_MT_SLOT, AbsInfo(value=0, min=0, max=self.MAX_SLOTS - 1, fuzz=0, flat=0, resolution=0)),
                (ecodes.ABS_MT_TRACKING_ID, AbsInfo(value=0, min=0, max=65535, fuzz=0, flat=0, resolution=0)),
                (ecodes.ABS_MT_POSITION_X, AbsInfo(value=0, min=0, max=width, fuzz=0, flat=0, resolution=0)),
                (ecodes.ABS_MT_POSITION_Y, AbsInfo(value=0, min=0, max=height, fuzz=0, flat=0, resolution=0)),
            ],
        }

        try:
            return UInput(
                events=capabilities,
                name="WayFire Virtual Touchscreen",
                input_props=[ecodes.INPUT_PROP_DIRECT],
            )
        except (PermissionError, OSError) as exc:
            raise PermissionError(
                "Unable to open /dev/uinput. Ensure your user belongs to the 'input' group "
                "or appropriate udev rules are installed."
            ) from exc

    def set_screen_dimensions(self, width: int, height: int) -> None:
        """Dynamically update screen boundary limits for touch clamping."""
        self.width = max(1, int(width))
        self.height = max(1, int(height))

    def _get_next_tracking_id(self) -> int:
        """Atomically generate and recycle tracking ID between 1 and 65535."""
        tid = self._next_tracking_id
        self._next_tracking_id += 1
        if self._next_tracking_id > 65535:
            self._next_tracking_id = 1
        return tid

    def _clamp_coords(self, x: int, y: int) -> tuple[int, int]:
        """Clamp coordinates to screen boundary [0, width] and [0, height]."""
        cx = max(0, min(self.width, int(x)))
        cy = max(0, min(self.height, int(y)))
        return cx, cy

    def touch_down(self, slot: int, x: int, y: int) -> None:
        """Emit touch down event on specified slot with new tracking ID."""
        cx, cy = self._clamp_coords(x, y)
        self.active_slots.add(slot)
        tid = self._get_next_tracking_id()

        self.sink.write(ecodes.EV_ABS, ecodes.ABS_MT_SLOT, slot)
        self.sink.write(ecodes.EV_ABS, ecodes.ABS_MT_TRACKING_ID, tid)
        self.sink.write(ecodes.EV_ABS, ecodes.ABS_MT_POSITION_X, cx)
        self.sink.write(ecodes.EV_ABS, ecodes.ABS_MT_POSITION_Y, cy)
        self.sink.write(ecodes.EV_KEY, ecodes.BTN_TOUCH, 1)
        self.sink.syn()

    def touch_move(self, slot: int, x: int, y: int) -> None:
        """Emit touch move event on an active slot."""
        if slot not in self.active_slots:
            return
        cx, cy = self._clamp_coords(x, y)

        self.sink.write(ecodes.EV_ABS, ecodes.ABS_MT_SLOT, slot)
        self.sink.write(ecodes.EV_ABS, ecodes.ABS_MT_POSITION_X, cx)
        self.sink.write(ecodes.EV_ABS, ecodes.ABS_MT_POSITION_Y, cy)
        self.sink.syn()

    def touch_up(self, slot: int) -> None:
        """Emit touch up event on slot and lift BTN_TOUCH when all slots are released."""
        if slot in self.active_slots:
            self.active_slots.remove(slot)

        self.sink.write(ecodes.EV_ABS, ecodes.ABS_MT_SLOT, slot)
        self.sink.write(ecodes.EV_ABS, ecodes.ABS_MT_TRACKING_ID, -1)

        btn_touch_value = 1 if len(self.active_slots) > 0 else 0
        self.sink.write(ecodes.EV_KEY, ecodes.BTN_TOUCH, btn_touch_value)
        self.sink.syn()

    def allocate_slot(self) -> int:
        """Allocate the lowest available dynamic multitouch slot (1-9)."""
        for slot in self.DYNAMIC_SLOT_RANGE:
            if slot not in self.active_slots:
                return slot
        raise RuntimeError("No free multitouch slots available (1-9)")

    def release_slot(self, slot: int) -> None:
        """Release an allocated dynamic slot."""
        if slot in self.active_slots:
            self.touch_up(slot)

    def reset_slot_cycle(
        self,
        slot: int,
        anchor_x: int,
        anchor_y: int,
        pause_sec: float = 0.001,
    ) -> None:
        """Execute atomic 1ms reset cycle: UP -> sleep 1ms -> DOWN at anchor."""
        self.touch_up(slot)
        if pause_sec > 0:
            time.sleep(pause_sec)
        self.touch_down(slot, anchor_x, anchor_y)

    def close(self) -> None:
        """Cleanly close the sink device."""
        self.sink.close()

    def __enter__(self) -> TouchInjector:
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        for slot in list(self.active_slots):
            self.touch_up(slot)
        self.close()
