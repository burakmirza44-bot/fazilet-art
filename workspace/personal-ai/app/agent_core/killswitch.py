"""Killswitch Module.

Provides global stop mechanism for halting all agent operations.
"""

from __future__ import annotations

import threading

# Global stop flag
_stop_requested = threading.Event()


def request_global_stop() -> None:
    """Request a global stop of all agent operations."""
    _stop_requested.set()


def clear_global_stop() -> None:
    """Clear the global stop request."""
    _stop_requested.clear()


def is_global_stop_requested() -> bool:
    """Check if a global stop has been requested.

    Returns:
        True if stop has been requested
    """
    return _stop_requested.is_set()


class Killswitch:
    """Context manager for killswitch state."""

    def __init__(self, active: bool = True):
        """Initialize killswitch context.

        Args:
            active: Whether to activate killswitch on enter
        """
        self._active = active
        self._previous_state = False

    def __enter__(self) -> "Killswitch":
        """Enter context, optionally activating killswitch."""
        self._previous_state = is_global_stop_requested()
        if self._active:
            request_global_stop()
        return self

    def __exit__(self, *args) -> None:
        """Exit context, restoring previous state."""
        if not self._previous_state:
            clear_global_stop()