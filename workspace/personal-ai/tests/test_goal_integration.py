"""Tests for Goal Generator Integration.

Tests integration of GoalGenerator with runtime loop, decomposition,
repair flow, and checkpoint resume flows.
"""

import pytest
from unittest.mock import MagicMock, patch
import tempfile
import os

# Import directly from modules to avoid circular import
from app.agent_core.goal_generator import (
    GoalGenerator,
    GoalGeneratorConfig,
    build_goal_request_from_task,
)
from app.agent_core.goal_models import (
    DomainHint,
    GoalArtifact,
    GoalGenerationMode,
    GoalGenerationResult,
    GoalRequest,
    GoalSourceSignal,
    GoalType,
)
from app.agent_core.goal_errors import (
    GoalGenerationError,
    GoalGenerationErrorType,
)


class TestRuntimeLoopIntegration:
    """Tests for runtime loop integration with GoalGenerator."""

    def test_generate_goal_before_execution(self):
        """Test that goals can be generated before execution."""
        generator = GoalGenerator()

        # Simulate runtime loop creating a goal request before execution
        request = GoalRequest.create(
            task_id="task_001",
            session_id="session_001",
            domain_hint=DomainHint.HOUDINI,
            raw_task_summary="Create a procedural terrain",
            goal_generation_mode=GoalGenerationMode.NEXT_GOAL.value,
            current_runtime_state_summary="Bridge healthy, ready to execute",
        )

        result = generator.generate_goals(request)

        assert result.has_goals
        assert result.primary_goal is not None

        # The goal should be usable for execution
        goal = result.primary_goal
        assert goal.title != ""
        assert goal.description != ""
        assert goal.domain != ""

    def test_generate_goals_for_step_execution(self):
        """Test goal generation for individual step execution."""
        generator = GoalGenerator()

        # Simulate generating a goal for a specific step
        step_description = "Create heightfield node with 512x512 resolution"
        request = GoalRequest.create(
            task_id="task_001_step_1",
            session_id="session_001",
            domain_hint=DomainHint.HOUDINI,
            raw_task_summary=step_description,
            goal_generation_mode=GoalGenerationMode.NEXT_GOAL.value,
        )

        result = generator.generate_goals(request)

        assert result.has_goals
        goal = result.primary_goal
        assert goal.execution_feasibility in ["high", "medium", "low"]

    def test_goal_with_bridge_context(self):
        """Test goal generation with bridge health context."""
        generator = GoalGenerator()

        request = GoalRequest.create(
            task_id="task_001",
            session_id="session_001",
            domain_hint=DomainHint.HOUDINI,
            raw_task_summary="Execute Houdini operation",
            current_runtime_state_summary="Bridge connected at localhost:9989",
        )

        result = generator.generate_goals(request)

        assert result.has_goals
        goal = result.primary_goal
        # Goal should have valid execution feasibility
        assert goal.execution_feasibility in ["high", "medium", "low"]


class TestDecompositionIntegration:
    """Tests for decomposition integration with GoalGenerator."""

    def test_goal_artifact_to_decomposition_input(self):
        """Test that GoalArtifact can be used for decomposition."""
        generator = GoalGenerator()

        request = GoalRequest.create(
            task_id="task_001",
            session_id="session_001",
            domain_hint=DomainHint.HOUDINI,
            raw_task_summary="Create a complete procedural city with buildings and streets",
        )

        result = generator.generate_goals(request)
        goal = result.primary_goal

        # Goal should have fields useful for decomposition
        assert goal.description != ""
        assert goal.success_criteria is not None
        assert goal.preconditions is not None

        # Subgoals can be generated from the goal
        subgoal_request = GoalRequest.create(
            task_id="task_001",
            session_id="session_001",
            domain_hint=DomainHint(goal.domain) if goal.domain else DomainHint.UNKNOWN,
            raw_task_summary=goal.description,
            goal_generation_mode=GoalGenerationMode.SUBGOAL_GENERATION.value,
            current_goal_context={
                "goal_id": goal.goal_id,
                "title": goal.title,
                "description": goal.description,
            },
        )

        subgoal_result = generator.generate_goals(subgoal_request)

        # Should generate subgoals
        assert subgoal_result.has_goals or subgoal_result.final_status in ["success", "no_goals"]

    def test_subgoal_chain(self):
        """Test chaining goals through parent-child relationship."""
        generator = GoalGenerator()

        # Create root goal
        root_request = GoalRequest.create(
            task_id="task_001",
            session_id="session_001",
            domain_hint=DomainHint.HOUDINI,
            raw_task_summary="Create procedural city",
        )

        root_result = generator.generate_goals(root_request)
        root_goal = root_result.primary_goal

        # Generate subgoals
        subgoals = generator.generate_subgoals(root_request, root_goal)

        # Verify parent-child relationship
        for subgoal in subgoals:
            if subgoal.parent_goal_id:
                assert subgoal.parent_goal_id == root_goal.goal_id


class TestRepairFlowIntegration:
    """Tests for repair flow integration with GoalGenerator."""

    def test_failure_to_repair_goal(self):
        """Test generating repair goal from failure context."""
        generator = GoalGenerator()

        # Simulate a failure from execution
        failure_context = {
            "error_type": "execution_failed",
            "message": "Node creation failed: parameter out of range",
            "failed_goal_id": "goal_prev_001",
            "step_id": "step_003",
        }

        request = GoalRequest.create(
            task_id="task_001",
            session_id="session_001",
            domain_hint=DomainHint.HOUDINI,
            raw_task_summary="Fix the parameter error and retry",
            goal_generation_mode=GoalGenerationMode.REPAIR_GOAL.value,
            failure_context=failure_context,
        )

        result = generator.generate_goals(request)

        assert result.has_goals
        repair_goal = result.primary_goal

        assert repair_goal.goal_type == GoalType.REPAIR_GOAL.value
        assert repair_goal.repair_hint != ""
        assert GoalSourceSignal.FAILURE_CONTEXT.value in repair_goal.source_signals

    def test_repair_goal_with_memory_patterns(self):
        """Test repair goal uses memory patterns."""
        generator = GoalGenerator()

        failure_context = {
            "error_type": "timeout",
            "message": "Operation exceeded 30s timeout",
        }

        memory_summary = {
            "repair_patterns": [
                {
                    "pattern": "break_into_smaller_steps",
                    "description": "Divide operation into smaller chunks",
                }
            ]
        }

        request = GoalRequest.create(
            task_id="task_001",
            session_id="session_001",
            domain_hint=DomainHint.HOUDINI,
            raw_task_summary="Handle timeout",
            goal_generation_mode=GoalGenerationMode.REPAIR_GOAL.value,
            failure_context=failure_context,
            memory_summary=memory_summary,
        )

        result = generator.generate_goals(request)

        assert result.has_goals
        assert result.memory_influenced

    def test_bridge_failure_repair(self):
        """Test repair goal for bridge failure."""
        generator = GoalGenerator()

        failure_context = {
            "error_type": "bridge_unavailable",
            "message": "Houdini bridge connection refused",
            "bridge_type": "houdini",
            "host": "localhost",
            "port": 9989,
        }

        request = GoalRequest.create(
            task_id="task_001",
            session_id="session_001",
            domain_hint=DomainHint.HOUDINI,
            raw_task_summary="Reconnect to bridge",
            goal_generation_mode=GoalGenerationMode.REPAIR_GOAL.value,
            failure_context=failure_context,
        )

        result = generator.generate_goals(request)

        assert result.has_goals
        repair_goal = result.primary_goal
        assert repair_goal.goal_type == GoalType.REPAIR_GOAL.value
        assert "bridge" in repair_goal.repair_hint.lower() or "connection" in repair_goal.repair_hint.lower()


class TestCheckpointResumeIntegration:
    """Tests for checkpoint resume integration with GoalGenerator."""

    def test_checkpoint_to_resume_goal(self):
        """Test generating resume goal from checkpoint."""
        generator = GoalGenerator()

        checkpoint_summary = {
            "checkpoint_id": "ckpt_20240310_001",
            "domain": "houdini",
            "task_id": "task_001",
            "session_id": "session_001",
            "last_completed_step": {
                "step_id": "step_002",
                "description": "Created base geometry",
            },
            "next_pending_step": {
                "step_id": "step_003",
                "description": "Add terrain displacement",
                "action": "create_node",
            },
            "remaining_steps": [
                {"step_id": "step_003", "description": "Add terrain displacement"},
                {"step_id": "step_004", "description": "Apply materials"},
            ],
        }

        request = GoalRequest.create(
            task_id="task_001",
            session_id="session_001",
            domain_hint=DomainHint.HOUDINI,
            raw_task_summary="Resume from checkpoint",
            goal_generation_mode=GoalGenerationMode.RESUME_GOAL.value,
            checkpoint_summary=checkpoint_summary,
        )

        result = generator.generate_goals(request)

        assert result.has_goals
        resume_goal = result.primary_goal

        assert resume_goal.goal_type == GoalType.RESUME_GOAL.value
        assert "checkpoint" in resume_goal.description.lower() or "resume" in resume_goal.description.lower()

    def test_resume_goal_with_context(self):
        """Test resume goal preserves execution context."""
        generator = GoalGenerator()

        checkpoint_summary = {
            "checkpoint_id": "ckpt_001",
            "domain": "touchdesigner",
            "next_pending_step": {
                "step_id": "step_005",
                "description": "Create CHOP network for audio",
            },
            "bridge_health": {
                "healthy": True,
                "latency_ms": 15,
            },
        }

        request = GoalRequest.create(
            task_id="task_001",
            session_id="session_001",
            domain_hint=DomainHint.TOUCHDESIGNER,
            raw_task_summary="Resume",
            goal_generation_mode=GoalGenerationMode.RESUME_GOAL.value,
            checkpoint_summary=checkpoint_summary,
        )

        result = generator.generate_goals(request)

        assert result.has_goals
        resume_goal = result.primary_goal
        assert resume_goal.domain == "touchdesigner"


class TestVerificationIntegration:
    """Tests for verification integration with GoalGenerator."""

    def test_verification_goal_from_evidence_gap(self):
        """Test generating verification goal from evidence gaps."""
        generator = GoalGenerator()

        verification_context = {
            "target_goal_id": "goal_001",
            "verification_type": "outcome",
            "evidence_gaps": [
                {
                    "description": "Node exists in network",
                    "hint": "Check /obj/terrain/heightfield1",
                },
                {
                    "description": "Parameters are correct",
                    "hint": "Verify size = 512",
                },
            ],
        }

        request = GoalRequest.create(
            task_id="task_001",
            session_id="session_001",
            domain_hint=DomainHint.HOUDINI,
            raw_task_summary="Verify execution result",
            goal_generation_mode=GoalGenerationMode.VERIFICATION_GOAL.value,
            verification_context=verification_context,
        )

        result = generator.generate_goals(request)

        assert result.has_goals
        # Should generate verification goals for each gap (up to 3)
        assert len(result.generated_goals) >= 1

        for goal in result.generated_goals:
            assert goal.goal_type == GoalType.VERIFICATION_GOAL.value
            assert goal.verification_hint != ""


class TestSessionTraceVisibility:
    """Tests for session trace visibility with goals."""

    def test_goal_in_session_trace(self):
        """Test that goals can be serialized for session traces."""
        generator = GoalGenerator()

        request = GoalRequest.create(
            task_id="task_001",
            session_id="session_001",
            domain_hint=DomainHint.HOUDINI,
            raw_task_summary="Create procedural terrain",
        )

        result = generator.generate_goals(request)
        goal = result.primary_goal

        # Serialize goal for trace
        goal_dict = goal.to_dict()

        assert "goal_id" in goal_dict
        assert "title" in goal_dict
        assert "description" in goal_dict
        assert "goal_type" in goal_dict
        assert "domain" in goal_dict
        assert "created_at" in goal_dict

    def test_result_in_session_trace(self):
        """Test that result can be serialized for session traces."""
        generator = GoalGenerator()

        request = GoalRequest.create(
            task_id="task_001",
            session_id="session_001",
            domain_hint=DomainHint.HOUDINI,
            raw_task_summary="Create terrain",
        )

        result = generator.generate_goals(request)

        # Serialize result for trace
        result_dict = result.to_dict()

        assert "goal_generation_performed" in result_dict
        assert "generated_goal_count" in result_dict
        assert "domain_inferred" in result_dict
        assert "final_status" in result_dict
        assert "generated_goals" in result_dict


class TestMixedModeIntegration:
    """Tests for mixed mode goal generation."""

    def test_mixed_mode_with_multiple_contexts(self):
        """Test mixed mode with failure and checkpoint contexts."""
        generator = GoalGenerator()

        request = GoalRequest.create(
            task_id="task_001",
            session_id="session_001",
            domain_hint=DomainHint.HOUDINI,
            raw_task_summary="Handle situation",
            goal_generation_mode=GoalGenerationMode.MIXED.value,
            failure_context={"error_type": "timeout"},
            checkpoint_summary={"checkpoint_id": "ckpt_001"},
        )

        result = generator.generate_goals(request)

        # Should generate goals (repair and/or resume)
        assert result.goal_generation_performed

    def test_mixed_mode_prioritizes_repair(self):
        """Test mixed mode prioritizes repair when failure exists."""
        generator = GoalGenerator()

        request = GoalRequest.create(
            task_id="task_001",
            session_id="session_001",
            domain_hint=DomainHint.HOUDINI,
            raw_task_summary="Handle situation",
            goal_generation_mode=GoalGenerationMode.MIXED.value,
            failure_context={"error_type": "execution_failed"},
        )

        result = generator.generate_goals(request)

        # Should generate repair goals when failure exists
        assert result.has_goals
        repair_goals = [g for g in result.generated_goals if g.goal_type == GoalType.REPAIR_GOAL.value]
        assert len(repair_goals) > 0


class TestEndToEndScenarios:
    """End-to-end integration scenarios."""

    def test_full_execution_flow(self):
        """Test full execution flow with goal generation."""
        generator = GoalGenerator()

        # Step 1: Generate root goal
        root_request = GoalRequest.create(
            task_id="task_001",
            session_id="session_001",
            domain_hint=DomainHint.HOUDINI,
            raw_task_summary="Create a procedural city with buildings",
        )

        root_result = generator.generate_goals(root_request)
        assert root_result.has_goals

        # Step 2: Generate subgoals for decomposition
        root_goal = root_result.primary_goal
        subgoal_request = GoalRequest.create(
            task_id="task_001",
            session_id="session_001",
            domain_hint=DomainHint(root_goal.domain),
            raw_task_summary=root_goal.description,
            goal_generation_mode=GoalGenerationMode.SUBGOAL_GENERATION.value,
            current_goal_context={
                "goal_id": root_goal.goal_id,
                "title": root_goal.title,
            },
        )

        # Step 3: Handle a simulated failure
        failure_request = GoalRequest.create(
            task_id="task_001",
            session_id="session_001",
            domain_hint=DomainHint.HOUDINI,
            raw_task_summary="Fix and retry",
            goal_generation_mode=GoalGenerationMode.REPAIR_GOAL.value,
            failure_context={"error_type": "timeout", "message": "Step timed out"},
        )

        repair_result = generator.generate_goals(failure_request)
        assert repair_result.has_goals

        # Step 4: Generate verification goal
        verify_request = GoalRequest.create(
            task_id="task_001",
            session_id="session_001",
            domain_hint=DomainHint.HOUDINI,
            raw_task_summary="Verify result",
            goal_generation_mode=GoalGenerationMode.VERIFICATION_GOAL.value,
            verification_context={
                "target_goal_id": root_goal.goal_id,
                "evidence_gaps": [{"description": "Buildings created", "hint": "Check output"}],
            },
        )

        verify_result = generator.generate_goals(verify_request)
        assert verify_result.has_goals

    def test_persistence_roundtrip(self):
        """Test goal persistence roundtrip."""
        generator = GoalGenerator()

        request = GoalRequest.create(
            task_id="task_001",
            session_id="session_001",
            domain_hint=DomainHint.HOUDINI,
            raw_task_summary="Create terrain",
        )

        result = generator.generate_goals(request)
        original_goal = result.primary_goal

        # Simulate persistence
        goal_dict = original_goal.to_dict()
        restored_goal = GoalArtifact.from_dict(goal_dict)

        # Verify roundtrip
        assert restored_goal.goal_id == original_goal.goal_id
        assert restored_goal.title == original_goal.title
        assert restored_goal.description == original_goal.description
        assert restored_goal.domain == original_goal.domain
        assert restored_goal.goal_type == original_goal.goal_type


class TestErrorRecovery:
    """Tests for error recovery in goal generation."""

    def test_recover_from_invalid_domain(self):
        """Test recovery from invalid domain hint."""
        generator = GoalGenerator()

        # Use domain inference by providing unknown hint
        request = GoalRequest.create(
            task_id="task_001",
            session_id="session_001",
            domain_hint=DomainHint.UNKNOWN,
            raw_task_summary="Create Houdini heightfield",
        )

        result = generator.generate_goals(request)

        # Should infer domain and generate goals
        assert result.has_goals
        assert result.domain_inferred == DomainHint.HOUDINI.value

    def test_recover_from_empty_task(self):
        """Test handling of empty task description."""
        generator = GoalGenerator()

        request = GoalRequest(
            goal_request_id="test",
            session_id="session_001",
            task_id="task_001",
            domain_hint=DomainHint.HOUDINI.value,
            raw_task_summary="",  # Empty
        )

        result = generator.generate_goals(request)

        # Should fail validation
        assert result.has_errors or not result.goal_generation_performed

    def test_fallback_to_generic_domain(self):
        """Test fallback to generic domain when inference fails."""
        generator = GoalGenerator()

        request = GoalRequest.create(
            task_id="task_001",
            session_id="session_001",
            domain_hint=DomainHint.UNKNOWN,
            raw_task_summary="Do something",  # No domain keywords
        )

        result = generator.generate_goals(request)

        # Should fall back to generic
        assert result.domain_inferred == DomainHint.GENERIC.value