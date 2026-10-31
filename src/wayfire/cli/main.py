"""Main command-line interface implementation for WayFire."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Optional

from evdev import InputDevice, ecodes
from wayfire.config.profile import WayFireProfile
from wayfire.config.profile_manager import ProfileManager
from wayfire.core.aim_engine import AimEngine, AimProcessor
from wayfire.core.mouse_capture import InputCaptureManager, detect_input_devices
from wayfire.core.touch_injector import TouchInjector
from wayfire.ui.terminal_hud import TerminalHUD
from wayfire.waydroid.controller import WaydroidController


def handle_calibration_hotkey(
    code: int,
    processor: AimProcessor,
    profile: WayFireProfile,
    profile_path: Optional[Path | str] = None,
) -> bool:
    """Adjust sensitivity in steps of 0.05 via F7..F10 hotkeys and persist to profile."""
    changed = False
    if code == ecodes.KEY_F7:
        processor.set_sensitivity(sens_x=round(processor.sens_x - 0.05, 2))
        profile.sens_x = processor.sens_x
        changed = True
    elif code == ecodes.KEY_F8:
        processor.set_sensitivity(sens_x=round(processor.sens_x + 0.05, 2))
        profile.sens_x = processor.sens_x
        changed = True
    elif code == ecodes.KEY_F9:
        processor.set_sensitivity(sens_y=round(processor.sens_y - 0.05, 2))
        profile.sens_y = processor.sens_y
        changed = True
    elif code == ecodes.KEY_F10:
        processor.set_sensitivity(sens_y=round(processor.sens_y + 0.05, 2))
        profile.sens_y = processor.sens_y
        changed = True

    if changed:
        try:
            profile.save(profile_path)
        except OSError:
            pass
    return changed


def cmd_test(args: argparse.Namespace) -> int:
    """Execute test subcommand diagnostics."""
    if args.devices:
        mouse_p, kbd_p = detect_input_devices()
        print(f"Auto-detected Physical Mouse:    {mouse_p or 'None'}")
        print(f"Auto-detected Physical Keyboard: {kbd_p or 'None'}")
        return 0

    if args.create_uinput:
        try:
            injector = TouchInjector()
            injector.close()
            print("SUCCESS: /dev/uinput virtual touchscreen created successfully.")
            return 0
        except PermissionError as exc:
            print(f"FAILED: {exc}", file=sys.stderr)
            return 1

    if args.interactive:
        hud = TerminalHUD()
        print("Starting interactive simulated HUD. Press Ctrl+C to exit.\n")
        try:
            for i in range(5):
                hud.render(is_locked=True, sens_x=1.45, sens_y=3.20, dx=i * 2, dy=i * 3, reset_count=i, force=True)
                time.sleep(0.05)
            hud.render(is_locked=False, sens_x=1.45, sens_y=3.20, force=True)
            print("\nSimulation completed successfully.")
            return 0
        except KeyboardInterrupt:
            return 0

    print("Use 'wayfire test --devices', '--create-uinput', or '--interactive'.")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    """Execute live input bridge and emulation loop."""
    if args.profile:
        profile_path = Path(args.profile)
        profile = WayFireProfile.load(profile_path)
    else:
        mgr = ProfileManager()
        profile = mgr.get_active_profile()
        profile_path = mgr.get_profile_path(profile.profile_name)

    width = args.width or profile.screen_width
    height = args.height or profile.screen_height

    mouse_path = args.mouse
    kbd_path = args.keyboard

    if not mouse_path or not kbd_path:
        detected_m, detected_k = detect_input_devices()
        mouse_path = mouse_path or detected_m
        kbd_path = kbd_path or detected_k

    if not mouse_path:
        print("ERROR: No physical mouse detected. Specify --mouse /dev/input/eventX", file=sys.stderr)
        return 1

    mouse_dev = InputDevice(mouse_path)
    kbd_dev = InputDevice(kbd_path) if kbd_path else None

    suspend_key = getattr(ecodes, profile.suspend_key, ecodes.KEY_F1)

    processor = AimProcessor(
        sens_x=profile.sens_x,
        sens_y=profile.sens_y,
        smoothing=profile.smoothing,
        alpha=profile.alpha,
        invert_y=profile.invert_y,
    )

    engine = AimEngine(
        processor=processor,
        screen_width=width,
        screen_height=height,
        anchor_norm_x=profile.camera_anchor[0],
        anchor_norm_y=profile.camera_anchor[1],
        radius_norm=profile.camera_radius,
        fire_button_norm=profile.fire_button_pos,
    )

    hud = TerminalHUD()

    try:
        injector = TouchInjector(width=width, height=height)
    except PermissionError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    with InputCaptureManager(mouse_dev=mouse_dev, keyboard_dev=kbd_dev, suspend_key=suspend_key) as capture:
        capture.setup_signal_handlers()

        def _on_move(dx: int, dy: int) -> None:
            engine.update_aim(dx, dy, injector)
            hud.render(
                is_locked=capture.is_aim_locked,
                sens_x=processor.sens_x,
                sens_y=processor.sens_y,
                dx=dx,
                dy=dy,
                reset_count=engine.reset_count,
            )

        def _on_btn(code: int, value: int) -> None:
            engine.handle_mouse_button(code, value, injector)

        def _on_key(code: int) -> None:
            if handle_calibration_hotkey(code, processor, profile, profile_path):
                hud.render(
                    is_locked=capture.is_aim_locked,
                    sens_x=processor.sens_x,
                    sens_y=processor.sens_y,
                    reset_count=engine.reset_count,
                    force=True,
                )

        def _on_lock_change(locked: bool) -> None:
            if not locked:
                engine.stop_aim(injector)
            hud.render(
                is_locked=locked,
                sens_x=processor.sens_x,
                sens_y=processor.sens_y,
                reset_count=engine.reset_count,
                force=True,
            )

        capture.on_mouse_move = _on_move
        capture.on_mouse_button = _on_btn
        capture.on_hotkey = _on_key
        capture.on_lock_changed = _on_lock_change

        hud.render(is_locked=False, sens_x=processor.sens_x, sens_y=processor.sens_y, force=True)

        try:
            while True:
                capture.poll_events(timeout=0.005)
        except KeyboardInterrupt:
            pass
        finally:
            injector.close()
            print("\nWayFire session terminated cleanly.")

    return 0


def cmd_launch(args: argparse.Namespace, controller: Optional[WaydroidController] = None) -> int:
    """Launch Free Fire with automated container readiness, resolution, and hardware spoofing."""
    ctrl = controller or WaydroidController()

    print("🔥 [WayFire] Verificando contêiner do Waydroid...")
    try:
        ctrl.ensure_container_active()
    except RuntimeError as exc:
        print(f"❌ [WayFire] Erro: {exc}", file=sys.stderr)
        return 1

    width = args.width
    height = args.height
    if args.stretched:
        width = 1440
        height = 1080

    if width is not None and height is not None:
        print(f"🖥️ [WayFire] Aplicando resolução {width}x{height}...")
        ctrl.set_resolution(width, height)

    if not args.no_spoof:
        print("⚡ [WayFire] Verificando spoofing ASUS ROG Phone 5 (120 FPS)...")
        ctrl.apply_spoofing()

    print("🚀 [WayFire] Inicializando sessão gráfica Waydroid...")
    try:
        ctrl.start_session()
    except TimeoutError as exc:
        print(f"❌ [WayFire] Erro: {exc}", file=sys.stderr)
        return 1

    pkg = ctrl.detect_freefire_package(args.package)
    print(f"🎯 [WayFire] Abrindo jogo ({pkg})...")
    if ctrl.launch_app(pkg):
        print("✅ [WayFire] Free Fire iniciado com sucesso!")
        return 0
    else:
        print(f"❌ [WayFire] Falha ao iniciar o pacote {pkg}.", file=sys.stderr)
        return 1


def cmd_stop(args: argparse.Namespace, controller: Optional[WaydroidController] = None) -> int:
    """Stop Free Fire application and optionally the entire Waydroid session."""
    ctrl = controller or WaydroidController()
    pkg = args.package or "com.dts.freefireth"

    if args.full:
        print(f"🛑 [WayFire] Encerrando {pkg} e desligando sessão Waydroid...")
        ctrl.stop_app(pkg, full=True)
        print("✅ [WayFire] Sessão e aplicativo encerrados.")
    else:
        print(f"🛑 [WayFire] Encerrando aplicativo {pkg}...")
        ctrl.stop_app(pkg, full=False)
        print("✅ [WayFire] Aplicativo finalizado. Sessão mantida ativa.")
    return 0


def cmd_spoof(args: argparse.Namespace, controller: Optional[WaydroidController] = None) -> int:
    """Manage hardware spoofing for unlocking 90/120 FPS in Free Fire."""
    ctrl = controller or WaydroidController()

    if args.restore:
        print("🔄 [WayFire] Restaurando propriedades originais do contêiner...")
        try:
            ctrl.restore_spoofing()
            print("✅ [WayFire] Propriedades originais restauradas com sucesso.")
            return 0
        except FileNotFoundError as exc:
            print(f"❌ [WayFire] Erro: {exc}", file=sys.stderr)
            return 1

    if args.apply:
        print("⚡ [WayFire] Forçando aplicação de spoofing ASUS ROG Phone 5...")
        ctrl.apply_spoofing()
        print("✅ [WayFire] Hardware ASUS ROG Phone 5 aplicado com sucesso.")
        return 0

    # Default or --status: display current spoofing state
    is_spoofed = ctrl.is_spoofing_applied()
    model = "ASUS_I005D (ROG Phone 5)" if is_spoofed else "Padrão / Desconhecido"
    status_str = "ATIVO (120 FPS liberado)" if is_spoofed else "INATIVO"
    print(f"📱 [WayFire] Modelo do Dispositivo: {model}")
    print(f"⚡ [WayFire] Status do Spoofing:     {status_str}")
    if ctrl.backup_path.exists():
        print(f"💾 [WayFire] Backup salvo em:        {ctrl.backup_path}")
    else:
        print("💾 [WayFire] Backup:                 Nenhum backup encontrado (nunca aplicado)")

    return 0


def cmd_profile(args: argparse.Namespace, manager: Optional[ProfileManager] = None) -> int:
    """Manage WayFire keymapping and configuration profiles."""
    mgr = manager or ProfileManager()

    if args.profile_action == "list":
        profiles = mgr.list_profiles()
        active = mgr.get_active_profile_name()
        print("📁 [WayFire] Perfis Instalados:")
        for p in profiles:
            marker = "* [ATIVO]" if p == active else " "
            print(f"  {marker:10} {p}")
        return 0

    if args.profile_action == "active":
        if args.set:
            try:
                mgr.set_active_profile(args.set)
                print(f"✅ [WayFire] Perfil ativo alterado para: {args.set}")
                return 0
            except (FileNotFoundError, ValueError) as exc:
                print(f"❌ [WayFire] Erro: {exc}", file=sys.stderr)
                return 1
        else:
            active = mgr.get_active_profile_name()
            print(f"⭐ [WayFire] Perfil ativo: {active}")
            return 0

    if args.profile_action == "show":
        name = args.name or mgr.get_active_profile_name()
        try:
            p = mgr.load_profile(name)
        except (FileNotFoundError, ValueError) as exc:
            print(f"❌ [WayFire] Erro: {exc}", file=sys.stderr)
            return 1

        print(f"📄 [WayFire] Perfil: {p.profile_name}")
        print(f"🎮 Pacote do Jogo:  {p.game_package}")
        print(f"🖥️ Resolução:       {p.resolution.width}x{p.resolution.height}")
        print(f"🎯 Sensibilidade X: {p.mouse_settings.sensitivity_x}")
        print(f"🎯 Sensibilidade Y: {p.mouse_settings.sensitivity_y}")
        print(f"🔒 Tecla de Trava:  {p.mouse_settings.lock_hotkey}")
        print(f"🧩 Widgets ({len(p.widgets)}):")
        for w in p.widgets:
            if hasattr(w, "key"):
                print(f"   - [{w.type.upper()}] {w.id}: Tecla='{w.key}' em ({w.x}, {w.y})")
            else:
                print(f"   - [{w.type.upper()}] {w.id} em ({w.x}, {w.y})")
        return 0

    if args.profile_action == "import":
        try:
            dest = mgr.import_profile(args.path, name=args.name)
            print(f"✅ [WayFire] Perfil importado com sucesso para: {dest}")
            return 0
        except Exception as exc:
            print(f"❌ [WayFire] Erro ao importar: {exc}", file=sys.stderr)
            return 1

    if args.profile_action == "export":
        try:
            dest = mgr.export_profile(args.name, args.path)
            print(f"✅ [WayFire] Perfil '{args.name}' exportado com sucesso para: {dest}")
            return 0
        except Exception as exc:
            print(f"❌ [WayFire] Erro ao exportar: {exc}", file=sys.stderr)
            return 1

    if args.profile_action == "delete":
        try:
            success = mgr.delete_profile(args.name)
            if success:
                print(f"✅ [WayFire] Perfil '{args.name}' excluído com sucesso.")
                return 0
            else:
                print(f"❌ [WayFire] Perfil '{args.name}' não encontrado.", file=sys.stderr)
                return 1
        except Exception as exc:
            print(f"❌ [WayFire] Erro ao excluir: {exc}", file=sys.stderr)
            return 1

    print("Use: wayfire profile list | active | show | import | export | delete")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build command-line parser."""
    parser = argparse.ArgumentParser(
        prog="wayfire",
        description="WayFire 🔥 - Native Linux input bridge for competitive Free Fire emulation",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subcommand: run
    run_parser = subparsers.add_parser("run", help="Start the live input bridge engine")
    run_parser.add_argument("--profile", type=str, help="Path to custom JSON profile")
    run_parser.add_argument("--mouse", type=str, help="Path to physical mouse device (/dev/input/event*)")
    run_parser.add_argument("--keyboard", type=str, help="Path to physical keyboard device (/dev/input/event*)")
    run_parser.add_argument("--width", type=int, help="Screen width in pixels")
    run_parser.add_argument("--height", type=int, help="Screen height in pixels")

    # Subcommand: test
    test_parser = subparsers.add_parser("test", help="Diagnose devices, permissions, and HUD")
    test_parser.add_argument("--devices", action="store_true", help="List detected physical devices")
    test_parser.add_argument("--create-uinput", action="store_true", help="Test uinput virtual device creation")
    test_parser.add_argument("--interactive", action="store_true", help="Run interactive TUI simulation")

    # Subcommand: launch
    launch_parser = subparsers.add_parser("launch", help="Start Waydroid and launch Free Fire optimized")
    launch_parser.add_argument("--package", type=str, help="Android package name (e.g., com.dts.freefireth)")
    launch_parser.add_argument("--width", type=int, help="Screen width in pixels")
    launch_parser.add_argument("--height", type=int, help="Screen height in pixels")
    launch_parser.add_argument("--stretched", action="store_true", help="Use competitive stretched 1440x1080 4:3")
    launch_parser.add_argument("--no-spoof", action="store_true", help="Skip ASUS ROG Phone 5 hardware spoofing")

    # Subcommand: stop
    stop_parser = subparsers.add_parser("stop", help="Stop Free Fire and optionally Waydroid session")
    stop_parser.add_argument("--package", type=str, help="Android package name to stop")
    stop_parser.add_argument("--full", action="store_true", help="Terminate full Waydroid graphics session")

    # Subcommand: spoof
    spoof_parser = subparsers.add_parser("spoof", help="Inspect and control ASUS ROG Phone 5 hardware spoofing")
    spoof_parser.add_argument("--status", action="store_true", help="Display current spoofing status")
    spoof_parser.add_argument("--apply", action="store_true", help="Force apply ASUS ROG Phone 5 properties")
    spoof_parser.add_argument("--restore", action="store_true", help="Restore original hardware properties from backup")

    # Subcommand: profile
    profile_parser = subparsers.add_parser("profile", help="Manage input mappings and configuration profiles")
    profile_subparsers = profile_parser.add_subparsers(dest="profile_action", required=True)

    # profile list
    profile_subparsers.add_parser("list", help="List all installed profiles")

    # profile active
    active_parser = profile_subparsers.add_parser("active", help="Show or set the currently active profile")
    active_parser.add_argument("--set", type=str, help="Set active profile by name")

    # profile show
    show_parser = profile_subparsers.add_parser("show", help="Display details of a profile")
    show_parser.add_argument("name", nargs="?", type=str, help="Name of profile to inspect (default: active)")

    # profile import
    import_parser = profile_subparsers.add_parser("import", help="Import external JSON profile")
    import_parser.add_argument("path", type=str, help="Path to JSON file to import")
    import_parser.add_argument("--name", type=str, help="Destination profile name")

    # profile export
    export_parser = profile_subparsers.add_parser("export", help="Export profile to a file")
    export_parser.add_argument("name", type=str, help="Name of profile to export")
    export_parser.add_argument("path", type=str, help="Destination file path")

    # profile delete
    delete_parser = profile_subparsers.add_parser("delete", help="Delete a custom profile")
    delete_parser.add_argument("name", type=str, help="Name of profile to delete")

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    """CLI application entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        return cmd_run(args)
    if args.command == "test":
        return cmd_test(args)
    if args.command == "launch":
        return cmd_launch(args)
    if args.command == "stop":
        return cmd_stop(args)
    if args.command == "spoof":
        return cmd_spoof(args)
    if args.command == "profile":
        return cmd_profile(args)

    return 0


if __name__ == "__main__":
    sys.exit(main())
