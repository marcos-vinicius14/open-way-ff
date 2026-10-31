"""JSON profile persistence and configuration data models for WayFire."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional

from wayfire.config.widgets import (
    AimWidget,
    BaseWidget,
    DPadWidget,
    FireWidget,
    TapWidget,
    WidgetFactory,
)


@dataclass
class ResolutionConfig:
    """Resolution parameters for game container display."""

    width: int = 1440
    height: int = 1080


@dataclass
class MouseSettingsConfig:
    """Mouse input sensitivity and hardware capture parameters."""

    sensitivity_x: float = 1.45
    sensitivity_y: float = 3.20
    lock_hotkey: str = "KEY_F1"
    smoothing: bool = True
    alpha: float = 0.80
    invert_y: bool = False


@dataclass
class UISettingsConfig:
    """On-screen display and overlay settings."""

    show_keys_on_screen: bool = True
    osd_opacity: float = 0.35


class WayFireProfile:
    """Configuration profile containing resolution, mouse settings, widgets and HUD mapping."""

    def __init__(
        self,
        profile_name: Optional[str] = None,
        game_package: str = "com.dts.freefireth",
        resolution: Optional[ResolutionConfig] = None,
        mouse_settings: Optional[MouseSettingsConfig] = None,
        ui_settings: Optional[UISettingsConfig] = None,
        widgets: Optional[list[BaseWidget]] = None,
        # Legacy Phase 1 keyword arguments
        name: Optional[str] = None,
        sens_x: Optional[float] = None,
        sens_y: Optional[float] = None,
        smoothing: Optional[bool] = None,
        alpha: Optional[float] = None,
        invert_y: Optional[bool] = None,
        suspend_key: Optional[str] = None,
        screen_width: Optional[int] = None,
        screen_height: Optional[int] = None,
        camera_anchor: Optional[tuple[float, float]] = None,
        camera_radius: Optional[float] = None,
        fire_button_pos: Optional[tuple[float, float]] = None,
    ) -> None:
        self.profile_name: str = str(profile_name or name or "default_freefire")
        self.game_package: str = str(game_package)

        self.resolution: ResolutionConfig = resolution or ResolutionConfig()
        if screen_width is not None:
            self.resolution.width = int(screen_width)
        if screen_height is not None:
            self.resolution.height = int(screen_height)

        self.mouse_settings: MouseSettingsConfig = mouse_settings or MouseSettingsConfig()
        if sens_x is not None:
            self.mouse_settings.sensitivity_x = float(sens_x)
        if sens_y is not None:
            self.mouse_settings.sensitivity_y = float(sens_y)
        if smoothing is not None:
            self.mouse_settings.smoothing = bool(smoothing)
        if alpha is not None:
            self.mouse_settings.alpha = float(alpha)
        if invert_y is not None:
            self.mouse_settings.invert_y = bool(invert_y)
        if suspend_key is not None:
            self.mouse_settings.lock_hotkey = str(suspend_key)

        self.ui_settings: UISettingsConfig = ui_settings or UISettingsConfig()
        self.widgets: list[BaseWidget] = list(widgets) if widgets is not None else []

        self._legacy_anchor: Optional[tuple[float, float]] = camera_anchor
        self._legacy_radius: Optional[float] = camera_radius
        self._legacy_fire_pos: Optional[tuple[float, float]] = fire_button_pos

        if camera_anchor is not None:
            self.camera_anchor = camera_anchor
        if camera_radius is not None:
            self.camera_radius = camera_radius
        if fire_button_pos is not None:
            self.fire_button_pos = fire_button_pos

    # --- Phase 1 Backward Compatibility Properties ---

    @property
    def name(self) -> str:
        return self.profile_name

    @name.setter
    def name(self, val: str) -> None:
        self.profile_name = str(val)

    @property
    def sens_x(self) -> float:
        return self.mouse_settings.sensitivity_x

    @sens_x.setter
    def sens_x(self, val: float) -> None:
        self.mouse_settings.sensitivity_x = float(val)

    @property
    def sens_y(self) -> float:
        return self.mouse_settings.sensitivity_y

    @sens_y.setter
    def sens_y(self, val: float) -> None:
        self.mouse_settings.sensitivity_y = float(val)

    @property
    def screen_width(self) -> int:
        return self.resolution.width

    @screen_width.setter
    def screen_width(self, val: int) -> None:
        self.resolution.width = int(val)

    @property
    def screen_height(self) -> int:
        return self.resolution.height

    @screen_height.setter
    def screen_height(self, val: int) -> None:
        self.resolution.height = int(val)

    @property
    def suspend_key(self) -> str:
        return self.mouse_settings.lock_hotkey

    @suspend_key.setter
    def suspend_key(self, val: str) -> None:
        self.mouse_settings.lock_hotkey = str(val)

    @property
    def smoothing(self) -> bool:
        return self.mouse_settings.smoothing

    @smoothing.setter
    def smoothing(self, val: bool) -> None:
        self.mouse_settings.smoothing = bool(val)

    @property
    def alpha(self) -> float:
        return self.mouse_settings.alpha

    @alpha.setter
    def alpha(self, val: float) -> None:
        self.mouse_settings.alpha = float(val)

    @property
    def invert_y(self) -> bool:
        return self.mouse_settings.invert_y

    @invert_y.setter
    def invert_y(self, val: bool) -> None:
        self.mouse_settings.invert_y = bool(val)

    @property
    def camera_anchor(self) -> tuple[float, float]:
        for w in self.widgets:
            if isinstance(w, AimWidget):
                w_w = max(1, self.resolution.width)
                w_h = max(1, self.resolution.height)
                return (round(float(w.x) / w_w, 2), round(float(w.y) / w_h, 2))
        return self._legacy_anchor or (0.65, 0.50)

    @camera_anchor.setter
    def camera_anchor(self, val: tuple[float, float]) -> None:
        self._legacy_anchor = (float(val[0]), float(val[1]))
        w_w = max(1, self.resolution.width)
        w_h = max(1, self.resolution.height)
        for w in self.widgets:
            if isinstance(w, AimWidget):
                w.x = round(val[0] * w_w, 2)
                w.y = round(val[1] * w_h, 2)
                return
        self.widgets.append(
            AimWidget(
                id="aim_camera",
                x=round(val[0] * w_w, 2),
                y=round(val[1] * w_h, 2),
                width=400,
                height=400,
            )
        )

    @property
    def camera_radius(self) -> float:
        for w in self.widgets:
            if isinstance(w, AimWidget):
                base_dim = min(self.resolution.width, self.resolution.height)
                return round(float(w.width / 2) / base_dim, 2)
        return self._legacy_radius if self._legacy_radius is not None else 0.20

    @camera_radius.setter
    def camera_radius(self, val: float) -> None:
        self._legacy_radius = float(val)
        base_dim = min(self.resolution.width, self.resolution.height)
        for w in self.widgets:
            if isinstance(w, AimWidget):
                w.width = round(val * 2 * base_dim, 2)
                w.height = round(val * 2 * base_dim, 2)
                return

    @property
    def fire_button_pos(self) -> tuple[float, float]:
        for w in self.widgets:
            if isinstance(w, FireWidget) or (isinstance(w, TapWidget) and w.id == "fire_button"):
                w_w = max(1, self.resolution.width)
                w_h = max(1, self.resolution.height)
                return (round(float(w.x) / w_w, 2), round(float(w.y) / w_h, 2))
        return self._legacy_fire_pos or (0.80, 0.75)

    @fire_button_pos.setter
    def fire_button_pos(self, val: tuple[float, float]) -> None:
        self._legacy_fire_pos = (float(val[0]), float(val[1]))
        w_w = max(1, self.resolution.width)
        w_h = max(1, self.resolution.height)
        for w in self.widgets:
            if isinstance(w, FireWidget) or (isinstance(w, TapWidget) and w.id == "fire_button"):
                w.x = round(val[0] * w_w, 2)
                w.y = round(val[1] * w_h, 2)
                return
        self.widgets.append(
            FireWidget(
                id="fire_button",
                key="Mouse_Left",
                x=round(val[0] * w_w, 2),
                y=round(val[1] * w_h, 2),
            )
        )

    # --- Serialization and Persistence ---

    @classmethod
    def get_default_profile_path(cls) -> Path:
        """Return the default system storage path for active profile."""
        return Path.home() / ".config" / "wayfire" / "profiles" / "default_freefire.json"

    def to_dict(self) -> dict[str, Any]:
        """Convert profile to modern hierarchical serializable dictionary."""
        return {
            "profile_name": self.profile_name,
            "game_package": self.game_package,
            "resolution": asdict(self.resolution),
            "mouse_settings": asdict(self.mouse_settings),
            "ui_settings": asdict(self.ui_settings),
            "widgets": [w.to_dict() for w in self.widgets],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WayFireProfile:
        """Construct WayFireProfile from dictionary, auto-migrating flat Phase 1 format."""
        if not isinstance(data, dict):
            return cls()

        # Check if legacy flat dictionary from Phase 1
        if "resolution" not in data and "mouse_settings" not in data:
            profile_name = str(data.get("name", "default_freefire"))
            res = ResolutionConfig(
                width=int(data.get("screen_width", 1920)),
                height=int(data.get("screen_height", 1080)),
            )
            mouse = MouseSettingsConfig(
                sensitivity_x=float(data.get("sens_x", 1.45)),
                sensitivity_y=float(data.get("sens_y", 3.20)),
                lock_hotkey=str(data.get("suspend_key", "KEY_F1")),
                smoothing=bool(data.get("smoothing", True)),
                alpha=float(data.get("alpha", 0.80)),
                invert_y=bool(data.get("invert_y", False)),
            )
            ui = UISettingsConfig()
            widgets: list[BaseWidget] = []

            anchor = data.get("camera_anchor", (0.65, 0.50))
            if isinstance(anchor, (list, tuple)) and len(anchor) >= 2:
                widgets.append(
                    AimWidget(
                        id="aim_camera",
                        x=round(float(anchor[0]) * res.width, 2),
                        y=round(float(anchor[1]) * res.height, 2),
                        width=round(float(data.get("camera_radius", 0.20)) * 2 * min(res.width, res.height), 2),
                        height=round(float(data.get("camera_radius", 0.20)) * 2 * min(res.width, res.height), 2),
                    )
                )

            fire_pos = data.get("fire_button_pos", (0.80, 0.75))
            if isinstance(fire_pos, (list, tuple)) and len(fire_pos) >= 2:
                widgets.append(
                    FireWidget(
                        id="fire_button",
                        key="Mouse_Left",
                        x=round(float(fire_pos[0]) * res.width, 2),
                        y=round(float(fire_pos[1]) * res.height, 2),
                    )
                )

            return cls(
                profile_name=profile_name,
                resolution=res,
                mouse_settings=mouse,
                ui_settings=ui,
                widgets=widgets,
            )

        # Hierarchical format
        res_data = data.get("resolution", {})
        res = ResolutionConfig(
            width=int(res_data.get("width", 1440)),
            height=int(res_data.get("height", 1080)),
        )

        mouse_data = data.get("mouse_settings", {})
        mouse = MouseSettingsConfig(
            sensitivity_x=float(mouse_data.get("sensitivity_x", 1.45)),
            sensitivity_y=float(mouse_data.get("sensitivity_y", 3.20)),
            lock_hotkey=str(mouse_data.get("lock_hotkey", "KEY_F1")),
            smoothing=bool(mouse_data.get("smoothing", True)),
            alpha=float(mouse_data.get("alpha", 0.80)),
            invert_y=bool(mouse_data.get("invert_y", False)),
        )

        ui_data = data.get("ui_settings", {})
        ui = UISettingsConfig(
            show_keys_on_screen=bool(ui_data.get("show_keys_on_screen", True)),
            osd_opacity=float(ui_data.get("osd_opacity", 0.35)),
        )

        widgets_data = data.get("widgets", [])
        widgets_list: list[BaseWidget] = []
        if isinstance(widgets_data, list):
            for item in widgets_data:
                if isinstance(item, dict):
                    try:
                        w = WidgetFactory.from_dict(item)
                        widgets_list.append(w)
                    except ValueError:
                        pass

        return cls(
            profile_name=str(data.get("profile_name", data.get("name", "default_freefire"))),
            game_package=str(data.get("game_package", "com.dts.freefireth")),
            resolution=res,
            mouse_settings=mouse,
            ui_settings=ui,
            widgets=widgets_list,
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
            profile = create_default_profile()
            profile.save(target_path)
            return profile

        try:
            with target_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return cls.from_dict(data)
        except (json.JSONDecodeError, OSError):
            return create_default_profile()


def create_default_profile() -> WayFireProfile:
    """Create complete game-ready factory default profile with 14 essential Free Fire buttons."""
    widgets: list[BaseWidget] = [
        AimWidget(id="aim_camera", x=1050, y=540, width=400, height=400),
        FireWidget(id="fire_button", key="Mouse_Left", x=1280, y=620),
        DPadWidget(
            id="movement_dpad",
            x=260,
            y=780,
            radius=90,
            keys={"up": "W", "down": "S", "left": "A", "right": "D"},
            deadzone=0.1,
        ),
        TapWidget(id="jump_button", key="Space", x=1350, y=720),
        TapWidget(id="crouch_button", key="C", x=1220, y=880),
        TapWidget(id="prone_button", key="Z", x=1220, y=960),
        TapWidget(id="reload_button", key="R", x=1180, y=280),
        TapWidget(id="scope_button", key="Mouse_Right", x=1310, y=420),
        TapWidget(id="medkit_button", key="4", x=200, y=600),
        TapWidget(id="grenade_button", key="E", x=400, y=700),
        TapWidget(id="interact_button", key="F", x=1000, y=400),
        TapWidget(id="weapon_1", key="1", x=900, y=180),
        TapWidget(id="weapon_2", key="2", x=1020, y=180),
        TapWidget(id="weapon_3", key="3", x=1140, y=180),
    ]

    return WayFireProfile(
        profile_name="default_freefire",
        game_package="com.dts.freefireth",
        resolution=ResolutionConfig(width=1440, height=1080),
        mouse_settings=MouseSettingsConfig(
            sensitivity_x=1.45,
            sensitivity_y=3.20,
            lock_hotkey="KEY_F1",
            smoothing=True,
            alpha=0.80,
            invert_y=False,
        ),
        ui_settings=UISettingsConfig(show_keys_on_screen=True, osd_opacity=0.35),
        widgets=widgets,
    )
