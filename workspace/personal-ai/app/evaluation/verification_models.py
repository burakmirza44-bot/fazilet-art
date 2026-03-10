"""Post-Execution Verification Pipeline Models.

Provides dataclasses for defining expected state after action execution
and capturing verification results with evidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class AssertionType(str, Enum):
    """Types of verification assertions."""

    ELEMENT_VISIBLE = "element_visible"
    ELEMENT_GONE = "element_gone"
    PARAMETER_VALUE = "parameter_value"
    NODE_COUNT = "node_count"
    CONNECTION_COUNT = "connection_count"
    ERROR_OCCURRED = "error_occurred"
    DIALOG_STATE = "dialog_state"
    NETWORK_PATH = "network_path"
    SELECTION_CHANGED = "selection_changed"


class VerificationMethod(str, Enum):
    """Methods for verification."""

    VISUAL = "visual"  # Screenshot comparison
    STATE_QUERY = "state_query"  # Direct application query
    LOG_CHECK = "log_check"  # Check application logs
    HYBRID = "hybrid"  # Combined methods


@dataclass
class ExpectedState:
    """What should be true after action completes successfully.

    Used for post-execution verification to validate that actions
    actually produced the intended effects.

    Examples:
        # After creating a comp node
        expected = ExpectedState(
            new_elements_visible=["comp1"],
            node_count=1
        )

        # After setting parameter
        expected = ExpectedState(
            parameter_values={"blur1.amount": 5.0}
        )

        # After connecting nodes
        expected = ExpectedState(
            new_elements_visible=["connection blur1 → comp1"],
            connection_count=1
        )
    """

    # Visual expectations
    new_elements_visible: list[str] = field(default_factory=list)
    """Elements that should appear after action (e.g., ['comp1', 'null1'])."""

    removed_elements: list[str] = field(default_factory=list)
    """Elements that should disappear after action (e.g., ['dialog'])."""

    element_properties: dict[str, dict[str, Any]] = field(default_factory=dict)
    """Expected properties for elements (e.g., {'comp1': {'type': 'comp', 'connections': 1}})."""

    # Network/graph expectations
    node_count: Optional[int] = None
    """Expected number of nodes (e.g., 5 after 'create 3 nodes')."""

    connection_count: Optional[int] = None
    """Expected number of connections (e.g., 2 after 'make 2 connections')."""

    # Parameter expectations
    parameter_values: dict[str, Any] = field(default_factory=dict)
    """Expected parameter values (e.g., {'blur1.amount': 5.0})."""

    # Application state expectations
    active_network: Optional[str] = None
    """Expected active network path (e.g., '/obj' after 'navigate to /obj')."""

    dialog_open: Optional[str] = None
    """Expected dialog state - None if should be closed, name if should be open."""

    selection_changed: bool = False
    """True if selection should have changed after action."""

    # Error expectations (for negative cases)
    should_have_error: bool = False
    """True if action should produce an error (for negative testing)."""

    error_message_contains: Optional[str] = None
    """Expected error message content if should_have_error is True."""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "new_elements_visible": self.new_elements_visible,
            "removed_elements": self.removed_elements,
            "element_properties": self.element_properties,
            "node_count": self.node_count,
            "connection_count": self.connection_count,
            "parameter_values": self.parameter_values,
            "active_network": self.active_network,
            "dialog_open": self.dialog_open,
            "selection_changed": self.selection_changed,
            "should_have_error": self.should_have_error,
            "error_message_contains": self.error_message_contains,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExpectedState:
        """Create from dictionary."""
        return cls(
            new_elements_visible=data.get("new_elements_visible", []),
            removed_elements=data.get("removed_elements", []),
            element_properties=data.get("element_properties", {}),
            node_count=data.get("node_count"),
            connection_count=data.get("connection_count"),
            parameter_values=data.get("parameter_values", {}),
            active_network=data.get("active_network"),
            dialog_open=data.get("dialog_open"),
            selection_changed=data.get("selection_changed", False),
            should_have_error=data.get("should_have_error", False),
            error_message_contains=data.get("error_message_contains"),
        )

    def summary(self) -> str:
        """Get human-readable summary of expected state."""
        parts = []

        if self.new_elements_visible:
            parts.append(f"new: {', '.join(self.new_elements_visible)}")
        if self.removed_elements:
            parts.append(f"removed: {', '.join(self.removed_elements)}")
        if self.node_count is not None:
            parts.append(f"nodes: {self.node_count}")
        if self.connection_count is not None:
            parts.append(f"connections: {self.connection_count}")
        if self.parameter_values:
            parts.append(f"params: {len(self.parameter_values)}")
        if self.active_network:
            parts.append(f"network: {self.active_network}")
        if self.dialog_open is not None:
            parts.append(f"dialog: {self.dialog_open or 'closed'}")

        return " | ".join(parts) if parts else "No specific expectations"


@dataclass
class VerificationAssertion:
    """Single assertion to verify after action execution."""

    assertion_type: str
    """Type of assertion (element_visible, parameter_value, etc.)."""

    target: str
    """Target of assertion (element name, parameter path, etc.)."""

    expected_value: Any = None
    """Expected value for the assertion."""

    tolerance: float = 0.0
    """Tolerance for numerical values (e.g., 0.1 means 10% tolerance)."""

    timeout: float = 5.0
    """How long to wait for assertion to become true (seconds)."""

    verification_method: str = VerificationMethod.VISUAL.value
    """Method to use for verification."""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "assertion_type": self.assertion_type,
            "target": self.target,
            "expected_value": self.expected_value,
            "tolerance": self.tolerance,
            "timeout": self.timeout,
            "verification_method": self.verification_method,
        }


@dataclass
class AssertionResult:
    """Result of a single assertion check."""

    assertion_type: str
    target: str
    passed: bool
    expected: Any = None
    actual: Any = None
    evidence: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        """Set defaults."""
        if not self.timestamp:
            object.__setattr__(self, "timestamp", datetime.now().isoformat())

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "assertion_type": self.assertion_type,
            "target": self.target,
            "passed": self.passed,
            "expected": self.expected,
            "actual": self.actual,
            "evidence": self.evidence,
            "timestamp": self.timestamp,
        }


@dataclass
class VisualVerificationResult:
    """Result of visual verification (screenshot comparison)."""

    before_screenshot: str
    """Path to screenshot before action."""

    after_screenshot: str
    """Path to screenshot after action."""

    assertions_passed: list[dict[str, Any]] = field(default_factory=list)
    """List of passed assertions with evidence."""

    assertions_failed: list[dict[str, Any]] = field(default_factory=list)
    """List of failed assertions with evidence."""

    vlm_analysis: dict[str, Any] = field(default_factory=dict)
    """VLM analysis results from screenshot comparison."""

    verification_method: str = VerificationMethod.VISUAL.value
    confidence: float = 0.0
    timestamp: str = ""

    def __post_init__(self) -> None:
        """Set defaults."""
        if not self.timestamp:
            object.__setattr__(self, "timestamp", datetime.now().isoformat())

    @property
    def success(self) -> bool:
        """Check if visual verification passed."""
        return len(self.assertions_failed) == 0 and len(self.assertions_passed) > 0

    @property
    def total_assertions(self) -> int:
        """Get total number of assertions checked."""
        return len(self.assertions_passed) + len(self.assertions_failed)

    def summary(self) -> str:
        """Get human-readable summary."""
        status = "✓ PASS" if self.success else "✗ FAIL"
        return (
            f"{status} Visual: {len(self.assertions_passed)} passed, "
            f"{len(self.assertions_failed)} failed (confidence: {self.confidence:.0%})"
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "before_screenshot": self.before_screenshot,
            "after_screenshot": self.after_screenshot,
            "assertions_passed": self.assertions_passed,
            "assertions_failed": self.assertions_failed,
            "vlm_analysis": self.vlm_analysis,
            "verification_method": self.verification_method,
            "confidence": self.confidence,
            "success": self.success,
            "timestamp": self.timestamp,
        }


@dataclass
class StateQueryVerificationResult:
    """Result of state query verification (direct application query)."""

    assertions_passed: list[dict[str, Any]] = field(default_factory=list)
    """List of passed assertions with evidence."""

    assertions_failed: list[dict[str, Any]] = field(default_factory=list)
    """List of failed assertions with evidence."""

    queried_state: dict[str, Any] = field(default_factory=dict)
    """Raw state data queried from application."""

    verification_method: str = VerificationMethod.STATE_QUERY.value
    confidence: float = 0.0
    timestamp: str = ""

    def __post_init__(self) -> None:
        """Set defaults."""
        if not self.timestamp:
            object.__setattr__(self, "timestamp", datetime.now().isoformat())

    @property
    def success(self) -> bool:
        """Check if state query verification passed."""
        return len(self.assertions_failed) == 0 and len(self.assertions_passed) > 0

    @property
    def total_assertions(self) -> int:
        """Get total number of assertions checked."""
        return len(self.assertions_passed) + len(self.assertions_failed)

    def summary(self) -> str:
        """Get human-readable summary."""
        status = "✓ PASS" if self.success else "✗ FAIL"
        return (
            f"{status} State Query: {len(self.assertions_passed)} passed, "
            f"{len(self.assertions_failed)} failed (confidence: {self.confidence:.0%})"
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "assertions_passed": self.assertions_passed,
            "assertions_failed": self.assertions_failed,
            "queried_state": self.queried_state,
            "verification_method": self.verification_method,
            "confidence": self.confidence,
            "success": self.success,
            "timestamp": self.timestamp,
        }


@dataclass
class ExecutionVerificationReport:
    """Final verification report after action execution.

    Combines visual and state query verification results into
    a comprehensive report with evidence and recommendations.
    """

    action: str
    """The action that was executed."""

    expected_state: ExpectedState
    """Expected state after action."""

    visual_result: Optional[VisualVerificationResult] = None
    """Visual verification result (if performed)."""

    state_result: Optional[StateQueryVerificationResult] = None
    """State query verification result (if performed)."""

    all_assertions_passed: list[dict[str, Any]] = field(default_factory=list)
    """All passed assertions from both methods."""

    all_assertions_failed: list[dict[str, Any]] = field(default_factory=list)
    """All failed assertions from both methods."""

    overall_success: bool = False
    """Whether verification passed overall."""

    confidence: float = 0.0
    """Overall confidence score (0.0 to 1.0)."""

    recommendations: list[str] = field(default_factory=list)
    """Recommendations based on verification results."""

    timestamp: str = ""
    execution_time_ms: float = 0.0

    def __post_init__(self) -> None:
        """Set defaults."""
        if not self.timestamp:
            object.__setattr__(self, "timestamp", datetime.now().isoformat())

    @property
    def has_visual_verification(self) -> bool:
        """Check if visual verification was performed."""
        return self.visual_result is not None

    @property
    def has_state_verification(self) -> bool:
        """Check if state verification was performed."""
        return self.state_result is not None

    @property
    def visual_confidence(self) -> float:
        """Get visual verification confidence."""
        return self.visual_result.confidence if self.visual_result else 0.0

    @property
    def state_confidence(self) -> float:
        """Get state query verification confidence."""
        return self.state_result.confidence if self.state_result else 0.0

    def summary(self) -> str:
        """Get human-readable summary."""
        status = "✓ PASS" if self.overall_success else "✗ FAIL"
        action_short = self.action[:50] + "..." if len(self.action) > 50 else self.action
        total_passed = len(self.all_assertions_passed)
        total_failed = len(self.all_assertions_failed)
        total = total_passed + total_failed

        return (
            f"{status} Action: {action_short} "
            f"(confidence: {self.confidence:.0%}, "
            f"{total_passed}/{total} assertions)"
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "action": self.action,
            "expected_state": self.expected_state.to_dict(),
            "visual_result": self.visual_result.to_dict() if self.visual_result else None,
            "state_result": self.state_result.to_dict() if self.state_result else None,
            "all_assertions_passed": self.all_assertions_passed,
            "all_assertions_failed": self.all_assertions_failed,
            "overall_success": self.overall_success,
            "confidence": self.confidence,
            "recommendations": self.recommendations,
            "timestamp": self.timestamp,
            "execution_time_ms": self.execution_time_ms,
        }
