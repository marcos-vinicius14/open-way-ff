# Phase 3: Editor Visual de Teclas (Overlay Wayland) - Pattern Mapping

**Phase:** 03 - editor-visual-de-teclas-overlay-wayland  
**Generated:** 2026-10-31  
**Status:** Ready for planning  
**Consumes:** `03-CONTEXT.md`, `03-RESEARCH.md`  
**Produces:** `03-PATTERNS.md` (Guidance for `03-PLAN.md`)

---

## 1. File Inventory & Classification

The following table catalogs all files to be created or modified in Phase 3, classified by architectural role, data flow model, and their closest existing analog in the codebase.

| File Path | Status | Role | Data Flow | Closest Existing Analog |
|---|---|---|---|---|
| `src/wayfire/config/widgets.py` | Modified | Config / Model | Static Data Model | `src/wayfire/config/widgets.py` |
| `src/wayfire/config/profile.py` | Modified | Config / Model | File I/O & Migration | `src/wayfire/config/profile.py` |
| `src/wayfire/ui/key_codes.py` | New | Utility | Pure Functional Lookup | `src/wayfire/core/mouse_capture.py` (ecodes lookup) |
| `src/wayfire/ui/debounce_saver.py` | New | Service | Debounced Timer Event | `src/wayfire/cli/main.py` (`handle_calibration_hotkey`) & `ProfileManager` |
| `src/wayfire/core/macro_scheduler.py` | New | Engine / Service | Non-Blocking Event Loop | `src/wayfire/core/aim_engine.py` (`AimProcessor` / `AimEngine`) |
| `src/wayfire/core/keymap_engine.py` | New | Engine / Controller | Event-Driven Dispatch | `src/wayfire/core/aim_engine.py` & `src/wayfire/core/mouse_capture.py` |
| `src/wayfire/ui/widget_views.py` | New | Component (GTK4) | UI Event Handling / CSS | `src/wayfire/ui/terminal_hud.py` (State-to-visual representation) |
| `src/wayfire/ui/overlay_canvas.py` | New | Component / Layout | Gestures & Focus Trapping | `src/wayfire/ui/terminal_hud.py` & `src/wayfire/config/widgets.py` |
| `src/wayfire/ui/floating_bar.py` | New | Component (GTK4) | User Control / Callback | `src/wayfire/ui/terminal_hud.py` |
| `src/wayfire/ui/overlay.py` | New | Controller / Window | Wayland Layer Shell / State | `src/wayfire/core/mouse_capture.py` (`InputCaptureManager`) |
| `src/wayfire/cli/main.py` | Modified | CLI / Entrypoint | Command Dispatch | `src/wayfire/cli/main.py` (`cmd_run`) |
| `tests/test_key_codes.py` | New | Test | Pure Unit Assertion | `tests/test_profile_manager.py` |
| `tests/test_macro_widget.py` | New | Test | Hermetic Mock Verification | `tests/test_aim_engine.py` & `tests/test_profile_manager.py` |
| `tests/test_debounce_saver.py` | New | Test | Timer / Mock GLib Callback | `tests/test_profile_manager.py` |
| `tests/test_keymap_engine.py` | New | Test | Multi-Touch Mock Sink | `tests/test_aim_engine.py` & `tests/test_touch_injector.py` |
| `tests/test_overlay_logic.py` | New | Test | Logic Isolation / Mock Shell | `tests/test_mouse_capture.py` |

---

## 2. Core Architectural Patterns to Replicate

### Pattern 1: Dataclass Modeling & Polymorphic Factory Pattern
**Origin:** [`src/wayfire/config/widgets.py`](file:///home/marcos/Projects/way-ff/src/wayfire/config/widgets.py#L10-L143)

All visual HUD elements derive from `BaseWidget` and register with `WidgetFactory`. Phase 3 adds `MacroStep` and `MacroWidget`.

#### Concrete Existing Pattern Excerpt
```python
# From src/wayfire/config/widgets.py
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
```

#### Adaptation for `MacroWidget` in Phase 3
1. Define `@dataclass class MacroStep` with `x`, `y`, `delay_ms: int = 30`.
2. Define `@dataclass class MacroWidget(BaseWidget)` with `key: str`, `steps: list[MacroStep]`, `delay_ms: int = 30`, `type: str = "macro"`.
3. Register `"macro": MacroWidget` in `WidgetFactory._REGISTRY`.
4. Parse `"steps"` in `WidgetFactory.from_dict` converting dictionaries into `MacroStep` instances.

---

### Pattern 2: Non-Blocking Scheduler & High-Performance Event Processing
**Origin:** [`src/wayfire/core/aim_engine.py`](file:///home/marcos/Projects/way-ff/src/wayfire/core/aim_engine.py#L13-L91)

No blocking calls (`time.sleep`) are permitted on the hot input path. `AimProcessor` uses accumulator states; similarly, `NonBlockingMacroScheduler` in `src/wayfire/core/macro_scheduler.py` uses monotonic timestamps (`time.monotonic()`) and remaining-queue processing.

#### Concrete Existing Pattern Excerpt
```python
# From src/wayfire/core/aim_engine.py
class AimProcessor:
    """Mathematical processor converting raw mouse deltas to scaled, smoothed aim movements."""

    def __init__(
        self,
        sens_x: float = 1.45,
        sens_y: float = 3.20,
        smoothing: bool = True,
        alpha: float = 0.80,
        invert_y: bool = False,
    ) -> None:
        self.sens_x: float = max(0.05, float(sens_x))
        self.sens_y: float = max(0.05, float(sens_y))
        # ... state variables ...
        self.acc_x: float = 0.0
        self.acc_y: float = 0.0

    def reset_state(self) -> None:
        """Reset internal accumulator and smoothing history."""
        self.prev_dx = 0.0
        self.prev_dy = 0.0
        self.acc_x = 0.0
        self.acc_y = 0.0
```

#### Adaptation for `NonBlockingMacroScheduler`
- Store queued tuples: `(fire_at_timestamp: float, action: str, slot: int, x: int, y: int)`.
- Method `trigger_macro(macro: MacroWidget)` allocates an available slot (range 4–9) and computes monotonic offsets without sleeping.
- Method `process_scheduled()` evaluates `time.monotonic() >= fire_at` inside the select/poll loop, executing actions and returning immediately.

---

### Pattern 3: Hermetic Mock Protocols for Hardware/Kernel Interfaces
**Origin:** [`src/wayfire/core/touch_injector.py`](file:///home/marcos/Projects/way-ff/src/wayfire/core/touch_injector.py#L10-L44) & [`tests/conftest.py`](file:///home/marcos/Projects/way-ff/tests/conftest.py#L1-L10)

Hardware dependencies (uinput, evdev, Wayland Layer Shell) must use runtime checkable `Protocol` or dependency injection to allow headless CI/CD testing without root permissions or physical screens.

#### Concrete Existing Pattern Excerpt
```python
# From src/wayfire/core/touch_injector.py
from typing import Protocol, runtime_checkable


@runtime_checkable
class UInputSink(Protocol):
    """Protocol abstraction for UInput device sink to allow hermetic testing."""

    def write(self, etype: int, code: int, value: int) -> None:
        """Write an input event."""
        ...

    def syn(self) -> None:
        """Synchronize input events."""
        ...

    def close(self) -> None:
        """Close the underlying device."""
        ...


class MockUInputSink(UInputSink):
    """Hermetic mock sink for unit testing without kernel uinput access."""

    def __init__(self) -> None:
        self.recorded_events: list[tuple[int, int, int]] = []
        self.syn_count: int = 0
        self.is_closed: bool = False

    def write(self, etype: int, code: int, value: int) -> None:
        self.recorded_events.append((etype, code, value))

    def syn(self) -> None:
        self.syn_count += 1

    def close(self) -> None:
        self.is_closed = True
```

#### Adaptation for Phase 3 Testing
- `TouchInjector` with `MockUInputSink` is reused to test `KeymapEngine` and `NonBlockingMacroScheduler`.
- GTK4 / Layer Shell interaction in `WayFireOverlayWindow` separates pure logic (coordinate transformations, unique instance checks, debounced saving) from PyGObject widgets so tests run without `Gdk.Display` segfaults.

---

### Pattern 4: Debounced Persistence & Atomic Profile I/O
**Origin:** [`src/wayfire/config/profile_manager.py`](file:///home/marcos/Projects/way-ff/src/wayfire/config/profile_manager.py#L85-L91) & [`src/wayfire/cli/main.py`](file:///home/marcos/Projects/way-ff/src/wayfire/cli/main.py#L46-L51)

Changes made in the visual editor must not hit the disk on every pixel of dragging. `ProfileDebounceSaver` in `src/wayfire/ui/debounce_saver.py` encapsulates this with `GLib.timeout_add(500, ...)`.

#### Concrete Existing Pattern Excerpt
```python
# From src/wayfire/config/profile_manager.py
def save_profile(self, profile: WayFireProfile, name: Optional[str] = None) -> Path:
    """Save profile to profiles directory using provided name or profile's name."""
    chosen_name = name or profile.profile_name
    target_path = self.get_profile_path(chosen_name)
    profile.profile_name = target_path.stem
    return profile.save(target_path)
```

```python
# From src/wayfire/cli/main.py
if changed:
    try:
        profile.save(profile_path)
    except OSError:
        pass
```

#### Adaptation for `ProfileDebounceSaver`
```python
class ProfileDebounceSaver:
    """Coalesces rapid visual edits into a single atomic profile save."""

    def __init__(self, profile_manager: ProfileManager, debounce_ms: int = 500) -> None:
        self.profile_manager = profile_manager
        self.debounce_ms = debounce_ms
        self._source_id: Optional[int] = None
        self._pending_profile: Optional[WayFireProfile] = None

    def request_save(self, profile: WayFireProfile) -> None:
        self._pending_profile = profile
        if self._source_id is not None:
            GLib.source_remove(self._source_id)
        self._source_id = GLib.timeout_add(self.debounce_ms, self._execute_save)

    def _execute_save(self) -> bool:
        if self._pending_profile is not None:
            try:
                self.profile_manager.save_profile(self._pending_profile)
            except OSError:
                pass
            self._pending_profile = None
        self._source_id = None
        return GLib.SOURCE_REMOVE

    def flush(self) -> None:
        if self._source_id is not None:
            GLib.source_remove(self._source_id)
            self._execute_save()
```

---

### Pattern 5: Input Capture Callback Registration & Mode Switching
**Origin:** [`src/wayfire/cli/main.py`](file:///home/marcos/Projects/way-ff/src/wayfire/cli/main.py#L145-L188)

`InputCaptureManager` uses explicit callback attributes (`on_mouse_move`, `on_mouse_button`, `on_hotkey`, `on_lock_changed`). `KeymapEngine` and `WayFireOverlayWindow` follow this exact callback-injection structure.

#### Concrete Existing Pattern Excerpt
```python
# From src/wayfire/cli/main.py
with InputCaptureManager(mouse_dev=mouse_dev, keyboard_dev=kbd_dev, suspend_key=suspend_key) as capture:
    capture.setup_signal_handlers()

    def _on_move(dx: int, dy: int) -> None:
        engine.update_aim(dx, dy, injector)
        # ...

    def _on_btn(code: int, value: int) -> None:
        engine.handle_mouse_button(code, value, injector)

    def _on_key(code: int) -> None:
        # Hotkey handler

    def _on_lock_change(locked: bool) -> None:
        if not locked:
            engine.stop_aim(injector)

    capture.on_mouse_move = _on_move
    capture.on_mouse_button = _on_btn
    capture.on_hotkey = _on_key
    capture.on_lock_changed = _on_lock_change
```

#### Adaptation for Phase 3
`KeymapEngine` attaches to `capture.on_key` and `capture.on_mouse_button`. When `F2` is detected, it triggers `overlay.toggle_edit_mode()`. When `F3` is detected, it triggers `overlay.toggle_osd_visibility()`. When `F1` toggles lock state, it informs `overlay.set_game_mode(suspended=not locked)`.

---

### Pattern 6: PyGObject / GTK4 Layer Shell & Cairo Region Pass-Through
**Origin:** Technical Research [`03-RESEARCH.md`](file:///home/marcos/Projects/way-ff/.planning/phases/03-editor-visual-de-teclas-overlay-wayland/03-RESEARCH.md#L187-L285)

Follows standard PyGObject boilerplate with version requirement calls before importing:

```python
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
try:
    gi.require_version("Gtk4LayerShell", "1.0")
    from gi.repository import Gtk4LayerShell
    HAS_LAYER_SHELL = True
except (ValueError, ImportError):
    HAS_LAYER_SHELL = False

from gi.repository import Adw, Gdk, GLib, Gtk
import cairo
```

#### Key Protocol Rules:
1. `Gtk4LayerShell.init_for_window(window)` MUST be called in `__init__` before the window is realized.
2. In Game Mode: `surface.set_input_region(cairo.Region())` (empty region = 100% pass-through).
3. In Suspended Mode: `surface.set_input_region(cairo.Region(pill_rect))` (only pill banner intercepts clicks).
4. In Edit Mode: `surface.set_input_region(None)` (entire screen captures input).

---

## 3. Detailed Component Pattern Catalog

### 3.1 `src/wayfire/ui/key_codes.py`
- **Pattern:** Bidirectional mapping dictionaries with fallback normalization.
- **Key mappings:**
  - `EVDEV_TO_CANONICAL`: maps `ecodes.KEY_*` and `ecodes.BTN_*` to canonical strings (`"Space"`, `"Shift_L"`, `"Mouse_4"`).
  - `CANONICAL_TO_OSD`: maps canonical strings to short HUD labels (`"SPC"`, `"SHF"`, `"CTL"`, `"M4"`).
  - `GDK_KEYVAL_TO_CANONICAL`: maps GDK keyvals to canonical strings during edit-mode key listening.
- **Helper functions:**
  - `is_reserved_key(key_name: str) -> bool`: returns `True` for `"F1"`, `"F2"`, `"F3"`, preventing accidental capture of system hotkeys.
  - `canonical_to_osd(key_name: str) -> str`: returns compact display label.

### 3.2 `src/wayfire/ui/widget_views.py`
- **Pattern:** Base visual class `BaseWidgetView(Gtk.Box)` encapsulating drag handling and selection state.
- **Specific Views:**
  - `TapWidgetView`: `Gtk.Box` or `Gtk.Button` with circular CSS styling (`border-radius: 50%`, 48x48px). Supports `.listening` pulsating animation and `.pressed` state.
  - `DPadWidgetView`: Drawing area or container showing center WASD cross and circular boundary with a resize drag handle.
  - `AimWidgetView`: Dashed rectangular frame with crosshair and corner resize handles. Contains contextual popover for sensitivity adjustments.
  - `FireWidgetView`: Dedicated button with trigger icon.
  - `MacroSequenceView`: Group of numbered badge sub-views linked by an identifier.
- **Popover Safety Rule:** Before removing a widget view from the canvas, always invoke `popover.unparent()` / `popover.popdown()` to prevent `Gtk-WARNING: Finalizing GtkButton ..., but it still has children left: GtkPopover`.

### 3.3 `src/wayfire/ui/overlay_canvas.py`
- **Pattern:** `Gtk.Fixed` subclass managing child coordinates and user interactions.
- **Gesture setup:**
  - `Gtk.GestureClick` with `gesture.set_button(0)`: detects single click (selection/drag start) and double click (`n_press == 2 and btn == 1` to create a new `TapWidget` in listening mode).
  - `Gtk.EventControllerKey`: captures key presses when a widget is in listening mode `[ ? ]` or handles `Delete`/`Backspace` to remove selected widgets.
- **Coordinate Normalization:**
  - Widgets store coordinates normalized to the profile resolution (e.g., 1440x1080).
  - Canvas maps between monitor pixel coordinates and profile coordinates using:
    $$x_{\text{canvas}} = \left(\frac{x_{\text{profile}}}{\text{profile.width}}\right) \times \text{window.width}$$
    $$y_{\text{canvas}} = \left(\frac{y_{\text{profile}}}{\text{profile.height}}\right) \times \text{window.height}$$

### 3.4 `src/wayfire/core/keymap_engine.py`
- **Pattern:** State machine dispatching evdev events to `TouchInjector` slots.
- **Slot allocation:**
  - Slot 0: Reserved exclusively for `AimEngine` (camera look).
  - Slot 1: Reserved exclusively for primary fire (`FireWidget`).
  - Slots 2–3: Reserved for dynamic taps / DPad directional touches.
  - Slots 4–9: Reserved for `NonBlockingMacroScheduler` sequences and multitouch buttons.
- **DPad Vector Math:**
  Given active pressed keys from `{up, down, left, right}`, compute normalized directional vector $(v_x, v_y)$, scale by `radius * (1.0 - deadzone)`, and dispatch touch coordinates centered at `(dpad.x, dpad.y)`.

---

## 4. Test Patterns & Fixtures

### Test Pattern 1: Polymorphic Widget Deserialization
**Origin:** [`tests/test_profile_manager.py:test_polymorphic_widgets_serialization`](file:///home/marcos/Projects/way-ff/tests/test_profile_manager.py#L23-L80)

```python
def test_macro_widget_serialization() -> None:
    """Ensure MacroWidget with steps serializes and deserializes via WidgetFactory."""
    macro = MacroWidget(
        id="combo_1",
        key="G",
        x=500,
        y=400,
        delay_ms=25,
        steps=[MacroStep(x=520, y=410, delay_ms=25), MacroStep(x=600, y=450, delay_ms=30)],
    )
    d = macro.to_dict()
    assert d["type"] == "macro"
    assert d["key"] == "G"
    assert len(d["steps"]) == 2

    restored = WidgetFactory.from_dict(d)
    assert isinstance(restored, MacroWidget)
    assert restored.id == "combo_1"
    assert len(restored.steps) == 2
    assert restored.steps[0].x == 520
```

### Test Pattern 2: Non-Blocking Scheduler Execution
**Origin:** [`tests/test_aim_engine.py`](file:///home/marcos/Projects/way-ff/tests/test_aim_engine.py#L85-L100) & [`tests/test_touch_injector.py`](file:///home/marcos/Projects/way-ff/tests/test_touch_injector.py)

```python
def test_macro_scheduler_dispatches_events_without_sleep(mock_sink: MockUInputSink) -> None:
    """Verify macro scheduler emits down and up events using monotonic time ticks."""
    injector = TouchInjector(sink=mock_sink, width=1920, height=1080)
    scheduler = NonBlockingMacroScheduler(injector=injector, slot_start=4, slot_end=9)

    macro = MacroWidget(
        id="m1",
        key="E",
        steps=[MacroStep(x=100, y=100, delay_ms=10), MacroStep(x=200, y=200, delay_ms=10)],
    )

    scheduler.trigger_macro(macro)
    assert len(scheduler.queue) > 0

    # Advance time ticks
    scheduler.process_scheduled()
    # Ensure uinput events were recorded without calling time.sleep
    assert mock_sink.recorded_events != []
```

### Test Pattern 3: Key Code Translation & Reserved Keys
```python
def test_key_code_canonical_and_reserved() -> None:
    """Ensure canonical translation and safety blocking of system keys."""
    assert canonical_to_osd("Space") == "SPC"
    assert canonical_to_osd("Shift_L") == "SHF"
    assert canonical_to_osd("Mouse_4") == "M4"
    assert is_reserved_key("F1") is True
    assert is_reserved_key("F2") is True
    assert is_reserved_key("F3") is True
    assert is_reserved_key("Space") is False
```

---

## 5. Anti-Patterns & Quality Traps to Avoid

| Anti-Pattern | Why It Fails in WayFire | Correct Architecture |
|---|---|---|
| **Blocking calls in input loop (`time.sleep`)** | Destroys the `<1ms` input latency guarantee; causes frame drops in Waydroid. | Use non-blocking event loops with `time.monotonic()` or `GLib.timeout_add`. |
| **Direct GTK widget instantiation in headless unit tests** | Segfaults with `SIGSEGV (code 139)` in Mesa/EGL when no Wayland/X11 display exists. | Isolate mathematical, mapping, and persistence logic into pure Python classes tested with mocks. Run visual tests with `xvfb-run` or check `Gdk.Display.get_default()`. |
| **Calling `Gtk4LayerShell.init_for_window` after realization** | Emits critical GLib warnings and fails to attach to the Wayland Layer Shell compositor. | Always call `init_for_window`, `set_layer`, and `set_anchor` in `__init__` before the window is mapped. |
| **Destroying widgets with attached `Gtk.Popover`** | Triggers `Gtk-WARNING: Finalizing GtkButton ..., but it still has children left: GtkPopover`. | Call `popover.unparent()` and `popover.popdown()` prior to removing widget views. |
| **Storing raw screen pixel coordinates in profile** | Breaks layout when running on different monitor resolutions or stretched 4:3 modes. | Always normalize coordinates against `profile.resolution` (`1440x1080`). |
| **Direct disk write on every mouse drag event** | Causes disk I/O thrashing and visual stutter. | Buffer changes with `ProfileDebounceSaver` (500ms debounce). |
| **Calling GTK UI updates directly from the evdev background thread** | Causes race conditions and memory corruption in GTK's main loop. | Marshal cross-thread GUI events using `GLib.idle_add(callback, *args)`. |

---

## 6. Implementation Quick Reference & Coding Rules

1. **Python 3.12 Standard:**
   - Every file must start with:
     ```python
     """Module docstring explaining responsibility."""
     from __future__ import annotations
     ```
   - Use strict typing annotations (`Optional`, `ClassVar`, `Callable`, `Protocol`).

2. **Language Separation:**
   - **Code & Comments:** English only (variable names, docstrings, internal comments).
   - **User Interface & Logs:** Brazilian Portuguese (toasts, CLI messages, HUD banners, error messages).

3. **Coordinate Systems:**
   - Always document whether coordinates are in:
     - `screen_px`: physical monitor pixels (e.g., 0..1920, 0..1080)
     - `profile_px`: profile resolution pixels (e.g., 0..1440, 0..1080)
     - `normalized`: floating point range (0.0 .. 1.0)

---

## PATTERN MAPPING COMPLETE
