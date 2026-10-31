"""Tests for canonical key code mappings and compact OSD labels."""

from __future__ import annotations

import gi
gi.require_version("Gdk", "4.0")
from gi.repository import Gdk

from wayfire.ui.key_codes import (
    canonical_to_osd,
    is_reserved_key,
    keyval_to_canonical,
)


def test_canonical_to_osd_conversions():
    """Verify conversion of canonical schema names to compact 1-3 char HUD labels (D-14)."""
    assert canonical_to_osd("Space") == "SPC"
    assert canonical_to_osd("Shift_L") == "SHF"
    assert canonical_to_osd("Control_L") == "CTL"
    assert canonical_to_osd("Alt_L") == "ALT"
    assert canonical_to_osd("Tab") == "TAB"
    assert canonical_to_osd("Caps_Lock") == "CPS"
    assert canonical_to_osd("Return") == "ENT"
    assert canonical_to_osd("Escape") == "ESC"
    assert canonical_to_osd("Mouse_4") == "M4"
    assert canonical_to_osd("Mouse_5") == "M5"
    assert canonical_to_osd("Mouse_Right") == "RMB"
    assert canonical_to_osd("Mouse_Left") == "LMB"
    assert canonical_to_osd("Mouse_Middle") == "MMB"

    # Regular single letter/number keys pass through in uppercase
    assert canonical_to_osd("e") == "E"
    assert canonical_to_osd("E") == "E"
    assert canonical_to_osd("1") == "1"


def test_is_reserved_key():
    """Verify system hotkeys F1, F2, F3 are detected as reserved per D-15."""
    assert is_reserved_key("F1") is True
    assert is_reserved_key("f1") is True
    assert is_reserved_key("F2") is True
    assert is_reserved_key("F3") is True

    # Other keys must not be blocked
    assert is_reserved_key("F4") is False
    assert is_reserved_key("Space") is False
    assert is_reserved_key("Mouse_4") is False
    assert is_reserved_key("E") is False


def test_keyval_to_canonical():
    """Verify Gdk keyval integers convert to standard canonical strings."""
    assert keyval_to_canonical(Gdk.KEY_space) == "Space"
    assert keyval_to_canonical(Gdk.KEY_Shift_L) == "Shift_L"
    assert keyval_to_canonical(Gdk.KEY_Control_L) == "Control_L"
    assert keyval_to_canonical(Gdk.KEY_Return) == "Return"
    assert keyval_to_canonical(Gdk.KEY_e) == "E"
    assert keyval_to_canonical(Gdk.KEY_1) == "1"
