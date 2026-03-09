"""Tests for BackendPolicy data models."""

import pytest

from app.agent_core.backend_policy import BackendPolicy, BackendType


class TestBackendType:
    """Tests for BackendType enum."""

    def test_backend_type_values(self):
        """Test that all expected backend types exist."""
        assert BackendType.BRIDGE.value == "bridge"
        assert BackendType.DIRECT_API.value == "direct_api"
        assert BackendType.UI.value == "ui"
        assert BackendType.DRY_RUN.value == "dry_run"
        assert BackendType.NONE.value == "none"

    def test_backend_type_string_conversion(self):
        """Test string conversion of backend types."""
        assert BackendType.BRIDGE.value == "bridge"
        assert BackendType("bridge") == BackendType.BRIDGE


class TestBackendPolicyDefaults:
    """Tests for BackendPolicy default values."""

    def test_default_policy(self):
        """Test default policy values."""
        policy = BackendPolicy()

        assert policy.preferred_backend == BackendType.BRIDGE
        assert policy.fallback_order == (BackendType.BRIDGE, BackendType.UI, BackendType.DRY_RUN)
        assert policy.fallback_to_ui is True
        assert policy.require_window_focus is True
        assert policy.respect_killswitch is True
        assert policy.validate_blocked_inputs is True
        assert policy.domain == ""
        assert policy.expected_window_hints == ()
        assert policy.bridge_timeout_seconds == 5.0
        assert policy.bridge_host == "127.0.0.1"
        assert policy.bridge_port is None

    def test_policy_custom_values(self):
        """Test policy with custom values."""
        policy = BackendPolicy(
            preferred_backend=BackendType.UI,
            fallback_order=(BackendType.UI, BackendType.DRY_RUN),
            fallback_to_ui=False,
            domain="test_domain",
            bridge_port=9999,
        )

        assert policy.preferred_backend == BackendType.UI
        assert policy.fallback_order == (BackendType.UI, BackendType.DRY_RUN)
        assert policy.fallback_to_ui is False
        assert policy.domain == "test_domain"
        assert policy.bridge_port == 9999


class TestBackendPolicyFactoryMethods:
    """Tests for BackendPolicy factory methods."""

    def test_for_touchdesigner(self):
        """Test TouchDesigner policy factory."""
        policy = BackendPolicy.for_touchdesigner()

        assert policy.preferred_backend == BackendType.BRIDGE
        assert policy.fallback_to_ui is True
        assert policy.domain == "touchdesigner"
        assert policy.bridge_port == 9988
        assert "TouchDesigner" in policy.expected_window_hints

    def test_for_touchdesigner_no_ui_fallback(self):
        """Test TouchDesigner policy without UI fallback."""
        policy = BackendPolicy.for_touchdesigner(fallback_to_ui=False)

        assert policy.fallback_to_ui is False
        assert BackendType.UI not in policy.fallback_order

    def test_for_touchdesigner_custom_port(self):
        """Test TouchDesigner policy with custom port."""
        policy = BackendPolicy.for_touchdesigner(bridge_port=8888)

        assert policy.bridge_port == 8888

    def test_for_houdini(self):
        """Test Houdini policy factory."""
        policy = BackendPolicy.for_houdini()

        assert policy.preferred_backend == BackendType.BRIDGE
        assert policy.fallback_to_ui is False  # Houdini has no UI fallback
        assert policy.domain == "houdini"
        assert policy.bridge_port == 9989
        assert "Houdini" in policy.expected_window_hints

    def test_for_houdini_no_ui_fallback(self):
        """Test Houdini policy never has UI fallback."""
        policy = BackendPolicy.for_houdini()

        assert BackendType.UI not in policy.fallback_order
        assert policy.fallback_order == (BackendType.BRIDGE, BackendType.DRY_RUN)

    def test_for_dry_run(self):
        """Test dry-run policy factory."""
        policy = BackendPolicy.for_dry_run()

        assert policy.preferred_backend == BackendType.DRY_RUN
        assert policy.fallback_order == (BackendType.DRY_RUN,)
        assert policy.fallback_to_ui is False
        assert policy.require_window_focus is False

    def test_for_dry_run_with_domain(self):
        """Test dry-run policy with domain."""
        policy = BackendPolicy.for_dry_run(domain="custom_domain")

        assert policy.domain == "custom_domain"


class TestBackendPolicyMethods:
    """Tests for BackendPolicy methods."""

    def test_allows_backend_true(self):
        """Test allows_backend returns True for allowed backends."""
        policy = BackendPolicy()

        assert policy.allows_backend(BackendType.BRIDGE) is True
        assert policy.allows_backend(BackendType.UI) is True
        assert policy.allows_backend(BackendType.DRY_RUN) is True

    def test_allows_backend_false(self):
        """Test allows_backend returns False for disallowed backends."""
        policy = BackendPolicy(fallback_order=(BackendType.BRIDGE,))

        assert policy.allows_backend(BackendType.BRIDGE) is True
        assert policy.allows_backend(BackendType.UI) is False

    def test_get_effective_fallback_order_with_ui(self):
        """Test effective fallback order includes UI when allowed."""
        policy = BackendPolicy(fallback_to_ui=True)

        effective = policy.get_effective_fallback_order()

        assert BackendType.UI in effective

    def test_get_effective_fallback_order_without_ui(self):
        """Test effective fallback order excludes UI when not allowed."""
        policy = BackendPolicy(fallback_to_ui=False)

        effective = policy.get_effective_fallback_order()

        assert BackendType.UI not in effective

    def test_slots_optimization(self):
        """Test that policy uses slots for memory efficiency."""
        policy = BackendPolicy()

        # Should not have __dict__ if using slots
        assert not hasattr(policy, "__dict__") or len(policy.__dict__) == 0


class TestBackendPolicyEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_empty_fallback_order(self):
        """Test policy with empty fallback order."""
        policy = BackendPolicy(fallback_order=())

        assert policy.allows_backend(BackendType.BRIDGE) is False
        assert policy.get_effective_fallback_order() == ()

    def test_single_backend_fallback(self):
        """Test policy with single backend in fallback."""
        policy = BackendPolicy(
            preferred_backend=BackendType.DRY_RUN,
            fallback_order=(BackendType.DRY_RUN,),
        )

        assert policy.allows_backend(BackendType.DRY_RUN) is True
        assert policy.allows_backend(BackendType.BRIDGE) is False

    def test_multiple_overrides(self):
        """Test policy with multiple custom overrides."""
        policy = BackendPolicy(
            preferred_backend=BackendType.DIRECT_API,
            fallback_order=(BackendType.DIRECT_API, BackendType.BRIDGE, BackendType.DRY_RUN),
            fallback_to_ui=False,
            require_window_focus=False,
            respect_killswitch=False,
            validate_blocked_inputs=False,
            domain="custom",
            expected_window_hints=("Window1", "Window2"),
            bridge_timeout_seconds=10.0,
            bridge_host="192.168.1.1",
            bridge_port=8080,
        )

        assert policy.preferred_backend == BackendType.DIRECT_API
        assert len(policy.fallback_order) == 3
        assert policy.fallback_to_ui is False
        assert policy.require_window_focus is False
        assert policy.respect_killswitch is False
        assert policy.validate_blocked_inputs is False
        assert policy.domain == "custom"
        assert len(policy.expected_window_hints) == 2
        assert policy.bridge_timeout_seconds == 10.0
        assert policy.bridge_host == "192.168.1.1"
        assert policy.bridge_port == 8080