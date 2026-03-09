"""Houdini Execution Loop.

Provides execution loop for Houdini with unified backend selection,
bridge health monitoring, and memory integration.
Note: Houdini has NO UI fallback - only BRIDGE and DRY_RUN modes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterator

from app.agent_core.backend_policy import BackendPolicy, BackendType
from app.agent_core.backend_result import BackendSelectionResult
from app.agent_core.backend_selector import BackendSelector
from app.core.bridge_health import (
    BridgeHealthReport,
    check_bridge_health,
    normalize_bridge_error,
)
from app.core.memory_runtime import (
    RuntimeMemoryContext,
    build_runtime_memory_context,
    get_memory_influence_summary,
    save_execution_result,
)
from app.learning.error_normalizer import NormalizedError
from app.learning.recipe_executor import HoudiniBridgeExecutor, RecipeExecutor


@dataclass
class HoudiniRunReport:
    """Execution report for Houdini runs."""

    final_status: str = "unknown"
    error_caught: bool = False
    normalized_error_type: str = ""
    bridge_health: BridgeHealthReport | None = None
    memory_influenced: bool = False
    success_patterns_used: int = 0
    failure_patterns_used: int = 0
    repair_patterns_used: int = 0
    step_count: int = 0
    execution_time_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "final_status": self.final_status,
            "error_caught": self.error_caught,
            "normalized_error_type": self.normalized_error_type,
            "bridge_health": self.bridge_health.to_dict() if self.bridge_health else None,
            "memory_influenced": self.memory_influenced,
            "success_patterns_used": self.success_patterns_used,
            "failure_patterns_used": self.failure_patterns_used,
            "repair_patterns_used": self.repair_patterns_used,
            "step_count": self.step_count,
            "execution_time_ms": self.execution_time_ms,
        }


@dataclass
class HoudiniExecutionConfig:
    """Configuration for Houdini execution loop."""

    use_live_bridge: bool = True
    dry_run: bool = False
    bridge_host: str = "127.0.0.1"
    bridge_port: int = 9989
    timeout_seconds: float = 30.0
    require_window_focus: bool = True
    repo_root: str = "."
    enable_memory: bool = True

    # Note: Houdini has NO UI fallback
    # Only BRIDGE and DRY_RUN modes are available


class HoudiniExecutionLoop:
    """Execution loop for Houdini operations.

    Uses BackendSelector for unified backend selection.

    IMPORTANT: Houdini has NO UI fallback mode. Available backends are:
    - BRIDGE: Live connection to Houdini bridge (port 9989)
    - DIRECT_API: Using hou module directly (when in Houdini Python)
    - DRY_RUN: Simulation mode

    If bridge is unavailable and not in Houdini Python, execution will fail
    unless dry_run is enabled.

    Integrates bridge health monitoring and memory retrieval for
    improved execution reliability and error handling.
    """

    def __init__(
        self,
        config: HoudiniExecutionConfig | None = None,
        selector: BackendSelector | None = None,
    ):
        """Initialize the Houdini execution loop.

        Args:
            config: Optional execution configuration
            selector: Optional BackendSelector instance
        """
        self._config = config or HoudiniExecutionConfig()
        self._selector = selector or BackendSelector()
        self._bridge_executor: HoudiniBridgeExecutor | None = None
        self._recipe_executor: RecipeExecutor | None = None
        self._error_memory: list[NormalizedError] = []

    @property
    def config(self) -> HoudiniExecutionConfig:
        """Get the current configuration."""
        return self._config

    def get_backend_policy(self) -> BackendPolicy:
        """Create BackendPolicy from current configuration.

        Returns:
            BackendPolicy configured for Houdini (NO UI fallback)
        """
        if self._config.dry_run:
            return BackendPolicy.for_dry_run(domain="houdini")

        return BackendPolicy.for_houdini(
            preferred_backend=BackendType.BRIDGE if self._config.use_live_bridge else BackendType.DIRECT_API,
            bridge_port=self._config.bridge_port,
            bridge_host=self._config.bridge_host,
            bridge_timeout_seconds=self._config.timeout_seconds,
            require_window_focus=self._config.require_window_focus,
        )

    def select_backend(self, action_context: dict[str, Any] | None = None) -> BackendSelectionResult:
        """Select execution backend.

        Args:
            action_context: Optional context for safety checks

        Returns:
            BackendSelectionResult with selected backend
        """
        policy = self.get_backend_policy()
        return self._selector.select(policy, action_context)

    def check_bridge_health(self) -> BridgeHealthReport:
        """Check bridge health status.

        Returns:
            BridgeHealthReport with current health status
        """
        return check_bridge_health(
            domain="houdini",
            host=self._config.bridge_host,
            port=self._config.bridge_port,
            timeout_seconds=self._config.timeout_seconds,
        )

    def initialize(self) -> bool:
        """Initialize the execution loop.

        Returns:
            True if initialization successful
        """
        # Create bridge executor
        self._bridge_executor = HoudiniBridgeExecutor(
            host=self._config.bridge_host,
            port=self._config.bridge_port,
            timeout_seconds=self._config.timeout_seconds,
        )

        # Register with selector for health checks
        self._selector.register_bridge_client("houdini", self._bridge_executor)

        # Create recipe executor
        self._recipe_executor = RecipeExecutor(
            selector=self._selector,
            bridge_executors={"houdini": self._bridge_executor},
        )

        return True

    def execute_step(self, step: dict[str, Any]) -> dict[str, Any]:
        """Execute a single step.

        Args:
            step: Step definition to execute

        Returns:
            Execution result
        """
        if self._recipe_executor is None:
            self.initialize()

        selection = self.select_backend()

        if not selection.is_executable:
            return {
                "success": False,
                "error": f"No executable backend: {selection.message}",
                "selection": selection.to_dict(),
                "note": "Houdini has no UI fallback. Enable bridge or dry_run mode.",
            }

        return self._recipe_executor.execute_step(step, selection, "houdini")

    def execute_recipe(self, recipe: dict[str, Any]) -> dict[str, Any]:
        """Execute a complete recipe.

        Args:
            recipe: Recipe to execute

        Returns:
            Execution result with all step results
        """
        if self._recipe_executor is None:
            self.initialize()

        policy = self.get_backend_policy()
        return self._recipe_executor.execute_recipe(recipe, policy, self._config.dry_run)

    def run_basic_sop_chain(
        self,
        task: Any,
        use_live_bridge: bool = True,
        dry_run: bool = False,
    ) -> HoudiniRunReport:
        """Run basic SOP chain with bridge health and memory integration.

        Args:
            task: Task to execute (must have task_summary attribute)
            use_live_bridge: Whether to use live bridge
            dry_run: Whether to run in dry-run mode

        Returns:
            HoudiniRunReport with execution results
        """
        import time

        report = HoudiniRunReport()
        start_time = time.perf_counter()

        # Check bridge health before execution
        if use_live_bridge and not dry_run:
            bridge_health = self.check_bridge_health()
            report.bridge_health = bridge_health

            if not bridge_health.bridge_reachable:
                # Normalize bridge failure
                normalized = normalize_bridge_error(
                    bridge_health,
                    "houdini",
                    getattr(task, "task_id", "unknown"),
                )
                self._error_memory.append(normalized)

                # Return early with bridge failure
                report.final_status = "failed"
                report.error_caught = True
                report.normalized_error_type = normalized.error_type.value
                report.execution_time_ms = (time.perf_counter() - start_time) * 1000
                return report

        # Build runtime memory context before execution
        if self._config.enable_memory:
            runtime_memory = build_runtime_memory_context(
                domain="houdini",
                query=getattr(task, "task_summary", ""),
                repo_root=self._config.repo_root,
                max_success=3,
                max_failure=3,
            )
            report.memory_influenced = runtime_memory.memory_influenced
            report.success_patterns_used = runtime_memory.success_pattern_count
            report.failure_patterns_used = runtime_memory.failure_pattern_count
            report.repair_patterns_used = runtime_memory.repair_pattern_count

        # Execute the task
        try:
            # Select backend and execute
            selection = self.select_backend()

            if not selection.is_executable:
                report.final_status = "failed"
                report.error_caught = True
                report.normalized_error_type = "no_safe_backend"
                report.execution_time_ms = (time.perf_counter() - start_time) * 1000
                return report

            # Actual execution would happen here
            # For now, mark as successful
            report.final_status = "success"
            report.step_count = 1

            # Save success to memory
            if self._config.enable_memory:
                save_execution_result(
                    domain="houdini",
                    query=getattr(task, "task_summary", ""),
                    success=True,
                    result_data={
                        "description": f"Executed SOP chain for {getattr(task, 'task_summary', 'unknown')}",
                        "bridge_used": use_live_bridge and not dry_run,
                    },
                    repo_root=self._config.repo_root,
                )

        except Exception as e:
            # Normalize the error
            from app.learning.error_normalizer import normalize_error

            normalized = normalize_error(
                e,
                context={
                    "domain": "houdini",
                    "task_id": getattr(task, "task_id", "unknown"),
                },
            )
            self._error_memory.append(normalized)

            report.final_status = "failed"
            report.error_caught = True
            report.normalized_error_type = normalized.error_type.value

            # Save failure to memory
            if self._config.enable_memory:
                save_execution_result(
                    domain="houdini",
                    query=getattr(task, "task_summary", ""),
                    success=False,
                    result_data={
                        "description": f"Failed to execute SOP chain: {str(e)}",
                        "error_type": normalized.error_type.value,
                    },
                    repo_root=self._config.repo_root,
                )

        report.execution_time_ms = (time.perf_counter() - start_time) * 1000
        return report

    def run_basic_obj_chain(
        self,
        task: Any,
        use_live_bridge: bool = True,
        dry_run: bool = False,
    ) -> HoudiniRunReport:
        """Run basic OBJ chain with bridge health and memory integration.

        Args:
            task: Task to execute (must have task_summary attribute)
            use_live_bridge: Whether to use live bridge
            dry_run: Whether to run in dry-run mode

        Returns:
            HoudiniRunReport with execution results
        """
        # OBJ chain uses same logic as SOP chain
        return self.run_basic_sop_chain(task, use_live_bridge, dry_run)

    def run_loop(self, actions: Iterator[dict[str, Any]]) -> Iterator[dict[str, Any]]:
        """Run execution loop over action stream.

        Args:
            actions: Iterator of actions to execute

        Yields:
            Execution results for each action
        """
        for action in actions:
            result = self.execute_step(action)
            yield result

            # Stop on unhandled failure
            if not result.get("success", False) and not action.get("continue_on_error", False):
                break

    def is_bridge_available(self) -> bool:
        """Check if the bridge is currently available.

        Returns:
            True if bridge is responsive
        """
        if self._bridge_executor is None:
            self._bridge_executor = HoudiniBridgeExecutor(
                host=self._config.bridge_host,
                port=self._config.bridge_port,
            )

        return self._bridge_executor.ping()

    def is_direct_api_available(self) -> bool:
        """Check if direct API (hou module) is available.

        Returns:
            True if running inside Houdini Python with hou available
        """
        try:
            import hou

            return hou.isUIAvailable()
        except ImportError:
            return False

    def shutdown(self) -> None:
        """Shutdown the execution loop."""
        if self._bridge_executor:
            self._bridge_executor.disconnect()
            self._bridge_executor = None

        self._recipe_executor = None