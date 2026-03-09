"""Core runtime infrastructure.

Provides runtime memory management, bridge health monitoring,
checkpoint/resume functionality, and unified error handling
across all execution paths.
"""

from app.core.bridge_health import (
    BridgeHealthReport,
    check_bridge_health,
    normalize_bridge_error,
)
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
from app.core.memory_runtime import (
    RuntimeMemoryContext,
    build_runtime_memory_context,
    get_memory_influence_summary,
)

__all__ = [
    # Bridge health
    "BridgeHealthReport",
    "check_bridge_health",
    "normalize_bridge_error",
    # Checkpoint
    "Checkpoint",
    "CheckpointStatus",
    "StepState",
    "StepStatus",
    "SubgoalState",
    "RetryState",
    "RepairState",
    "BridgeHealthSummary",
    "ExecutionBackendSummary",
    "MemoryContextSummary",
    "VerificationSummary",
    "create_checkpoint_id",
    "create_step_id",
    "create_subgoal_id",
    # Checkpoint lifecycle
    "CheckpointLifecycle",
    "CheckpointBoundaryDetector",
    "CheckpointValidationResult",
    # Checkpoint resume
    "ResumeManager",
    "ResumeDecision",
    "ResumeContext",
    "ResumeResult",
    "should_attempt_resume",
    # Memory runtime
    "RuntimeMemoryContext",
    "build_runtime_memory_context",
    "get_memory_influence_summary",
]
