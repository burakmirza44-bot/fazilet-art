"""Goal Models Module.

Provides structured goal types, requests, and artifacts for the Goal Generator.
Goals flow through the runtime spine as structured artifacts with metadata,
source signals, and execution hints.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
import uuid


class GoalGenerationMode(str, Enum):
    """Mode of goal generation.

    Determines how goals should be generated based on runtime context.
    """

    ROOT_GOAL = "root_goal"  # Generate initial goal from task
    SUBGOAL_GENERATION = "subgoal_generation"  # Generate subgoals from parent
    NEXT_GOAL = "next_goal"  # Generate next action goal
    REPAIR_GOAL = "repair_goal"  # Generate goal from failure context
    VERIFICATION_GOAL = "verification_goal"  # Generate goal to verify/collect evidence
    RESUME_GOAL = "resume_goal"  # Generate goal to resume from checkpoint
    MIXED = "mixed"  # Mixed mode with multiple signals


class GoalType(str, Enum):
    """Type of generated goal.

    Determines the nature and handling of the goal.
    """

    ROOT_GOAL = "root_goal"  # Top-level goal from task
    SUBGOAL = "subgoal"  # Decomposed subgoal
    NEXT_ACTION_GOAL = "next_action_goal"  # Immediate next action
    REPAIR_GOAL = "repair_goal"  # Goal to repair a failure
    VERIFICATION_GOAL = "verification_goal"  # Goal to verify outcome
    RESEARCH_GOAL = "research_goal"  # Goal to gather information
    INSPECT_GOAL = "inspect_goal"  # Goal to inspect state
    RESUME_GOAL = "resume_goal"  # Goal to resume from checkpoint


class DomainHint(str, Enum):
    """Domain hint for goal generation.

    Helps inform domain-specific goal generation strategies.
    """

    HOUDINI = "houdini"
    TOUCHDESIGNER = "touchdesigner"
    MIXED = "mixed"
    GENERIC = "generic"
    UNKNOWN = "unknown"


class GoalSourceSignal(str, Enum):
    """Source signal that influenced goal generation.

    Tracks which signals contributed to the goal's creation.
    """

    TASK = "task"  # Original task description
    OBSERVATION = "observation"  # Runtime observation
    MEMORY = "memory"  # Memory patterns
    TRANSCRIPT_KNOWLEDGE = "transcript_knowledge"  # Tutorial/transcript knowledge
    RECIPE_KNOWLEDGE = "recipe_knowledge"  # Recipe knowledge
    FAILURE_CONTEXT = "failure_context"  # Failure context
    REPAIR_CONTEXT = "repair_context"  # Repair context
    VERIFICATION_CONTEXT = "verification_context"  # Verification context


class ExecutionFeasibility(str, Enum):
    """Execution feasibility level for a goal.

    Indicates how likely a goal can be successfully executed.
    """

    HIGH = "high"  # Well-understood, high success rate
    MEDIUM = "medium"  # Reasonable chance of success
    LOW = "low"  # Uncertain, may need adjustment
    UNKNOWN = "unknown"  # Not enough information


class GoalStatus(str, Enum):
    """Status of a goal in the execution pipeline.

    Tracks the lifecycle of a goal from generation to completion.
    """

    GENERATED = "generated"  # Just created by goal generator
    VALIDATED = "validated"  # Passed validation checks
    SCHEDULED = "scheduled"  # Added to execution queue
    READY = "ready"  # Dependencies satisfied, ready to execute
    IN_PROGRESS = "in_progress"  # Currently being executed
    COMPLETED = "completed"  # Successfully completed
    FAILED = "failed"  # Execution failed
    BLOCKED = "blocked"  # Blocked by precondition or dependency
    CANCELLED = "cancelled"  # Cancelled before execution
    VERIFIED = "verified"  # Execution result verified


def _generate_id(prefix: str = "goal") -> str:
    """Generate a unique ID with prefix."""
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


@dataclass(slots=True)
class GoalRequest:
    """Request to generate goals from runtime context.

    Contains all context needed to generate structured goals including
    task summary, runtime state, memory, knowledge, and failure context.
    """

    goal_request_id: str
    session_id: str
    task_id: str
    domain_hint: str  # DomainHint value
    raw_task_summary: str
    normalized_task_summary: str = ""
    current_runtime_state_summary: str = ""
    current_goal_context: dict[str, Any] = field(default_factory=dict)
    active_subgoal_context: dict[str, Any] = field(default_factory=dict)
    observation_summary: str = ""
    memory_summary: dict[str, Any] = field(default_factory=dict)
    transcript_knowledge_summary: dict[str, Any] = field(default_factory=dict)
    recipe_knowledge_summary: dict[str, Any] = field(default_factory=dict)
    failure_context: dict[str, Any] = field(default_factory=dict)
    repair_context: dict[str, Any] = field(default_factory=dict)
    verification_context: dict[str, Any] = field(default_factory=dict)
    checkpoint_summary: dict[str, Any] = field(default_factory=dict)
    dry_run: bool = True
    bounded_mode: bool = True
    safety_mode: bool = True
    verification_required: bool = False
    max_goal_count: int = 5
    goal_generation_mode: str = "root_goal"
    created_at: str = ""

    def __post_init__(self) -> None:
        """Set defaults after initialization."""
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    @classmethod
    def create(
        cls,
        task_id: str,
        session_id: str,
        domain_hint: str | DomainHint,
        raw_task_summary: str,
        **kwargs: Any,
    ) -> "GoalRequest":
        """Factory method to create a GoalRequest with auto-generated ID.

        Args:
            task_id: Task ID
            session_id: Session ID
            domain_hint: Domain hint (string or DomainHint)
            raw_task_summary: Raw task description
            **kwargs: Additional fields to set

        Returns:
            GoalRequest instance
        """
        domain_value = domain_hint.value if isinstance(domain_hint, DomainHint) else domain_hint

        return cls(
            goal_request_id=_generate_id("greq"),
            session_id=session_id,
            task_id=task_id,
            domain_hint=domain_value,
            raw_task_summary=raw_task_summary,
            created_at=datetime.now().isoformat(),
            **kwargs,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary representation
        """
        return {
            "goal_request_id": self.goal_request_id,
            "session_id": self.session_id,
            "task_id": self.task_id,
            "domain_hint": self.domain_hint,
            "raw_task_summary": self.raw_task_summary,
            "normalized_task_summary": self.normalized_task_summary,
            "current_runtime_state_summary": self.current_runtime_state_summary,
            "current_goal_context": self.current_goal_context,
            "active_subgoal_context": self.active_subgoal_context,
            "observation_summary": self.observation_summary,
            "memory_summary": self.memory_summary,
            "transcript_knowledge_summary": self.transcript_knowledge_summary,
            "recipe_knowledge_summary": self.recipe_knowledge_summary,
            "failure_context": self.failure_context,
            "repair_context": self.repair_context,
            "verification_context": self.verification_context,
            "checkpoint_summary": self.checkpoint_summary,
            "dry_run": self.dry_run,
            "bounded_mode": self.bounded_mode,
            "safety_mode": self.safety_mode,
            "verification_required": self.verification_required,
            "max_goal_count": self.max_goal_count,
            "goal_generation_mode": self.goal_generation_mode,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GoalRequest":
        """Create GoalRequest from dictionary.

        Args:
            data: Dictionary with request data

        Returns:
            GoalRequest instance
        """
        return cls(
            goal_request_id=data["goal_request_id"],
            session_id=data["session_id"],
            task_id=data["task_id"],
            domain_hint=data["domain_hint"],
            raw_task_summary=data["raw_task_summary"],
            normalized_task_summary=data.get("normalized_task_summary", ""),
            current_runtime_state_summary=data.get("current_runtime_state_summary", ""),
            current_goal_context=data.get("current_goal_context", {}),
            active_subgoal_context=data.get("active_subgoal_context", {}),
            observation_summary=data.get("observation_summary", ""),
            memory_summary=data.get("memory_summary", {}),
            transcript_knowledge_summary=data.get("transcript_knowledge_summary", {}),
            recipe_knowledge_summary=data.get("recipe_knowledge_summary", {}),
            failure_context=data.get("failure_context", {}),
            repair_context=data.get("repair_context", {}),
            verification_context=data.get("verification_context", {}),
            checkpoint_summary=data.get("checkpoint_summary", {}),
            dry_run=data.get("dry_run", True),
            bounded_mode=data.get("bounded_mode", True),
            safety_mode=data.get("safety_mode", True),
            verification_required=data.get("verification_required", False),
            max_goal_count=data.get("max_goal_count", 5),
            goal_generation_mode=data.get("goal_generation_mode", "root_goal"),
            created_at=data.get("created_at", ""),
        )


@dataclass(slots=True)
class GoalArtifact:
    """Structured goal artifact with metadata and execution hints.

    A goal artifact flows through the runtime spine, carrying
    all information needed for execution, verification, and repair.
    """

    goal_id: str
    parent_goal_id: str | None = None
    task_id: str = ""
    session_id: str = ""
    domain: str = ""
    goal_type: str = "root_goal"  # GoalType value
    title: str = ""
    description: str = ""
    rationale_summary: str = ""
    source_signals: tuple[str, ...] = ()  # GoalSourceSignal values
    confidence: float = 0.0
    ambiguity_flags: tuple[str, ...] = ()
    safety_summary: str = ""
    execution_feasibility: str = "unknown"  # high, medium, low, unknown
    backend_hint: str = ""
    verification_hint: str = ""
    repair_hint: str = ""
    preconditions: tuple[str, ...] = ()
    success_criteria: dict[str, Any] = field(default_factory=dict)
    blocked_reason: str = ""
    created_at: str = ""
    schema_version: str = "1.0.0"

    def __post_init__(self) -> None:
        """Set defaults after initialization."""
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.goal_id:
            self.goal_id = _generate_id("goal")

    @classmethod
    def create(
        cls,
        goal_type: str | GoalType,
        title: str,
        description: str,
        domain: str = "",
        task_id: str = "",
        session_id: str = "",
        **kwargs: Any,
    ) -> "GoalArtifact":
        """Factory method to create a GoalArtifact with auto-generated ID.

        Args:
            goal_type: Type of goal (string or GoalType)
            title: Short title for the goal
            description: Detailed description
            domain: Execution domain
            task_id: Associated task ID
            session_id: Associated session ID
            **kwargs: Additional fields to set

        Returns:
            GoalArtifact instance
        """
        goal_type_value = goal_type.value if isinstance(goal_type, GoalType) else goal_type

        return cls(
            goal_id=_generate_id("goal"),
            task_id=task_id,
            session_id=session_id,
            domain=domain,
            goal_type=goal_type_value,
            title=title,
            description=description,
            created_at=datetime.now().isoformat(),
            **kwargs,
        )

    @property
    def is_blocked(self) -> bool:
        """Check if goal is blocked."""
        return bool(self.blocked_reason)

    @property
    def is_subgoal(self) -> bool:
        """Check if this is a subgoal."""
        return self.goal_type == GoalType.SUBGOAL.value

    @property
    def is_repair(self) -> bool:
        """Check if this is a repair goal."""
        return self.goal_type == GoalType.REPAIR_GOAL.value

    @property
    def is_verification(self) -> bool:
        """Check if this is a verification goal."""
        return self.goal_type == GoalType.VERIFICATION_GOAL.value

    @property
    def is_resume(self) -> bool:
        """Check if this is a resume goal."""
        return self.goal_type == GoalType.RESUME_GOAL.value

    @property
    def has_high_feasibility(self) -> bool:
        """Check if goal has high execution feasibility."""
        return self.execution_feasibility == ExecutionFeasibility.HIGH.value

    @property
    def source_signal_list(self) -> list[str]:
        """Get source signals as list."""
        return list(self.source_signals)

    def add_source_signal(self, signal: str | GoalSourceSignal) -> None:
        """Add a source signal to the goal.

        Args:
            signal: Signal to add (string or GoalSourceSignal)
        """
        signal_value = signal.value if isinstance(signal, GoalSourceSignal) else signal
        if signal_value not in self.source_signals:
            self.source_signals = (*self.source_signals, signal_value)

    def add_ambiguity_flag(self, flag: str) -> None:
        """Add an ambiguity flag to the goal.

        Args:
            flag: Ambiguity flag to add
        """
        if flag not in self.ambiguity_flags:
            self.ambiguity_flags = (*self.ambiguity_flags, flag)

    def add_precondition(self, precondition: str) -> None:
        """Add a precondition to the goal.

        Args:
            precondition: Precondition to add
        """
        if precondition not in self.preconditions:
            self.preconditions = (*self.preconditions, precondition)

    def block(self, reason: str) -> None:
        """Block the goal with a reason.

        Args:
            reason: Reason for blocking
        """
        self.blocked_reason = reason

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary representation
        """
        return {
            "goal_id": self.goal_id,
            "parent_goal_id": self.parent_goal_id,
            "task_id": self.task_id,
            "session_id": self.session_id,
            "domain": self.domain,
            "goal_type": self.goal_type,
            "title": self.title,
            "description": self.description,
            "rationale_summary": self.rationale_summary,
            "source_signals": list(self.source_signals),
            "confidence": self.confidence,
            "ambiguity_flags": list(self.ambiguity_flags),
            "safety_summary": self.safety_summary,
            "execution_feasibility": self.execution_feasibility,
            "backend_hint": self.backend_hint,
            "verification_hint": self.verification_hint,
            "repair_hint": self.repair_hint,
            "preconditions": list(self.preconditions),
            "success_criteria": self.success_criteria,
            "blocked_reason": self.blocked_reason,
            "created_at": self.created_at,
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GoalArtifact":
        """Create GoalArtifact from dictionary.

        Args:
            data: Dictionary with artifact data

        Returns:
            GoalArtifact instance
        """
        return cls(
            goal_id=data["goal_id"],
            parent_goal_id=data.get("parent_goal_id"),
            task_id=data.get("task_id", ""),
            session_id=data.get("session_id", ""),
            domain=data.get("domain", ""),
            goal_type=data.get("goal_type", "root_goal"),
            title=data.get("title", ""),
            description=data.get("description", ""),
            rationale_summary=data.get("rationale_summary", ""),
            source_signals=tuple(data.get("source_signals", [])),
            confidence=data.get("confidence", 0.0),
            ambiguity_flags=tuple(data.get("ambiguity_flags", [])),
            safety_summary=data.get("safety_summary", ""),
            execution_feasibility=data.get("execution_feasibility", "unknown"),
            backend_hint=data.get("backend_hint", ""),
            verification_hint=data.get("verification_hint", ""),
            repair_hint=data.get("repair_hint", ""),
            preconditions=tuple(data.get("preconditions", [])),
            success_criteria=data.get("success_criteria", {}),
            blocked_reason=data.get("blocked_reason", ""),
            created_at=data.get("created_at", ""),
            schema_version=data.get("schema_version", "1.0.0"),
        )


@dataclass(slots=True)
class GoalGenerationResult:
    """Result of goal generation with metadata and generated goals.

    Captures the outcome of a goal generation request including
    generated goals, domain inference, knowledge usage, and errors.
    """

    goal_generation_performed: bool
    generated_goal_count: int
    selected_goal_ids: list[str]
    selected_goal_summary: str
    goal_generation_mode: str
    domain_inferred: str
    domain_confidence: float
    memory_influenced: bool
    transcript_knowledge_used: bool
    recipe_knowledge_used: bool
    ambiguity_summary: str
    blocked_goal_count: int
    filtered_goal_count: int
    generated_goals: list[GoalArtifact]
    final_status: str
    errors: list[dict[str, Any]] = field(default_factory=list)

    @property
    def has_goals(self) -> bool:
        """Check if any goals were generated."""
        return self.generated_goal_count > 0

    @property
    def has_selected_goals(self) -> bool:
        """Check if any goals were selected."""
        return len(self.selected_goal_ids) > 0

    @property
    def has_errors(self) -> bool:
        """Check if any errors occurred."""
        return len(self.errors) > 0

    @property
    def primary_goal(self) -> GoalArtifact | None:
        """Get the primary (first selected) goal.

        Returns:
            Primary goal or None if no goals selected
        """
        if not self.selected_goal_ids:
            return None

        for goal in self.generated_goals:
            if goal.goal_id == self.selected_goal_ids[0]:
                return goal

        return self.generated_goals[0] if self.generated_goals else None

    @property
    def all_goals_blocked(self) -> bool:
        """Check if all generated goals are blocked."""
        if not self.generated_goals:
            return False
        return all(g.is_blocked for g in self.generated_goals)

    def add_error(self, error_type: str, message: str, details: dict[str, Any] | None = None) -> None:
        """Add an error to the result.

        Args:
            error_type: Type of error
            message: Error message
            details: Optional error details
        """
        self.errors.append({
            "error_type": error_type,
            "message": message,
            "details": details or {},
        })

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary representation
        """
        return {
            "goal_generation_performed": self.goal_generation_performed,
            "generated_goal_count": self.generated_goal_count,
            "selected_goal_ids": self.selected_goal_ids,
            "selected_goal_summary": self.selected_goal_summary,
            "goal_generation_mode": self.goal_generation_mode,
            "domain_inferred": self.domain_inferred,
            "domain_confidence": self.domain_confidence,
            "memory_influenced": self.memory_influenced,
            "transcript_knowledge_used": self.transcript_knowledge_used,
            "recipe_knowledge_used": self.recipe_knowledge_used,
            "ambiguity_summary": self.ambiguity_summary,
            "blocked_goal_count": self.blocked_goal_count,
            "filtered_goal_count": self.filtered_goal_count,
            "generated_goals": [g.to_dict() for g in self.generated_goals],
            "final_status": self.final_status,
            "errors": self.errors,
        }

    @classmethod
    def empty_result(cls, mode: str = "root_goal", reason: str = "No generation performed") -> "GoalGenerationResult":
        """Create an empty result indicating no goals were generated.

        Args:
            mode: Goal generation mode
            reason: Reason for empty result

        Returns:
            GoalGenerationResult with no goals
        """
        return cls(
            goal_generation_performed=False,
            generated_goal_count=0,
            selected_goal_ids=[],
            selected_goal_summary="",
            goal_generation_mode=mode,
            domain_inferred=DomainHint.UNKNOWN.value,
            domain_confidence=0.0,
            memory_influenced=False,
            transcript_knowledge_used=False,
            recipe_knowledge_used=False,
            ambiguity_summary=reason,
            blocked_goal_count=0,
            filtered_goal_count=0,
            generated_goals=[],
            final_status="skipped",
            errors=[],
        )

    @classmethod
    def error_result(cls, mode: str, errors: list[dict[str, Any]]) -> "GoalGenerationResult":
        """Create an error result.

        Args:
            mode: Goal generation mode
            errors: List of errors

        Returns:
            GoalGenerationResult with errors
        """
        return cls(
            goal_generation_performed=True,
            generated_goal_count=0,
            selected_goal_ids=[],
            selected_goal_summary="",
            goal_generation_mode=mode,
            domain_inferred=DomainHint.UNKNOWN.value,
            domain_confidence=0.0,
            memory_influenced=False,
            transcript_knowledge_used=False,
            recipe_knowledge_used=False,
            ambiguity_summary="",
            blocked_goal_count=0,
            filtered_goal_count=0,
            generated_goals=[],
            final_status="error",
            errors=errors,
        )