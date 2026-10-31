"""Main command-line interface implementation for WayFire."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Optional

from evdev import InputDevice, ecodes
from wayfire.config.profile import WayFireProfile
from wayfire.core.aim_engine import AimEngine, AimProcessor
from wayfire.core.mouse_capture import InputCaptureManager, detect_input_devices
from wayfire.core.touch_injector import TouchInjector
from wayfire.ui.terminal_hud import TerminalHUD


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
    profile_path = Path(args.profile) if args.profile else None
    profile = WayFireProfile.load(profile_path)

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

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    """CLI application entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        return cmd_run(args)
    if args.command == "test":
        return cmd_test(args)

    return 0


if __name__ == "__main__":
    sys.exit(main())
