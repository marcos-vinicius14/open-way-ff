# Phase 2: Comunicação com Waydroid e Gerenciamento de Perfis - Research

**Researched:** 2026-10-31  
**Target Phase:** Phase 2: Comunicação com Waydroid e Gerenciamento de Perfis  
**Requirements Covered:** WAY-01, WAY-02, WAY-03, MAP-01  
**Context & Decisions:** [02-CONTEXT.md](file:///home/marcos/Projects/way-ff/.planning/phases/02-comunica-o-com-waydroid-e-gerenciamento-de-perfis/02-CONTEXT.md)

---

## 1. Architecture Overview

Phase 2 builds the orchestration layer connecting the Linux host with the Waydroid Android runtime, while establishing a robust, polymorphic configuration architecture for player profiles.

```
┌────────────────────────────────────────────────────────────────────────┐
│                        WayFire Host Application                        │
│                                                                        │
│   ┌────────────────────────────────┐  ┌────────────────────────────┐   │
│   │        ProfileManager          │  │     WaydroidController     │   │
│   │  (~/.config/wayfire/profiles/) │  │   (Subprocess / Host IPC)  │   │
│   │                                │  │                            │   │
│   │  - default_freefire.json       │  │  - Lifecycle & Session     │   │
│   │  - Polymorphic Widgets         │  │  - Stretched Resolution    │   │
│   │  - Schema Validation           │  │  - ASUS ROG Phone Spoofing │   │
│   │  - Phase 1 Migration Adapter   │  │  - App Launch & am stop    │   │
│   └───────────────┬────────────────┘  └──────────────┬─────────────┘   │
│                   │                                  │                 │
│                   ▼                                  ▼                 │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │                     WayFire Core Engine                        │   │
│   │                                                                │   │
│   │  - TouchInjector: dynamic dimensions (set_screen_dimensions)   │   │
│   │  - AimEngine: re-scaled normalized anchor/boundary coordinates │   │
│   │  - CLI: launch, stop, spoof, profile subcommands               │   │
│   └───────────────────────────────┬────────────────────────────────┘   │
└───────────────────────────────────┼────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                          Waydroid (Android)                            │
│                                                                        │
│   - systemctl is-active waydroid-container.service                     │
│   - waydroid session start/stop & status                               │
│   - waydroid prop set ro.product.* / persist.waydroid.*                │
│   - waydroid app launch com.dts.freefireth / max                       │
└────────────────────────────────────────────────────────────────────────┘
```

The phase spans two major modules:
1. **`wayfire.waydroid.controller.WaydroidController`**: Programmatic lifecycle controller for Waydroid session, service check, dynamic screen resolution (including competitive stretched 4:3 1440x1080 and 1024x768), hardware spoofing (ASUS ROG Phone 5), and direct app launching/stopping.
2. **`wayfire.config.profile_manager.ProfileManager` & `wayfire.config.widgets`**: Polymorphic typed widget models (`TapWidget`, `DPadWidget`, `AimWidget`, `FireWidget`), hierarchical profile schema, transparent migration for Phase 1 flat profiles, factory default profile (`default_freefire.json`), and CRUD operations with input sanitization.

---

## 2. Waydroid Controller & Subprocess Architecture

### 2.1 Waydroid CLI Mechanics & Status Protocol

Inspection of `/usr/lib/waydroid/tools/` reveals how Waydroid operates:

* **Session & Container Status (`waydroid status`)**:
  - When stopped:
    ```
    Session:	STOPPED
    Vendor type:	MAINLINE
    ```
  - When running:
    ```
    Session:	RUNNING
    Container:	RUNNING
    Vendor type:	MAINLINE
    IP address:	192.168.240.xx
    Session user:	user(1000)
    Wayland display:	wayland-1
    ```
  - Parsing strategy: regex match `r"^Session:\s*([A-Za-z]+)"` and `r"^Container:\s*([A-Za-z]+)"`. Both must equal `"RUNNING"` for full operational readiness.

* **Container Service Check (`systemctl is-active waydroid-container.service`)**:
  - Returns `active` (code 0) when running.
  - If inactive or failed, attempt `systemctl start waydroid-container.service` or `pkexec systemctl start waydroid-container.service`.
  - If permissions fail or user cancels pkexec, raise a descriptive error directing the user to run:  
    `sudo systemctl start waydroid-container.service`.
  - Fallback check: if `waydroid status` indicates `Container: RUNNING`, proceed even if systemctl is unavailable (essential for test environments, containerized dev environments, or custom init systems).

* **Session Lifecycle (`waydroid session start` & `stop`)**:
  - `waydroid session start` runs a blocking GLib mainloop in the foreground. It **must** be launched as an asynchronous background subprocess (`subprocess.Popen(["waydroid", "session", "start"])`).
  - Supervised readiness loop: poll `get_status()` every `0.5s` up to `30s` timeout until `Session: RUNNING`.
  - `waydroid session stop` sends a DBus Stop call to terminate the session.

* **Application Launch and Termination (`waydroid app launch` & `waydroid shell am force-stop`)**:
  - Launch: `waydroid app launch <package>`.
  - Termination (Decision D-04): `waydroid shell am force-stop <package>` stops Free Fire gracefully while leaving the Waydroid compositor session alive for rapid relaunch.
  - Full stop (`wayfire stop --full`): executes `waydroid shell am force-stop <package>` followed by `waydroid session stop`.

* **Smart Free Fire Package Detection (Decision D-03)**:
  - `waydroid app list` prints:
    ```
    Name: Free Fire
    packageName: com.dts.freefireth
    ```
  - Priority detection order:
    1. Explicit profile override (`profile.game_package`).
    2. Detection via `waydroid app list` (checking for `com.dts.freefiremax`, then `com.dts.freefireth`).
    3. Standard fallback: `com.dts.freefireth`.

### 2.2 Critical Discovery: Virtualenv Environment Sanitization

> [!CAUTION]
> `/usr/bin/waydroid` uses the shebang `#!/usr/bin/env python3`.  
> When WayFire runs inside a Python virtualenv (e.g., `.venv/bin/python3`), invoking `subprocess.run(["waydroid", ...])` will execute Waydroid using the virtualenv's Python binary. If the virtualenv lacks system packages (like `dbus` / `python-dbus`), Waydroid crashes immediately with:  
> `ModuleNotFoundError: No module named 'dbus'`!

**Mitigation in `WaydroidController`:**
All subprocess executions must sanitize the environment dictionary:
```python
def get_clean_env() -> dict[str, str]:
    env = os.environ.copy()
    # Strip virtualenv paths from PATH so /usr/bin/python3 is selected
    paths = [p for p in env.get("PATH", "").split(os.pathsep) if "venv" not in p and not os.path.exists(os.path.join(p, "activate"))]
    env["PATH"] = os.pathsep.join(paths)
    env.pop("VIRTUAL_ENV", None)
    env.pop("PYTHONHOME", None)
    env.pop("PYTHONPATH", None)
    return env
```
This guarantees Waydroid runs against system Python where `dbus` and `gbinder` are natively installed.

### 2.3 Resoluções Esticadas Competitivas (WAY-02, D-05, D-06, D-07)

Waydroid configures display size via Android system properties:
- `persist.waydroid.width`
- `persist.waydroid.height`

Presets:
| Preset | Dimensões | Proporção | Descrição Competitiva |
| :--- | :--- | :--- | :--- |
| `1080p` (Nativa) | `1920x1080` | 16:9 | Visual nativo padrão, máxima nitidez |
| `stretched` (Competitiva) | `1440x1080` | 4:3 | Padrão competitivo: alvos mais largos, puxada de capa facilitada |
| `stretched_light` | `1024x768` | 4:3 | Leve: para GPUs integradas ou máquinas modestas |

**Idempotency & Restart Logic:**
1. Check current `persist.waydroid.width` and `persist.waydroid.height` via `waydroid prop get`.
2. If already equal to target resolution: return `False` (zero delay, avoid restart).
3. If different:
   - Call `waydroid prop set persist.waydroid.width <w>`
   - Call `waydroid prop set persist.waydroid.height <h>`
   - If session is currently `RUNNING`, perform transparent restart: `waydroid session stop` -> wait for `STOPPED` -> `waydroid session start` in background -> wait for `RUNNING`.
   - Return `True`.

### 2.4 Hardware Spoofing (ASUS ROG Phone 5) (WAY-03, D-09, D-10, D-11, D-12)

Free Fire queries device model properties to unlock 90/120 FPS and "Ultra" graphics presets.

Target Properties:
```ini
ro.product.brand=asus
ro.product.manufacturer=asus
ro.product.model=ASUS_I005D
ro.product.name=ASUS_I005D
ro.product.device=ASUS_I005D
```

**Backup & Restore Flow:**
1. Default backup location: `~/.config/wayfire/device_backup.json`.
2. Check if spoofing is already applied:
   - If `waydroid prop get ro.product.model == "ASUS_I005D"`, return `True` immediately (zero overhead on game startup).
3. First-time apply:
   - Read current values of the 5 properties.
   - If `device_backup.json` does not exist, write the original values to `device_backup.json`.
   - Apply the 5 ROG Phone values via `waydroid prop set <prop> <value>`.
4. Restore flow (`wayfire spoof --restore`):
   - Read `device_backup.json`.
   - Write back each original property via `waydroid prop set`.

---

## 3. Dynamic Resolution Scaling in Core Engine (D-08)

To support arbitrary resolutions and on-the-fly switching between 16:9 (1920x1080) and 4:3 (1440x1080), the core engine requires dynamic dimension updates.

### 3.1 `TouchInjector`
Add `set_screen_dimensions(width: int, height: int) -> None`:
```python
def set_screen_dimensions(self, width: int, height: int) -> None:
    """Dynamically update screen boundary limits for touch clamping."""
    self.width = max(1, int(width))
    self.height = max(1, int(height))
```

### 3.2 `AimEngine`
Add `set_screen_dimensions(width: int, height: int) -> None`:
```python
def set_screen_dimensions(self, width: int, height: int) -> None:
    """Dynamically update active screen resolution and recalculate pixel anchor/radius."""
    self.screen_width = max(1, int(width))
    self.screen_height = max(1, int(height))
    self.anchor_px = (
        int(self.anchor_norm_x * self.screen_width),
        int(self.anchor_norm_y * self.screen_height),
    )
    self.radius_px = int(self.radius_norm * min(self.screen_width, self.screen_height))
    self.max_dist_sq = (self.radius_px * self.threshold_ratio) ** 2
    self.current_x = self.anchor_px[0]
    self.current_y = self.anchor_px[1]
```
All normalized coordinates ($X = pct\_x \times width$, $Y = pct\_y \times height$) recalculate instantly without restarting the input bridge loop.

---

## 4. Profile Schema & Profile Manager (MAP-01, D-13..D-16)

### 4.1 Hierarchical Schema Structure

Defined in `docs/KEYMAPPING.md` §3:
```json
{
  "profile_name": "Free Fire Competitivo",
  "game_package": "com.dts.freefireth",
  "resolution": {
    "width": 1440,
    "height": 1080
  },
  "mouse_settings": {
    "sensitivity_x": 1.45,
    "sensitivity_y": 3.20,
    "lock_hotkey": "Control_L",
    "smoothing": true,
    "alpha": 0.80,
    "invert_y": false
  },
  "ui_settings": {
    "show_keys_on_screen": true,
    "osd_opacity": 0.35
  },
  "widgets": [
    ...
  ]
}
```

### 4.2 Polymorphic Widget Models (`src/wayfire/config/widgets.py`)

Using a clean class hierarchy with type discrimination:

```python
class BaseWidget(ABC):
    id: str
    type: str

    @abstractmethod
    def to_dict(self) -> dict[str, Any]: ...

@dataclass
class TapWidget(BaseWidget):
    id: str
    key: str
    x: float | int
    y: float | int
    mode: str = "single"  # single, hold, turbo
    type: str = "tap"

@dataclass
class DPadWidget(BaseWidget):
    id: str
    x: float | int
    y: float | int
    radius: float | int = 90
    keys: dict[str, str] = field(default_factory=lambda: {"up": "W", "down": "S", "left": "A", "right": "D"})
    deadzone: float = 0.1
    type: str = "dpad"

@dataclass
class AimWidget(BaseWidget):
    id: str
    x: float | int
    y: float | int
    width: float | int = 400
    height: float | int = 400
    sensitivity_x: Optional[float] = None
    sensitivity_y: Optional[float] = None
    type: str = "aim"

@dataclass
class FireWidget(BaseWidget):
    id: str
    key: str = "Mouse_Left"
    x: float | int = 1280
    y: float | int = 620
    type: str = "fire"
```

**`WidgetFactory`:**
```python
class WidgetFactory:
    _REGISTRY: dict[str, type[BaseWidget]] = {
        "tap": TapWidget,
        "dpad": DPadWidget,
        "aim": AimWidget,
        "fire": FireWidget,
    }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BaseWidget:
        w_type = data.get("type")
        if not w_type or w_type not in cls._REGISTRY:
            raise ValueError(f"Unknown or missing widget type: {w_type}")
        # Validate required fields and instantiate
        ...
```

### 4.3 Phase 1 Backward Compatibility & Migration

Existing Phase 1 tests in `tests/test_config.py` and `tests/test_cli.py` construct `WayFireProfile(sens_x=..., screen_width=...)`.  
To prevent any regressions while migrating to the hierarchical format:

1. `WayFireProfile` provides properties for Phase 1 fields:
   - `sens_x` <-> `mouse_settings.sensitivity_x`
   - `sens_y` <-> `mouse_settings.sensitivity_y`
   - `screen_width` <-> `resolution.width`
   - `screen_height` <-> `resolution.height`
   - `suspend_key` <-> `mouse_settings.lock_hotkey`
   - `name` <-> `profile_name`
   - `camera_anchor`, `camera_radius`, `fire_button_pos` derived from/mapped to widgets.
2. `WayFireProfile.from_dict()` detects flat vs. nested formats:
   - If `"mouse_settings"` is absent but `"sens_x"` is present -> migrates flat dictionary to nested structure.
   - If `"resolution"` is absent but `"screen_width"` is present -> creates `ResolutionConfig(width=..., height=...)`.
   - If `"widgets"` is absent -> populates default widgets matching the flat anchor/fire coords.

### 4.4 Default Profile Factory (`default_freefire.json`) (D-15)

The factory default profile provides a turnkey competitive layout for 1440x1080:
- **AimController**: `aim_camera` (X=1050, Y=540, W=400, H=400)
- **DPad**: `movement_dpad` (X=260, Y=780, R=90, WASD)
- **FireButton**: `fire_button` (`Mouse_Left`, X=1280, Y=620)
- **Scope**: `scope_button` (`Mouse_Right`, X=1310, Y=420)
- **Jump**: `jump_button` (`Space`, X=1350, Y=720)
- **Crouch**: `crouch_button` (`c`, X=1220, Y=880)
- **Prone**: `prone_button` (`z`, X=1220, Y=960)
- **Reload**: `reload_button` (`r`, X=1180, Y=280)
- **Medkit**: `medkit_button` (`4`, X=200, Y=600)
- **Grenade**: `grenade_button` (`e`, X=400, Y=700)
- **Interact / Loot**: `interact_button` (`f`, X=1000, Y=400)
- **Weapons 1, 2, 3**: `weapon_1` (`1`), `weapon_2` (`2`), `weapon_3` (`3`)

### 4.5 `ProfileManager` Operations (D-16)

Storage structure:
- Directory: `~/.config/wayfire/profiles/`
- Active profile tracker: `~/.config/wayfire/active_profile` (stores plain name, e.g., `"default_freefire"`)
- Methods:
  - `list_profiles() -> list[str]`
  - `load_profile(name_or_path: str | Path) -> WayFireProfile`
  - `save_profile(profile: WayFireProfile, name: Optional[str] = None) -> Path`
  - `get_active_profile() -> WayFireProfile`
  - `set_active_profile(name: str) -> None`
  - `export_profile(name: str, target_path: Path | str) -> Path`
  - `import_profile(source_path: Path | str, name: Optional[str] = None) -> Path`
  - `delete_profile(name: str) -> bool`

**Security Sanitization:**
Importing and saving must sanitize filenames (`Path(name).stem` sanitized with `re.sub(r'[^a-zA-Z0-9_-]', '', name)`) to prevent directory traversal (`../../etc/shadow`).

---

## 5. Verification Architecture & Test Strategy

### 5.1 Test Harness Isolation (`CommandRunner` Protocol)

Just as Phase 1 decoupled `/dev/uinput` via `UInputSink` and `MockUInputSink`, `WaydroidController` must be decoupled from the system shell via `CommandRunner`:

```python
class CommandRunner(Protocol):
    def run(self, cmd: list[str], check: bool = False, capture_output: bool = True, text: bool = True, env: Optional[dict[str, str]] = None) -> subprocess.CompletedProcess[str]: ...
    def popen(self, cmd: list[str], env: Optional[dict[str, str]] = None, **kwargs: Any) -> subprocess.Popen[Any]: ...
```

A `MockCommandRunner` records executed commands and provides scripted responses for:
- `waydroid status` (Session: STOPPED vs RUNNING)
- `systemctl is-active waydroid-container.service` (active vs inactive)
- `waydroid prop get/set`
- `waydroid app list/launch`
- `waydroid shell am force-stop`

This enables 100% hermetic unit testing without requiring root access, systemd, or Waydroid installed in CI.

### 5.2 Verification Coverage Plan

1. **Waydroid Controller Tests (`tests/test_waydroid_controller.py`)**:
   - Status parsing for stopped, running, and error outputs.
   - Container check, start attempt, pkexec fallback, and error formatting.
   - Session start supervised polling (success within 3 attempts, timeout after 30s).
   - Idempotent resolution changes (no session restart when width/height match).
   - Dynamic resolution change triggering session restart when dimensions change.
   - Hardware spoofing:
     - Backup file created on first apply with original properties.
     - 5 ROG Phone properties set.
     - Re-apply skipped when `ro.product.model == ASUS_I005D`.
     - Restore correctly applies values from backup file.
   - Package detection (`com.dts.freefiremax` vs `com.dts.freefireth` vs manual override).
   - App stop via `waydroid shell am force-stop <package>` and full stop.

2. **Profile Manager & Widgets Tests (`tests/test_profile_manager.py`)**:
   - Polymorphic widget instantiation and serialization (`TapWidget`, `DPadWidget`, `AimWidget`, `FireWidget`).
   - `WidgetFactory.from_dict()` type dispatch and error raising on malformed widgets.
   - Backward compatibility: Phase 1 flat dictionary deserialization and attribute access.
   - Generation and verification of `default_freefire.json` (all 14 buttons present, valid coordinates).
   - Profile CRUD: list, load, save, set_active, get_active.
   - Import/export: round-trip consistency, directory traversal prevention (`../../../bad.json`).

3. **Core Engine Dynamic Scaling Tests (`tests/test_scaling.py`)**:
   - `TouchInjector.set_screen_dimensions(1440, 1080)` updates clamping bounds.
   - `AimEngine.set_screen_dimensions(1440, 1080)` correctly recalculates pixel anchor, radius, and max boundary distance.

4. **CLI Extension Tests (`tests/test_cli_phase2.py`)**:
   - Subcommand parsing for `launch`, `stop`, `spoof`, `profile`.
   - Execution paths for each subcommand mocked with `MockCommandRunner`.

---

## 6. Landmines & Pitfalls

| Landmine | Impact | Mitigation |
| :--- | :--- | :--- |
| **Virtualenv Python shebang pollution** | `waydroid` fails with `ModuleNotFoundError: No module named 'dbus'` when run inside virtualenv | `WaydroidController` strips `VIRTUAL_ENV` and virtualenv paths from `PATH` in `get_clean_env()`. |
| **Non-systemd environments** | `systemctl is-active` fails with `System has not been booted with systemd as init system` | Catch systemctl errors; fallback to checking `waydroid status` container state. |
| **Async session start race condition** | Launching game immediately after `waydroid session start` causes launch failure | Implement polling loop checking `waydroid status` until `Session: RUNNING` (timeout 30s). |
| **Session stopped when setting props** | `waydroid prop set` fails with `WayDroid session is stopped` | If session is not running when resolution/spoofing is applied, start session first or queue properties. |
| **Accidental backup overwrite** | Calling `apply_spoofing()` multiple times could overwrite original backup with `ASUS_I005D` | Check if backup file already exists before creating; check if current model is already `ASUS_I005D`. |
| **Phase 1 Profile regression** | Existing code/tests crash if `WayFireProfile` signature or fields change | Preserve all Phase 1 attributes via properties and adapt `from_dict()` for flat dicts. |
| **Path traversal in Profile import** | Untrusted profile filenames could write outside `~/.config/wayfire/profiles/` | Sanitize imported profile names using strict regex (`[a-zA-Z0-9_-]+`). |

---

## 7. Plan Slicing Recommendations

Based on phase requirements and dependencies, Phase 2 splits cleanly into 2 plans:

* **Plan 02-01: Waydroid Controller, Resoluções Esticadas e Spoofing ROG Phone**
  - Implement `CommandRunner` protocol & `MockCommandRunner`.
  - Implement `WaydroidController`:
    - `ensure_container_active()`, `get_status()`, `start_session()`, `stop_session()`, `restart_session()`.
    - `set_resolution()`, resolution presets (`1080p`, `1440x1080`, `1024x768`), idempotent check.
    - `apply_spoofing()`, `restore_spoofing()`, `~/.config/wayfire/device_backup.json`.
    - `detect_freefire_package()`, `launch_app()`, `stop_app()`.
  - Update `TouchInjector.set_screen_dimensions()` and `AimEngine.set_screen_dimensions()`.
  - CLI subcommands: `launch`, `stop`, `spoof`.
  - Unit tests in `tests/test_waydroid_controller.py`.

* **Plan 02-02: Profile Manager, Widgets Polimórficos e default_freefire.json**
  - Implement polymorphic widget hierarchy in `src/wayfire/config/widgets.py` (`BaseWidget`, `TapWidget`, `DPadWidget`, `AimWidget`, `FireWidget`, `WidgetFactory`).
  - Upgrade `WayFireProfile` in `src/wayfire/config/profile.py` with hierarchical schema and Phase 1 backward compatibility.
  - Implement `default_freefire.json` factory profile with complete 14-button competitive layout.
  - Implement `ProfileManager` in `src/wayfire/config/profile_manager.py` with CRUD, active profile tracking, and sanitization.
  - CLI subcommands: `profile list`, `profile active`, `profile show`, `profile import`, `profile export`.
  - Unit tests in `tests/test_profile_manager.py` and `tests/test_scaling.py`.

---
## RESEARCH COMPLETE
