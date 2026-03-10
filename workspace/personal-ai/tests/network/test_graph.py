"""Unit tests for Claude Network graph management."""

import pytest

from app.network.graph import ExecutionLevel, NetworkGraph, ValidationResult
from app.network.models import (
    EdgeType,
    NetworkEdge,
    NetworkNode,
    NodeType,
    PortDefinition,
)


def create_test_node(node_id: str, node_type: NodeType = NodeType.AGENT) -> NetworkNode:
    """Helper to create test nodes."""
    return NetworkNode(
        node_id=node_id,
        node_type=node_type,
        name=f"Test {node_id}",
        inputs=[PortDefinition(name="input")],
        outputs=[PortDefinition(name="output")],
    )


def create_test_edge(edge_id: str, source: str, target: str) -> NetworkEdge:
    """Helper to create test edges."""
    return NetworkEdge(
        edge_id=edge_id,
        source_node=source,
        source_port="output",
        target_node=target,
        target_port="input",
    )


class TestNetworkGraph:
    """Tests for NetworkGraph."""

    def test_create_graph(self):
        """Test creating a graph."""
        graph = NetworkGraph(name="test_graph", domain="test")
        assert graph.name == "test_graph"
        assert graph.domain == "test"
        assert graph.node_count == 0
        assert graph.edge_count == 0

    def test_add_node(self):
        """Test adding nodes."""
        graph = NetworkGraph()
        node = create_test_node("n1")

        node_id = graph.add_node(node)
        assert node_id == "n1"
        assert graph.node_count == 1
        assert graph.get_node("n1") == node

    def test_add_duplicate_node(self):
        """Test adding duplicate node raises error."""
        graph = NetworkGraph()
        graph.add_node(create_test_node("n1"))

        with pytest.raises(ValueError, match="already exists"):
            graph.add_node(create_test_node("n1"))

    def test_remove_node(self):
        """Test removing nodes."""
        graph = NetworkGraph()
        graph.add_node(create_test_node("n1"))
        graph.add_node(create_test_node("n2"))
        graph.add_edge(create_test_edge("e1", "n1", "n2"))

        result = graph.remove_node("n1")
        assert result is True
        assert graph.node_count == 1
        assert graph.edge_count == 0  # Edge should be removed too

    def test_add_edge(self):
        """Test adding edges."""
        graph = NetworkGraph()
        graph.add_node(create_test_node("n1"))
        graph.add_node(create_test_node("n2"))

        edge = create_test_edge("e1", "n1", "n2")
        edge_id = graph.add_edge(edge)
        assert edge_id == "e1"
        assert graph.edge_count == 1

    def test_add_edge_missing_node(self):
        """Test adding edge with missing node raises error."""
        graph = NetworkGraph()
        graph.add_node(create_test_node("n1"))

        with pytest.raises(ValueError, match="does not exist"):
            graph.add_edge(create_test_edge("e1", "n1", "n2"))

    def test_get_successors_and_predecessors(self):
        """Test getting successors and predecessors."""
        graph = NetworkGraph()
        graph.add_node(create_test_node("n1"))
        graph.add_node(create_test_node("n2"))
        graph.add_node(create_test_node("n3"))
        graph.add_edge(create_test_edge("e1", "n1", "n2"))
        graph.add_edge(create_test_edge("e2", "n2", "n3"))

        assert graph.get_successors("n1") == ["n2"]
        assert graph.get_successors("n2") == ["n3"]
        assert graph.get_predecessors("n2") == ["n1"]
        assert graph.get_predecessors("n3") == ["n2"]

    def test_get_source_and_sink_nodes(self):
        """Test getting source and sink nodes."""
        graph = NetworkGraph()
        graph.add_node(create_test_node("source"))
        graph.add_node(create_test_node("middle"))
        graph.add_node(create_test_node("sink"))
        graph.add_edge(create_test_edge("e1", "source", "middle"))
        graph.add_edge(create_test_edge("e2", "middle", "sink"))

        assert graph.get_source_nodes() == ["source"]
        assert graph.get_sink_nodes() == ["sink"]


class TestGraphValidation:
    """Tests for graph validation."""

    def test_validate_empty_graph(self):
        """Test validating empty graph."""
        graph = NetworkGraph()
        result = graph.validate()
        assert result.valid is True
        assert result.has_warnings is True

    def test_validate_acyclic_graph(self):
        """Test validating acyclic graph."""
        graph = NetworkGraph()
        graph.add_node(create_test_node("n1"))
        graph.add_node(create_test_node("n2"))
        graph.add_edge(create_test_edge("e1", "n1", "n2"))

        result = graph.validate()
        assert result.valid is True

    def test_validate_cyclic_graph(self):
        """Test detecting cycles."""
        graph = NetworkGraph()
        graph.add_node(create_test_node("n1"))
        graph.add_node(create_test_node("n2"))
        graph.add_node(create_test_node("n3"))
        graph.add_edge(create_test_edge("e1", "n1", "n2"))
        graph.add_edge(create_test_edge("e2", "n2", "n3"))
        graph.add_edge(create_test_edge("e3", "n3", "n1"))  # Creates cycle

        result = graph.validate()
        assert result.valid is False
        assert "cycles" in result.errors[0].lower()


class TestExecutionOrder:
    """Tests for execution order computation."""

    def test_linear_execution_order(self):
        """Test execution order for linear graph."""
        graph = NetworkGraph()
        graph.add_node(create_test_node("a"))
        graph.add_node(create_test_node("b"))
        graph.add_node(create_test_node("c"))
        graph.add_edge(create_test_edge("e1", "a", "b"))
        graph.add_edge(create_test_edge("e2", "b", "c"))

        order = graph.get_execution_order()
        assert order == [["a"], ["b"], ["c"]]

    def test_parallel_execution_order(self):
        """Test execution order with parallel nodes."""
        graph = NetworkGraph()
        graph.add_node(create_test_node("source"))
        graph.add_node(create_test_node("a"))
        graph.add_node(create_test_node("b"))
        graph.add_node(create_test_node("sink"))
        graph.add_edge(create_test_edge("e1", "source", "a"))
        graph.add_edge(create_test_edge("e2", "source", "b"))
        graph.add_edge(create_test_edge("e3", "a", "sink"))
        graph.add_edge(create_test_edge("e4", "b", "sink"))

        order = graph.get_execution_order()
        assert order[0] == ["source"]
        # a and b can run in parallel
        assert set(order[1]) == {"a", "b"}
        assert order[2] == ["sink"]

    def test_get_execution_levels(self):
        """Test getting execution levels."""
        graph = NetworkGraph()
        graph.add_node(create_test_node("a"))
        graph.add_node(create_test_node("b"))
        graph.add_edge(create_test_edge("e1", "a", "b"))

        levels = graph.get_execution_levels()
        assert len(levels) == 2
        assert levels[0].node_ids == ["a"]
        assert levels[0].dependencies == []
        assert levels[1].node_ids == ["b"]
        assert levels[1].dependencies == ["a"]


class TestDependencyTracking:
    """Tests for dependency tracking."""

    def test_get_dependencies(self):
        """Test getting dependencies."""
        graph = NetworkGraph()
        graph.add_node(create_test_node("a"))
        graph.add_node(create_test_node("b"))
        graph.add_node(create_test_node("c"))
        graph.add_edge(create_test_edge("e1", "a", "b"))
        graph.add_edge(create_test_edge("e2", "b", "c"))

        deps = graph.get_dependencies("c")
        assert set(deps) == {"a", "b"}

    def test_get_dependents(self):
        """Test getting dependents."""
        graph = NetworkGraph()
        graph.add_node(create_test_node("a"))
        graph.add_node(create_test_node("b"))
        graph.add_node(create_test_node("c"))
        graph.add_edge(create_test_edge("e1", "a", "b"))
        graph.add_edge(create_test_edge("e2", "b", "c"))

        deps = graph.get_dependents("a")
        assert set(deps) == {"b", "c"}


class TestGraphSerialization:
    """Tests for graph serialization."""

    def test_to_dict(self):
        """Test serializing to dictionary."""
        graph = NetworkGraph(name="test", domain="test_domain")
        graph.add_node(create_test_node("n1"))

        data = graph.to_dict()
        assert data["name"] == "test"
        assert data["domain"] == "test_domain"
        assert "n1" in data["nodes"]

    def test_from_dict(self):
        """Test deserializing from dictionary."""
        graph = NetworkGraph(name="test")
        graph.add_node(create_test_node("n1"))
        graph.add_node(create_test_node("n2"))
        graph.add_edge(create_test_edge("e1", "n1", "n2"))

        data = graph.to_dict()
        restored = NetworkGraph.from_dict(data)

        assert restored.name == "test"
        assert restored.node_count == 2
        assert restored.edge_count == 1


class TestSubgraph:
    """Tests for subgraph extraction."""

    def test_subgraph(self):
        """Test extracting subgraph."""
        graph = NetworkGraph()
        graph.add_node(create_test_node("a"))
        graph.add_node(create_test_node("b"))
        graph.add_node(create_test_node("c"))
        graph.add_edge(create_test_edge("e1", "a", "b"))
        graph.add_edge(create_test_edge("e2", "b", "c"))

        sub = graph.subgraph(["a", "b"])
        assert sub.node_count == 2
        assert sub.edge_count == 1
        assert sub.get_node("a") is not None
        assert sub.get_node("c") is None