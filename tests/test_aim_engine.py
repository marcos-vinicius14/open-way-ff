"""Unit tests for AimProcessor sensitivity engine, subpixel accumulation, and EMA smoothing."""

from evdev import ecodes
from wayfire.core.aim_engine import AimEngine, AimProcessor
from wayfire.core.touch_injector import MockUInputSink, TouchInjector


def test_sensitivity_scaling_independent() -> None:
    """Verify that X and Y axes scale independently according to Sens_X and Sens_Y."""
    processor = AimProcessor(sens_x=1.0, sens_y=2.5, smoothing=False)

    step_x, step_y = processor.process_delta(raw_dx=10, raw_dy=10)
    assert step_x == 10
    assert step_y == 25
    assert step_y > step_x  # Asymmetric sensitivity for Free Fire "puxada de capa"


def test_subpixel_accumulation_preserves_micro_movements() -> None:
    """Micro-movements below 1 full pixel must be preserved without truncation loss."""
    processor = AimProcessor(sens_x=0.35, sens_y=0.35, smoothing=False)

    outputs_x = []
    for _ in range(10):
        sx, _ = processor.process_delta(raw_dx=1, raw_dy=0)
        outputs_x.append(sx)

    # Frame 1: 0.35 -> 0 (rem 0.35)
    # Frame 2: 0.70 -> 0 (rem 0.70)
    # Frame 3: 1.05 -> 1 (rem 0.05)
    assert outputs_x[0] == 0
    assert outputs_x[1] == 0
    assert outputs_x[2] == 1
    # Over 10 frames of 0.35: total delta = 3.5 -> 3 steps total
    assert sum(outputs_x) == 3


def test_ema_smoothing_attenuates_jitter() -> None:
    """EMA smoothing attenuates high-frequency alternating jitter spikes."""
    proc_raw = AimProcessor(sens_x=1.0, sens_y=1.0, smoothing=False)
    proc_smooth = AimProcessor(sens_x=1.0, sens_y=1.0, smoothing=True, alpha=0.5)

    raw_outputs = []
    smooth_outputs = []

    # Send sharp spike: 0 -> 20 -> 0 -> 20
    test_inputs = [0, 20, 0, 20, 0]
    for inp in test_inputs:
        rx, _ = proc_raw.process_delta(raw_dx=inp, raw_dy=0)
        sx, _ = proc_smooth.process_delta(raw_dx=inp, raw_dy=0)
        raw_outputs.append(rx)
        smooth_outputs.append(sx)

    # Peak of smoothed output must be smaller than raw peak (20)
    assert max(raw_outputs) == 20
    assert max(smooth_outputs) < 20


def test_invert_y_toggle() -> None:
    """Invert Y flag toggles vertical delta orientation."""
    proc_normal = AimProcessor(sens_x=1.0, sens_y=1.0, smoothing=False, invert_y=False)
    proc_inverted = AimProcessor(sens_x=1.0, sens_y=1.0, smoothing=False, invert_y=True)

    _, y_norm = proc_normal.process_delta(raw_dx=0, raw_dy=15)
    _, y_inv = proc_inverted.process_delta(raw_dx=0, raw_dy=15)

    assert y_norm == 15
    assert y_inv == -15


def test_reset_state_clears_residue() -> None:
    """reset_state clears all fractional subpixel residue and filter history."""
    processor = AimProcessor(sens_x=0.4, sens_y=0.4, smoothing=False)
    processor.process_delta(raw_dx=1, raw_dy=1)

    assert processor.acc_x > 0.0
    assert processor.acc_y > 0.0

    processor.reset_state()
    assert processor.acc_x == 0.0
    assert processor.acc_y == 0.0
    assert processor.prev_dx == 0.0
    assert processor.prev_dy == 0.0


def test_anti_border_trigger_at_75_percent() -> None:
    """Verify that moving past 75% boundary triggers atomic 1ms reset cycle back to anchor."""
    sink = MockUInputSink()
    injector = TouchInjector(sink=sink, width=1920, height=1080)
    processor = AimProcessor(sens_x=1.0, sens_y=1.0, smoothing=False)
    engine = AimEngine(
        processor=processor,
        screen_width=1920,
        screen_height=1080,
        anchor_norm_x=0.5,
        anchor_norm_y=0.5,
        radius_norm=0.2,
        threshold_ratio=0.75,
    )
    # anchor is (960, 540)
    # radius_px is 0.2 * 1080 = 216
    # threshold 75% is 216 * 0.75 = 162 pixels
    engine.start_aim(injector)
    assert engine.current_x == 960
    assert engine.current_y == 540
    assert engine.reset_count == 0

    # Move 100px right (within 162px limit) -> no reset
    cur_x, cur_y, reset = engine.update_aim(raw_dx=100, raw_dy=0, injector=injector)
    assert cur_x == 1060
    assert cur_y == 540
    assert reset is False
    assert engine.reset_count == 0

    # Move another 70px right (total 170px > 162px threshold) -> triggers reset!
    cur_x, cur_y, reset = engine.update_aim(raw_dx=70, raw_dy=0, injector=injector)
    assert reset is True
    assert engine.reset_count == 1
    # Coordinates must be snapped back to anchor
    assert cur_x == 960
    assert cur_y == 540
    assert engine.current_x == 960
    assert engine.current_y == 540


def test_continuous_360_rotation_infinite() -> None:
    """Simulate rapid continuous one-directional mouse movement over 150 cycles without locking."""
    sink = MockUInputSink()
    injector = TouchInjector(sink=sink, width=1920, height=1080)
    processor = AimProcessor(sens_x=1.0, sens_y=1.0, smoothing=False)
    engine = AimEngine(processor=processor)

    engine.start_aim(injector)

    # Move right continuously 150 times with dx=50
    for _ in range(150):
        engine.update_aim(raw_dx=50, raw_dy=0, injector=injector)

    # Must have triggered multiple anti-border resets
    assert engine.reset_count > 10
    # Must remain active and at/near anchor or within safe radius
    dist_sq = (engine.current_x - engine.anchor_px[0]) ** 2 + (engine.current_y - engine.anchor_px[1]) ** 2
    assert dist_sq <= engine.max_dist_sq


def test_fire_button_slot_1_concurrency() -> None:
    """Verify left click triggers Slot 1 fire button touch down and up while Slot 0 aim is active."""
    sink = MockUInputSink()
    injector = TouchInjector(sink=sink, width=1920, height=1080)
    processor = AimProcessor(sens_x=1.0, sens_y=1.0, smoothing=False)
    engine = AimEngine(processor=processor, screen_width=1920, screen_height=1080)

    # Start aim on Slot 0
    engine.start_aim(injector)
    assert 0 in injector.active_slots

    # Press left click (BTN_LEFT = 1) -> Fire on Slot 1
    sink.recorded_events.clear()
    engine.handle_mouse_button(code=ecodes.BTN_LEFT, value=1, injector=injector)
    assert 1 in injector.active_slots
    assert (ecodes.EV_ABS, ecodes.ABS_MT_SLOT, 1) in sink.recorded_events
    fire_x = int(0.80 * 1920)
    fire_y = int(0.75 * 1080)
    assert (ecodes.EV_ABS, ecodes.ABS_MT_POSITION_X, fire_x) in sink.recorded_events
    assert (ecodes.EV_ABS, ecodes.ABS_MT_POSITION_Y, fire_y) in sink.recorded_events

    # Release left click (BTN_LEFT = 0) -> Release Slot 1
    sink.recorded_events.clear()
    engine.handle_mouse_button(code=ecodes.BTN_LEFT, value=0, injector=injector)
    assert 1 not in injector.active_slots
    assert (ecodes.EV_ABS, ecodes.ABS_MT_SLOT, 1) in sink.recorded_events
    assert (ecodes.EV_ABS, ecodes.ABS_MT_TRACKING_ID, -1) in sink.recorded_events
    # Slot 0 remains active
    assert 0 in injector.active_slots

