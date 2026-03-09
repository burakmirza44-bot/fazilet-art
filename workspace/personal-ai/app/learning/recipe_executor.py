"""Recipe Executor Module.

Provides recipe execution with backend selection integration,
bridge executors for TD and Houdini, and precondition validation.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from app.agent_core.backend_policy import BackendPolicy, BackendType
from app.agent_core.backend_result import BackendSelectionResult
from app.agent_core.backend_selector import BackendSelector


@dataclass(slots=True)
class PreconditionsReport:
    """Validation report for recipe execution preconditions.

    Follows the same pattern as existing validation reports in the codebase.
    """

    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        """Check if there are any errors."""
        return len(self.errors) > 0

    @property
    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return len(self.warnings) > 0

    def add_error(self, error: str) -> None:
        """Add an error to the report."""
        self.errors.append(error)
        self.valid = False

    def add_warning(self, warning: str) -> None:
        """Add a warning to the report."""
        self.warnings.append(warning)


class BridgeExecutor(ABC):
    """Abstract base class for bridge executors.

    Defines the interface for bridge-based execution across
    different domains (TouchDesigner, Houdini, etc.).
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 9988,
        timeout_seconds: float = 5.0,
    ):
        """Initialize the bridge executor.

        Args:
            host: Bridge server host
            port: Bridge server port
            timeout_seconds: Connection timeout
        """
        self.host = host
        self.port = port
        self.timeout_seconds = timeout_seconds
        self._connected = False

    @abstractmethod
    def ping(self) -> bool:
        """Check if the bridge is available.

        Returns:
            True if bridge is responsive
        """
        pass

    @abstractmethod
    def execute(self, command: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Execute a command on the bridge.

        Args:
            command: Command name to execute
            params: Optional parameters for the command

        Returns:
            Result dictionary with success status and data
        """
        pass

    @abstractmethod
    def execute_step(self, step: dict[str, Any]) -> dict[str, Any]:
        """Execute a recipe step.

        Args:
            step: Step definition dictionary

        Returns:
            Result dictionary with execution outcome
        """
        pass

    def connect(self) -> bool:
        """Connect to the bridge.

        Returns:
            True if connection successful
        """
        self._connected = self.ping()
        return self._connected

    def disconnect(self) -> None:
        """Disconnect from the bridge."""
        self._connected = False

    @property
    def is_connected(self) -> bool:
        """Check if connected to bridge."""
        return self._connected


class TDBridgeExecutor(BridgeExecutor):
    """Bridge executor for TouchDesigner.

    Communicates with TouchDesigner via the live bridge on port 9988.
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 9988,
        timeout_seconds: float = 5.0,
    ):
        """Initialize TD bridge executor.

        Args:
            host: Bridge server host (default: 127.0.0.1)
            port: Bridge server port (default: 9988 for TD)
            timeout_seconds: Connection timeout
        """
        super().__init__(host, port, timeout_seconds)

    def ping(self) -> bool:
        """Check if TouchDesigner bridge is available.

        Returns:
            True if bridge is responsive
        """
        import socket

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout_seconds)
            result = sock.connect_ex((self.host, self.port))
            sock.close()
            return result == 0
        except Exception:
            return False

    def execute(self, command: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Execute a command on TouchDesigner.

        Args:
            command: Command name (e.g., "set_par", "run_script")
            params: Command parameters

        Returns:
            Result dictionary
        """
        # Placeholder for actual bridge communication
        # Real implementation would use the TD live client
        return {
            "success": False,
            "error": "Bridge communication not implemented",
            "command": command,
            "params": params or {},
        }

    def execute_step(self, step: dict[str, Any]) -> dict[str, Any]:
        """Execute a recipe step on TouchDesigner.

        Args:
            step: Step definition with action and parameters

        Returns:
            Execution result
        """
        action = step.get("action", "")
        params = step.get("params", {})

        # Map step actions to bridge commands
        return self.execute(action, params)


class HoudiniBridgeExecutor(BridgeExecutor):
    """Bridge executor for Houdini.

    Communicates with Houdini via the live bridge on port 9989.
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 9989,
        timeout_seconds: float = 5.0,
    ):
        """Initialize Houdini bridge executor.

        Args:
            host: Bridge server host (default: 127.0.0.1)
            port: Bridge server port (default: 9989 for Houdini)
            timeout_seconds: Connection timeout
        """
        super().__init__(host, port, timeout_seconds)

    def ping(self) -> bool:
        """Check if Houdini bridge is available.

        Returns:
            True if bridge is responsive
        """
        import socket

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout_seconds)
            result = sock.connect_ex((self.host, self.port))
            sock.close()
            return result == 0
        except Exception:
            return False

    def execute(self, command: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Execute a command on Houdini.

        Args:
            command: Command name (e.g., "create_node", "set_parm")
            params: Command parameters

        Returns:
            Result dictionary
        """
        # Placeholder for actual bridge communication
        # Real implementation would use the Houdini live client
        return {
            "success": False,
            "error": "Bridge communication not implemented",
            "command": command,
            "params": params or {},
        }

    def execute_step(self, step: dict[str, Any]) -> dict[str, Any]:
        """Execute a recipe step on Houdini.

        Args:
            step: Step definition with action and parameters

        Returns:
            Execution result
        """
        action = step.get("action", "")
        params = step.get("params", {})

        # Map step actions to bridge commands
        return self.execute(action, params)


class RecipeExecutor:
    """Executes recipes with unified backend selection.

    Uses BackendSelector for consistent backend selection across
    all recipe steps, with fallback support and safety integration.
    """

    def __init__(
        self,
        selector: BackendSelector | None = None,
        bridge_executors: dict[str, BridgeExecutor] | None = None,
    ):
        """Initialize the RecipeExecutor.

        Args:
            selector: Optional BackendSelector (creates default if None)
            bridge_executors: Optional dict of domain -> BridgeExecutor
        """
        self._selector = selector or BackendSelector()
        self._bridge_executors = bridge_executors or {}
        self._last_selection: BackendSelectionResult | None = None

    def register_bridge_executor(self, domain: str, executor: BridgeExecutor) -> None:
        """Register a bridge executor for a domain.

        Args:
            domain: Domain name (e.g., "touchdesigner", "houdini")
            executor: BridgeExecutor instance
        """
        self._bridge_executors[domain] = executor

    def validate_preconditions(
        self,
        recipe: dict[str, Any],
        policy: BackendPolicy,
    ) -> PreconditionsReport:
        """Validate preconditions for recipe execution.

        Args:
            recipe: Recipe to validate
            policy: Backend policy for execution

        Returns:
            PreconditionsReport with validation results
        """
        report = PreconditionsReport(valid=True)

        # Check recipe structure
        if "steps" not in recipe:
            report.add_error("Recipe missing 'steps' field")
            return report

        steps = recipe.get("steps", [])
        if not steps:
            report.add_warning("Recipe has no steps to execute")

        # Check step validity
        for i, step in enumerate(steps):
            if not isinstance(step, dict):
                report.add_error(f"Step {i} is not a dictionary")
            elif "action" not in step:
                report.add_error(f"Step {i} missing 'action' field")

        # Check backend availability
        selection = self._selector.select(policy)
        self._last_selection = selection

        if not selection.is_executable:
            report.add_error(f"No available backend: {selection.message}")

        return report

    def execute_recipe(
        self,
        recipe: dict[str, Any],
        policy: BackendPolicy,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Execute a complete recipe.

        Args:
            recipe: Recipe to execute
            policy: Backend policy for execution
            dry_run: Force dry-run mode

        Returns:
            Execution result with step results
        """
        # Validate preconditions
        report = self.validate_preconditions(recipe, policy)
        if not report.valid:
            return {
                "success": False,
                "error": "Precondition validation failed",
                "errors": report.errors,
                "warnings": report.warnings,
            }

        # Override policy if dry_run requested
        if dry_run:
            policy = BackendPolicy.for_dry_run(domain=policy.domain)

        # Select backend
        selection = self._selector.select(policy)
        self._last_selection = selection

        if not selection.is_executable:
            return {
                "success": False,
                "error": f"No executable backend: {selection.message}",
                "selection": selection.to_dict(),
            }

        # Execute steps
        steps = recipe.get("steps", [])
        results = []

        for i, step in enumerate(steps):
            step_result = self.execute_step(step, selection, policy.domain)
            results.append(step_result)

            # Stop on failure unless continue_on_error
            if not step_result.get("success", False):
                if not step.get("continue_on_error", False):
                    return {
                        "success": False,
                        "error": f"Step {i} failed: {step_result.get('error', 'Unknown error')}",
                        "step_index": i,
                        "step_results": results,
                        "selection": selection.to_dict(),
                    }

        return {
            "success": True,
            "step_count": len(steps),
            "step_results": results,
            "selection": selection.to_dict(),
        }

    def execute_step(
        self,
        step: dict[str, Any],
        selection: BackendSelectionResult | None = None,
        domain: str = "",
    ) -> dict[str, Any]:
        """Execute a single recipe step.

        Args:
            step: Step definition to execute
            selection: Optional pre-computed backend selection
            domain: Domain for execution

        Returns:
            Step execution result
        """
        # Use provided selection or create new one
        if selection is None:
            if not domain:
                return {
                    "success": False,
                    "error": "No domain specified and no selection provided",
                }

            policy = BackendPolicy(domain=domain)
            selection = self._selector.select(policy)

        # Route to appropriate executor based on backend type
        backend = selection.selected_backend

        if backend == BackendType.DRY_RUN:
            return self._execute_dry_run(step)

        if backend == BackendType.BRIDGE:
            return self._execute_via_bridge(step, domain or selection.domain)

        if backend == BackendType.UI:
            return self._execute_via_ui(step)

        if backend == BackendType.DIRECT_API:
            return self._execute_via_direct_api(step, domain or selection.domain)

        return {
            "success": False,
            "error": f"No handler for backend type: {backend.value}",
        }

    def _execute_dry_run(self, step: dict[str, Any]) -> dict[str, Any]:
        """Execute step in dry-run mode (simulation).

        Args:
            step: Step to simulate

        Returns:
            Simulated result
        """
        return {
            "success": True,
            "dry_run": True,
            "action": step.get("action", "unknown"),
            "message": f"Dry-run: Would execute {step.get('action', 'unknown')}",
        }

    def _execute_via_bridge(self, step: dict[str, Any], domain: str) -> dict[str, Any]:
        """Execute step via bridge connection.

        Args:
            step: Step to execute
            domain: Target domain

        Returns:
            Execution result from bridge
        """
        executor = self._bridge_executors.get(domain)

        if executor is None:
            # Create default executor
            if domain == "touchdesigner":
                executor = TDBridgeExecutor()
            elif domain == "houdini":
                executor = HoudiniBridgeExecutor()
            else:
                return {
                    "success": False,
                    "error": f"No bridge executor for domain: {domain}",
                }

        return executor.execute_step(step)

    def _execute_via_ui(self, step: dict[str, Any]) -> dict[str, Any]:
        """Execute step via UI automation.

        Args:
            step: Step to execute

        Returns:
            Execution result from UI automation
        """
        # Placeholder for UI automation integration
        # Real implementation would route to UI automation system
        return {
            "success": False,
            "error": "UI automation not implemented",
            "action": step.get("action", "unknown"),
        }

    def _execute_via_direct_api(self, step: dict[str, Any], domain: str) -> dict[str, Any]:
        """Execute step via direct API.

        Args:
            step: Step to execute
            domain: Target domain

        Returns:
            Execution result from direct API
        """
        # Direct API is primarily for Houdini (hou module)
        if domain != "houdini":
            return {
                "success": False,
                "error": f"No direct API for domain: {domain}",
            }

        try:
            import hou

            # Execute using hou module
            action = step.get("action", "")
            params = step.get("params", {})

            # Placeholder for actual hou-based execution
            return {
                "success": True,
                "action": action,
                "message": f"Direct API: Would execute {action}",
            }
        except ImportError:
            return {
                "success": False,
                "error": "Houdini (hou) module not available",
            }

    @property
    def last_selection(self) -> BackendSelectionResult | None:
        """Get the last backend selection result."""
        return self._last_selection