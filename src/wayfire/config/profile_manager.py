"""Profile manager providing CRUD operations, active profile selection, and secure serialization."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Optional

from wayfire.config.profile import WayFireProfile, create_default_profile


def sanitize_profile_name(name: str) -> str:
    """Sanitize and validate profile name to prevent directory traversal and injection."""
    if not name or not isinstance(name, str):
        raise ValueError("O nome do perfil não pode ser vazio.")

    # Extract stem to strip extensions or directory path prefixes
    stem = Path(name).stem
    clean = re.sub(r"[^a-zA-Z0-9_-]", "", stem)
    if not clean:
        raise ValueError(f"Nome de perfil inválido: '{name}'")
    return clean


class ProfileManager:
    """Manages storage, active profile selection, and import/export of WayFire profiles."""

    def __init__(
        self,
        profiles_dir: Optional[Path | str] = None,
        active_file: Optional[Path | str] = None,
    ) -> None:
        self.profiles_dir: Path = (
            Path(profiles_dir).resolve()
            if profiles_dir is not None
            else (Path.home() / ".config" / "wayfire" / "profiles").resolve()
        )
        self.active_file: Path = (
            Path(active_file).resolve()
            if active_file is not None
            else (Path.home() / ".config" / "wayfire" / "active_profile").resolve()
        )

        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        self.active_file.parent.mkdir(parents=True, exist_ok=True)

        # Seed factory default if no profiles exist
        json_profiles = list(self.profiles_dir.glob("*.json"))
        if not json_profiles:
            default_path = self.profiles_dir / "default_freefire.json"
            default_p = create_default_profile()
            default_p.save(default_path)

        # Seed active_file if missing or empty
        if not self.active_file.exists() or not self.active_file.read_text(encoding="utf-8").strip():
            self.active_file.write_text("default_freefire\n", encoding="utf-8")

    def get_profile_path(self, name: str) -> Path:
        """Resolve full sanitized filesystem path for profile name."""
        clean_name = sanitize_profile_name(name)
        target = (self.profiles_dir / f"{clean_name}.json").resolve()
        if not str(target).startswith(str(self.profiles_dir)):
            raise ValueError(f"Tentativa de path traversal detectada no perfil: '{name}'")
        return target

    def list_profiles(self) -> list[str]:
        """List all available profile names in alphabetical order without extension."""
        names = [p.stem for p in self.profiles_dir.glob("*.json")]
        return sorted(names)

    def load_profile(self, name_or_path: str | Path) -> WayFireProfile:
        """Load profile by name from profiles directory or directly from existing path."""
        p = Path(name_or_path)
        if p.is_file():
            return WayFireProfile.load(p)

        target = self.get_profile_path(str(name_or_path))
        if not target.exists():
            raise FileNotFoundError(f"Perfil '{name_or_path}' não encontrado em {self.profiles_dir}")

        return WayFireProfile.load(target)

    def save_profile(self, profile: WayFireProfile, name: Optional[str] = None) -> Path:
        """Save profile to profiles directory using provided name or profile's name."""
        chosen_name = name or profile.profile_name
        target_path = self.get_profile_path(chosen_name)
        profile.profile_name = target_path.stem
        return profile.save(target_path)

    def get_active_profile_name(self) -> str:
        """Read active profile name with fallback to default_freefire."""
        if not self.active_file.exists():
            return "default_freefire"

        try:
            content = self.active_file.read_text(encoding="utf-8").strip()
            if not content:
                return "default_freefire"
            clean = sanitize_profile_name(content)
            # Verify profile actually exists on disk
            if (self.profiles_dir / f"{clean}.json").exists():
                return clean
        except Exception:
            pass

        return "default_freefire"

    def set_active_profile(self, name: str) -> None:
        """Set active profile by name, validating that it exists on disk."""
        target = self.get_profile_path(name)
        if not target.exists():
            raise FileNotFoundError(f"Perfil '{name}' não encontrado em {self.profiles_dir}")

        self.active_file.write_text(f"{target.stem}\n", encoding="utf-8")

    def get_active_profile(self) -> WayFireProfile:
        """Load and return current active profile."""
        active_name = self.get_active_profile_name()
        return self.load_profile(active_name)

    def export_profile(self, name: str, target_path: str | Path) -> Path:
        """Export specified profile to external destination file."""
        profile = self.load_profile(name)
        dest = Path(target_path).resolve()
        dest.parent.mkdir(parents=True, exist_ok=True)
        return profile.save(dest)

    def import_profile(self, source_path: str | Path, name: Optional[str] = None) -> Path:
        """Import and validate external JSON profile into profiles directory."""
        src = Path(source_path).resolve()
        if not src.exists():
            raise FileNotFoundError(f"Arquivo de origem para importação não encontrado: {src}")

        with src.open("r", encoding="utf-8") as f:
            data = json.load(f)

        profile = WayFireProfile.from_dict(data)

        destination_name = sanitize_profile_name(name or profile.profile_name or src.stem)
        target_path = self.get_profile_path(destination_name)
        profile.profile_name = destination_name
        profile.save(target_path)
        return target_path

    def delete_profile(self, name: str) -> bool:
        """Delete custom profile file. Factory default profile cannot be deleted."""
        clean_name = sanitize_profile_name(name)
        if clean_name == "default_freefire":
            raise ValueError("O perfil padrão de fábrica 'default_freefire' não pode ser excluído.")

        target = self.get_profile_path(clean_name)
        if target.exists():
            target.unlink()
            # If deleted profile was active, reset active profile to default
            if self.get_active_profile_name() == clean_name:
                self.set_active_profile("default_freefire")
            return True

        return False
