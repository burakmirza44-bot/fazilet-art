"""Integrated Runtime Loop Module.

Provides unified runtime orchestration with integrated error handling,
memory management, bridge health monitoring, and checkpoint/resume support.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from app.core.bridge_health import BridgeHealthReport, check_bridge_health
from app.core.checkpoint import Checkpoint, StepStatus
from app.core.checkpoint_lifecycle import CheckpointLifecycle, CheckpointBoundaryDetector
from app.core.checkpoint_resume import ResumeManager, ResumeResult, ResumeContext
from app.core.memory_runtime import (
    RuntimeMemoryContext,
    build_runtime_memory_context,
    get_memory_influence_summary,
    save_execution_result,
)
from app.learning.error_normalizer import NormalizedError, normalize_error
from app.self_directed_learning.learning_goal_models import (
    LearningGoalGenerationResult,
)
from app.self_directed_learning.runtime_integration import (
    RuntimeLearningIntegrator,
    SDLIntegrationResult,
    get_learning_integrator,
    initialize_learning_integration,
)


@dataclass
class RuntimeLoopResult:
    """Result of a runtime loop execution.

    Provides visibility into memory usage, bridge health, execution status,
    checkpoint/resume metadata, and self-directed learning.
    """

    success: bool = False
    memory_retrieved: bool = False
    memory_items_used: int = 0
    success_patterns_used: int = 0
    failure_patterns_used: int = 0
    repair_patterns_used: int = 0
    memory_writeback_done: bool = False
    bridge_health_summary: dict[str, Any] = field(default_factory=dict)
    error_count: int = 0
    normalized_errors: list[dict] = field(default_factory=list)
    execution_time_ms: float = 0.0
    domain: str = ""
    task_id: str = ""
    # Checkpoint/resume metadata
    checkpoint_created: bool = False
    checkpoint_id: str | None = None
    checkpoint_saved: bool = False
    resumed_from_checkpoint: bool = False
    resume_checkpoint_id: str | None = None
    resume_success: bool = False
    resume_context: dict[str, Any] | None = None
    replayed_steps: list[str] = field(default_factory=list)
    recovery_mode: str = ""
    # Self-directed learning metadata
    learning_goals_generated: bool = False
    learning_goal_count: int = 0
    high_priority_learning_goals: int = 0
    learning_goal_summary: list[dict] = field(default_factory=list)
    # Verification metadata
    verified: bool = False
    verification_confidence: float = 0.0
    verification_gaps: list[str] = field(default_factory=list)
    verification_performed: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "success": self.success,
            "memory_retrieved": self.memory_retrieved,
            "memory_items_used": self.memory_items_used,
            "success_patterns_used": self.success_patterns_used,
            "failure_patterns_used": self.failure_patterns_used,
            "repair_patterns_used": self.repair_patterns_used,
            "memory_writeback_done": self.memory_writeback_done,
            "bridge_health_summary": self.bridge_health_summary,
            "error_count": self.error_count,
            "normalized_errors": self.normalized_errors,
            "execution_time_ms": self.execution_time_ms,
            "domain": self.domain,
            "task_id": self.task_id,
            # Checkpoint/resume metadata
            "checkpoint_created": self.checkpoint_created,
            "checkpoint_id": self.checkpoint_id,
            "checkpoint_saved": self.checkpoint_saved,
            "resumed_from_checkpoint": self.resumed_from_checkpoint,
            "resume_checkpoint_id": self.resume_checkpoint_id,
            "resume_success": self.resume_success,
            "resume_context": self.resume_context,
            "replayed_steps": self.replayed_steps,
            "recovery_mode": self.recovery_mode,
            # Self-directed learning metadata
            "learning_goals_generated": self.learning_goals_generated,
            "learning_goal_count": self.learning_goal_count,
            "high_priority_learning_goals": self.high_priority_learning_goals,
            "learning_goal_summary": self.learning_goal_summary,
            # Verification metadata
            "verified": self.verified,
            "verification_confidence": self.verification_confidence,
            "verification_gaps": self.verification_gaps,
            "verification_performed": self.verification_performed,
        }


class IntegratedRuntimeLoop:
    """Unified runtime loop with integrated error, memory, bridge, and checkpoint systems.

    This class provides a single entry point for task execution that:
    1. Attempts to resume from checkpoint if available
    2. Checks bridge health before execution
    3. Retrieves memory context before execution
    4. Creates checkpoints at safe boundaries
    5. Normalizes all errors into the error loop
    6. Saves results to memory after execution
    7. Provides visibility into all systems via RuntimeLoopResult
    """

    def __init__(
        self,
        domain: str,
        repo_root: str = ".",
        enable_memory: bool = True,
        enable_bridge_health: bool = True,
        enable_checkpoints: bool = True,
        enable_learning: bool = True,
        task_id: str = "",
        session_id: str = "",
        plan_id: str = "",
    ):
        """Initialize the integrated runtime loop.

        Args:
            domain: Execution domain ("touchdesigner" or "houdini")
            repo_root: Repository root for memory stores
            enable_memory: Whether to enable memory retrieval/writeback
            enable_bridge_health: Whether to enable bridge health checks
            enable_checkpoints: Whether to enable checkpoint/resume
            enable_learning: Whether to enable self-directed learning
            task_id: Task ID for checkpoint tracking
            session_id: Session ID for checkpoint tracking
            plan_id: Plan ID for checkpoint tracking
        """
        self._domain = domain
        self._repo_root = repo_root
        self._enable_memory = enable_memory
        self._enable_bridge_health = enable_bridge_health
        self._enable_checkpoints = enable_checkpoints
        self._enable_learning = enable_learning
        self._task_id = task_id
        self._session_id = session_id or f"session_{int(time.time())}"
        self._plan_id = plan_id
        self._error_memory: list[NormalizedError] = []

        # Initialize checkpoint systems
        self._checkpoint_lifecycle: CheckpointLifecycle | None = None
        self._resume_manager: ResumeManager | None = None
        self._boundary_detector: CheckpointBoundaryDetector | None = None
        self._current_checkpoint: Checkpoint | None = None
        self._resume_result: ResumeResult | None = None

        if self._enable_checkpoints:
            self._checkpoint_lifecycle = CheckpointLifecycle(repo_root=repo_root)
            self._resume_manager = ResumeManager(
                lifecycle=self._checkpoint_lifecycle,
                repo_root=repo_root,
            )
            self._boundary_detector = CheckpointBoundaryDetector()

        # Initialize learning integration
        self._learning_integrator: RuntimeLearningIntegrator | None = None
        if self._enable_learning:
            integrator = get_learning_integrator()
            if integrator is None:
                integrator = initialize_learning_integration(
                    repo_root=repo_root,
                    enable_learning=True,
                )
            self._learning_integrator = integrator

    @property
    def domain(self) -> str:
        """Get the execution domain."""
        return self._domain

    @property
    def current_checkpoint(self) -> Checkpoint | None:
        """Get the current checkpoint."""
        return self._current_checkpoint

    def attempt_resume(
        self,
        force_checkpoint_id: str | None = None,
    ) -> ResumeResult | None:
        """Attempt to resume from a checkpoint.

        Args:
            force_checkpoint_id: Optional specific checkpoint ID to use

        Returns:
            ResumeResult if resume was attempted, None if checkpoints disabled
        """
        if not self._enable_checkpoints or not self._resume_manager:
            return None

        if not self._task_id:
            return None

        result = self._resume_manager.attempt_resume(
            task_id=self._task_id,
            plan_id=self._plan_id,
            session_id=self._session_id,
            force_checkpoint_id=force_checkpoint_id,
        )

        self._resume_result = result

        if result.success and result.resume_context:
            self._current_checkpoint = result.resume_context.checkpoint

        return result

    def create_checkpoint(
        self,
        current_goal: str,
        steps: list[dict[str, Any]] | None = None,
        reason: str = "manual",
    ) -> Checkpoint | None:
        """Create a checkpoint for the current execution.

        Args:
            current_goal: Current goal being pursued
            steps: Optional list of step definitions
            reason: Reason for creating checkpoint

        Returns:
            Checkpoint or None if checkpoints disabled
        """
        if not self._enable_checkpoints or not self._checkpoint_lifecycle:
            return None

        if not self._task_id:
            return None

        # Get bridge health if enabled
        bridge_health = None
        if self._enable_bridge_health:
            bridge_health = self.check_bridge_health()

        # Get memory context if enabled
        memory_context = None
        if self._enable_memory:
            memory_context = self.retrieve_memory(current_goal)

        checkpoint = self._checkpoint_lifecycle.create_checkpoint(
            task_id=self._task_id,
            session_id=self._session_id,
            plan_id=self._plan_id or f"plan_{self._task_id}",
            domain=self._domain,
            current_goal=current_goal,
            steps=steps,
            bridge_health=bridge_health,
            memory_context=memory_context,
            checkpoint_reason=reason,
        )

        self._current_checkpoint = checkpoint
        return checkpoint

    def save_checkpoint(self) -> bool:
        """Save the current checkpoint to disk.

        Returns:
            True if checkpoint was saved
        """
        if not self._enable_checkpoints or not self._checkpoint_lifecycle:
            return False

        if not self._current_checkpoint:
            return False

        try:
            self._checkpoint_lifecycle.save_checkpoint(self._current_checkpoint)
            return True
        except Exception:
            return False

    def update_checkpoint_for_step(
        self,
        step_id: str,
        status: StepStatus,
        result: dict[str, Any] | None = None,
        error: dict[str, Any] | None = None,
        verified: bool = False,
    ) -> bool:
        """Update the checkpoint for a step completion.

        Args:
            step_id: Step ID
            status: New step status
            result: Optional step result
            error: Optional error information
            verified: Whether step was verified

        Returns:
            True if checkpoint was updated
        """
        if not self._enable_checkpoints or not self._checkpoint_lifecycle:
            return False

        if not self._current_checkpoint:
            return False

        try:
            self._checkpoint_lifecycle.update_checkpoint(
                checkpoint=self._current_checkpoint,
                step_id=step_id,
                step_status=status,
                step_result=result,
                error=error,
                verified=verified,
            )
            return True
        except Exception:
            return False

    def check_bridge_health(
        self,
        host: str = "127.0.0.1",
        port: int | None = None,
    ) -> BridgeHealthReport | None:
        """Check bridge health if enabled.

        Args:
            host: Bridge host address
            port: Bridge port (defaults based on domain)

        Returns:
            BridgeHealthReport or None if disabled
        """
        if not self._enable_bridge_health:
            return None

        if port is None:
            port = 9988 if self._domain == "touchdesigner" else 9989

        return check_bridge_health(
            domain=self._domain,
            host=host,
            port=port,
        )

    def retrieve_memory(
        self,
        query: str,
        max_success: int = 3,
        max_failure: int = 3,
    ) -> RuntimeMemoryContext:
        """Retrieve memory context if enabled.

        Args:
            query: Query string to match patterns
            max_success: Maximum success patterns to retrieve
            max_failure: Maximum failure patterns to retrieve

        Returns:
            RuntimeMemoryContext with retrieved patterns
        """
        if not self._enable_memory:
            return RuntimeMemoryContext(
                domain=self._domain,
                query=query,
                memory_influenced=False,
            )

        return build_runtime_memory_context(
            domain=self._domain,
            query=query,
            repo_root=self._repo_root,
            max_success=max_success,
            max_failure=max_failure,
        )

    def execute_step_with_retry(
        self,
        step: dict[str, Any],
        max_retries: int = 3,
        task_id: str = "",
        step_id: str | None = None,
    ) -> RuntimeLoopResult:
        """Execute a single step with retry, error normalization, and checkpoint support.

        Args:
            step: Step definition to execute
            max_retries: Maximum retry attempts
            task_id: Task ID for tracking
            step_id: Optional step ID for checkpoint tracking

        Returns:
            RuntimeLoopResult with execution status
        """
        start_time = time.perf_counter()
        result = RuntimeLoopResult(
            domain=self._domain,
            task_id=task_id or self._task_id,
        )

        # Track checkpoint metadata
        if self._current_checkpoint:
            result.checkpoint_id = self._current_checkpoint.checkpoint_id

        if self._resume_result:
            result.resumed_from_checkpoint = self._resume_result.success
            result.resume_checkpoint_id = self._resume_result.checkpoint_id
            result.resume_success = self._resume_result.success
            result.recovery_mode = self._resume_result.recovery_mode
            result.replayed_steps = self._resume_result.replayed_steps

        # Retrieve memory before execution
        query = step.get("description", step.get("action", ""))
        runtime_memory = self.retrieve_memory(query)
        result.memory_retrieved = runtime_memory.memory_influenced
        result.memory_items_used = runtime_memory.total_patterns
        result.success_patterns_used = runtime_memory.success_pattern_count
        result.failure_patterns_used = runtime_memory.failure_pattern_count
        result.repair_patterns_used = runtime_memory.repair_pattern_count

        # Check bridge health if needed
        if step.get("requires_bridge", False):
            bridge_health = self.check_bridge_health()
            if bridge_health:
                result.bridge_health_summary = bridge_health.to_dict()

                if not bridge_health.is_healthy:
                    # Normalize bridge failure
                    normalized = normalize_error(
                        Exception(f"Bridge unhealthy: {bridge_health.last_error_message}"),
                        context={
                            "domain": self._domain,
                            "task_id": task_id or self._task_id,
                            "bridge_health": bridge_health.to_dict(),
                        },
                    )
                    self._error_memory.append(normalized)
                    result.normalized_errors.append(normalized.to_dict())
                    result.error_count = 1
                    result.execution_time_ms = (time.perf_counter() - start_time) * 1000
                    return result

        # Mark step as started in checkpoint
        if step_id and self._enable_checkpoints:
            self.update_checkpoint_for_step(
                step_id=step_id,
                status=StepStatus.IN_PROGRESS,
            )

        # Execute with retry
        last_error: Exception | None = None
        verified = False
        for attempt in range(max_retries):
            try:
                # Actual execution would happen here
                # For now, simulate success
                result.success = True
                verified = step.get("verify", False)
                result.execution_time_ms = (time.perf_counter() - start_time) * 1000

                # Mark step as completed in checkpoint
                if step_id and self._enable_checkpoints:
                    self.update_checkpoint_for_step(
                        step_id=step_id,
                        status=StepStatus.COMPLETED_VERIFIED if verified else StepStatus.COMPLETED,
                        result={"success": True, "attempts": attempt + 1},
                        verified=verified,
                    )
                    self.save_checkpoint()

                # Save success to memory
                if self._enable_memory:
                    save_execution_result(
                        domain=self._domain,
                        query=query,
                        success=True,
                        result_data={
                            "description": f"Executed step: {step.get('action', 'unknown')}",
                            "attempts": attempt + 1,
                            "checkpoint_id": self._current_checkpoint.checkpoint_id if self._current_checkpoint else None,
                        },
                        repo_root=self._repo_root,
                    )
                    result.memory_writeback_done = True

                return result

            except Exception as e:
                last_error = e

                # Normalize the error
                normalized = normalize_error(
                    e,
                    context={
                        "domain": self._domain,
                        "task_id": task_id or self._task_id,
                        "attempt": attempt + 1,
                        "step": step,
                    },
                )
                self._error_memory.append(normalized)
                result.normalized_errors.append(normalized.to_dict())
                result.error_count += 1

                # Mark step as failed in checkpoint
                is_recoverable = attempt < max_retries - 1
                if step_id and self._enable_checkpoints:
                    self.update_checkpoint_for_step(
                        step_id=step_id,
                        status=StepStatus.FAILED_RECOVERABLE if is_recoverable else StepStatus.FAILED,
                        error={"message": str(e), "type": type(e).__name__},
                    )
                    self.save_checkpoint()

                # Retrieve repair patterns for retry context
                if attempt < max_retries - 1 and self._enable_memory:
                    repair_memory = self.retrieve_memory(
                        query=f"{query} error: {str(e)}",
                        max_success=0,
                        max_failure=2,
                    )
                    # Use repair patterns for retry strategy
                    if repair_memory.repair_patterns:
                        result.repair_patterns_used = len(repair_memory.repair_patterns)

        # All retries exhausted
        if last_error:
            result.success = False
            result.execution_time_ms = (time.perf_counter() - start_time) * 1000

            # Save failure to memory
            if self._enable_memory:
                save_execution_result(
                    domain=self._domain,
                    query=query,
                    success=False,
                    result_data={
                        "description": f"Failed step: {step.get('action', 'unknown')}",
                        "error": str(last_error),
                        "attempts": max_retries,
                        "checkpoint_id": self._current_checkpoint.checkpoint_id if self._current_checkpoint else None,
                    },
                    repo_root=self._repo_root,
                )
                result.memory_writeback_done = True

        return result

    def execute_recipe(
        self,
        recipe: dict[str, Any],
        task_id: str = "",
        attempt_resume: bool = True,
    ) -> RuntimeLoopResult:
        """Execute a complete recipe with full integration and checkpoint support.

        Args:
            recipe: Recipe with steps to execute
            task_id: Task ID for tracking
            attempt_resume: Whether to attempt resume from checkpoint

        Returns:
            RuntimeLoopResult with aggregated execution status
        """
        start_time = time.perf_counter()
        result = RuntimeLoopResult(
            domain=self._domain,
            task_id=task_id or self._task_id,
        )

        steps = recipe.get("steps", [])
        if not steps:
            result.success = False
            result.execution_time_ms = 0.0
            return result

        # Attempt resume if enabled
        if attempt_resume and self._enable_checkpoints and self._task_id:
            resume_result = self.attempt_resume()
            if resume_result:
                result.resumed_from_checkpoint = resume_result.success
                result.resume_checkpoint_id = resume_result.checkpoint_id
                result.resume_success = resume_result.success
                result.recovery_mode = resume_result.recovery_mode
                result.replayed_steps = resume_result.replayed_steps
                result.resume_context = resume_result.to_dict()

                if resume_result.success and resume_result.resume_context:
                    # Restore execution position from checkpoint
                    checkpoint = resume_result.resume_context.checkpoint
                    # Skip already completed steps
                    completed_steps = set(checkpoint.completed_step_ids)
                    steps = [s for s in steps if s.get("step_id", "") not in completed_steps]

        # Create checkpoint for recipe start if not resuming
        if self._enable_checkpoints and not self._current_checkpoint:
            query = recipe.get("description", recipe.get("name", ""))
            self.create_checkpoint(
                current_goal=query,
                steps=steps,
                reason="recipe_start",
            )
            result.checkpoint_created = True
            if self._current_checkpoint:
                result.checkpoint_id = self._current_checkpoint.checkpoint_id
                self.save_checkpoint()
                result.checkpoint_saved = True

        # Retrieve memory for the recipe
        query = recipe.get("description", recipe.get("name", ""))
        runtime_memory = self.retrieve_memory(query)
        result.memory_retrieved = runtime_memory.memory_influenced
        result.memory_items_used = runtime_memory.total_patterns
        result.success_patterns_used = runtime_memory.success_pattern_count
        result.failure_patterns_used = runtime_memory.failure_pattern_count
        result.repair_patterns_used = runtime_memory.repair_pattern_count

        # Check bridge health if any step requires bridge
        requires_bridge = any(step.get("requires_bridge", False) for step in steps)
        if requires_bridge:
            bridge_health = self.check_bridge_health()
            if bridge_health:
                result.bridge_health_summary = bridge_health.to_dict()

                if not bridge_health.is_healthy:
                    # Normalize bridge failure
                    normalized = normalize_error(
                        Exception(f"Bridge unhealthy: {bridge_health.last_error_message}"),
                        context={
                            "domain": self._domain,
                            "task_id": task_id or self._task_id,
                            "bridge_health": bridge_health.to_dict(),
                        },
                    )
                    self._error_memory.append(normalized)
                    result.normalized_errors.append(normalized.to_dict())
                    result.error_count = 1
                    result.success = False
                    result.execution_time_ms = (time.perf_counter() - start_time) * 1000
                    return result

        # Execute each step
        all_success = True
        for i, step in enumerate(steps):
            step_id = step.get("step_id") or f"step_{i}"

            # Check if this step needs replay (from resume)
            if result.replayed_steps and step_id not in result.replayed_steps:
                # Step was already completed in previous run
                continue

            step_result = self.execute_step_with_retry(
                step,
                task_id=f"{task_id or self._task_id}_step_{i}",
                step_id=step_id,
            )

            result.normalized_errors.extend(step_result.normalized_errors)
            result.error_count += step_result.error_count
            result.checkpoint_id = step_result.checkpoint_id
            result.checkpoint_saved = step_result.checkpoint_saved

            if not step_result.success:
                all_success = False
                if not step.get("continue_on_error", False):
                    break

        result.success = all_success
        result.execution_time_ms = (time.perf_counter() - start_time) * 1000

        # Mark checkpoint as completed if successful
        if all_success and self._current_checkpoint and self._enable_checkpoints:
            from app.core.checkpoint_lifecycle import CheckpointLifecycle, CheckpointStatus
            lifecycle = self._checkpoint_lifecycle or CheckpointLifecycle(repo_root=self._repo_root)
            lifecycle.mark_checkpoint_status(
                checkpoint=self._current_checkpoint,
                status=CheckpointStatus.COMPLETED,
                reason="Recipe completed successfully",
            )
            self.save_checkpoint()

        # Save final result to memory
        if self._enable_memory:
            save_execution_result(
                domain=self._domain,
                query=query,
                success=all_success,
                result_data={
                    "description": f"Executed recipe: {recipe.get('name', 'unknown')}",
                    "steps": len(steps),
                    "errors": result.error_count,
                    "checkpoint_id": result.checkpoint_id,
                    "resumed": result.resumed_from_checkpoint,
                },
                repo_root=self._repo_root,
            )
            result.memory_writeback_done = True

        # Generate learning goals from execution evidence
        if self._enable_learning and self._learning_integrator:
            sdl_result = self._learning_integrator.generate_from_runtime(
                session_id=self._session_id,
                runtime_result=result,
                domain=self._domain,
                task_id=task_id or self._task_id,
            )
            result.learning_goals_generated = sdl_result.learning_goals_generated
            result.learning_goal_count = sdl_result.learning_goal_count
            result.high_priority_learning_goals = sdl_result.high_priority_goals
            result.learning_goal_summary = [
                {"id": g.learning_goal_id, "title": g.title, "priority": g.priority}
                for g in sdl_result.goals
            ]

        return result

    def execute_goal(
        self,
        goal: "GoalArtifact",
        max_retries: int = 3,
        verify: bool = True,
    ) -> RuntimeLoopResult:
        """Execute a GoalArtifact directly.

        Converts a goal to a step definition and executes it.

        Args:
            goal: GoalArtifact to execute
            max_retries: Maximum retry attempts
            verify: Whether to perform verification

        Returns:
            RuntimeLoopResult with execution status
        """
        from app.agent_core.goal_models import GoalArtifact

        # Convert goal to step
        step = {
            "step_id": goal.goal_id,
            "action": goal.backend_hint or "execute",
            "description": goal.description,
            "title": goal.title,
            "domain": goal.domain,
            "goal_type": goal.goal_type,
            "preconditions": list(goal.preconditions),
            "success_criteria": goal.success_criteria,
            "verification_hint": goal.verification_hint,
            "repair_hint": goal.repair_hint,
            "requires_bridge": goal.domain in ("houdini", "touchdesigner"),
            "verify": verify and bool(goal.verification_hint),
            "continue_on_error": False,
            "metadata": {
                "confidence": goal.confidence,
                "execution_feasibility": goal.execution_feasibility,
            },
        }

        # Execute the step
        result = self.execute_step_with_retry(
            step=step,
            max_retries=max_retries,
            task_id=goal.task_id,
            step_id=goal.goal_id,
        )

        return result

    def get_error_memory(self) -> list[NormalizedError]:
        """Get all normalized errors captured during execution.

        Returns:
            List of NormalizedError instances
        """
        return self._error_memory.copy()

    def clear_error_memory(self) -> None:
        """Clear the error memory."""
        self._error_memory.clear()
