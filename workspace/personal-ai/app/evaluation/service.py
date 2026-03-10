"""Output Evaluator Service Module.

Provides the main entry points for output evaluation,
gating decisions, and integration with other modules.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.evaluation.models import (
    ArtifactKind,
    EvaluationDecision,
    EvaluationInput,
    EvaluationResult,
    EvaluationSummary,
    GateDecision,
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
from app.evaluation.rules import RuleBasedEvaluator
from app.evaluation.scoring import ScoringConfig


@dataclass
class OutputEvaluatorConfig:
    """Configuration for the output evaluator."""

    enable_caching: bool = True
    strict_mode: bool = False
    auto_archive_weak: bool = True
    min_promotion_score: float = 0.70
    min_shipping_score: float = 0.80
    min_kb_score: float = 0.65


class OutputEvaluator:
    """Main output evaluation service.

    Provides unified interface for evaluating different artifact types
    and making gating decisions for promotion, shipping, and KB updates.

    Example:
        evaluator = OutputEvaluator()
        result = evaluator.evaluate_recipe_output(recipe, domain="houdini")
        if result.shippable:
            ship_artifact(recipe)
    """

    def __init__(
        self,
        config: OutputEvaluatorConfig | None = None,
        scoring_config: ScoringConfig | None = None,
    ):
        """Initialize the output evaluator.

        Args:
            config: Optional evaluator configuration
            scoring_config: Optional scoring configuration
        """
        self._config = config or OutputEvaluatorConfig()
        self._scoring_config = scoring_config or ScoringConfig()
        self._normalizer = ArtifactNormalizer()
        self._evaluator = RuleBasedEvaluator(self._scoring_config)
        self._result_cache: dict[str, EvaluationResult] = {}

    def evaluate(self, input_data: EvaluationInput) -> EvaluationResult:
        """Evaluate a normalized artifact.

        Main entry point for evaluation.

        Args:
            input_data: Normalized artifact input

        Returns:
            EvaluationResult with scores and decisions
        """
        # Check cache
        if self._config.enable_caching:
            cache_key = f"{input_data.artifact_id}:{input_data.artifact_kind}"
            if cache_key in self._result_cache:
                return self._result_cache[cache_key]

        # Perform evaluation
        result = self._evaluator.evaluate(input_data)

        # Cache result
        if self._config.enable_caching:
            self._result_cache[cache_key] = result

        return result

    def evaluate_outputs(
        self,
        inputs: list[EvaluationInput],
    ) -> EvaluationSummary:
        """Evaluate multiple outputs and provide summary.

        Args:
            inputs: List of normalized artifact inputs

        Returns:
            EvaluationSummary with aggregated metrics
        """
        summary = EvaluationSummary()

        for input_data in inputs:
            result = self.evaluate(input_data)
            summary.add_result(result)

        return summary

    def evaluate_recipe_output(
        self,
        recipe: dict[str, Any],
        domain: str = "",
        execution_id: str = "",
        verification: dict[str, Any] | None = None,
        provenance: dict[str, Any] | None = None,
    ) -> EvaluationResult:
        """Evaluate a recipe output.

        Args:
            recipe: Recipe dictionary
            domain: Domain
            execution_id: Execution ID
            verification: Verification metadata
            provenance: Provenance metadata

        Returns:
            EvaluationResult
        """
        input_data = normalize_recipe_output(
            recipe=recipe,
            domain=domain,
            execution_id=execution_id,
            verification=verification,
            provenance=provenance,
        )
        return self.evaluate(input_data)

    def evaluate_documentation_output(
        self,
        documentation: dict[str, Any],
        domain: str = "",
        source_id: str = "",
        provenance: dict[str, Any] | None = None,
    ) -> EvaluationResult:
        """Evaluate a documentation output.

        Args:
            documentation: Documentation dictionary
            domain: Domain
            source_id: Source ID
            provenance: Provenance metadata

        Returns:
            EvaluationResult
        """
        input_data = normalize_documentation_output(
            documentation=documentation,
            domain=domain,
            source_id=source_id,
            provenance=provenance,
        )
        return self.evaluate(input_data)

    def evaluate_kb_candidate(
        self,
        candidate: dict[str, Any],
        domain: str = "",
        source_id: str = "",
        provenance: dict[str, Any] | None = None,
    ) -> EvaluationResult:
        """Evaluate a KB update candidate.

        Args:
            candidate: KB candidate dictionary
            domain: Domain
            source_id: Source ID
            provenance: Provenance metadata

        Returns:
            EvaluationResult
        """
        input_data = normalize_kb_candidate(
            candidate=candidate,
            domain=domain,
            source_id=source_id,
            provenance=provenance,
        )
        return self.evaluate(input_data)

    def evaluate_runtime_result(
        self,
        result: dict[str, Any],
        domain: str = "",
        run_id: str = "",
    ) -> EvaluationResult:
        """Evaluate a runtime result.

        Args:
            result: Runtime result dictionary
            domain: Domain
            run_id: Run ID

        Returns:
            EvaluationResult
        """
        input_data = normalize_runtime_result(
            result=result,
            domain=domain,
            run_id=run_id,
        )
        return self.evaluate(input_data)

    def evaluate_repair_pattern(
        self,
        pattern: dict[str, Any],
        domain: str = "",
        source_id: str = "",
    ) -> EvaluationResult:
        """Evaluate a repair pattern.

        Args:
            pattern: Repair pattern dictionary
            domain: Domain
            source_id: Source ID

        Returns:
            EvaluationResult
        """
        input_data = normalize_repair_pattern(
            pattern=pattern,
            domain=domain,
            source_id=source_id,
        )
        return self.evaluate(input_data)

    def evaluate_tutorial_artifact(
        self,
        artifact: dict[str, Any],
        domain: str = "",
        source_id: str = "",
    ) -> EvaluationResult:
        """Evaluate a tutorial/distillation artifact.

        Args:
            artifact: Tutorial artifact dictionary
            domain: Domain
            source_id: Source ID

        Returns:
            EvaluationResult
        """
        input_data = normalize_tutorial_artifact(
            artifact=artifact,
            domain=domain,
            source_id=source_id,
        )
        return self.evaluate(input_data)

    # Gate decision helpers

    def should_promote_output(self, result: EvaluationResult) -> bool:
        """Check if output should be promoted.

        Args:
            result: Evaluation result

        Returns:
            True if promotion is allowed
        """
        return result.promotion_recommendation == GateDecision.PROMOTION_ALLOWED.value

    def should_ship_output(self, result: EvaluationResult) -> bool:
        """Check if output should be shipped.

        Args:
            result: Evaluation result

        Returns:
            True if shipping is allowed
        """
        return result.shipping_recommendation == GateDecision.SHIPPING_ALLOWED.value

    def should_update_kb(self, result: EvaluationResult) -> bool:
        """Check if output should update knowledge base.

        Args:
            result: Evaluation result

        Returns:
            True if KB update is allowed
        """
        return result.kb_recommendation == GateDecision.KB_UPDATE_ALLOWED.value

    def is_reusable(self, result: EvaluationResult) -> bool:
        """Check if output is reusable.

        Args:
            result: Evaluation result

        Returns:
            True if reusable
        """
        return result.reusable

    # Convenience functions for common queries

    def get_promotable_artifacts(
        self,
        results: list[EvaluationResult],
    ) -> list[EvaluationResult]:
        """Filter results to promotable artifacts.

        Args:
            results: List of evaluation results

        Returns:
            List of promotable results
        """
        return [r for r in results if self.should_promote_output(r)]

    def get_shippable_artifacts(
        self,
        results: list[EvaluationResult],
    ) -> list[EvaluationResult]:
        """Filter results to shippable artifacts.

        Args:
            results: List of evaluation results

        Returns:
            List of shippable results
        """
        return [r for r in results if self.should_ship_output(r)]

    def get_kb_updatable_artifacts(
        self,
        results: list[EvaluationResult],
    ) -> list[EvaluationResult]:
        """Filter results to KB-updatable artifacts.

        Args:
            results: List of evaluation results

        Returns:
            List of KB-updatable results
        """
        return [r for r in results if self.should_update_kb(r)]

    def get_blocked_artifacts(
        self,
        results: list[EvaluationResult],
    ) -> list[EvaluationResult]:
        """Filter results to blocked artifacts.

        Args:
            results: List of evaluation results

        Returns:
            List of blocked results
        """
        return [r for r in results if r.has_critical_failures]

    def clear_cache(self) -> None:
        """Clear the result cache."""
        self._result_cache.clear()


# Module-level convenience functions

_default_evaluator: OutputEvaluator | None = None


def get_evaluator() -> OutputEvaluator:
    """Get the default output evaluator.

    Returns:
        Default OutputEvaluator instance
    """
    global _default_evaluator
    if _default_evaluator is None:
        _default_evaluator = OutputEvaluator()
    return _default_evaluator


def evaluate_output(
    artifact: dict[str, Any],
    artifact_kind: str | ArtifactKind,
    domain: str = "",
    source_id: str = "",
) -> EvaluationResult:
    """Evaluate an artifact using default evaluator.

    Convenience function for quick evaluation.

    Args:
        artifact: Artifact to evaluate
        artifact_kind: Kind of artifact
        domain: Domain
        source_id: Source ID

    Returns:
        EvaluationResult
    """
    evaluator = get_evaluator()
    input_data = evaluator._normalizer.normalize(
        artifact=artifact,
        artifact_kind=artifact_kind,
        domain=domain,
        source_id=source_id,
    )
    return evaluator.evaluate(input_data)


def evaluate_outputs(inputs: list[EvaluationInput]) -> EvaluationSummary:
    """Evaluate multiple outputs using default evaluator.

    Args:
        inputs: List of inputs

    Returns:
        EvaluationSummary
    """
    return get_evaluator().evaluate_outputs(inputs)


def should_promote_output(result: EvaluationResult) -> bool:
    """Check if output should be promoted.

    Args:
        result: Evaluation result

    Returns:
        True if promotion allowed
    """
    return get_evaluator().should_promote_output(result)


def should_ship_output(result: EvaluationResult) -> bool:
    """Check if output should be shipped.

    Args:
        result: Evaluation result

    Returns:
        True if shipping allowed
    """
    return get_evaluator().should_ship_output(result)


def should_update_kb(result: EvaluationResult) -> bool:
    """Check if output should update KB.

    Args:
        result: Evaluation result

    Returns:
        True if KB update allowed
    """
    return get_evaluator().should_update_kb(result)