"""Asynchronous game session coordinator and motor lifecycle manager.

Orchestrates the 5-step supervised boot sequence (container, resolution, spoofing,
Waydroid graphics session, and Free Fire launch), manages high-priority evdev input
threads (<1ms), coordinates live sensitivity hot-reloads, and ensures strict kernel
resource cleanup on termination (D-05..D-08, D-15, MAP-03, UI-03).
"""

from __future__ import annotations

from enum import Enum
import logging
import threading
import time
from typing import Any, Callable, Optional

import evdev
import gi

gi.require_version("GLib", "2.0")
from gi.repository import GLib

from wayfire.config.profile import WayFireProfile
from wayfire.config.profile_manager import ProfileManager
from wayfire.core.aim_engine import AimEngine, AimProcessor
from wayfire.core.keymap_engine import KeymapEngine
from wayfire.core.mouse_capture import InputCaptureManager, detect_input_devices
from wayfire.core.touch_injector import TouchInjector
from wayfire.ui.key_codes import EVDEV_TO_CANONICAL
from wayfire.waydroid.controller import WaydroidController

logger = logging.getLogger(__name__)


class SessionState(str, Enum):
    """High-level game session lifecycle states."""

    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"


class GameSessionCoordinator:
    """Supervises and coordinates Waydroid, uinput, evdev motors and overlay."""

    def __init__(
        self,
        profile_manager: Optional[ProfileManager] = None,
        waydroid_controller: Optional[WaydroidController] = None,
        injector_factory: Optional[Callable[[int, int], TouchInjector]] = None,
        device_detector: Optional[Callable[..., tuple[Optional[str], Optional[str]]]] = None,
        overlay_factory: Optional[Callable[..., Any]] = None,
        sync_callbacks: bool = False,
    ) -> None:
        self.profile_manager: ProfileManager = (
            profile_manager if profile_manager is not None else ProfileManager()
        )
        self.waydroid_controller: WaydroidController = (
            waydroid_controller if waydroid_controller is not None else WaydroidController()
        )
        self.injector_factory: Callable[[int, int], TouchInjector] = (
            injector_factory if injector_factory is not None else (lambda w, h: TouchInjector(width=w, height=h))
        )
        self.device_detector: Callable[..., tuple[Optional[str], Optional[str]]] = (
            device_detector if device_detector is not None else detect_input_devices
        )
        self.overlay_factory: Optional[Callable[..., Any]] = overlay_factory
        self.sync_callbacks: bool = sync_callbacks

        self.state: SessionState = SessionState.STOPPED
        self.active_profile: WayFireProfile = self.profile_manager.get_active_profile()
        self.current_package: Optional[str] = None

        # Threading controls
        self.worker_thread: Optional[threading.Thread] = None
        self.input_thread: Optional[threading.Thread] = None
        self.stop_event: threading.Event = threading.Event()

        # Engine instances
        self.injector: Optional[TouchInjector] = None
        self.aim_processor: Optional[AimProcessor] = None
        self.aim_engine: Optional[AimEngine] = None
        self.keymap_engine: Optional[KeymapEngine] = None
        self.capture_manager: Optional[InputCaptureManager] = None
        self.overlay_window: Optional[Any] = None

        # Observability callbacks
        self.on_state_change: Optional[Callable[[SessionState, str], None]] = None
        self.on_progress: Optional[Callable[[int, int, str], None]] = None

    def _emit_state_change(self, message: str) -> None:
        """Notify state change listener, marshaling to GTK thread if needed."""
        if self.on_state_change is not None:
            if self.sync_callbacks:
                self.on_state_change(self.state, message)
            else:
                cb = self.on_state_change
                st = self.state

                def _call() -> bool:
                    cb(st, message)
                    return False

                GLib.idle_add(_call)

    def _notify_progress(self, step: int, total: int, message: str) -> None:
        """Notify boot step progress (e.g. 1/5, 2/5), marshaling to GTK thread if needed."""
        if self.on_progress is not None:
            if self.sync_callbacks:
                self.on_progress(step, total, message)
            else:
                cb = self.on_progress

                def _call() -> bool:
                    cb(step, total, message)
                    return False

                GLib.idle_add(_call)

    def _resolve_key_code(self, key: str | int) -> int:
        """Resolve profile key name or string to evdev integer key code."""
        if isinstance(key, int):
            return key
        if hasattr(evdev.ecodes, str(key)):
            return getattr(evdev.ecodes, str(key))
        if hasattr(evdev.ecodes, f"KEY_{str(key).upper()}"):
            return getattr(evdev.ecodes, f"KEY_{str(key).upper()}")
        for code, name in EVDEV_TO_CANONICAL.items():
            if name.upper() == str(key).upper():
                return code
        return evdev.ecodes.KEY_F1

    def start_session_async(
        self,
        package: Optional[str] = None,
        stretched: bool = False,
        enable_overlay: bool = True,
        on_completed: Optional[Callable[[bool, Optional[str]], None]] = None,
    ) -> None:
        """Asynchronously trigger the 5-step supervised boot sequence."""
        if self.state != SessionState.STOPPED:
            raise RuntimeError("Sessão já em andamento")

        self.state = SessionState.STARTING
        self.stop_event.clear()
        self._emit_state_change("Iniciando sessão do Free Fire...")

        self.worker_thread = threading.Thread(
            target=self._launch_worker,
            args=(package, stretched, enable_overlay, on_completed),
            name="WayFire-LaunchWorker",
            daemon=True,
        )
        self.worker_thread.start()

    def _launch_worker(
        self,
        package: Optional[str],
        stretched: bool,
        enable_overlay: bool,
        on_completed: Optional[Callable[[bool, Optional[str]], None]],
    ) -> None:
        """Worker thread executing the 5 supervised boot steps (D-07)."""
        try:
            # Reload fresh profile settings
            self.active_profile = self.profile_manager.get_active_profile()

            # Passo 1/5 (20%): Container validation
            self._notify_progress(1, 5, "Verificando contêiner Waydroid...")
            self.waydroid_controller.ensure_container_active()

            # Passo 2/5 (40%): Resolution setup
            self._notify_progress(2, 5, "Aplicando resolução de tela...")
            if stretched:
                width, height = (1440, 1080)
            else:
                width = int(self.active_profile.screen_width or 1920)
                height = int(self.active_profile.screen_height or 1080)
            self.waydroid_controller.set_resolution(width, height, restart_if_running=False)

            # Passo 3/5 (60%): ROG Phone 5 spoofing
            self._notify_progress(3, 5, "Aplicando spoofing ASUS ROG Phone 5 (120 FPS)...")
            self.waydroid_controller.apply_spoofing()

            # Passo 4/5 (80%): Waydroid graphics session
            self._notify_progress(4, 5, "Iniciando sessão gráfica do Waydroid...")
            self.waydroid_controller.start_session()

            # Passo 5/5 (100%): App launch & motor initialization
            self._notify_progress(5, 5, "Lançando Free Fire e inicializando motores...")
            pkg = self.waydroid_controller.detect_freefire_package(package)
            self.current_package = pkg
            self.waydroid_controller.launch_app(pkg)

            # 1. Multi-touch injector
            self.injector = self.injector_factory(width, height)

            # 2. Aim engine and smoothing processor
            self.aim_processor = AimProcessor(
                sens_x=self.active_profile.sens_x,
                sens_y=self.active_profile.sens_y,
                smoothing=self.active_profile.smoothing,
                alpha=getattr(self.active_profile, "alpha", 0.80),
                invert_y=self.active_profile.invert_y,
            )
            self.aim_engine = AimEngine(
                processor=self.aim_processor,
                screen_width=width,
                screen_height=height,
            )

            # 3. Keymap engine
            self.keymap_engine = KeymapEngine(
                profile=self.active_profile,
                injector=self.injector,
            )

            # 4. Input device detection and capture manager
            mouse_path, kbd_path = self.device_detector()
            mouse_dev = None
            kbd_dev = None
            if mouse_path:
                try:
                    mouse_dev = evdev.InputDevice(mouse_path)
                except Exception as e:
                    logger.warning("Falha ao abrir mouse %s: %s", mouse_path, e)
            if kbd_path:
                try:
                    kbd_dev = evdev.InputDevice(kbd_path)
                except Exception as e:
                    logger.warning("Falha ao abrir teclado %s: %s", kbd_path, e)

            suspend_code = self._resolve_key_code(self.active_profile.suspend_key)

            self.capture_manager = InputCaptureManager(
                mouse_dev=mouse_dev,
                keyboard_dev=kbd_dev,
                suspend_key=suspend_code,
            )

            # Connect callbacks
            self.capture_manager.on_lock_changed = self._on_lock_changed
            self.capture_manager.on_panic = self._on_panic
            self.capture_manager.on_mouse_move = self._on_mouse_move
            self.capture_manager.on_mouse_button = self._on_mouse_button
            self.capture_manager.on_keyboard_event = self._on_keyboard_event

            # Start input processing thread
            self.input_thread = threading.Thread(
                target=self._input_loop,
                name="WayFire-InputLoop",
                daemon=True,
            )
            self.input_thread.start()

            # 5. Overlay window if requested
            if enable_overlay:
                self._init_overlay()

            self.state = SessionState.RUNNING
            self._emit_state_change("Jogo em execução")

            if on_completed is not None:
                if self.sync_callbacks:
                    on_completed(True, None)
                else:
                    def _done() -> bool:
                        on_completed(True, None)
                        return False

                    GLib.idle_add(_done)

        except Exception as exc:
            logger.exception("Falha durante o boot supervisionado: %s", exc)
            self.cleanup_resources()
            self.state = SessionState.STOPPED
            self._emit_state_change(f"Erro ao iniciar: {exc}")

            if on_completed is not None:
                err_msg = str(exc)
                if self.sync_callbacks:
                    on_completed(False, err_msg)
                else:
                    def _fail() -> bool:
                        on_completed(False, err_msg)
                        return False

                    GLib.idle_add(_fail)

    def _init_overlay(self) -> None:
        """Initialize or show WayFireOverlayWindow on the GTK thread."""
        def _build() -> bool:
            try:
                if self.overlay_factory is not None:
                    self.overlay_window = self.overlay_factory(
                        profile=self.active_profile,
                        profile_manager=self.profile_manager,
                    )
                else:
                    from wayfire.ui.overlay import WayFireOverlayWindow

                    self.overlay_window = WayFireOverlayWindow(
                        profile=self.active_profile,
                        profile_manager=self.profile_manager,
                    )
                if hasattr(self.overlay_window, "present"):
                    self.overlay_window.present()
                elif hasattr(self.overlay_window, "show"):
                    self.overlay_window.show()
            except Exception as e:
                logger.warning("Não foi possível inicializar OverlayWindow: %s", e)
            return False

        if self.sync_callbacks:
            _build()
        else:
            GLib.idle_add(_build)

    def _input_loop(self) -> None:
        """Dedicated high-priority polling loop for evdev inputs and macro scheduling."""
        while not self.stop_event.is_set():
            if self.capture_manager is not None:
                self.capture_manager.poll_events(timeout=0.001)
            if self.keymap_engine is not None:
                self.keymap_engine.poll_tick()

    def _on_lock_changed(self, is_locked: bool) -> None:
        """Handle aim lock toggle (F1): recenter on lock, reset on suspension (D-09, D-10)."""
        if is_locked:
            if self.aim_engine is not None and self.injector is not None:
                self.aim_engine.start_aim(self.injector)
            if self.keymap_engine is not None:
                self.keymap_engine.recenter_dpad()
            if self.overlay_window is not None and hasattr(self.overlay_window, "set_mode"):
                try:
                    from wayfire.ui.overlay import OverlayMode

                    self.overlay_window.set_mode(OverlayMode.GAME_LOCKED)
                except Exception:
                    pass
        else:
            if self.aim_engine is not None and self.injector is not None:
                self.aim_engine.stop_aim(self.injector)
            if self.keymap_engine is not None:
                self.keymap_engine.reset_dpad()
            if self.overlay_window is not None and hasattr(self.overlay_window, "set_mode"):
                try:
                    from wayfire.ui.overlay import OverlayMode

                    self.overlay_window.set_mode(OverlayMode.MOUSE_FREE)
                except Exception:
                    pass

    def _on_panic(self) -> None:
        """Handle emergency double-tap F1 (<350ms): release all touches and recenter (D-11)."""
        if self.keymap_engine is not None:
            self.keymap_engine.panic_reset()
        if self.aim_processor is not None:
            self.aim_processor.reset_state()
        if self.aim_engine is not None and self.injector is not None:
            self.aim_engine.stop_aim(self.injector)
            if self.capture_manager is not None and self.capture_manager.is_aim_locked:
                self.aim_engine.start_aim(self.injector)

    def _on_mouse_move(self, dx: int, dy: int) -> None:
        """Feed relative mouse deltas to AimEngine."""
        if self.aim_engine is not None and self.injector is not None:
            self.aim_engine.process_mouse_move(self.injector, dx, dy)

    def _on_mouse_button(self, code: int, value: int) -> None:
        """Feed mouse button clicks to KeymapEngine."""
        if self.keymap_engine is not None:
            self.keymap_engine.handle_mouse_button(code, value)

    def _on_keyboard_event(self, code: int, value: int) -> None:
        """Feed keyboard presses/releases to KeymapEngine."""
        if self.keymap_engine is not None:
            self.keymap_engine.handle_key_event(code, value)

    def set_sensitivity(
        self,
        sens_x: Optional[float] = None,
        sens_y: Optional[float] = None,
    ) -> None:
        """Hot-reload sensitivity multipliers in real-time without restarting (D-08)."""
        if sens_x is not None:
            self.active_profile.sens_x = max(0.05, float(sens_x))
        if sens_y is not None:
            self.active_profile.sens_y = max(0.05, float(sens_y))

        if self.aim_processor is not None:
            self.aim_processor.set_sensitivity(sens_x, sens_y)

        self.profile_manager.save_profile(self.active_profile)

    def set_resolution_preset(self, width: int, height: int) -> bool:
        """Update active profile resolution and configure Waydroid container."""
        self.active_profile.screen_width = width
        self.active_profile.screen_height = height
        self.profile_manager.save_profile(self.active_profile)

        if self.aim_engine is not None:
            self.aim_engine.set_screen_dimensions(width, height)

        return self.waydroid_controller.set_resolution(width, height)

    def cleanup_resources(self) -> None:
        """Release all kernel inputs, mouse grabs, and background threads."""
        self.stop_event.set()

        if self.capture_manager is not None:
            try:
                self.capture_manager.cleanup()
            except Exception as e:
                logger.warning("Erro ao limpar capture_manager: %s", e)
            self.capture_manager = None

        if self.input_thread is not None and self.input_thread.is_alive():
            self.input_thread.join(timeout=2.0)
        self.input_thread = None

        if self.keymap_engine is not None:
            try:
                self.keymap_engine.panic_reset()
            except Exception:
                pass

        if self.injector is not None:
            try:
                self.injector.close()
            except Exception as e:
                logger.warning("Erro ao fechar injector: %s", e)
            self.injector = None

        if self.overlay_window is not None:
            try:
                win = self.overlay_window

                def _close() -> bool:
                    if hasattr(win, "destroy"):
                        win.destroy()
                    elif hasattr(win, "close"):
                        win.close()
                    return False

                if self.sync_callbacks:
                    _close()
                else:
                    GLib.idle_add(_close)
            except Exception:
                pass
            self.overlay_window = None

    def stop_session(self) -> bool:
        """Gracefully stop running game session and associated services (D-06)."""
        if self.state == SessionState.STOPPED:
            return True

        self.state = SessionState.STOPPING
        self._emit_state_change("Encerrando sessão...")

        self.cleanup_resources()

        if self.current_package:
            try:
                self.waydroid_controller.stop_app(self.current_package)
            except Exception as e:
                logger.warning("Erro ao parar app %s: %s", self.current_package, e)

        self.state = SessionState.STOPPED
        self._emit_state_change("Jogo finalizado")
        return True
