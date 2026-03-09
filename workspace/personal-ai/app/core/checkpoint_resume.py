"""Checkpoint Resume and Recovery Module.

Provides resume and recovery functionality for long-horizon plans,
including checkpoint loading, validation, context restoration,
and safe continuation of interrupted executions.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.core.checkpoint import (
    Checkpoint,
    CheckpointStatus,
    StepState,
    StepStatus,
    SubgoalState,
)
from app.core.checkpoint_lifecycle import (
    CheckpointLifecycle,
    CheckpointValidationResult,
)
from app.core.bridge_health import BridgeHealthReport, check_bridge_health
from app.learning.error_normalizer import (
    NormalizedError,
    NormalizedErrorType,
    normalize_checkpoint_failure,
)


@dataclass
class ResumeDecision:
    """Decision about whether and how to resume from a checkpoint."""

    should_resume: bool
    reason: str
    recovery_mode: str = "normal"  # normal, replay, safe, fail
    steps_to_skip: list[str] = field(default_factory=list)
    steps_to_replay: list[str] = field(default_factory=list)
    resume_from_step_id: str | None = None
    resume_from_subgoal_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "should_resume": self.should_resume,
            "reason": self.reason,
            "recovery_mode": self.recovery_mode,
            "steps_to_skip": self.steps_to_skip,
            "steps_to_replay": self.steps_to_replay,
            "resume_from_step_id": self.resume_from_step_id,
            "resume_from_subgoal_id": self.resume_from_subgoal_id,
        }


@dataclass
class ResumeContext:
    """Context restored from a checkpoint for resuming execution."""

    checkpoint: Checkpoint
    restored_retry_state: dict[str, Any]
    restored_repair_state: dict[str, Any]
    bridge_health_at_checkpoint: dict[str, Any] | None
    verification_status: dict[str, Any]
    memory_context: dict[str, Any]
    resume_decision: ResumeDecision
    replay_required: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint.checkpoint_id,
            "restored_retry_state": self.restored_retry_state,
            "restored_repair_state": self.restored_repair_state,
            "bridge_health_at_checkpoint": self.bridge_health_at_checkpoint,
            "verification_status": self.verification_status,
            "memory_context": self.memory_context,
            "resume_decision": self.resume_decision.to_dict(),
            "replay_required": self.replay_required,
        }


@dataclass
class ResumeResult:
    """Result of a resume operation."""

    success: bool
    checkpoint_loaded: bool
    checkpoint_id: str | None
    checkpoint_valid: bool
    resumed_from_step: str | None
    resumed_from_subgoal: str | None
    restored_retry_state: dict[str, Any]
    restored_repair_state: dict[str, Any]
    replay_required: bool
    replayed_steps: list[str]
    recovery_mode: str
    resume_decision_reason: str
    recovery_success: bool
    final_resume_status: str
    normalized_error: NormalizedError | None = None
    resume_context: ResumeContext | None = None

    def to_dict(self) -> dict[str, Any]:
        result = {
            "success": self.success,
            "checkpoint_loaded": self.checkpoint_loaded,
            "checkpoint_id": self.checkpoint_id,
            "checkpoint_valid": self.checkpoint_valid,
            "resumed_from_step": self.resumed_from_step,
            "resumed_from_subgoal": self.resumed_from_subgoal,
            "restored_retry_state": self.restored_retry_state,
            "restored_repair_state": self.restored_repair_state,
            "replay_required": self.replay_required,
            "replayed_steps": self.replayed_steps,
            "recovery_mode": self.recovery_mode,
            "resume_decision_reason": self.resume_decision_reason,
            "recovery_success": self.recovery_success,
            "final_resume_status": self.final_resume_status,
        }

        if self.normalized_error:
            result["error"] = self.normalized_error.to_dict()

        if self.resume_context:
            result["resume_context"] = self.resume_context.to_dict()

        return result


class ResumeManager:
    """Manages resume and recovery from checkpoints.

    Provides a unified interface for:
    - Loading and validating checkpoints
    - Making resume decisions based on policy and context
    - Restoring execution context
    - Handling partial or inconsistent checkpoints
    - Managing replay of steps when needed
    """

    def __init__(
        self,
        lifecycle: CheckpointLifecycle | None = None,
        repo_root: str = ".",
        policy_replay_verified: bool = False,
        policy_require_bridge_health_check: bool = True,
        policy_max_resume_attempts: int = 3,
    ):
        """Initialize the resume manager.

        Args:
            lifecycle: Optional CheckpointLifecycle instance
            repo_root: Repository root path
            policy_replay_verified: Whether to replay verified steps
            policy_require_bridge_health_check: Whether to require bridge health check
            policy_max_resume_attempts: Maximum resume attempts
        """
        self._lifecycle = lifecycle or CheckpointLifecycle(repo_root=repo_root)
        self._repo_root = repo_root
        self._policy_replay_verified = policy_replay_verified
        self._policy_require_bridge_health_check = policy_require_bridge_health_check
        self._policy_max_resume_attempts = policy_max_resume_attempts

    def attempt_resume(
        self,
        task_id: str,
        plan_id: str | None = None,
        session_id: str | None = None,
        force_checkpoint_id: str | None = None,
        validate_bridge_health: bool = True,
    ) -> ResumeResult:
        """Attempt to resume from the latest valid checkpoint.

        Args:
            task_id: Task ID to resume
            plan_id: Optional plan ID filter
            session_id: Optional expected session ID (for validation)
            force_checkpoint_id: Optional specific checkpoint ID to use
            validate_bridge_health: Whether to check current bridge health

        Returns:
            ResumeResult with resume status and context
        """
        # Step 1: Load checkpoint
        checkpoint, load_error = self._load_checkpoint(
            task_id=task_id,
            plan_id=plan_id,
            checkpoint_id=force_checkpoint_id,
        )

        if checkpoint is None:
            return ResumeResult(
                success=False,
                checkpoint_loaded=False,
                checkpoint_id=None,
                checkpoint_valid=False,
                resumed_from_step=None,
                resumed_from_subgoal=None,
                restored_retry_state={},
                restored_repair_state={},
                replay_required=False,
                replayed_steps=[],
                recovery_mode="fail",
                resume_decision_reason=load_error or "checkpoint_missing",
                recovery_success=False,
                final_resume_status="failed",
                normalized_error=normalize_checkpoint_failure(
                    checkpoint_id=force_checkpoint_id or f"{task_id}_latest",
                    failure_reason=load_error or "No checkpoint found",
                    error_type=NormalizedErrorType.CHECKPOINT_MISSING,
                    task_id=task_id,
                    plan_id=plan_id or "",
                ),
            )

        # Step 2: Validate checkpoint
        validation = self._lifecycle.validate_checkpoint(
            checkpoint=checkpoint,
            expected_task_id=task_id,
            expected_plan_id=plan_id,
        )

        if not validation.valid:
            return ResumeResult(
                success=False,
                checkpoint_loaded=True,
                checkpoint_id=checkpoint.checkpoint_id,
                checkpoint_valid=False,
                resumed_from_step=None,
                resumed_from_subgoal=None,
                restored_retry_state={},
                restored_repair_state={},
                replay_required=False,
                replayed_steps=[],
                recovery_mode="fail",
                resume_decision_reason=validation.error_message or validation.error_type,
                recovery_success=False,
                final_resume_status="failed",
                normalized_error=normalize_checkpoint_failure(
                    checkpoint_id=checkpoint.checkpoint_id,
                    failure_reason=validation.error_message or "Validation failed",
                    error_type=NormalizedErrorType(validation.error_type or "checkpoint_invalid"),
                    task_id=task_id,
                    plan_id=plan_id or "",
                ),
            )

        # Step 3: Check bridge health if required
        if validate_bridge_health and self._policy_require_bridge_health_check:
            bridge_health = check_bridge_health(
                domain=checkpoint.domain,
                host="127.0.0.1",
                port=9988 if checkpoint.domain == "touchdesigner" else 9989,
            )

            if not bridge_health.is_healthy and checkpoint.bridge_health_summary:
                # Bridge was healthy at checkpoint but not now
                if checkpoint.bridge_health_summary.bridge_reachable:
                    # This is a degradation - may need special handling
                    pass  # Continue with caution

        # Step 4: Make resume decision
        decision = self._make_resume_decision(checkpoint, validation)

        if not decision.should_resume:
            return ResumeResult(
                success=False,
                checkpoint_loaded=True,
                checkpoint_id=checkpoint.checkpoint_id,
                checkpoint_valid=True,
                resumed_from_step=None,
                resumed_from_subgoal=None,
                restored_retry_state={},
                restored_repair_state={},
                replay_required=False,
                replayed_steps=[],
                recovery_mode=decision.recovery_mode,
                resume_decision_reason=decision.reason,
                recovery_success=False,
                final_resume_status="blocked",
                normalized_error=normalize_checkpoint_failure(
                    checkpoint_id=checkpoint.checkpoint_id,
                    failure_reason=decision.reason,
                    error_type=NormalizedErrorType.RESUME_NOT_ALLOWED,
                    task_id=task_id,
                    plan_id=plan_id or "",
                ),
            )

        # Step 5: Restore context
        try:
            resume_context = self._restore_context(checkpoint, decision)
        except Exception as e:
            return ResumeResult(
                success=False,
                checkpoint_loaded=True,
                checkpoint_id=checkpoint.checkpoint_id,
                checkpoint_valid=True,
                resumed_from_step=None,
                resumed_from_subgoal=None,
                restored_retry_state={},
                restored_repair_state={},
                replay_required=False,
                replayed_steps=[],
                recovery_mode="fail",
                resume_decision_reason=f"Context restoration failed: {e}",
                recovery_success=False,
                final_resume_status="failed",
                normalized_error=normalize_checkpoint_failure(
                    checkpoint_id=checkpoint.checkpoint_id,
                    failure_reason=str(e),
                    error_type=NormalizedErrorType.CHECKPOINT_RESTORE_FAILED,
                    task_id=task_id,
                    plan_id=plan_id or "",
                    original_error=e,
                ),
            )

        # Step 6: Update checkpoint as resumed
        self._lifecycle.mark_checkpoint_status(
            checkpoint=checkpoint,
            status=CheckpointStatus.ACTIVE,
            reason=f"Resumed: {decision.reason}",
        )
        self._lifecycle.save_checkpoint(checkpoint)

        return ResumeResult(
            success=True,
            checkpoint_loaded=True,
            checkpoint_id=checkpoint.checkpoint_id,
            checkpoint_valid=True,
            resumed_from_step=decision.resume_from_step_id,
            resumed_from_subgoal=decision.resume_from_subgoal_id,
            restored_retry_state=resume_context.restored_retry_state,
            restored_repair_state=resume_context.restored_repair_state,
            replay_required=resume_context.replay_required,
            replayed_steps=decision.steps_to_replay,
            recovery_mode=decision.recovery_mode,
            resume_decision_reason=decision.reason,
            recovery_success=True,
            final_resume_status="resumed",
            resume_context=resume_context,
        )

    def _load_checkpoint(
        self,
        task_id: str,
        plan_id: str | None = None,
        checkpoint_id: str | None = None,
    ) -> tuple[Checkpoint | None, str | None]:
        """Load a checkpoint.

        Args:
            task_id: Task ID
            plan_id: Optional plan ID
            checkpoint_id: Optional specific checkpoint ID

        Returns:
            Tuple of (checkpoint or None, error message or None)
        """
        if checkpoint_id:
            checkpoint = self._lifecycle.load_checkpoint(checkpoint_id, task_id)
            if checkpoint is None:
                return None, f"Checkpoint {checkpoint_id} not found"
            return checkpoint, None

        checkpoint = self._lifecycle.load_latest_checkpoint(task_id, plan_id)
        if checkpoint is None:
            return None, "No checkpoint found for task"

        return checkpoint, None

    def _make_resume_decision(
        self,
        checkpoint: Checkpoint,
        validation: CheckpointValidationResult,
    ) -> ResumeDecision:
        """Make a decision about whether and how to resume.

        Args:
            checkpoint: Checkpoint to resume from
            validation: Validation result

        Returns:
            ResumeDecision
        """
        # Determine which steps need handling
        steps_to_skip = []
        steps_to_replay = []
        resume_from_step_id = None
        resume_from_subgoal_id = checkpoint.current_subgoal_id

        # Analyze each step
        for step_id in checkpoint.step_order:
            step = checkpoint.steps.get(step_id)
            if not step:
                continue

            if step.status == StepStatus.COMPLETED_VERIFIED:
                # Verified steps may be skipped (unless policy requires replay)
                if self._policy_replay_verified:
                    steps_to_replay.append(step_id)
                else:
                    steps_to_skip.append(step_id)

            elif step.status == StepStatus.COMPLETED:
                # Completed steps are skipped
                steps_to_skip.append(step_id)

            elif step.status == StepStatus.FAILED_RECOVERABLE:
                # Failed but recoverable steps may be retried
                if step.can_retry():
                    steps_to_replay.append(step_id)
                    if resume_from_step_id is None:
                        resume_from_step_id = step_id
                else:
                    # Exhausted retries - can't resume
                    return ResumeDecision(
                        should_resume=False,
                        reason=f"Step {step_id} has exhausted retries",
                        recovery_mode="fail",
                    )

            elif step.status == StepStatus.FAILED:
                # Failed steps block resume unless repairable
                return ResumeDecision(
                    should_resume=False,
                    reason=f"Step {step_id} failed without recovery",
                    recovery_mode="fail",
                )

            elif step.status == StepStatus.IN_PROGRESS:
                # In-progress steps need replay
                steps_to_replay.append(step_id)
                if resume_from_step_id is None:
                    resume_from_step_id = step_id

            elif step.status == StepStatus.PENDING:
                # First pending step is where we resume
                if resume_from_step_id is None:
                    resume_from_step_id = step_id

        # Check if we have any steps to execute
        if resume_from_step_id is None and not steps_to_replay:
            return ResumeDecision(
                should_resume=False,
                reason="No steps to execute",
                recovery_mode="fail",
            )

        # Determine recovery mode
        recovery_mode = "normal"
        if steps_to_replay:
            # Check if replay is for failed steps
            failed_steps = [s for s in steps_to_replay if checkpoint.steps[s].status == StepStatus.FAILED_RECOVERABLE]
            if failed_steps:
                recovery_mode = "retry"
            elif any(checkpoint.steps[s].status == StepStatus.IN_PROGRESS for s in steps_to_replay):
                recovery_mode = "safe"

        return ResumeDecision(
            should_resume=True,
            reason=f"Resuming from step {resume_from_step_id}",
            recovery_mode=recovery_mode,
            steps_to_skip=steps_to_skip,
            steps_to_replay=steps_to_replay,
            resume_from_step_id=resume_from_step_id,
            resume_from_subgoal_id=resume_from_subgoal_id,
        )

    def _restore_context(
        self,
        checkpoint: Checkpoint,
        decision: ResumeDecision,
    ) -> ResumeContext:
        """Restore execution context from checkpoint.

        Args:
            checkpoint: Checkpoint to restore from
            decision: Resume decision

        Returns:
            ResumeContext
        """
        # Restore retry state
        restored_retry_state = {
            "global": checkpoint.global_retry_state.to_dict(),
            "per_step": {
                step_id: checkpoint.retry_state[step_id].to_dict()
                for step_id in checkpoint.retry_state
            },
        }

        # Restore repair state
        restored_repair_state = {
            "global": checkpoint.global_repair_state.to_dict(),
            "per_step": {
                step_id: checkpoint.repair_state[step_id].to_dict()
                for step_id in checkpoint.repair_state
            },
        }

        # Get bridge health at checkpoint
        bridge_health_at_checkpoint = None
        if checkpoint.bridge_health_summary:
            bridge_health_at_checkpoint = checkpoint.bridge_health_summary.to_dict()

        # Get verification status
        verification_status = {
            "verified_steps": [
                step_id for step_id in checkpoint.step_order
                if checkpoint.steps.get(step_id)
                and checkpoint.steps[step_id].status == StepStatus.COMPLETED_VERIFIED
            ],
            "unverified_steps": [
                step_id for step_id in checkpoint.step_order
                if checkpoint.steps.get(step_id)
                and checkpoint.steps[step_id].status == StepStatus.COMPLETED
            ],
            "verification_summary": checkpoint.verification_summary.to_dict(),
        }

        # Get memory context
        memory_context = checkpoint.memory_context_summary.to_dict()

        # Determine if replay is required
        replay_required = len(decision.steps_to_replay) > 0

        return ResumeContext(
            checkpoint=checkpoint,
            restored_retry_state=restored_retry_state,
            restored_repair_state=restored_repair_state,
            bridge_health_at_checkpoint=bridge_health_at_checkpoint,
            verification_status=verification_status,
            memory_context=memory_context,
            resume_decision=decision,
            replay_required=replay_required,
        )

    def get_resume_recommendation(
        self,
        task_id: str,
        plan_id: str | None = None,
    ) -> dict[str, Any]:
        """Get a recommendation about whether resume is advisable.

        Args:
            task_id: Task ID
            plan_id: Optional plan ID

        Returns:
            Dictionary with recommendation details
        """
        # Check for checkpoint
        checkpoint = self._lifecycle.load_latest_checkpoint(task_id, plan_id)

        if checkpoint is None:
            return {
                "can_resume": False,
                "recommendation": "no_checkpoint",
                "reason": "No checkpoint found for task",
                "checkpoint_id": None,
            }

        # Validate checkpoint
        validation = self._lifecycle.validate_checkpoint(
            checkpoint=checkpoint,
            expected_task_id=task_id,
            expected_plan_id=plan_id,
        )

        if not validation.valid:
            return {
                "can_resume": False,
                "recommendation": "invalid_checkpoint",
                "reason": validation.error_message,
                "checkpoint_id": checkpoint.checkpoint_id,
                "error_type": validation.error_type,
                "can_recover": validation.can_recover,
            }

        # Get progress
        progress = checkpoint.get_progress()

        # Make resume decision
        decision = self._make_resume_decision(checkpoint, validation)

        return {
            "can_resume": decision.should_resume,
            "recommendation": "resume" if decision.should_resume else "start_fresh",
            "reason": decision.reason,
            "checkpoint_id": checkpoint.checkpoint_id,
            "progress": progress,
            "recovery_mode": decision.recovery_mode,
            "steps_to_replay": len(decision.steps_to_replay),
            "steps_completed": len(decision.steps_to_skip),
        }

    def handle_partial_checkpoint(
        self,
        task_id: str,
        checkpoint_id: str,
    ) -> ResumeResult:
        """Handle a partial or inconsistent checkpoint.

        Attempts to recover as much context as possible from a damaged
        checkpoint and make a best-effort resume decision.

        Args:
            task_id: Task ID
            checkpoint_id: Checkpoint ID

        Returns:
            ResumeResult
        """
        # Try to load checkpoint
        checkpoint = self._lifecycle.load_checkpoint(checkpoint_id, task_id)

        if checkpoint is None:
            return ResumeResult(
                success=False,
                checkpoint_loaded=False,
                checkpoint_id=checkpoint_id,
                checkpoint_valid=False,
                resumed_from_step=None,
                resumed_from_subgoal=None,
                restored_retry_state={},
                restored_repair_state={},
                replay_required=False,
                replayed_steps=[],
                recovery_mode="fail",
                resume_decision_reason="Could not load partial checkpoint",
                recovery_success=False,
                final_resume_status="failed",
                normalized_error=normalize_checkpoint_failure(
                    checkpoint_id=checkpoint_id,
                    failure_reason="Could not load partial checkpoint",
                    error_type=NormalizedErrorType.CHECKPOINT_CORRUPT,
                    task_id=task_id,
                ),
            )

        # Mark as corrupt but try to resume
        checkpoint.status = CheckpointStatus.CORRUPT

        # Try to find any step we can resume from
        resume_step = None
        for step_id in checkpoint.step_order:
            step = checkpoint.steps.get(step_id)
            if step and step.status in (StepStatus.PENDING, StepStatus.FAILED_RECOVERABLE):
                resume_step = step_id
                break

        if resume_step is None:
            return ResumeResult(
                success=False,
                checkpoint_loaded=True,
                checkpoint_id=checkpoint_id,
                checkpoint_valid=False,
                resumed_from_step=None,
                resumed_from_subgoal=None,
                restored_retry_state={},
                restored_repair_state={},
                replay_required=False,
                replayed_steps=[],
                recovery_mode="fail",
                resume_decision_reason="Partial checkpoint has no resumable steps",
                recovery_success=False,
                final_resume_status="failed",
                normalized_error=normalize_checkpoint_failure(
                    checkpoint_id=checkpoint_id,
                    failure_reason="Partial checkpoint has no resumable steps",
                    error_type=NormalizedErrorType.RECOVERY_CONTEXT_INSUFFICIENT,
                    task_id=task_id,
                ),
            )

        # Attempt partial recovery
        decision = ResumeDecision(
            should_resume=True,
            reason="Partial checkpoint recovery",
            recovery_mode="safe",
            resume_from_step_id=resume_step,
            resume_from_subgoal_id=checkpoint.current_subgoal_id,
        )

        # Restore what context we can
        resume_context = self._restore_context(checkpoint, decision)

        return ResumeResult(
            success=True,
            checkpoint_loaded=True,
            checkpoint_id=checkpoint_id,
            checkpoint_valid=False,  # Marked as partial
            resumed_from_step=resume_step,
            resumed_from_subgoal=checkpoint.current_subgoal_id,
            restored_retry_state=resume_context.restored_retry_state,
            restored_repair_state=resume_context.restored_repair_state,
            replay_required=True,
            replayed_steps=[],
            recovery_mode="safe",
            resume_decision_reason="Partial checkpoint recovery - caution advised",
            recovery_success=True,
            final_resume_status="partial_recovery",
            resume_context=resume_context,
        )


def should_attempt_resume(
    task_id: str,
    lifecycle: CheckpointLifecycle | None = None,
    max_age_minutes: int = 60,
) -> tuple[bool, str]:
    """Quick check whether resume should be attempted.

    Args:
        task_id: Task ID to check
        lifecycle: Optional CheckpointLifecycle instance
        max_age_minutes: Maximum age for considering resume

    Returns:
        Tuple of (should_attempt, reason)
    """
    lifecycle = lifecycle or CheckpointLifecycle()

    checkpoint = lifecycle.load_latest_checkpoint(task_id)

    if checkpoint is None:
        return False, "no_checkpoint_found"

    # Check age
    try:
        created = datetime.fromisoformat(checkpoint.created_at)
        age_minutes = (datetime.now() - created).total_seconds() / 60
        if age_minutes > max_age_minutes:
            return False, f"checkpoint_too_old:{age_minutes:.0f}m"
    except ValueError:
        return False, "invalid_checkpoint_timestamp"

    # Check if resume is possible
    can_resume, reason = checkpoint.is_safe_to_resume()
    if not can_resume:
        return False, reason or "unsafe_to_resume"

    return True, "checkpoint_valid_and_fresh"
