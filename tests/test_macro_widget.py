"""Tests for MacroWidget model, serialization, and NonBlockingMacroScheduler."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch
import pytest

from wayfire.config.widgets import MacroStep, MacroWidget, WidgetFactory
from wayfire.core.macro_scheduler import NonBlockingMacroScheduler
from wayfire.core.touch_injector import MockUInputSink, TouchInjector


def test_macro_widget_serialization():
    """Verify MacroStep and MacroWidget polymorphic serialization and deserialization (D-16)."""
    step1 = MacroStep(x=400, y=500, delay_ms=25)
    step2 = MacroStep(x=600, y=700, delay_ms=35)

    macro = MacroWidget(
        id="macro_combo_1",
        key="G",
        delay_ms=30,
        x=400,
        y=500,
        steps=[step1, step2],
    )

    data = macro.to_dict()
    assert data["id"] == "macro_combo_1"
    assert data["type"] == "macro"
    assert data["key"] == "G"
    assert data["delay_ms"] == 30
    assert len(data["steps"]) == 2
    assert data["steps"][0] == {"x": 400, "y": 500, "delay_ms": 25}
    assert data["steps"][1] == {"x": 600, "y": 700, "delay_ms": 35}

    # Deserialization via WidgetFactory
    deserialized = WidgetFactory.from_dict(data)
    assert isinstance(deserialized, MacroWidget)
    assert deserialized.id == "macro_combo_1"
    assert deserialized.key == "G"
    assert len(deserialized.steps) == 2
    assert isinstance(deserialized.steps[0], MacroStep)
    assert deserialized.steps[0].x == 400.0
    assert deserialized.steps[0].delay_ms == 25


def test_non_blocking_macro_scheduler_execution():
    """Verify NonBlockingMacroScheduler executes sequential touches based on monotonic time without time.sleep."""
    sink = MockUInputSink()
    injector = TouchInjector(sink=sink, width=1920, height=1080)
    scheduler = NonBlockingMacroScheduler(injector=injector, slot_start=4, slot_end=6)

    macro = MacroWidget(
        id="macro_test",
        key="M4",
        steps=[
            MacroStep(x=200, y=300, delay_ms=20),
            MacroStep(x=500, y=600, delay_ms=20),
        ],
    )

    slot = scheduler.trigger_macro(macro)
    assert slot == 4
    assert scheduler.has_pending_actions is True

    # Initial tick immediately executes step 1 touch down
    executed = scheduler.process_scheduled()
    assert executed >= 1

    # Advance virtual time through loop ticks
    base_time = time.monotonic()
    with patch("wayfire.core.macro_scheduler.time.monotonic") as mock_time:
        # +25ms: step 1 touch up and step 2 touch down
        mock_time.return_value = base_time + 0.025
        scheduler.process_scheduled()

        # +60ms: step 2 touch up and slot release
        mock_time.return_value = base_time + 0.060
        scheduler.process_scheduled()

    assert scheduler.has_pending_actions is False
    assert 4 in scheduler.available_slots
