"""Session Module.

Provides runtime visibility through comprehensive session metadata tracking.

Key Components:
- ExecutionPhase: Phases in the execution lifecycle
- SessionMetadata: Complete session metadata
- SessionTracker: Track metadata during execution
- SessionDisplayFormatter: Format for display

Usage:
    from app.session import SessionTracker, ExecutionPhase

    tracker = SessionTracker("session_001", "Create geometry", "houdini")

    tracker.record_phase_start(ExecutionPhase.PLANNING)
    tracker.record_knowledge_hit("recipe_001", "Noise Terrain", 0.85, "distilled", "planning")
    tracker.record_phase_end(ExecutionPhase.PLANNING)

    tracker.record_phase_start(ExecutionPhase.EXECUTION)
    tracker.record_execution_step(1, "Create geometry", "houdini", 156.0, True)
    tracker.record_phase_end(ExecutionPhase.EXECUTION)

    tracker.finalize(success=True)
    tracker.export()

Integration with Runtime:
    The SessionTracker integrates with the runtime loop to provide
    visibility into:
    - Which knowledge was retrieved and used
    - How many RAG queries were made
    - Planning iterations and replanning
    - Execution step success rates
    - Error recovery attempts
    - Bridge health status
"""

from app.session.metadata import (
    BridgeHealthMetrics,
    ErrorRecoveryMetrics,
    ExecutionPhase,
    ExecutionStepMetrics,
    KnowledgeHit,
    KnowledgeQualityMetrics,
    PlanningMetrics,
    RagRetrievalMetrics,
    SessionMetadata,
)
from app.session.tracker import SessionTracker
from app.session.display import (
    SessionDisplayFormatter,
    format_session_summary,
    print_session_summary,
)

__all__ = [
    # Metadata classes
    "ExecutionPhase",
    "KnowledgeHit",
    "RagRetrievalMetrics",
    "PlanningMetrics",
    "ExecutionStepMetrics",
    "ErrorRecoveryMetrics",
    "KnowledgeQualityMetrics",
    "BridgeHealthMetrics",
    "SessionMetadata",
    # Tracker
    "SessionTracker",
    # Display
    "SessionDisplayFormatter",
    "format_session_summary",
    "print_session_summary",
]

__version__ = "1.0.0"