"""Network Execution Context.

Provides shared context between nodes during network execution,
including input/output tracking, memory, and execution state.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4


@dataclass
class ExecutionContext:
    """Shared execution context for network runs.

    Maintains:
    - Node inputs/outputs
    - Memory patterns
    - Execution state
    - Variables for conditional evaluation
    """

    execution_id: str = field(default_factory=lambda: str(uuid4())[:8])
    session_id: str = ""
    task_id: str = ""
    domain: str = ""
    start_time: float = field(default_factory=time.time)

    # Node outputs: node_id -> {port_name: value}
    _node_outputs: dict[str, dict[str, Any]] = field(default_factory=dict)

    # Memory patterns retrieved during execution
    _memory_patterns: dict[str, list[dict]] = field(default_factory=dict)

    # Variables for conditional evaluation
    _variables: dict[str, Any] = field(default_factory=dict)

    # Execution metadata
    _metadata: dict[str, Any] = field(default_factory=dict)

    # Error tracking
    _errors: list[dict[str, Any]] = field(default_factory=list)

    def set_node_output(self, node_id: str, port: str, value: Any) -> None:
        """Set output value for a node port."""
        if node_id not in self._node_outputs:
            self._node_outputs[node_id] = {}
        self._node_outputs[node_id][port] = value

    def get_node_output(self, node_id: str, port: str) -> Any:
        """Get output value from a node port."""
        return self._node_outputs.get(node_id, {}).get(port)

    def get_all_node_outputs(self, node_id: str) -> dict[str, Any]:
        """Get all outputs from a node."""
        return self._node_outputs.get(node_id, {}).copy()

    def set_memory_patterns(self, key: str, patterns: list[dict]) -> None:
        """Store memory patterns for a key."""
        self._memory_patterns[key] = patterns

    def get_memory_patterns(self, key: str) -> list[dict]:
        """Get memory patterns for a key."""
        return self._memory_patterns.get(key, [])

    def set_variable(self, name: str, value: Any) -> None:
        """Set a variable for conditional evaluation."""
        self._variables[name] = value

    def get_variable(self, name: str, default: Any = None) -> Any:
        """Get a variable value."""
        return self._variables.get(name, default)

    def get_variables(self) -> dict[str, Any]:
        """Get all variables."""
        return self._variables.copy()

    def set_metadata(self, key: str, value: Any) -> None:
        """Set execution metadata."""
        self._metadata[key] = value

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get execution metadata."""
        return self._metadata.get(key, default)

    def add_error(self, node_id: str, error: str, details: dict[str, Any] | None = None) -> None:
        """Record an error."""
        self._errors.append({
            "node_id": node_id,
            "error": error,
            "details": details or {},
            "timestamp": time.time(),
        })

    def get_errors(self) -> list[dict[str, Any]]:
        """Get all recorded errors."""
        return self._errors.copy()

    def has_errors(self) -> bool:
        """Check if any errors occurred."""
        return len(self._errors) > 0

    def get_execution_time_ms(self) -> float:
        """Get elapsed execution time in milliseconds."""
        return (time.time() - self.start_time) * 1000

    def to_dict(self) -> dict[str, Any]:
        """Serialize context to dictionary."""
        return {
            "execution_id": self.execution_id,
            "session_id": self.session_id,
            "task_id": self.task_id,
            "domain": self.domain,
            "start_time": self.start_time,
            "execution_time_ms": self.get_execution_time_ms(),
            "node_outputs": self._node_outputs,
            "memory_patterns": {k: v for k, v in self._memory_patterns.items()},
            "variables": self._variables,
            "metadata": self._metadata,
            "errors": self._errors,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExecutionContext:
        """Deserialize context from dictionary."""
        ctx = cls(
            execution_id=data.get("execution_id", str(uuid4())[:8]),
            session_id=data.get("session_id", ""),
            task_id=data.get("task_id", ""),
            domain=data.get("domain", ""),
            start_time=data.get("start_time", time.time()),
        )
        ctx._node_outputs = data.get("node_outputs", {})
        ctx._memory_patterns = data.get("memory_patterns", {})
        ctx._variables = data.get("variables", {})
        ctx._metadata = data.get("metadata", {})
        ctx._errors = data.get("errors", [])
        return ctx


class NetworkContext:
    """High-level network execution context.

    Provides:
    - Shared state management
    - Memory integration
    - Variable evaluation
    - Checkpoint support
    """

    def __init__(
        self,
        domain: str = "",
        session_id: str = "",
        task_id: str = "",
        repo_root: str = ".",
    ):
        """Initialize network context.

        Args:
            domain: Execution domain
            session_id: Session identifier
            task_id: Task identifier
            repo_root: Repository root for memory stores
        """
        self._ctx = ExecutionContext(
            domain=domain,
            session_id=session_id,
            task_id=task_id,
        )
        self._repo_root = repo_root
        self._memory_enabled = True
        self._checkpoints_enabled = True

    @property
    def execution_id(self) -> str:
        """Get execution ID."""
        return self._ctx.execution_id

    @property
    def domain(self) -> str:
        """Get execution domain."""
        return self._ctx.domain

    @property
    def session_id(self) -> str:
        """Get session ID."""
        return self._ctx.session_id

    @property
    def task_id(self) -> str:
        """Get task ID."""
        return self._ctx.task_id

    def set_input(self, node_id: str, port: str, value: Any) -> None:
        """Set input value for a node (stored as node output for source nodes)."""
        self._ctx.set_node_output(node_id, port, value)

    def get_input(self, node_id: str, port: str) -> Any:
        """Get input value for a node from predecessor outputs."""
        return self._ctx.get_node_output(node_id, port)

    def set_output(self, node_id: str, outputs: dict[str, Any]) -> None:
        """Set all outputs for a node."""
        for port, value in outputs.items():
            self._ctx.set_node_output(node_id, port, value)

    def get_output(self, node_id: str, port: str = "output") -> Any:
        """Get output from a node."""
        return self._ctx.get_node_output(node_id, port)

    def get_all_outputs(self, node_id: str) -> dict[str, Any]:
        """Get all outputs from a node."""
        return self._ctx.get_all_node_outputs(node_id)

    def set_variable(self, name: str, value: Any) -> None:
        """Set a variable for conditional evaluation."""
        self._ctx.set_variable(name, value)

    def get_variable(self, name: str, default: Any = None) -> Any:
        """Get a variable value."""
        return self._ctx.get_variable(name, default)

    def evaluate_condition(self, condition: str) -> bool:
        """Evaluate a condition expression.

        Supports simple expressions like:
        - "domain == 'houdini'"
        - "confidence > 0.8"
        - "status == 'success'"

        Args:
            condition: Condition expression string

        Returns:
            Boolean result of evaluation
        """
        # Build evaluation context with variables
        eval_context = {
            **self._ctx.get_variables(),
            "domain": self._ctx.domain,
            "session_id": self._ctx.session_id,
            "task_id": self._ctx.task_id,
        }

        # Add all node outputs to context
        for node_id, outputs in self._ctx._node_outputs.items():
            for port, value in outputs.items():
                # Safe variable names (replace special chars)
                var_name = f"{node_id}_{port}".replace("-", "_")
                eval_context[var_name] = value

        try:
            # Safe evaluation with limited builtins
            result = eval(condition, {"__builtins__": {}}, eval_context)
            return bool(result)
        except Exception:
            # If evaluation fails, return False
            return False

    def query_memory(self, query: str, pattern_type: str = "success") -> list[dict]:
        """Query memory for patterns.

        Args:
            query: Query string
            pattern_type: Type of patterns to retrieve

        Returns:
            List of matching patterns
        """
        if not self._memory_enabled:
            return []

        # Check cache first
        cache_key = f"{pattern_type}:{query}"
        cached = self._ctx.get_memory_patterns(cache_key)
        if cached:
            return cached

        # Load from memory store
        try:
            from app.core.memory_runtime import build_runtime_memory_context

            max_patterns = 5 if pattern_type == "success" else 3
            memory_ctx = build_runtime_memory_context(
                domain=self._ctx.domain,
                query=query,
                repo_root=self._repo_root,
                max_success=max_patterns if pattern_type == "success" else 0,
                max_failure=max_patterns if pattern_type == "failure" else 0,
            )

            patterns = []
            if pattern_type == "success":
                patterns = memory_ctx.success_patterns
            elif pattern_type == "failure":
                patterns = memory_ctx.failure_patterns
            elif pattern_type == "repair":
                patterns = memory_ctx.repair_patterns

            self._ctx.set_memory_patterns(cache_key, patterns)
            return patterns

        except Exception:
            return []

    def save_to_memory(
        self,
        query: str,
        success: bool,
        result_data: dict[str, Any],
    ) -> bool:
        """Save execution result to memory.

        Args:
            query: Query/task description
            success: Whether execution was successful
            result_data: Result data to save

        Returns:
            True if saved successfully
        """
        if not self._memory_enabled:
            return False

        try:
            from app.core.memory_runtime import save_execution_result

            return save_execution_result(
                domain=self._ctx.domain,
                query=query,
                success=success,
                result_data=result_data,
                repo_root=self._repo_root,
            )
        except Exception:
            return False

    def record_error(self, node_id: str, error: str, details: dict[str, Any] | None = None) -> None:
        """Record an error in the context."""
        self._ctx.add_error(node_id, error, details)

    def get_errors(self) -> list[dict[str, Any]]:
        """Get all recorded errors."""
        return self._ctx.get_errors()

    def has_errors(self) -> bool:
        """Check if any errors occurred."""
        return self._ctx.has_errors()

    def get_execution_time_ms(self) -> float:
        """Get elapsed execution time."""
        return self._ctx.get_execution_time_ms()

    def to_dict(self) -> dict[str, Any]:
        """Serialize context to dictionary."""
        return self._ctx.to_dict()

    def snapshot(self) -> dict[str, Any]:
        """Create a snapshot of the current context state."""
        return {
            "execution_id": self._ctx.execution_id,
            "domain": self._ctx.domain,
            "session_id": self._ctx.session_id,
            "task_id": self._ctx.task_id,
            "execution_time_ms": self.get_execution_time_ms(),
            "node_outputs": {
                k: v.copy() for k, v in self._ctx._node_outputs.items()
            },
            "variables": self._ctx.get_variables(),
            "errors_count": len(self._ctx._errors),
        }

    def enable_memory(self, enabled: bool = True) -> None:
        """Enable or disable memory integration."""
        self._memory_enabled = enabled

    def enable_checkpoints(self, enabled: bool = True) -> None:
        """Enable or disable checkpoint support."""
        self._checkpoints_enabled = enabled


def create_context(
    domain: str = "",
    session_id: str = "",
    task_id: str = "",
    repo_root: str = ".",
    **variables: Any,
) -> NetworkContext:
    """Create a network context with optional initial variables.

    Args:
        domain: Execution domain
        session_id: Session identifier
        task_id: Task identifier
        repo_root: Repository root
        **variables: Initial variables to set

    Returns:
        NetworkContext instance
    """
    ctx = NetworkContext(
        domain=domain,
        session_id=session_id,
        task_id=task_id,
        repo_root=repo_root,
    )

    for name, value in variables.items():
        ctx.set_variable(name, value)

    return ctx