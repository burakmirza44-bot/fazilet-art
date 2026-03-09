"""Checkpoint Module.

Provides structured checkpoint data models for persisting execution state,
enabling resume and recovery for long-horizon plans and tasks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class CheckpointStatus(str, Enum):
    """Status of a checkpoint."""

    ACTIVE = "active"  # Checkpoint is current and valid
    STALE = "stale"  # Checkpoint exists but may be outdated
    CORRUPT = "corrupt"  # Checkpoint data is invalid
    COMPLETED = "completed"  # Plan completed, checkpoint archived
    FAILED = "failed"  # Plan failed, checkpoint retained for analysis


class StepStatus(str, Enum):
    """Status of a step within a checkpoint."""

    PENDING = "pending"  # Step not yet started
    IN_PROGRESS = "in_progress"  # Step currently executing
    COMPLETED = "completed"  # Step completed successfully
    COMPLETED_VERIFIED = "completed_verified"  # Step completed and verified
    FAILED = "failed"  # Step failed
    FAILED_RECOVERABLE = "failed_recoverable"  # Step failed but can retry
    SKIPPED = "skipped"  # Step skipped per policy


@dataclass(slots=True)
class StepState:
    """State of a single step in a plan.

    Tracks execution status, verification state, and metadata
    for individual steps within a larger plan.
    """

    step_id: str
    status: StepStatus = StepStatus.PENDING
    description: str = ""
    action: str = ""
    params: dict[str, Any] = field(default_factory=dict)
    started_at: str | None = None
    completed_at: str | None = None
    verified: bool = False
    verification_result: dict[str, Any] | None = None
    retry_count: int = 0
    max_retries: int = 3
    error: dict[str, Any] | None = None
    output: dict[str, Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "step_id": self.step_id,
            "status": self.status.value,
            "description": self.description,
            "action": self.action,
            "params": self.params,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "verified": self.verified,
            "verification_result": self.verification_result,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "error": self.error,
            "output": self.output,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StepState":
        """Create StepState from dictionary."""
        return cls(
            step_id=data["step_id"],
            status=StepStatus(data.get("status", "pending")),
            description=data.get("description", ""),
            action=data.get("action", ""),
            params=data.get("params", {}),
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
            verified=data.get("verified", False),
            verification_result=data.get("verification_result"),
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 3),
            error=data.get("error"),
            output=data.get("output"),
            metadata=data.get("metadata", {}),
        )

    def mark_started(self) -> None:
        """Mark step as started."""
        self.status = StepStatus.IN_PROGRESS
        self.started_at = datetime.now().isoformat()

    def mark_completed(self, verified: bool = False) -> None:
        """Mark step as completed."""
        self.status = StepStatus.COMPLETED_VERIFIED if verified else StepStatus.COMPLETED
        self.completed_at = datetime.now().isoformat()
        self.verified = verified

    def mark_failed(self, error: dict[str, Any] | None = None, recoverable: bool = False) -> None:
        """Mark step as failed."""
        self.status = StepStatus.FAILED_RECOVERABLE if recoverable else StepStatus.FAILED
        self.error = error
        self.retry_count += 1

    def can_retry(self) -> bool:
        """Check if step can be retried."""
        return self.retry_count < self.max_retries and self.status == StepStatus.FAILED_RECOVERABLE


@dataclass(slots=True)
class SubgoalState:
    """State of a subgoal within a plan.

    Tracks progress through subgoals which group related steps.
    """

    subgoal_id: str
    description: str = ""
    status: StepStatus = StepStatus.PENDING
    steps: dict[str, StepState] = field(default_factory=dict)
    step_order: list[str] = field(default_factory=list)
    started_at: str | None = None
    completed_at: str | None = None
    parent_subgoal_id: str | None = None
    child_subgoal_ids: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "subgoal_id": self.subgoal_id,
            "description": self.description,
            "status": self.status.value,
            "steps": {k: v.to_dict() for k, v in self.steps.items()},
            "step_order": self.step_order,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "parent_subgoal_id": self.parent_subgoal_id,
            "child_subgoal_ids": self.child_subgoal_ids,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SubgoalState":
        """Create SubgoalState from dictionary."""
        return cls(
            subgoal_id=data["subgoal_id"],
            description=data.get("description", ""),
            status=StepStatus(data.get("status", "pending")),
            steps={k: StepState.from_dict(v) for k, v in data.get("steps", {}).items()},
            step_order=data.get("step_order", []),
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
            parent_subgoal_id=data.get("parent_subgoal_id"),
            child_subgoal_ids=data.get("child_subgoal_ids", []),
            metadata=data.get("metadata", {}),
        )

    def get_active_step(self) -> StepState | None:
        """Get the currently active step in this subgoal."""
        for step_id in self.step_order:
            step = self.steps.get(step_id)
            if step and step.status in (StepStatus.IN_PROGRESS, StepStatus.PENDING):
                return step
            if step and step.status in (StepStatus.FAILED, StepStatus.FAILED_RECOVERABLE):
                if step.can_retry():
                    return step
        return None

    def get_progress(self) -> tuple[int, int]:
        """Get completion progress as (completed, total)."""
        completed = sum(
            1 for step_id in self.step_order
            if self.steps.get(step_id)
            and self.steps[step_id].status in (StepStatus.COMPLETED, StepStatus.COMPLETED_VERIFIED, StepStatus.SKIPPED)
        )
        return completed, len(self.step_order)


@dataclass(slots=True)
class RetryState:
    """State for retry management.

    Tracks retry budgets and strategies for failed operations.
    """

    retry_count: int = 0
    max_retries: int = 3
    backoff_strategy: str = "exponential"  # exponential, linear, fixed
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 60.0
    last_retry_at: str | None = None
    retry_reasons: list[str] = field(default_factory=list)
    cumulative_delay_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "backoff_strategy": self.backoff_strategy,
            "base_delay_seconds": self.base_delay_seconds,
            "max_delay_seconds": self.max_delay_seconds,
            "last_retry_at": self.last_retry_at,
            "retry_reasons": self.retry_reasons,
            "cumulative_delay_seconds": self.cumulative_delay_seconds,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RetryState":
        """Create RetryState from dictionary."""
        return cls(
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 3),
            backoff_strategy=data.get("backoff_strategy", "exponential"),
            base_delay_seconds=data.get("base_delay_seconds", 1.0),
            max_delay_seconds=data.get("max_delay_seconds", 60.0),
            last_retry_at=data.get("last_retry_at"),
            retry_reasons=data.get("retry_reasons", []),
            cumulative_delay_seconds=data.get("cumulative_delay_seconds", 0.0),
        )

    def can_retry(self) -> bool:
        """Check if another retry is allowed."""
        return self.retry_count < self.max_retries

    def record_retry(self, reason: str) -> None:
        """Record a retry attempt."""
        self.retry_count += 1
        self.last_retry_at = datetime.now().isoformat()
        self.retry_reasons.append(reason)
        # Calculate delay
        if self.backoff_strategy == "exponential":
            delay = self.base_delay_seconds * (2 ** (self.retry_count - 1))
        elif self.backoff_strategy == "linear":
            delay = self.base_delay_seconds * self.retry_count
        else:  # fixed
            delay = self.base_delay_seconds
        self.cumulative_delay_seconds += min(delay, self.max_delay_seconds)

    def get_next_delay(self) -> float:
        """Get the delay for the next retry."""
        if self.backoff_strategy == "exponential":
            delay = self.base_delay_seconds * (2 ** self.retry_count)
        elif self.backoff_strategy == "linear":
            delay = self.base_delay_seconds * (self.retry_count + 1)
        else:  # fixed
            delay = self.base_delay_seconds
        return min(delay, self.max_delay_seconds)


@dataclass(slots=True)
class RepairState:
    """State for repair operations.

    Tracks repair attempts and strategies for fixing failed operations.
    """

    repair_count: int = 0
    max_repairs: int = 2
    repair_strategies_attempted: list[str] = field(default_factory=list)
    current_strategy: str | None = None
    last_repair_at: str | None = None
    successful_repairs: list[dict[str, Any]] = field(default_factory=list)
    failed_repairs: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "repair_count": self.repair_count,
            "max_repairs": self.max_repairs,
            "repair_strategies_attempted": self.repair_strategies_attempted,
            "current_strategy": self.current_strategy,
            "last_repair_at": self.last_repair_at,
            "successful_repairs": self.successful_repairs,
            "failed_repairs": self.failed_repairs,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RepairState":
        """Create RepairState from dictionary."""
        return cls(
            repair_count=data.get("repair_count", 0),
            max_repairs=data.get("max_repairs", 2),
            repair_strategies_attempted=data.get("repair_strategies_attempted", []),
            current_strategy=data.get("current_strategy"),
            last_repair_at=data.get("last_repair_at"),
            successful_repairs=data.get("successful_repairs", []),
            failed_repairs=data.get("failed_repairs", []),
        )

    def can_repair(self) -> bool:
        """Check if another repair attempt is allowed."""
        return self.repair_count < self.max_repairs

    def start_repair(self, strategy: str) -> None:
        """Start a repair attempt with a strategy."""
        self.repair_count += 1
        self.current_strategy = strategy
        self.repair_strategies_attempted.append(strategy)
        self.last_repair_at = datetime.now().isoformat()

    def record_success(self, details: dict[str, Any]) -> None:
        """Record a successful repair."""
        self.successful_repairs.append({
            "strategy": self.current_strategy,
            "timestamp": datetime.now().isoformat(),
            "details": details,
        })
        self.current_strategy = None

    def record_failure(self, details: dict[str, Any]) -> None:
        """Record a failed repair."""
        self.failed_repairs.append({
            "strategy": self.current_strategy,
            "timestamp": datetime.now().isoformat(),
            "details": details,
        })
        self.current_strategy = None


@dataclass(slots=True)
class BridgeHealthSummary:
    """Summary of bridge health at checkpoint time."""

    bridge_type: str = ""
    bridge_enabled: bool = False
    bridge_reachable: bool = False
    ping_ok: bool = False
    latency_ms: float = 0.0
    last_error_code: str = ""
    last_error_message: str = ""
    degraded: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "bridge_type": self.bridge_type,
            "bridge_enabled": self.bridge_enabled,
            "bridge_reachable": self.bridge_reachable,
            "ping_ok": self.ping_ok,
            "latency_ms": self.latency_ms,
            "last_error_code": self.last_error_code,
            "last_error_message": self.last_error_message,
            "degraded": self.degraded,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BridgeHealthSummary":
        """Create BridgeHealthSummary from dictionary."""
        return cls(
            bridge_type=data.get("bridge_type", ""),
            bridge_enabled=data.get("bridge_enabled", False),
            bridge_reachable=data.get("bridge_reachable", False),
            ping_ok=data.get("ping_ok", False),
            latency_ms=data.get("latency_ms", 0.0),
            last_error_code=data.get("last_error_code", ""),
            last_error_message=data.get("last_error_message", ""),
            degraded=data.get("degraded", False),
        )


@dataclass(slots=True)
class VerificationSummary:
    """Summary of verification state at checkpoint time."""

    verification_enabled: bool = False
    last_verification_at: str | None = None
    verified_steps_count: int = 0
    unverified_steps_count: int = 0
    verification_failures: list[dict[str, Any]] = field(default_factory=list)
    verification_method: str = ""  # e.g., "screenshot", "state_check", "manual"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "verification_enabled": self.verification_enabled,
            "last_verification_at": self.last_verification_at,
            "verified_steps_count": self.verified_steps_count,
            "unverified_steps_count": self.unverified_steps_count,
            "verification_failures": self.verification_failures,
            "verification_method": self.verification_method,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VerificationSummary":
        """Create VerificationSummary from dictionary."""
        return cls(
            verification_enabled=data.get("verification_enabled", False),
            last_verification_at=data.get("last_verification_at"),
            verified_steps_count=data.get("verified_steps_count", 0),
            unverified_steps_count=data.get("unverified_steps_count", 0),
            verification_failures=data.get("verification_failures", []),
            verification_method=data.get("verification_method", ""),
        )


@dataclass(slots=True)
class MemoryContextSummary:
    """Summary of memory context at checkpoint time."""

    memory_influenced: bool = False
    success_patterns_used: int = 0
    failure_patterns_used: int = 0
    repair_patterns_used: int = 0
    recent_session_ids: list[str] = field(default_factory=list)
    memory_writeback_enabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "memory_influenced": self.memory_influenced,
            "success_patterns_used": self.success_patterns_used,
            "failure_patterns_used": self.failure_patterns_used,
            "repair_patterns_used": self.repair_patterns_used,
            "recent_session_ids": self.recent_session_ids,
            "memory_writeback_enabled": self.memory_writeback_enabled,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MemoryContextSummary":
        """Create MemoryContextSummary from dictionary."""
        return cls(
            memory_influenced=data.get("memory_influenced", False),
            success_patterns_used=data.get("success_patterns_used", 0),
            failure_patterns_used=data.get("failure_patterns_used", 0),
            repair_patterns_used=data.get("repair_patterns_used", 0),
            recent_session_ids=data.get("recent_session_ids", []),
            memory_writeback_enabled=data.get("memory_writeback_enabled", True),
        )


@dataclass(slots=True)
class ExecutionBackendSummary:
    """Summary of execution backend state at checkpoint time."""

    backend_type: str = ""  # bridge, ui, direct_api, dry_run
    backend_selected_at: str | None = None
    fallback_used: bool = False
    dry_run_mode: bool = False
    safety_checks_passed: bool = True
    killswitch_active: bool = False
    window_focus_correct: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "backend_type": self.backend_type,
            "backend_selected_at": self.backend_selected_at,
            "fallback_used": self.fallback_used,
            "dry_run_mode": self.dry_run_mode,
            "safety_checks_passed": self.safety_checks_passed,
            "killswitch_active": self.killswitch_active,
            "window_focus_correct": self.window_focus_correct,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExecutionBackendSummary":
        """Create ExecutionBackendSummary from dictionary."""
        return cls(
            backend_type=data.get("backend_type", ""),
            backend_selected_at=data.get("backend_selected_at"),
            fallback_used=data.get("fallback_used", False),
            dry_run_mode=data.get("dry_run_mode", False),
            safety_checks_passed=data.get("safety_checks_passed", True),
            killswitch_active=data.get("killswitch_active", False),
            window_focus_correct=data.get("window_focus_correct", True),
        )


@dataclass(slots=True)
class Checkpoint:
    """Complete checkpoint for plan execution state.

    Captures all state needed to resume a plan execution from a
    known safe point, including step progress, retry/repair state,
    and contextual summaries.
    """

    # Identification
    checkpoint_id: str
    task_id: str
    session_id: str
    plan_id: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    # Versioning
    checkpoint_version: str = "1.0.0"
    schema_version: str = "1.0.0"

    # Domain and Goal
    domain: str = ""  # touchdesigner, houdini, etc.
    current_goal: str = ""
    current_subgoal_id: str | None = None

    # Step Tracking
    steps: dict[str, StepState] = field(default_factory=dict)
    step_order: list[str] = field(default_factory=list)
    subgoals: dict[str, SubgoalState] = field(default_factory=dict)
    subgoal_order: list[str] = field(default_factory=list)

    # State Management
    active_step_id: str | None = None
    completed_step_ids: list[str] = field(default_factory=list)
    pending_step_ids: list[str] = field(default_factory=list)
    failed_step_ids: list[str] = field(default_factory=list)

    # Retry and Repair
    retry_state: dict[str, RetryState] = field(default_factory=dict)
    repair_state: dict[str, RepairState] = field(default_factory=dict)
    global_retry_state: RetryState = field(default_factory=RetryState)
    global_repair_state: RepairState = field(default_factory=RepairState)

    # Summaries
    execution_backend_summary: ExecutionBackendSummary = field(default_factory=ExecutionBackendSummary)
    bridge_health_summary: BridgeHealthSummary | None = None
    verification_summary: VerificationSummary = field(default_factory=VerificationSummary)
    memory_context_summary: MemoryContextSummary = field(default_factory=MemoryContextSummary)

    # Status
    status: CheckpointStatus = CheckpointStatus.ACTIVE
    last_runtime_status: str = "unknown"
    resume_possible: bool = True
    resume_blocked_reason: str | None = None

    # Metadata
    checkpoint_reason: str = ""  # Why was this checkpoint created
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert checkpoint to dictionary for serialization."""
        return {
            # Identification
            "checkpoint_id": self.checkpoint_id,
            "task_id": self.task_id,
            "session_id": self.session_id,
            "plan_id": self.plan_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            # Versioning
            "checkpoint_version": self.checkpoint_version,
            "schema_version": self.schema_version,
            # Domain and Goal
            "domain": self.domain,
            "current_goal": self.current_goal,
            "current_subgoal_id": self.current_subgoal_id,
            # Step Tracking
            "steps": {k: v.to_dict() for k, v in self.steps.items()},
            "step_order": self.step_order,
            "subgoals": {k: v.to_dict() for k, v in self.subgoals.items()},
            "subgoal_order": self.subgoal_order,
            # State Management
            "active_step_id": self.active_step_id,
            "completed_step_ids": self.completed_step_ids,
            "pending_step_ids": self.pending_step_ids,
            "failed_step_ids": self.failed_step_ids,
            # Retry and Repair
            "retry_state": {k: v.to_dict() for k, v in self.retry_state.items()},
            "repair_state": {k: v.to_dict() for k, v in self.repair_state.items()},
            "global_retry_state": self.global_retry_state.to_dict(),
            "global_repair_state": self.global_repair_state.to_dict(),
            # Summaries
            "execution_backend_summary": self.execution_backend_summary.to_dict(),
            "bridge_health_summary": self.bridge_health_summary.to_dict() if self.bridge_health_summary else None,
            "verification_summary": self.verification_summary.to_dict(),
            "memory_context_summary": self.memory_context_summary.to_dict(),
            # Status
            "status": self.status.value,
            "last_runtime_status": self.last_runtime_status,
            "resume_possible": self.resume_possible,
            "resume_blocked_reason": self.resume_blocked_reason,
            # Metadata
            "checkpoint_reason": self.checkpoint_reason,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Checkpoint":
        """Create Checkpoint from dictionary."""
        checkpoint = cls(
            # Identification
            checkpoint_id=data["checkpoint_id"],
            task_id=data["task_id"],
            session_id=data["session_id"],
            plan_id=data["plan_id"],
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
            # Versioning
            checkpoint_version=data.get("checkpoint_version", "1.0.0"),
            schema_version=data.get("schema_version", "1.0.0"),
            # Domain and Goal
            domain=data.get("domain", ""),
            current_goal=data.get("current_goal", ""),
            current_subgoal_id=data.get("current_subgoal_id"),
            # Step Tracking
            steps={k: StepState.from_dict(v) for k, v in data.get("steps", {}).items()},
            step_order=data.get("step_order", []),
            subgoals={k: SubgoalState.from_dict(v) for k, v in data.get("subgoals", {}).items()},
            subgoal_order=data.get("subgoal_order", []),
            # State Management
            active_step_id=data.get("active_step_id"),
            completed_step_ids=data.get("completed_step_ids", []),
            pending_step_ids=data.get("pending_step_ids", []),
            failed_step_ids=data.get("failed_step_ids", []),
            # Retry and Repair
            retry_state={k: RetryState.from_dict(v) for k, v in data.get("retry_state", {}).items()},
            repair_state={k: RepairState.from_dict(v) for k, v in data.get("repair_state", {}).items()},
            global_retry_state=RetryState.from_dict(data.get("global_retry_state", {})),
            global_repair_state=RepairState.from_dict(data.get("global_repair_state", {})),
            # Summaries
            execution_backend_summary=ExecutionBackendSummary.from_dict(data.get("execution_backend_summary", {})),
            bridge_health_summary=BridgeHealthSummary.from_dict(data["bridge_health_summary"]) if data.get("bridge_health_summary") else None,
            verification_summary=VerificationSummary.from_dict(data.get("verification_summary", {})),
            memory_context_summary=MemoryContextSummary.from_dict(data.get("memory_context_summary", {})),
            # Status
            status=CheckpointStatus(data.get("status", "active")),
            last_runtime_status=data.get("last_runtime_status", "unknown"),
            resume_possible=data.get("resume_possible", True),
            resume_blocked_reason=data.get("resume_blocked_reason"),
            # Metadata
            checkpoint_reason=data.get("checkpoint_reason", ""),
            metadata=data.get("metadata", {}),
        )
        return checkpoint

    def update_timestamp(self) -> None:
        """Update the checkpoint timestamp."""
        self.updated_at = datetime.now().isoformat()

    def get_active_step(self) -> StepState | None:
        """Get the currently active step."""
        if self.active_step_id and self.active_step_id in self.steps:
            return self.steps[self.active_step_id]

        # Find first pending/in_progress step
        for step_id in self.step_order:
            step = self.steps.get(step_id)
            if step and step.status in (StepStatus.PENDING, StepStatus.IN_PROGRESS):
                return step

        return None

    def get_next_pending_step(self) -> StepState | None:
        """Get the next step that should be executed."""
        for step_id in self.step_order:
            step = self.steps.get(step_id)
            if step and step.status == StepStatus.PENDING:
                return step
            # Also consider failed steps that can retry
            if step and step.status == StepStatus.FAILED_RECOVERABLE and step.can_retry():
                return step
        return None

    def get_progress(self) -> dict[str, Any]:
        """Get execution progress summary."""
        total = len(self.step_order)
        completed = len(self.completed_step_ids)
        pending = len(self.pending_step_ids)
        failed = len(self.failed_step_ids)

        return {
            "total_steps": total,
            "completed": completed,
            "pending": pending,
            "failed": failed,
            "percent_complete": (completed / total * 100) if total > 0 else 0,
            "active_step_id": self.active_step_id,
        }

    def mark_step_started(self, step_id: str) -> None:
        """Mark a step as started."""
        if step_id in self.steps:
            self.steps[step_id].mark_started()
            self.active_step_id = step_id
            if step_id in self.pending_step_ids:
                self.pending_step_ids.remove(step_id)
            self.update_timestamp()

    def mark_step_completed(self, step_id: str, verified: bool = False) -> None:
        """Mark a step as completed."""
        if step_id in self.steps:
            self.steps[step_id].mark_completed(verified=verified)
            if step_id not in self.completed_step_ids:
                self.completed_step_ids.append(step_id)
            if step_id in self.failed_step_ids:
                self.failed_step_ids.remove(step_id)
            if step_id == self.active_step_id:
                self.active_step_id = None
            self.update_timestamp()

    def mark_step_failed(self, step_id: str, error: dict[str, Any] | None = None, recoverable: bool = False) -> None:
        """Mark a step as failed."""
        if step_id in self.steps:
            self.steps[step_id].mark_failed(error=error, recoverable=recoverable)
            if step_id not in self.failed_step_ids:
                self.failed_step_ids.append(step_id)
            if step_id == self.active_step_id:
                self.active_step_id = None
            self.update_timestamp()

    def is_safe_to_resume(self) -> tuple[bool, str | None]:
        """Check if it's safe to resume from this checkpoint."""
        if not self.resume_possible:
            return False, self.resume_blocked_reason or "resume_not_allowed"

        if self.status == CheckpointStatus.CORRUPT:
            return False, "checkpoint_corrupt"

        if self.status == CheckpointStatus.COMPLETED:
            return False, "plan_already_completed"

        # Check if there are any steps to execute
        next_step = self.get_next_pending_step()
        if next_step is None and not any(
            s.status == StepStatus.FAILED_RECOVERABLE and s.can_retry()
            for s in self.steps.values()
        ):
            return False, "no_pending_steps"

        return True, None

    def should_replay_step(self, step_id: str, policy_replay_verified: bool = False) -> bool:
        """Determine if a step should be replayed.

        Args:
            step_id: The step to check
            policy_replay_verified: Whether policy requires replay of verified steps

        Returns:
            True if step should be replayed
        """
        if step_id not in self.steps:
            return True  # Unknown step, should execute

        step = self.steps[step_id]

        # Always replay failed steps
        if step.status in (StepStatus.FAILED, StepStatus.FAILED_RECOVERABLE):
            return True

        # Replay in-progress steps (they may not have completed)
        if step.status == StepStatus.IN_PROGRESS:
            return True

        # Replay pending steps
        if step.status == StepStatus.PENDING:
            return True

        # Verified completed steps may need replay based on policy
        if step.status == StepStatus.COMPLETED_VERIFIED and policy_replay_verified:
            return True

        # Regular completed steps should not be replayed unless policy says so
        return False


def create_checkpoint_id(task_id: str) -> str:
    """Generate a unique checkpoint ID.

    Args:
        task_id: The task ID to include in the checkpoint ID

    Returns:
        Unique checkpoint ID string
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    return f"checkpoint_{task_id}_{timestamp}"


def create_step_id(subgoal_id: str, step_index: int, action: str) -> str:
    """Generate a unique step ID.

    Args:
        subgoal_id: The parent subgoal ID
        step_index: Index of step within subgoal
        action: The action name

    Returns:
        Unique step ID string
    """
    action_clean = action.replace(" ", "_").replace("-", "_")[:30]
    return f"step_{subgoal_id}_{step_index:03d}_{action_clean}"


def create_subgoal_id(plan_id: str, subgoal_index: int, description: str) -> str:
    """Generate a unique subgoal ID.

    Args:
        plan_id: The parent plan ID
        subgoal_index: Index of subgoal within plan
        description: Brief description of subgoal

    Returns:
        Unique subgoal ID string
    """
    desc_clean = description.replace(" ", "_").replace("-", "_")[:30]
    return f"subgoal_{plan_id}_{subgoal_index:03d}_{desc_clean}"
