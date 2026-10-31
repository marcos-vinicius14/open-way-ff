"""Core input and emulation modules for WayFire."""

from wayfire.core.aim_engine import AimEngine, AimProcessor
from wayfire.core.keymap_engine import KeymapEngine
from wayfire.core.mouse_capture import InputCaptureManager, detect_input_devices
from wayfire.core.session_coordinator import GameSessionCoordinator, SessionState
from wayfire.core.touch_injector import TouchInjector

__all__ = [
    "AimEngine",
    "AimProcessor",
    "GameSessionCoordinator",
    "InputCaptureManager",
    "KeymapEngine",
    "SessionState",
    "TouchInjector",
    "detect_input_devices",
]
