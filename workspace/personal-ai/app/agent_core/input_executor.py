"""Input Executor Module.

Provides safe input execution with blocked pattern checking.
"""

from __future__ import annotations

# Blocked patterns
_BLOCKED_KEYS = {
    # System keys that should never be automated
    "Win",
    "Meta",
    "Super",
}

_BLOCKED_KEY_COMBOS = {
    # Dangerous key combinations
    ("Ctrl", "Alt", "Delete"),
    ("Ctrl", "Shift", "Escape"),
    ("Alt", "F4"),
    ("Ctrl", "Win", "D"),  # Show desktop
}

_BLOCKED_HOTKEY_PREFIXES = {
    "Ctrl+Alt+Del",
    "Alt+F4",
    "Win+",
}

_BLOCKED_TEXT_PATTERNS = [
    # Commands that could be dangerous
    "rm -rf",
    "del /s",
    "format ",
    "shutdown",
    "restart",
    "halt",
    "init 0",
    "init 6",
]


def is_blocked_key(key: str) -> bool:
    """Check if a key is blocked from automation.

    Args:
        key: Key name to check

    Returns:
        True if the key is blocked
    """
    if not key:
        return False

    key_clean = key.strip().title()

    # Check against blocked keys
    if key_clean in _BLOCKED_KEYS:
        return True

    return False


def is_blocked_hotkey(hotkey: str) -> bool:
    """Check if a hotkey combination is blocked.

    Args:
        hotkey: Hotkey string (e.g., "Ctrl+C")

    Returns:
        True if the hotkey is blocked
    """
    if not hotkey:
        return False

    hotkey_clean = hotkey.strip()

    # Check blocked prefixes
    for prefix in _BLOCKED_HOTKEY_PREFIXES:
        if hotkey_clean.lower().startswith(prefix.lower()):
            return True

    # Parse and check combinations
    parts = tuple(sorted(p.strip().title() for p in hotkey_clean.split("+")))
    if parts in _BLOCKED_KEY_COMBOS:
        return True

    return False


def is_blocked_text(text: str) -> bool:
    """Check if text contains blocked patterns.

    Args:
        text: Text to check

    Returns:
        True if text contains blocked patterns
    """
    if not text:
        return False

    text_lower = text.lower()

    for pattern in _BLOCKED_TEXT_PATTERNS:
        if pattern.lower() in text_lower:
            return True

    return False


def check_input_safety(
    key: str | None = None,
    hotkey: str | None = None,
    text: str | None = None,
) -> tuple[bool, str | None]:
    """Check input safety for multiple input types.

    Args:
        key: Optional key to check
        hotkey: Optional hotkey to check
        text: Optional text to check

    Returns:
        Tuple of (is_safe, reason_if_blocked)
    """
    if key and is_blocked_key(key):
        return False, f"Blocked key: {key}"

    if hotkey and is_blocked_hotkey(hotkey):
        return False, f"Blocked hotkey: {hotkey}"

    if text and is_blocked_text(text):
        return False, f"Blocked text pattern detected"

    return True, None


def add_blocked_key(key: str) -> None:
    """Add a key to the blocked list.

    Args:
        key: Key name to block
    """
    _BLOCKED_KEYS.add(key.strip().title())


def add_blocked_hotkey_prefix(prefix: str) -> None:
    """Add a hotkey prefix to the blocked list.

    Args:
        prefix: Hotkey prefix to block (e.g., "Win+")
    """
    _BLOCKED_HOTKEY_PREFIXES.add(prefix)


def add_blocked_text_pattern(pattern: str) -> None:
    """Add a text pattern to the blocked list.

    Args:
        pattern: Text pattern to block
    """
    _BLOCKED_TEXT_PATTERNS.append(pattern)