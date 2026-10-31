"""Core input and emulation modules for WayFire."""

from typing import Any

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


def __getattr__(name: str) -> Any:
    if name in ("AimEngine", "AimProcessor"):
        from wayfire.core.aim_engine import AimEngine, AimProcessor
        return locals()[name]
    if name == "KeymapEngine":
        from wayfire.core.keymap_engine import KeymapEngine
        return KeymapEngine
    if name in ("InputCaptureManager", "detect_input_devices"):
        from wayfire.core.mouse_capture import InputCaptureManager, detect_input_devices
        return locals()[name]
    if name in ("GameSessionCoordinator", "SessionState"):
        from wayfire.core.session_coordinator import GameSessionCoordinator, SessionState
        return locals()[name]
    if name == "TouchInjector":
        from wayfire.core.touch_injector import TouchInjector
        return TouchInjector
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
