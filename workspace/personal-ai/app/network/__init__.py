"""Claude Network - Multi-Agent Orchestration System.

A comprehensive multi-agent orchestration system that provides:
- Task decomposition and parallel execution
- Memory sharing between agents
- Tool chaining and integration
- Domain expert routing

Quick Start:
    from app.network import NetworkBuilder, agent_node, router_node

    # Build a network
    network = (
        NetworkBuilder("my-pipeline")
        .add_agent("planner", system_prompt="You are a task planner...")
        .add_router("router", domains=["houdini", "touchdesigner"])
        .add_memory("memory", query_type="success_patterns")
        .connect("router", "memory")
        .connect("memory", "planner")
        .build()
    )

    # Execute
    result = await network.execute({"input": "Create particle system"})
"""

from app.network.builder import (
    NetworkBuilder,
    NodeBuilder,
    ConnectionBuilder,
    agent_node,
    decomposer_node,
    memory_node,
    network,
    router_node,
    tool_node,
)
from app.network.context import (
    ExecutionContext,
    NetworkContext,
    create_context,
)
from app.network.executor import (
    ExecutorConfig,
    ExecutionResult,
    NetworkExecutor,
    SyncNetworkExecutor,
)
from app.network.graph import (
    ExecutionLevel,
    NetworkGraph,
    ValidationResult,
)
from app.network.models import (
    EdgeType,
    NetworkEdge,
    NetworkNode,
    NetworkResult,
    NodeResult,
    NodeStatus,
    NodeType,
    OrchestratorConfig,
    PortDefinition,
    create_agent_node,
    create_decomposer_node,
    create_memory_node,
    create_router_node,
    create_tool_node,
)
from app.network.node_types import (
    AgentNodeExecutor,
    DecomposerNodeExecutor,
    MemoryNodeExecutor,
    NodeExecutor,
    RouterNodeExecutor,
    ToolNodeExecutor,
    get_executor,
)
from app.network.orchestrator import (
    NetworkOrchestrator,
    OrchestrationHooks,
    SyncNetworkOrchestrator,
    create_orchestrator,
)
from app.network.routers import (
    DomainProfile,
    DomainRouter,
    LoadBalancingRouter,
    RoutingDecision,
    create_router,
)

__all__ = [
    # Builder
    "NetworkBuilder",
    "NodeBuilder",
    "ConnectionBuilder",
    "network",
    "agent_node",
    "router_node",
    "memory_node",
    "tool_node",
    "decomposer_node",
    # Context
    "NetworkContext",
    "ExecutionContext",
    "create_context",
    # Executor
    "NetworkExecutor",
    "SyncNetworkExecutor",
    "ExecutorConfig",
    "ExecutionResult",
    # Graph
    "NetworkGraph",
    "ExecutionLevel",
    "ValidationResult",
    # Models
    "NetworkNode",
    "NetworkEdge",
    "NetworkResult",
    "NodeResult",
    "NodeType",
    "EdgeType",
    "NodeStatus",
    "PortDefinition",
    "OrchestratorConfig",
    "create_agent_node",
    "create_tool_node",
    "create_memory_node",
    "create_router_node",
    "create_decomposer_node",
    # Node Types
    "NodeExecutor",
    "AgentNodeExecutor",
    "ToolNodeExecutor",
    "MemoryNodeExecutor",
    "RouterNodeExecutor",
    "DecomposerNodeExecutor",
    "get_executor",
    # Orchestrator
    "NetworkOrchestrator",
    "SyncNetworkOrchestrator",
    "OrchestrationHooks",
    "create_orchestrator",
    # Routers
    "DomainRouter",
    "DomainProfile",
    "RoutingDecision",
    "LoadBalancingRouter",
    "create_router",
]

__version__ = "1.0.0"