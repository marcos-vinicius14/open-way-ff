"""Unit tests for configuration profiles and JSON persistence."""

from pathlib import Path
from wayfire.config.profile import WayFireProfile


def test_profile_serialization(tmp_path: Path) -> None:
    """Verify profile serialization and round-trip JSON persistence."""
    profile_path = tmp_path / "test_profile.json"

    profile = WayFireProfile(
        name="competitive_ff",
        sens_x=1.85,
        sens_y=3.60,
        smoothing=True,
        alpha=0.75,
        invert_y=False,
        suspend_key="KEY_F1",
        screen_width=1440,
        screen_height=1080,
        camera_anchor=(0.60, 0.50),
        camera_radius=0.22,
        fire_button_pos=(0.82, 0.70),
    )

    saved_path = profile.save(profile_path)
    assert saved_path == profile_path
    assert profile_path.exists()

    loaded = WayFireProfile.load(profile_path)
    assert loaded.name == "competitive_ff"
    assert loaded.sens_x == 1.85
    assert loaded.sens_y == 3.60
    assert loaded.screen_width == 1440
    assert loaded.screen_height == 1080
    assert loaded.camera_anchor == (0.60, 0.50)
    assert loaded.fire_button_pos == (0.82, 0.70)


def test_profile_load_fallback_to_defaults(tmp_path: Path) -> None:
    """Verify that non-existent or corrupted files fall back to standard defaults."""
    non_existent = tmp_path / "does_not_exist.json"
    profile = WayFireProfile.load(non_existent)

    assert profile.name == "default_freefire"
    assert profile.sens_x == 1.45
    assert profile.sens_y == 3.20

    # Test corrupted JSON recovery
    corrupted = tmp_path / "corrupted.json"
    corrupted.write_text("{ broken json content", encoding="utf-8")
    recovered = WayFireProfile.load(corrupted)
    assert recovered.name == "default_freefire"
