"""Tests for checkpoint integration.

Tests Checkpoint, CheckpointLifecycle, CheckpointResume, and their
integration with the runtime loop and domain execution paths.
"""

import json
import os
import tempfile
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from app.core.checkpoint import (
    BridgeHealthSummary,
    Checkpoint,
    CheckpointStatus,
    ExecutionBackendSummary,
    MemoryContextSummary,
    RepairState,
    RetryState,
    StepState,
    StepStatus,
    SubgoalState,
    VerificationSummary,
    create_checkpoint_id,
    create_step_id,
    create_subgoal_id,
)
from app.core.checkpoint_lifecycle import (
    CheckpointBoundaryDetector,
    CheckpointLifecycle,
    CheckpointValidationResult,
)
from app.core.checkpoint_resume import (
    ResumeContext,
    ResumeDecision,
    ResumeManager,
    ResumeResult,
    should_attempt_resume,
)
from app.core.memory_runtime import RuntimeMemoryContext
from app.learning.error_normalizer import NormalizedErrorType


class TestStepState:
    """Tests for StepState dataclass."""

    def test_step_state_creation(self):
        """Test creating a StepState."""
        step = StepState(
            step_id="step_001",
            description="Test step",
            action="create_node",
        )

        assert step.step_id == "step_001"
        assert step.description == "Test step"
        assert step.action == "create_node"
        assert step.status == StepStatus.PENDING

    def test_step_state_mark_started(self):
        """Test marking step as started."""
        step = StepState(step_id="step_001")
        step.mark_started()

        assert step.status == StepStatus.IN_PROGRESS
        assert step.started_at is not None

    def test_step_state_mark_completed(self):
        """Test marking step as completed."""
        step = StepState(step_id="step_001")
        step.mark_completed(verified=True)

        assert step.status == StepStatus.COMPLETED_VERIFIED
        assert step.verified is True
        assert step.completed_at is not None

    def test_step_state_mark_failed(self):
        """Test marking step as failed."""
        step = StepState(step_id="step_001")
        step.mark_failed(error={"message": "test error"}, recoverable=True)

        assert step.status == StepStatus.FAILED_RECOVERABLE
        assert step.retry_count == 1
        assert step.error is not None

    def test_step_state_can_retry(self):
        """Test retry logic."""
        step = StepState(step_id="step_001", max_retries=3)
        assert step.can_retry() is False  # Not failed yet

        step.mark_failed(recoverable=True)
        assert step.can_retry() is True

        step.mark_failed(recoverable=True)
        step.mark_failed(recoverable=True)
        assert step.can_retry() is False  # Max retries reached


class TestSubgoalState:
    """Tests for SubgoalState dataclass."""

    def test_subgoal_state_creation(self):
        """Test creating a SubgoalState."""
        subgoal = SubgoalState(
            subgoal_id="subgoal_001",
            description="Test subgoal",
        )

        assert subgoal.subgoal_id == "subgoal_001"
        assert subgoal.description == "Test subgoal"
        assert subgoal.status == StepStatus.PENDING

    def test_subgoal_get_progress(self):
        """Test progress calculation."""
        subgoal = SubgoalState(subgoal_id="subgoal_001")

        # Add steps
        step1 = StepState(step_id="step_1")
        step2 = StepState(step_id="step_2")
        step3 = StepState(step_id="step_3")

        step1.mark_completed()
        step2.mark_completed()

        subgoal.steps = {"step_1": step1, "step_2": step2, "step_3": step3}
        subgoal.step_order = ["step_1", "step_2", "step_3"]

        completed, total = subgoal.get_progress()
        assert completed == 2
        assert total == 3


class TestCheckpoint:
    """Tests for Checkpoint dataclass."""

    def test_checkpoint_creation(self):
        """Test creating a checkpoint."""
        checkpoint = Checkpoint(
            checkpoint_id="checkpoint_001",
            task_id="task_001",
            session_id="session_001",
            plan_id="plan_001",
            domain="touchdesigner",
            current_goal="Create TOP network",
        )

        assert checkpoint.checkpoint_id == "checkpoint_001"
        assert checkpoint.task_id == "task_001"
        assert checkpoint.domain == "touchdesigner"
        assert checkpoint.status == CheckpointStatus.ACTIVE

    def test_checkpoint_serialization(self):
        """Test checkpoint serialization/deserialization."""
        checkpoint = Checkpoint(
            checkpoint_id="checkpoint_001",
            task_id="task_001",
            session_id="session_001",
            plan_id="plan_001",
            domain="touchdesigner",
            current_goal="Create TOP network",
        )

        # Add a step
        step = StepState(step_id="step_001", action="create_node")
        checkpoint.steps["step_001"] = step
        checkpoint.step_order.append("step_001")

        # Serialize
        data = checkpoint.to_dict()
        assert data["checkpoint_id"] == "checkpoint_001"
        assert data["steps"]["step_001"]["step_id"] == "step_001"

        # Deserialize
        restored = Checkpoint.from_dict(data)
        assert restored.checkpoint_id == "checkpoint_001"
        assert "step_001" in restored.steps

    def test_checkpoint_is_safe_to_resume(self):
        """Test resume safety check."""
        checkpoint = Checkpoint(
            checkpoint_id="checkpoint_001",
            task_id="task_001",
            session_id="session_001",
            plan_id="plan_001",
            domain="touchdesigner",
            current_goal="Create TOP network",
        )

        # Not safe - no pending steps
        can_resume, reason = checkpoint.is_safe_to_resume()
        assert can_resume is False

        # Add a pending step
        step = StepState(step_id="step_001")
        checkpoint.steps["step_001"] = step
        checkpoint.step_order.append("step_001")
        checkpoint.pending_step_ids.append("step_001")

        can_resume, reason = checkpoint.is_safe_to_resume()
        assert can_resume is True

    def test_checkpoint_get_progress(self):
        """Test checkpoint progress calculation."""
        checkpoint = Checkpoint(
            checkpoint_id="checkpoint_001",
            task_id="task_001",
            session_id="session_001",
            plan_id="plan_001",
        )

        # Add steps
        for i in range(5):
            step = StepState(step_id=f"step_{i}")
            checkpoint.steps[f"step_{i}"] = step
            checkpoint.step_order.append(f"step_{i}")
            if i < 3:
                step.mark_completed()
                checkpoint.completed_step_ids.append(f"step_{i}")
            else:
                checkpoint.pending_step_ids.append(f"step_{i}")

        progress = checkpoint.get_progress()
        assert progress["total_steps"] == 5
        assert progress["completed"] == 3
        assert progress["pending"] == 2

    def test_checkpoint_should_replay_step(self):
        """Test replay decision logic."""
        checkpoint = Checkpoint(
            checkpoint_id="checkpoint_001",
            task_id="task_001",
            session_id="session_001",
            plan_id="plan_001",
        )

        # Failed step should be replayed
        failed_step = StepState(step_id="step_failed")
        failed_step.mark_failed(recoverable=False)
        checkpoint.steps["step_failed"] = failed_step

        assert checkpoint.should_replay_step("step_failed") is True

        # Completed verified step should not be replayed (unless policy requires)
        verified_step = StepState(step_id="step_verified")
        verified_step.mark_completed(verified=True)
        checkpoint.steps["step_verified"] = verified_step

        assert checkpoint.should_replay_step("step_verified") is False
        assert checkpoint.should_replay_step("step_verified", policy_replay_verified=True) is True


class TestCheckpointLifecycle:
    """Tests for CheckpointLifecycle."""

    def test_checkpoint_lifecycle_init(self):
        """Test lifecycle manager initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lifecycle = CheckpointLifecycle(repo_root=tmpdir)
            assert lifecycle.current_checkpoint is None

    def test_create_checkpoint(self):
        """Test checkpoint creation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lifecycle = CheckpointLifecycle(repo_root=tmpdir)

            checkpoint = lifecycle.create_checkpoint(
                task_id="task_001",
                session_id="session_001",
                plan_id="plan_001",
                domain="touchdesigner",
                current_goal="Create TOP network",
                steps=[
                    {"action": "create_node", "description": "Create node"},
                    {"action": "set_param", "description": "Set parameter"},
                ],
            )

            assert checkpoint.task_id == "task_001"
            assert checkpoint.domain == "touchdesigner"
            assert len(checkpoint.steps) == 2
            assert lifecycle.current_checkpoint == checkpoint

    def test_save_and_load_checkpoint(self):
        """Test checkpoint persistence."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lifecycle = CheckpointLifecycle(repo_root=tmpdir)

            checkpoint = lifecycle.create_checkpoint(
                task_id="task_001",
                session_id="session_001",
                plan_id="plan_001",
                domain="touchdesigner",
                current_goal="Create TOP network",
            )

            # Save checkpoint
            filepath = lifecycle.save_checkpoint(checkpoint)
            assert os.path.exists(filepath)

            # Load checkpoint
            loaded = lifecycle.load_checkpoint(checkpoint.checkpoint_id, "task_001")
            assert loaded is not None
            assert loaded.checkpoint_id == checkpoint.checkpoint_id

    def test_load_latest_checkpoint(self):
        """Test loading latest checkpoint."""
        import time
        with tempfile.TemporaryDirectory() as tmpdir:
            lifecycle = CheckpointLifecycle(repo_root=tmpdir)

            # Create multiple checkpoints with delay
            for i in range(3):
                checkpoint = lifecycle.create_checkpoint(
                    task_id="task_001",
                    session_id="session_001",
                    plan_id="plan_001",
                    domain="touchdesigner",
                    current_goal=f"Goal {i}",
                )
                lifecycle.save_checkpoint(checkpoint)
                time.sleep(0.1)  # Ensure different timestamps

            # Load latest
            latest = lifecycle.load_latest_checkpoint("task_001")
            assert latest is not None
            assert latest.current_goal == "Goal 2"

    def test_validate_checkpoint(self):
        """Test checkpoint validation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lifecycle = CheckpointLifecycle(repo_root=tmpdir)

            checkpoint = lifecycle.create_checkpoint(
                task_id="task_001",
                session_id="session_001",
                plan_id="plan_001",
                domain="touchdesigner",
                current_goal="Create TOP network",
            )

            # Add a pending step
            step = StepState(step_id="step_001")
            checkpoint.steps["step_001"] = step
            checkpoint.step_order.append("step_001")
            checkpoint.pending_step_ids.append("step_001")

            # Valid checkpoint
            result = lifecycle.validate_checkpoint(checkpoint, expected_task_id="task_001")
            assert result.valid is True

            # Wrong task ID
            result = lifecycle.validate_checkpoint(checkpoint, expected_task_id="task_002")
            assert result.valid is False
            assert result.error_type == "checkpoint_incompatible"

    def test_validate_checkpoint_stale(self):
        """Test stale checkpoint detection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lifecycle = CheckpointLifecycle(repo_root=tmpdir, ttl_minutes=1)

            checkpoint = lifecycle.create_checkpoint(
                task_id="task_001",
                session_id="session_001",
                plan_id="plan_001",
                domain="touchdesigner",
                current_goal="Create TOP network",
            )

            # Add pending step
            step = StepState(step_id="step_001")
            checkpoint.steps["step_001"] = step
            checkpoint.step_order.append("step_001")
            checkpoint.pending_step_ids.append("step_001")

            # Manually set created_at to be old
            old_time = (datetime.now() - timedelta(minutes=5)).isoformat()
            checkpoint.created_at = old_time

            result = lifecycle.validate_checkpoint(checkpoint, expected_task_id="task_001")
            assert result.valid is False
            assert result.error_type == "checkpoint_stale"

    def test_list_checkpoints(self):
        """Test listing checkpoints."""
        import time
        with tempfile.TemporaryDirectory() as tmpdir:
            lifecycle = CheckpointLifecycle(repo_root=tmpdir)

            # Create checkpoints with delay
            for i in range(3):
                checkpoint = lifecycle.create_checkpoint(
                    task_id="task_001",
                    session_id="session_001",
                    plan_id="plan_001",
                    domain="touchdesigner",
                    current_goal=f"Goal {i}",
                )
                lifecycle.save_checkpoint(checkpoint)
                time.sleep(0.1)  # Ensure different timestamps

            checkpoints = lifecycle.list_checkpoints("task_001")
            assert len(checkpoints) == 3

    def test_delete_checkpoint(self):
        """Test checkpoint deletion."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lifecycle = CheckpointLifecycle(repo_root=tmpdir)

            checkpoint = lifecycle.create_checkpoint(
                task_id="task_001",
                session_id="session_001",
                plan_id="plan_001",
                domain="touchdesigner",
                current_goal="Goal",
            )
            lifecycle.save_checkpoint(checkpoint)

            # Delete
            result = lifecycle.delete_checkpoint(checkpoint.checkpoint_id, "task_001")
            assert result is True

            # Verify deleted
            loaded = lifecycle.load_checkpoint(checkpoint.checkpoint_id, "task_001")
            assert loaded is None


class TestCheckpointBoundaryDetector:
    """Tests for CheckpointBoundaryDetector."""

    def test_boundary_detector_init(self):
        """Test boundary detector initialization."""
        detector = CheckpointBoundaryDetector()
        assert detector._checkpoint_after_steps == 1

    def test_should_checkpoint_step_completed(self):
        """Test checkpoint after step completion."""
        detector = CheckpointBoundaryDetector(checkpoint_after_steps=2)

        # First step - no checkpoint
        should, reason = detector.should_checkpoint(step_completed=True)
        assert should is False

        # Second step - checkpoint
        should, reason = detector.should_checkpoint(step_completed=True)
        assert should is True
        assert reason == "step_threshold"

    def test_should_checkpoint_verified(self):
        """Test checkpoint after verified step."""
        detector = CheckpointBoundaryDetector(checkpoint_after_verified_steps=True)

        should, reason = detector.should_checkpoint(step_completed=True, step_verified=True)
        assert should is True
        assert reason == "step_verified"

    def test_should_checkpoint_failure(self):
        """Test checkpoint on failure."""
        detector = CheckpointBoundaryDetector(checkpoint_on_failure=True)

        should, reason = detector.should_checkpoint(step_failed=True)
        assert should is True
        assert reason == "step_failed"

    def test_should_checkpoint_force(self):
        """Test forced checkpoint."""
        detector = CheckpointBoundaryDetector()

        should, reason = detector.should_checkpoint(force=True)
        assert should is True
        assert reason == "forced"


class TestResumeManager:
    """Tests for ResumeManager."""

    def test_resume_manager_init(self):
        """Test resume manager initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ResumeManager(repo_root=tmpdir)
            assert manager._policy_max_resume_attempts == 3

    def test_attempt_resume_no_checkpoint(self):
        """Test resume with no checkpoint."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ResumeManager(repo_root=tmpdir)

            result = manager.attempt_resume("nonexistent_task")

            assert result.success is False
            assert result.checkpoint_loaded is False
            assert result.normalized_error is not None
            assert result.normalized_error.error_type == NormalizedErrorType.CHECKPOINT_MISSING

    def test_attempt_resume_success(self):
        """Test successful resume."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lifecycle = CheckpointLifecycle(repo_root=tmpdir)
            manager = ResumeManager(lifecycle=lifecycle, repo_root=tmpdir)

            # Create checkpoint
            checkpoint = lifecycle.create_checkpoint(
                task_id="task_001",
                session_id="session_001",
                plan_id="plan_001",
                domain="touchdesigner",
                current_goal="Create TOP network",
            )

            # Add pending step
            step = StepState(step_id="step_001")
            checkpoint.steps["step_001"] = step
            checkpoint.step_order.append("step_001")
            checkpoint.pending_step_ids.append("step_001")

            lifecycle.save_checkpoint(checkpoint)

            # Attempt resume
            result = manager.attempt_resume("task_001")

            assert result.success is True
            assert result.checkpoint_loaded is True
            assert result.checkpoint_valid is True

    def test_attempt_resume_invalid_checkpoint(self):
        """Test resume with invalid checkpoint."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lifecycle = CheckpointLifecycle(repo_root=tmpdir)
            manager = ResumeManager(lifecycle=lifecycle, repo_root=tmpdir)

            # Create checkpoint with wrong task ID
            checkpoint = lifecycle.create_checkpoint(
                task_id="task_001",
                session_id="session_001",
                plan_id="plan_001",
                domain="touchdesigner",
                current_goal="Create TOP network",
            )
            lifecycle.save_checkpoint(checkpoint)

            # Attempt resume with different task ID
            result = manager.attempt_resume("task_002")

            assert result.success is False
            assert result.checkpoint_loaded is False
            assert result.normalized_error is not None

    def test_get_resume_recommendation(self):
        """Test resume recommendation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lifecycle = CheckpointLifecycle(repo_root=tmpdir)
            manager = ResumeManager(lifecycle=lifecycle, repo_root=tmpdir)

            # No checkpoint
            rec = manager.get_resume_recommendation("nonexistent")
            assert rec["can_resume"] is False
            assert rec["recommendation"] == "no_checkpoint"

            # Create checkpoint
            checkpoint = lifecycle.create_checkpoint(
                task_id="task_001",
                session_id="session_001",
                plan_id="plan_001",
                domain="touchdesigner",
                current_goal="Create TOP network",
            )

            # Add pending step
            step = StepState(step_id="step_001")
            checkpoint.steps["step_001"] = step
            checkpoint.step_order.append("step_001")
            checkpoint.pending_step_ids.append("step_001")

            lifecycle.save_checkpoint(checkpoint)

            rec = manager.get_resume_recommendation("task_001")
            assert rec["can_resume"] is True
            assert rec["recommendation"] == "resume"

    def test_handle_partial_checkpoint(self):
        """Test partial checkpoint handling."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lifecycle = CheckpointLifecycle(repo_root=tmpdir)
            manager = ResumeManager(lifecycle=lifecycle, repo_root=tmpdir)

            # Create checkpoint
            checkpoint = lifecycle.create_checkpoint(
                task_id="task_001",
                session_id="session_001",
                plan_id="plan_001",
                domain="touchdesigner",
                current_goal="Create TOP network",
            )

            # Add pending step
            step = StepState(step_id="step_001")
            checkpoint.steps["step_001"] = step
            checkpoint.step_order.append("step_001")
            checkpoint.pending_step_ids.append("step_001")

            lifecycle.save_checkpoint(checkpoint)

            # Handle as partial
            result = manager.handle_partial_checkpoint("task_001", checkpoint.checkpoint_id)

            assert result.success is True
            assert result.checkpoint_valid is False  # Marked as partial
            assert result.final_resume_status == "partial_recovery"


class TestCheckpointHelpers:
    """Tests for checkpoint helper functions."""

    def test_create_checkpoint_id(self):
        """Test checkpoint ID generation."""
        checkpoint_id = create_checkpoint_id("task_001")
        assert checkpoint_id.startswith("checkpoint_task_001_")

    def test_create_step_id(self):
        """Test step ID generation."""
        step_id = create_step_id("subgoal_001", 5, "create node")
        assert step_id.startswith("step_subgoal_001_005_")
        assert "create_node" in step_id

    def test_create_subgoal_id(self):
        """Test subgoal ID generation."""
        subgoal_id = create_subgoal_id("plan_001", 3, "setup network")
        assert subgoal_id.startswith("subgoal_plan_001_003_")
        assert "setup_network" in subgoal_id

    def test_should_attempt_resume(self):
        """Test resume attempt decision."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lifecycle = CheckpointLifecycle(repo_root=tmpdir)

            # No checkpoint
            should, reason = should_attempt_resume("nonexistent", lifecycle=lifecycle)
            assert should is False
            assert reason == "no_checkpoint_found"

            # Create checkpoint
            checkpoint = lifecycle.create_checkpoint(
                task_id="task_001",
                session_id="session_001",
                plan_id="plan_001",
                domain="touchdesigner",
                current_goal="Create TOP network",
            )

            # Add pending step
            step = StepState(step_id="step_001")
            checkpoint.steps["step_001"] = step
            checkpoint.step_order.append("step_001")
            checkpoint.pending_step_ids.append("step_001")

            lifecycle.save_checkpoint(checkpoint)

            should, reason = should_attempt_resume("task_001", lifecycle=lifecycle)
            assert should is True
            assert reason == "checkpoint_valid_and_fresh"


class TestDomainExecutionLoopCheckpoint:
    """Tests for checkpoint integration in domain execution loops."""

    def test_td_execution_loop_checkpoint_config(self):
        """Test TouchDesigner execution loop checkpoint configuration."""
        from app.domains.touchdesigner.td_execution_loop import TDExecutionConfig, TDExecutionLoop

        config = TDExecutionConfig(
            enable_checkpoints=True,
            task_id="test_task",
            plan_id="test_plan",
        )
        loop = TDExecutionLoop(config)

        assert loop._config.enable_checkpoints is True
        assert loop._checkpoint_lifecycle is not None
        assert loop._resume_manager is not None

    def test_houdini_execution_loop_checkpoint_config(self):
        """Test Houdini execution loop checkpoint configuration."""
        from app.domains.houdini.houdini_execution_loop import HoudiniExecutionConfig, HoudiniExecutionLoop

        config = HoudiniExecutionConfig(
            enable_checkpoints=True,
            task_id="test_task",
            plan_id="test_plan",
        )
        loop = HoudiniExecutionLoop(config)

        assert loop._config.enable_checkpoints is True
        assert loop._checkpoint_lifecycle is not None
        assert loop._resume_manager is not None

    def test_td_run_report_checkpoint_fields(self):
        """Test TouchDesigner run report includes checkpoint fields."""
        from app.domains.touchdesigner.td_execution_loop import TDRunReport

        report = TDRunReport(
            checkpoint_created=True,
            checkpoint_id="test_checkpoint",
            resumed_from_checkpoint=True,
            recovery_mode="retry",
        )

        data = report.to_dict()
        assert data["checkpoint_created"] is True
        assert data["checkpoint_id"] == "test_checkpoint"
        assert data["resumed_from_checkpoint"] is True
        assert data["recovery_mode"] == "retry"

    def test_houdini_run_report_checkpoint_fields(self):
        """Test Houdini run report includes checkpoint fields."""
        from app.domains.houdini.houdini_execution_loop import HoudiniRunReport

        report = HoudiniRunReport(
            checkpoint_created=True,
            checkpoint_id="test_checkpoint",
            resumed_from_checkpoint=True,
            recovery_mode="safe",
        )

        data = report.to_dict()
        assert data["checkpoint_created"] is True
        assert data["checkpoint_id"] == "test_checkpoint"
        assert data["resumed_from_checkpoint"] is True
        assert data["recovery_mode"] == "safe"

    def test_td_execution_without_checkpoint(self):
        """Test TouchDesigner execution without checkpoints enabled."""
        from app.domains.touchdesigner.td_execution_loop import TDExecutionConfig, TDExecutionLoop

        config = TDExecutionConfig(enable_checkpoints=False)
        loop = TDExecutionLoop(config)

        assert loop._checkpoint_lifecycle is None
        assert loop._resume_manager is None

        # attempt_resume should return None when disabled
        result = loop.attempt_resume()
        assert result is None

    def test_houdini_execution_without_checkpoint(self):
        """Test Houdini execution without checkpoints enabled."""
        from app.domains.houdini.houdini_execution_loop import HoudiniExecutionConfig, HoudiniExecutionLoop

        config = HoudiniExecutionConfig(enable_checkpoints=False)
        loop = HoudiniExecutionLoop(config)

        assert loop._checkpoint_lifecycle is None
        assert loop._resume_manager is None

        # attempt_resume should return None when disabled
        result = loop.attempt_resume()
        assert result is None

    def test_full_checkpoint_lifecycle(self):
        """Test full checkpoint creation, save, load, resume lifecycle."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create lifecycle
            lifecycle = CheckpointLifecycle(repo_root=tmpdir)

            # Create checkpoint with steps
            checkpoint = lifecycle.create_checkpoint(
                task_id="task_001",
                session_id="session_001",
                plan_id="plan_001",
                domain="touchdesigner",
                current_goal="Create TOP network",
                steps=[
                    {"action": "create_node", "description": "Create node 1"},
                    {"action": "create_node", "description": "Create node 2"},
                    {"action": "connect_nodes", "description": "Connect nodes"},
                ],
            )

            # Execute first step
            lifecycle.update_checkpoint(
                checkpoint=checkpoint,
                step_id=checkpoint.step_order[0],
                step_status=StepStatus.IN_PROGRESS,
            )

            lifecycle.update_checkpoint(
                checkpoint=checkpoint,
                step_id=checkpoint.step_order[0],
                step_status=StepStatus.COMPLETED_VERIFIED,
                verified=True,
            )

            lifecycle.save_checkpoint(checkpoint)

            # Simulate resume
            manager = ResumeManager(lifecycle=lifecycle, repo_root=tmpdir)
            result = manager.attempt_resume("task_001")

            assert result.success is True
            assert result.resumed_from_step == checkpoint.step_order[1]  # Second step
            assert len(result.replayed_steps) == 0  # No replay needed

    def test_checkpoint_with_bridge_health(self):
        """Test checkpoint with bridge health summary."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lifecycle = CheckpointLifecycle(repo_root=tmpdir)

            # Create bridge health summary
            bridge_health = BridgeHealthSummary(
                bridge_type="touchdesigner",
                bridge_enabled=True,
                bridge_reachable=True,
                ping_ok=True,
                latency_ms=15.5,
            )

            checkpoint = lifecycle.create_checkpoint(
                task_id="task_001",
                session_id="session_001",
                plan_id="plan_001",
                domain="touchdesigner",
                current_goal="Create TOP network",
            )

            checkpoint.bridge_health_summary = bridge_health

            # Serialize and verify
            data = checkpoint.to_dict()
            assert data["bridge_health_summary"]["bridge_reachable"] is True
            assert data["bridge_health_summary"]["latency_ms"] == 15.5

    def test_checkpoint_with_memory_context(self):
        """Test checkpoint with memory context summary."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lifecycle = CheckpointLifecycle(repo_root=tmpdir)

            # Create memory context
            memory_context = RuntimeMemoryContext(
                domain="touchdesigner",
                query="test",
                memory_influenced=True,
                success_pattern_count=2,
                failure_pattern_count=1,
                repair_pattern_count=1,
            )

            checkpoint = lifecycle.create_checkpoint(
                task_id="task_001",
                session_id="session_001",
                plan_id="plan_001",
                domain="touchdesigner",
                current_goal="Create TOP network",
                memory_context=memory_context,
            )

            # Verify memory context captured
            assert checkpoint.memory_context_summary.memory_influenced is True
            assert checkpoint.memory_context_summary.success_patterns_used == 2

    def test_retry_state_persistence(self):
        """Test retry state persistence across checkpoint."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lifecycle = CheckpointLifecycle(repo_root=tmpdir)

            checkpoint = lifecycle.create_checkpoint(
                task_id="task_001",
                session_id="session_001",
                plan_id="plan_001",
                domain="touchdesigner",
                current_goal="Create TOP network",
            )

            # Create retry state
            retry_state = RetryState(retry_count=0, max_retries=3)
            retry_state.record_retry("connection_timeout")
            retry_state.record_retry("rate_limit")

            checkpoint.retry_state["step_001"] = retry_state

            # Save and reload
            lifecycle.save_checkpoint(checkpoint)
            loaded = lifecycle.load_latest_checkpoint("task_001")

            assert loaded is not None
            assert "step_001" in loaded.retry_state
            assert loaded.retry_state["step_001"].retry_count == 2
            assert len(loaded.retry_state["step_001"].retry_reasons) == 2
