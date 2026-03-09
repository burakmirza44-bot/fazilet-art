"""Action Dispatch Module.

Provides action dispatching with backend selection integration.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from app.agent_core.backend_policy import BackendPolicy, BackendType
from app.agent_core.backend_result import BackendSelectionResult, SelectionStatus
from app.agent_core.backend_selector import BackendSelector


class DispatchMode(str, Enum):
    """Available dispatch modes for action execution."""

    BRIDGE = "bridge"  # Execute via live bridge connection
    DIRECT = "direct"  # Execute via direct API (e.g., hou module)
    UI = "ui"  # Execute via UI automation
    DRY_RUN = "dry_run"  # Simulation mode - no actual execution


@dataclass(slots=True)
class DispatchConfig:
    """Configuration for action dispatch.

    Controls how actions are dispatched to execution backends,
    including mode preference and fallback behavior.
    """

    mode: DispatchMode = DispatchMode.BRIDGE
    prefer_bridge: bool = True
    fallback_to_ui: bool = True
    dry_run: bool = False
    timeout_seconds: float = 30.0

    def to_backend_policy(self, domain: str = "") -> BackendPolicy:
        """Convert DispatchConfig to BackendPolicy.

        Args:
            domain: Domain name for the policy

        Returns:
            BackendPolicy equivalent to this configuration
        """
        if self.dry_run:
            return BackendPolicy.for_dry_run(domain=domain)

        preferred = self._get_preferred_backend()
        fallback_order = self._get_fallback_order()

        return BackendPolicy(
            preferred_backend=preferred,
            fallback_order=fallback_order,
            fallback_to_ui=self.fallback_to_ui,
            domain=domain,
        )

    def _get_preferred_backend(self) -> BackendType:
        """Get preferred backend type from mode."""
        mode_map = {
            DispatchMode.BRIDGE: BackendType.BRIDGE,
            DispatchMode.DIRECT: BackendType.DIRECT_API,
            DispatchMode.UI: BackendType.UI,
            DispatchMode.DRY_RUN: BackendType.DRY_RUN,
        }
        return mode_map.get(self.mode, BackendType.BRIDGE)

    def _get_fallback_order(self) -> tuple[BackendType, ...]:
        """Get fallback order based on configuration."""
        if self.dry_run:
            return (BackendType.DRY_RUN,)

        order = [BackendType.BRIDGE]

        if self.mode == DispatchMode.DIRECT:
            order.insert(0, BackendType.DIRECT_API)

        if self.fallback_to_ui:
            order.append(BackendType.UI)

        order.append(BackendType.DRY_RUN)

        return tuple(order)


@dataclass(slots=True)
class DispatchDecision:
    """Result of dispatch decision-making.

    Contains the selected execution mode and backend selection result
    for audit and debugging purposes.
    """

    mode: DispatchMode
    selection_result: BackendSelectionResult
    action_id: str | None = None
    timestamp: float = 0.0

    @property
    def is_executable(self) -> bool:
        """Check if this decision allows execution."""
        return self.selection_result.is_executable

    @property
    def is_dry_run(self) -> bool:
        """Check if this is a dry-run decision."""
        return self.mode == DispatchMode.DRY_RUN

    @property
    def used_fallback(self) -> bool:
        """Check if fallback was used."""
        return self.selection_result.used_fallback


class ActionDispatcher:
    """Dispatches actions to appropriate execution backends.

    Integrates with BackendSelector for unified backend selection
    across all action types.
    """

    def __init__(self, selector: BackendSelector | None = None):
        """Initialize the ActionDispatcher.

        Args:
            selector: Optional BackendSelector instance (uses default if None)
        """
        self._selector = selector or BackendSelector()

    def decide(
        self,
        config: DispatchConfig,
        domain: str = "",
        action_context: dict[str, Any] | None = None,
        action_id: str | None = None,
    ) -> DispatchDecision:
        """Make a dispatch decision based on configuration and context.

        Args:
            config: DispatchConfig with preferences
            domain: Target domain (e.g., "touchdesigner", "houdini")
            action_context: Optional context for safety checks
            action_id: Optional action identifier for tracking

        Returns:
            DispatchDecision with selected mode and result
        """
        import time

        policy = config.to_backend_policy(domain)
        selection_result = self._selector.select(policy, action_context)

        # Map backend type to dispatch mode
        mode = self._backend_to_mode(selection_result.selected_backend)

        return DispatchDecision(
            mode=mode,
            selection_result=selection_result,
            action_id=action_id,
            timestamp=time.time(),
        )

    def dispatch(
        self,
        action: dict[str, Any],
        config: DispatchConfig,
        domain: str = "",
        action_id: str | None = None,
    ) -> DispatchDecision:
        """Dispatch an action to the selected backend.

        Args:
            action: Action to dispatch
            config: DispatchConfig with preferences
            domain: Target domain
            action_id: Optional action identifier

        Returns:
            DispatchDecision with execution result
        """
        # Build action context for safety checks
        action_context = self._build_action_context(action)

        # Make the dispatch decision
        decision = self.decide(config, domain, action_context, action_id)

        # Execute based on selected mode
        if decision.is_executable and not decision.is_dry_run:
            self._execute_action(action, decision, domain)

        return decision

    def _backend_to_mode(self, backend: BackendType) -> DispatchMode:
        """Map BackendType to DispatchMode."""
        mapping = {
            BackendType.BRIDGE: DispatchMode.BRIDGE,
            BackendType.DIRECT_API: DispatchMode.DIRECT,
            BackendType.UI: DispatchMode.UI,
            BackendType.DRY_RUN: DispatchMode.DRY_RUN,
            BackendType.NONE: DispatchMode.DRY_RUN,  # Fallback to dry-run for NONE
        }
        return mapping.get(backend, DispatchMode.DRY_RUN)

    def _build_action_context(self, action: dict[str, Any]) -> dict[str, Any]:
        """Build action context for safety checks.

        Args:
            action: Action dictionary

        Returns:
            Context dictionary with relevant fields
        """
        context = {}

        # Extract key-related fields
        if "key" in action:
            context["key"] = action["key"]
        if "keys" in action:
            context["keys"] = action["keys"]
        if "hotkey" in action:
            context["hotkey"] = action["hotkey"]
        if "text" in action:
            context["text"] = action["text"]

        return context

    def _execute_action(
        self,
        action: dict[str, Any],
        decision: DispatchDecision,
        domain: str,
    ) -> None:
        """Execute an action on the selected backend.

        This is a placeholder that should be implemented by domain-specific
        subclasses or through registered executors.

        Args:
            action: Action to execute
            decision: DispatchDecision with execution mode
            domain: Target domain
        """
        # Implementation would route to appropriate executor
        # This is intentionally left as a placeholder for integration
        pass


# Convenience function for quick dispatch decisions
def create_dispatch_decision(
    prefer_bridge: bool = True,
    fallback_to_ui: bool = True,
    dry_run: bool = False,
    domain: str = "",
) -> DispatchDecision:
    """Create a dispatch decision with common options.

    Args:
        prefer_bridge: Prefer bridge mode if available
        fallback_to_ui: Allow UI fallback if bridge unavailable
        dry_run: Force dry-run mode
        domain: Target domain

    Returns:
        DispatchDecision with selected mode
    """
    config = DispatchConfig(
        prefer_bridge=prefer_bridge,
        fallback_to_ui=fallback_to_ui,
        dry_run=dry_run,
    )

    dispatcher = ActionDispatcher()
    return dispatcher.decide(config, domain)