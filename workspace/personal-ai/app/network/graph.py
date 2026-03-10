"""Network Graph Management.

Provides graph construction, validation, and execution order computation
for the Claude Network multi-agent orchestration system.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any

from app.network.models import (
    EdgeType,
    NetworkEdge,
    NetworkNode,
    NodeType,
    PortDefinition,
)


@dataclass
class ValidationResult:
    """Result of graph validation."""

    valid: bool = True
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
        """Add an error to the result."""
        self.errors.append(error)
        self.valid = False

    def add_warning(self, warning: str) -> None:
        """Add a warning to the result."""
        self.warnings.append(warning)

    def merge(self, other: ValidationResult) -> None:
        """Merge another validation result into this one."""
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        if not other.valid:
            self.valid = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings,
        }


@dataclass
class ExecutionLevel:
    """A level in the execution plan (nodes that can run in parallel)."""

    level: int
    node_ids: list[str]
    dependencies: list[str]  # Node IDs this level depends on

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "level": self.level,
            "node_ids": self.node_ids,
            "dependencies": self.dependencies,
        }


class NetworkGraph:
    """Network graph management for multi-agent orchestration.

    Provides:
    - Node and edge management
    - Graph validation (cycles, missing nodes, port mismatches)
    - Topological sort for execution order
    - Dependency tracking
    """

    def __init__(self, name: str = "", domain: str = ""):
        """Initialize the network graph.

        Args:
            name: Name of the network
            domain: Domain this network operates in (e.g., "houdini", "touchdesigner")
        """
        self.name = name
        self.domain = domain
        self._nodes: dict[str, NetworkNode] = {}
        self._edges: dict[str, NetworkEdge] = {}
        self._adjacency: dict[str, list[str]] = defaultdict(list)
        self._reverse_adjacency: dict[str, list[str]] = defaultdict(list)
        self._edge_by_source: dict[str, list[str]] = defaultdict(list)
        self._edge_by_target: dict[str, list[str]] = defaultdict(list)

    @property
    def nodes(self) -> dict[str, NetworkNode]:
        """Get all nodes in the graph."""
        return self._nodes.copy()

    @property
    def edges(self) -> dict[str, NetworkEdge]:
        """Get all edges in the graph."""
        return self._edges.copy()

    @property
    def node_count(self) -> int:
        """Get the number of nodes."""
        return len(self._nodes)

    @property
    def edge_count(self) -> int:
        """Get the number of edges."""
        return len(self._edges)

    def add_node(self, node: NetworkNode) -> str:
        """Add a node to the graph.

        Args:
            node: NetworkNode to add

        Returns:
            Node ID of the added node

        Raises:
            ValueError: If node with same ID already exists
        """
        if node.node_id in self._nodes:
            raise ValueError(f"Node with ID '{node.node_id}' already exists")

        self._nodes[node.node_id] = node
        self._adjacency[node.node_id] = []
        self._reverse_adjacency[node.node_id] = []

        return node.node_id

    def remove_node(self, node_id: str) -> bool:
        """Remove a node and all connected edges.

        Args:
            node_id: ID of node to remove

        Returns:
            True if node was removed, False if not found
        """
        if node_id not in self._nodes:
            return False

        # Remove connected edges
        edges_to_remove = (
            self._edge_by_source.get(node_id, []) +
            self._edge_by_target.get(node_id, [])
        )
        for edge_id in edges_to_remove:
            self.remove_edge(edge_id)

        # Remove node
        del self._nodes[node_id]
        del self._adjacency[node_id]
        del self._reverse_adjacency[node_id]

        return True

    def add_edge(self, edge: NetworkEdge) -> str:
        """Add an edge to the graph.

        Args:
            edge: NetworkEdge to add

        Returns:
            Edge ID of the added edge

        Raises:
            ValueError: If edge with same ID exists or nodes don't exist
        """
        if edge.edge_id in self._edges:
            raise ValueError(f"Edge with ID '{edge.edge_id}' already exists")

        if edge.source_node not in self._nodes:
            raise ValueError(f"Source node '{edge.source_node}' does not exist")

        if edge.target_node not in self._nodes:
            raise ValueError(f"Target node '{edge.target_node}' does not exist")

        self._edges[edge.edge_id] = edge

        # Update adjacency lists
        self._adjacency[edge.source_node].append(edge.target_node)
        self._reverse_adjacency[edge.target_node].append(edge.source_node)

        # Track edges by source/target
        self._edge_by_source[edge.source_node].append(edge.edge_id)
        self._edge_by_target[edge.target_node].append(edge.edge_id)

        return edge.edge_id

    def remove_edge(self, edge_id: str) -> bool:
        """Remove an edge from the graph.

        Args:
            edge_id: ID of edge to remove

        Returns:
            True if edge was removed, False if not found
        """
        if edge_id not in self._edges:
            return False

        edge = self._edges[edge_id]

        # Update adjacency lists
        if edge.target_node in self._adjacency[edge.source_node]:
            self._adjacency[edge.source_node].remove(edge.target_node)
        if edge.source_node in self._reverse_adjacency[edge.target_node]:
            self._reverse_adjacency[edge.target_node].remove(edge.source_node)

        # Remove from tracking
        if edge_id in self._edge_by_source[edge.source_node]:
            self._edge_by_source[edge.source_node].remove(edge_id)
        if edge_id in self._edge_by_target[edge.target_node]:
            self._edge_by_target[edge.target_node].remove(edge_id)

        del self._edges[edge_id]

        return True

    def get_node(self, node_id: str) -> NetworkNode | None:
        """Get a node by ID."""
        return self._nodes.get(node_id)

    def get_edge(self, edge_id: str) -> NetworkEdge | None:
        """Get an edge by ID."""
        return self._edges.get(edge_id)

    def get_outgoing_edges(self, node_id: str) -> list[NetworkEdge]:
        """Get all edges originating from a node."""
        edge_ids = self._edge_by_source.get(node_id, [])
        return [self._edges[eid] for eid in edge_ids if eid in self._edges]

    def get_incoming_edges(self, node_id: str) -> list[NetworkEdge]:
        """Get all edges targeting a node."""
        edge_ids = self._edge_by_target.get(node_id, [])
        return [self._edges[eid] for eid in edge_ids if eid in self._edges]

    def get_successors(self, node_id: str) -> list[str]:
        """Get node IDs that this node connects to."""
        return self._adjacency.get(node_id, []).copy()

    def get_predecessors(self, node_id: str) -> list[str]:
        """Get node IDs that connect to this node."""
        return self._reverse_adjacency.get(node_id, []).copy()

    def get_source_nodes(self) -> list[str]:
        """Get nodes with no incoming edges (entry points)."""
        return [
            node_id for node_id in self._nodes
            if not self._reverse_adjacency.get(node_id)
        ]

    def get_sink_nodes(self) -> list[str]:
        """Get nodes with no outgoing edges (exit points)."""
        return [
            node_id for node_id in self._nodes
            if not self._adjacency.get(node_id)
        ]

    def validate(self) -> ValidationResult:
        """Validate the graph for common issues.

        Checks:
        - Empty graph
        - Disconnected components
        - Cycles (for DAG requirement)
        - Missing node references
        - Port mismatches
        - Missing required inputs

        Returns:
            ValidationResult with any errors or warnings
        """
        result = ValidationResult()

        # Check for empty graph
        if not self._nodes:
            result.add_warning("Graph has no nodes")
            return result

        # Check for disconnected nodes
        result.merge(self._validate_connectivity())

        # Check for cycles (networks should be DAGs for execution)
        result.merge(self._validate_acyclic())

        # Validate port connections
        result.merge(self._validate_ports())

        # Validate node-specific requirements
        result.merge(self._validate_nodes())

        return result

    def _validate_connectivity(self) -> ValidationResult:
        """Validate that all nodes are reachable from source nodes."""
        result = ValidationResult()

        if len(self._nodes) <= 1:
            return result

        # BFS from source nodes
        visited = set()
        queue = deque(self.get_source_nodes())

        while queue:
            node_id = queue.popleft()
            if node_id in visited:
                continue
            visited.add(node_id)

            for successor in self._adjacency.get(node_id, []):
                if successor not in visited:
                    queue.append(successor)

        # Check for disconnected nodes
        disconnected = set(self._nodes.keys()) - visited
        if disconnected:
            result.add_warning(
                f"Disconnected nodes (not reachable from sources): {disconnected}"
            )

        return result

    def _validate_acyclic(self) -> ValidationResult:
        """Validate that the graph is acyclic (DAG)."""
        result = ValidationResult()

        # Use Kahn's algorithm for cycle detection
        in_degree = {node_id: 0 for node_id in self._nodes}

        for edge in self._edges.values():
            in_degree[edge.target_node] += 1

        queue = deque([n for n, d in in_degree.items() if d == 0])
        visited_count = 0

        while queue:
            node_id = queue.popleft()
            visited_count += 1

            for successor in self._adjacency.get(node_id, []):
                in_degree[successor] -= 1
                if in_degree[successor] == 0:
                    queue.append(successor)

        if visited_count != len(self._nodes):
            # Cycle detected
            result.add_error(
                f"Graph contains cycles. Only {visited_count}/{len(self._nodes)} nodes reachable in topological order."
            )

        return result

    def _validate_ports(self) -> ValidationResult:
        """Validate port connections between nodes."""
        result = ValidationResult()

        for edge in self._edges.values():
            source = self._nodes.get(edge.source_node)
            target = self._nodes.get(edge.target_node)

            if not source or not target:
                continue  # Already caught by node validation

            # Check source port exists
            source_ports = source.get_output_names()
            if edge.source_port not in source_ports:
                result.add_warning(
                    f"Edge '{edge.edge_id}': source port '{edge.source_port}' not found in node '{edge.source_node}'. "
                    f"Available: {source_ports}"
                )

            # Check target port exists
            target_ports = target.get_input_names()
            if edge.target_port not in target_ports:
                result.add_warning(
                    f"Edge '{edge.edge_id}': target port '{edge.target_port}' not found in node '{edge.target_node}'. "
                    f"Available: {target_ports}"
                )

        return result

    def _validate_nodes(self) -> ValidationResult:
        """Validate node-specific requirements."""
        result = ValidationResult()

        # Track input edges for each node's ports
        node_input_edges: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))

        for edge in self._edges.values():
            node_input_edges[edge.target_node][edge.target_port].append(edge.edge_id)

        for node_id, node in self._nodes.items():
            # Check required inputs have connections
            for port in node.inputs:
                if port.required:
                    connected_edges = node_input_edges.get(node_id, {}).get(port.name, [])
                    if not connected_edges:
                        # Check if this is a source node (might receive input externally)
                        if self._reverse_adjacency.get(node_id):
                            result.add_warning(
                                f"Node '{node_id}': required input port '{port.name}' has no connection"
                            )

            # Validate node type specific requirements
            if node.node_type == NodeType.ROUTER:
                if not node.capabilities:
                    result.add_warning(
                        f"Router node '{node_id}' has no domain capabilities defined"
                    )

            elif node.node_type == NodeType.AGENT:
                provider = node.config.get("provider")
                if not provider:
                    result.add_warning(
                        f"Agent node '{node_id}' has no provider configured"
                    )

        return result

    def get_execution_order(self) -> list[list[str]]:
        """Get execution order using topological sort.

        Returns a list of levels, where each level contains nodes
        that can be executed in parallel (no dependencies between them).

        Returns:
            List of lists of node IDs, each inner list is a parallel level
        """
        if not self._nodes:
            return []

        # Kahn's algorithm with level tracking
        in_degree = {node_id: 0 for node_id in self._nodes}

        for edge in self._edges.values():
            in_degree[edge.target_node] += 1

        # Start with nodes that have no dependencies
        current_level = [n for n, d in in_degree.items() if d == 0]
        execution_order: list[list[str]] = []

        while current_level:
            execution_order.append(current_level)
            next_level = []

            for node_id in current_level:
                for successor in self._adjacency.get(node_id, []):
                    in_degree[successor] -= 1
                    if in_degree[successor] == 0:
                        next_level.append(successor)

            current_level = next_level

        return execution_order

    def get_execution_levels(self) -> list[ExecutionLevel]:
        """Get detailed execution levels with dependency information.

        Returns:
            List of ExecutionLevel objects with level, nodes, and dependencies
        """
        execution_order = self.get_execution_order()
        levels = []

        for i, node_ids in enumerate(execution_order):
            # Get dependencies for this level
            dependencies = set()
            for node_id in node_ids:
                dependencies.update(self._reverse_adjacency.get(node_id, []))

            levels.append(ExecutionLevel(
                level=i,
                node_ids=node_ids,
                dependencies=list(dependencies),
            ))

        return levels

    def get_dependencies(self, node_id: str) -> list[str]:
        """Get all nodes that must complete before this node can run.

        Args:
            node_id: Node to get dependencies for

        Returns:
            List of node IDs that must complete first
        """
        if node_id not in self._nodes:
            return []

        # BFS to collect all ancestors
        dependencies = set()
        queue = deque(self._reverse_adjacency.get(node_id, []))

        while queue:
            dep_id = queue.popleft()
            if dep_id not in dependencies:
                dependencies.add(dep_id)
                queue.extend(self._reverse_adjacency.get(dep_id, []))

        return list(dependencies)

    def get_dependents(self, node_id: str) -> list[str]:
        """Get all nodes that depend on this node.

        Args:
            node_id: Node to get dependents for

        Returns:
            List of node IDs that depend on this node
        """
        if node_id not in self._nodes:
            return []

        # BFS to collect all descendants
        dependents = set()
        queue = deque(self._adjacency.get(node_id, []))

        while queue:
            dep_id = queue.popleft()
            if dep_id not in dependents:
                dependents.add(dep_id)
                queue.extend(self._adjacency.get(dep_id, []))

        return list(dependents)

    def subgraph(self, node_ids: list[str]) -> NetworkGraph:
        """Create a subgraph containing only specified nodes.

        Args:
            node_ids: List of node IDs to include

        Returns:
            New NetworkGraph with only the specified nodes and their edges
        """
        sub = NetworkGraph(name=f"{self.name}_subgraph", domain=self.domain)

        # Add nodes
        for node_id in node_ids:
            node = self._nodes.get(node_id)
            if node:
                sub.add_node(node)

        # Add edges between included nodes
        for edge in self._edges.values():
            if edge.source_node in node_ids and edge.target_node in node_ids:
                sub.add_edge(edge)

        return sub

    def to_dict(self) -> dict[str, Any]:
        """Serialize the graph to a dictionary."""
        return {
            "name": self.name,
            "domain": self.domain,
            "nodes": {k: v.to_dict() for k, v in self._nodes.items()},
            "edges": {k: v.to_dict() for k, v in self._edges.items()},
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> NetworkGraph:
        """Deserialize a graph from a dictionary.

        Args:
            data: Dictionary with graph data

        Returns:
            NetworkGraph instance
        """
        graph = cls(name=data.get("name", ""), domain=data.get("domain", ""))

        # Add nodes
        for node_id, node_data in data.get("nodes", {}).items():
            node = NetworkNode(
                node_id=node_id,
                node_type=NodeType(node_data["node_type"]),
                name=node_data["name"],
                config=node_data.get("config", {}),
                inputs=[
                    PortDefinition(
                        name=p["name"],
                        data_type=p.get("data_type", "any"),
                        required=p.get("required", True),
                        description=p.get("description", ""),
                    )
                    for p in node_data.get("inputs", [])
                ],
                outputs=[
                    PortDefinition(
                        name=p["name"],
                        data_type=p.get("data_type", "any"),
                        required=p.get("required", True),
                        description=p.get("description", ""),
                    )
                    for p in node_data.get("outputs", [])
                ],
                capabilities=node_data.get("capabilities", []),
                metadata=node_data.get("metadata", {}),
            )
            graph._nodes[node_id] = node

        # Add edges (need to import here for deserialization)
        for edge_id, edge_data in data.get("edges", {}).items():
            edge = NetworkEdge(
                edge_id=edge_id,
                source_node=edge_data["source_node"],
                source_port=edge_data["source_port"],
                target_node=edge_data["target_node"],
                target_port=edge_data["target_port"],
                edge_type=EdgeType(edge_data.get("edge_type", "data")),
                condition=edge_data.get("condition"),
                metadata=edge_data.get("metadata", {}),
            )
            graph._edges[edge_id] = edge

            # Rebuild adjacency lists
            graph._adjacency[edge.source_node].append(edge.target_node)
            graph._reverse_adjacency[edge.target_node].append(edge.source_node)
            graph._edge_by_source[edge.source_node].append(edge_id)
            graph._edge_by_target[edge.target_node].append(edge_id)

        return graph