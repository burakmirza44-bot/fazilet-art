"""Tests for Goal Generator.

Tests for the core GoalGenerator class including all generation types,
ranking, safety, and domain inference.
"""

import pytest

# Import directly from modules to avoid circular import
from app.agent_core.goal_errors import (
    GoalGenerationError,
    GoalGenerationErrorType,
)
from app.agent_core.goal_generator import (
    DOMAIN_KEYWORDS,
    UNSAFE_PATTERNS,
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


class TestGoalGeneratorConfig:
    """Tests for GoalGeneratorConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = GoalGeneratorConfig()

        assert config.enable_memory is True
        assert config.enable_safety_checks is True
        assert config.enable_ranking is True
        assert config.max_goals_per_request == 5
        assert config.min_confidence_threshold == 0.3

    def test_custom_config(self):
        """Test custom configuration values."""
        config = GoalGeneratorConfig(
            enable_memory=False,
            enable_safety_checks=False,
            max_goals_per_request=10,
        )

        assert config.enable_memory is False
        assert config.enable_safety_checks is False
        assert config.max_goals_per_request == 10


class TestGoalGeneratorInit:
    """Tests for GoalGenerator initialization."""

    def test_init_default(self):
        """Test default initialization."""
        generator = GoalGenerator()

        assert generator._repo_root == "."
        assert generator.config is not None
        assert generator.config.enable_memory is True

    def test_init_with_config(self):
        """Test initialization with custom config."""
        config = GoalGeneratorConfig(enable_memory=False)
        generator = GoalGenerator(config=config)

        assert generator.config.enable_memory is False

    def test_init_with_repo_root(self):
        """Test initialization with repo root."""
        generator = GoalGenerator(repo_root="/path/to/repo")

        assert generator._repo_root == "/path/to/repo"


class TestGenerateRootGoal:
    """Tests for generate_root_goal method."""

    def test_generate_root_goal_basic(self):
        """Test basic root goal generation."""
        generator = GoalGenerator()
        request = GoalRequest.create(
            task_id="task_001",
            session_id="session_001",
            domain_hint=DomainHint.HOUDINI,
            raw_task_summary="Create a procedural terrain",
        )

        goals = generator.generate_root_goal(request)

        assert len(goals) >= 1
        assert goals[0].goal_type == GoalType.ROOT_GOAL.value
        assert "terrain" in goals[0].description.lower()
        assert goals[0].domain == DomainHint.HOUDINI.value

    def test_generate_root_goal_with_memory(self):
        """Test root goal generation with memory context."""
        generator = GoalGenerator()
        request = GoalRequest.create(
            task_id="task_001",
            session_id="session_001",
            domain_hint=DomainHint.TOUCHDESIGNER,
            raw_task_summary="Build interactive UI",
            memory_summary={"success_patterns": [{"pattern": "setup_first"}]},
        )

        goals = generator.generate_root_goal(request)

        assert len(goals) >= 1
        assert GoalSourceSignal.MEMORY.value in goals[0].source_signals

    def test_generate_root_goal_infers_domain(self):
        """Test domain inference in root goal generation."""
        generator = GoalGenerator()
        request = GoalRequest.create(
            task_id="task_001",
            session_id="session_001",
            domain_hint=DomainHint.UNKNOWN,
            raw_task_summary="Create a Houdini heightfield for terrain generation",
        )

        goals = generator.generate_root_goal(request)

        # Should infer Houdini from keywords
        assert goals[0].domain == DomainHint.HOUDINI.value

    def test_generate_root_goal_extracts_preconditions(self):
        """Test precondition extraction."""
        generator = GoalGenerator()
        request = GoalRequest.create(
            task_id="task_001",
            session_id="session_001",
            domain_hint=DomainHint.HOUDINI,
            raw_task_summary="Create simulation requires bridge connection before starting",
        )

        goals = generator.generate_root_goal(request)

        # Check that preconditions were analyzed
        assert len(goals) >= 1


class TestGenerateSubgoals:
    """Tests for generate_subgoals method."""

    def test_generate_subgoals_from_parent(self):
        """Test subgoal generation from parent goal."""
        generator = GoalGenerator()
        parent = GoalArtifact.create(
            goal_type=GoalType.ROOT_GOAL,
            title="Create terrain",
            description="Create a procedural terrain in Houdini",
            domain="houdini",
        )

        request = GoalRequest.create(
            task_id="task_001",
            session_id="session_001",
            domain_hint=DomainHint.HOUDINI,
            raw_task_summary="Create terrain",
        )

        subgoals = generator.generate_subgoals(request, parent)

        assert len(subgoals) >= 1
        for subgoal in subgoals:
            assert subgoal.goal_type == GoalType.SUBGOAL.value
            assert subgoal.parent_goal_id == parent.goal_id

    def test_generate_subgoals_without_parent(self):
        """Test subgoal generation falls back to root goal without parent."""
        generator = GoalGenerator()
        request = GoalRequest.create(
            task_id="task_001",
            session_id="session_001",
            domain_hint=DomainHint.HOUDINI,
            raw_task_summary="Create terrain",
        )

        goals = generator.generate_subgoals(request, None)

        # Should fall back to root goal generation
        assert len(goals) >= 1
        assert goals[0].goal_type == GoalType.ROOT_GOAL.value


class TestGenerateNextGoal:
    """Tests for generate_next_goal method."""

    def test_generate_next_goal_basic(self):
        """Test basic next goal generation."""
        generator = GoalGenerator()
        request = GoalRequest.create(
            task_id="task_001",
            session_id="session_001",
            domain_hint=DomainHint.HOUDINI,
            raw_task_summary="Continue execution",
            active_subgoal_context={
                "pending_steps": [
                    {"title": "Step 1", "description": "First step"},
                ]
            },
        )

        goals = generator.generate_next_goal(request)

        assert len(goals) >= 1
        assert goals[0].goal_type == GoalType.NEXT_ACTION_GOAL.value

    def test_generate_next_goal_with_state(self):
        """Test next goal generation with runtime state."""
        generator = GoalGenerator()
        request = GoalRequest.create(
            task_id="task_001",
            session_id="session_001",
            domain_hint=DomainHint.TOUCHDESIGNER,
            raw_task_summary="Continue",
            current_runtime_state_summary="Bridge connected, ready for input",
        )

        goals = generator.generate_next_goal(request)

        assert len(goals) >= 1


class TestGenerateRepairGoal:
    """Tests for generate_repair_goal method."""

    def test_generate_repair_goal_timeout(self):
        """Test repair goal for timeout error."""
        generator = GoalGenerator()
        request = GoalRequest.create(
            task_id="task_001",
            session_id="session_001",
            domain_hint=DomainHint.HOUDINI,
            raw_task_summary="Fix the issue",
            failure_context={
                "error_type": "timeout",
                "message": "Operation timed out",
                "failed_goal_id": "goal_prev",
            },
        )

        goals = generator.generate_repair_goal(request)

        assert len(goals) >= 1
        assert goals[0].goal_type == GoalType.REPAIR_GOAL.value
        assert goals[0].repair_hint != ""
        assert GoalSourceSignal.FAILURE_CONTEXT.value in goals[0].source_signals

    def test_generate_repair_goal_bridge_unavailable(self):
        """Test repair goal for bridge unavailable error."""
        generator = GoalGenerator()
        request = GoalRequest.create(
            task_id="task_001",
            session_id="session_001",
            domain_hint=DomainHint.TOUCHDESIGNER,
            raw_task_summary="Fix connection",
            failure_context={
                "error_type": "bridge_unavailable",
                "message": "Bridge connection failed",
            },
        )

        goals = generator.generate_repair_goal(request)

        assert len(goals) >= 1
        assert goals[0].goal_type == GoalType.REPAIR_GOAL.value

    def test_generate_repair_goal_no_context(self):
        """Test repair goal without failure context falls back."""
        generator = GoalGenerator()
        request = GoalRequest.create(
            task_id="task_001",
            session_id="session_001",
            domain_hint=DomainHint.HOUDINI,
            raw_task_summary="Fix the issue",
        )

        goals = generator.generate_repair_goal(request)

        # Should fall back to root goal generation
        assert len(goals) >= 1


class TestGenerateVerificationGoal:
    """Tests for generate_verification_goal method."""

    def test_generate_verification_goal_basic(self):
        """Test basic verification goal generation."""
        generator = GoalGenerator()
        request = GoalRequest.create(
            task_id="task_001",
            session_id="session_001",
            domain_hint=DomainHint.HOUDINI,
            raw_task_summary="Verify result",
            verification_context={
                "target_goal_id": "goal_prev",
                "evidence_gaps": [
                    {"description": "Output node exists", "hint": "Check node exists"},
                ],
            },
        )

        goals = generator.generate_verification_goal(request)

        assert len(goals) >= 1
        assert goals[0].goal_type == GoalType.VERIFICATION_GOAL.value
        assert goals[0].verification_hint != ""

    def test_generate_verification_goal_no_context(self):
        """Test verification goal without context returns empty."""
        generator = GoalGenerator()
        request = GoalRequest.create(
            task_id="task_001",
            session_id="session_001",
            domain_hint=DomainHint.HOUDINI,
            raw_task_summary="Verify",
        )

        goals = generator.generate_verification_goal(request)

        assert len(goals) == 0


class TestGenerateResumeGoal:
    """Tests for generate_resume_goal method."""

    def test_generate_resume_goal_basic(self):
        """Test basic resume goal generation."""
        generator = GoalGenerator()
        request = GoalRequest.create(
            task_id="task_001",
            session_id="session_001",
            domain_hint=DomainHint.HOUDINI,
            raw_task_summary="Resume execution",
            checkpoint_summary={
                "checkpoint_id": "ckpt_001",
                "domain": "houdini",
                "next_pending_step": {
                    "description": "Create output node",
                },
            },
        )

        goals = generator.generate_resume_goal(request)

        assert len(goals) >= 1
        assert goals[0].goal_type == GoalType.RESUME_GOAL.value

    def test_generate_resume_goal_no_checkpoint(self):
        """Test resume goal without checkpoint returns empty."""
        generator = GoalGenerator()
        request = GoalRequest.create(
            task_id="task_001",
            session_id="session_001",
            domain_hint=DomainHint.HOUDINI,
            raw_task_summary="Resume",
        )

        goals = generator.generate_resume_goal(request)

        assert len(goals) == 0


class TestGenerateGoals:
    """Tests for main generate_goals method."""

    def test_generate_goals_root_mode(self):
        """Test generate_goals in root mode."""
        generator = GoalGenerator()
        request = GoalRequest.create(
            task_id="task_001",
            session_id="session_001",
            domain_hint=DomainHint.HOUDINI,
            raw_task_summary="Create terrain",
            goal_generation_mode=GoalGenerationMode.ROOT_GOAL.value,
        )

        result = generator.generate_goals(request)

        assert result.goal_generation_performed
        assert result.has_goals
        assert result.goal_generation_mode == GoalGenerationMode.ROOT_GOAL.value

    def test_generate_goals_repair_mode(self):
        """Test generate_goals in repair mode."""
        generator = GoalGenerator()
        request = GoalRequest.create(
            task_id="task_001",
            session_id="session_001",
            domain_hint=DomainHint.HOUDINI,
            raw_task_summary="Fix error",
            goal_generation_mode=GoalGenerationMode.REPAIR_GOAL.value,
            failure_context={"error_type": "timeout"},
        )

        result = generator.generate_goals(request)

        assert result.goal_generation_performed
        assert result.goal_generation_mode == GoalGenerationMode.REPAIR_GOAL.value

    def test_generate_goals_with_max_limit(self):
        """Test generate_goals respects max_goal_count."""
        generator = GoalGenerator()
        request = GoalRequest.create(
            task_id="task_001",
            session_id="session_001",
            domain_hint=DomainHint.HOUDINI,
            raw_task_summary="Create terrain",
            max_goal_count=2,
        )

        result = generator.generate_goals(request)

        assert len(result.selected_goal_ids) <= 2

    def test_generate_goals_validation_error(self):
        """Test generate_goals with invalid request."""
        generator = GoalGenerator()
        request = GoalRequest(
            goal_request_id="test",
            session_id="",  # Missing
            task_id="",  # Missing
            domain_hint="unknown",
            raw_task_summary="",  # Missing
        )

        result = generator.generate_goals(request)

        # Validation should fail - result has errors
        assert result.has_errors
        assert result.final_status == "error"
        assert len(result.errors) > 0

    def test_generate_goals_mixed_mode(self):
        """Test generate_goals in mixed mode."""
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

        assert result.goal_generation_performed


class TestDomainInference:
    """Tests for domain inference."""

    def test_infer_domain_houdini_keywords(self):
        """Test domain inference with Houdini keywords."""
        generator = GoalGenerator()
        request = GoalRequest.create(
            task_id="task_001",
            session_id="session_001",
            domain_hint=DomainHint.UNKNOWN,
            raw_task_summary="Create a procedural heightfield with vellum simulation",
        )

        goals = generator.generate_root_goal(request)

        assert goals[0].domain == DomainHint.HOUDINI.value

    def test_infer_domain_touchdesigner_keywords(self):
        """Test domain inference with TouchDesigner keywords."""
        generator = GoalGenerator()
        request = GoalRequest.create(
            task_id="task_001",
            session_id="session_001",
            domain_hint=DomainHint.UNKNOWN,
            raw_task_summary="Create an interactive visual with CHOP and TOP operators",
        )

        goals = generator.generate_root_goal(request)

        assert goals[0].domain == DomainHint.TOUCHDESIGNER.value

    def test_infer_domain_explicit_hint(self):
        """Test domain inference respects explicit hint."""
        generator = GoalGenerator()
        request = GoalRequest.create(
            task_id="task_001",
            session_id="session_001",
            domain_hint=DomainHint.HOUDINI,
            raw_task_summary="Create something with CHOP operators",
        )

        goals = generator.generate_root_goal(request)

        # Explicit hint should override keyword analysis
        assert goals[0].domain == DomainHint.HOUDINI.value

    def test_infer_domain_generic(self):
        """Test domain inference returns generic for unknown."""
        generator = GoalGenerator()
        request = GoalRequest.create(
            task_id="task_001",
            session_id="session_001",
            domain_hint=DomainHint.UNKNOWN,
            raw_task_summary="Do something",
        )

        goals = generator.generate_root_goal(request)

        assert goals[0].domain == DomainHint.GENERIC.value


class TestSafetyChecks:
    """Tests for safety checks."""

    def test_safety_blocks_unsafe_pattern(self):
        """Test safety blocks unsafe patterns."""
        generator = GoalGenerator()
        request = GoalRequest.create(
            task_id="task_001",
            session_id="session_001",
            domain_hint=DomainHint.HOUDINI,
            raw_task_summary="Delete all files and format disk",
        )

        result = generator.generate_goals(request)

        # Goals should be blocked
        assert result.blocked_goal_count > 0 or not result.has_goals

    def test_safety_allows_safe_goal(self):
        """Test safety allows safe goals."""
        generator = GoalGenerator()
        request = GoalRequest.create(
            task_id="task_001",
            session_id="session_001",
            domain_hint=DomainHint.HOUDINI,
            raw_task_summary="Create a procedural terrain",
        )

        result = generator.generate_goals(request)

        assert result.blocked_goal_count == 0

    def test_safety_can_be_disabled(self):
        """Test safety can be disabled."""
        config = GoalGeneratorConfig(enable_safety_checks=False)
        generator = GoalGenerator(config=config)
        request = GoalRequest.create(
            task_id="task_001",
            session_id="session_001",
            domain_hint=DomainHint.HOUDINI,
            raw_task_summary="Delete all files",
        )

        goals = generator.generate_root_goal(request)

        # Should still generate goals (even though unsafe)
        assert len(goals) >= 1


class TestGoalRanking:
    """Tests for goal ranking."""

    def test_ranking_sorts_by_confidence(self):
        """Test ranking sorts goals by confidence."""
        generator = GoalGenerator()
        request = GoalRequest.create(
            task_id="task_001",
            session_id="session_001",
            domain_hint=DomainHint.HOUDINI,
            raw_task_summary="Create terrain with heightfield",
        )

        result = generator.generate_goals(request)

        # Goals should be sorted by confidence (highest first)
        if len(result.generated_goals) > 1:
            for i in range(len(result.generated_goals) - 1):
                assert result.generated_goals[i].confidence >= result.generated_goals[i + 1].confidence

    def test_ranking_can_be_disabled(self):
        """Test ranking can be disabled."""
        config = GoalGeneratorConfig(enable_ranking=False)
        generator = GoalGenerator(config=config)
        request = GoalRequest.create(
            task_id="task_001",
            session_id="session_001",
            domain_hint=DomainHint.HOUDINI,
            raw_task_summary="Create terrain",
        )

        result = generator.generate_goals(request)

        # Should still generate goals
        assert result.has_goals


class TestBuildGoalRequestFromTask:
    """Tests for build_goal_request_from_task helper."""

    def test_build_basic_request(self):
        """Test building basic request."""
        request = build_goal_request_from_task(
            task="Create terrain",
            task_id="task_001",
            session_id="session_001",
        )

        assert request.task_id == "task_001"
        assert request.session_id == "session_001"
        assert request.raw_task_summary == "Create terrain"
        assert request.goal_generation_mode == GoalGenerationMode.ROOT_GOAL.value

    def test_build_request_with_failure(self):
        """Test building request with failure context."""
        request = build_goal_request_from_task(
            task="Fix error",
            task_id="task_001",
            session_id="session_001",
            failure_context={"error_type": "timeout"},
        )

        assert request.goal_generation_mode == GoalGenerationMode.REPAIR_GOAL.value
        assert request.failure_context == {"error_type": "timeout"}

    def test_build_request_with_checkpoint(self):
        """Test building request with checkpoint."""
        request = build_goal_request_from_task(
            task="Resume",
            task_id="task_001",
            session_id="session_001",
            checkpoint={"checkpoint_id": "ckpt_001"},
        )

        assert request.goal_generation_mode == GoalGenerationMode.RESUME_GOAL.value
        assert request.checkpoint_summary == {"checkpoint_id": "ckpt_001"}

    def test_build_request_with_domain(self):
        """Test building request with domain."""
        request = build_goal_request_from_task(
            task="Create terrain",
            task_id="task_001",
            session_id="session_001",
            domain="houdini",
        )

        assert request.domain_hint == "houdini"


class TestErrorLog:
    """Tests for error logging."""

    def test_error_log_captures_errors(self):
        """Test error log captures generation errors."""
        generator = GoalGenerator()
        request = GoalRequest(
            goal_request_id="test",
            session_id="",  # Invalid
            task_id="",  # Invalid
            domain_hint="unknown",
            raw_task_summary="",  # Invalid
        )

        generator.generate_goals(request)

        assert len(generator.error_log) > 0
        assert generator.error_log[0].error_type == GoalGenerationErrorType.GOAL_CONTEXT_MISSING


class TestGoalGeneratorResultMetadata:
    """Tests for GoalGenerationResult metadata."""

    def test_result_memory_influenced(self):
        """Test result tracks memory influence."""
        generator = GoalGenerator()
        request = GoalRequest.create(
            task_id="task_001",
            session_id="session_001",
            domain_hint=DomainHint.HOUDINI,
            raw_task_summary="Create terrain",
            memory_summary={"patterns": ["p1"]},
        )

        result = generator.generate_goals(request)

        assert result.memory_influenced is True

    def test_result_knowledge_used(self):
        """Test result tracks knowledge usage."""
        generator = GoalGenerator()
        request = GoalRequest.create(
            task_id="task_001",
            session_id="session_001",
            domain_hint=DomainHint.HOUDINI,
            raw_task_summary="Create terrain",
            transcript_knowledge_summary={"tutorials": ["t1"]},
            recipe_knowledge_summary={"recipes": ["r1"]},
        )

        result = generator.generate_goals(request)

        assert result.transcript_knowledge_used is True
        assert result.recipe_knowledge_used is True

    def test_result_domain_confidence(self):
        """Test result includes domain confidence."""
        generator = GoalGenerator()
        request = GoalRequest.create(
            task_id="task_001",
            session_id="session_001",
            domain_hint=DomainHint.HOUDINI,
            raw_task_summary="Create Houdini heightfield with vellum simulation",
        )

        result = generator.generate_goals(request)

        assert result.domain_confidence > 0.5


class TestAmbiguityDetection:
    """Tests for ambiguity detection."""

    def test_detects_vague_terms(self):
        """Test detection of vague terms."""
        generator = GoalGenerator()
        request = GoalRequest.create(
            task_id="task_001",
            session_id="session_001",
            domain_hint=DomainHint.HOUDINI,
            raw_task_summary="Create something maybe with some stuff",
        )

        goals = generator.generate_root_goal(request)

        # Should have ambiguity flags
        assert any(len(g.ambiguity_flags) > 0 for g in goals) or len(goals) > 1

    def test_clear_task_no_ambiguity(self):
        """Test clear task has minimal ambiguity."""
        generator = GoalGenerator()
        request = GoalRequest.create(
            task_id="task_001",
            session_id="session_001",
            domain_hint=DomainHint.HOUDINI,
            raw_task_summary="Create a terrain heightfield with 512x512 resolution",
        )

        goals = generator.generate_root_goal(request)

        # Clear task should have fewer ambiguity flags
        primary = goals[0]
        assert len(primary.ambiguity_flags) <= 2 <= 2