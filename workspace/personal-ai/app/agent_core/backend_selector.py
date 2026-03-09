"""Core Backend Selector.

Central backend selection mechanism that unifies backend selection across
all execution paths, with policy-aware routing, safety integration, and
bridge health awareness.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from app.agent_core.backend_policy import BackendPolicy, BackendType
from app.agent_core.backend_result import (
    BackendSelectionResult,
    BridgeHealthResult,
    SafetyCheckResult,
    SelectionStatus,
)


@dataclass
class BridgeHealthCache:
    """Cache entry for bridge health status."""

    result: BridgeHealthResult
    timestamp: float
    ttl_seconds: float = 1.0

    def is_valid(self) -> bool:
        """Check if cache entry is still valid."""
        return (time.monotonic() - self.timestamp) < self.ttl_seconds


class BackendSelector:
    """Central backend selection mechanism.

    Provides a unified interface for selecting execution backends across
    all major execution paths, with consistent policy enforcement, safety
    integration, and bridge health awareness.

    Selection Flow:
        1. Check killswitch -> BLOCKED_SAFETY if active
        2. Check window focus (if required) -> BLOCKED_SAFETY if wrong window
        3. Check blocked inputs (if action_context provided) -> BLOCKED_SAFETY if blocked
        4. If dry_run forced -> return DRY_RUN
        5. Check bridge health (with caching, TTL=1s)
        6. Try preferred_backend, then fallback_order
        7. Return first available backend or NONE
    """

    def __init__(self, bridge_health_ttl: float = 1.0):
        """Initialize the BackendSelector.

        Args:
            bridge_health_ttl: TTL for bridge health cache in seconds (default: 1.0)
        """
        self._bridge_health_cache: dict[str, BridgeHealthCache] = {}
        self._bridge_health_ttl = bridge_health_ttl

        # Optional injectable dependencies for testing/mocking
        self._killswitch_check: callable | None = None
        self._window_title_getter: callable | None = None
        self._input_checker: callable | None = None
        self._bridge_clients: dict[str, Any] = {}

    def set_killswitch_check(self, check_fn: callable) -> None:
        """Set a custom killswitch check function.

        Args:
            check_fn: Function that returns True if killswitch is active
        """
        self._killswitch_check = check_fn

    def set_window_title_getter(self, getter_fn: callable) -> None:
        """Set a custom window title getter function.

        Args:
            getter_fn: Function that returns the active window title
        """
        self._window_title_getter = getter_fn

    def set_input_checker(self, checker_fn: callable) -> None:
        """Set a custom input checker function.

        Args:
            checker_fn: Function to check for blocked inputs
        """
        self._input_checker = checker_fn

    def register_bridge_client(self, domain: str, client: Any) -> None:
        """Register a bridge client for a domain.

        Args:
            domain: Domain name (e.g., "touchdesigner", "houdini")
            client: Bridge client with a ping() method
        """
        self._bridge_clients[domain] = client

    def select(
        self,
        policy: BackendPolicy,
        action_context: dict[str, Any] | None = None,
    ) -> BackendSelectionResult:
        """Main entry point for backend selection.

        Args:
            policy: BackendPolicy defining selection preferences and constraints
            action_context: Optional context for safety checks (keys, text, etc.)

        Returns:
            BackendSelectionResult with selected backend and audit trail
        """
        start_time = time.perf_counter()
        attempted_backends: list[BackendType] = []
        rejected_backends: list[BackendType] = []

        # Step 1: Check for dry-run forced first (bypasses all safety checks)
        if policy.preferred_backend == BackendType.DRY_RUN:
            duration_ms = (time.perf_counter() - start_time) * 1000
            return BackendSelectionResult(
                selected_backend=BackendType.DRY_RUN,
                status=SelectionStatus.DRY_RUN_FORCED,
                message="Dry-run mode forced by policy",
                requested_backend=policy.preferred_backend,
                attempted_backends=(BackendType.DRY_RUN,),
                rejected_backends=(),
                safety_passed=True,  # Dry-run bypasses safety
                domain=policy.domain,
                selection_duration_ms=duration_ms,
            )

        # Step 2: Run safety checks (for non-dry-run modes)
        safety_result = self.check_safety(policy, action_context)
        if not safety_result.passed:
            duration_ms = (time.perf_counter() - start_time) * 1000
            return BackendSelectionResult(
                selected_backend=BackendType.NONE,
                status=SelectionStatus.BLOCKED_SAFETY,
                message=f"Safety check failed: {safety_result.block_reason}",
                requested_backend=policy.preferred_backend,
                attempted_backends=tuple(attempted_backends),
                rejected_backends=tuple(rejected_backends),
                safety_passed=False,
                safety_block_reason=safety_result.block_reason,
                domain=policy.domain,
                selection_duration_ms=duration_ms,
            )

        # Step 3: Check bridge health if BRIDGE is in consideration
        bridge_health: BridgeHealthResult | None = None
        if BackendType.BRIDGE in policy.get_effective_fallback_order():
            bridge_health = self.check_bridge_health(policy)

        # Step 4: Try backends in fallback order
        effective_fallback = policy.get_effective_fallback_order()

        for backend in effective_fallback:
            attempted_backends.append(backend)

            if self._is_backend_available(backend, bridge_health, policy):
                duration_ms = (time.perf_counter() - start_time) * 1000

                # Determine status
                if backend == policy.preferred_backend:
                    status = SelectionStatus.SELECTED
                    message = f"Selected preferred backend: {backend.value}"
                else:
                    status = SelectionStatus.FALLBACK_USED
                    message = f"Using fallback backend: {backend.value}"

                return BackendSelectionResult(
                    selected_backend=backend,
                    status=status,
                    message=message,
                    requested_backend=policy.preferred_backend,
                    attempted_backends=tuple(attempted_backends),
                    rejected_backends=tuple(rejected_backends),
                    safety_passed=True,
                    bridge_healthy=bridge_health.healthy if bridge_health else None,
                    bridge_ping_ms=bridge_health.ping_ms if bridge_health else None,
                    domain=policy.domain,
                    selection_duration_ms=duration_ms,
                )
            else:
                rejected_backends.append(backend)

        # Step 5: No available backend
        duration_ms = (time.perf_counter() - start_time) * 1000
        return BackendSelectionResult(
            selected_backend=BackendType.NONE,
            status=SelectionStatus.BLOCKED_UNAVAILABLE,
            message="No safe backend available",
            requested_backend=policy.preferred_backend,
            attempted_backends=tuple(attempted_backends),
            rejected_backends=tuple(rejected_backends),
            safety_passed=True,
            bridge_healthy=bridge_health.healthy if bridge_health else None,
            bridge_ping_ms=bridge_health.ping_ms if bridge_health else None,
            domain=policy.domain,
            selection_duration_ms=duration_ms,
        )

    def check_bridge_health(self, policy: BackendPolicy) -> BridgeHealthResult:
        """Check bridge availability with caching.

        Args:
            policy: BackendPolicy with bridge configuration

        Returns:
            BridgeHealthResult with health status
        """
        if policy.bridge_port is None:
            return BridgeHealthResult(
                healthy=False,
                host=policy.bridge_host,
                port=0,
                error="No bridge port configured",
            )

        # Check cache
        cache_key = f"{policy.bridge_host}:{policy.bridge_port}"
        cached = self._bridge_health_cache.get(cache_key)

        if cached and cached.is_valid():
            return BridgeHealthResult(
                healthy=cached.result.healthy,
                host=cached.result.host,
                port=cached.result.port,
                ping_ms=cached.result.ping_ms,
                error=cached.result.error,
                cached=True,
            )

        # Perform actual health check
        result = self._ping_bridge(policy)

        # Cache the result
        self._bridge_health_cache[cache_key] = BridgeHealthCache(
            result=result,
            timestamp=time.monotonic(),
            ttl_seconds=self._bridge_health_ttl,
        )

        return result

    def check_safety(
        self,
        policy: BackendPolicy,
        action_context: dict[str, Any] | None = None,
    ) -> SafetyCheckResult:
        """Run all safety checks.

        Args:
            policy: BackendPolicy with safety requirements
            action_context: Optional context for input validation

        Returns:
            SafetyCheckResult with pass/fail status
        """
        # 1. Killswitch check
        if policy.respect_killswitch:
            if self._is_killswitch_active():
                return SafetyCheckResult(
                    passed=False,
                    reason="killswitch_active",
                    killswitch_active=True,
                )

        # 2. Window focus check
        if policy.require_window_focus and policy.expected_window_hints:
            if not self._is_expected_window(policy.expected_window_hints):
                return SafetyCheckResult(
                    passed=False,
                    reason="wrong_window_focus",
                    wrong_window=True,
                )

        # 3. Blocked inputs check
        if action_context and policy.validate_blocked_inputs:
            blocked_result = self._check_blocked_inputs(action_context)
            if blocked_result:
                return SafetyCheckResult(
                    passed=False,
                    reason=f"blocked_input: {blocked_result}",
                    blocked_input=True,
                )

        return SafetyCheckResult(passed=True)

    def clear_cache(self) -> None:
        """Clear the bridge health cache."""
        self._bridge_health_cache.clear()

    def _is_backend_available(
        self,
        backend: BackendType,
        bridge_health: BridgeHealthResult | None,
        policy: BackendPolicy,
    ) -> bool:
        """Check if a specific backend is available.

        Args:
            backend: Backend type to check
            bridge_health: Bridge health result if available
            policy: Current policy

        Returns:
            True if backend is available
        """
        if backend == BackendType.BRIDGE:
            if bridge_health is None:
                return False
            return bridge_health.healthy

        if backend == BackendType.DIRECT_API:
            # Check if direct API is available (e.g., hou module for Houdini)
            return self._check_direct_api_availability(policy.domain)

        if backend == BackendType.UI:
            # UI is always "available" if policy allows it
            return policy.fallback_to_ui

        if backend == BackendType.DRY_RUN:
            # Dry-run is always available
            return True

        return False

    def _ping_bridge(self, policy: BackendPolicy) -> BridgeHealthResult:
        """Ping the bridge to check health.

        Args:
            policy: Policy with bridge configuration

        Returns:
            BridgeHealthResult with ping result
        """
        import socket

        start_time = time.perf_counter()

        # Try to use registered client first
        domain = policy.domain
        if domain in self._bridge_clients:
            client = self._bridge_clients[domain]
            try:
                if hasattr(client, 'ping') and callable(client.ping):
                    healthy = client.ping()
                    ping_ms = (time.perf_counter() - start_time) * 1000
                    return BridgeHealthResult(
                        healthy=healthy,
                        host=policy.bridge_host,
                        port=policy.bridge_port or 0,
                        ping_ms=ping_ms,
                    )
            except Exception as e:
                return BridgeHealthResult(
                    healthy=False,
                    host=policy.bridge_host,
                    port=policy.bridge_port or 0,
                    error=str(e),
                )

        # Fallback to socket check
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(policy.bridge_timeout_seconds)
            result = sock.connect_ex((policy.bridge_host, policy.bridge_port))
            sock.close()

            ping_ms = (time.perf_counter() - start_time) * 1000
            healthy = result == 0

            return BridgeHealthResult(
                healthy=healthy,
                host=policy.bridge_host,
                port=policy.bridge_port or 0,
                ping_ms=ping_ms,
                error=None if healthy else f"Connection refused (code: {result})",
            )
        except Exception as e:
            return BridgeHealthResult(
                healthy=False,
                host=policy.bridge_host,
                port=policy.bridge_port or 0,
                error=str(e),
            )

    def _is_killswitch_active(self) -> bool:
        """Check if global killswitch is active.

        Returns:
            True if killswitch is active
        """
        # Use injected function if available
        if self._killswitch_check:
            return self._killswitch_check()

        # Try to import and use the real killswitch
        try:
            from app.agent_core.killswitch import is_global_stop_requested

            return is_global_stop_requested()
        except ImportError:
            # Killswitch module not available
            return False

    def _is_expected_window(self, expected_hints: tuple[str, ...]) -> bool:
        """Check if the active window matches expected hints.

        Args:
            expected_hints: Tuple of window title hints to match

        Returns:
            True if active window matches any hint
        """
        # Use injected function if available
        if self._window_title_getter:
            active_title = self._window_title_getter()
        else:
            # Try to import and use the real window guard
            try:
                from app.agent_core.window_guard import get_active_window_title

                active_title = get_active_window_title()
            except ImportError:
                # Window guard not available, assume correct window
                return True

        if not active_title:
            return False

        active_lower = active_title.lower()
        return any(hint.lower() in active_lower for hint in expected_hints)

    def _check_blocked_inputs(self, action_context: dict[str, Any]) -> str | None:
        """Check for blocked inputs in action context.

        Args:
            action_context: Context with potential input data

        Returns:
            Reason string if blocked, None otherwise
        """
        # Use injected function if available
        if self._input_checker:
            return self._input_checker(action_context)

        # Try to import and use real input checks
        try:
            from app.agent_core.input_executor import (
                is_blocked_key,
                is_blocked_hotkey,
                is_blocked_text,
            )

            # Check keys
            if "key" in action_context:
                if is_blocked_key(action_context["key"]):
                    return f"blocked_key: {action_context['key']}"

            # Check hotkeys
            if "hotkey" in action_context:
                if is_blocked_hotkey(action_context["hotkey"]):
                    return f"blocked_hotkey: {action_context['hotkey']}"

            # Check text
            if "text" in action_context:
                if is_blocked_text(action_context["text"]):
                    return f"blocked_text: {action_context['text'][:20]}..."

        except ImportError:
            # Input executor not available
            pass

        return None

    def _check_direct_api_availability(self, domain: str) -> bool:
        """Check if direct API is available for the domain.

        Args:
            domain: Domain to check (e.g., "houdini")

        Returns:
            True if direct API is available
        """
        if domain == "houdini":
            try:
                import hou

                return hou.isUIAvailable()
            except ImportError:
                return False

        # No direct API for other domains
        return False


# Singleton instance for convenience
_default_selector: BackendSelector | None = None


def get_default_selector() -> BackendSelector:
    """Get the default BackendSelector instance.

    Returns:
        Singleton BackendSelector instance
    """
    global _default_selector
    if _default_selector is None:
        _default_selector = BackendSelector()
    return _default_selector


def select_backend(
    policy: BackendPolicy,
    action_context: dict[str, Any] | None = None,
) -> BackendSelectionResult:
    """Convenience function for backend selection using default selector.

    Args:
        policy: BackendPolicy for selection
        action_context: Optional context for safety checks

    Returns:
        BackendSelectionResult
    """
    return get_default_selector().select(policy, action_context)