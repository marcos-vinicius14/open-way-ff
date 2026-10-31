"""User interface and HUD modules for WayFire."""

from typing import Any

__all__ = [
    "AimState",
    "OverlayMode",
    "StatusPill",
    "WayFireLauncherWindow",
    "WayFireLogDialog",
    "WayFireOverlayWindow",
]


def __getattr__(name: str) -> Any:
    if name in ("OverlayMode", "WayFireOverlayWindow"):
        from wayfire.ui.overlay import OverlayMode, WayFireOverlayWindow
        return locals()[name]
    if name in ("AimState", "StatusPill"):
        from wayfire.ui.status_pill import AimState, StatusPill
        return locals()[name]
    if name == "WayFireLauncherWindow":
        from wayfire.ui.launcher_window import WayFireLauncherWindow
        return WayFireLauncherWindow
    if name == "WayFireLogDialog":
        from wayfire.ui.log_dialog import WayFireLogDialog
        return WayFireLogDialog
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
