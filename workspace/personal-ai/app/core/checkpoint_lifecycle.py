"""Checkpoint Lifecycle Manager.

Provides checkpoint creation, persistence, validation, and lifecycle management
for long-horizon plan execution with resume and recovery support.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from app.core.checkpoint import (
    BridgeHealthSummary,
    Checkpoint,
    CheckpointStatus,
    ExecutionBackendSummary,
    MemoryContextSummary,
    RetryState,
    RepairState,
    StepState,
    StepStatus,
    SubgoalState,
    VerificationSummary,
    create_checkpoint_id,
    create_step_id,
    create_subgoal_id,
)
from app.core.bridge_health import BridgeHealthReport
from app.core.memory_runtime import RuntimeMemoryContext
from app.agent_core.backend_result import BackendSelectionResult


# Constants for checkpoint management
CHECKPOINT_VERSION = "1.0.0"
SCHEMA_VERSION = "1.0.0"
DEFAULT_CHECKPOINT_TTL_MINUTES = 60  # Checkpoints expire after 60 minutes by default
MAX_CHECKPOINTS_PER_TASK = 10  # Keep max 10 checkpoints per task


class CheckpointValidationResult:
    """Result of checkpoint validation."""

    def __init__(
        self,
        valid: bool,
        error_type: str | None = None,
        error_message: str | None = None,
        can_recover: bool = False,
    ):
        self.valid = valid
        self.error_type = error_type
        self.error_message = error_message
        self.can_recover = can_recover

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "can_recover": self.can_recover,
        }


class CheckpointLifecycle:
    """Manages checkpoint lifecycle from creation to archival.

    Provides a unified interface for:
    - Creating checkpoints at safe boundaries
    - Persisting checkpoints to disk
    - Validating checkpoint freshness and compatibility
    - Retrieving latest valid checkpoints
    - Managing checkpoint cleanup and archival
    """

    def __init__(
        self,
        repo_root: str = ".",
        checkpoint_dir: str | None = None,
        ttl_minutes: int = DEFAULT_CHECKPOINT_TTL_MINUTES,
    ):
        """Initialize the checkpoint lifecycle manager.

        Args:
            repo_root: Repository root path
            checkpoint_dir: Directory for checkpoint storage (default: repo_root/data/checkpoints)
            ttl_minutes: Time-to-live for checkpoints in minutes
        """
        self._repo_root = repo_root
        self._checkpoint_dir = checkpoint_dir or os.path.join(repo_root, "data", "checkpoints")
        self._ttl_minutes = ttl_minutes
        self._current_checkpoint: Checkpoint | None = None

        # Ensure checkpoint directory exists
        os.makedirs(self._checkpoint_dir, exist_ok=True)

    @property
    def current_checkpoint(self) -> Checkpoint | None:
        """Get the currently active checkpoint."""
        return self._current_checkpoint

    def create_checkpoint(
        self,
        task_id: str,
        session_id: str,
        plan_id: str,
        domain: str,
        current_goal: str,
        steps: list[dict[str, Any]] | None = None,
        subgoals: list[dict[str, Any]] | None = None,
        bridge_health: BridgeHealthReport | None = None,
        memory_context: RuntimeMemoryContext | None = None,
        backend_selection: BackendSelectionResult | None = None,
        checkpoint_reason: str = "manual",
        metadata: dict[str, Any] | None = None,
    ) -> Checkpoint:
        """Create a new checkpoint.

        Args:
            task_id: Task ID
            session_id: Session ID
            plan_id: Plan ID
            domain: Execution domain (e.g., "touchdesigner", "houdini")
            current_goal: Current goal being pursued
            steps: Optional list of step definitions
            subgoals: Optional list of subgoal definitions
            bridge_health: Optional bridge health report
            memory_context: Optional memory context
            backend_selection: Optional backend selection result
            checkpoint_reason: Reason for creating checkpoint
            metadata: Optional metadata

        Returns:
            New Checkpoint instance
        """
        checkpoint_id = create_checkpoint_id(task_id)

        checkpoint = Checkpoint(
            checkpoint_id=checkpoint_id,
            task_id=task_id,
            session_id=session_id,
            plan_id=plan_id,
            domain=domain,
            current_goal=current_goal,
            checkpoint_version=CHECKPOINT_VERSION,
            schema_version=SCHEMA_VERSION,
            checkpoint_reason=checkpoint_reason,
            metadata=metadata or {},
        )

        # Add steps if provided
        if steps:
            self._add_steps_to_checkpoint(checkpoint, steps)

        # Add subgoals if provided
        if subgoals:
            self._add_subgoals_to_checkpoint(checkpoint, subgoals)

        # Add bridge health summary
        if bridge_health:
            checkpoint.bridge_health_summary = BridgeHealthSummary(
                bridge_type=domain,
                bridge_enabled=True,
                bridge_reachable=bridge_health.bridge_reachable,
                ping_ok=bridge_health.ping_ok,
                latency_ms=bridge_health.latency_ms,
                last_error_code=bridge_health.last_error_code,
                last_error_message=bridge_health.last_error_message,
                degraded=bridge_health.degraded,
            )

        # Add memory context summary
        if memory_context:
            checkpoint.memory_context_summary = MemoryContextSummary(
                memory_influenced=memory_context.memory_influenced,
                success_patterns_used=memory_context.success_pattern_count,
                failure_patterns_used=memory_context.failure_pattern_count,
                repair_patterns_used=memory_context.repair_pattern_count,
            )

        # Add execution backend summary
        if backend_selection:
            checkpoint.execution_backend_summary = ExecutionBackendSummary(
                backend_type=backend_selection.selected_backend.value,
                backend_selected_at=datetime.now().isoformat(),
                fallback_used=backend_selection.used_fallback,
                dry_run_mode=backend_selection.is_dry_run,
                safety_checks_passed=backend_selection.safety_passed,
            )

        self._current_checkpoint = checkpoint
        return checkpoint

    def _add_steps_to_checkpoint(
        self,
        checkpoint: Checkpoint,
        steps: list[dict[str, Any]],
        subgoal_id: str = "default",
    ) -> None:
        """Add steps to a checkpoint.

        Args:
            checkpoint: Checkpoint to add steps to
            steps: List of step definitions
            subgoal_id: ID of the parent subgoal
        """
        for i, step_def in enumerate(steps):
            step_id = create_step_id(
                subgoal_id=subgoal_id,
                step_index=i,
                action=step_def.get("action", "unknown"),
            )

            step_state = StepState(
                step_id=step_id,
                description=step_def.get("description", ""),
                action=step_def.get("action", ""),
                params=step_def.get("params", {}),
                status=StepStatus.PENDING,
                max_retries=step_def.get("max_retries", 3),
            )

            checkpoint.steps[step_id] = step_state
            checkpoint.step_order.append(step_id)
            checkpoint.pending_step_ids.append(step_id)

    def _add_subgoals_to_checkpoint(
        self,
        checkpoint: Checkpoint,
        subgoals: list[dict[str, Any]],
    ) -> None:
        """Add subgoals to a checkpoint.

        Args:
            checkpoint: Checkpoint to add subgoals to
            subgoals: List of subgoal definitions
        """
        for i, subgoal_def in enumerate(subgoals):
            subgoal_id = create_subgoal_id(
                plan_id=checkpoint.plan_id,
                subgoal_index=i,
                description=subgoal_def.get("description", f"subgoal_{i}"),
            )

            subgoal_state = SubgoalState(
                subgoal_id=subgoal_id,
                description=subgoal_def.get("description", ""),
                status=StepStatus.PENDING,
            )

            # Add steps within subgoal
            if "steps" in subgoal_def:
                for j, step_def in enumerate(subgoal_def["steps"]):
                    step_id = create_step_id(
                        subgoal_id=subgoal_id,
                        step_index=j,
                        action=step_def.get("action", "unknown"),
                    )

                    step_state = StepState(
                        step_id=step_id,
                        description=step_def.get("description", ""),
                        action=step_def.get("action", ""),
                        params=step_def.get("params", {}),
                        status=StepStatus.PENDING,
                        max_retries=step_def.get("max_retries", 3),
                    )

                    subgoal_state.steps[step_id] = step_state
                    subgoal_state.step_order.append(step_id)
                    checkpoint.steps[step_id] = step_state
                    checkpoint.step_order.append(step_id)
                    checkpoint.pending_step_ids.append(step_id)

            checkpoint.subgoals[subgoal_id] = subgoal_state
            checkpoint.subgoal_order.append(subgoal_id)

    def update_checkpoint(
        self,
        checkpoint: Checkpoint | None = None,
        step_id: str | None = None,
        step_status: StepStatus | None = None,
        step_result: dict[str, Any] | None = None,
        error: dict[str, Any] | None = None,
        verified: bool = False,
        bridge_health: BridgeHealthReport | None = None,
        runtime_status: str | None = None,
    ) -> Checkpoint:
        """Update a checkpoint with new state.

        Args:
            checkpoint: Checkpoint to update (uses current if None)
            step_id: Step ID that was updated
            step_status: New step status
            step_result: Result data from step execution
            error: Error information if step failed
            verified: Whether step was verified
            bridge_health: Updated bridge health report
            runtime_status: Updated runtime status

        Returns:
            Updated Checkpoint
        """
        checkpoint = checkpoint or self._current_checkpoint
        if checkpoint is None:
            raise ValueError("No checkpoint to update")

        # Update step state
        if step_id and step_id in checkpoint.steps:
            step = checkpoint.steps[step_id]

            if step_status == StepStatus.IN_PROGRESS:
                step.mark_started()
                checkpoint.active_step_id = step_id
                if step_id in checkpoint.pending_step_ids:
                    checkpoint.pending_step_ids.remove(step_id)

            elif step_status in (StepStatus.COMPLETED, StepStatus.COMPLETED_VERIFIED):
                step.mark_completed(verified=verified)
                step.output = step_result
                if step_id not in checkpoint.completed_step_ids:
                    checkpoint.completed_step_ids.append(step_id)
                if step_id in checkpoint.failed_step_ids:
                    checkpoint.failed_step_ids.remove(step_id)
                if checkpoint.active_step_id == step_id:
                    checkpoint.active_step_id = None

            elif step_status in (StepStatus.FAILED, StepStatus.FAILED_RECOVERABLE):
                recoverable = step_status == StepStatus.FAILED_RECOVERABLE
                step.mark_failed(error=error, recoverable=recoverable)
                if step_id not in checkpoint.failed_step_ids:
                    checkpoint.failed_step_ids.append(step_id)
                if checkpoint.active_step_id == step_id:
                    checkpoint.active_step_id = None

        # Update bridge health
        if bridge_health:
            checkpoint.bridge_health_summary = BridgeHealthSummary(
                bridge_type=checkpoint.domain,
                bridge_enabled=True,
                bridge_reachable=bridge_health.bridge_reachable,
                ping_ok=bridge_health.ping_ok,
                latency_ms=bridge_health.latency_ms,
                last_error_code=bridge_health.last_error_code,
                last_error_message=bridge_health.last_error_message,
                degraded=bridge_health.degraded,
            )

        # Update runtime status
        if runtime_status:
            checkpoint.last_runtime_status = runtime_status

        checkpoint.update_timestamp()
        self._current_checkpoint = checkpoint
        return checkpoint

    def save_checkpoint(self, checkpoint: Checkpoint | None = None) -> str:
        """Save a checkpoint to disk.

        Args:
            checkpoint: Checkpoint to save (uses current if None)

        Returns:
            Path to saved checkpoint file
        """
        checkpoint = checkpoint or self._current_checkpoint
        if checkpoint is None:
            raise ValueError("No checkpoint to save")

        # Create task-specific directory
        task_dir = os.path.join(self._checkpoint_dir, checkpoint.task_id)
        os.makedirs(task_dir, exist_ok=True)

        # Save checkpoint
        filepath = os.path.join(task_dir, f"{checkpoint.checkpoint_id}.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(checkpoint.to_dict(), f, indent=2)

        # Cleanup old checkpoints for this task
        self._cleanup_old_checkpoints(checkpoint.task_id)

        return filepath

    def load_checkpoint(self, checkpoint_id: str, task_id: str) -> Checkpoint | None:
        """Load a checkpoint from disk.

        Args:
            checkpoint_id: Checkpoint ID to load
            task_id: Task ID for the checkpoint

        Returns:
            Checkpoint or None if not found
        """
        filepath = os.path.join(self._checkpoint_dir, task_id, f"{checkpoint_id}.json")

        if not os.path.exists(filepath):
            return None

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            return Checkpoint.from_dict(data)
        except (json.JSONDecodeError, KeyError, ValueError):
            return None

    def load_latest_checkpoint(
        self,
        task_id: str,
        plan_id: str | None = None,
    ) -> Checkpoint | None:
        """Load the most recent checkpoint for a task.

        Args:
            task_id: Task ID to find checkpoint for
            plan_id: Optional plan ID filter

        Returns:
            Latest Checkpoint or None if not found
        """
        task_dir = os.path.join(self._checkpoint_dir, task_id)

        if not os.path.exists(task_dir):
            return None

        # Find all checkpoint files
        checkpoint_files = [
            f for f in os.listdir(task_dir)
            if f.startswith("checkpoint_") and f.endswith(".json")
        ]

        if not checkpoint_files:
            return None

        # Sort by modification time (newest first)
        checkpoint_files.sort(
            key=lambda f: os.path.getmtime(os.path.join(task_dir, f)),
            reverse=True,
        )

        # Try loading checkpoints until we find a valid one
        for filename in checkpoint_files:
            filepath = os.path.join(task_dir, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)

                checkpoint = Checkpoint.from_dict(data)

                # Filter by plan_id if specified
                if plan_id and checkpoint.plan_id != plan_id:
                    continue

                self._current_checkpoint = checkpoint
                return checkpoint

            except (json.JSONDecodeError, KeyError, ValueError):
                continue

        return None

    def validate_checkpoint(
        self,
        checkpoint: Checkpoint,
        expected_task_id: str | None = None,
        expected_plan_id: str | None = None,
        max_age_minutes: int | None = None,
    ) -> CheckpointValidationResult:
        """Validate a checkpoint for freshness and compatibility.

        Args:
            checkpoint: Checkpoint to validate
            expected_task_id: Optional expected task ID
            expected_plan_id: Optional expected plan ID
            max_age_minutes: Optional max age in minutes (uses default TTL if not specified)

        Returns:
            CheckpointValidationResult with validation status
        """
        # Check schema version compatibility
        if checkpoint.schema_version != SCHEMA_VERSION:
            return CheckpointValidationResult(
                valid=False,
                error_type="checkpoint_incompatible",
                error_message=f"Schema version mismatch: {checkpoint.schema_version} != {SCHEMA_VERSION}",
                can_recover=False,
            )

        # Check task ID match
        if expected_task_id and checkpoint.task_id != expected_task_id:
            return CheckpointValidationResult(
                valid=False,
                error_type="checkpoint_incompatible",
                error_message=f"Task ID mismatch: {checkpoint.task_id} != {expected_task_id}",
                can_recover=False,
            )

        # Check plan ID match
        if expected_plan_id and checkpoint.plan_id != expected_plan_id:
            return CheckpointValidationResult(
                valid=False,
                error_type="checkpoint_incompatible",
                error_message=f"Plan ID mismatch: {checkpoint.plan_id} != {expected_plan_id}",
                can_recover=False,
            )

        # Check checkpoint status
        if checkpoint.status == CheckpointStatus.CORRUPT:
            return CheckpointValidationResult(
                valid=False,
                error_type="checkpoint_corrupt",
                error_message="Checkpoint marked as corrupt",
                can_recover=False,
            )

        if checkpoint.status == CheckpointStatus.COMPLETED:
            return CheckpointValidationResult(
                valid=False,
                error_type="checkpoint_stale",
                error_message="Plan already completed",
                can_recover=False,
            )

        # Check resume possibility
        can_resume, reason = checkpoint.is_safe_to_resume()
        if not can_resume:
            return CheckpointValidationResult(
                valid=False,
                error_type=reason or "unsafe_to_resume",
                error_message=f"Cannot resume: {reason}",
                can_recover=False,
            )

        # Check freshness
        max_age = max_age_minutes or self._ttl_minutes
        try:
            created_time = datetime.fromisoformat(checkpoint.created_at)
            age = datetime.now() - created_time
            if age > timedelta(minutes=max_age):
                return CheckpointValidationResult(
                    valid=False,
                    error_type="checkpoint_stale",
                    error_message=f"Checkpoint too old: {age.total_seconds() / 60:.1f} minutes",
                    can_recover=True,
                )
        except ValueError:
            return CheckpointValidationResult(
                valid=False,
                error_type="checkpoint_invalid",
                error_message="Invalid timestamp in checkpoint",
                can_recover=False,
            )

        return CheckpointValidationResult(valid=True)

    def list_checkpoints(self, task_id: str) -> list[dict[str, Any]]:
        """List all checkpoints for a task.

        Args:
            task_id: Task ID to list checkpoints for

        Returns:
            List of checkpoint metadata dictionaries
        """
        task_dir = os.path.join(self._checkpoint_dir, task_id)

        if not os.path.exists(task_dir):
            return []

        checkpoints = []
        for filename in os.listdir(task_dir):
            if not filename.endswith(".json"):
                continue

            filepath = os.path.join(task_dir, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)

                checkpoints.append({
                    "checkpoint_id": data.get("checkpoint_id"),
                    "task_id": data.get("task_id"),
                    "plan_id": data.get("plan_id"),
                    "created_at": data.get("created_at"),
                    "updated_at": data.get("updated_at"),
                    "status": data.get("status"),
                    "domain": data.get("domain"),
                    "current_goal": data.get("current_goal"),
                    "resume_possible": data.get("resume_possible"),
                })
            except (json.JSONDecodeError, KeyError):
                continue

        # Sort by creation time (newest first)
        checkpoints.sort(key=lambda c: c.get("created_at", ""), reverse=True)
        return checkpoints

    def delete_checkpoint(self, checkpoint_id: str, task_id: str) -> bool:
        """Delete a checkpoint.

        Args:
            checkpoint_id: Checkpoint ID to delete
            task_id: Task ID for the checkpoint

        Returns:
            True if deleted successfully
        """
        filepath = os.path.join(self._checkpoint_dir, task_id, f"{checkpoint_id}.json")

        if not os.path.exists(filepath):
            return False

        try:
            os.remove(filepath)
            return True
        except OSError:
            return False

    def archive_checkpoint(self, checkpoint_id: str, task_id: str) -> bool:
        """Archive a completed or failed checkpoint.

        Args:
            checkpoint_id: Checkpoint ID to archive
            task_id: Task ID for the checkpoint

        Returns:
            True if archived successfully
        """
        filepath = os.path.join(self._checkpoint_dir, task_id, f"{checkpoint_id}.json")
        archive_dir = os.path.join(self._checkpoint_dir, "archive", task_id)

        if not os.path.exists(filepath):
            return False

        try:
            os.makedirs(archive_dir, exist_ok=True)
            archive_path = os.path.join(archive_dir, f"{checkpoint_id}.json")
            os.rename(filepath, archive_path)
            return True
        except OSError:
            return False

    def _cleanup_old_checkpoints(self, task_id: str) -> None:
        """Clean up old checkpoints for a task, keeping only the most recent.

        Args:
            task_id: Task ID to clean up
        """
        task_dir = os.path.join(self._checkpoint_dir, task_id)

        if not os.path.exists(task_dir):
            return

        # Get all checkpoint files with modification times
        checkpoint_files = []
        for filename in os.listdir(task_dir):
            if filename.endswith(".json"):
                filepath = os.path.join(task_dir, filename)
                checkpoint_files.append((filename, os.path.getmtime(filepath)))

        # Sort by modification time (newest first)
        checkpoint_files.sort(key=lambda x: x[1], reverse=True)

        # Remove excess checkpoints
        for filename, _ in checkpoint_files[MAX_CHECKPOINTS_PER_TASK:]:
            try:
                os.remove(os.path.join(task_dir, filename))
            except OSError:
                pass

    def mark_checkpoint_status(
        self,
        checkpoint: Checkpoint,
        status: CheckpointStatus,
        reason: str | None = None,
    ) -> Checkpoint:
        """Mark a checkpoint with a specific status.

        Args:
            checkpoint: Checkpoint to update
            status: New status
            reason: Optional reason for status change

        Returns:
            Updated checkpoint
        """
        checkpoint.status = status
        checkpoint.update_timestamp()

        if reason:
            checkpoint.metadata["status_change_reason"] = reason

        if status == CheckpointStatus.COMPLETED:
            checkpoint.resume_possible = False
            checkpoint.last_runtime_status = "completed"

        elif status == CheckpointStatus.FAILED:
            checkpoint.resume_possible = False
            checkpoint.last_runtime_status = "failed"

        self._current_checkpoint = checkpoint
        return checkpoint


class CheckpointBoundaryDetector:
    """Detects safe checkpoint boundaries during execution.

    Determines when it's safe to create or update a checkpoint based on
    execution state and policy.
    """

    def __init__(
        self,
        checkpoint_after_steps: int = 1,
        checkpoint_after_subgoals: bool = True,
        checkpoint_after_verified_steps: bool = True,
        checkpoint_on_failure: bool = True,
    ):
        """Initialize the boundary detector.

        Args:
            checkpoint_after_steps: Create checkpoint after every N steps
            checkpoint_after_subgoals: Create checkpoint after subgoal completion
            checkpoint_after_verified_steps: Create checkpoint after verified steps
            checkpoint_on_failure: Create checkpoint on step failure
        """
        self._checkpoint_after_steps = checkpoint_after_steps
        self._checkpoint_after_subgoals = checkpoint_after_subgoals
        self._checkpoint_after_verified_steps = checkpoint_after_verified_steps
        self._checkpoint_on_failure = checkpoint_on_failure
        self._steps_since_checkpoint = 0

    def should_checkpoint(
        self,
        step_completed: bool = False,
        step_verified: bool = False,
        step_failed: bool = False,
        subgoal_completed: bool = False,
        force: bool = False,
    ) -> tuple[bool, str]:
        """Determine if a checkpoint should be created.

        Args:
            step_completed: Whether a step was just completed
            step_verified: Whether the step was verified
            step_failed: Whether a step failed
            subgoal_completed: Whether a subgoal was completed
            force: Force checkpoint creation

        Returns:
            Tuple of (should_checkpoint, reason)
        """
        if force:
            self._steps_since_checkpoint = 0
            return True, "forced"

        if step_failed and self._checkpoint_on_failure:
            self._steps_since_checkpoint = 0
            return True, "step_failed"

        if step_completed:
            self._steps_since_checkpoint += 1

            if self._checkpoint_after_verified_steps and step_verified:
                self._steps_since_checkpoint = 0
                return True, "step_verified"

            if self._steps_since_checkpoint >= self._checkpoint_after_steps:
                self._steps_since_checkpoint = 0
                return True, "step_threshold"

        if subgoal_completed and self._checkpoint_after_subgoals:
            self._steps_since_checkpoint = 0
            return True, "subgoal_completed"

        return False, ""

    def reset(self) -> None:
        """Reset the step counter."""
        self._steps_since_checkpoint = 0
