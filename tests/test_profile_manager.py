"""Unit tests for polymorphic widgets, profile manager, migration, and security."""

from pathlib import Path
import pytest

from wayfire.config.profile import (
    MouseSettingsConfig,
    ResolutionConfig,
    UISettingsConfig,
    WayFireProfile,
    create_default_profile,
)
from wayfire.config.widgets import (
    AimWidget,
    BaseWidget,
    DPadWidget,
    FireWidget,
    TapWidget,
    WidgetFactory,
)


def test_polymorphic_widgets_serialization() -> None:
    """Ensure polymorphic widgets serialize to dict and deserialize via WidgetFactory."""
    # 1. TapWidget
    tap = TapWidget(id="jump_btn", key="Space", x=1350, y=720, mode="single")
    tap_dict = tap.to_dict()
    assert tap_dict["type"] == "tap"
    assert tap_dict["id"] == "jump_btn"
    assert tap_dict["key"] == "Space"
    assert tap_dict["x"] == 1350
    assert tap_dict["y"] == 720
    assert tap_dict["mode"] == "single"

    tap_restored = WidgetFactory.from_dict(tap_dict)
    assert isinstance(tap_restored, TapWidget)
    assert tap_restored.id == "jump_btn"
    assert tap_restored.key == "Space"
    assert tap_restored.x == 1350

    # 2. DPadWidget
    dpad = DPadWidget(
        id="movement",
        x=260,
        y=780,
        radius=95,
        keys={"up": "W", "down": "S", "left": "A", "right": "D"},
        deadzone=0.15,
    )
    dpad_dict = dpad.to_dict()
    assert dpad_dict["type"] == "dpad"
    assert dpad_dict["radius"] == 95
    assert dpad_dict["deadzone"] == 0.15

    dpad_restored = WidgetFactory.from_dict(dpad_dict)
    assert isinstance(dpad_restored, DPadWidget)
    assert dpad_restored.radius == 95
    assert dpad_restored.keys["up"] == "W"

    # 3. AimWidget
    aim = AimWidget(id="cam", x=1050, y=540, width=420, height=420, sensitivity_x=1.5, sensitivity_y=3.0)
    aim_dict = aim.to_dict()
    assert aim_dict["type"] == "aim"
    assert aim_dict["sensitivity_x"] == 1.5

    aim_restored = WidgetFactory.from_dict(aim_dict)
    assert isinstance(aim_restored, AimWidget)
    assert aim_restored.width == 420
    assert aim_restored.sensitivity_x == 1.5

    # 4. FireWidget
    fire = FireWidget(id="fire_btn", key="Mouse_Left", x=1280, y=620)
    fire_dict = fire.to_dict()
    assert fire_dict["type"] == "fire"
    assert fire_dict["key"] == "Mouse_Left"

    fire_restored = WidgetFactory.from_dict(fire_dict)
    assert isinstance(fire_restored, FireWidget)
    assert fire_restored.x == 1280


def test_widget_factory_validation_errors() -> None:
    """Ensure WidgetFactory validates type and required coordinate fields."""
    with pytest.raises(ValueError, match="Tipo de widget desconhecido"):
        WidgetFactory.from_dict({"id": "unknown", "type": "flying_carpet", "x": 100, "y": 100})

    with pytest.raises(ValueError, match="Campo obrigatório 'type'"):
        WidgetFactory.from_dict({"id": "missing_type", "x": 100, "y": 100})

    with pytest.raises(ValueError, match="Campo obrigatório 'id'"):
        WidgetFactory.from_dict({"type": "tap", "x": 100, "y": 100})

    with pytest.raises(ValueError, match="Campos de coordenadas"):
        WidgetFactory.from_dict({"id": "no_coords", "type": "tap"})


def test_default_profile_structure() -> None:
    """Validate that create_default_profile creates 14 game-ready buttons in 1440x1080."""
    profile = create_default_profile()

    assert profile.profile_name == "default_freefire"
    assert profile.resolution.width == 1440
    assert profile.resolution.height == 1080
    assert profile.mouse_settings.sensitivity_x == 1.45
    assert profile.mouse_settings.sensitivity_y == 3.20

    # Verify all 14 buttons
    assert len(profile.widgets) == 14

    widget_ids = {w.id for w in profile.widgets}
    expected_ids = {
        "aim_camera",
        "fire_button",
        "movement_dpad",
        "jump_button",
        "crouch_button",
        "prone_button",
        "reload_button",
        "scope_button",
        "medkit_button",
        "grenade_button",
        "interact_button",
        "weapon_1",
        "weapon_2",
        "weapon_3",
    }
    assert expected_ids.issubset(widget_ids)

    # Verify aim and fire are present and match camera_anchor / fire_button_pos
    aim_w = next(w for w in profile.widgets if isinstance(w, AimWidget))
    assert aim_w.x == 1050
    assert aim_w.y == 540
    assert profile.camera_anchor == (round(1050 / 1440, 2), round(540 / 1080, 2))

    fire_w = next(w for w in profile.widgets if isinstance(w, FireWidget))
    assert fire_w.x == 1280
    assert fire_w.y == 620
    assert profile.fire_button_pos == (round(1280 / 1440, 2), round(620 / 1080, 2))


def test_legacy_profile_migration() -> None:
    """Verify that flat Phase 1 profiles auto-migrate to hierarchical format transparently."""
    legacy_data = {
        "name": "legacy_phase1",
        "sens_x": 1.75,
        "sens_y": 3.50,
        "smoothing": True,
        "alpha": 0.85,
        "invert_y": False,
        "suspend_key": "KEY_F1",
        "screen_width": 1920,
        "screen_height": 1080,
        "camera_anchor": [0.65, 0.50],
        "camera_radius": 0.20,
        "fire_button_pos": [0.80, 0.75],
    }

    profile = WayFireProfile.from_dict(legacy_data)

    assert profile.profile_name == "legacy_phase1"
    assert profile.name == "legacy_phase1"
    assert profile.resolution.width == 1920
    assert profile.resolution.height == 1080
    assert profile.mouse_settings.sensitivity_x == 1.75
    assert profile.mouse_settings.sensitivity_y == 3.50
    assert profile.mouse_settings.lock_hotkey == "KEY_F1"

    # Check migrated widgets
    assert len(profile.widgets) == 2
    aim_w = next((w for w in profile.widgets if isinstance(w, AimWidget)), None)
    fire_w = next((w for w in profile.widgets if isinstance(w, FireWidget)), None)
    assert aim_w is not None
    assert fire_w is not None
    assert aim_w.x == 0.65 * 1920
    assert aim_w.y == 0.50 * 1080
    assert fire_w.x == 0.80 * 1920
    assert fire_w.y == 0.75 * 1080

    # Ensure modern to_dict preserves these
    d = profile.to_dict()
    assert "resolution" in d
    assert "mouse_settings" in d
    assert "widgets" in d
