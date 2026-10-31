"""Asynchronous debounced save service for WayFire profiles.

Coalesces rapid visual editing events (e.g., continuous mouse dragging at 120-240Hz)
into a single atomic disk write after a 500ms quiet window (D-03).
"""

from __future__ import annotations

import logging
from typing import Optional

import gi

gi.require_version("GLib", "2.0")
from gi.repository import GLib

from wayfire.config.profile import WayFireProfile
from wayfire.config.profile_manager import ProfileManager

logger = logging.getLogger(__name__)


class ProfileDebounceSaver:
    """Coalesces profile save requests to prevent disk thrashing during visual editing."""

    def __init__(
        self,
        profile_manager: ProfileManager,
        debounce_ms: int = 500,
    ) -> None:
        self.profile_manager = profile_manager
        self.debounce_ms = debounce_ms
        self._source_id: Optional[int] = None
        self._pending_profile: Optional[WayFireProfile] = None
        self.save_count: int = 0

    def request_save(self, profile: WayFireProfile) -> None:
        """Schedule a save for the given profile after debounce_ms quiet time."""
        self._pending_profile = profile

        if self._source_id is not None:
            GLib.source_remove(self._source_id)
            self._source_id = None

        self._source_id = GLib.timeout_add(self.debounce_ms, self._execute_save)

    def _execute_save(self) -> bool:
        """Execute the pending save operation."""
        if self._pending_profile is not None:
            try:
                self.profile_manager.save_profile(self._pending_profile)
                self.save_count += 1
            except Exception as e:
                logger.error("Failed to debounced save profile '%s': %s", self._pending_profile.name, e)
            finally:
                self._pending_profile = None

        self._source_id = None
        return GLib.SOURCE_REMOVE

    def flush(self) -> None:
        """Immediately execute any pending save operation without waiting for timeout."""
        if self._source_id is not None:
            GLib.source_remove(self._source_id)
            self._source_id = None

        if self._pending_profile is not None:
            self._execute_save()

    @property
    def has_pending_save(self) -> bool:
        """Return True if a save is currently scheduled and pending."""
        return self._source_id is not None or self._pending_profile is not None
