"""Unit tests for TouchInjector and Multi-Touch Type B virtual input."""

import time
import pytest
from evdev import ecodes
from wayfire.core.touch_injector import MockUInputSink, TouchInjector


def test_tracer_touch_injection_lifecycle(mock_sink: MockUInputSink) -> None:
    """Tracer test: end-to-end multitouch injection lifecycle on virtual device."""
    injector = TouchInjector(sink=mock_sink, width=1920, height=1080)

    # 1. Touch Down
    injector.touch_down(slot=0, x=960, y=540)
    assert mock_sink.syn_count == 1
    events = list(mock_sink.recorded_events)

    assert (ecodes.EV_ABS, ecodes.ABS_MT_SLOT, 0) in events
    assert (ecodes.EV_ABS, ecodes.ABS_MT_POSITION_X, 960) in events
    assert (ecodes.EV_ABS, ecodes.ABS_MT_POSITION_Y, 540) in events
    assert (ecodes.EV_KEY, ecodes.BTN_TOUCH, 1) in events

    # Check positive tracking id
    tid_events = [val for (et, code, val) in events if et == ecodes.EV_ABS and code == ecodes.ABS_MT_TRACKING_ID]
    assert len(tid_events) == 1
    first_tid = tid_events[0]
    assert first_tid > 0

    # 2. Touch Move
    mock_sink.recorded_events.clear()
    injector.touch_move(slot=0, x=980, y=560)
    assert mock_sink.syn_count == 2
    events_move = list(mock_sink.recorded_events)
    assert (ecodes.EV_ABS, ecodes.ABS_MT_SLOT, 0) in events_move
    assert (ecodes.EV_ABS, ecodes.ABS_MT_POSITION_X, 980) in events_move
    assert (ecodes.EV_ABS, ecodes.ABS_MT_POSITION_Y, 560) in events_move

    # 3. Touch Up
    mock_sink.recorded_events.clear()
    injector.touch_up(slot=0)
    assert mock_sink.syn_count == 3
    events_up = list(mock_sink.recorded_events)
    assert (ecodes.EV_ABS, ecodes.ABS_MT_SLOT, 0) in events_up
    assert (ecodes.EV_ABS, ecodes.ABS_MT_TRACKING_ID, -1) in events_up
    assert (ecodes.EV_KEY, ecodes.BTN_TOUCH, 0) in events_up


def test_multislot_concurrent_touches(mock_sink: MockUInputSink) -> None:
    """Verify concurrent multi-slot touch tracking and global BTN_TOUCH coordination."""
    injector = TouchInjector(sink=mock_sink, width=1920, height=1080)

    # Touch down on Slot 0 (Aim) and Slot 1 (Fire)
    injector.touch_down(slot=0, x=960, y=540)
    injector.touch_down(slot=1, x=1500, y=800)

    assert injector.active_slots == {0, 1}

    # Release Slot 0 (Aim) while Slot 1 (Fire) is still active
    mock_sink.recorded_events.clear()
    injector.touch_up(slot=0)
    assert (ecodes.EV_KEY, ecodes.BTN_TOUCH, 1) in mock_sink.recorded_events
    assert injector.active_slots == {1}

    # Release Slot 1: now BTN_TOUCH must transition to 0
    mock_sink.recorded_events.clear()
    injector.touch_up(slot=1)
    assert (ecodes.EV_KEY, ecodes.BTN_TOUCH, 0) in mock_sink.recorded_events
    assert len(injector.active_slots) == 0


def test_slot_reservation_and_allocation(mock_sink: MockUInputSink) -> None:
    """Verify that Slot 0 is strictly reserved and dynamic slots 1..9 allocate correctly."""
    injector = TouchInjector(sink=mock_sink)

    allocated = []
    for _ in range(9):
        slot = injector.allocate_slot()
        assert slot != TouchInjector.CAMERA_SLOT
        assert 1 <= slot <= 9
        injector.touch_down(slot, 100, 100)
        allocated.append(slot)

    assert set(allocated) == set(range(1, 10))

    # All dynamic slots 1-9 are occupied; next allocate must fail
    with pytest.raises(RuntimeError, match="No free multitouch slots available"):
        injector.allocate_slot()

    # Releasing slot 4 should allow re-allocating slot 4
    injector.release_slot(4)
    reallocated = injector.allocate_slot()
    assert reallocated == 4


def test_reset_slot_cycle_timing_and_events(mock_sink: MockUInputSink) -> None:
    """Verify 1ms atomic reset cycle: UP -> sleep 1ms -> DOWN at anchor."""
    injector = TouchInjector(sink=mock_sink)
    injector.touch_down(slot=0, x=1800, y=900)

    mock_sink.recorded_events.clear()
    start_t = time.perf_counter()
    injector.reset_slot_cycle(slot=0, anchor_x=960, anchor_y=540, pause_sec=0.001)
    duration = time.perf_counter() - start_t

    # Must have taken at least 1ms (accounting for scheduler precision)
    assert duration >= 0.0008

    events = mock_sink.recorded_events
    # Check that UP was emitted first
    up_idx = events.index((ecodes.EV_ABS, ecodes.ABS_MT_TRACKING_ID, -1))
    assert up_idx != -1

    # Check that DOWN was emitted after with anchor coordinates
    down_x_idx = events.index((ecodes.EV_ABS, ecodes.ABS_MT_POSITION_X, 960))
    down_y_idx = events.index((ecodes.EV_ABS, ecodes.ABS_MT_POSITION_Y, 540))
    assert down_x_idx > up_idx
    assert down_y_idx > up_idx


def test_coordinate_clamping(mock_sink: MockUInputSink) -> None:
    """Coordinates outside [0, width] and [0, height] must be clamped."""
    injector = TouchInjector(sink=mock_sink, width=1920, height=1080)

    injector.touch_down(slot=0, x=-50, y=2500)
    events = mock_sink.recorded_events
    assert (ecodes.EV_ABS, ecodes.ABS_MT_POSITION_X, 0) in events
    assert (ecodes.EV_ABS, ecodes.ABS_MT_POSITION_Y, 1080) in events

    mock_sink.recorded_events.clear()
    injector.touch_move(slot=0, x=3000, y=-100)
    events_move = mock_sink.recorded_events
    assert (ecodes.EV_ABS, ecodes.ABS_MT_POSITION_X, 1920) in events_move
    assert (ecodes.EV_ABS, ecodes.ABS_MT_POSITION_Y, 0) in events_move


def test_context_manager_cleanup(mock_sink: MockUInputSink) -> None:
    """Context manager must release all active touches and close device."""
    with TouchInjector(sink=mock_sink) as injector:
        injector.touch_down(slot=0, x=500, y=500)
        injector.touch_down(slot=2, x=700, y=700)
        assert len(injector.active_slots) == 2

    assert len(injector.active_slots) == 0
    assert mock_sink.is_closed is True
