"""Autonomous Loop Module.

Provides continuous self-directed execution cycles with configurable
autonomy levels, goal scheduling, execution, verification, and learning.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable

from app.agent_core.goal_generator import GoalGenerator, GoalGeneratorConfig
from app.agent_core.goal_models import (
    DomainHint,
    GoalArtifact,
    GoalGenerationMode,
    GoalGenerationResult,
    GoalRequest,
    GoalType,
)
from app.agent_core.goal_scheduler_bridge import (
    GoalSchedulerBridge,
    GoalStatus,
    ScheduledGoal,
    SchedulePriority,
    create_scheduler,
)
from app.agent_core.runtime_loop import IntegratedRuntimeLoop, RuntimeLoopResult
from app.evaluation.execution_verifier import ExecutionVerifier, VerifierConfig
from app.evaluation.screenshot_utils import take_screenshot
from app.evaluation.verification_models import (
    ExecutionVerificationReport,
    ExpectedState,
)


class AutonomyLevel(str, Enum):
    """Level of autonomous operation.

    Determines how much human oversight is required.
    """

    FULLY_AUTONOMOUS = "fully_autonomous"  # No human intervention
    SUPERVISED = "supervised"  # Human approval for critical actions
    ADVISORY = "advisory"  # Human reviews all actions
    MANUAL = "manual"  # Human triggers each action


class CycleState(str, Enum):
    """State of an execution cycle."""

    IDLE = "idle"
    GENERATING_GOALS = "generating_goals"
    SCHEDULING = "scheduling"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    LEARNING = "learning"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


class CyclePhase(str, Enum):
    """Phase within a cycle."""

    GOAL_SELECT = "goal_select"
    GOAL_GENERATE = "goal_generate"
    GOAL_SCHEDULE = "goal_schedule"
    GOAL_EXECUTE = "goal_execute"
    RESULT_VERIFY = "result_verify"
    RESULT_LEARN = "result_learn"
    CYCLE_COMPLETE = "cycle_complete"


@dataclass(slots=True)
class CycleResult:
    """Result of a single autonomous cycle.

    Captures all phases and outcomes of one execution cycle.
    """

    cycle_id: str
    started_at: str
    completed_at: str | None = None
    state: str = CycleState.IDLE.value
    phase: str = CyclePhase.GOAL_SELECT.value
    autonomy_level: str = AutonomyLevel.SUPERVISED.value

    # Goal generation phase
    goal_generation_performed: bool = False
    goal_generation_result: GoalGenerationResult | None = None
    generated_goals: list[GoalArtifact] = field(default_factory=list)

    # Scheduling phase
    scheduling_performed: bool = False
    scheduled_goals: list[ScheduledGoal] = field(default_factory=list)
    selected_goal: GoalArtifact | None = None

    # Execution phase
    execution_performed: bool = False
    execution_result: RuntimeLoopResult | None = None
    execution_success: bool = False

    # Verification phase
    verification_performed: bool = False
    verification_passed: bool = False
    verification_gaps: list[str] = field(default_factory=list)
    verification_report: ExecutionVerificationReport | None = None
    """Full verification report with evidence."""
    before_screenshot: str = ""
    """Path to screenshot before execution."""
    after_screenshot: str = ""
    """Path to screenshot after execution."""

    # Learning phase
    learning_performed: bool = False
    learning_insights: list[str] = field(default_factory=list)

    # Errors and context
    errors: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def success(self) -> bool:
        """Check if cycle completed successfully."""
        return (
            self.state != CycleState.ERROR.value
            and self.execution_success
            and (self.verification_passed or not self.verification_performed)
        )

    @property
    def execution_time_ms(self) -> float:
        """Calculate total cycle execution time."""
        if not self.completed_at or not self.started_at:
            return 0.0

        try:
            start = datetime.fromisoformat(self.started_at)
            end = datetime.fromisoformat(self.completed_at)
            return (end - start).total_seconds() * 1000
        except (ValueError, TypeError):
            return 0.0

    def add_error(self, error_type: str, message: str, details: dict[str, Any] | None = None) -> None:
        """Add an error to the cycle result."""
        self.errors.append({
            "error_type": error_type,
            "message": message,
            "details": details or {},
            "timestamp": datetime.now().isoformat(),
        })
        self.state = CycleState.ERROR.value

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "cycle_id": self.cycle_id,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "state": self.state,
            "phase": self.phase,
            "autonomy_level": self.autonomy_level,
            "goal_generation_performed": self.goal_generation_performed,
            "generated_goals_count": len(self.generated_goals),
            "scheduling_performed": self.scheduling_performed,
            "scheduled_goals_count": len(self.scheduled_goals),
            "execution_performed": self.execution_performed,
            "execution_success": self.execution_success,
            "verification_performed": self.verification_performed,
            "verification_passed": self.verification_passed,
            "learning_performed": self.learning_performed,
            "errors_count": len(self.errors),
            "warnings_count": len(self.warnings),
            "execution_time_ms": self.execution_time_ms,
            "success": self.success,
            "errors": self.errors,
            "warnings": self.warnings,
            "metadata": self.metadata,
        }


@dataclass
class AutonomousConfig:
    """Configuration for autonomous operation."""

    autonomy_level: str = AutonomyLevel.SUPERVISED.value
    domain: str = ""
    enable_memory: bool = True
    enable_checkpoints: bool = True
    enable_learning: bool = True
    enable_verification: bool = True
    max_cycles: int = 100
    cycle_delay_ms: int = 100  # Delay between cycles
    max_consecutive_failures: int = 3
    max_cycle_time_ms: int = 300000  # 5 minutes max per cycle
    checkpoint_interval: int = 10  # Checkpoint every N cycles

    # Approval callbacks for supervised mode
    require_goal_approval: bool = True
    require_execution_approval: bool = False

    # Post-execution verification settings
    enable_visual_verification: bool = True
    """Enable visual (screenshot) verification."""
    enable_state_verification: bool = True
    """Enable state query verification."""
    verification_min_confidence: float = 0.6
    """Minimum confidence required for verification to pass."""
    screenshot_delay_seconds: float = 1.0
    """Delay between action and screenshot capture."""


@dataclass
class LoopStatus:
    """Current status of the autonomous loop."""

    is_running: bool = False
    is_paused: bool = False
    current_cycle: int = 0
    current_state: str = CycleState.IDLE.value
    current_phase: str = CyclePhase.GOAL_SELECT.value
    total_goals_generated: int = 0
    total_goals_executed: int = 0
    total_goals_succeeded: int = 0
    total_goals_failed: int = 0
    consecutive_failures: int = 0
    started_at: str | None = None
    last_cycle_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "is_running": self.is_running,
            "is_paused": self.is_paused,
            "current_cycle": self.current_cycle,
            "current_state": self.current_state,
            "current_phase": self.current_phase,
            "total_goals_generated": self.total_goals_generated,
            "total_goals_executed": self.total_goals_executed,
            "total_goals_succeeded": self.total_goals_succeeded,
            "total_goals_failed": self.total_goals_failed,
            "consecutive_failures": self.consecutive_failures,
            "started_at": self.started_at,
            "last_cycle_at": self.last_cycle_at,
        }


class AutonomousLoop:
    """Continuous self-directed execution loop.

    The autonomous loop orchestrates:
    1. Goal generation and selection
    2. Goal scheduling with priority
    3. Runtime execution
    4. Result verification
    5. Learning and knowledge capture
    6. Cycle management and checkpointing

    Example:
        config = AutonomousConfig(
            domain="houdini",
            autonomy_level=AutonomyLevel.SUPERVISED.value,
        )
        loop = AutonomousLoop(config, repo_root="/path/to/repo")
        await loop.run_continuous()
    """

    def __init__(
        self,
        config: AutonomousConfig,
        repo_root: str,
        domain: str | None = None,
        goal_generator: GoalGenerator | None = None,
        scheduler: GoalSchedulerBridge | None = None,
    ):
        """Initialize the autonomous loop.

        Args:
            config: Autonomous configuration
            repo_root: Repository root for storage
            domain: Override domain from config
            goal_generator: Optional pre-configured goal generator
            scheduler: Optional pre-configured scheduler
        """
        self._config = config
        self._repo_root = repo_root
        self._domain = domain or config.domain

        # Core components
        self._goal_generator = goal_generator or GoalGenerator(
            repo_root=repo_root,
            config=GoalGeneratorConfig(
                enable_memory=config.enable_memory,
                enable_safety_checks=True,
                enable_ranking=True,
            ),
        )

        self._scheduler = scheduler or create_scheduler(
            repo_root=repo_root,
            domain=self._domain,
            enable_memory=config.enable_memory,
            enable_checkpoints=config.enable_checkpoints,
        )

        # State
        self._status = LoopStatus()
        self._current_cycle_result: CycleResult | None = None
        self._cycle_history: list[CycleResult] = []
        self._pause_requested = False
        self._stop_requested = False

        # Post-execution verification
        self._verifier: ExecutionVerifier | None = None
        if config.enable_verification:
            verifier_config = VerifierConfig(
                enable_visual=config.enable_visual_verification,
                enable_state_query=config.enable_state_verification,
                min_confidence_threshold=config.verification_min_confidence,
                screenshot_delay=config.screenshot_delay_seconds,
            )
            self._verifier = ExecutionVerifier(verifier_config)

    @property
    def config(self) -> AutonomousConfig:
        """Get the configuration."""
        return self._config

    @property
    def status(self) -> LoopStatus:
        """Get current status."""
        return self._status

    @property
    def scheduler(self) -> GoalSchedulerBridge:
        """Get the scheduler."""
        return self._scheduler

    @property
    def goal_generator(self) -> GoalGenerator:
        """Get the goal generator."""
        return self._goal_generator

    def set_callbacks(
        self,
        on_goal_generated: Callable[[GoalArtifact], bool] | None = None,
        on_before_execute: Callable[[ScheduledGoal], bool] | None = None,
        on_cycle_complete: Callable[[CycleResult], None] | None = None,
    ) -> None:
        """Set callback functions for supervised mode.

        Args:
            on_goal_generated: Called when a goal is generated, return True to approve
            on_before_execute: Called before execution, return True to approve
            on_cycle_complete: Called after each cycle completes
        """
        self._on_goal_generated = on_goal_generated
        self._on_before_execute = on_before_execute
        self._on_cycle_complete = on_cycle_complete

    def _generate_cycle_id(self) -> str:
        """Generate a unique cycle ID."""
        timestamp = int(time.time() * 1000)
        return f"cycle_{timestamp}_{self._status.current_cycle}"

    async def run_cycle(
        self,
        task_summary: str = "",
        task_id: str = "",
        session_id: str = "",
        context: dict[str, Any] | None = None,
    ) -> CycleResult:
        """Run a single execution cycle.

        A cycle consists of:
        1. Goal generation/selection
        2. Scheduling
        3. Execution
        4. Verification
        5. Learning

        Args:
            task_summary: Task description for goal generation
            task_id: Task ID for tracking
            session_id: Session ID for tracking
            context: Additional context for goal generation

        Returns:
            CycleResult with all phase details
        """
        cycle_id = self._generate_cycle_id()
        result = CycleResult(
            cycle_id=cycle_id,
            started_at=datetime.now().isoformat(),
            state=CycleState.GENERATING_GOALS.value,
            phase=CyclePhase.GOAL_GENERATE.value,
            autonomy_level=self._config.autonomy_level,
        )

        self._current_cycle_result = result
        self._status.current_state = CycleState.GENERATING_GOALS.value
        self._status.current_phase = CyclePhase.GOAL_GENERATE.value

        try:
            # Phase 1: Goal Generation
            goal_result = await self._generate_goals_phase(
                task_summary=task_summary,
                task_id=task_id or f"task_{cycle_id}",
                session_id=session_id or f"session_{cycle_id}",
                context=context,
            )

            result.goal_generation_performed = True
            result.goal_generation_result = goal_result
            result.generated_goals = goal_result.generated_goals

            if not goal_result.has_goals:
                result.state = CycleState.IDLE.value
                result.phase = CyclePhase.CYCLE_COMPLETE.value
                result.completed_at = datetime.now().isoformat()
                result.warnings.append("No goals generated")
                return result

            self._status.total_goals_generated += len(goal_result.generated_goals)

            # Phase 2: Goal Selection and Approval
            selected_goal = goal_result.primary_goal
            if selected_goal and self._config.require_goal_approval:
                if self._on_goal_generated and not self._on_goal_generated(selected_goal):
                    result.warnings.append(f"Goal {selected_goal.goal_id} not approved")
                    selected_goal = None

            if not selected_goal:
                result.state = CycleState.IDLE.value
                result.phase = CyclePhase.CYCLE_COMPLETE.value
                result.completed_at = datetime.now().isoformat()
                result.warnings.append("No goal selected for execution")
                return result

            result.selected_goal = selected_goal
            result.state = CycleState.SCHEDULING.value
            result.phase = CyclePhase.GOAL_SCHEDULE.value
            self._status.current_state = CycleState.SCHEDULING.value
            self._status.current_phase = CyclePhase.GOAL_SCHEDULE.value

            # Phase 3: Scheduling
            scheduled = await self._schedule_goal_phase(selected_goal)
            result.scheduling_performed = True
            result.scheduled_goals = [scheduled]

            # Phase 4: Execution
            result.state = CycleState.EXECUTING.value
            result.phase = CyclePhase.GOAL_EXECUTE.value
            self._status.current_state = CycleState.EXECUTING.value
            self._status.current_phase = CyclePhase.GOAL_EXECUTE.value

            # Check for execution approval in supervised mode
            if self._config.require_execution_approval:
                if self._on_before_execute and not self._on_before_execute(scheduled):
                    result.warnings.append("Execution not approved")
                    result.execution_performed = False
                    result.state = CycleState.IDLE.value
                    result.completed_at = datetime.now().isoformat()
                    return result

            execution_result, before_screenshot, after_screenshot = await self._execute_goal_phase(scheduled)
            result.execution_performed = True
            result.execution_result = execution_result
            result.execution_success = execution_result.success
            result.before_screenshot = before_screenshot
            result.after_screenshot = after_screenshot

            self._status.total_goals_executed += 1
            if execution_result.success:
                self._status.total_goals_succeeded += 1
                self._status.consecutive_failures = 0
            else:
                self._status.total_goals_failed += 1
                self._status.consecutive_failures += 1

            # Phase 5: Verification
            if self._config.enable_verification:
                result.state = CycleState.VERIFYING.value
                result.phase = CyclePhase.RESULT_VERIFY.value
                self._status.current_state = CycleState.VERIFYING.value

                verification_result = await self._verify_result_phase(
                    scheduled, execution_result, before_screenshot, after_screenshot
                )
                result.verification_performed = True
                result.verification_passed = verification_result.get("passed", False)
                result.verification_gaps = verification_result.get("gaps", [])
                result.verification_report = verification_result.get("report")

                # Update execution success based on verification
                if not result.verification_passed:
                    result.execution_success = False
                    self._status.total_goals_succeeded -= 1
                    self._status.total_goals_failed += 1
                    self._status.consecutive_failures += 1

            # Phase 6: Learning
            if self._config.enable_learning:
                result.state = CycleState.LEARNING.value
                result.phase = CyclePhase.RESULT_LEARN.value
                self._status.current_state = CycleState.LEARNING.value

                learning_result = await self._learn_phase(scheduled, execution_result)
                result.learning_performed = True
                result.learning_insights = learning_result.get("insights", [])

            # Complete cycle
            result.state = CycleState.IDLE.value
            result.phase = CyclePhase.CYCLE_COMPLETE.value
            result.completed_at = datetime.now().isoformat()

        except Exception as e:
            result.add_error(
                error_type="cycle_error",
                message=str(e),
                details={"phase": result.phase},
            )

        finally:
            self._current_cycle_result = None
            self._cycle_history.append(result)
            self._status.current_cycle += 1
            self._status.last_cycle_at = datetime.now().isoformat()

            # Call cycle complete callback
            if self._on_cycle_complete:
                self._on_cycle_complete(result)

        return result

    async def run_continuous(
        self,
        initial_task: str = "",
        task_id: str = "",
        session_id: str = "",
    ) -> None:
        """Run continuous autonomous execution cycles.

        Runs cycles until stopped, max cycles reached, or too many failures.

        Args:
            initial_task: Initial task to start with
            task_id: Task ID for tracking
            session_id: Session ID for tracking
        """
        self._status.is_running = True
        self._status.started_at = datetime.now().isoformat()
        self._stop_requested = False
        self._pause_requested = False

        cycle_count = 0
        current_task = initial_task

        while (
            not self._stop_requested
            and cycle_count < self._config.max_cycles
            and self._status.consecutive_failures < self._config.max_consecutive_failures
        ):
            # Handle pause
            while self._pause_requested and not self._stop_requested:
                self._status.is_paused = True
                await asyncio.sleep(0.1)

            self._status.is_paused = False

            if self._stop_requested:
                break

            # Run a cycle
            result = await self.run_cycle(
                task_summary=current_task,
                task_id=task_id,
                session_id=session_id,
            )

            cycle_count += 1

            # Update task from result for next cycle
            if result.selected_goal:
                current_task = result.selected_goal.description

            # Checkpoint at intervals
            if (
                self._config.enable_checkpoints
                and cycle_count % self._config.checkpoint_interval == 0
            ):
                await self._create_checkpoint()

            # Delay between cycles
            if self._config.cycle_delay_ms > 0:
                await asyncio.sleep(self._config.cycle_delay_ms / 1000.0)

        self._status.is_running = False
        self._status.current_state = CycleState.STOPPED.value

    def pause(self) -> None:
        """Request a pause of the autonomous loop."""
        self._pause_requested = True

    def resume(self) -> None:
        """Resume from a paused state."""
        self._pause_requested = False

    def stop(self) -> None:
        """Request a stop of the autonomous loop."""
        self._stop_requested = True

    async def resume_from_checkpoint(self, checkpoint_id: str) -> bool:
        """Resume execution from a checkpoint.

        Args:
            checkpoint_id: ID of checkpoint to resume from

        Returns:
            True if resume was successful
        """
        if not self._scheduler.runtime_loop:
            return False

        try:
            result = self._scheduler.runtime_loop.attempt_resume(
                force_checkpoint_id=checkpoint_id
            )
            return result is not None and result.success
        except Exception:
            return False

    def get_cycle_history(self, limit: int = 10) -> list[CycleResult]:
        """Get recent cycle history.

        Args:
            limit: Maximum number of results to return

        Returns:
            List of CycleResult instances
        """
        return self._cycle_history[-limit:]

    # Phase implementations

    async def _generate_goals_phase(
        self,
        task_summary: str,
        task_id: str,
        session_id: str,
        context: dict[str, Any] | None = None,
    ) -> GoalGenerationResult:
        """Generate goals for the cycle."""
        context = context or {}

        request = GoalRequest.create(
            task_id=task_id,
            session_id=session_id,
            domain_hint=self._domain or DomainHint.UNKNOWN.value,
            raw_task_summary=task_summary,
            memory_summary=context.get("memory_summary", {}),
            failure_context=context.get("failure_context", {}),
            checkpoint_summary=context.get("checkpoint_summary", {}),
            goal_generation_mode=context.get("goal_generation_mode", GoalGenerationMode.ROOT_GOAL.value),
        )

        return self._goal_generator.generate_goals(request)

    async def _schedule_goal_phase(self, goal: GoalArtifact) -> ScheduledGoal:
        """Schedule a goal for execution."""
        priority = self._scheduler.calculate_priority(goal)
        return self._scheduler.schedule_goal(goal, priority=priority)

    async def _execute_goal_phase(
        self,
        scheduled: ScheduledGoal,
    ) -> tuple[RuntimeLoopResult, str, str]:
        """Execute a scheduled goal with screenshot capture.

        Args:
            scheduled: Scheduled goal to execute

        Returns:
            Tuple of (execution result, before screenshot path, after screenshot path)
        """
        # Capture before screenshot if verification enabled
        before_screenshot = ""
        after_screenshot = ""

        if self._config.enable_verification and self._verifier:
            before_screenshot = take_screenshot(
                app=self._domain or "generic",
                label="before",
                output_dir=f"data/screenshots/{self._domain or 'generic'}",
            )

        # Execute the goal
        execution_result = self._scheduler.execute_goal(scheduled)

        # Capture after screenshot if verification enabled
        if self._config.enable_verification and self._verifier:
            import asyncio
            await asyncio.sleep(self._config.screenshot_delay_seconds)
            after_screenshot = take_screenshot(
                app=self._domain or "generic",
                label="after",
                output_dir=f"data/screenshots/{self._domain or 'generic'}",
            )

        return execution_result, before_screenshot, after_screenshot

    async def _verify_result_phase(
        self,
        scheduled: ScheduledGoal,
        execution_result: RuntimeLoopResult,
        before_screenshot: str = "",
        after_screenshot: str = "",
    ) -> dict[str, Any]:
        """Verify execution result using post-execution verification pipeline.

        Performs comprehensive verification including:
        - Visual verification (screenshot comparison)
        - State query verification (direct application queries)
        - Evidence collection
        - Confidence scoring

        Args:
            scheduled: The scheduled goal that was executed
            execution_result: The result of execution
            before_screenshot: Path to screenshot before execution
            after_screenshot: Path to screenshot after execution

        Returns:
            Verification result with 'passed', 'gaps', 'report' keys
        """
        result: dict[str, Any] = {
            "passed": False,
            "gaps": [],
            "confidence": 0.0,
            "report": None,
        }

        goal = scheduled.goal_artifact

        # Use new verification pipeline if verifier is available
        if self._verifier:
            # Infer expected state from goal and action
            expected_state = self._infer_expected_state_from_goal(goal)

            # Build action description
            action = goal.backend_hint or goal.description

            try:
                verification_report = self._verifier.verify_execution(
                    action=action,
                    before_screenshot=before_screenshot if before_screenshot else None,
                    after_screenshot=after_screenshot if after_screenshot else None,
                    expected_state=expected_state,
                    app=self._domain or "generic",
                    context={
                        "goal_id": goal.goal_id,
                        "task_id": goal.task_id,
                        "execution_success": execution_result.success,
                    },
                )

                result["passed"] = verification_report.overall_success
                result["confidence"] = verification_report.confidence
                result["report"] = verification_report
                result["gaps"] = [
                    f"{a.get('type', 'assertion')}: {a.get('target', 'unknown')} - "
                    f"expected {a.get('expected')}, got {a.get('actual')}"
                    for a in verification_report.all_assertions_failed
                ]

                # Add recommendations as gaps if verification failed
                if not result["passed"] and verification_report.recommendations:
                    result["gaps"].extend(verification_report.recommendations)

            except Exception as e:
                result["gaps"].append(f"Verification pipeline error: {str(e)}")
                # Fall back to basic verification
                result["passed"] = execution_result.success
                result["confidence"] = 0.8 if execution_result.success else 0.3

        else:
            # Fallback to basic verification
            # Check success criteria
            if goal.success_criteria:
                for criterion, expected in goal.success_criteria.items():
                    if execution_result.success:
                        result["passed"] = True
                    else:
                        result["gaps"].append(f"Criterion not met: {criterion}")

            # Use verification hint if available
            if goal.verification_hint:
                result["gaps"].append(f"Verification hint: {goal.verification_hint}")

            # If no specific criteria, pass based on execution success
            if not goal.success_criteria:
                result["passed"] = execution_result.success

            result["confidence"] = 0.8 if result["passed"] else 0.3

        return result

    def _infer_expected_state_from_goal(self, goal: GoalArtifact) -> ExpectedState:
        """Infer expected state from goal artifact.

        Args:
            goal: Goal artifact

        Returns:
            ExpectedState inferred from goal
        """
        expected = ExpectedState()

        # Use verifier's inference if available
        if self._verifier:
            expected = self._verifier.infer_expected_state(
                action=goal.backend_hint or goal.description,
                goal_description=goal.description,
            )

        # Override with goal's success criteria if available
        if goal.success_criteria:
            for criterion, value in goal.success_criteria.items():
                # Try to interpret criterion
                if "node" in criterion.lower() or "count" in criterion.lower():
                    try:
                        expected.node_count = int(value)
                    except (ValueError, TypeError):
                        pass
                elif "parameter" in criterion.lower() or "." in criterion:
                    expected.parameter_values[criterion] = value
                elif "visible" in criterion.lower():
                    if isinstance(value, list):
                        expected.new_elements_visible.extend(value)
                    else:
                        expected.new_elements_visible.append(str(value))

        # Use verification hint
        if goal.verification_hint:
            # Parse verification hint for additional expectations
            if "dialog" in goal.verification_hint.lower():
                if "close" in goal.verification_hint.lower():
                    expected.dialog_open = None
                elif "open" in goal.verification_hint.lower():
                    # Try to extract dialog name
                    import re
                    match = re.search(r'open\s+(\w+)', goal.verification_hint, re.IGNORECASE)
                    if match:
                        expected.dialog_open = match.group(1)

        return expected

    async def _learn_phase(
        self,
        scheduled: ScheduledGoal,
        execution_result: RuntimeLoopResult,
    ) -> dict[str, Any]:
        """Learn from execution result.

        Args:
            scheduled: The scheduled goal that was executed
            execution_result: The result of execution

        Returns:
            Learning result with insights
        """
        insights: list[str] = []

        # Extract patterns from successful execution
        if execution_result.success:
            if execution_result.memory_items_used > 0:
                insights.append(
                    f"Used {execution_result.memory_items_used} memory patterns"
                )

            if execution_result.learning_goals_generated:
                insights.append(
                    f"Generated {execution_result.learning_goal_count} learning goals"
                )

        # Extract patterns from failed execution
        else:
            if execution_result.normalized_errors:
                for error in execution_result.normalized_errors[:3]:
                    insights.append(f"Error pattern: {error.get('type', 'unknown')}")

        # Record learning insights
        if self._config.enable_memory and insights:
            # Would save to memory store here
            pass

        return {
            "insights": insights,
            "memory_updated": execution_result.memory_writeback_done,
        }

    async def _create_checkpoint(self) -> str | None:
        """Create a checkpoint of current state.

        Returns:
            Checkpoint ID or None if failed
        """
        if not self._scheduler.runtime_loop:
            return None

        try:
            checkpoint = self._scheduler.runtime_loop.create_checkpoint(
                current_goal=f"Autonomous cycle {self._status.current_cycle}",
                reason="autonomous_checkpoint",
            )

            if checkpoint and self._scheduler.runtime_loop.save_checkpoint():
                return checkpoint.checkpoint_id

        except Exception:
            pass

        return None


def create_autonomous_loop(
    repo_root: str,
    domain: str = "",
    autonomy_level: str = AutonomyLevel.SUPERVISED.value,
    enable_memory: bool = True,
    enable_checkpoints: bool = True,
    enable_learning: bool = True,
    enable_verification: bool = True,
    enable_visual_verification: bool = True,
    enable_state_verification: bool = True,
    verification_min_confidence: float = 0.6,
    screenshot_delay_seconds: float = 1.0,
) -> AutonomousLoop:
    """Create a configured autonomous loop.

    Args:
        repo_root: Repository root
        domain: Execution domain
        autonomy_level: Level of autonomy
        enable_memory: Enable memory integration
        enable_checkpoints: Enable checkpoint support
        enable_learning: Enable learning from execution
        enable_verification: Enable result verification
        enable_visual_verification: Enable visual (screenshot) verification
        enable_state_verification: Enable state query verification
        verification_min_confidence: Minimum confidence for verification to pass
        screenshot_delay_seconds: Delay between action and screenshot

    Returns:
        Configured AutonomousLoop
    """
    config = AutonomousConfig(
        autonomy_level=autonomy_level,
        domain=domain,
        enable_memory=enable_memory,
        enable_checkpoints=enable_checkpoints,
        enable_learning=enable_learning,
        enable_verification=enable_verification,
        enable_visual_verification=enable_visual_verification,
        enable_state_verification=enable_state_verification,
        verification_min_confidence=verification_min_confidence,
        screenshot_delay_seconds=screenshot_delay_seconds,
    )

    return AutonomousLoop(config=config, repo_root=repo_root)