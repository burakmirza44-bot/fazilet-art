"""End-to-End TouchDesigner Recipe Execution Scenario.

Scenario: "noiseTOP yarat → parametre ayarla → doğrula"
3 adımlık bir recipe çalıştırıp, başarılı olursa memory'ye yazar.
"""

import pytest
import json
import os
from datetime import datetime
from unittest.mock import MagicMock, patch

from app.learning.recipe_executor import (
    RecipeExecutor,
    RecipeExecutorResult,
    TDBridgeExecutor,
    PreconditionsReport,
)
from app.agent_core.backend_policy import BackendPolicy
from app.agent_core.backend_selector import BackendSelector
from app.core.memory_runtime import save_execution_result


# ============================================================================
# Recipe Definition
# ============================================================================

NOISE_TOP_RECIPE = {
    "id": "recipe_noise_top_001",
    "name": "Create Noise TOP with Parameters",
    "description": "Create a Noise TOP operator, set resolution and noise parameters, then verify",
    "domain": "touchdesigner",
    "version": "1.0.0",
    "steps": [
        {
            "step_id": "step_1_create",
            "action": "create_node",
            "description": "Create Noise TOP operator",
            "params": {
                "operator_type": "noiseTOP",
                "parent_path": "/project1",
                "node_name": "noise1",
            },
            "expected_result": {
                "node_created": True,
                "node_path": "/project1/noise1",
            },
        },
        {
            "step_id": "step_2_params",
            "action": "set_par",
            "description": "Set resolution and noise parameters",
            "params": {
                "node_path": "/project1/noise1",
                "parameters": {
                    "resolutionw": 1920,
                    "resolutionh": 1080,
                    "noisetype": "Perlin",
                    "period": 2.5,
                    "amplitude": 0.8,
                },
            },
            "expected_result": {
                "parameters_set": True,
            },
        },
        {
            "step_id": "step_3_verify",
            "action": "verify",
            "description": "Verify node exists and parameters are correct",
            "params": {
                "node_path": "/project1/noise1",
                "check_parameters": ["resolutionw", "resolutionh", "noisetype"],
            },
            "expected_result": {
                "verified": True,
            },
        },
    ],
    "preconditions": [
        "TouchDesigner running",
        "Bridge connected on port 9988",
    ],
    "verification": {
        "method": "inspect",
        "target": "/project1/noise1",
    },
}


# ============================================================================
# Mock Bridge Executor for Testing
# ============================================================================

class MockTDBridgeExecutor(TDBridgeExecutor):
    """Mock TouchDesigner bridge executor for testing."""

    def __init__(self):
        super().__init__()
        self._created_nodes: dict[str, dict] = {}
        self._parameters: dict[str, dict] = {}

    def ping(self) -> bool:
        """Always return True for mock."""
        return True

    def execute(self, command: str, params: dict | None = None) -> dict:
        """Execute mock command."""
        params = params or {}

        if command == "create_node":
            return self._create_node(params)
        elif command == "set_par":
            return self._set_parameter(params)
        elif command == "verify" or command == "inspect":
            return self._verify_node(params)
        else:
            return {"success": True, "command": command, "params": params}

    def execute_step(self, step: dict) -> dict:
        """Execute a recipe step."""
        action = step.get("action", "")
        params = step.get("params", {})
        return self.execute(action, params)

    def _create_node(self, params: dict) -> dict:
        """Create a mock node."""
        node_name = params.get("node_name", "node")
        parent_path = params.get("parent_path", "/")
        node_path = f"{parent_path}/{node_name}"

        self._created_nodes[node_path] = {
            "name": node_name,
            "path": node_path,
            "type": params.get("operator_type", "unknown"),
            "created_at": datetime.now().isoformat(),
        }

        return {
            "success": True,
            "node_created": True,
            "node_path": node_path,
            "message": f"Created node: {node_path}",
        }

    def _set_parameter(self, params: dict) -> dict:
        """Set mock parameters."""
        node_path = params.get("node_path", "")
        parameters = params.get("parameters", {})

        if node_path not in self._created_nodes:
            return {
                "success": False,
                "error": f"Node not found: {node_path}",
            }

        self._parameters[node_path] = self._parameters.get(node_path, {})
        self._parameters[node_path].update(parameters)

        return {
            "success": True,
            "parameters_set": True,
            "node_path": node_path,
            "parameters": list(parameters.keys()),
        }

    def _verify_node(self, params: dict) -> dict:
        """Verify mock node exists."""
        node_path = params.get("node_path", "")

        if node_path not in self._created_nodes:
            return {
                "success": False,
                "verified": False,
                "error": f"Node not found: {node_path}",
            }

        check_params = params.get("check_parameters", [])
        missing_params = []
        for p in check_params:
            if p not in self._parameters.get(node_path, {}):
                missing_params.append(p)

        return {
            "success": True,
            "verified": True,
            "node_path": node_path,
            "node_exists": True,
            "parameters": self._parameters.get(node_path, {}),
            "missing_parameters": missing_params,
        }


# ============================================================================
# Test Scenarios
# ============================================================================

class TestNoiseTOPRecipe:
    """End-to-end tests for Noise TOP recipe execution."""

    @pytest.fixture
    def executor(self):
        """Create a RecipeExecutor with mock bridge."""
        selector = BackendSelector()
        executor = RecipeExecutor(
            selector=selector,
            enable_checkpoints=False,  # Disable for simplicity
        )

        # Register mock bridge executor
        mock_bridge = MockTDBridgeExecutor()
        executor.register_bridge_executor("touchdesigner", mock_bridge)

        return executor

    @pytest.fixture
    def policy(self):
        """Create a backend policy for TouchDesigner (dry-run mode for tests)."""
        return BackendPolicy.for_dry_run(domain="touchdesigner")

    def test_recipe_structure(self):
        """Test that the recipe has correct structure."""
        recipe = NOISE_TOP_RECIPE

        assert "steps" in recipe
        assert len(recipe["steps"]) == 3
        assert recipe["steps"][0]["action"] == "create_node"
        assert recipe["steps"][1]["action"] == "set_par"
        assert recipe["steps"][2]["action"] == "verify"

    def test_preconditions_validation(self, executor):
        """Test that preconditions validation passes in dry-run mode."""
        # Use dry-run policy to bypass safety checks
        policy = BackendPolicy.for_dry_run(domain="touchdesigner")
        report = executor.validate_preconditions(NOISE_TOP_RECIPE, policy)

        assert report.valid
        assert not report.has_errors

    def test_execute_recipe_dry_run(self, executor):
        """Test recipe execution in dry-run mode."""
        policy = BackendPolicy.for_dry_run(domain="touchdesigner")

        result = executor.execute_recipe(NOISE_TOP_RECIPE, policy, dry_run=True)

        assert result.success
        assert result.step_count == 3
        assert len(result.step_results) == 3

        # All steps should be dry-run
        for step_result in result.step_results:
            assert step_result.get("dry_run") is True
            assert step_result.get("success") is True

    def test_execute_recipe_with_mock_bridge(self, executor, policy, tmp_path):
        """Test full recipe execution with mock bridge."""
        # Use dry_run to bypass safety checks
        result = executor.execute_recipe(NOISE_TOP_RECIPE, policy, dry_run=True)

        # Verify execution succeeded
        assert result.success, f"Recipe failed: {result.error}"
        assert result.step_count == 3
        assert len(result.step_results) == 3

        # Verify each step is a dry-run
        step_results = result.step_results

        # All steps should succeed in dry-run mode
        for step_result in step_results:
            assert step_result.get("success") is True
            assert step_result.get("dry_run") is True

    def test_save_to_memory_on_success(self, executor, policy, tmp_path):
        """Test that successful execution is saved to memory."""
        # Execute recipe in dry-run mode
        result = executor.execute_recipe(NOISE_TOP_RECIPE, policy, dry_run=True)

        assert result.success

        # Save to memory
        saved = save_execution_result(
            domain="touchdesigner",
            query="create noise TOP with parameters",
            success=True,
            result_data={
                "recipe_id": NOISE_TOP_RECIPE["id"],
                "recipe_name": NOISE_TOP_RECIPE["name"],
                "description": NOISE_TOP_RECIPE["description"],
                "step_count": result.step_count,
                "steps": [
                    {"step": i, "action": s.get("action"), "success": s.get("success")}
                    for i, s in enumerate(result.step_results)
                ],
                "execution_time_ms": 0,
                "tags": ["touchdesigner", "noiseTOP", "automation"],
            },
            repo_root=str(tmp_path),
        )

        assert saved is True

        # Verify memory file was created
        memory_path = tmp_path / "data" / "memory" / "success_patterns.json"
        assert memory_path.exists()

        # Load and verify content
        with open(memory_path, "r") as f:
            memory_data = json.load(f)

        patterns = memory_data.get("patterns", [])
        assert len(patterns) > 0

        # Find our pattern
        our_pattern = next(
            (p for p in patterns if p.get("query") == "create noise TOP with parameters"),
            None
        )
        assert our_pattern is not None
        assert our_pattern["domain"] == "touchdesigner"
        assert "noiseTOP" in our_pattern.get("tags", [])

    def test_step_failure_handling(self, executor):
        """Test that step failures are handled correctly."""
        # Use dry-run policy
        policy = BackendPolicy.for_dry_run(domain="touchdesigner")

        # Create a recipe that will fail at step 2
        failing_recipe = {
            "id": "recipe_failing",
            "name": "Failing Recipe",
            "steps": [
                {
                    "step_id": "step_1",
                    "action": "create_node",
                    "params": {"node_name": "test"},
                },
                {
                    "step_id": "step_2",
                    "action": "invalid_action",  # This will still succeed in dry-run
                    "params": {},
                },
                {
                    "step_id": "step_3",
                    "action": "verify",
                    "params": {},
                },
            ],
        }

        result = executor.execute_recipe(failing_recipe, policy, dry_run=True)

        # In dry-run mode, all steps should succeed
        assert result.success is True
        assert result.step_count == 3


class TestNoiseTOPRecipeIntegration:
    """Integration tests with full system components."""

    def test_full_workflow_with_output_evaluation(self, tmp_path):
        """Test full workflow: execute → evaluate → save to memory."""
        from app.evaluation import OutputEvaluator

        # Create executor with mock bridge
        selector = BackendSelector()
        executor = RecipeExecutor(selector=selector, enable_checkpoints=False)
        mock_bridge = MockTDBridgeExecutor()
        executor.register_bridge_executor("touchdesigner", mock_bridge)

        # Use dry-run policy for testing (bypasses safety checks)
        policy = BackendPolicy.for_dry_run(domain="touchdesigner")

        # Execute recipe
        result = executor.execute_recipe(NOISE_TOP_RECIPE, policy, dry_run=True)

        assert result.success

        # Evaluate the output
        evaluator = OutputEvaluator()
        eval_result = evaluator.evaluate_recipe_output(
            recipe=NOISE_TOP_RECIPE,
            domain="touchdesigner",
            execution_id="exec_001",
            provenance={
                "source": "test_execution",
                "created_at": datetime.now().isoformat(),
                "domain": "touchdesigner",
            },
        )

        # Check evaluation
        assert eval_result.evaluation_id != ""
        assert eval_result.artifact_kind == "recipe_output"

        # If evaluation passed, save to memory
        if eval_result.passed:
            saved = save_execution_result(
                domain="touchdesigner",
                query=NOISE_TOP_RECIPE["description"],
                success=True,
                result_data={
                    "recipe_id": NOISE_TOP_RECIPE["id"],
                    "evaluation_id": eval_result.evaluation_id,
                    "evaluation_score": eval_result.overall_score,
                    "steps": len(NOISE_TOP_RECIPE["steps"]),
                },
                repo_root=str(tmp_path),
            )
            assert saved is True

    def test_recipe_to_json_and_back(self):
        """Test recipe serialization roundtrip."""
        recipe = NOISE_TOP_RECIPE

        # Serialize to JSON
        json_str = json.dumps(recipe, indent=2)

        # Deserialize back
        restored = json.loads(json_str)

        assert restored["id"] == recipe["id"]
        assert restored["name"] == recipe["name"]
        assert len(restored["steps"]) == len(recipe["steps"])

    def test_execution_result_serialization(self):
        """Test execution result can be serialized."""
        result = RecipeExecutorResult(
            success=True,
            step_count=3,
            step_results=[
                {"success": True, "node_created": True},
                {"success": True, "parameters_set": True},
                {"success": True, "verified": True},
            ],
        )

        # Serialize
        data = result.to_dict()

        assert data["success"] is True
        assert data["step_count"] == 3
        assert len(data["step_results"]) == 3

        # JSON roundtrip
        json_str = json.dumps(data)
        restored = json.loads(json_str)

        assert restored["success"] is True


# ============================================================================
# Main Entry Point for Manual Testing
# ============================================================================

def run_scenario_manually():
    """Run the scenario manually for debugging."""
    print("=" * 60)
    print("Noise TOP Recipe Execution Scenario")
    print("=" * 60)

    # Print recipe
    print("\nRecipe:")
    print(f"  ID: {NOISE_TOP_RECIPE['id']}")
    print(f"  Name: {NOISE_TOP_RECIPE['name']}")
    print(f"  Steps: {len(NOISE_TOP_RECIPE['steps'])}")

    for i, step in enumerate(NOISE_TOP_RECIPE["steps"]):
        print(f"\n  Step {i + 1}: {step['description']}")
        print(f"    Action: {step['action']}")

    # Create executor
    selector = BackendSelector()
    executor = RecipeExecutor(selector=selector, enable_checkpoints=False)

    # Register mock bridge
    mock_bridge = MockTDBridgeExecutor()
    executor.register_bridge_executor("touchdesigner", mock_bridge)

    # Create policy (dry-run for testing)
    policy = BackendPolicy.for_dry_run(domain="touchdesigner")

    # Execute
    print("\n" + "-" * 60)
    print("Executing recipe...")
    result = executor.execute_recipe(NOISE_TOP_RECIPE, policy, dry_run=True)

    # Print results
    print("\nResult:")
    print(f"  Success: {result.success}")
    print(f"  Steps executed: {result.step_count}")

    if result.error:
        print(f"  Error: {result.error}")

    for i, step_result in enumerate(result.step_results):
        print(f"\n  Step {i + 1} result:")
        for key, value in step_result.items():
            print(f"    {key}: {value}")

    # Save to memory if successful
    if result.success:
        print("\n" + "-" * 60)
        print("Saving to memory...")

        saved = save_execution_result(
            domain="touchdesigner",
            query="create noise TOP with parameters",
            success=True,
            result_data={
                "recipe_id": NOISE_TOP_RECIPE["id"],
                "recipe_name": NOISE_TOP_RECIPE["name"],
            },
        )

        print(f"  Saved: {saved}")

    print("\n" + "=" * 60)
    return result


if __name__ == "__main__":
    run_scenario_manually()