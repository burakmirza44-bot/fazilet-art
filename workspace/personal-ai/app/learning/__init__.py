"""Learning Module.

Provides recipe execution, tutorial distillation, and learning-related functionality.
"""

from app.learning.recipe_executor import (
    BridgeExecutor,
    HoudiniBridgeExecutor,
    PreconditionsReport,
    RecipeExecutor,
    TDBridgeExecutor,
)
from app.learning.tutorial_distillation import (
    BatchDistiller,
    DistilledKnowledgeStore,
    DistilledRecipe,
    ExtractionMetrics,
    KnowledgeType,
    RecipeStep,
    TutorialDistiller,
    create_store,
    distill_single,
)

__all__ = [
    # Recipe executor
    "BridgeExecutor",
    "HoudiniBridgeExecutor",
    "PreconditionsReport",
    "RecipeExecutor",
    "TDBridgeExecutor",
    # Tutorial distillation
    "BatchDistiller",
    "DistilledKnowledgeStore",
    "DistilledRecipe",
    "ExtractionMetrics",
    "KnowledgeType",
    "RecipeStep",
    "TutorialDistiller",
    "create_store",
    "distill_single",
]