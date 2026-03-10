"""Goal Generation Error Types.

Provides normalized error types for goal generation failures,
enabling consistent error handling and recovery strategies.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any
import uuid


class GoalGenerationErrorType(str, Enum):
    """Types of errors that can occur during goal generation."""

    GOAL_GENERATION_FAILED = "goal_generation_failed"  # General generation failure
    GOAL_CONTEXT_MISSING = "goal_context_missing"  # Missing required context
    DOMAIN_INFERENCE_FAILED = "domain_inference_failed"  # Unable to infer domain
    MEMORY_CONTEXT_UNAVAILABLE = "memory_context_unavailable"  # Memory unavailable
    TRANSCRIPT_KNOWLEDGE_UNAVAILABLE = "transcript_knowledge_unavailable"  # Transcript knowledge unavailable
    RECIPE_KNOWLEDGE_UNAVAILABLE = "recipe_knowledge_unavailable"  # Recipe knowledge unavailable
    AMBIGUITY_TOO_HIGH = "ambiguity_too_high"  # Goal too ambiguous to generate
    NO_USABLE_GOAL_GENERATED = "no_usable_goal_generated"  # All generated goals blocked/filtered
    GOAL_SCHEMA_INVALID = "goal_schema_invalid"  # Generated goal violates schema
    GOAL_RANKING_FAILED = "goal_ranking_failed"  # Failed to rank goals
    GOAL_SAFETY_BLOCKED = "goal_safety_blocked"  # Goal blocked by safety checks
    GOAL_RUNTIME_INJECTION_FAILED = "goal_runtime_injection_failed"  # Failed to inject goal into runtime


def _generate_error_id() -> str:
    """Generate a unique error ID."""
    return f"gerr_{uuid.uuid4().hex[:12]}"


@dataclass(slots=True)
class GoalGenerationError:
    """Normalized error from goal generation.

    Provides structured error information with recovery hints
    and contextual details for debugging and recovery.
    """

    error_id: str
    error_type: GoalGenerationErrorType
    message: str
    domain: str = ""
    task_id: str = ""
    recoverable: bool = True
    fix_hint: str = ""
    context: dict[str, Any] | None = None
    timestamp: str = ""

    def __post_init__(self) -> None:
        """Set defaults after initialization."""
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
        if not self.error_id:
            self.error_id = _generate_error_id()

    @classmethod
    def create(
        cls,
        error_type: GoalGenerationErrorType,
        message: str,
        domain: str = "",
        task_id: str = "",
        recoverable: bool = True,
        fix_hint: str = "",
        context: dict[str, Any] | None = None,
    ) -> "GoalGenerationError":
        """Factory method to create a GoalGenerationError.

        Args:
            error_type: Type of error
            message: Human-readable error message
            domain: Domain where error occurred
            task_id: Associated task ID
            recoverable: Whether error is recoverable
            fix_hint: Hint for fixing the error
            context: Additional context

        Returns:
            GoalGenerationError instance
        """
        return cls(
            error_id=_generate_error_id(),
            error_type=error_type,
            message=message,
            domain=domain,
            task_id=task_id,
            recoverable=recoverable,
            fix_hint=fix_hint,
            context=context,
            timestamp=datetime.now().isoformat(),
        )

    @property
    def is_recoverable(self) -> bool:
        """Check if error is recoverable."""
        return self.recoverable

    @property
    def requires_context_retry(self) -> bool:
        """Check if error can be fixed by providing more context."""
        return self.error_type in (
            GoalGenerationErrorType.GOAL_CONTEXT_MISSING,
            GoalGenerationErrorType.MEMORY_CONTEXT_UNAVAILABLE,
            GoalGenerationErrorType.TRANSCRIPT_KNOWLEDGE_UNAVAILABLE,
            GoalGenerationErrorType.RECIPE_KNOWLEDGE_UNAVAILABLE,
        )

    @property
    def requires_decomposition_retry(self) -> bool:
        """Check if error can be fixed by retrying decomposition."""
        return self.error_type in (
            GoalGenerationErrorType.AMBIGUITY_TOO_HIGH,
            GoalGenerationErrorType.NO_USABLE_GOAL_GENERATED,
        )

    @property
    def requires_safety_override(self) -> bool:
        """Check if error requires safety override."""
        return self.error_type == GoalGenerationErrorType.GOAL_SAFETY_BLOCKED

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary representation
        """
        return {
            "error_id": self.error_id,
            "error_type": self.error_type.value,
            "message": self.message,
            "domain": self.domain,
            "task_id": self.task_id,
            "recoverable": self.recoverable,
            "fix_hint": self.fix_hint,
            "context": self.context,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GoalGenerationError":
        """Create GoalGenerationError from dictionary.

        Args:
            data: Dictionary with error data

        Returns:
            GoalGenerationError instance
        """
        return cls(
            error_id=data.get("error_id", _generate_error_id()),
            error_type=GoalGenerationErrorType(data.get("error_type", "goal_generation_failed")),
            message=data.get("message", ""),
            domain=data.get("domain", ""),
            task_id=data.get("task_id", ""),
            recoverable=data.get("recoverable", True),
            fix_hint=data.get("fix_hint", ""),
            context=data.get("context"),
            timestamp=data.get("timestamp", ""),
        )

    def __str__(self) -> str:
        """Return string representation."""
        return f"[{self.error_type.value}] {self.message}"

    def __repr__(self) -> str:
        """Return repr."""
        return f"GoalGenerationError({self.error_type.value!r}, {self.message!r})"


def create_context_missing_error(
    missing_fields: list[str],
    task_id: str = "",
    domain: str = "",
) -> GoalGenerationError:
    """Create a context missing error.

    Args:
        missing_fields: List of missing context fields
        task_id: Associated task ID
        domain: Domain where error occurred

    Returns:
        GoalGenerationError for missing context
    """
    return GoalGenerationError.create(
        error_type=GoalGenerationErrorType.GOAL_CONTEXT_MISSING,
        message=f"Missing required context fields: {', '.join(missing_fields)}",
        domain=domain,
        task_id=task_id,
        recoverable=True,
        fix_hint="Provide missing context fields in GoalRequest",
        context={"missing_fields": missing_fields},
    )


def create_domain_inference_error(
    raw_task: str,
    task_id: str = "",
    reason: str = "",
) -> GoalGenerationError:
    """Create a domain inference error.

    Args:
        raw_task: Raw task that failed domain inference
        task_id: Associated task ID
        reason: Reason for failure

    Returns:
        GoalGenerationError for domain inference failure
    """
    return GoalGenerationError.create(
        error_type=GoalGenerationErrorType.DOMAIN_INFERENCE_FAILED,
        message=f"Unable to infer domain from task: {reason or 'unknown'}",
        domain="unknown",
        task_id=task_id,
        recoverable=True,
        fix_hint="Provide explicit domain_hint in GoalRequest",
        context={"raw_task": raw_task[:200], "reason": reason},
    )


def create_ambiguity_error(
    ambiguity_flags: list[str],
    task_id: str = "",
    domain: str = "",
) -> GoalGenerationError:
    """Create an ambiguity error.

    Args:
        ambiguity_flags: List of ambiguity flags detected
        task_id: Associated task ID
        domain: Domain where error occurred

    Returns:
        GoalGenerationError for high ambiguity
    """
    return GoalGenerationError.create(
        error_type=GoalGenerationErrorType.AMBIGUITY_TOO_HIGH,
        message=f"Goal too ambiguous: {', '.join(ambiguity_flags)}",
        domain=domain,
        task_id=task_id,
        recoverable=True,
        fix_hint="Clarify task description or provide more specific context",
        context={"ambiguity_flags": ambiguity_flags},
    )


def create_no_usable_goal_error(
    generated_count: int,
    blocked_count: int,
    filtered_count: int,
    task_id: str = "",
    domain: str = "",
) -> GoalGenerationError:
    """Create a no usable goal error.

    Args:
        generated_count: Number of goals generated
        blocked_count: Number of goals blocked
        filtered_count: Number of goals filtered
        task_id: Associated task ID
        domain: Domain where error occurred

    Returns:
        GoalGenerationError for no usable goals
    """
    return GoalGenerationError.create(
        error_type=GoalGenerationErrorType.NO_USABLE_GOAL_GENERATED,
        message=f"No usable goals: {blocked_count} blocked, {filtered_count} filtered out of {generated_count}",
        domain=domain,
        task_id=task_id,
        recoverable=True,
        fix_hint="Review blocked goals and adjust safety constraints or provide more context",
        context={
            "generated_count": generated_count,
            "blocked_count": blocked_count,
            "filtered_count": filtered_count,
        },
    )


def create_safety_blocked_error(
    goal_title: str,
    safety_reason: str,
    task_id: str = "",
    domain: str = "",
) -> GoalGenerationError:
    """Create a safety blocked error.

    Args:
        goal_title: Title of the blocked goal
        safety_reason: Reason for safety block
        task_id: Associated task ID
        domain: Domain where error occurred

    Returns:
        GoalGenerationError for safety blocked goal
    """
    return GoalGenerationError.create(
        error_type=GoalGenerationErrorType.GOAL_SAFETY_BLOCKED,
        message=f"Goal '{goal_title}' blocked by safety: {safety_reason}",
        domain=domain,
        task_id=task_id,
        recoverable=False,
        fix_hint="Goal violates safety constraints and cannot be executed",
        context={"goal_title": goal_title, "safety_reason": safety_reason},
    )


def create_generation_failed_error(
    reason: str,
    task_id: str = "",
    domain: str = "",
    original_error: Exception | None = None,
) -> GoalGenerationError:
    """Create a general generation failed error.

    Args:
        reason: Reason for failure
        task_id: Associated task ID
        domain: Domain where error occurred
        original_error: Optional original exception

    Returns:
        GoalGenerationError for generation failure
    """
    context = {"reason": reason}
    if original_error:
        context["original_error"] = str(original_error)
        context["original_error_type"] = type(original_error).__name__

    return GoalGenerationError.create(
        error_type=GoalGenerationErrorType.GOAL_GENERATION_FAILED,
        message=f"Goal generation failed: {reason}",
        domain=domain,
        task_id=task_id,
        recoverable=True,
        fix_hint="Check error context and retry with adjusted parameters",
        context=context,
    )