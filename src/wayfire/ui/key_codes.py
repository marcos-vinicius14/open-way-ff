"""Bidirectional key mappings, canonical schema names, and compact OSD labels.

Standardizes JSON profile keys (Space, Shift_L, Mouse_4) and compact HUD labels (SPC, SHF, M4)
while protecting reserved system hotkeys (F1, F2, F3) per D-14 and D-15.
"""

from __future__ import annotations

import evdev
from evdev import ecodes
import gi

gi.require_version("Gdk", "4.0")
from gi.repository import Gdk

RESERVED_SYSTEM_HOTKEYS = {"F1", "F2", "F3"}

# evdev key/button code -> canonical schema string
EVDEV_TO_CANONICAL: dict[int, str] = {
    # Alpha keys A-Z
    ecodes.KEY_A: "A",
    ecodes.KEY_B: "B",
    ecodes.KEY_C: "C",
    ecodes.KEY_D: "D",
    ecodes.KEY_E: "E",
    ecodes.KEY_F: "F",
    ecodes.KEY_G: "G",
    ecodes.KEY_H: "H",
    ecodes.KEY_I: "I",
    ecodes.KEY_J: "J",
    ecodes.KEY_K: "K",
    ecodes.KEY_L: "L",
    ecodes.KEY_M: "M",
    ecodes.KEY_N: "N",
    ecodes.KEY_O: "O",
    ecodes.KEY_P: "P",
    ecodes.KEY_Q: "Q",
    ecodes.KEY_R: "R",
    ecodes.KEY_S: "S",
    ecodes.KEY_T: "T",
    ecodes.KEY_U: "U",
    ecodes.KEY_V: "V",
    ecodes.KEY_W: "W",
    ecodes.KEY_X: "X",
    ecodes.KEY_Y: "Y",
    ecodes.KEY_Z: "Z",
    # Numeric row 0-9
    ecodes.KEY_0: "0",
    ecodes.KEY_1: "1",
    ecodes.KEY_2: "2",
    ecodes.KEY_3: "3",
    ecodes.KEY_4: "4",
    ecodes.KEY_5: "5",
    ecodes.KEY_6: "6",
    ecodes.KEY_7: "7",
    ecodes.KEY_8: "8",
    ecodes.KEY_9: "9",
    # Modifiers & Controls
    ecodes.KEY_SPACE: "Space",
    ecodes.KEY_LEFTSHIFT: "Shift_L",
    ecodes.KEY_RIGHTSHIFT: "Shift_R",
    ecodes.KEY_LEFTCTRL: "Control_L",
    ecodes.KEY_RIGHTCTRL: "Control_R",
    ecodes.KEY_LEFTALT: "Alt_L",
    ecodes.KEY_RIGHTALT: "Alt_R",
    ecodes.KEY_TAB: "Tab",
    ecodes.KEY_CAPSLOCK: "Caps_Lock",
    ecodes.KEY_ENTER: "Return",
    ecodes.KEY_ESC: "Escape",
    ecodes.KEY_BACKSPACE: "BackSpace",
    ecodes.KEY_DELETE: "Delete",
    # Function keys
    ecodes.KEY_F1: "F1",
    ecodes.KEY_F2: "F2",
    ecodes.KEY_F3: "F3",
    ecodes.KEY_F4: "F4",
    ecodes.KEY_F5: "F5",
    ecodes.KEY_F6: "F6",
    ecodes.KEY_F7: "F7",
    ecodes.KEY_F8: "F8",
    ecodes.KEY_F9: "F9",
    ecodes.KEY_F10: "F10",
    ecodes.KEY_F11: "F11",
    ecodes.KEY_F12: "F12",
    # Mouse Buttons
    ecodes.BTN_LEFT: "Mouse_Left",
    ecodes.BTN_RIGHT: "Mouse_Right",
    ecodes.BTN_MIDDLE: "Mouse_Middle",
    ecodes.BTN_SIDE: "Mouse_4",
    ecodes.BTN_EXTRA: "Mouse_5",
}

# Canonical name -> compact OSD label for HUD circles (D-14)
CANONICAL_TO_OSD: dict[str, str] = {
    "Space": "SPC",
    "Shift_L": "SHF",
    "Shift_R": "SHF",
    "Control_L": "CTL",
    "Control_R": "CTL",
    "Alt_L": "ALT",
    "Alt_R": "ALT",
    "Tab": "TAB",
    "Caps_Lock": "CPS",
    "Return": "ENT",
    "Enter": "ENT",
    "Escape": "ESC",
    "BackSpace": "DEL",
    "Delete": "DEL",
    "Mouse_Left": "LMB",
    "Mouse_Right": "RMB",
    "Mouse_Middle": "MMB",
    "Mouse_4": "M4",
    "Mouse_5": "M5",
}

GDK_KEYVAL_TO_CANONICAL: dict[int, str] = {
    Gdk.KEY_space: "Space",
    Gdk.KEY_Shift_L: "Shift_L",
    Gdk.KEY_Shift_R: "Shift_R",
    Gdk.KEY_Control_L: "Control_L",
    Gdk.KEY_Control_R: "Control_R",
    Gdk.KEY_Alt_L: "Alt_L",
    Gdk.KEY_Alt_R: "Alt_R",
    Gdk.KEY_Tab: "Tab",
    Gdk.KEY_Caps_Lock: "Caps_Lock",
    Gdk.KEY_Return: "Return",
    Gdk.KEY_Escape: "Escape",
    Gdk.KEY_BackSpace: "BackSpace",
    Gdk.KEY_Delete: "Delete",
}


def canonical_to_osd(key_name: str) -> str:
    """Return compact 1-3 char label for OSD HUD display, or uppercase name (D-14)."""
    if not key_name:
        return ""
    if key_name in CANONICAL_TO_OSD:
        return CANONICAL_TO_OSD[key_name]
    return key_name.upper()


def is_reserved_key(key_name: str) -> bool:
    """Check whether key_name is reserved for system control (F1, F2, F3) per D-15."""
    return key_name.upper() in RESERVED_SYSTEM_HOTKEYS


def keyval_to_canonical(keyval: int) -> str:
    """Convert Gdk keyval integer into canonical schema key name."""
    if keyval in GDK_KEYVAL_TO_CANONICAL:
        return GDK_KEYVAL_TO_CANONICAL[keyval]

    name = Gdk.keyval_name(keyval)
    if not name:
        return "?"

    if len(name) == 1:
        return name.upper()

    return name
