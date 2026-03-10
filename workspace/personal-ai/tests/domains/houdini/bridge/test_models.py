"""Tests for Houdini Bridge models."""

import pytest

from app.domains.houdini.bridge.models import (
    HoudiniBridgeConfig,
    RecipeRequest,
    RecipeResult,
    RecipeStep,
    StepResult,
    connect_nodes_step,
    create_node_step,
    run_script_step,
    set_parameter_step,
)


class TestRecipeStep:
    """Tests for RecipeStep."""

    def test_create_step(self):
        """Test creating a recipe step."""
        step = RecipeStep(
            order=1,
            name="Create box",
            action="create_node",
            node_type="box",
            node_path="/obj/geo1/box1",
        )
        assert step.order == 1
        assert step.action == "create_node"
        assert step.node_type == "box"

    def test_step_to_dict(self):
        """Test step serialization."""
        step = RecipeStep(
            order=1,
            name="Set size",
            action="set_parameter",
            target_node="box1",
            parameter="sizex",
            value=2.0,
        )
        d = step.to_dict()
        assert d["order"] == 1
        assert d["target_node"] == "box1"
        assert d["value"] == 2.0

    def test_step_from_dict(self):
        """Test step deserialization."""
        data = {
            "order": 2,
            "name": "Connect nodes",
            "action": "make_connection",
            "source_node": "box1",
            "target_node": "null1",
        }
        step = RecipeStep.from_dict(data)
        assert step.order == 2
        assert step.source_node == "box1"

    def test_step_defaults(self):
        """Test step default values."""
        step = RecipeStep(order=1, name="Test", action="test")
        assert step.continue_on_error is False
        assert step.verify is False
        assert step.timeout == 10.0


class TestRecipeRequest:
    """Tests for RecipeRequest."""

    def test_create_request(self):
        """Test creating a recipe request."""
        steps = [
            RecipeStep(order=1, name="Create GEO", action="create_node"),
        ]
        request = RecipeRequest(
            recipe_id="test_recipe",
            recipe_steps=steps,
        )
        assert request.recipe_id == "test_recipe"
        assert len(request.recipe_steps) == 1

    def test_auto_generate_id(self):
        """Test auto-generated recipe ID."""
        steps = []
        request = RecipeRequest(recipe_id="", recipe_steps=steps)
        assert request.recipe_id  # Should have auto-generated ID
        assert request.recipe_id.startswith("recipe_")

    def test_request_to_dict(self):
        """Test request serialization."""
        steps = [
            RecipeStep(order=1, name="Create", action="create_node"),
        ]
        request = RecipeRequest(recipe_id="test", recipe_steps=steps)
        d = request.to_dict()
        assert d["recipe_id"] == "test"
        assert len(d["recipe_steps"]) == 1

    def test_request_from_dict(self):
        """Test request deserialization."""
        data = {
            "recipe_id": "test_123",
            "recipe_steps": [
                {
                    "order": 1,
                    "name": "Create box",
                    "action": "create_node",
                    "node_type": "box",
                }
            ],
            "context": {"network": "/obj"},
            "timeout": 60.0,
        }
        request = RecipeRequest.from_dict(data)
        assert request.recipe_id == "test_123"
        assert len(request.recipe_steps) == 1
        assert request.context["network"] == "/obj"


class TestStepResult:
    """Tests for StepResult."""

    def test_success_result(self):
        """Test successful step result."""
        result = StepResult(
            step_name="Create box",
            success=True,
            output={"created_node": "/obj/geo1/box1"},
        )
        assert result.success is True
        assert result.output["created_node"] == "/obj/geo1/box1"

    def test_failure_result(self):
        """Test failed step result."""
        result = StepResult(
            step_name="Set parameter",
            success=False,
            error="Parameter not found",
        )
        assert result.success is False
        assert result.error == "Parameter not found"

    def test_result_to_dict(self):
        """Test result serialization."""
        result = StepResult(
            step_name="Test",
            success=True,
            execution_time_ms=123.45,
        )
        d = result.to_dict()
        assert d["step_name"] == "Test"
        assert d["execution_time_ms"] == 123.45


class TestRecipeResult:
    """Tests for RecipeResult."""

    def test_success_result(self):
        """Test successful recipe result."""
        result = RecipeResult(
            recipe_id="test",
            success=True,
            steps_executed=["Create box", "Set parameter"],
            output={"created_nodes": ["/obj/geo1/box1"]},
        )
        assert result.success is True
        assert len(result.steps_executed) == 2
        assert len(result.errors) == 0

    def test_failure_result(self):
        """Test failed recipe result."""
        result = RecipeResult(
            recipe_id="test",
            success=False,
            errors=[{"step": "Create box", "error": "Node type not found"}],
        )
        assert result.success is False
        assert len(result.errors) == 1

    def test_result_to_dict_and_back(self):
        """Test serialization round-trip."""
        original = RecipeResult(
            recipe_id="test",
            success=True,
            steps_executed=["Create", "Connect"],
            output={"nodes": 2},
            houdini_version=(20, 0, 590),
        )
        data = original.to_dict()
        restored = RecipeResult.from_dict(data)

        assert restored.recipe_id == original.recipe_id
        assert restored.success == original.success
        assert restored.steps_executed == original.steps_executed
        assert restored.houdini_version == original.houdini_version


class TestFactoryFunctions:
    """Tests for factory functions."""

    def test_create_node_step(self):
        """Test create_node_step factory."""
        step = create_node_step(
            order=1,
            node_type="geo",
            node_path="/obj/geo1",
        )
        assert step.action == "create_node"
        assert step.node_type == "geo"
        assert step.node_path == "/obj/geo1"

    def test_set_parameter_step(self):
        """Test set_parameter_step factory."""
        step = set_parameter_step(
            order=2,
            target_node="box1",
            parameter="sizex",
            value=5.0,
        )
        assert step.action == "set_parameter"
        assert step.target_node == "box1"
        assert step.value == 5.0

    def test_connect_nodes_step(self):
        """Test connect_nodes_step factory."""
        step = connect_nodes_step(
            order=3,
            source_node="box1",
            target_node="null1",
            source_output=0,
            target_input=0,
        )
        assert step.action == "make_connection"
        assert step.source_node == "box1"
        assert step.target_node == "null1"

    def test_run_script_step(self):
        """Test run_script_step factory."""
        step = run_script_step(
            order=4,
            script="print('hello')",
        )
        assert step.action == "run_script"
        assert step.script == "print('hello')"


class TestHoudiniBridgeConfig:
    """Tests for HoudiniBridgeConfig."""

    def test_default_config(self):
        """Test default configuration."""
        config = HoudiniBridgeConfig()
        assert config.inbox_dir == "./data/inbox"
        assert config.outbox_dir == "./data/outbox"
        assert config.poll_interval == 1.0

    def test_custom_config(self):
        """Test custom configuration."""
        config = HoudiniBridgeConfig(
            inbox_dir="/custom/inbox",
            outbox_dir="/custom/outbox",
            poll_interval=0.5,
            timeout=60.0,
        )
        assert config.inbox_dir == "/custom/inbox"
        assert config.poll_interval == 0.5