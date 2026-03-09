"""Tests for bridge health integration.

Tests BridgeHealthReport, check_bridge_health, and integration
with execution loops.
"""

import json
import os
import socket
from unittest.mock import MagicMock, patch

import pytest

from app.core.bridge_health import (
    BridgeHealthReport,
    bridge_health_from_backend_result,
    check_bridge_health,
    normalize_bridge_error,
)
from app.agent_core.backend_result import BridgeHealthResult


class TestBridgeHealthReport:
    """Tests for BridgeHealthReport dataclass."""

    def test_bridge_health_report_creation(self):
        """Test creating a BridgeHealthReport."""
        report = BridgeHealthReport(
            bridge_type="touchdesigner",
            bridge_enabled=True,
            bridge_required=True,
            bridge_reachable=True,
            ping_ok=True,
            inspect_ok=True,
        )

        assert report.bridge_type == "touchdesigner"
        assert report.bridge_enabled is True
        assert report.bridge_required is True
        assert report.bridge_reachable is True
        assert report.ping_ok is True
        assert report.inspect_ok is True
        assert report.is_healthy is True
        assert report.can_execute is True

    def test_bridge_health_report_unhealthy(self):
        """Test BridgeHealthReport when bridge is unhealthy."""
        report = BridgeHealthReport(
            bridge_type="houdini",
            bridge_enabled=True,
            bridge_required=True,
            bridge_reachable=False,
            ping_ok=False,
            inspect_ok=False,
            degraded=True,
        )

        assert report.is_healthy is False
        assert report.can_execute is False

    def test_bridge_health_report_fallback(self):
        """Test BridgeHealthReport with fallback mode."""
        report = BridgeHealthReport(
            bridge_type="touchdesigner",
            bridge_enabled=True,
            bridge_required=True,
            bridge_reachable=False,
            ping_ok=False,
            fallback_mode_used=True,
        )

        assert report.is_healthy is False
        assert report.can_execute is True  # Can execute via fallback

    def test_bridge_health_report_to_dict(self):
        """Test converting BridgeHealthReport to dict."""
        report = BridgeHealthReport(
            bridge_type="touchdesigner",
            bridge_enabled=True,
            bridge_required=True,
            bridge_reachable=True,
            ping_ok=True,
            inspect_ok=True,
            latency_ms=15.5,
        )

        data = report.to_dict()

        assert data["bridge_type"] == "touchdesigner"
        assert data["bridge_reachable"] is True
        assert data["ping_ok"] is True
        assert data["is_healthy"] is True
        assert data["can_execute"] is True
        assert data["latency_ms"] == 15.5


class TestCheckBridgeHealth:
    """Tests for check_bridge_health function."""

    @patch("socket.socket")
    def test_check_bridge_health_success(self, mock_socket_class):
        """Test successful bridge health check."""
        mock_socket = MagicMock()
        mock_socket.connect_ex.return_value = 0
        mock_socket_class.return_value = mock_socket

        report = check_bridge_health(
            domain="touchdesigner",
            host="127.0.0.1",
            port=9988,
        )

        assert report.bridge_type == "touchdesigner"
        assert report.bridge_reachable is True
        assert report.ping_ok is True
        assert report.inspect_ok is True
        assert report.is_healthy is True
        assert report.latency_ms > 0

    @patch("socket.socket")
    def test_check_bridge_health_connection_refused(self, mock_socket_class):
        """Test bridge health check when connection is refused."""
        mock_socket = MagicMock()
        mock_socket.connect_ex.return_value = 61  # Connection refused
        mock_socket_class.return_value = mock_socket

        report = check_bridge_health(
            domain="houdini",
            host="127.0.0.1",
            port=9989,
        )

        assert report.bridge_type == "houdini"
        assert report.bridge_reachable is False
        assert report.ping_ok is False
        assert report.degraded is True
        assert "CONNECTION_REFUSED" in report.last_error_code

    @patch("socket.socket")
    def test_check_bridge_health_timeout(self, mock_socket_class):
        """Test bridge health check when ping times out."""
        mock_socket = MagicMock()
        mock_socket.connect_ex.side_effect = socket.timeout()
        mock_socket_class.return_value = mock_socket

        report = check_bridge_health(
            domain="touchdesigner",
            host="127.0.0.1",
            port=9988,
            timeout_seconds=0.1,
        )

        assert report.bridge_reachable is False
        assert report.ping_ok is False
        assert report.last_error_code == "PING_TIMEOUT"
        assert "timed out" in report.last_error_message

    @patch("socket.socket")
    def test_check_bridge_health_exception(self, mock_socket_class):
        """Test bridge health check when exception occurs."""
        mock_socket = MagicMock()
        mock_socket.connect_ex.side_effect = Exception("Network error")
        mock_socket_class.return_value = mock_socket

        report = check_bridge_health(
            domain="houdini",
            host="127.0.0.1",
            port=9989,
        )

        assert report.bridge_reachable is False
        assert report.ping_ok is False
        assert "Network error" in report.last_error_message

    def test_check_bridge_health_default_ports(self):
        """Test that default ports are set correctly."""
        with patch("socket.socket") as mock_socket_class:
            mock_socket = MagicMock()
            mock_socket.connect_ex.return_value = 0
            mock_socket_class.return_value = mock_socket

            # TouchDesigner should default to port 9988
            report_td = check_bridge_health(domain="touchdesigner")
            assert report_td.bridge_type == "touchdesigner"

            # Houdini should default to port 9989
            report_houdini = check_bridge_health(domain="houdini")
            assert report_houdini.bridge_type == "houdini"


class TestNormalizeBridgeError:
    """Tests for normalize_bridge_error function."""

    def test_normalize_bridge_error_ping_failed(self):
        """Test normalizing a ping failure."""
        report = BridgeHealthReport(
            bridge_type="touchdesigner",
            bridge_reachable=False,
            ping_ok=False,
            last_error_code="PING_TIMEOUT",
            last_error_message="Ping timed out",
        )

        error = normalize_bridge_error(report, "touchdesigner", "task_123")

        assert error.error_type.value == "bridge_ping_failed"
        assert "touchdesigner" in error.message
        assert error.context["bridge_type"] == "touchdesigner"
        assert error.context["task_id"] == "task_123"

    def test_normalize_bridge_error_inspect_failed(self):
        """Test normalizing an inspect failure."""
        report = BridgeHealthReport(
            bridge_type="houdini",
            bridge_reachable=True,
            ping_ok=True,
            inspect_ok=False,
            last_error_code="INSPECT_ERROR",
            last_error_message="Inspection failed",
        )

        error = normalize_bridge_error(report, "houdini", "task_456")

        assert error.error_type.value == "bridge_inspect_failed"
        assert error.context["task_id"] == "task_456"


class TestBridgeHealthFromBackendResult:
    """Tests for bridge_health_from_backend_result function."""

    def test_from_healthy_result(self):
        """Test converting healthy BridgeHealthResult."""
        result = BridgeHealthResult(
            healthy=True,
            host="127.0.0.1",
            port=9988,
            ping_ms=15.5,
        )

        report = bridge_health_from_backend_result(result, "touchdesigner")

        assert report.bridge_type == "touchdesigner"
        assert report.bridge_reachable is True
        assert report.ping_ok is True
        assert report.latency_ms == 15.5
        assert report.degraded is False

    def test_from_unhealthy_result(self):
        """Test converting unhealthy BridgeHealthResult."""
        result = BridgeHealthResult(
            healthy=False,
            host="127.0.0.1",
            port=9989,
            error="Connection refused",
        )

        report = bridge_health_from_backend_result(result, "houdini")

        assert report.bridge_reachable is False
        assert report.ping_ok is False
        assert report.degraded is True
        assert report.last_error_message == "Connection refused"


class TestBridgeHealthIntegration:
    """Tests for bridge health integration with execution loops."""

    def test_execution_loop_includes_bridge_health(self):
        """Test that execution loop includes bridge health in report."""
        from app.domains.touchdesigner.td_execution_loop import (
            TDExecutionConfig,
            TDExecutionLoop,
        )

        config = TDExecutionConfig(
            use_live_bridge=True,
            dry_run=True,  # Use dry run to avoid actual bridge check
            enable_memory=False,
        )
        loop = TDExecutionLoop(config)

        # Mock task object
        task = MagicMock()
        task.task_summary = "test_task"
        task.task_id = "test_123"

        report = loop.run_basic_top_chain(task, use_live_bridge=False, dry_run=True)

        # In dry run mode with use_live_bridge=False, bridge health is not checked
        # but the report structure should be valid
        assert hasattr(report, "final_status")
        assert hasattr(report, "bridge_health")
        assert hasattr(report, "memory_influenced")

    def test_houdini_execution_loop_bridge_health(self):
        """Test Houdini execution loop bridge health integration."""
        from app.domains.houdini.houdini_execution_loop import (
            HoudiniExecutionConfig,
            HoudiniExecutionLoop,
        )

        config = HoudiniExecutionConfig(
            use_live_bridge=True,
            dry_run=True,
            enable_memory=False,
        )
        loop = HoudiniExecutionLoop(config)

        # Mock task object
        task = MagicMock()
        task.task_summary = "test_sop_task"
        task.task_id = "houdini_123"

        report = loop.run_basic_sop_chain(task, use_live_bridge=False, dry_run=True)

        assert hasattr(report, "final_status")
        assert hasattr(report, "bridge_health")
        assert report.final_status in ["success", "failed"]
