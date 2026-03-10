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

Post-Execution Verification:
    from app.evaluation import ExecutionVerifier, ExpectedState

    # Create verifier
    verifier = ExecutionVerifier()

    # Define expected state
    expected = ExpectedState(
        new_elements_visible=["comp1"],
        node_count=1
    )

    # Verify execution
    report = verifier.verify_execution(
        action="Create comp1 node",
        before_screenshot="before.png",
        after_screenshot="after.png",
        expected_state=expected,
        app="touchdesigner"
    )
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
from app.evaluation.verification_models import (
    AssertionType,
    ExpectedState,
    VerificationAssertion,
    VerificationMethod,
    VisualVerificationResult,
    StateQueryVerificationResult,
    ExecutionVerificationReport,
)
from app.evaluation.execution_verifier import (
    ExecutionVerifier,
    VerifierConfig,
    create_execution_verifier,
)
from app.evaluation.visual_verifier import (
    VisualVerifier,
    VisualUnderstandingPipeline,
    create_visual_verifier,
)
from app.evaluation.state_verifier import (
    StateQueryVerifier,
    ApplicationState,
    create_state_query_verifier,
)
from app.evaluation.screenshot_utils import (
    ScreenshotCapture,
    TDScreenshotCapture,
    HoudiniScreenshotCapture,
    take_screenshot,
    take_td_screenshot,
    take_houdini_screenshot,
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
    # Verification Models
    "AssertionType",
    "ExpectedState",
    "VerificationAssertion",
    "VerificationMethod",
    "VisualVerificationResult",
    "StateQueryVerificationResult",
    "ExecutionVerificationReport",
    # Verifiers
    "ExecutionVerifier",
    "VerifierConfig",
    "create_execution_verifier",
    "VisualVerifier",
    "VisualUnderstandingPipeline",
    "create_visual_verifier",
    "StateQueryVerifier",
    "ApplicationState",
    "create_state_query_verifier",
    # Screenshot Utils
    "ScreenshotCapture",
    "TDScreenshotCapture",
    "HoudiniScreenshotCapture",
    "take_screenshot",
    "take_td_screenshot",
    "take_houdini_screenshot",
]