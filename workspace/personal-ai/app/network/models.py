"""Core Data Models for Claude Network.

Defines node types, edge types, and result structures for the multi-agent
orchestration system.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


class NodeType(str, Enum):
    """Types of nodes in the network."""

    AGENT = "agent"
    TOOL = "tool"
    MEMORY = "memory"
    ROUTER = "router"
    DECOMPOSER = "decomposer"


class EdgeType(str, Enum):
    """Types of connections between nodes."""

    DATA = "data"
    CONTROL = "control"
    MEMORY = "memory"


class NodeStatus(str, Enum):
    """Status of a node during execution."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(slots=True)
class PortDefinition:
    """Definition of an input or output port."""

    name: str
    data_type: str = "any"
    required: bool = True
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "data_type": self.data_type,
            "required": self.required,
            "description": self.description,
        }


@dataclass(slots=True)
class NetworkNode:
    """A node in the execution network.

    Nodes are the building blocks of the network, representing agents,
    tools, memory stores, routers, or task decomposers.
    """

    node_id: str
    node_type: NodeType
    name: str
    config: dict[str, Any] = field(default_factory=dict)
    inputs: list[PortDefinition] = field(default_factory=list)
    outputs: list[PortDefinition] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __hash__(self) -> int:
        return hash(self.node_id)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, NetworkNode):
            return False
        return self.node_id == other.node_id

    def get_input_names(self) -> list[str]:
        """Get list of input port names."""
        return [p.name for p in self.inputs]

    def get_output_names(self) -> list[str]:
        """Get list of output port names."""
        return [p.name for p in self.outputs]

    def has_capability(self, capability: str) -> bool:
        """Check if node has a specific capability."""
        return capability in self.capabilities

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "node_id": self.node_id,
            "node_type": self.node_type.value,
            "name": self.name,
            "config": self.config,
            "inputs": [p.to_dict() for p in self.inputs],
            "outputs": [p.to_dict() for p in self.outputs],
            "capabilities": self.capabilities,
            "metadata": self.metadata,
        }


@dataclass(slots=True)
class NetworkEdge:
    """A connection between two nodes in the network.

    Edges define how data, control flow, and memory are passed between nodes.
    """

    edge_id: str
    source_node: str
    source_port: str
    target_node: str
    target_port: str
    edge_type: EdgeType = EdgeType.DATA
    transform: Callable[[Any], Any] | None = None
    condition: str | None = None  # Expression for conditional execution
    metadata: dict[str, Any] = field(default_factory=dict)

    def __hash__(self) -> int:
        return hash(self.edge_id)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, NetworkEdge):
            return False
        return self.edge_id == other.edge_id

    def apply_transform(self, value: Any) -> Any:
        """Apply transformation function if defined."""
        if self.transform is not None:
            return self.transform(value)
        return value

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary (without transform function)."""
        return {
            "edge_id": self.edge_id,
            "source_node": self.source_node,
            "source_port": self.source_port,
            "target_node": self.target_node,
            "target_port": self.target_port,
            "edge_type": self.edge_type.value,
            "condition": self.condition,
            "metadata": self.metadata,
        }


@dataclass(slots=True)
class NodeResult:
    """Result of executing a single node.

    Contains the output data, status, timing, and any errors from execution.
    """

    node_id: str
    status: NodeStatus = NodeStatus.PENDING
    outputs: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    error_details: dict[str, Any] = field(default_factory=dict)
    execution_time_ms: float = 0.0
    retries: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def success(self) -> bool:
        """Check if execution was successful."""
        return self.status == NodeStatus.COMPLETED

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "node_id": self.node_id,
            "status": self.status.value,
            "outputs": self.outputs,
            "error": self.error,
            "error_details": self.error_details,
            "execution_time_ms": self.execution_time_ms,
            "retries": self.retries,
            "metadata": self.metadata,
            "success": self.success,
        }


@dataclass
class NetworkResult:
    """Result of executing an entire network.

    Aggregates results from all nodes with overall status and timing.
    """

    network_name: str = ""
    success: bool = False
    node_results: dict[str, NodeResult] = field(default_factory=dict)
    execution_order: list[list[str]] = field(default_factory=list)
    total_execution_time_ms: float = 0.0
    nodes_executed: int = 0
    nodes_failed: int = 0
    nodes_skipped: int = 0
    final_output: dict[str, Any] = field(default_factory=dict)
    context_snapshot: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_node_result(self, result: NodeResult) -> None:
        """Add a node result to the aggregate."""
        self.node_results[result.node_id] = result
        self.nodes_executed += 1

        if result.status == NodeStatus.FAILED:
            self.nodes_failed += 1
        elif result.status == NodeStatus.SKIPPED:
            self.nodes_skipped += 1

    def get_successful_nodes(self) -> list[str]:
        """Get list of successfully executed node IDs."""
        return [
            node_id for node_id, result in self.node_results.items()
            if result.success
        ]

    def get_failed_nodes(self) -> list[str]:
        """Get list of failed node IDs."""
        return [
            node_id for node_id, result in self.node_results.items()
            if result.status == NodeStatus.FAILED
        ]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "network_name": self.network_name,
            "success": self.success,
            "node_results": {k: v.to_dict() for k, v in self.node_results.items()},
            "execution_order": self.execution_order,
            "total_execution_time_ms": self.total_execution_time_ms,
            "nodes_executed": self.nodes_executed,
            "nodes_failed": self.nodes_failed,
            "nodes_skipped": self.nodes_skipped,
            "final_output": self.final_output,
            "context_snapshot": self.context_snapshot,
            "error": self.error,
            "metadata": self.metadata,
        }


@dataclass(slots=True)
class OrchestratorConfig:
    """Configuration for network orchestration."""

    max_parallel_nodes: int = 4
    default_timeout_seconds: float = 30.0
    retry_count: int = 2
    retry_delay_ms: float = 100.0
    enable_memory: bool = True
    enable_checkpoints: bool = True
    checkpoint_interval: int = 5  # Checkpoint every N nodes
    fail_fast: bool = True  # Stop on first failure
    continue_on_error: bool = False  # Continue even if node fails
    log_level: str = "INFO"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "max_parallel_nodes": self.max_parallel_nodes,
            "default_timeout_seconds": self.default_timeout_seconds,
            "retry_count": self.retry_count,
            "retry_delay_ms": self.retry_delay_ms,
            "enable_memory": self.enable_memory,
            "enable_checkpoints": self.enable_checkpoints,
            "checkpoint_interval": self.checkpoint_interval,
            "fail_fast": self.fail_fast,
            "continue_on_error": self.continue_on_error,
            "log_level": self.log_level,
        }


# Factory functions for common node types

def create_agent_node(
    node_id: str,
    name: str,
    provider: str = "claude",
    system_prompt: str = "",
    tools: list[str] | None = None,
    capabilities: list[str] | None = None,
    **kwargs: Any,
) -> NetworkNode:
    """Create an agent node with standard configuration.

    Args:
        node_id: Unique identifier for the node
        name: Human-readable name
        provider: LLM provider (claude, ollama, gemini)
        system_prompt: System prompt for the agent
        tools: List of tool names the agent can use
        capabilities: List of domain capabilities
        **kwargs: Additional config options

    Returns:
        Configured NetworkNode
    """
    return NetworkNode(
        node_id=node_id,
        node_type=NodeType.AGENT,
        name=name,
        config={
            "provider": provider,
            "system_prompt": system_prompt,
            "tools": tools or [],
            **kwargs,
        },
        inputs=[
            PortDefinition(name="input", data_type="str", required=True),
        ],
        outputs=[
            PortDefinition(name="output", data_type="str"),
            PortDefinition(name="structured", data_type="dict"),
        ],
        capabilities=capabilities or [],
    )


def create_tool_node(
    node_id: str,
    name: str,
    tool_name: str,
    input_schema: dict[str, Any] | None = None,
    output_schema: dict[str, Any] | None = None,
) -> NetworkNode:
    """Create a tool node with standard configuration.

    Args:
        node_id: Unique identifier for the node
        name: Human-readable name
        tool_name: Name of the tool to execute
        input_schema: Expected input schema
        output_schema: Expected output schema

    Returns:
        Configured NetworkNode
    """
    return NetworkNode(
        node_id=node_id,
        node_type=NodeType.TOOL,
        name=name,
        config={
            "tool_name": tool_name,
            "input_schema": input_schema or {},
            "output_schema": output_schema or {},
        },
        inputs=[
            PortDefinition(name="params", data_type="dict", required=True),
        ],
        outputs=[
            PortDefinition(name="result", data_type="any"),
        ],
    )


def create_memory_node(
    node_id: str,
    name: str,
    query_type: str = "success_patterns",
    max_results: int = 5,
) -> NetworkNode:
    """Create a memory node with standard configuration.

    Args:
        node_id: Unique identifier for the node
        name: Human-readable name
        query_type: Type of patterns to query
        max_results: Maximum results to return

    Returns:
        Configured NetworkNode
    """
    return NetworkNode(
        node_id=node_id,
        node_type=NodeType.MEMORY,
        name=name,
        config={
            "query_type": query_type,
            "max_results": max_results,
        },
        inputs=[
            PortDefinition(name="query", data_type="str", required=True),
        ],
        outputs=[
            PortDefinition(name="patterns", data_type="list"),
            PortDefinition(name="context", data_type="dict"),
        ],
    )


def create_router_node(
    node_id: str,
    name: str,
    domains: list[str] | None = None,
    routing_strategy: str = "first_match",
) -> NetworkNode:
    """Create a router node with standard configuration.

    Args:
        node_id: Unique identifier for the node
        name: Human-readable name
        domains: List of domains this router can route to
        routing_strategy: Strategy for routing decisions

    Returns:
        Configured NetworkNode
    """
    return NetworkNode(
        node_id=node_id,
        node_type=NodeType.ROUTER,
        name=name,
        config={
            "domains": domains or [],
            "routing_strategy": routing_strategy,
        },
        inputs=[
            PortDefinition(name="task", data_type="str", required=True),
        ],
        outputs=[
            PortDefinition(name="domain", data_type="str"),
            PortDefinition(name="confidence", data_type="float"),
        ],
        capabilities=domains or [],
    )


def create_decomposer_node(
    node_id: str,
    name: str,
    max_subtasks: int = 5,
    strategy: str = "sequential",
) -> NetworkNode:
    """Create a decomposer node with standard configuration.

    Args:
        node_id: Unique identifier for the node
        name: Human-readable name
        max_subtasks: Maximum number of subtasks to generate
        strategy: Decomposition strategy (sequential, parallel, hybrid)

    Returns:
        Configured NetworkNode
    """
    return NetworkNode(
        node_id=node_id,
        node_type=NodeType.DECOMPOSER,
        name=name,
        config={
            "max_subtasks": max_subtasks,
            "strategy": strategy,
        },
        inputs=[
            PortDefinition(name="task", data_type="str", required=True),
        ],
        outputs=[
            PortDefinition(name="subtasks", data_type="list"),
            PortDefinition(name="dependencies", data_type="dict"),
        ],
    )