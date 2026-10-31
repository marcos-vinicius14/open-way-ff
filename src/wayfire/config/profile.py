"""JSON profile persistence and configuration data models for WayFire."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Optional


@dataclass
class WayFireProfile:
    """Configuration profile containing sensitivity, anti-border and HUD mapping parameters."""

    name: str = "default_freefire"
    sens_x: float = 1.45
    sens_y: float = 3.20
    smoothing: bool = True
    alpha: float = 0.80
    invert_y: bool = False
    suspend_key: str = "KEY_F1"
    screen_width: int = 1920
    screen_height: int = 1080
    camera_anchor: tuple[float, float] = (0.65, 0.50)
    camera_radius: float = 0.20
    fire_button_pos: tuple[float, float] = (0.80, 0.75)

    @classmethod
    def get_default_profile_path(cls) -> Path:
        """Return the default system storage path for active profile."""
        return Path.home() / ".config" / "wayfire" / "profiles" / "default_freefire.json"

    def to_dict(self) -> dict[str, Any]:
        """Convert profile to serializable dictionary."""
        d = asdict(self)
        d["camera_anchor"] = list(self.camera_anchor)
        d["fire_button_pos"] = list(self.fire_button_pos)
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WayFireProfile:
        """Construct WayFireProfile from dictionary, preserving defaults for missing keys."""
        anchor = tuple(data.get("camera_anchor", [0.65, 0.50]))
        fire_pos = tuple(data.get("fire_button_pos", [0.80, 0.75]))

        return cls(
            name=str(data.get("name", "default_freefire")),
            sens_x=float(data.get("sens_x", 1.45)),
            sens_y=float(data.get("sens_y", 3.20)),
            smoothing=bool(data.get("smoothing", True)),
            alpha=float(data.get("alpha", 0.80)),
            invert_y=bool(data.get("invert_y", False)),
            suspend_key=str(data.get("suspend_key", "KEY_F1")),
            screen_width=int(data.get("screen_width", 1920)),
            screen_height=int(data.get("screen_height", 1080)),
            camera_anchor=(float(anchor[0]), float(anchor[1])),
            camera_radius=float(data.get("camera_radius", 0.20)),
            fire_button_pos=(float(fire_pos[0]), float(fire_pos[1])),
        )

    def save(self, path: Optional[Path | str] = None) -> Path:
        """Persist profile to JSON file, creating parent directories if needed."""
        target_path = Path(path) if path is not None else self.get_default_profile_path()
        target_path.parent.mkdir(parents=True, exist_ok=True)

        with target_path.open("w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

        return target_path

    @classmethod
    def load(cls, path: Optional[Path | str] = None) -> WayFireProfile:
        """Load profile from JSON file or return default profile if file does not exist."""
        target_path = Path(path) if path is not None else cls.get_default_profile_path()
        if not target_path.exists():
            profile = cls()
            profile.save(target_path)
            return profile

        try:
            with target_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return cls.from_dict(data)
        except (json.JSONDecodeError, OSError):
            return cls()
