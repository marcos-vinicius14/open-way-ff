"""Unit tests for AimProcessor sensitivity engine, subpixel accumulation, and EMA smoothing."""

from wayfire.core.aim_engine import AimProcessor


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
