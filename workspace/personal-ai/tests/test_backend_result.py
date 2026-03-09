"""Tests for BackendResult data models."""

import pytest

from app.agent_core.backend_policy import BackendType
from app.agent_core.backend_result import (
    BackendSelectionResult,
    BridgeHealthResult,
    SafetyCheckResult,
    SelectionStatus,
)


class TestSelectionStatus:
    """Tests for SelectionStatus enum."""

    def test_selection_status_values(self):
        """Test that all expected statuses exist."""
        assert SelectionStatus.SELECTED.value == "selected"
        assert SelectionStatus.FALLBACK_USED.value == "fallback_used"
        assert SelectionStatus.BLOCKED_SAFETY.value == "blocked_safety"
        assert SelectionStatus.BLOCKED_UNAVAILABLE.value == "blocked_unavailable"
        assert SelectionStatus.DRY_RUN_FORCED.value == "dry_run_forced"


class TestBridgeHealthResult:
    """Tests for BridgeHealthResult."""

    def test_healthy_result(self):
        """Test healthy bridge result."""
        result = BridgeHealthResult(
            healthy=True,
            host="127.0.0.1",
            port=9988,
            ping_ms=5.5,
        )

        assert result.healthy is True
        assert result.is_available is True
        assert result.ping_ms == 5.5
        assert result.error is None
        assert result.cached is False

    def test_unhealthy_result(self):
        """Test unhealthy bridge result."""
        result = BridgeHealthResult(
            healthy=False,
            host="127.0.0.1",
            port=9988,
            error="Connection refused",
        )

        assert result.healthy is False
        assert result.is_available is False
        assert result.error == "Connection refused"

    def test_cached_result(self):
        """Test cached bridge result."""
        result = BridgeHealthResult(
            healthy=True,
            host="127.0.0.1",
            port=9988,
            cached=True,
        )

        assert result.cached is True


class TestSafetyCheckResult:
    """Tests for SafetyCheckResult."""

    def test_passed_result(self):
        """Test passed safety check."""
        result = SafetyCheckResult(passed=True)

        assert result.passed is True
        assert result.block_reason is None

    def test_failed_killswitch(self):
        """Test failed safety check due to killswitch."""
        result = SafetyCheckResult(
            passed=False,
            reason="killswitch_active",
            killswitch_active=True,
        )

        assert result.passed is False
        assert result.block_reason == "killswitch_active"
        assert result.killswitch_active is True

    def test_failed_wrong_window(self):
        """Test failed safety check due to wrong window."""
        result = SafetyCheckResult(
            passed=False,
            reason="wrong_window_focus",
            wrong_window=True,
        )

        assert result.passed is False
        assert result.block_reason == "wrong_window_focus"
        assert result.wrong_window is True

    def test_failed_blocked_input(self):
        """Test failed safety check due to blocked input."""
        result = SafetyCheckResult(
            passed=False,
            reason="blocked_input: Ctrl+Alt+Del",
            blocked_input=True,
        )

        assert result.passed is False
        assert result.block_reason == "blocked_input: Ctrl+Alt+Del"
        assert result.blocked_input is True


class TestBackendSelectionResult:
    """Tests for BackendSelectionResult."""

    def test_selected_result(self):
        """Test successful selection of preferred backend."""
        result = BackendSelectionResult(
            selected_backend=BackendType.BRIDGE,
            status=SelectionStatus.SELECTED,
            message="Selected preferred backend: bridge",
            requested_backend=BackendType.BRIDGE,
        )

        assert result.selected_backend == BackendType.BRIDGE
        assert result.status == SelectionStatus.SELECTED
        assert result.is_executable is True
        assert result.is_dry_run is False
        assert result.is_blocked is False
        assert result.used_fallback is False

    def test_fallback_result(self):
        """Test fallback backend selection."""
        result = BackendSelectionResult(
            selected_backend=BackendType.UI,
            status=SelectionStatus.FALLBACK_USED,
            message="Using fallback backend: ui",
            requested_backend=BackendType.BRIDGE,
            attempted_backends=(BackendType.BRIDGE, BackendType.UI),
            rejected_backends=(BackendType.BRIDGE,),
        )

        assert result.selected_backend == BackendType.UI
        assert result.status == SelectionStatus.FALLBACK_USED
        assert result.used_fallback is True
        assert result.is_executable is True

    def test_blocked_safety_result(self):
        """Test blocked by safety selection."""
        result = BackendSelectionResult(
            selected_backend=BackendType.NONE,
            status=SelectionStatus.BLOCKED_SAFETY,
            message="Safety check failed: killswitch_active",
            requested_backend=BackendType.BRIDGE,
            safety_passed=False,
            safety_block_reason="killswitch_active",
        )

        assert result.selected_backend == BackendType.NONE
        assert result.status == SelectionStatus.BLOCKED_SAFETY
        assert result.is_executable is False
        assert result.is_blocked is True
        assert result.safety_passed is False

    def test_blocked_unavailable_result(self):
        """Test blocked due to unavailability."""
        result = BackendSelectionResult(
            selected_backend=BackendType.NONE,
            status=SelectionStatus.BLOCKED_UNAVAILABLE,
            message="No safe backend available",
            requested_backend=BackendType.BRIDGE,
            attempted_backends=(BackendType.BRIDGE,),
            rejected_backends=(BackendType.BRIDGE,),
        )

        assert result.selected_backend == BackendType.NONE
        assert result.status == SelectionStatus.BLOCKED_UNAVAILABLE
        assert result.is_executable is False
        assert result.is_blocked is True

    def test_dry_run_result(self):
        """Test dry-run selection."""
        result = BackendSelectionResult(
            selected_backend=BackendType.DRY_RUN,
            status=SelectionStatus.DRY_RUN_FORCED,
            message="Dry-run mode forced by policy",
            requested_backend=BackendType.DRY_RUN,
        )

        assert result.selected_backend == BackendType.DRY_RUN
        assert result.is_dry_run is True
        assert result.is_executable is True

    def test_to_dict(self):
        """Test serialization to dictionary."""
        result = BackendSelectionResult(
            selected_backend=BackendType.BRIDGE,
            status=SelectionStatus.SELECTED,
            message="Selected bridge",
            requested_backend=BackendType.BRIDGE,
            attempted_backends=(BackendType.BRIDGE,),
            rejected_backends=(),
            safety_passed=True,
            bridge_healthy=True,
            bridge_ping_ms=5.0,
            domain="touchdesigner",
            selection_duration_ms=1.5,
        )

        d = result.to_dict()

        assert d["selected_backend"] == "bridge"
        assert d["status"] == "selected"
        assert d["message"] == "Selected bridge"
        assert d["requested_backend"] == "bridge"
        assert d["attempted_backends"] == ["bridge"]
        assert d["rejected_backends"] == []
        assert d["safety_passed"] is True
        assert d["bridge_healthy"] is True
        assert d["bridge_ping_ms"] == 5.0
        assert d["domain"] == "touchdesigner"
        assert d["selection_duration_ms"] == 1.5

    def test_slots_optimization(self):
        """Test that result uses slots for memory efficiency."""
        result = BackendSelectionResult(
            selected_backend=BackendType.BRIDGE,
            status=SelectionStatus.SELECTED,
            message="Test",
            requested_backend=BackendType.BRIDGE,
        )

        # Should not have __dict__ if using slots
        assert not hasattr(result, "__dict__") or len(result.__dict__) == 0


class TestBackendSelectionResultProperties:
    """Tests for BackendSelectionResult property combinations."""

    def test_is_executable_with_blocked_status(self):
        """Test is_executable is False for blocked status even if backend is not NONE."""
        result = BackendSelectionResult(
            selected_backend=BackendType.BRIDGE,
            status=SelectionStatus.BLOCKED_SAFETY,
            message="Blocked",
            requested_backend=BackendType.BRIDGE,
            safety_passed=False,
        )

        assert result.selected_backend != BackendType.NONE
        assert result.is_executable is False

    def test_is_executable_with_none_backend(self):
        """Test is_executable is False for NONE backend."""
        result = BackendSelectionResult(
            selected_backend=BackendType.NONE,
            status=SelectionStatus.SELECTED,
            message="None",
            requested_backend=BackendType.BRIDGE,
        )

        assert result.is_executable is False

    def test_is_executable_with_safety_failed(self):
        """Test is_executable is False when safety failed."""
        result = BackendSelectionResult(
            selected_backend=BackendType.BRIDGE,
            status=SelectionStatus.SELECTED,
            message="Selected",
            requested_backend=BackendType.BRIDGE,
            safety_passed=False,
        )

        assert result.is_executable is False