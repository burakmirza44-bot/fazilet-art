"""Window Guard Module.

Provides window focus validation for safe execution.
"""

from __future__ import annotations

from typing import Callable

# Platform-specific imports
try:
    import pygetwindow as gw

    _HAS_PYGETWINDOW = True
except ImportError:
    _HAS_PYGETWINDOW = False

# Fallback for platforms without pygetwindow
_window_title_getter: Callable[[], str | None] | None = None


def set_window_title_getter(getter: Callable[[], str | None]) -> None:
    """Set a custom window title getter function.

    Args:
        getter: Function that returns the active window title
    """
    global _window_title_getter
    _window_title_getter = getter


def get_active_window_title() -> str | None:
    """Get the title of the currently active window.

    Returns:
        Window title string or None if unable to determine
    """
    # Use custom getter if set
    if _window_title_getter:
        return _window_title_getter()

    # Try pygetwindow
    if _HAS_PYGETWINDOW:
        try:
            active = gw.getActiveWindow()
            if active:
                return active.title
        except Exception:
            pass

    # Platform-specific fallbacks
    try:
        import platform

        system = platform.system()

        if system == "Windows":
            import ctypes

            user32 = ctypes.windll.user32
            handle = user32.GetForegroundWindow()
            length = user32.GetWindowTextLengthW(handle)
            if length > 0:
                buffer = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(handle, buffer, length + 1)
                return buffer.value

        elif system == "Darwin":  # macOS
            # Would need AppKit or similar
            pass

        elif system == "Linux":
            # Would need xdotool or similar
            pass

    except Exception:
        pass

    return None


class WindowGuard:
    """Guard for validating window focus before execution."""

    def __init__(self, expected_hints: tuple[str, ...] = ()):
        """Initialize the window guard.

        Args:
            expected_hints: Tuple of window title hints to match
        """
        self._expected_hints = expected_hints

    def is_expected_window_active(self) -> bool:
        """Check if an expected window is currently active.

        Returns:
            True if active window matches any expected hint
        """
        if not self._expected_hints:
            return True  # No hints means always valid

        title = get_active_window_title()
        if not title:
            return False

        title_lower = title.lower()
        return any(hint.lower() in title_lower for hint in self._expected_hints)

    def wait_for_expected_window(self, timeout_seconds: float = 30.0) -> bool:
        """Wait for an expected window to become active.

        Args:
            timeout_seconds: Maximum time to wait

        Returns:
            True if expected window became active
        """
        import time

        start = time.monotonic()
        while (time.monotonic() - start) < timeout_seconds:
            if self.is_expected_window_active():
                return True
            time.sleep(0.1)

        return False

    def __enter__(self) -> "WindowGuard":
        """Enter context, validating window state."""
        return self

    def __exit__(self, *args) -> None:
        """Exit context."""
        pass