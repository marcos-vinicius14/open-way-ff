"""Polymorphic widget modeling and discriminator factory for HUD mapping."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, ClassVar, Optional


@dataclass
class BaseWidget(ABC):
    """Abstract base class for all HUD mapping components."""

    id: str
    type: str

    @abstractmethod
    def to_dict(self) -> dict[str, Any]:
        """Serialize widget configuration to dictionary."""
        ...


@dataclass
class TapWidget(BaseWidget):
    """Single tap, hold, or turbo action button component."""

    key: str = ""
    x: float | int = 0
    y: float | int = 0
    mode: str = "single"  # "single", "hold", "turbo"
    type: str = "tap"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "key": self.key,
            "x": self.x,
            "y": self.y,
            "mode": self.mode,
        }


@dataclass
class DPadWidget(BaseWidget):
    """Virtual 8-way directional analog pad for movement."""

    x: float | int = 0
    y: float | int = 0
    radius: float | int = 90
    keys: dict[str, str] = field(default_factory=lambda: {"up": "W", "down": "S", "left": "A", "right": "D"})
    deadzone: float = 0.1
    type: str = "dpad"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "x": self.x,
            "y": self.y,
            "radius": self.radius,
            "keys": dict(self.keys),
            "deadzone": self.deadzone,
        }


@dataclass
class AimWidget(BaseWidget):
    """FPS camera view and mouse aim coordinate tracker."""

    x: float | int = 0
    y: float | int = 0
    width: float | int = 400
    height: float | int = 400
    sensitivity_x: Optional[float] = None
    sensitivity_y: Optional[float] = None
    type: str = "aim"

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "id": self.id,
            "type": self.type,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
        }
        if self.sensitivity_x is not None:
            d["sensitivity_x"] = self.sensitivity_x
        if self.sensitivity_y is not None:
            d["sensitivity_y"] = self.sensitivity_y
        return d


@dataclass
class FireWidget(BaseWidget):
    """Dedicated weapon trigger mapped to mouse click."""

    key: str = "Mouse_Left"
    x: float | int = 1280
    y: float | int = 620
    type: str = "fire"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "key": self.key,
            "x": self.x,
            "y": self.y,
        }


class WidgetFactory:
    """Discriminator factory for serializing and deserializing polymorphic widgets."""

    _REGISTRY: ClassVar[dict[str, type[BaseWidget]]] = {
        "tap": TapWidget,
        "dpad": DPadWidget,
        "aim": AimWidget,
        "fire": FireWidget,
    }

    @classmethod
    def register(cls, widget_type: str, widget_cls: type[BaseWidget]) -> None:
        """Register a new widget class under the given type discriminator."""
        cls._REGISTRY[widget_type.lower()] = widget_cls

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BaseWidget:
        """Instantiate appropriate widget subclass from raw dictionary."""
        if not isinstance(data, dict):
            raise ValueError(f"Dados do widget inválidos, esperado dict, recebido {type(data)}")

        widget_type = data.get("type")
        if not widget_type or not isinstance(widget_type, str):
            raise ValueError("Campo obrigatório 'type' ausente ou inválido no widget.")

        w_type = widget_type.lower()
        target_cls = cls._REGISTRY.get(w_type)
        if target_cls is None:
            raise ValueError(f"Tipo de widget desconhecido: '{widget_type}'. Tipos suportados: {list(cls._REGISTRY.keys())}")

        widget_id = data.get("id")
        if not widget_id or not isinstance(widget_id, str):
            raise ValueError("Campo obrigatório 'id' ausente ou inválido no widget.")

        if "x" not in data or "y" not in data:
            raise ValueError(f"Campos de coordenadas 'x' e 'y' são obrigatórios no widget '{widget_id}'.")

        try:
            x = float(data["x"])
            y = float(data["y"])
        except (ValueError, TypeError) as exc:
            raise ValueError(f"Coordenadas 'x' e 'y' devem ser numéricas no widget '{widget_id}'.") from exc

        if target_cls is TapWidget:
            return TapWidget(
                id=widget_id,
                key=str(data.get("key", "")),
                x=x,
                y=y,
                mode=str(data.get("mode", "single")),
            )

        if target_cls is DPadWidget:
            keys = data.get("keys", {"up": "W", "down": "S", "left": "A", "right": "D"})
            if not isinstance(keys, dict):
                keys = {"up": "W", "down": "S", "left": "A", "right": "D"}
            return DPadWidget(
                id=widget_id,
                x=x,
                y=y,
                radius=float(data.get("radius", 90)),
                keys=keys,
                deadzone=float(data.get("deadzone", 0.1)),
            )

        if target_cls is AimWidget:
            sens_x = float(data["sensitivity_x"]) if "sensitivity_x" in data and data["sensitivity_x"] is not None else None
            sens_y = float(data["sensitivity_y"]) if "sensitivity_y" in data and data["sensitivity_y"] is not None else None
            return AimWidget(
                id=widget_id,
                x=x,
                y=y,
                width=float(data.get("width", 400)),
                height=float(data.get("height", 400)),
                sensitivity_x=sens_x,
                sensitivity_y=sens_y,
            )

        if target_cls is FireWidget:
            return FireWidget(
                id=widget_id,
                key=str(data.get("key", "Mouse_Left")),
                x=x,
                y=y,
            )

        # Fallback for custom registered widgets
        kwargs: dict[str, Any] = {k: v for k, v in data.items() if k != "type"}
        return target_cls(**kwargs)
