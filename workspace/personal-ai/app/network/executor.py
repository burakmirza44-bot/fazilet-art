"""Network Executor for Parallel and Sequential Execution.

Provides execution strategies for network nodes with support for
parallel execution, timeout handling, and error recovery.
"""

from __future__ import annotations

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(slots=True)
class ExecutorConfig:
    """Configuration for network execution."""

    max_parallel: int = 4
    timeout_seconds: float = 30.0
    retry_count: int = 2
    retry_delay_ms: float = 100.0
    fail_fast: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "max_parallel": self.max_parallel,
            "timeout_seconds": self.timeout_seconds,
            "retry_count": self.retry_count,
            "retry_delay_ms": self.retry_delay_ms,
            "fail_fast": self.fail_fast,
        }


@dataclass
class ExecutionResult:
    """Result of executing a single unit of work."""

    success: bool = False
    output: Any = None
    error: str | None = None
    execution_time_ms: float = 0.0
    retries: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "execution_time_ms": self.execution_time_ms,
            "retries": self.retries,
        }


class NetworkExecutor:
    """Executes network nodes with parallel and sequential support.

    Provides:
    - Parallel execution of independent nodes
    - Timeout handling
    - Retry with exponential backoff
    - Error recovery
    """

    def __init__(self, config: ExecutorConfig | None = None):
        """Initialize the executor.

        Args:
            config: Executor configuration
        """
        self._config = config or ExecutorConfig()
        self._thread_pool = ThreadPoolExecutor(max_workers=self._config.max_parallel)
        self._running_tasks: dict[str, asyncio.Task] = {}

    async def execute_node(
        self,
        node_id: str,
        executor_fn: Callable[[], Any],
        inputs: dict[str, Any] | None = None,
    ) -> ExecutionResult:
        """Execute a single node with timeout and retry.

        Args:
            node_id: Node identifier
            executor_fn: Function to execute
            inputs: Optional inputs for the node

        Returns:
            ExecutionResult with outcome
        """
        start_time = time.perf_counter()
        result = ExecutionResult()

        for attempt in range(self._config.retry_count + 1):
            try:
                # Execute with timeout
                output = await asyncio.wait_for(
                    self._run_async(executor_fn, inputs),
                    timeout=self._config.timeout_seconds,
                )

                result.success = True
                result.output = output
                result.retries = attempt
                result.execution_time_ms = (time.perf_counter() - start_time) * 1000
                return result

            except asyncio.TimeoutError:
                result.error = f"Timeout after {self._config.timeout_seconds}s"
                result.retries = attempt

            except Exception as e:
                result.error = str(e)
                result.retries = attempt

            # Retry delay with exponential backoff
            if attempt < self._config.retry_count:
                delay = self._config.retry_delay_ms * (2 ** attempt) / 1000
                await asyncio.sleep(delay)

        result.execution_time_ms = (time.perf_counter() - start_time) * 1000
        return result

    async def execute_level(
        self,
        node_ids: list[str],
        executor_fns: dict[str, Callable[[], Any]],
        inputs: dict[str, dict[str, Any]] | None = None,
    ) -> dict[str, ExecutionResult]:
        """Execute multiple nodes in parallel.

        Args:
            node_ids: Node IDs to execute
            executor_fns: Map of node ID to executor function
            inputs: Map of node ID to inputs

        Returns:
            Map of node ID to ExecutionResult
        """
        inputs = inputs or {}

        # Create tasks for all nodes
        tasks = {
            node_id: self.execute_node(
                node_id=node_id,
                executor_fn=executor_fns[node_id],
                inputs=inputs.get(node_id),
            )
            for node_id in node_ids
            if node_id in executor_fns
        }

        # Execute all tasks concurrently
        results = {}
        for node_id, task in tasks.items():
            self._running_tasks[node_id] = asyncio.create_task(task)

        # Wait for all tasks
        for node_id, task in self._running_tasks.items():
            try:
                results[node_id] = await task
            except Exception as e:
                results[node_id] = ExecutionResult(
                    success=False,
                    error=str(e),
                )

        # Clear running tasks
        self._running_tasks.clear()

        return results

    async def execute_sequence(
        self,
        node_order: list[list[str]],
        executor_fns: dict[str, Callable[[], Any]],
        inputs: dict[str, dict[str, Any]] | None = None,
        on_level_complete: Callable[[int, dict[str, ExecutionResult]], None] | None = None,
    ) -> dict[str, ExecutionResult]:
        """Execute nodes in sequence by level.

        Args:
            node_order: List of node ID lists (levels)
            executor_fns: Map of node ID to executor function
            inputs: Map of node ID to inputs
            on_level_complete: Callback for level completion

        Returns:
            Map of node ID to ExecutionResult
        """
        all_results: dict[str, ExecutionResult] = {}
        inputs = inputs or {}

        for level, node_ids in enumerate(node_order):
            # Execute level in parallel
            level_results = await self.execute_level(
                node_ids=node_ids,
                executor_fns=executor_fns,
                inputs=inputs,
            )

            all_results.update(level_results)

            # Callback for level completion
            if on_level_complete:
                on_level_complete(level, level_results)

            # Check for failures if fail_fast
            if self._config.fail_fast:
                failures = [nid for nid, res in level_results.items() if not res.success]
                if failures:
                    # Mark remaining nodes as skipped
                    remaining_nodes = [
                        nid
                        for level_nodes in node_order[level + 1:]
                        for nid in level_nodes
                    ]
                    for nid in remaining_nodes:
                        all_results[nid] = ExecutionResult(
                            success=False,
                            error=f"Skipped due to failure in: {failures}",
                        )
                    break

        return all_results

    async def _run_async(
        self,
        fn: Callable[[], Any],
        inputs: dict[str, Any] | None = None,
    ) -> Any:
        """Run a function, handling both sync and async.

        Args:
            fn: Function to run
            inputs: Optional inputs

        Returns:
            Function result
        """
        if asyncio.iscoroutinefunction(fn):
            if inputs:
                return await fn(**inputs)
            return await fn()
        else:
            # Run in thread pool
            loop = asyncio.get_event_loop()
            if inputs:
                return await loop.run_in_executor(
                    self._thread_pool,
                    lambda: fn(**inputs),
                )
            return await loop.run_in_executor(self._thread_pool, fn)

    def cancel(self, node_id: str) -> bool:
        """Cancel a running task.

        Args:
            node_id: Node ID to cancel

        Returns:
            True if task was cancelled
        """
        task = self._running_tasks.get(node_id)
        if task and not task.done():
            task.cancel()
            return True
        return False

    def cancel_all(self) -> int:
        """Cancel all running tasks.

        Returns:
            Number of tasks cancelled
        """
        count = 0
        for node_id, task in self._running_tasks.items():
            if not task.done():
                task.cancel()
                count += 1
        self._running_tasks.clear()
        return count

    def shutdown(self) -> None:
        """Shutdown the executor."""
        self.cancel_all()
        self._thread_pool.shutdown(wait=False)


class SyncNetworkExecutor:
    """Synchronous wrapper for NetworkExecutor.

    Provides a synchronous interface for the async executor.
    """

    def __init__(self, config: ExecutorConfig | None = None):
        """Initialize the sync executor.

        Args:
            config: Executor configuration
        """
        self._executor = NetworkExecutor(config)

    def execute_node(
        self,
        node_id: str,
        executor_fn: Callable[[], Any],
        inputs: dict[str, Any] | None = None,
    ) -> ExecutionResult:
        """Execute a single node synchronously.

        Args:
            node_id: Node identifier
            executor_fn: Function to execute
            inputs: Optional inputs

        Returns:
            ExecutionResult
        """
        return asyncio.run(
            self._executor.execute_node(node_id, executor_fn, inputs)
        )

    def execute_level(
        self,
        node_ids: list[str],
        executor_fns: dict[str, Callable[[], Any]],
        inputs: dict[str, dict[str, Any]] | None = None,
    ) -> dict[str, ExecutionResult]:
        """Execute multiple nodes in parallel synchronously.

        Args:
            node_ids: Node IDs to execute
            executor_fns: Map of node ID to executor function
            inputs: Map of node ID to inputs

        Returns:
            Map of node ID to ExecutionResult
        """
        return asyncio.run(
            self._executor.execute_level(node_ids, executor_fns, inputs)
        )

    def execute_sequence(
        self,
        node_order: list[list[str]],
        executor_fns: dict[str, Callable[[], Any]],
        inputs: dict[str, dict[str, Any]] | None = None,
        on_level_complete: Callable[[int, dict[str, ExecutionResult]], None] | None = None,
    ) -> dict[str, ExecutionResult]:
        """Execute nodes in sequence synchronously.

        Args:
            node_order: List of node ID lists (levels)
            executor_fns: Map of node ID to executor function
            inputs: Map of node ID to inputs
            on_level_complete: Callback for level completion

        Returns:
            Map of node ID to ExecutionResult
        """
        return asyncio.run(
            self._executor.execute_sequence(
                node_order, executor_fns, inputs, on_level_complete
            )
        )

    def shutdown(self) -> None:
        """Shutdown the executor."""
        self._executor.shutdown()