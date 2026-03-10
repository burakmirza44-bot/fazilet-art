"""Unit tests for Claude Network models."""

import pytest

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


class TestPortDefinition:
    """Tests for PortDefinition."""

    def test_create_port(self):
        """Test creating a port definition."""
        port = PortDefinition(name="input", data_type="str", required=True)
        assert port.name == "input"
        assert port.data_type == "str"
        assert port.required is True

    def test_port_to_dict(self):
        """Test port serialization."""
        port = PortDefinition(name="output", data_type="dict", description="Result output")
        d = port.to_dict()
        assert d["name"] == "output"
        assert d["data_type"] == "dict"
        assert d["description"] == "Result output"


class TestNetworkNode:
    """Tests for NetworkNode."""

    def test_create_node(self):
        """Test creating a network node."""
        node = NetworkNode(
            node_id="test_node",
            node_type=NodeType.AGENT,
            name="Test Agent",
        )
        assert node.node_id == "test_node"
        assert node.node_type == NodeType.AGENT
        assert node.name == "Test Agent"

    def test_node_hash_and_equality(self):
        """Test node hashing and equality."""
        node1 = NetworkNode(node_id="id1", node_type=NodeType.AGENT, name="Node 1")
        node2 = NetworkNode(node_id="id1", node_type=NodeType.TOOL, name="Node 2")
        node3 = NetworkNode(node_id="id2", node_type=NodeType.AGENT, name="Node 1")

        # Same ID means equal
        assert node1 == node2
        # Different ID means not equal
        assert node1 != node3
        # Hash based on ID
        assert hash(node1) == hash(node2)

    def test_node_ports(self):
        """Test getting port names."""
        node = NetworkNode(
            node_id="test",
            node_type=NodeType.AGENT,
            name="Test Node",
            inputs=[
                PortDefinition(name="input1"),
                PortDefinition(name="input2"),
            ],
            outputs=[
                PortDefinition(name="output"),
            ],
        )
        assert node.get_input_names() == ["input1", "input2"]
        assert node.get_output_names() == ["output"]

    def test_node_capabilities(self):
        """Test capability checking."""
        node = NetworkNode(
            node_id="test",
            node_type=NodeType.ROUTER,
            name="Test Router",
            capabilities=["houdini", "touchdesigner"],
        )
        assert node.has_capability("houdini") is True
        assert node.has_capability("blender") is False


class TestNetworkEdge:
    """Tests for NetworkEdge."""

    def test_create_edge(self):
        """Test creating an edge."""
        edge = NetworkEdge(
            edge_id="e1",
            source_node="node1",
            source_port="output",
            target_node="node2",
            target_port="input",
        )
        assert edge.edge_id == "e1"
        assert edge.edge_type == EdgeType.DATA

    def test_edge_transform(self):
        """Test edge transformation."""
        edge = NetworkEdge(
            edge_id="e1",
            source_node="n1",
            source_port="out",
            target_node="n2",
            target_port="in",
            transform=lambda x: x.upper(),
        )
        result = edge.apply_transform("hello")
        assert result == "HELLO"

    def test_edge_no_transform(self):
        """Test edge without transformation."""
        edge = NetworkEdge(
            edge_id="e1",
            source_node="n1",
            source_port="out",
            target_node="n2",
            target_port="in",
        )
        result = edge.apply_transform("hello")
        assert result == "hello"


class TestNodeResult:
    """Tests for NodeResult."""

    def test_successful_result(self):
        """Test successful node result."""
        result = NodeResult(
            node_id="node1",
            status=NodeStatus.COMPLETED,
            outputs={"output": "success"},
        )
        assert result.success is True
        assert result.outputs["output"] == "success"

    def test_failed_result(self):
        """Test failed node result."""
        result = NodeResult(
            node_id="node1",
            status=NodeStatus.FAILED,
            error="Something went wrong",
        )
        assert result.success is False
        assert result.error == "Something went wrong"


class TestNetworkResult:
    """Tests for NetworkResult."""

    def test_add_results(self):
        """Test adding node results."""
        net_result = NetworkResult(network_name="test_network")

        result1 = NodeResult(node_id="n1", status=NodeStatus.COMPLETED)
        result2 = NodeResult(node_id="n2", status=NodeStatus.FAILED)
        result3 = NodeResult(node_id="n3", status=NodeStatus.SKIPPED)

        net_result.add_node_result(result1)
        net_result.add_node_result(result2)
        net_result.add_node_result(result3)

        assert net_result.nodes_executed == 3
        assert net_result.nodes_failed == 1
        assert net_result.nodes_skipped == 1
        assert net_result.get_successful_nodes() == ["n1"]
        assert net_result.get_failed_nodes() == ["n2"]


class TestFactoryFunctions:
    """Tests for node factory functions."""

    def test_create_agent_node(self):
        """Test agent node factory."""
        node = create_agent_node(
            node_id="agent1",
            name="Test Agent",
            provider="claude",
            system_prompt="You are helpful.",
            tools=["tool1"],
            capabilities=["code"],
        )
        assert node.node_type == NodeType.AGENT
        assert node.config["provider"] == "claude"
        assert node.config["system_prompt"] == "You are helpful."
        assert "code" in node.capabilities

    def test_create_tool_node(self):
        """Test tool node factory."""
        node = create_tool_node(
            node_id="tool1",
            name="Test Tool",
            tool_name="execute",
        )
        assert node.node_type == NodeType.TOOL
        assert node.config["tool_name"] == "execute"

    def test_create_memory_node(self):
        """Test memory node factory."""
        node = create_memory_node(
            node_id="mem1",
            name="Memory",
            query_type="success_patterns",
            max_results=10,
        )
        assert node.node_type == NodeType.MEMORY
        assert node.config["query_type"] == "success_patterns"

    def test_create_router_node(self):
        """Test router node factory."""
        node = create_router_node(
            node_id="router1",
            name="Router",
            domains=["houdini", "touchdesigner"],
        )
        assert node.node_type == NodeType.ROUTER
        assert "houdini" in node.capabilities

    def test_create_decomposer_node(self):
        """Test decomposer node factory."""
        node = create_decomposer_node(
            node_id="decomp1",
            name="Decomposer",
            max_subtasks=10,
        )
        assert node.node_type == NodeType.DECOMPOSER
        assert node.config["max_subtasks"] == 10


class TestOrchestratorConfig:
    """Tests for OrchestratorConfig."""

    def test_default_config(self):
        """Test default configuration."""
        config = OrchestratorConfig()
        assert config.max_parallel_nodes == 4
        assert config.default_timeout_seconds == 30.0
        assert config.retry_count == 2
        assert config.fail_fast is True

    def test_custom_config(self):
        """Test custom configuration."""
        config = OrchestratorConfig(
            max_parallel_nodes=8,
            default_timeout_seconds=60.0,
            retry_count=3,
            fail_fast=False,
        )
        assert config.max_parallel_nodes == 8
        assert config.fail_fast is False