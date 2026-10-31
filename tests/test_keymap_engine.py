"""Tests for KeymapEngine event dispatching, multi-touch slots, DPad 8-way, and Fire button."""

from __future__ import annotations

from unittest.mock import MagicMock
import pytest
from evdev import ecodes

from wayfire.config.profile import WayFireProfile
from wayfire.config.widgets import (
    AimWidget,
    DPadWidget,
    FireWidget,
    MacroStep,
    MacroWidget,
    TapWidget,
)
from wayfire.core.keymap_engine import KeymapEngine
from wayfire.core.touch_injector import MockUInputSink, TouchInjector


@pytest.fixture
def test_setup():
    sink = MockUInputSink()
    injector = TouchInjector(sink=sink, width=1920, height=1080)
    profile = WayFireProfile(name="test_engine_profile")
    profile.widgets = []
    key_state_mock = MagicMock()

    engine = KeymapEngine(
        profile=profile,
        injector=injector,
        on_key_state_change=key_state_mock,
    )
    return engine, profile, sink, injector, key_state_mock


def test_keymap_engine_tap_dispatch(test_setup):
    """Verify single and multi-touch tap buttons dispatch to dynamic slots (D-16, MAP-02)."""
    engine, profile, sink, _, _ = test_setup

    tap1 = TapWidget(id="tap_space", key="Space", x=500.0, y=600.0)
    tap2 = TapWidget(id="tap_e", key="E", x=700.0, y=800.0)
    profile.widgets.extend([tap1, tap2])

    # Press Space
    handled_space = engine.handle_key_event(ecodes.KEY_SPACE, 1)
    assert handled_space is True
    assert tap1.id in engine.active_widget_touches
    slot1 = engine.active_widget_touches[tap1.id]
    assert (ecodes.EV_ABS, ecodes.ABS_MT_SLOT, slot1) in sink.recorded_events
    assert (ecodes.EV_ABS, ecodes.ABS_MT_POSITION_X, 500) in sink.recorded_events

    # Press E simultaneously (multi-touch concurrency)
    sink.recorded_events.clear()
    handled_e = engine.handle_key_event(ecodes.KEY_E, 1)
    assert handled_e is True
    assert tap2.id in engine.active_widget_touches
    slot2 = engine.active_widget_touches[tap2.id]
    assert slot1 != slot2
    assert (ecodes.EV_ABS, ecodes.ABS_MT_SLOT, slot2) in sink.recorded_events

    # Release Space
    sink.recorded_events.clear()
    engine.handle_key_event(ecodes.KEY_SPACE, 0)
    assert tap1.id not in engine.active_widget_touches
    assert (ecodes.EV_ABS, ecodes.ABS_MT_SLOT, slot1) in sink.recorded_events
    assert (ecodes.EV_ABS, ecodes.ABS_MT_TRACKING_ID, -1) in sink.recorded_events

    # Release E
    sink.recorded_events.clear()
    engine.handle_key_event(ecodes.KEY_E, 0)
    assert tap2.id not in engine.active_widget_touches
    assert (ecodes.EV_ABS, ecodes.ABS_MT_SLOT, slot2) in sink.recorded_events


def test_keymap_engine_dpad_8way_movement(test_setup):
    """Verify DPad calculates 8-directional analog vector on dedicated slot 2 (MAP-02)."""
    engine, profile, sink, _, _ = test_setup

    dpad = DPadWidget(
        id="dpad_main",
        x=300.0,
        y=300.0,
        radius=100.0,
        keys={"up": "W", "down": "S", "left": "A", "right": "D"},
    )
    profile.widgets.append(dpad)

    # 1. Press W (Up: y decreases by radius)
    engine.handle_key_event(ecodes.KEY_W, 1)
    assert "dpad" in engine.active_widget_touches
    assert engine.active_widget_touches["dpad"] == 2
    assert (ecodes.EV_ABS, ecodes.ABS_MT_SLOT, 2) in sink.recorded_events
    assert (ecodes.EV_ABS, ecodes.ABS_MT_POSITION_X, 300) in sink.recorded_events
    assert (ecodes.EV_ABS, ecodes.ABS_MT_POSITION_Y, 200) in sink.recorded_events

    # 2. Press D (Up-Right diagonal: normalizes vector)
    sink.recorded_events.clear()
    engine.handle_key_event(ecodes.KEY_D, 1)
    expected_x = int(300 + 100 * (1 / (2**0.5)))
    expected_y = int(300 - 100 * (1 / (2**0.5)))
    assert (ecodes.EV_ABS, ecodes.ABS_MT_POSITION_X, expected_x) in sink.recorded_events
    assert (ecodes.EV_ABS, ecodes.ABS_MT_POSITION_Y, expected_y) in sink.recorded_events

    # 3. Release W (Right only)
    sink.recorded_events.clear()
    engine.handle_key_event(ecodes.KEY_W, 0)
    assert (ecodes.EV_ABS, ecodes.ABS_MT_POSITION_X, 400) in sink.recorded_events
    assert (ecodes.EV_ABS, ecodes.ABS_MT_POSITION_Y, 300) in sink.recorded_events

    # 4. Release D (All released -> touch up on slot 2)
    sink.recorded_events.clear()
    engine.handle_key_event(ecodes.KEY_D, 0)
    assert "dpad" not in engine.active_widget_touches
    assert (ecodes.EV_ABS, ecodes.ABS_MT_SLOT, 2) in sink.recorded_events
    assert (ecodes.EV_ABS, ecodes.ABS_MT_TRACKING_ID, -1) in sink.recorded_events


def test_keymap_engine_fire_button(test_setup):
    """Verify dedicated weapon trigger maps to slot 1 on Mouse_Left (BTN_LEFT)."""
    engine, profile, sink, _, _ = test_setup

    fire = FireWidget(id="fire_btn", x=1280.0, y=620.0, key="Mouse_Left")
    profile.widgets.append(fire)

    # Press Left Click
    handled_press = engine.handle_mouse_button(ecodes.BTN_LEFT, 1)
    assert handled_press is True
    assert (ecodes.EV_ABS, ecodes.ABS_MT_SLOT, 1) in sink.recorded_events
    assert (ecodes.EV_ABS, ecodes.ABS_MT_POSITION_X, 1280) in sink.recorded_events
    assert (ecodes.EV_ABS, ecodes.ABS_MT_POSITION_Y, 620) in sink.recorded_events

    # Release Left Click
    sink.recorded_events.clear()
    handled_release = engine.handle_mouse_button(ecodes.BTN_LEFT, 0)
    assert handled_release is True
    assert (ecodes.EV_ABS, ecodes.ABS_MT_SLOT, 1) in sink.recorded_events
    assert (ecodes.EV_ABS, ecodes.ABS_MT_TRACKING_ID, -1) in sink.recorded_events


def test_keymap_engine_macro_trigger(test_setup):
    """Verify macro widget triggers sequential steps via scheduler (D-16)."""
    engine, profile, sink, _, _ = test_setup

    macro = MacroWidget(
        id="macro_test",
        key="G",
        steps=[MacroStep(x=100, y=100, delay_ms=10)],
    )
    profile.widgets.append(macro)

    handled = engine.handle_key_event(ecodes.KEY_G, 1)
    assert handled is True
    assert engine.macro_scheduler.has_pending_actions is True

    engine.poll_tick()
    assert (ecodes.EV_ABS, ecodes.ABS_MT_POSITION_X, 100) in sink.recorded_events
