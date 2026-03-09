"""Backend Selection Result Data Models.

Defines result structures for backend selection, including
selection status, bridge health, safety checks, and audit trail.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from time import perf_counter

from app.agent_core.backend_policy import BackendType


class SelectionStatus(str, Enum):
    """Status of a backend selection attempt."""

    SELECTED = "selected"  # Preferred backend was selected
    FALLBACK_USED = "fallback_used"  # Fallback backend was selected
    BLOCKED_SAFETY = "blocked_safety"  # Blocked by safety check
    BLOCKED_UNAVAILABLE = "blocked_unavailable"  # No backend available
    DRY_RUN_FORCED = "dry_run_forced"  # Dry run forced by policy


@dataclass(slots=True)
class BridgeHealthResult:
    """Result of a bridge health check."""

    healthy: bool
    host: str
    port: int
    ping_ms: float | None = None
    error: str | None = None
    cached: bool = False

    @property
    def is_available(self) -> bool:
        """Check if bridge is available for use."""
        return self.healthy


@dataclass(slots=True)
class SafetyCheckResult:
    """Result of safety validation checks."""

    passed: bool
    reason: str | None = None
    killswitch_active: bool = False
    wrong_window: bool = False
    blocked_input: bool = False

    @property
    def block_reason(self) -> str | None:
        """Get the reason for blocking, if any."""
        if self.passed:
            return None
        return self.reason


@dataclass(slots=True)
class BackendSelectionResult:
    """Result of backend selection with audit trail and metadata."""

    # Selection outcome
    selected_backend: BackendType
    status: SelectionStatus
    message: str

    # Audit trail
    requested_backend: BackendType
    attempted_backends: tuple[BackendType, ...] = ()
    rejected_backends: tuple[BackendType, ...] = ()

    # Safety
    safety_passed: bool = True
    safety_block_reason: str | None = None

    # Bridge health
    bridge_healthy: bool | None = None
    bridge_ping_ms: float | None = None

    # Metadata
    domain: str = ""
    selection_duration_ms: float = 0.0

    @property
    def is_executable(self) -> bool:
        """Check if the selected backend can execute actions.

        Returns:
            True if backend is not NONE and safety passed
        """
        return (
            self.selected_backend != BackendType.NONE
            and self.safety_passed
            and self.status not in (SelectionStatus.BLOCKED_SAFETY, SelectionStatus.BLOCKED_UNAVAILABLE)
        )

    @property
    def is_dry_run(self) -> bool:
        """Check if this is a dry-run selection.

        Returns:
            True if the selected backend is DRY_RUN
        """
        return self.selected_backend == BackendType.DRY_RUN

    @property
    def is_blocked(self) -> bool:
        """Check if selection was blocked.

        Returns:
            True if selection was blocked by safety or unavailability
        """
        return self.status in (SelectionStatus.BLOCKED_SAFETY, SelectionStatus.BLOCKED_UNAVAILABLE)

    @property
    def used_fallback(self) -> bool:
        """Check if a fallback backend was used.

        Returns:
            True if fallback was used instead of preferred backend
        """
        return self.status == SelectionStatus.FALLBACK_USED

    def to_dict(self) -> dict:
        """Convert result to dictionary for serialization.

        Returns:
            Dictionary representation of the result
        """
        return {
            "selected_backend": self.selected_backend.value,
            "status": self.status.value,
            "message": self.message,
            "requested_backend": self.requested_backend.value,
            "attempted_backends": [b.value for b in self.attempted_backends],
            "rejected_backends": [b.value for b in self.rejected_backends],
            "safety_passed": self.safety_passed,
            "safety_block_reason": self.safety_block_reason,
            "bridge_healthy": self.bridge_healthy,
            "bridge_ping_ms": self.bridge_ping_ms,
            "domain": self.domain,
            "selection_duration_ms": self.selection_duration_ms,
        }