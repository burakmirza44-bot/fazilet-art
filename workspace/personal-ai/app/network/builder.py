"""Network Builder with Fluent API.

Provides a convenient fluent interface for constructing networks
with nodes, edges, and configurations.
"""

from __future__ import annotations

from typing import Any, Callable

from app.network.graph import NetworkGraph
from app.network.models import (
    EdgeType,
    NetworkEdge,
    NetworkNode,
    NodeType,
    OrchestratorConfig,
    PortDefinition,
    create_agent_node,
    create_decomposer_node,
    create_memory_node,
    create_router_node,
    create_tool_node,
)
from app.network.orchestrator import NetworkOrchestrator


class NodeBuilder:
    """Builder for individual nodes."""

    def __init__(self, node_id: str, node_type: NodeType, name: str = ""):
        """Initialize the node builder.

        Args:
            node_id: Unique node identifier
            node_type: Type of the node
            name: Human-readable name
        """
        self._node_id = node_id
        self._node_type = node_type
        self._name = name or node_id
        self._config: dict[str, Any] = {}
        self._inputs: list[PortDefinition] = []
        self._outputs: list[PortDefinition] = []
        self._capabilities: list[str] = []
        self._metadata: dict[str, Any] = {}

    def with_name(self, name: str) -> NodeBuilder:
        """Set the node name."""
        self._name = name
        return self

    def with_config(self, **kwargs: Any) -> NodeBuilder:
        """Add configuration options."""
        self._config.update(kwargs)
        return self

    def with_input(
        self,
        name: str,
        data_type: str = "any",
        required: bool = True,
        description: str = "",
    ) -> NodeBuilder:
        """Add an input port."""
        self._inputs.append(PortDefinition(
            name=name,
            data_type=data_type,
            required=required,
            description=description,
        ))
        return self

    def with_output(
        self,
        name: str,
        data_type: str = "any",
        description: str = "",
    ) -> NodeBuilder:
        """Add an output port."""
        self._outputs.append(PortDefinition(
            name=name,
            data_type=data_type,
            required=False,
            description=description,
        ))
        return self

    def with_capability(self, capability: str) -> NodeBuilder:
        """Add a capability."""
        self._capabilities.append(capability)
        return self

    def with_capabilities(self, *capabilities: str) -> NodeBuilder:
        """Add multiple capabilities."""
        self._capabilities.extend(capabilities)
        return self

    def with_metadata(self, **kwargs: Any) -> NodeBuilder:
        """Add metadata."""
        self._metadata.update(kwargs)
        return self

    def build(self) -> NetworkNode:
        """Build the node."""
        return NetworkNode(
            node_id=self._node_id,
            node_type=self._node_type,
            name=self._name,
            config=self._config,
            inputs=self._inputs,
            outputs=self._outputs,
            capabilities=self._capabilities,
            metadata=self._metadata,
        )


class ConnectionBuilder:
    """Builder for connections between nodes."""

    def __init__(self, source_node: str, source_port: str = "output"):
        """Initialize the connection builder.

        Args:
            source_node: Source node ID
            source_port: Source port name
        """
        self._source_node = source_node
        self._source_port = source_port
        self._target_node: str | None = None
        self._target_port: str = "input"
        self._edge_type: EdgeType = EdgeType.DATA
        self._transform: Callable[[Any], Any] | None = None
        self._condition: str | None = None
        self._metadata: dict[str, Any] = {}

    def to(self, target_node: str, target_port: str = "input") -> ConnectionBuilder:
        """Set the target node and port.

        Args:
            target_node: Target node ID
            target_port: Target port name

        Returns:
            Self for chaining
        """
        self._target_node = target_node
        self._target_port = target_port
        return self

    def as_data(self) -> ConnectionBuilder:
        """Set edge type to data."""
        self._edge_type = EdgeType.DATA
        return self

    def as_control(self) -> ConnectionBuilder:
        """Set edge type to control."""
        self._edge_type = EdgeType.CONTROL
        return self

    def as_memory(self) -> ConnectionBuilder:
        """Set edge type to memory."""
        self._edge_type = EdgeType.MEMORY
        return self

    def with_transform(self, transform: Callable[[Any], Any]) -> ConnectionBuilder:
        """Set a transformation function."""
        self._transform = transform
        return self

    def with_condition(self, condition: str) -> ConnectionBuilder:
        """Set a conditional expression.

        Args:
            condition: Python expression to evaluate (e.g., "domain == 'houdini'")

        Returns:
            Self for chaining
        """
        self._condition = condition
        return self

    def with_metadata(self, **kwargs: Any) -> ConnectionBuilder:
        """Add metadata."""
        self._metadata.update(kwargs)
        return self

    def build(self, edge_id: str) -> NetworkEdge:
        """Build the edge."""
        if not self._target_node:
            raise ValueError("Target node not set")

        return NetworkEdge(
            edge_id=edge_id,
            source_node=self._source_node,
            source_port=self._source_port,
            target_node=self._target_node,
            target_port=self._target_port,
            edge_type=self._edge_type,
            transform=self._transform,
            condition=self._condition,
            metadata=self._metadata,
        )


class NetworkBuilder:
    """Fluent builder for Claude networks.

    Example:
        network = (
            NetworkBuilder("my-network")
            .add_agent("planner", system_prompt="You are a planner...")
            .add_router("router", domains=["houdini", "touchdesigner"])
            .connect("router", "planner")
            .build()
        )
    """

    def __init__(self, name: str = "", domain: str = ""):
        """Initialize the network builder.

        Args:
            name: Network name
            domain: Domain for the network
        """
        self._name = name
        self._domain = domain
        self._nodes: dict[str, NetworkNode] = {}
        self._connections: list[tuple[str, str, str, str, ConnectionBuilder | None]] = []
        self._edge_counter = 0
        self._config: OrchestratorConfig = OrchestratorConfig()

    # -------------------------------------------------------------------------
    # Node Addition Methods
    # -------------------------------------------------------------------------

    def add_node(self, node: NetworkNode) -> NetworkBuilder:
        """Add a pre-built node.

        Args:
            node: Node to add

        Returns:
            Self for chaining
        """
        self._nodes[node.node_id] = node
        return self

    def add_agent(
        self,
        node_id: str,
        name: str = "",
        provider: str = "claude",
        system_prompt: str = "",
        tools: list[str] | None = None,
        capabilities: list[str] | None = None,
        **kwargs: Any,
    ) -> NetworkBuilder:
        """Add an agent node.

        Args:
            node_id: Unique identifier
            name: Human-readable name
            provider: LLM provider (claude, ollama, gemini)
            system_prompt: System prompt
            tools: Available tools
            capabilities: Domain capabilities
            **kwargs: Additional configuration

        Returns:
            Self for chaining
        """
        node = create_agent_node(
            node_id=node_id,
            name=name or node_id,
            provider=provider,
            system_prompt=system_prompt,
            tools=tools,
            capabilities=capabilities,
            **kwargs,
        )
        return self.add_node(node)

    def add_tool(
        self,
        node_id: str,
        name: str = "",
        tool_name: str = "",
        input_schema: dict[str, Any] | None = None,
        output_schema: dict[str, Any] | None = None,
    ) -> NetworkBuilder:
        """Add a tool node.

        Args:
            node_id: Unique identifier
            name: Human-readable name
            tool_name: Name of the tool
            input_schema: Expected input schema
            output_schema: Expected output schema

        Returns:
            Self for chaining
        """
        node = create_tool_node(
            node_id=node_id,
            name=name or node_id,
            tool_name=tool_name or node_id,
            input_schema=input_schema,
            output_schema=output_schema,
        )
        return self.add_node(node)

    def add_memory(
        self,
        node_id: str,
        name: str = "",
        query_type: str = "success_patterns",
        max_results: int = 5,
    ) -> NetworkBuilder:
        """Add a memory node.

        Args:
            node_id: Unique identifier
            name: Human-readable name
            query_type: Type of patterns to query
            max_results: Maximum results

        Returns:
            Self for chaining
        """
        node = create_memory_node(
            node_id=node_id,
            name=name or node_id,
            query_type=query_type,
            max_results=max_results,
        )
        return self.add_node(node)

    def add_router(
        self,
        node_id: str,
        name: str = "",
        domains: list[str] | None = None,
        routing_strategy: str = "first_match",
    ) -> NetworkBuilder:
        """Add a router node.

        Args:
            node_id: Unique identifier
            name: Human-readable name
            domains: Available domains
            routing_strategy: Strategy for routing

        Returns:
            Self for chaining
        """
        node = create_router_node(
            node_id=node_id,
            name=name or node_id,
            domains=domains,
            routing_strategy=routing_strategy,
        )
        return self.add_node(node)

    def add_decomposer(
        self,
        node_id: str,
        name: str = "",
        max_subtasks: int = 5,
        strategy: str = "sequential",
    ) -> NetworkBuilder:
        """Add a decomposer node.

        Args:
            node_id: Unique identifier
            name: Human-readable name
            max_subtasks: Maximum subtasks
            strategy: Decomposition strategy

        Returns:
            Self for chaining
        """
        node = create_decomposer_node(
            node_id=node_id,
            name=name or node_id,
            max_subtasks=max_subtasks,
            strategy=strategy,
        )
        return self.add_node(node)

    # -------------------------------------------------------------------------
    # Connection Methods
    # -------------------------------------------------------------------------

    def connect(
        self,
        source: str,
        target: str,
        source_port: str = "output",
        target_port: str = "input",
        edge_type: EdgeType = EdgeType.DATA,
        condition: str | None = None,
        transform: Callable[[Any], Any] | None = None,
    ) -> NetworkBuilder:
        """Connect two nodes.

        Args:
            source: Source node ID
            target: Target node ID
            source_port: Source port name
            target_port: Target port name
            edge_type: Type of connection
            condition: Optional condition for control edges
            transform: Optional transformation function

        Returns:
            Self for chaining
        """
        self._connections.append((
            source,
            source_port,
            target,
            target_port,
            ConnectionBuilder(source, source_port)
            .to(target, target_port)
            .with_condition(condition)
            .with_transform(transform) if condition or transform else None,
        ))

        # Store edge type for later
        if self._connections:
            last = self._connections[-1]
            if last[4]:
                last[4]._edge_type = edge_type
            self._edge_counter += 1

        return self

    def connect_data(self, source: str, target: str, **kwargs: Any) -> NetworkBuilder:
        """Connect with data edge type."""
        return self.connect(source, target, edge_type=EdgeType.DATA, **kwargs)

    def connect_control(
        self,
        source: str,
        target: str,
        condition: str | None = None,
        **kwargs: Any,
    ) -> NetworkBuilder:
        """Connect with control edge type."""
        return self.connect(
            source, target,
            edge_type=EdgeType.CONTROL,
            condition=condition,
            **kwargs,
        )

    def connect_memory(self, source: str, target: str, **kwargs: Any) -> NetworkBuilder:
        """Connect with memory edge type."""
        return self.connect(source, target, edge_type=EdgeType.MEMORY, **kwargs)

    # -------------------------------------------------------------------------
    # Configuration Methods
    # -------------------------------------------------------------------------

    def with_domain(self, domain: str) -> NetworkBuilder:
        """Set the network domain."""
        self._domain = domain
        return self

    def with_config(
        self,
        max_parallel: int = 4,
        timeout_seconds: float = 30.0,
        retry_count: int = 2,
        fail_fast: bool = True,
    ) -> NetworkBuilder:
        """Set orchestration configuration."""
        self._config = OrchestratorConfig(
            max_parallel_nodes=max_parallel,
            default_timeout_seconds=timeout_seconds,
            retry_count=retry_count,
            fail_fast=fail_fast,
        )
        return self

    # -------------------------------------------------------------------------
    # Build Methods
    # -------------------------------------------------------------------------

    def build_graph(self) -> NetworkGraph:
        """Build the network graph.

        Returns:
            NetworkGraph instance
        """
        graph = NetworkGraph(name=self._name, domain=self._domain)

        # Add nodes
        for node in self._nodes.values():
            graph.add_node(node)

        # Add edges
        edge_counter = 0
        for source, source_port, target, target_port, builder in self._connections:
            edge_id = f"edge_{edge_counter}"
            edge_counter += 1

            if builder:
                edge = builder.build(edge_id)
            else:
                edge = NetworkEdge(
                    edge_id=edge_id,
                    source_node=source,
                    source_port=source_port,
                    target_node=target,
                    target_port=target_port,
                )

            graph.add_edge(edge)

        return graph

    def build(self) -> NetworkOrchestrator:
        """Build and return an orchestrator.

        Returns:
            NetworkOrchestrator instance
        """
        graph = self.build_graph()
        return NetworkOrchestrator(graph, self._config)

    def build_and_execute(
        self,
        input_data: dict[str, Any],
        domain: str = "",
        repo_root: str = ".",
    ) -> dict[str, Any]:
        """Build and execute the network synchronously.

        Args:
            input_data: Input data for execution
            domain: Execution domain
            repo_root: Repository root

        Returns:
            Execution result
        """
        orchestrator = self.build()
        from app.network.orchestrator import SyncNetworkOrchestrator

        sync = SyncNetworkOrchestrator(
            orchestrator._graph,
            orchestrator._config,
        )

        result = sync.execute(
            input_data,
            domain=domain or self._domain,
            repo_root=repo_root,
        )

        return result.to_dict()


# Convenience functions

def network(name: str = "", domain: str = "") -> NetworkBuilder:
    """Create a new network builder.

    Args:
        name: Network name
        domain: Network domain

    Returns:
        NetworkBuilder instance
    """
    return NetworkBuilder(name, domain)


def agent_node(
    node_id: str,
    name: str = "",
    provider: str = "claude",
    system_prompt: str = "",
    **kwargs: Any,
) -> NodeBuilder:
    """Create an agent node builder.

    Args:
        node_id: Unique identifier
        name: Human-readable name
        provider: LLM provider
        system_prompt: System prompt
        **kwargs: Additional configuration

    Returns:
        NodeBuilder instance
    """
    builder = NodeBuilder(node_id, NodeType.AGENT, name or node_id)
    builder.with_config(provider=provider, system_prompt=system_prompt, **kwargs)
    builder.with_input("input", "str")
    builder.with_output("output", "str")
    builder.with_output("structured", "dict")
    return builder


def router_node(
    node_id: str,
    name: str = "",
    domains: list[str] | None = None,
) -> NodeBuilder:
    """Create a router node builder.

    Args:
        node_id: Unique identifier
        name: Human-readable name
        domains: Available domains

    Returns:
        NodeBuilder instance
    """
    builder = NodeBuilder(node_id, NodeType.ROUTER, name or node_id)
    builder.with_config(domains=domains or [])
    builder.with_input("task", "str")
    builder.with_output("domain", "str")
    builder.with_output("confidence", "float")
    if domains:
        builder.with_capabilities(*domains)
    return builder


def memory_node(
    node_id: str,
    name: str = "",
    query_type: str = "success_patterns",
) -> NodeBuilder:
    """Create a memory node builder.

    Args:
        node_id: Unique identifier
        name: Human-readable name
        query_type: Type of patterns

    Returns:
        NodeBuilder instance
    """
    builder = NodeBuilder(node_id, NodeType.MEMORY, name or node_id)
    builder.with_config(query_type=query_type)
    builder.with_input("query", "str")
    builder.with_output("patterns", "list")
    builder.with_output("context", "dict")
    return builder


def tool_node(
    node_id: str,
    name: str = "",
    tool_name: str = "",
) -> NodeBuilder:
    """Create a tool node builder.

    Args:
        node_id: Unique identifier
        name: Human-readable name
        tool_name: Name of the tool

    Returns:
        NodeBuilder instance
    """
    builder = NodeBuilder(node_id, NodeType.TOOL, name or node_id)
    builder.with_config(tool_name=tool_name or node_id)
    builder.with_input("params", "dict")
    builder.with_output("result", "any")
    return builder


def decomposer_node(
    node_id: str,
    name: str = "",
    max_subtasks: int = 5,
) -> NodeBuilder:
    """Create a decomposer node builder.

    Args:
        node_id: Unique identifier
        name: Human-readable name
        max_subtasks: Maximum subtasks

    Returns:
        NodeBuilder instance
    """
    builder = NodeBuilder(node_id, NodeType.DECOMPOSER, name or node_id)
    builder.with_config(max_subtasks=max_subtasks)
    builder.with_input("task", "str")
    builder.with_output("subtasks", "list")
    builder.with_output("dependencies", "dict")
    return builder