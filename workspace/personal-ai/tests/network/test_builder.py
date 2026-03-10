"""Unit tests for Claude Network builder."""

import pytest

from app.network.builder import (
    NetworkBuilder,
    agent_node,
    decomposer_node,
    memory_node,
    network,
    router_node,
    tool_node,
)
from app.network.models import EdgeType, NodeType


class TestNetworkBuilder:
    """Tests for NetworkBuilder fluent API."""

    def test_create_empty_network(self):
        """Test creating empty network."""
        builder = NetworkBuilder("test_network")
        assert builder._name == "test_network"

    def test_add_agent_node(self):
        """Test adding agent node."""
        builder = (
            NetworkBuilder("test")
            .add_agent(
                node_id="agent1",
                name="Test Agent",
                provider="claude",
                system_prompt="You are helpful.",
            )
        )

        assert "agent1" in builder._nodes
        node = builder._nodes["agent1"]
        assert node.node_type == NodeType.AGENT
        assert node.config["provider"] == "claude"

    def test_add_tool_node(self):
        """Test adding tool node."""
        builder = (
            NetworkBuilder("test")
            .add_tool(
                node_id="tool1",
                tool_name="execute",
            )
        )

        assert "tool1" in builder._nodes
        assert builder._nodes["tool1"].node_type == NodeType.TOOL

    def test_add_memory_node(self):
        """Test adding memory node."""
        builder = (
            NetworkBuilder("test")
            .add_memory(
                node_id="memory1",
                query_type="success_patterns",
            )
        )

        assert "memory1" in builder._nodes
        assert builder._nodes["memory1"].node_type == NodeType.MEMORY

    def test_add_router_node(self):
        """Test adding router node."""
        builder = (
            NetworkBuilder("test")
            .add_router(
                node_id="router1",
                domains=["houdini", "touchdesigner"],
            )
        )

        assert "router1" in builder._nodes
        assert builder._nodes["router1"].node_type == NodeType.ROUTER
        assert "houdini" in builder._nodes["router1"].capabilities

    def test_add_decomposer_node(self):
        """Test adding decomposer node."""
        builder = (
            NetworkBuilder("test")
            .add_decomposer(
                node_id="decomp1",
                max_subtasks=10,
            )
        )

        assert "decomp1" in builder._nodes
        assert builder._nodes["decomp1"].node_type == NodeType.DECOMPOSER

    def test_connect_nodes(self):
        """Test connecting nodes."""
        builder = (
            NetworkBuilder("test")
            .add_agent("a")
            .add_agent("b")
            .connect("a", "b")
        )

        assert len(builder._connections) == 1
        conn = builder._connections[0]
        assert conn[0] == "a"  # source
        assert conn[2] == "b"  # target

    def test_connect_with_edge_types(self):
        """Test connecting with different edge types."""
        builder = (
            NetworkBuilder("test")
            .add_agent("a")
            .add_agent("b")
            .add_agent("c")
            .connect_data("a", "b")
            .connect_control("b", "c", condition="success == True")
            .connect_memory("a", "c")
        )

        assert len(builder._connections) == 3

    def test_build_graph(self):
        """Test building graph from builder."""
        graph = (
            NetworkBuilder("test_network")
            .with_domain("test_domain")
            .add_agent("source")
            .add_agent("target")
            .connect("source", "target")
            .build_graph()
        )

        assert graph.name == "test_network"
        assert graph.domain == "test_domain"
        assert graph.node_count == 2
        assert graph.edge_count == 1

    def test_build_orchestrator(self):
        """Test building orchestrator."""
        orchestrator = (
            NetworkBuilder("test")
            .add_agent("a")
            .with_config(max_parallel=8, timeout_seconds=60.0)
            .build()
        )

        assert orchestrator is not None
        assert orchestrator._graph.node_count == 1
        assert orchestrator._config.max_parallel_nodes == 8


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_network_function(self):
        """Test network() function."""
        builder = network("my_network", domain="test")
        assert isinstance(builder, NetworkBuilder)
        assert builder._name == "my_network"
        assert builder._domain == "test"

    def test_agent_node_function(self):
        """Test agent_node() function."""
        node = agent_node(
            "agent1",
            provider="claude",
            system_prompt="Test",
        ).build()

        assert node.node_id == "agent1"
        assert node.node_type == NodeType.AGENT

    def test_router_node_function(self):
        """Test router_node() function."""
        node = router_node(
            "router1",
            domains=["houdini"],
        ).build()

        assert node.node_id == "router1"
        assert node.node_type == NodeType.ROUTER

    def test_memory_node_function(self):
        """Test memory_node() function."""
        node = memory_node("mem1").build()

        assert node.node_id == "mem1"
        assert node.node_type == NodeType.MEMORY

    def test_tool_node_function(self):
        """Test tool_node() function."""
        node = tool_node("tool1", tool_name="execute").build()

        assert node.node_id == "tool1"
        assert node.node_type == NodeType.TOOL

    def test_decomposer_node_function(self):
        """Test decomposer_node() function."""
        node = decomposer_node("decomp1", max_subtasks=5).build()

        assert node.node_id == "decomp1"
        assert node.node_type == NodeType.DECOMPOSER


class TestComplexNetwork:
    """Tests for complex network building."""

    def test_build_multi_agent_network(self):
        """Test building multi-agent network."""
        graph = (
            NetworkBuilder("houdini-pipeline")
            .with_domain("houdini")
            .add_router("router", domains=["houdini", "touchdesigner"])
            .add_memory("memory", query_type="success_patterns")
            .add_agent(
                "planner",
                provider="claude",
                system_prompt="You are a task planner...",
            )
            .add_agent(
                "houdini_expert",
                provider="claude",
                system_prompt="You are a Houdini expert...",
                capabilities=["sop", "vex", "python"],
            )
            .add_agent(
                "td_expert",
                provider="claude",
                system_prompt="You are a TouchDesigner expert...",
                capabilities=["top", "chop", "python"],
            )
            .connect("router", "memory", edge_type=EdgeType.MEMORY)
            .connect("memory", "planner")
            .connect("planner", "houdini_expert", condition="domain == 'houdini'")
            .connect("planner", "td_expert", condition="domain == 'touchdesigner'")
            .build_graph()
        )

        assert graph.node_count == 5
        assert graph.edge_count == 4

        # Validate graph
        result = graph.validate()
        assert result.valid is True

    def test_build_with_conditional_routing(self):
        """Test building network with conditional routing."""
        graph = (
            NetworkBuilder("conditional")
            .add_router("router", domains=["code", "houdini"])
            .add_agent("code_agent")
            .add_agent("houdini_agent")
            .connect_control("router", "code_agent", condition="domain == 'code'")
            .connect_control("router", "houdini_agent", condition="domain == 'houdini'")
            .build_graph()
        )

        assert graph.node_count == 3
        # Check edges have conditions
        edges = graph.edges
        for edge in edges.values():
            if edge.source_node == "router":
                assert edge.condition is not None