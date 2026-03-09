"""Error Normalizer Module.

Provides normalized error types for consistent error handling across
different execution backends.
"""

from __future__ import annotations

from enum import Enum
from typing import Any


class NormalizedErrorType(str, Enum):
    """Normalized error types for consistent error handling."""

    # Bridge-related errors
    BRIDGE_UNAVAILABLE = "bridge_unavailable"
    BRIDGE_UNHEALTHY = "bridge_unhealthy"
    BRIDGE_TIMEOUT = "bridge_timeout"
    BRIDGE_CONNECTION_FAILED = "bridge_connection_failed"
    BRIDGE_PING_FAILED = "bridge_ping_failed"
    BRIDGE_INSPECT_FAILED = "bridge_inspect_failed"
    BRIDGE_COMMAND_REJECTED = "bridge_command_rejected"
    BRIDGE_RESPONSE_INVALID = "bridge_response_invalid"

    # Backend selection errors
    NO_SAFE_BACKEND = "no_safe_backend"
    UI_FALLBACK_BLOCKED = "ui_fallback_blocked"

    # Safety-related errors
    SAFETY_BLOCKED = "safety_blocked"
    KILLSWITCH_ACTIVE = "killswitch_active"
    WRONG_WINDOW_FOCUS = "wrong_window_focus"
    BLOCKED_INPUT = "blocked_input"

    # Execution errors
    EXECUTION_FAILED = "execution_failed"
    TIMEOUT = "timeout"
    INVALID_ACTION = "invalid_action"
    INVALID_PARAMS = "invalid_params"

    # Recipe errors
    RECIPE_INVALID = "recipe_invalid"
    STEP_FAILED = "step_failed"
    PRECONDITION_FAILED = "precondition_failed"

    # Checkpoint and recovery errors
    CHECKPOINT_MISSING = "checkpoint_missing"
    CHECKPOINT_INVALID = "checkpoint_invalid"
    CHECKPOINT_INCOMPATIBLE = "checkpoint_incompatible"
    CHECKPOINT_CORRUPT = "checkpoint_corrupt"
    RESUME_NOT_ALLOWED = "resume_not_allowed"
    RECOVERY_CONTEXT_INSUFFICIENT = "recovery_context_insufficient"
    REPLAY_REQUIRED_BUT_BLOCKED = "replay_required_but_blocked"
    CHECKPOINT_RESTORE_FAILED = "checkpoint_restore_failed"
    CHECKPOINT_STALE = "checkpoint_stale"
    UNSAFE_TO_RESUME = "unsafe_to_resume"

    # Unknown
    UNKNOWN = "unknown"


class NormalizedError:
    """Normalized error with consistent structure."""

    def __init__(
        self,
        error_type: NormalizedErrorType,
        message: str,
        original_error: Exception | None = None,
        context: dict[str, Any] | None = None,
    ):
        """Initialize a normalized error.

        Args:
            error_type: Type of the error
            message: Human-readable error message
            original_error: Optional original exception
            context: Optional additional context
        """
        self.error_type = error_type
        self.message = message
        self.original_error = original_error
        self.context = context or {}

    def __str__(self) -> str:
        """Return string representation."""
        return f"[{self.error_type.value}] {self.message}"

    def __repr__(self) -> str:
        """Return repr."""
        return f"NormalizedError({self.error_type.value!r}, {self.message!r})"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            "error_type": self.error_type.value,
            "message": self.message,
            "original_error": str(self.original_error) if self.original_error else None,
            "context": self.context,
        }

    @classmethod
    def from_exception(
        cls,
        exc: Exception,
        context: dict[str, Any] | None = None,
    ) -> "NormalizedError":
        """Create a normalized error from an exception.

        Args:
            exc: Exception to normalize
            context: Optional additional context

        Returns:
            NormalizedError instance
        """
        # Map common exceptions to types
        error_type = NormalizedErrorType.UNKNOWN

        exc_name = type(exc).__name__.lower()
        message = str(exc)

        if "timeout" in exc_name or "timeout" in message.lower():
            error_type = NormalizedErrorType.TIMEOUT
        elif "connection" in exc_name or "connection" in message.lower():
            error_type = NormalizedErrorType.BRIDGE_CONNECTION_FAILED

        return cls(
            error_type=error_type,
            message=message,
            original_error=exc,
            context=context,
        )


def normalize_error(
    error: Exception | NormalizedError | str,
    error_type: NormalizedErrorType = NormalizedErrorType.UNKNOWN,
    context: dict[str, Any] | None = None,
) -> NormalizedError:
    """Normalize an error to a consistent format.

    Args:
        error: Error to normalize
        error_type: Type to use if creating new error
        context: Optional additional context

    Returns:
        NormalizedError instance
    """
    if isinstance(error, NormalizedError):
        return error

    if isinstance(error, Exception):
        return NormalizedError.from_exception(error, context)

    if isinstance(error, str):
        return NormalizedError(error_type, error, context=context)

    return NormalizedError(
        NormalizedErrorType.UNKNOWN,
        str(error),
        context=context,
    )


def normalize_bridge_failure(
    bridge_type: str,
    failure_reason: str,
    error_code: str = "",
    host: str = "",
    port: int = 0,
    latency_ms: float = 0.0,
    original_error: Exception | None = None,
) -> NormalizedError:
    """Normalize a bridge failure to a consistent error format.

    Args:
        bridge_type: Type of bridge ("touchdesigner" | "houdini")
        failure_reason: Human-readable failure description
        error_code: Machine-readable error code
        host: Bridge host address
        port: Bridge port number
        latency_ms: Ping latency in milliseconds
        original_error: Optional original exception

    Returns:
        NormalizedError with bridge-specific context
    """
    # Map failure reasons to error types
    error_type = NormalizedErrorType.BRIDGE_UNAVAILABLE
    reason_lower = failure_reason.lower()

    if "ping" in reason_lower or "ping" in error_code.lower():
        error_type = NormalizedErrorType.BRIDGE_PING_FAILED
    elif "inspect" in reason_lower or "inspect" in error_code.lower():
        error_type = NormalizedErrorType.BRIDGE_INSPECT_FAILED
    elif "command" in reason_lower or "reject" in reason_lower:
        error_type = NormalizedErrorType.BRIDGE_COMMAND_REJECTED
    elif "timeout" in reason_lower:
        error_type = NormalizedErrorType.BRIDGE_TIMEOUT
    elif "invalid" in reason_lower or "malformed" in reason_lower:
        error_type = NormalizedErrorType.BRIDGE_RESPONSE_INVALID
    elif "unhealthy" in reason_lower:
        error_type = NormalizedErrorType.BRIDGE_UNHEALTHY
    elif "connection" in reason_lower:
        error_type = NormalizedErrorType.BRIDGE_CONNECTION_FAILED

    context = {
        "bridge_type": bridge_type,
        "error_code": error_code,
        "host": host,
        "port": port,
        "latency_ms": latency_ms,
        "timestamp": __import__("datetime").datetime.now().isoformat(),
    }

    return NormalizedError(
        error_type=error_type,
        message=f"[{bridge_type}] {failure_reason}",
        original_error=original_error,
        context=context,
    )


def normalize_checkpoint_failure(
    checkpoint_id: str,
    failure_reason: str,
    error_type: NormalizedErrorType = NormalizedErrorType.CHECKPOINT_INVALID,
    task_id: str = "",
    plan_id: str = "",
    original_error: Exception | None = None,
) -> NormalizedError:
    """Normalize a checkpoint failure to a consistent error format.

    Args:
        checkpoint_id: ID of the checkpoint involved
        failure_reason: Human-readable failure description
        error_type: Type of checkpoint error (default: CHECKPOINT_INVALID)
        task_id: Associated task ID
        plan_id: Associated plan ID
        original_error: Optional original exception

    Returns:
        NormalizedError with checkpoint-specific context
    """
    context = {
        "checkpoint_id": checkpoint_id,
        "task_id": task_id,
        "plan_id": plan_id,
        "timestamp": __import__("datetime").datetime.now().isoformat(),
    }

    return NormalizedError(
        error_type=error_type,
        message=f"[Checkpoint {checkpoint_id}] {failure_reason}",
        original_error=original_error,
        context=context,
    )