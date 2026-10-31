"""Integrated log inspection dialog for WayFire desktop launcher."""

from __future__ import annotations

from typing import Optional

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Gdk", "4.0")
from gi.repository import Adw, Gdk, GLib, Gtk


class WayFireLogDialog(Adw.Window):
    """Modal dialog displaying runtime WayFire, Waydroid, and emulator logs."""

    def __init__(self, parent_window: Optional[Gtk.Window] = None) -> None:
        super().__init__()
        self.set_title("Logs do WayFire 🔥")
        self.set_default_size(700, 500)

        if parent_window is not None:
            self.set_transient_for(parent_window)
            self.set_modal(True)

        toolbar_view = Adw.ToolbarView()
        header = Adw.HeaderBar()

        self.copy_btn = Gtk.Button(label="📋 Copiar Logs")
        self.copy_btn.connect("clicked", self._on_copy_clicked)
        header.pack_end(self.copy_btn)

        toolbar_view.add_top_bar(header)

        self.text_view = Gtk.TextView(
            monospace=True,
            editable=False,
            wrap_mode=Gtk.WrapMode.WORD,
        )
        self.text_buffer: Gtk.TextBuffer = self.text_view.get_buffer()

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_child(self.text_view)
        toolbar_view.set_content(scrolled)

        self.set_content(toolbar_view)

    def append_log(self, text: str) -> None:
        """Append log message and automatically scroll to the bottom."""
        # Sanitize text per ASVS CWE-20
        clean_text = "".join(ch for ch in text if ch in "\n\t\r" or ch >= " ")
        end_iter = self.text_buffer.get_end_iter()
        self.text_buffer.insert(end_iter, clean_text)

        # Scroll to latest log entry
        mark = self.text_buffer.create_mark(None, self.text_buffer.get_end_iter(), False)
        self.text_view.scroll_to_mark(mark, 0.0, True, 0.0, 1.0)

    def get_logs_text(self) -> str:
        """Return complete text contents from the log buffer."""
        start = self.text_buffer.get_start_iter()
        end = self.text_buffer.get_end_iter()
        return self.text_buffer.get_text(start, end, False)

    def _on_copy_clicked(self, _btn: Gtk.Button) -> None:
        """Copy accumulated logs to the system clipboard."""
        logs = self.get_logs_text()
        display = Gdk.Display.get_default()
        if display is not None:
            clipboard = display.get_clipboard()
            clipboard.set(logs)
