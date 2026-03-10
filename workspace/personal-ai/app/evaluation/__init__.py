"""Output Evaluation Module.

Provides comprehensive evaluation of output artifacts for quality,
gating decisions, and promotion/shipping readiness.

Key Components:
- EvaluationInput: Normalized input for evaluation
- EvaluationResult: Structured result with scores and decisions
- OutputEvaluator: Main evaluation service
- ArtifactNormalizer: Normalizes different artifact types
- RuleBasedEvaluator: Type-specific evaluation rules

Supported Artifact Types:
- Recipe outputs
- Documentation outputs
- KB update candidates
- Runtime result artifacts
- Repair patterns
- Tutorial artifacts

Example:
    from app.evaluation import OutputEvaluator, evaluate_recipe_output

    # Using convenience function
    result = evaluate_recipe_output(recipe, domain="houdini")
    if result.shippable:
        ship_artifact(recipe)

    # Using evaluator instance
    evaluator = OutputEvaluator()
    result = evaluator.evaluate_recipe_output(recipe)
    print(result.summary())
"""

from app.evaluation.models import (
    ArtifactKind,
    EvaluationDecision,
    EvaluationInput,
    EvaluationResult,
    EvaluationSummary,
    GateDecision,
    QualityDimension,
    QualityDimensionScore,
    ScoreBand,
    SourceType,
    score_to_band,
)
from app.evaluation.normalizer import (
    ArtifactNormalizer,
    normalize_documentation_output,
    normalize_kb_candidate,
    normalize_recipe_output,
    normalize_repair_pattern,
    normalize_runtime_result,
    normalize_tutorial_artifact,
)
from app.evaluation.scoring import (
    CompositeScorer,
    DimensionScorer,
    ScoringConfig,
)
from app.evaluation.rules import (
    ArtifactEvaluationRules,
    DEFAULT_RULES,
    RuleBasedEvaluator,
)
from app.evaluation.service import (
    OutputEvaluator,
    OutputEvaluatorConfig,
    evaluate_output,
    evaluate_outputs,
    get_evaluator,
    should_promote_output,
    should_ship_output,
    should_update_kb,
)

__all__ = [
    # Models
    "ArtifactKind",
    "EvaluationDecision",
    "EvaluationInput",
    "EvaluationResult",
    "EvaluationSummary",
    "GateDecision",
    "QualityDimension",
    "QualityDimensionScore",
    "ScoreBand",
    "SourceType",
    "score_to_band",
    # Normalizer
    "ArtifactNormalizer",
    "normalize_recipe_output",
    "normalize_documentation_output",
    "normalize_kb_candidate",
    "normalize_runtime_result",
    "normalize_repair_pattern",
    "normalize_tutorial_artifact",
    # Scoring
    "CompositeScorer",
    "DimensionScorer",
    "ScoringConfig",
    # Rules
    "ArtifactEvaluationRules",
    "DEFAULT_RULES",
    "RuleBasedEvaluator",
    # Service
    "OutputEvaluator",
    "OutputEvaluatorConfig",
    "evaluate_output",
    "evaluate_outputs",
    "get_evaluator",
    "should_promote_output",
    "should_ship_output",
    "should_update_kb",
]