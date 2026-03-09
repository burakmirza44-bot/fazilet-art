"""Tests for BackendSelector core logic."""

import pytest
from unittest.mock import MagicMock, patch
import time

from app.agent_core.backend_policy import BackendPolicy, BackendType
from app.agent_core.backend_result import SelectionStatus
from app.agent_core.backend_selector import BackendSelector, select_backend, get_default_selector


class TestBackendSelectorInit:
    """Tests for BackendSelector initialization."""

    def test_default_init(self):
        """Test default initialization."""
        selector = BackendSelector()

        assert selector._bridge_health_ttl == 1.0
        assert selector._bridge_health_cache == {}

    def test_custom_ttl(self):
        """Test initialization with custom TTL."""
        selector = BackendSelector(bridge_health_ttl=5.0)

        assert selector._bridge_health_ttl == 5.0


class TestBackendSelectorSafetyChecks:
    """Tests for safety check functionality."""

    def test_killswitch_blocks_selection(self):
        """Test that active killswitch blocks selection."""
        selector = BackendSelector()
        selector.set_killswitch_check(lambda: True)

        policy = BackendPolicy()
        result = selector.select(policy)

        assert result.status == SelectionStatus.BLOCKED_SAFETY
        assert result.safety_passed is False
        assert "killswitch" in result.safety_block_reason.lower()

    def test_killswitch_respected_when_disabled(self):
        """Test that killswitch check is skipped when policy disables it."""
        selector = BackendSelector()
        selector.set_killswitch_check(lambda: True)

        policy = BackendPolicy(respect_killswitch=False)
        result = selector.select(policy)

        # Should not be blocked by killswitch
        assert result.status != SelectionStatus.BLOCKED_SAFETY or "killswitch" not in (result.safety_block_reason or "")

    def test_wrong_window_blocks_selection(self):
        """Test that wrong window focus blocks selection."""
        selector = BackendSelector()
        selector.set_window_title_getter(lambda: "Notepad")

        policy = BackendPolicy(
            require_window_focus=True,
            expected_window_hints=("TouchDesigner", "Houdini"),
        )
        result = selector.select(policy)

        assert result.status == SelectionStatus.BLOCKED_SAFETY
        assert result.safety_passed is False
        assert "window" in result.safety_block_reason.lower()

    def test_correct_window_allows_selection(self):
        """Test that correct window focus allows selection."""
        selector = BackendSelector()
        selector.set_window_title_getter(lambda: "TouchDesigner - project.toe")
        selector.set_killswitch_check(lambda: False)

        policy = BackendPolicy(
            require_window_focus=True,
            expected_window_hints=("TouchDesigner",),
            bridge_port=9988,
        )
        # Mock bridge as unavailable so we get UI fallback
        result = selector.select(policy)

        # Should proceed to backend selection (may be blocked by unavailability)
        assert result.status != SelectionStatus.BLOCKED_SAFETY or "window" not in (result.safety_block_reason or "")

    def test_window_focus_disabled(self):
        """Test that window focus check is skipped when disabled."""
        selector = BackendSelector()
        selector.set_window_title_getter(lambda: "Notepad")

        policy = BackendPolicy(
            require_window_focus=False,
            expected_window_hints=("TouchDesigner",),
        )
        result = selector.select(policy)

        # Should not be blocked by window focus
        assert result.status != SelectionStatus.BLOCKED_SAFETY or "window" not in (result.safety_block_reason or "")

    def test_blocked_input_blocks_selection(self):
        """Test that blocked input blocks selection."""
        selector = BackendSelector()
        selector.set_input_checker(lambda ctx: "blocked_hotkey: Ctrl+Alt+Del")

        policy = BackendPolicy()
        result = selector.select(policy, action_context={"hotkey": "Ctrl+Alt+Del"})

        assert result.status == SelectionStatus.BLOCKED_SAFETY
        assert result.safety_passed is False

    def test_input_check_disabled(self):
        """Test that input check is skipped when disabled."""
        selector = BackendSelector()
        selector.set_input_checker(lambda ctx: "blocked_key: Win")

        policy = BackendPolicy(validate_blocked_inputs=False)
        result = selector.select(policy, action_context={"key": "Win"})

        # Should not be blocked by input check
        assert result.status != SelectionStatus.BLOCKED_SAFETY or "input" not in (result.safety_block_reason or "")


class TestBackendSelectorDryRun:
    """Tests for dry-run mode."""

    def test_dry_run_forced(self):
        """Test that dry-run policy forces dry-run mode."""
        selector = BackendSelector()
        policy = BackendPolicy.for_dry_run()

        result = selector.select(policy)

        assert result.selected_backend == BackendType.DRY_RUN
        assert result.status == SelectionStatus.DRY_RUN_FORCED
        assert result.is_dry_run is True

    def test_dry_run_always_available(self):
        """Test that dry-run is always available."""
        selector = BackendSelector()
        selector.set_killswitch_check(lambda: True)  # Block everything

        # But dry-run should still work
        policy = BackendPolicy.for_dry_run()
        result = selector.select(policy)

        assert result.selected_backend == BackendType.DRY_RUN


class TestBackendSelectorBridgeHealth:
    """Tests for bridge health checking."""

    def test_bridge_health_check_unavailable(self):
        """Test bridge health check when bridge is unavailable."""
        selector = BackendSelector()
        policy = BackendPolicy.for_touchdesigner(bridge_port=9988)

        result = selector.check_bridge_health(policy)

        assert result.healthy is False
        assert result.host == "127.0.0.1"
        assert result.port == 9988

    def test_bridge_health_caching(self):
        """Test that bridge health is cached."""
        selector = BackendSelector()
        policy = BackendPolicy.for_touchdesigner(bridge_port=9988)

        # First check
        result1 = selector.check_bridge_health(policy)
        assert result1.cached is False

        # Second check should be cached
        result2 = selector.check_bridge_health(policy)
        assert result2.cached is True

    def test_bridge_health_cache_expiry(self):
        """Test that bridge health cache expires."""
        selector = BackendSelector(bridge_health_ttl=0.01)  # Very short TTL
        policy = BackendPolicy.for_touchdesigner(bridge_port=9988)

        # First check
        result1 = selector.check_bridge_health(policy)
        assert result1.cached is False

        # Wait for cache to expire
        time.sleep(0.02)

        # Should be a fresh check
        result2 = selector.check_bridge_health(policy)
        assert result2.cached is False

    def test_bridge_health_with_registered_client(self):
        """Test bridge health with registered client."""
        selector = BackendSelector()

        mock_client = MagicMock()
        mock_client.ping.return_value = True

        selector.register_bridge_client("touchdesigner", mock_client)

        policy = BackendPolicy.for_touchdesigner()
        result = selector.check_bridge_health(policy)

        assert result.healthy is True
        mock_client.ping.assert_called_once()

    def test_no_bridge_port(self):
        """Test bridge health when no port is configured."""
        selector = BackendSelector()
        policy = BackendPolicy(bridge_port=None)

        result = selector.check_bridge_health(policy)

        assert result.healthy is False
        assert "No bridge port" in result.error


class TestBackendSelectorSelection:
    """Tests for backend selection logic."""

    def test_bridge_selected_when_healthy(self):
        """Test bridge is selected when healthy and preferred."""
        selector = BackendSelector()

        # Mock to bypass safety checks
        selector.set_killswitch_check(lambda: False)
        selector.set_window_title_getter(lambda: "TouchDesigner - project")

        # Mock healthy bridge
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        selector.register_bridge_client("touchdesigner", mock_client)

        policy = BackendPolicy.for_touchdesigner()
        result = selector.select(policy)

        assert result.selected_backend == BackendType.BRIDGE
        assert result.status == SelectionStatus.SELECTED

    def test_ui_fallback_when_bridge_unhealthy(self):
        """Test UI fallback when bridge is unavailable."""
        selector = BackendSelector()

        # Mock to bypass safety checks
        selector.set_killswitch_check(lambda: False)
        selector.set_window_title_getter(lambda: "TouchDesigner - project")

        policy = BackendPolicy.for_touchdesigner(fallback_to_ui=True)
        result = selector.select(policy)

        # Bridge is unavailable, should fall back to UI
        assert result.selected_backend == BackendType.UI
        assert result.status == SelectionStatus.FALLBACK_USED

    def test_ui_fallback_blocked_by_policy(self):
        """Test that UI fallback is blocked when policy disallows it."""
        selector = BackendSelector()

        # Mock to bypass safety checks
        selector.set_killswitch_check(lambda: False)
        selector.set_window_title_getter(lambda: "Houdini - project")

        # Houdini policy has no UI fallback
        policy = BackendPolicy.for_houdini()
        result = selector.select(policy)

        # Bridge is unavailable and no UI fallback, should be dry_run
        assert result.selected_backend == BackendType.DRY_RUN
        assert BackendType.UI not in result.attempted_backends

    def test_no_safe_backend(self):
        """Test NONE backend when no backend is available."""
        selector = BackendSelector()

        # Mock to bypass safety checks
        selector.set_killswitch_check(lambda: False)
        selector.set_window_title_getter(lambda: "Some Window")

        # Policy with only bridge (unavailable) and no other fallbacks
        policy = BackendPolicy(
            preferred_backend=BackendType.BRIDGE,
            fallback_order=(BackendType.BRIDGE,),
            fallback_to_ui=False,
        )
        result = selector.select(policy)

        assert result.selected_backend == BackendType.NONE
        assert result.status == SelectionStatus.BLOCKED_UNAVAILABLE

    def test_selection_audit_trail(self):
        """Test that selection result has proper audit trail."""
        selector = BackendSelector()

        # Mock to bypass safety checks
        selector.set_killswitch_check(lambda: False)
        selector.set_window_title_getter(lambda: "TouchDesigner - project")

        policy = BackendPolicy.for_touchdesigner(fallback_to_ui=True)
        result = selector.select(policy)

        assert result.requested_backend == BackendType.BRIDGE
        assert BackendType.BRIDGE in result.attempted_backends
        assert BackendType.BRIDGE in result.rejected_backends  # Unavailable

    def test_selection_timing(self):
        """Test that selection duration is tracked."""
        selector = BackendSelector()

        policy = BackendPolicy.for_dry_run()
        result = selector.select(policy)

        assert result.selection_duration_ms >= 0


class TestBackendSelectorCache:
    """Tests for cache management."""

    def test_clear_cache(self):
        """Test that cache can be cleared."""
        selector = BackendSelector()
        policy = BackendPolicy.for_touchdesigner()

        # Populate cache
        selector.check_bridge_health(policy)
        assert len(selector._bridge_health_cache) == 1

        # Clear cache
        selector.clear_cache()
        assert len(selector._bridge_health_cache) == 0


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_get_default_selector(self):
        """Test default selector singleton."""
        selector1 = get_default_selector()
        selector2 = get_default_selector()

        assert selector1 is selector2

    def test_select_backend_function(self):
        """Test select_backend convenience function."""
        policy = BackendPolicy.for_dry_run()
        result = select_backend(policy)

        assert result.selected_backend == BackendType.DRY_RUN


class TestBackendSelectorIntegration:
    """Integration tests for BackendSelector."""

    def test_full_selection_flow(self):
        """Test complete selection flow with all checks."""
        selector = BackendSelector()

        # Set up mocks
        selector.set_killswitch_check(lambda: False)
        selector.set_window_title_getter(lambda: "TouchDesigner - project")

        mock_client = MagicMock()
        mock_client.ping.return_value = True
        selector.register_bridge_client("touchdesigner", mock_client)

        policy = BackendPolicy.for_touchdesigner(
            require_window_focus=True,
            expected_window_hints=("TouchDesigner",),
        )

        result = selector.select(policy, action_context={"key": "A"})

        assert result.is_executable is True
        assert result.selected_backend == BackendType.BRIDGE
        assert result.safety_passed is True

    def test_selection_with_blocked_input_context(self):
        """Test selection with action context containing blocked input."""
        selector = BackendSelector()
        selector.set_input_checker(lambda ctx: "blocked_key: Win")

        policy = BackendPolicy()
        result = selector.select(policy, action_context={"key": "Win"})

        assert result.status == SelectionStatus.BLOCKED_SAFETY
        assert "blocked" in result.safety_block_reason.lower()