"""Backend Policy Data Models.

Defines the policy configuration for backend selection, including
preferences, fallback order, safety requirements, and domain-specific factory methods.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class BackendType(str, Enum):
    """Available execution backend types."""

    BRIDGE = "bridge"  # Live bridge connection (TD/Houdini)
    DIRECT_API = "direct_api"  # Direct API (e.g., hou module)
    UI = "ui"  # UI automation fallback
    DRY_RUN = "dry_run"  # Simulation mode
    NONE = "none"  # No safe backend available


@dataclass(slots=True)
class BackendPolicy:
    """Policy configuration for backend selection.

    Controls how the BackendSelector chooses which execution backend to use,
    including preferences, fallback order, safety requirements, and timing.
    """

    # Backend preferences
    preferred_backend: BackendType = BackendType.BRIDGE
    fallback_order: tuple[BackendType, ...] = (
        BackendType.BRIDGE,
        BackendType.UI,
        BackendType.DRY_RUN,
    )
    fallback_to_ui: bool = True

    # Safety
    require_window_focus: bool = True
    respect_killswitch: bool = True
    validate_blocked_inputs: bool = True

    # Domain
    domain: str = ""
    expected_window_hints: tuple[str, ...] = ()

    # Timing
    bridge_timeout_seconds: float = 5.0
    bridge_host: str = "127.0.0.1"
    bridge_port: int | None = None

    @classmethod
    def for_touchdesigner(
        cls,
        preferred_backend: BackendType = BackendType.BRIDGE,
        fallback_to_ui: bool = True,
        bridge_port: int = 9988,
        **overrides,
    ) -> BackendPolicy:
        """Create a BackendPolicy configured for TouchDesigner.

        Args:
            preferred_backend: Preferred backend type (default: BRIDGE)
            fallback_to_ui: Whether to allow UI fallback (default: True)
            bridge_port: Bridge port for TouchDesigner (default: 9988)
            **overrides: Additional policy overrides

        Returns:
            BackendPolicy configured for TouchDesigner execution
        """
        fallback_order = (
            BackendType.BRIDGE,
            BackendType.UI,
            BackendType.DRY_RUN,
        ) if fallback_to_ui else (BackendType.BRIDGE, BackendType.DRY_RUN)

        # Set defaults only if not provided in overrides
        if "expected_window_hints" not in overrides:
            overrides["expected_window_hints"] = ("TouchDesigner", "TouchDesigner099", "TD")

        return cls(
            preferred_backend=preferred_backend,
            fallback_order=fallback_order,
            fallback_to_ui=fallback_to_ui,
            domain="touchdesigner",
            bridge_port=bridge_port,
            **overrides,
        )

    @classmethod
    def for_houdini(
        cls,
        preferred_backend: BackendType = BackendType.BRIDGE,
        bridge_port: int = 9989,
        **overrides,
    ) -> BackendPolicy:
        """Create a BackendPolicy configured for Houdini.

        Note: Houdini has NO UI fallback - it only supports BRIDGE and DRY_RUN.

        Args:
            preferred_backend: Preferred backend type (default: BRIDGE)
            bridge_port: Bridge port for Houdini (default: 9989)
            **overrides: Additional policy overrides

        Returns:
            BackendPolicy configured for Houdini execution
        """
        # Houdini has no UI fallback - only BRIDGE and DRY_RUN
        fallback_order = (BackendType.BRIDGE, BackendType.DRY_RUN)

        # Set defaults only if not provided in overrides
        if "expected_window_hints" not in overrides:
            overrides["expected_window_hints"] = ("Houdini", "houdini", "HIP")

        return cls(
            preferred_backend=preferred_backend,
            fallback_order=fallback_order,
            fallback_to_ui=False,  # Houdini has no UI fallback
            domain="houdini",
            bridge_port=bridge_port,
            **overrides,
        )

    @classmethod
    def for_dry_run(cls, domain: str = "", **overrides) -> BackendPolicy:
        """Create a BackendPolicy configured for dry-run mode.

        Args:
            domain: Domain name for logging
            **overrides: Additional policy overrides

        Returns:
            BackendPolicy configured for dry-run (simulation) mode
        """
        return cls(
            preferred_backend=BackendType.DRY_RUN,
            fallback_order=(BackendType.DRY_RUN,),
            fallback_to_ui=False,
            domain=domain,
            require_window_focus=False,
            **overrides,
        )

    def allows_backend(self, backend: BackendType) -> bool:
        """Check if a backend type is allowed by this policy.

        Args:
            backend: Backend type to check

        Returns:
            True if the backend is in the fallback order
        """
        return backend in self.fallback_order

    def get_effective_fallback_order(self) -> tuple[BackendType, ...]:
        """Get the effective fallback order, respecting UI fallback setting.

        Returns:
            Tuple of backend types in fallback priority order
        """
        if not self.fallback_to_ui:
            return tuple(b for b in self.fallback_order if b != BackendType.UI)
        return self.fallback_order