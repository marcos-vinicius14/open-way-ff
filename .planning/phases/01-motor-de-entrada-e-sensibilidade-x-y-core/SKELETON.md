# Walking Skeleton — WayFire 🔥

**Phase:** 1
**Generated:** 2026-10-31

## Capability Proven End-to-End

A player can move their physical mouse and press buttons to control Free Fire's camera rotation with independent X/Y sensitivity ("puxada de capa") and trigger shooting in Waydroid via a virtual multitouch touchscreen injected into Linux Kernel `/dev/uinput` with sub-1ms latency and continuous 360° rotation.

## Architectural Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Virtual Touchscreen Injection | Linux Kernel `/dev/uinput` with Multi-Touch Protocol Type B (`ABS_MT_SLOT` 0..9) & `INPUT_PROP_DIRECT` | Direct kernel-level touchscreen emulation eliminates the 150ms+ latency of ADB or Scrcpy, providing native sub-1ms response recognized directly by Wayland compositors and Waydroid. |
| Event Multiplexing | Synchronous `selectors.DefaultSelector` over Linux `epoll` descriptors | Avoids the GIL and scheduling jitter of `asyncio` coroutines, ensuring deterministic microsecond event handling on raw input packets. |
| Input Capture & Host Lockout Safety | `ioctl EVIOCGRAB` (`evdev.grab()`) with signal-safe `ungrab()` cleanup handlers and F1 toggle | Exclusively locks the mouse to prevent desktop cursor drift during gameplay, while guaranteeing instant restoration on F1 or process interruption (SIGINT/SIGTERM) to prevent host lockout. |
| Aim Sensitivity & Precision Engine | Independent $Sens_X$ / $Sens_Y$ scaling, EMA anti-jitter filter ($\alpha=0.8$), and fractional subpixel accumulator | Guarantees asymmetric vertical acceleration for Free Fire headshots ("puxada de capa") while preventing pixel skipping on high-DPI micro-aiming. |
| Camera Anti-Border Reset | 1ms atomic cycle (`UP` -> `1ms sleep` -> `DOWN` at anchor $(X_0, Y_0)$) triggered at 75% boundary | Prevents camera edge lockups and violent 180° reverse snaps by letting Android process touch release before re-anchoring. |
| Multitouch Slot Allocation | Slot 0 reserved for camera aim, Slots 1–9 allocated dynamically for action/fire buttons | Keeps continuous aim motion isolated from discrete HUD button touches and fire trigger events. |
| Interactive Terminal HUD | Native ANSI/VT100 in-place terminal rendering with F7–F10 on-the-fly calibration | Provides immediate visual feedback of aim lock state and sensitivity without heavy external dependencies. |
| Packaging & Module Layout | Modular `src/wayfire` package with PEP 621 `pyproject.toml` and CLI entry points | Structured for system-wide installation and Arch Linux / AUR packaging in later phases. |

## Stack Touched in Phase 1

- [x] Project scaffold (`pyproject.toml`, `pytest` test runner, modular `src/wayfire` package)
- [x] Kernel virtual input injection (`src/wayfire/core/touch_injector.py` via `/dev/uinput`)
- [x] Hardware input capture and F1 suspend hotkey (`src/wayfire/core/mouse_capture.py` via `/dev/input/event*`)
- [x] Aim mathematical engine with subpixel, EMA, and anti-border 1ms reset (`src/wayfire/core/aim_engine.py`)
- [x] Terminal HUD and CLI interactive runner (`src/wayfire/ui/terminal_hud.py`, `src/wayfire/cli/main.py`)
- [x] Configuration model and JSON profile persistence (`src/wayfire/config/profile.py`)

## Out of Scope (Deferred to Later Slices)

- Waydroid container lifecycle automation (`waydroid session start/stop`) (deferred to Phase 2)
- Competitive stretched resolution switching (1440x1080 / 1024x768) (deferred to Phase 2)
- ASUS ROG Phone hardware properties spoofing for 90/120 FPS (deferred to Phase 2)
- GTK4 / Layer Shell transparent overlay with floating icon and GG Mouse Pro visual editor (deferred to Phase 3)
- DPad analog anti-bug protection and GTK4 / Libadwaita launcher desktop GUI (deferred to Phase 4)
- One-command automated `install.sh` and Arch Linux AUR `PKGBUILD` (deferred to Phase 5)

## Subsequent Slice Plan

Each later phase adds one vertical slice on top of this skeleton without altering its architectural decisions:

- **Phase 2:** Container lifecycle orchestration, stretched resolution switching via Android system props, ROG Phone spoofing, and profile management.
- **Phase 3:** GTK4 / Layer Shell transparent overlay with interactive GG Mouse Pro style visual button creator and in-game OSD widget rendering.
- **Phase 4:** Desktop launcher in Libadwaita with 1-click launch, sensitivity sliders, and soft analog reset algorithm preventing character running lockup.
- **Phase 5:** System distribution with automated `install.sh`, udev permission rules for `/dev/uinput`, and Arch Linux `PKGBUILD`.
