"""Network Orchestrator for Multi-Agent Execution.

Provides the main orchestration logic for executing networks
with proper coordination, error handling, and checkpoint support.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable

from app.network.context import NetworkContext, create_context
from app.network.executor import ExecutorConfig, NetworkExecutor, SyncNetworkExecutor
from app.network.graph import NetworkGraph, ValidationResult
from app.network.models import (
    NetworkNode,
    NetworkResult,
    NodeResult,
    NodeStatus,
    NodeType,
    OrchestratorConfig,
)
from app.network.node_types import NodeExecutor, get_executor


@dataclass
class OrchestrationHooks:
    """Hooks for orchestration lifecycle events."""

    on_node_start: Callable[[str, NetworkNode], None] | None = None
    on_node_complete: Callable[[str, NodeResult], None] | None = None
    on_level_start: Callable[[int, list[str]], None] | None = None
    on_level_complete: Callable[[int, dict[str, NodeResult]], None] | None = None
    on_error: Callable[[str, Exception], None] | None = None


class NetworkOrchestrator:
    """Orchestrates network execution with proper coordination.

    Features:
    - Topological execution order
    - Parallel execution of independent nodes
    - Error handling and retry
    - Memory integration
    - Checkpoint support
    - Lifecycle hooks
    """

    def __init__(
        self,
        graph: NetworkGraph,
        config: OrchestratorConfig | None = None,
        context: NetworkContext | None = None,
    ):
        """Initialize the orchestrator.

        Args:
            graph: Network graph to execute
            config: Orchestration configuration
            context: Optional pre-created context
        """
        self._graph = graph
        self._config = config or OrchestratorConfig()
        self._context = context
        self._executor: NetworkExecutor | None = None
        self._node_executors: dict[NodeType, NodeExecutor] = {}
        self._hooks = OrchestrationHooks()
        self._current_result: NetworkResult | None = None

    def set_hooks(self, hooks: OrchestrationHooks) -> None:
        """Set lifecycle hooks.

        Args:
            hooks: Hooks to set
        """
        self._hooks = hooks

    def register_node_executor(self, node_type: NodeType, executor: NodeExecutor) -> None:
        """Register a custom executor for a node type.

        Args:
            node_type: Node type
            executor: Executor instance
        """
        self._node_executors[node_type] = executor

    def validate(self) -> ValidationResult:
        """Validate the network before execution.

        Returns:
            ValidationResult with any issues
        """
        return self._graph.validate()

    async def execute(
        self,
        input_data: dict[str, Any],
        context: NetworkContext | None = None,
    ) -> NetworkResult:
        """Execute the network asynchronously.

        Args:
            input_data: Input data for the network
            context: Optional execution context (creates new if None)

        Returns:
            NetworkResult with execution outcome
        """
        start_time = time.perf_counter()

        # Create or use provided context
        ctx = context or self._context or create_context(domain=self._graph.domain)

        # Initialize result
        result = NetworkResult(
            network_name=self._graph.name,
            success=False,
        )
        self._current_result = result

        # Validate network
        validation = self.validate()
        if not validation.valid:
            result.error = f"Network validation failed: {'; '.join(validation.errors)}"
            result.total_execution_time_ms = (time.perf_counter() - start_time) * 1000
            return result

        # Get execution order
        execution_order = self._graph.get_execution_order()
        result.execution_order = execution_order

        # Initialize executor
        executor_config = ExecutorConfig(
            max_parallel=self._config.max_parallel_nodes,
            timeout_seconds=self._config.default_timeout_seconds,
            retry_count=self._config.retry_count,
            retry_delay_ms=self._config.retry_delay_ms,
            fail_fast=self._config.fail_fast,
        )
        self._executor = NetworkExecutor(executor_config)

        try:
            # Execute each level
            for level_idx, level_nodes in enumerate(execution_order):
                # Call level start hook
                if self._hooks.on_level_start:
                    self._hooks.on_level_start(level_idx, level_nodes)

                # Execute level
                level_results = await self._execute_level(level_nodes, input_data, ctx)

                # Add results
                for node_id, node_result in level_results.items():
                    result.add_node_result(node_result)

                # Call level complete hook
                if self._hooks.on_level_complete:
                    self._hooks.on_level_complete(level_idx, level_results)

                # Check for failures
                failures = [nid for nid, res in level_results.items() if res.status == NodeStatus.FAILED]
                if failures and self._config.fail_fast:
                    result.error = f"Execution stopped due to failures in nodes: {failures}"
                    break

            # Determine overall success
            result.success = not result.has_errors() and result.nodes_failed == 0

        except Exception as e:
            result.error = f"Orchestration error: {e}"
            if self._hooks.on_error:
                self._hooks.on_error("orchestrator", e)

        finally:
            result.total_execution_time_ms = (time.perf_counter() - start_time) * 1000
            result.context_snapshot = ctx.snapshot()

            if self._executor:
                self._executor.shutdown()

        return result

    def execute_sync(
        self,
        input_data: dict[str, Any],
        context: NetworkContext | None = None,
    ) -> NetworkResult:
        """Execute the network synchronously.

        Args:
            input_data: Input data for the network
            context: Optional execution context

        Returns:
            NetworkResult with execution outcome
        """
        import asyncio
        return asyncio.run(self.execute(input_data, context))

    async def _execute_level(
        self,
        node_ids: list[str],
        input_data: dict[str, Any],
        context: NetworkContext,
    ) -> dict[str, NodeResult]:
        """Execute a level of nodes.

        Args:
            node_ids: Node IDs in this level
            input_data: Input data
            context: Execution context

        Returns:
            Map of node ID to NodeResult
        """
        results: dict[str, NodeResult] = {}

        # Build executor functions for each node
        executor_fns = {}
        for node_id in node_ids:
            node = self._graph.get_node(node_id)
            if node:
                executor_fns[node_id] = self._create_node_executor(node, input_data, context)

        # Execute all nodes in parallel
        if self._executor:
            execution_results = await self._executor.execute_level(
                node_ids=node_ids,
                executor_fns=executor_fns,
            )

            # Convert to NodeResult
            for node_id, exec_result in execution_results.items():
                node_result = NodeResult(
                    node_id=node_id,
                    status=NodeStatus.COMPLETED if exec_result.success else NodeStatus.FAILED,
                    outputs=exec_result.output if isinstance(exec_result.output, dict) else {"output": exec_result.output},
                    error=exec_result.error,
                    execution_time_ms=exec_result.execution_time_ms,
                    retries=exec_result.retries,
                )
                results[node_id] = node_result

                # Update context with outputs
                node = self._graph.get_node(node_id)
                if node and isinstance(exec_result.output, dict):
                    context.set_output(node_id, exec_result.output)

        return results

    def _create_node_executor(
        self,
        node: NetworkNode,
        input_data: dict[str, Any],
        context: NetworkContext,
    ) -> Callable[[], Any]:
        """Create an executor function for a node.

        Args:
            node: Node to create executor for
            input_data: Input data
            context: Execution context

        Returns:
            Async callable that executes the node
        """
        async def execute_node() -> Any:
            # Call node start hook
            if self._hooks.on_node_start:
                self._hooks.on_node_start(node.node_id, node)

            # Get inputs for this node
            node_inputs = self._get_node_inputs(node, input_data, context)

            # Get executor for node type
            executor = self._node_executors.get(node.node_type)
            if executor is None:
                executor = get_executor(node.node_type)

            # Execute
            result = await executor.execute(node, node_inputs, context)

            # Call node complete hook
            if self._hooks.on_node_complete:
                self._hooks.on_node_complete(node.node_id, result)

            return result.outputs

        return execute_node

    def _get_node_inputs(
        self,
        node: NetworkNode,
        input_data: dict[str, Any],
        context: NetworkContext,
    ) -> dict[str, Any]:
        """Get inputs for a node from predecessors.

        Args:
            node: Target node
            input_data: Original input data
            context: Execution context

        Returns:
            Input dictionary for the node
        """
        inputs: dict[str, Any] = {}

        # Get incoming edges
        incoming_edges = self._graph.get_incoming_edges(node.node_id)

        if not incoming_edges:
            # Source node - use input data directly
            inputs = input_data.copy()
        else:
            # Get outputs from predecessors
            for edge in incoming_edges:
                source_output = context.get_output(edge.source_node, edge.source_port)
                if source_output is not None:
                    # Apply transformation if defined
                    value = edge.apply_transform(source_output)
                    inputs[edge.target_port] = value

        return inputs

    def get_current_result(self) -> NetworkResult | None:
        """Get the current execution result.

        Returns:
            Current NetworkResult or None if not started
        """
        return self._current_result


class SyncNetworkOrchestrator:
    """Synchronous wrapper for NetworkOrchestrator.

    Provides a simpler interface for synchronous execution.
    """

    def __init__(
        self,
        graph: NetworkGraph,
        config: OrchestratorConfig | None = None,
    ):
        """Initialize the sync orchestrator.

        Args:
            graph: Network graph to execute
            config: Orchestration configuration
        """
        self._orchestrator = NetworkOrchestrator(graph, config)

    def execute(
        self,
        input_data: dict[str, Any],
        domain: str = "",
        repo_root: str = ".",
    ) -> NetworkResult:
        """Execute the network synchronously.

        Args:
            input_data: Input data
            domain: Execution domain
            repo_root: Repository root for memory

        Returns:
            NetworkResult
        """
        context = create_context(
            domain=domain or self._orchestrator._graph.domain,
            repo_root=repo_root,
        )
        return self._orchestrator.execute_sync(input_data, context)

    def set_hooks(self, hooks: OrchestrationHooks) -> None:
        """Set lifecycle hooks."""
        self._orchestrator.set_hooks(hooks)

    def validate(self) -> ValidationResult:
        """Validate the network."""
        return self._orchestrator.validate()


def create_orchestrator(
    graph: NetworkGraph,
    max_parallel: int = 4,
    timeout_seconds: float = 30.0,
    retry_count: int = 2,
    fail_fast: bool = True,
) -> NetworkOrchestrator:
    """Create an orchestrator with common configuration.

    Args:
        graph: Network graph
        max_parallel: Maximum parallel nodes
        timeout_seconds: Default timeout
        retry_count: Number of retries
        fail_fast: Stop on first failure

    Returns:
        Configured NetworkOrchestrator
    """
    config = OrchestratorConfig(
        max_parallel_nodes=max_parallel,
        default_timeout_seconds=timeout_seconds,
        retry_count=retry_count,
        fail_fast=fail_fast,
    )
    return NetworkOrchestrator(graph, config)