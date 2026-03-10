"""Agent Core Module.

Provides core agent functionality including action dispatch,
backend selection, safety mechanisms, goal generation, and benchmark policy management.
"""

# Import core modules first (no circular dependencies)
from app.agent_core.backend_policy import BackendPolicy, BackendType
from app.agent_core.backend_result import (
    BackendSelectionResult,
    BridgeHealthResult,
    SafetyCheckResult,
    SelectionStatus,
)
from app.agent_core.backend_selector import BackendSelector, get_default_selector, select_backend

# Import goal modules (no circular dependencies)
from app.agent_core.goal_models import (
    DomainHint,
    ExecutionFeasibility,
    GoalArtifact,
    GoalGenerationMode,
    GoalGenerationResult,
    GoalRequest,
    GoalSourceSignal,
    GoalStatus,
    GoalType,
)
from app.agent_core.goal_errors import (
    GoalGenerationError,
    GoalGenerationErrorType,
)
from app.agent_core.goal_generator import (
    GoalGenerator,
    GoalGeneratorConfig,
    build_goal_request_from_task,
)

# Import goal store
from app.agent_core.goal_store import (
    GoalLifecycleEvent,
    GoalStats,
    GoalStore,
    create_goal_store,
)

# Import runtime loop
from app.agent_core.runtime_loop import IntegratedRuntimeLoop, RuntimeLoopResult

# Import goal scheduler bridge
from app.agent_core.goal_scheduler_bridge import (
    GoalSchedulerBridge,
    GoalStatus as SchedulerGoalStatus,
    ScheduledGoal,
    SchedulePriority,
    ScheduleResult,
    create_scheduler,
)

# Import autonomous loop
from app.agent_core.autonomous_loop import (
    AutonomousConfig,
    AutonomousLoop,
    AutonomyLevel,
    CyclePhase,
    CycleResult,
    CycleState,
    LoopStatus,
    create_autonomous_loop,
)

# Import verification gate
from app.agent_core.verification_gate import (
    GapSeverity,
    VerificationConfig,
    VerificationGate,
    VerificationGap,
    VerificationLevel,
    VerificationRequest,
    VerificationResult,
    VerificationStatus,
    create_verification_gate,
)

# Import KB updater
from app.agent_core.kb_updater import (
    KBPattern,
    KBUpdateRequest,
    KBUpdateResult,
    KBUpdateStatus,
    KBUpdateType,
    KBUpdater,
    KBUpdaterConfig,
    create_kb_updater,
)

# Import shipping
from app.agent_core.shipping import (
    ArtifactShipper,
    ShippingArtifact,
    ShippingDestination,
    ShippingPriority,
    ShippingRequest,
    ShippingResult,
    ShippingStatus,
    ShipperConfig,
    create_shipper,
)

# Import fusion
from app.agent_core.fusion import (
    DataFusion,
    FusionConfig,
    FusionMode,
    FusionRequest,
    FusionResult,
    FusionSource,
    FusionSourceType,
    create_fusion,
)

# Import RAG integration
from app.agent_core.recipe_rag_integration import (
    ContextRequirement,
    MergedContext,
    RAGContext,
    RecipeKnowledge,
    RecipeRAGBridge,
    RecipeStep,
    RetrievedDocument,
    TaskType,
    build_context,
    decompose_task,
)

# Import pre-planning retrieval
from app.agent_core.preplanning_models import (
    DecisionPoint,
    DecisionType,
    ExecutionStrategy,
    PastExecution,
    PlanWithRetrieval,
    StrategySource,
    SubgoalWithHints,
    STRATEGY_TEMPLATES,
)
from app.agent_core.similar_task_retriever import (
    RetrievalConfig,
    SimilarTaskRetriever,
    create_retriever,
    extract_strategy_from_execution,
    format_hints_for_planning,
)
from app.agent_core.long_horizon_planner import (
    PlannerConfig,
    LongHorizonPlannerWithRetrieval,
    create_planner,
)


# Lazy import for benchmark_policy_adapter (has circular dependency with app.evals)
def __getattr__(name: str):
    """Lazy import for benchmark_policy_adapter to avoid circular imports."""
    if name in (
        "BenchmarkPolicyAdapter",
        "BenchmarkExecutionContext",
        "RuntimeLoopSettings",
        "create_runtime_loop_for_benchmark",
    ):
        from app.agent_core.benchmark_policy_adapter import (
            BenchmarkExecutionContext,
            BenchmarkPolicyAdapter,
            RuntimeLoopSettings,
            create_runtime_loop_for_benchmark,
        )
        if name == "BenchmarkPolicyAdapter":
            return BenchmarkPolicyAdapter
        elif name == "BenchmarkExecutionContext":
            return BenchmarkExecutionContext
        elif name == "RuntimeLoopSettings":
            return RuntimeLoopSettings
        elif name == "create_runtime_loop_for_benchmark":
            return create_runtime_loop_for_benchmark
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    # Policy
    "BackendPolicy",
    "BackendType",
    # Result
    "BackendSelectionResult",
    "BridgeHealthResult",
    "SafetyCheckResult",
    "SelectionStatus",
    # Selector
    "BackendSelector",
    "get_default_selector",
    "select_backend",
    # Benchmark Policy Adapter (lazy loaded)
    "BenchmarkPolicyAdapter",
    "BenchmarkExecutionContext",
    "RuntimeLoopSettings",
    "create_runtime_loop_for_benchmark",
    # Goal Models
    "DomainHint",
    "ExecutionFeasibility",
    "GoalArtifact",
    "GoalGenerationMode",
    "GoalGenerationResult",
    "GoalRequest",
    "GoalSourceSignal",
    "GoalStatus",
    "GoalType",
    # Goal Errors
    "GoalGenerationError",
    "GoalGenerationErrorType",
    # Goal Generator
    "GoalGenerator",
    "GoalGeneratorConfig",
    "build_goal_request_from_task",
    # Goal Store
    "GoalLifecycleEvent",
    "GoalStats",
    "GoalStore",
    "create_goal_store",
    # Runtime Loop
    "IntegratedRuntimeLoop",
    "RuntimeLoopResult",
    # Goal Scheduler Bridge
    "GoalSchedulerBridge",
    "ScheduledGoal",
    "SchedulePriority",
    "ScheduleResult",
    "create_scheduler",
    # Autonomous Loop
    "AutonomousConfig",
    "AutonomousLoop",
    "AutonomyLevel",
    "CyclePhase",
    "CycleResult",
    "CycleState",
    "LoopStatus",
    "create_autonomous_loop",
    # Verification Gate
    "GapSeverity",
    "VerificationConfig",
    "VerificationGate",
    "VerificationGap",
    "VerificationLevel",
    "VerificationRequest",
    "VerificationResult",
    "VerificationStatus",
    "create_verification_gate",
    # KB Updater
    "KBPattern",
    "KBUpdateRequest",
    "KBUpdateResult",
    "KBUpdateStatus",
    "KBUpdateType",
    "KBUpdater",
    "KBUpdaterConfig",
    "create_kb_updater",
    # Shipping
    "ArtifactShipper",
    "ShippingArtifact",
    "ShippingDestination",
    "ShippingPriority",
    "ShippingRequest",
    "ShippingResult",
    "ShippingStatus",
    "ShipperConfig",
    "create_shipper",
    # Fusion
    "DataFusion",
    "FusionConfig",
    "FusionMode",
    "FusionRequest",
    "FusionResult",
    "FusionSource",
    "FusionSourceType",
    "create_fusion",
    # RAG Integration
    "ContextRequirement",
    "MergedContext",
    "RAGContext",
    "RecipeKnowledge",
    "RecipeRAGBridge",
    "RecipeStep",
    "RetrievedDocument",
    "TaskType",
    "build_context",
    "decompose_task",
    # Pre-Planning Retrieval Models
    "DecisionPoint",
    "DecisionType",
    "ExecutionStrategy",
    "PastExecution",
    "PlanWithRetrieval",
    "StrategySource",
    "SubgoalWithHints",
    "STRATEGY_TEMPLATES",
    # Similar Task Retriever
    "RetrievalConfig",
    "SimilarTaskRetriever",
    "create_retriever",
    "extract_strategy_from_execution",
    "format_hints_for_planning",
    # Long-Horizon Planner
    "PlannerConfig",
    "LongHorizonPlannerWithRetrieval",
    "create_planner",
]