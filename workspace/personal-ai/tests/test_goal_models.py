"""Tests for Goal Models.

Tests serialization, deserialization, and validation for
GoalRequest, GoalArtifact, GoalGenerationResult, and related enums.
"""

import pytest

# Import directly from modules to avoid circular import
from app.agent_core.goal_models import (
    DomainHint,
    ExecutionFeasibility,
    GoalArtifact,
    GoalGenerationMode,
    GoalGenerationResult,
    GoalRequest,
    GoalSourceSignal,
    GoalType,
)


class TestGoalGenerationMode:
    """Tests for GoalGenerationMode enum."""

    def test_root_goal_mode(self):
        """Test root goal mode value."""
        assert GoalGenerationMode.ROOT_GOAL.value == "root_goal"

    def test_subgoal_generation_mode(self):
        """Test subgoal generation mode value."""
        assert GoalGenerationMode.SUBGOAL_GENERATION.value == "subgoal_generation"

    def test_repair_goal_mode(self):
        """Test repair goal mode value."""
        assert GoalGenerationMode.REPAIR_GOAL.value == "repair_goal"

    def test_verification_goal_mode(self):
        """Test verification goal mode value."""
        assert GoalGenerationMode.VERIFICATION_GOAL.value == "verification_goal"

    def test_resume_goal_mode(self):
        """Test resume goal mode value."""
        assert GoalGenerationMode.RESUME_GOAL.value == "resume_goal"

    def test_all_modes_exist(self):
        """Test all expected modes exist."""
        expected_modes = [
            "ROOT_GOAL",
            "SUBGOAL_GENERATION",
            "NEXT_GOAL",
            "REPAIR_GOAL",
            "VERIFICATION_GOAL",
            "RESUME_GOAL",
            "MIXED",
        ]
        for mode in expected_modes:
            assert hasattr(GoalGenerationMode, mode)


class TestGoalType:
    """Tests for GoalType enum."""

    def test_root_goal_type(self):
        """Test root goal type value."""
        assert GoalType.ROOT_GOAL.value == "root_goal"

    def test_subgoal_type(self):
        """Test subgoal type value."""
        assert GoalType.SUBGOAL.value == "subgoal"

    def test_repair_goal_type(self):
        """Test repair goal type value."""
        assert GoalType.REPAIR_GOAL.value == "repair_goal"

    def test_verification_goal_type(self):
        """Test verification goal type value."""
        assert GoalType.VERIFICATION_GOAL.value == "verification_goal"

    def test_resume_goal_type(self):
        """Test resume goal type value."""
        assert GoalType.RESUME_GOAL.value == "resume_goal"

    def test_all_types_exist(self):
        """Test all expected types exist."""
        expected_types = [
            "ROOT_GOAL",
            "SUBGOAL",
            "NEXT_ACTION_GOAL",
            "REPAIR_GOAL",
            "VERIFICATION_GOAL",
            "RESEARCH_GOAL",
            "INSPECT_GOAL",
            "RESUME_GOAL",
        ]
        for goal_type in expected_types:
            assert hasattr(GoalType, goal_type)


class TestDomainHint:
    """Tests for DomainHint enum."""

    def test_houdini_domain(self):
        """Test Houdini domain value."""
        assert DomainHint.HOUDINI.value == "houdini"

    def test_touchdesigner_domain(self):
        """Test TouchDesigner domain value."""
        assert DomainHint.TOUCHDESIGNER.value == "touchdesigner"

    def test_mixed_domain(self):
        """Test mixed domain value."""
        assert DomainHint.MIXED.value == "mixed"

    def test_generic_domain(self):
        """Test generic domain value."""
        assert DomainHint.GENERIC.value == "generic"

    def test_unknown_domain(self):
        """Test unknown domain value."""
        assert DomainHint.UNKNOWN.value == "unknown"


class TestGoalSourceSignal:
    """Tests for GoalSourceSignal enum."""

    def test_task_signal(self):
        """Test task signal value."""
        assert GoalSourceSignal.TASK.value == "task"

    def test_memory_signal(self):
        """Test memory signal value."""
        assert GoalSourceSignal.MEMORY.value == "memory"

    def test_failure_context_signal(self):
        """Test failure context signal value."""
        assert GoalSourceSignal.FAILURE_CONTEXT.value == "failure_context"

    def test_all_signals_exist(self):
        """Test all expected signals exist."""
        expected_signals = [
            "TASK",
            "OBSERVATION",
            "MEMORY",
            "TRANSCRIPT_KNOWLEDGE",
            "RECIPE_KNOWLEDGE",
            "FAILURE_CONTEXT",
            "REPAIR_CONTEXT",
            "VERIFICATION_CONTEXT",
        ]
        for signal in expected_signals:
            assert hasattr(GoalSourceSignal, signal)


class TestExecutionFeasibility:
    """Tests for ExecutionFeasibility enum."""

    def test_high_feasibility(self):
        """Test high feasibility value."""
        assert ExecutionFeasibility.HIGH.value == "high"

    def test_medium_feasibility(self):
        """Test medium feasibility value."""
        assert ExecutionFeasibility.MEDIUM.value == "medium"

    def test_low_feasibility(self):
        """Test low feasibility value."""
        assert ExecutionFeasibility.LOW.value == "low"

    def test_unknown_feasibility(self):
        """Test unknown feasibility value."""
        assert ExecutionFeasibility.UNKNOWN.value == "unknown"


class TestGoalRequest:
    """Tests for GoalRequest dataclass."""

    def test_create_goal_request(self):
        """Test creating a GoalRequest."""
        request = GoalRequest.create(
            task_id="task_001",
            session_id="session_001",
            domain_hint=DomainHint.HOUDINI,
            raw_task_summary="Create a procedural terrain",
        )

        assert request.task_id == "task_001"
        assert request.session_id == "session_001"
        assert request.domain_hint == "houdini"
        assert request.raw_task_summary == "Create a procedural terrain"
        assert request.goal_request_id.startswith("greq_")
        assert request.created_at != ""

    def test_goal_request_to_dict(self):
        """Test GoalRequest serialization to dict."""
        request = GoalRequest.create(
            task_id="task_001",
            session_id="session_001",
            domain_hint=DomainHint.TOUCHDESIGNER,
            raw_task_summary="Build an interactive UI",
        )

        data = request.to_dict()

        assert data["task_id"] == "task_001"
        assert data["session_id"] == "session_001"
        assert data["domain_hint"] == "touchdesigner"
        assert data["raw_task_summary"] == "Build an interactive UI"
        assert "goal_request_id" in data
        assert "created_at" in data

    def test_goal_request_from_dict(self):
        """Test GoalRequest deserialization from dict."""
        data = {
            "goal_request_id": "greq_123",
            "session_id": "session_001",
            "task_id": "task_001",
            "domain_hint": "houdini",
            "raw_task_summary": "Test task",
            "normalized_task_summary": "Normalized test task",
            "dry_run": True,
            "bounded_mode": True,
            "safety_mode": True,
        }

        request = GoalRequest.from_dict(data)

        assert request.goal_request_id == "greq_123"
        assert request.task_id == "task_001"
        assert request.domain_hint == "houdini"
        assert request.raw_task_summary == "Test task"
        assert request.normalized_task_summary == "Normalized test task"

    def test_goal_request_with_memory_summary(self):
        """Test GoalRequest with memory summary."""
        request = GoalRequest.create(
            task_id="task_001",
            session_id="session_001",
            domain_hint=DomainHint.HOUDINI,
            raw_task_summary="Test",
            memory_summary={"success_patterns": ["pattern1"]},
        )

        assert request.memory_summary == {"success_patterns": ["pattern1"]}

    def test_goal_request_with_failure_context(self):
        """Test GoalRequest with failure context."""
        request = GoalRequest.create(
            task_id="task_001",
            session_id="session_001",
            domain_hint=DomainHint.HOUDINI,
            raw_task_summary="Test",
            failure_context={"error_type": "timeout"},
        )

        assert request.failure_context == {"error_type": "timeout"}


class TestGoalArtifact:
    """Tests for GoalArtifact dataclass."""

    def test_create_goal_artifact(self):
        """Test creating a GoalArtifact."""
        goal = GoalArtifact.create(
            goal_type=GoalType.ROOT_GOAL,
            title="Test Goal",
            description="Test goal description",
            domain="houdini",
            task_id="task_001",
            session_id="session_001",
        )

        assert goal.title == "Test Goal"
        assert goal.description == "Test goal description"
        assert goal.domain == "houdini"
        assert goal.goal_type == "root_goal"
        assert goal.goal_id.startswith("goal_")
        assert goal.schema_version == "1.0.0"

    def test_goal_artifact_to_dict(self):
        """Test GoalArtifact serialization to dict."""
        goal = GoalArtifact.create(
            goal_type=GoalType.SUBGOAL,
            title="Subgoal",
            description="A subgoal",
            domain="touchdesigner",
        )

        data = goal.to_dict()

        assert data["title"] == "Subgoal"
        assert data["description"] == "A subgoal"
        assert data["domain"] == "touchdesigner"
        assert data["goal_type"] == "subgoal"

    def test_goal_artifact_from_dict(self):
        """Test GoalArtifact deserialization from dict."""
        data = {
            "goal_id": "goal_123",
            "parent_goal_id": "goal_parent",
            "task_id": "task_001",
            "session_id": "session_001",
            "domain": "houdini",
            "goal_type": "repair_goal",
            "title": "Repair Goal",
            "description": "Fix the issue",
            "confidence": 0.85,
            "source_signals": ["task", "failure_context"],
        }

        goal = GoalArtifact.from_dict(data)

        assert goal.goal_id == "goal_123"
        assert goal.parent_goal_id == "goal_parent"
        assert goal.goal_type == "repair_goal"
        assert goal.title == "Repair Goal"
        assert goal.confidence == 0.85
        assert "task" in goal.source_signals
        assert "failure_context" in goal.source_signals

    def test_goal_artifact_is_blocked(self):
        """Test goal is_blocked property."""
        goal = GoalArtifact.create(
            goal_type=GoalType.ROOT_GOAL,
            title="Test",
            description="Test",
        )

        assert not goal.is_blocked

        goal.block("Safety violation")
        assert goal.is_blocked
        assert goal.blocked_reason == "Safety violation"

    def test_goal_artifact_is_subgoal(self):
        """Test goal is_subgoal property."""
        goal = GoalArtifact.create(
            goal_type=GoalType.SUBGOAL,
            title="Subgoal",
            description="Test",
        )

        assert goal.is_subgoal

    def test_goal_artifact_is_repair(self):
        """Test goal is_repair property."""
        goal = GoalArtifact.create(
            goal_type=GoalType.REPAIR_GOAL,
            title="Repair",
            description="Test",
        )

        assert goal.is_repair

    def test_goal_artifact_is_verification(self):
        """Test goal is_verification property."""
        goal = GoalArtifact.create(
            goal_type=GoalType.VERIFICATION_GOAL,
            title="Verify",
            description="Test",
        )

        assert goal.is_verification

    def test_goal_artifact_is_resume(self):
        """Test goal is_resume property."""
        goal = GoalArtifact.create(
            goal_type=GoalType.RESUME_GOAL,
            title="Resume",
            description="Test",
        )

        assert goal.is_resume

    def test_goal_artifact_add_source_signal(self):
        """Test adding source signals."""
        goal = GoalArtifact.create(
            goal_type=GoalType.ROOT_GOAL,
            title="Test",
            description="Test",
        )

        goal.add_source_signal(GoalSourceSignal.TASK)
        goal.add_source_signal(GoalSourceSignal.MEMORY)

        assert GoalSourceSignal.TASK.value in goal.source_signals
        assert GoalSourceSignal.MEMORY.value in goal.source_signals

    def test_goal_artifact_add_ambiguity_flag(self):
        """Test adding ambiguity flags."""
        goal = GoalArtifact.create(
            goal_type=GoalType.ROOT_GOAL,
            title="Test",
            description="Test",
        )

        goal.add_ambiguity_flag("vague_term")
        goal.add_ambiguity_flag("multiple_domains")

        assert "vague_term" in goal.ambiguity_flags
        assert "multiple_domains" in goal.ambiguity_flags

    def test_goal_artifact_add_precondition(self):
        """Test adding preconditions."""
        goal = GoalArtifact.create(
            goal_type=GoalType.ROOT_GOAL,
            title="Test",
            description="Test",
        )

        goal.add_precondition("Environment accessible")
        goal.add_precondition("Bridge connected")

        assert "Environment accessible" in goal.preconditions
        assert "Bridge connected" in goal.preconditions

    def test_goal_artifact_has_high_feasibility(self):
        """Test has_high_feasibility property."""
        goal = GoalArtifact.create(
            goal_type=GoalType.ROOT_GOAL,
            title="Test",
            description="Test",
            execution_feasibility="high",
        )

        assert goal.has_high_feasibility

        goal.execution_feasibility = "medium"
        assert not goal.has_high_feasibility


class TestGoalGenerationResult:
    """Tests for GoalGenerationResult dataclass."""

    def test_create_result_with_goals(self):
        """Test creating a result with goals."""
        goal = GoalArtifact.create(
            goal_type=GoalType.ROOT_GOAL,
            title="Test",
            description="Test",
        )

        result = GoalGenerationResult(
            goal_generation_performed=True,
            generated_goal_count=1,
            selected_goal_ids=[goal.goal_id],
            selected_goal_summary="Test goal",
            goal_generation_mode="root_goal",
            domain_inferred="houdini",
            domain_confidence=0.9,
            memory_influenced=False,
            transcript_knowledge_used=False,
            recipe_knowledge_used=False,
            ambiguity_summary="",
            blocked_goal_count=0,
            filtered_goal_count=0,
            generated_goals=[goal],
            final_status="success",
        )

        assert result.has_goals
        assert result.has_selected_goals
        assert not result.has_errors
        assert result.primary_goal is not None

    def test_result_empty_result(self):
        """Test empty_result factory method."""
        result = GoalGenerationResult.empty_result(
            mode="root_goal",
            reason="No context",
        )

        assert not result.goal_generation_performed
        assert result.generated_goal_count == 0
        assert not result.has_goals
        assert result.final_status == "skipped"

    def test_result_error_result(self):
        """Test error_result factory method."""
        errors = [{"error_type": "test_error", "message": "Test error"}]

        result = GoalGenerationResult.error_result(
            mode="root_goal",
            errors=errors,
        )

        assert result.goal_generation_performed
        assert result.has_errors
        assert result.final_status == "error"
        assert len(result.errors) == 1

    def test_result_primary_goal(self):
        """Test primary_goal property."""
        goal1 = GoalArtifact.create(
            goal_type=GoalType.ROOT_GOAL,
            title="Goal 1",
            description="First goal",
        )
        goal2 = GoalArtifact.create(
            goal_type=GoalType.ROOT_GOAL,
            title="Goal 2",
            description="Second goal",
        )

        result = GoalGenerationResult(
            goal_generation_performed=True,
            generated_goal_count=2,
            selected_goal_ids=[goal2.goal_id],
            selected_goal_summary="",
            goal_generation_mode="root_goal",
            domain_inferred="houdini",
            domain_confidence=0.9,
            memory_influenced=False,
            transcript_knowledge_used=False,
            recipe_knowledge_used=False,
            ambiguity_summary="",
            blocked_goal_count=0,
            filtered_goal_count=0,
            generated_goals=[goal1, goal2],
            final_status="success",
        )

        # Primary should be the selected one
        primary = result.primary_goal
        assert primary is not None
        assert primary.goal_id == goal2.goal_id

    def test_result_all_goals_blocked(self):
        """Test all_goals_blocked property."""
        goal1 = GoalArtifact.create(
            goal_type=GoalType.ROOT_GOAL,
            title="Goal 1",
            description="First",
        )
        goal1.block("Safety")

        goal2 = GoalArtifact.create(
            goal_type=GoalType.ROOT_GOAL,
            title="Goal 2",
            description="Second",
        )
        goal2.block("Safety")

        result = GoalGenerationResult(
            goal_generation_performed=True,
            generated_goal_count=2,
            selected_goal_ids=[],
            selected_goal_summary="",
            goal_generation_mode="root_goal",
            domain_inferred="houdini",
            domain_confidence=0.9,
            memory_influenced=False,
            transcript_knowledge_used=False,
            recipe_knowledge_used=False,
            ambiguity_summary="",
            blocked_goal_count=2,
            filtered_goal_count=0,
            generated_goals=[goal1, goal2],
            final_status="no_goals",
        )

        assert result.all_goals_blocked

    def test_result_to_dict(self):
        """Test GoalGenerationResult serialization to dict."""
        goal = GoalArtifact.create(
            goal_type=GoalType.ROOT_GOAL,
            title="Test",
            description="Test",
        )

        result = GoalGenerationResult(
            goal_generation_performed=True,
            generated_goal_count=1,
            selected_goal_ids=[goal.goal_id],
            selected_goal_summary="Test goal",
            goal_generation_mode="root_goal",
            domain_inferred="houdini",
            domain_confidence=0.9,
            memory_influenced=True,
            transcript_knowledge_used=False,
            recipe_knowledge_used=True,
            ambiguity_summary="",
            blocked_goal_count=0,
            filtered_goal_count=0,
            generated_goals=[goal],
            final_status="success",
        )

        data = result.to_dict()

        assert data["goal_generation_performed"] is True
        assert data["generated_goal_count"] == 1
        assert data["domain_inferred"] == "houdini"
        assert data["memory_influenced"] is True
        assert data["recipe_knowledge_used"] is True
        assert len(data["generated_goals"]) == 1

    def test_result_add_error(self):
        """Test add_error method."""
        result = GoalGenerationResult(
            goal_generation_performed=True,
            generated_goal_count=0,
            selected_goal_ids=[],
            selected_goal_summary="",
            goal_generation_mode="root_goal",
            domain_inferred="unknown",
            domain_confidence=0.0,
            memory_influenced=False,
            transcript_knowledge_used=False,
            recipe_knowledge_used=False,
            ambiguity_summary="",
            blocked_goal_count=0,
            filtered_goal_count=0,
            generated_goals=[],
            final_status="error",
        )

        result.add_error("test_error", "Test error message", {"detail": "value"})

        assert result.has_errors
        assert len(result.errors) == 1
        assert result.errors[0]["error_type"] == "test_error"


class TestRoundTripSerialization:
    """Tests for round-trip serialization."""

    def test_goal_request_round_trip(self):
        """Test GoalRequest round-trip through dict."""
        original = GoalRequest.create(
            task_id="task_001",
            session_id="session_001",
            domain_hint=DomainHint.HOUDINI,
            raw_task_summary="Create terrain",
            memory_summary={"patterns": ["p1"]},
            failure_context={"error": "timeout"},
        )

        data = original.to_dict()
        restored = GoalRequest.from_dict(data)

        assert restored.task_id == original.task_id
        assert restored.session_id == original.session_id
        assert restored.domain_hint == original.domain_hint
        assert restored.raw_task_summary == original.raw_task_summary
        assert restored.memory_summary == original.memory_summary
        assert restored.failure_context == original.failure_context

    def test_goal_artifact_round_trip(self):
        """Test GoalArtifact round-trip through dict."""
        original = GoalArtifact.create(
            goal_type=GoalType.REPAIR_GOAL,
            title="Repair Goal",
            description="Fix the issue",
            domain="touchdesigner",
            task_id="task_001",
            session_id="session_001",
            confidence=0.85,
        )
        original.add_source_signal(GoalSourceSignal.FAILURE_CONTEXT)
        original.add_ambiguity_flag("uncertain")
        original.repair_hint = "Check connection"

        data = original.to_dict()
        restored = GoalArtifact.from_dict(data)

        assert restored.goal_type == original.goal_type
        assert restored.title == original.title
        assert restored.description == original.description
        assert restored.domain == original.domain
        assert restored.confidence == original.confidence
        assert restored.source_signals == original.source_signals
        assert restored.ambiguity_flags == original.ambiguity_flags
        assert restored.repair_hint == original.repair_hint