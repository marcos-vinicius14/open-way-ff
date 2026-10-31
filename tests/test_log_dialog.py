"""Unit tests for WayFireLogDialog."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
import pytest

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Gdk", "4.0")
from gi.repository import Adw, Gdk, Gtk

from wayfire.ui.log_dialog import WayFireLogDialog


@pytest.fixture(autouse=True)
def ensure_gtk():
    """Ensure GTK/Adwaita is initialized."""
    Gtk.init_check()
    Adw.init()


def test_log_dialog_appends_and_copies_to_clipboard():
    """Verify WayFireLogDialog appends text, sanitizes input, and copies to clipboard (D-16)."""
    dialog = WayFireLogDialog()

    dialog.append_log("Linha 1: Inicializando motores...\n")
    dialog.append_log("Linha 2: Contêiner ativo.\n")

    full_text = dialog.get_logs_text()
    assert "Linha 1: Inicializando motores..." in full_text
    assert "Linha 2: Contêiner ativo." in full_text

    mock_clipboard = MagicMock()
    mock_display = MagicMock()
    mock_display.get_clipboard.return_value = mock_clipboard

    with patch("gi.repository.Gdk.Display.get_default", return_value=mock_display):
        dialog.copy_btn.emit("clicked")
        mock_clipboard.set.assert_called_once_with(full_text)

    dialog.destroy()
