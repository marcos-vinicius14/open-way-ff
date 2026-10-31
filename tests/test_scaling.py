"""Unit tests for dynamic screen resolution scaling in TouchInjector and AimEngine."""

from evdev import ecodes

from wayfire.core.aim_engine import AimEngine, AimProcessor
from wayfire.core.touch_injector import MockUInputSink, TouchInjector


def test_touch_injector_dynamic_dimensions() -> None:
    """Validate that updating screen dimensions clamps coordinates to the new boundary."""
    sink = MockUInputSink()
    injector = TouchInjector(sink=sink, width=1920, height=1080)

    # Touch down with coordinate within 1920 but outside 1440
    injector.touch_down(slot=1, x=1800, y=1000)
    x_events = [e for e in sink.recorded_events if e[0] == ecodes.EV_ABS and e[1] == ecodes.ABS_MT_POSITION_X]
    assert x_events[-1][2] == 1800

    # Dynamically change dimensions to stretched 1440x1080
    injector.set_screen_dimensions(width=1440, height=1080)
    assert injector.width == 1440
    assert injector.height == 1080

    # Moving to 1800 should now clamp to 1440
    injector.touch_move(slot=1, x=1800, y=1000)
    x_events = [e for e in sink.recorded_events if e[0] == ecodes.EV_ABS and e[1] == ecodes.ABS_MT_POSITION_X]
    assert x_events[-1][2] == 1440


def test_aim_engine_dynamic_dimensions() -> None:
    """Validate that AimEngine dynamically converts normalized anchor and radius on resolution update."""
    processor = AimProcessor(sens_x=1.0, sens_y=1.0, smoothing=False)
    engine = AimEngine(
        processor=processor,
        screen_width=1920,
        screen_height=1080,
        anchor_norm_x=0.65,
        anchor_norm_y=0.50,
        radius_norm=0.20,
    )

    # In 1920x1080:
    # anchor_x = int(0.65 * 1920) = 1248
    # anchor_y = int(0.50 * 1080) = 540
    # radius_px = int(0.20 * min(1920, 1080)) = int(0.20 * 1080) = 216
    assert engine.anchor_px == (1248, 540)
    assert engine.radius_px == 216
    assert engine.current_x == 1248
    assert engine.current_y == 540

    # Switch to stretched 4:3 (1440x1080)
    # anchor_x = int(0.65 * 1440) = 936
    # anchor_y = int(0.50 * 1080) = 540
    # radius_px = int(0.20 * min(1440, 1080)) = int(0.20 * 1080) = 216
    engine.set_screen_dimensions(1440, 1080)
    assert engine.screen_width == 1440
    assert engine.screen_height == 1080
    assert engine.anchor_px == (936, 540)
    assert engine.radius_px == 216
    assert engine.current_x == 936
    assert engine.current_y == 540

    # Switch to 1024x768
    # anchor_x = int(0.65 * 1024) = 665
    # anchor_y = int(0.50 * 768) = 384
    # radius_px = int(0.20 * 768) = 153
    engine.set_screen_dimensions(1024, 768)
    assert engine.screen_width == 1024
    assert engine.screen_height == 768
    assert engine.anchor_px == (665, 384)
    assert engine.radius_px == 153
    assert engine.current_x == 665
    assert engine.current_y == 384
