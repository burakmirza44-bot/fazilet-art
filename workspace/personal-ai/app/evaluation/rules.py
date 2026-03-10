"""Evaluation Rules Module.

Provides artifact-type-specific evaluation rules and criteria.
Each artifact kind has different requirements and scoring priorities.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.evaluation.models import (
    ArtifactKind,
    EvaluationDecision,
    EvaluationInput,
    EvaluationResult,
    GateDecision,
    QualityDimension,
    QualityDimensionScore,
    score_to_band,
)
from app.evaluation.scoring import (
    CompositeScorer,
    DimensionScorer,
    ScoringConfig,
)


@dataclass
class ArtifactEvaluationRules:
    """Evaluation rules for a specific artifact kind."""

    artifact_kind: ArtifactKind
    required_dimensions: list[str] = field(default_factory=list)
    optional_dimensions: list[str] = field(default_factory=list)
    required_content_fields: list[str] = field(default_factory=list)
    critical_threshold: float = 0.5
    pass_threshold: float = 0.60
    promotion_threshold: float = 0.70
    shipping_threshold: float = 0.80
    dimension_weights: dict[str, float] = field(default_factory=dict)


# Default rules for each artifact kind
DEFAULT_RULES: dict[ArtifactKind, ArtifactEvaluationRules] = {
    ArtifactKind.RECIPE_OUTPUT: ArtifactEvaluationRules(
        artifact_kind=ArtifactKind.RECIPE_OUTPUT,
        required_dimensions=[
            QualityDimension.CORRECTNESS.value,
            QualityDimension.COMPLETENESS.value,
            QualityDimension.STRUCTURAL_VALIDITY.value,
            QualityDimension.SAFETY.value,
            QualityDimension.ACTIONABILITY.value,
        ],
        optional_dimensions=[
            QualityDimension.CLARITY.value,
            QualityDimension.REUSABILITY.value,
            QualityDimension.PROVENANCE_QUALITY.value,
            QualityDimension.DEPENDENCY_INTEGRITY.value,
            QualityDimension.EXECUTOR_COMPATIBILITY.value,
        ],
        required_content_fields=["steps", "name", "domain"],
        dimension_weights={
            QualityDimension.CORRECTNESS.value: 1.5,
            QualityDimension.STRUCTURAL_VALIDITY.value: 1.5,
            QualityDimension.SAFETY.value: 2.0,
            QualityDimension.ACTIONABILITY.value: 1.2,
        },
    ),
    ArtifactKind.DOCUMENTATION_OUTPUT: ArtifactEvaluationRules(
        artifact_kind=ArtifactKind.DOCUMENTATION_OUTPUT,
        required_dimensions=[
            QualityDimension.CLARITY.value,
            QualityDimension.COMPLETENESS.value,
            QualityDimension.INFORMATION_DENSITY.value,
        ],
        optional_dimensions=[
            QualityDimension.USABILITY.value,
            QualityDimension.PROVENANCE_QUALITY.value,
            QualityDimension.DOCUMENTATION_READABILITY.value,
        ],
        required_content_fields=["content", "title"],
        pass_threshold=0.55,
        dimension_weights={
            QualityDimension.CLARITY.value: 1.5,
            QualityDimension.INFORMATION_DENSITY.value: 1.3,
        },
    ),
    ArtifactKind.KB_CANDIDATE: ArtifactEvaluationRules(
        artifact_kind=ArtifactKind.KB_CANDIDATE,
        required_dimensions=[
            QualityDimension.PROVENANCE_QUALITY.value,
            QualityDimension.NOVELTY.value,
            QualityDimension.INFORMATION_DENSITY.value,
            QualityDimension.CORRECTNESS.value,
        ],
        optional_dimensions=[
            QualityDimension.USABILITY.value,
            QualityDimension.KB_DEDUPE_QUALITY.value,
            QualityDimension.DOMAIN_COVERAGE.value,
        ],
        required_content_fields=["content", "domain"],
        promotion_threshold=0.75,
        dimension_weights={
            QualityDimension.PROVENANCE_QUALITY.value: 1.8,
            QualityDimension.NOVELTY.value: 1.5,
            QualityDimension.CORRECTNESS.value: 1.5,
        },
    ),
    ArtifactKind.RUNTIME_RESULT: ArtifactEvaluationRules(
        artifact_kind=ArtifactKind.RUNTIME_RESULT,
        required_dimensions=[
            QualityDimension.CORRECTNESS.value,
            QualityDimension.COMPLETENESS.value,
            QualityDimension.PROVENANCE_QUALITY.value,
        ],
        optional_dimensions=[
            QualityDimension.REUSABILITY.value,
            QualityDimension.CONSISTENCY.value,
        ],
        required_content_fields=["success", "steps"],
        pass_threshold=0.50,
        dimension_weights={
            QualityDimension.CORRECTNESS.value: 1.5,
        },
    ),
    ArtifactKind.REPAIR_PATTERN: ArtifactEvaluationRules(
        artifact_kind=ArtifactKind.REPAIR_PATTERN,
        required_dimensions=[
            QualityDimension.CORRECTNESS.value,
            QualityDimension.ACTIONABILITY.value,
            QualityDimension.REUSABILITY.value,
        ],
        optional_dimensions=[
            QualityDimension.PROVENANCE_QUALITY.value,
            QualityDimension.CLARITY.value,
        ],
        required_content_fields=["error_type", "repair_strategy"],
        promotion_threshold=0.70,
        dimension_weights={
            QualityDimension.ACTIONABILITY.value: 1.5,
            QualityDimension.REUSABILITY.value: 1.3,
        },
    ),
    ArtifactKind.TUTORIAL_ARTIFACT: ArtifactEvaluationRules(
        artifact_kind=ArtifactKind.TUTORIAL_ARTIFACT,
        required_dimensions=[
            QualityDimension.CLARITY.value,
            QualityDimension.COMPLETENESS.value,
            QualityDimension.ACTIONABILITY.value,
        ],
        optional_dimensions=[
            QualityDimension.PROVENANCE_QUALITY.value,
            QualityDimension.INFORMATION_DENSITY.value,
        ],
        required_content_fields=["source", "content"],
        pass_threshold=0.55,
        dimension_weights={
            QualityDimension.CLARITY.value: 1.5,
            QualityDimension.ACTIONABILITY.value: 1.3,
        },
    ),
    ArtifactKind.SHIPPING_ARTIFACT: ArtifactEvaluationRules(
        artifact_kind=ArtifactKind.SHIPPING_ARTIFACT,
        required_dimensions=[
            QualityDimension.CORRECTNESS.value,
            QualityDimension.COMPLETENESS.value,
            QualityDimension.SAFETY.value,
            QualityDimension.PROVENANCE_QUALITY.value,
        ],
        optional_dimensions=[
            QualityDimension.USABILITY.value,
            QualityDimension.CONSISTENCY.value,
        ],
        required_content_fields=["artifact_id", "content"],
        shipping_threshold=0.85,
        dimension_weights={
            QualityDimension.CORRECTNESS.value: 1.8,
            QualityDimension.SAFETY.value: 2.0,
        },
    ),
    ArtifactKind.VERIFICATION_RESULT: ArtifactEvaluationRules(
        artifact_kind=ArtifactKind.VERIFICATION_RESULT,
        required_dimensions=[
            QualityDimension.CORRECTNESS.value,
            QualityDimension.COMPLETENESS.value,
        ],
        optional_dimensions=[
            QualityDimension.PROVENANCE_QUALITY.value,
        ],
        required_content_fields=["verified"],
        pass_threshold=0.60,
    ),
    ArtifactKind.UNKNOWN: ArtifactEvaluationRules(
        artifact_kind=ArtifactKind.UNKNOWN,
        required_dimensions=[
            QualityDimension.COMPLETENESS.value,
            QualityDimension.STRUCTURAL_VALIDITY.value,
        ],
        optional_dimensions=[],
        required_content_fields=[],
        pass_threshold=0.50,
    ),
}


class RuleBasedEvaluator:
    """Evaluates artifacts using type-specific rules."""

    def __init__(
        self,
        config: ScoringConfig | None = None,
        rules: dict[ArtifactKind, ArtifactEvaluationRules] | None = None,
    ):
        """Initialize the evaluator.

        Args:
            config: Optional scoring configuration
            rules: Optional custom rules by artifact kind
        """
        self._config = config or ScoringConfig()
        self._rules = rules or DEFAULT_RULES
        self._dimension_scorer = DimensionScorer(self._config)
        self._composite_scorer = CompositeScorer(self._config)

    def evaluate(self, input_data: EvaluationInput) -> EvaluationResult:
        """Evaluate an artifact using appropriate rules.

        Args:
            input_data: Normalized artifact input

        Returns:
            EvaluationResult with scores and decisions
        """
        # Get rules for artifact kind
        kind = ArtifactKind(input_data.artifact_kind)
        rules = self._rules.get(kind, DEFAULT_RULES[ArtifactKind.UNKNOWN])

        # Score dimensions
        dimension_scores = self._score_dimensions(input_data, rules)

        # Calculate overall score
        overall_score = self._composite_scorer.calculate_overall_score(dimension_scores)

        # Apply penalties
        overall_score = self._apply_penalties(overall_score, input_data, rules, dimension_scores)

        # Determine decision
        decision = self._determine_decision(overall_score, dimension_scores, rules)

        # Identify strengths and weaknesses
        strengths = self._composite_scorer.identify_strengths(dimension_scores)
        weaknesses = self._composite_scorer.identify_weaknesses(dimension_scores)

        # Identify critical failures
        critical_failures = self._composite_scorer.identify_critical_failures(dimension_scores)

        # Generate warnings
        warnings = self._generate_warnings(input_data, rules, dimension_scores)

        # Determine gate recommendations
        promotion_rec, shipping_rec, kb_rec = self._determine_gate_recommendations(
            overall_score, decision, dimension_scores, rules
        )

        # Generate rationale
        rationale = self._generate_rationale(
            overall_score, decision, strengths, weaknesses, critical_failures
        )

        # Create result
        return EvaluationResult.create(
            artifact_id=input_data.artifact_id,
            artifact_kind=input_data.artifact_kind,
            domain=input_data.domain,
            overall_score=overall_score,
            decision=decision.value,
            quality_dimensions=dimension_scores,
            critical_failures=critical_failures,
            warnings=warnings,
            strengths=strengths,
            weaknesses=weaknesses,
            rationale=rationale,
            promotion_recommendation=promotion_rec,
            shipping_recommendation=shipping_rec,
            kb_recommendation=kb_rec,
            reusable=overall_score >= 0.70 and self._check_reusable(dimension_scores),
            requires_revision=decision in (EvaluationDecision.REVISE, EvaluationDecision.ACCEPT_WITH_WARNINGS),
            provenance_ok=self._check_provenance(input_data),
        )

    def _score_dimensions(
        self,
        input_data: EvaluationInput,
        rules: ArtifactEvaluationRules,
    ) -> list[QualityDimensionScore]:
        """Score all relevant dimensions.

        Args:
            input_data: Evaluation input
            rules: Evaluation rules

        Returns:
            List of dimension scores
        """
        scores: list[QualityDimensionScore] = []

        # Score required dimensions
        for dim in rules.required_dimensions:
            score = self._score_dimension(dim, input_data)
            score.critical = True
            scores.append(score)

        # Score optional dimensions
        for dim in rules.optional_dimensions:
            score = self._score_dimension(dim, input_data)
            score.critical = False
            scores.append(score)

        return scores

    def _score_dimension(
        self,
        dimension: str,
        input_data: EvaluationInput,
    ) -> QualityDimensionScore:
        """Score a single dimension.

        Args:
            dimension: Dimension name
            input_data: Evaluation input

        Returns:
            QualityDimensionScore
        """
        content = input_data.content
        verification = input_data.verification_metadata
        provenance = input_data.provenance_metadata
        runtime = input_data.runtime_metadata

        score = 0.5
        evidence: list[str] = []
        rationale = ""

        if dimension == QualityDimension.CORRECTNESS.value:
            score, evidence = self._dimension_scorer.score_correctness(content, verification)
            rationale = "Verification and error analysis"

        elif dimension == QualityDimension.COMPLETENESS.value:
            rules = self._rules.get(ArtifactKind(input_data.artifact_kind), DEFAULT_RULES[ArtifactKind.UNKNOWN])
            required = rules.required_content_fields
            score, evidence = self._dimension_scorer.score_completeness(content, required)
            rationale = f"Required fields presence: {len(required)} fields"

        elif dimension == QualityDimension.STRUCTURAL_VALIDITY.value:
            score, evidence = self._dimension_scorer.score_structural_validity(content)
            rationale = "Structure and schema validation"

        elif dimension == QualityDimension.SAFETY.value:
            safety_meta = input_data.shipping_metadata.get("safety", {})
            score, evidence = self._dimension_scorer.score_safety(content, safety_meta)
            rationale = "Safety checks and dangerous patterns"

        elif dimension == QualityDimension.PROVENANCE_QUALITY.value:
            score, evidence = self._dimension_scorer.score_provenance_quality(provenance)
            rationale = "Provenance metadata completeness"

        elif dimension == QualityDimension.REUSABILITY.value:
            score, evidence = self._dimension_scorer.score_reusability(content, runtime)
            rationale = "Parameterization and usage history"

        elif dimension == QualityDimension.CLARITY.value:
            score, evidence = self._dimension_scorer.score_clarity(content)
            rationale = "Naming and documentation clarity"

        elif dimension == QualityDimension.ACTIONABILITY.value:
            score, evidence = self._dimension_scorer.score_actionability(content, verification)
            rationale = "Actionable steps and criteria"

        elif dimension == QualityDimension.INFORMATION_DENSITY.value:
            score, evidence = self._dimension_scorer.score_information_density(content)
            rationale = "Information-to-filler ratio"

        elif dimension == QualityDimension.NOVELTY.value:
            # Would need existing entries for comparison
            score, evidence = self._dimension_scorer.score_novelty(content)
            rationale = "Novelty vs existing entries"

        else:
            rationale = "Default neutral score"

        return QualityDimensionScore(
            dimension=dimension,
            score=score,
            rationale=rationale,
            evidence=evidence,
            critical=False,
        )

    def _apply_penalties(
        self,
        score: float,
        input_data: EvaluationInput,
        rules: ArtifactEvaluationRules,
        dimension_scores: list[QualityDimensionScore],
    ) -> float:
        """Apply penalties to the overall score.

        Args:
            score: Current score
            input_data: Evaluation input
            rules: Evaluation rules
            dimension_scores: Dimension scores

        Returns:
            Adjusted score
        """
        adjusted = score

        # Missing required fields penalty
        missing = [f for f in rules.required_content_fields if f not in input_data.content]
        if missing:
            adjusted -= len(missing) * self._config.missing_field_penalty

        # Weak provenance penalty
        prov_score = next((s for s in dimension_scores if s.dimension == QualityDimension.PROVENANCE_QUALITY.value), None)
        if prov_score and prov_score.score < 0.5:
            adjusted -= self._config.weak_provenance_penalty

        return max(0.0, min(1.0, adjusted))

    def _determine_decision(
        self,
        score: float,
        dimension_scores: list[QualityDimensionScore],
        rules: ArtifactEvaluationRules,
    ) -> EvaluationDecision:
        """Determine evaluation decision.

        Args:
            score: Overall score
            dimension_scores: Dimension scores
            rules: Evaluation rules

        Returns:
            EvaluationDecision
        """
        # Check for critical failures
        for dim_score in dimension_scores:
            if dim_score.critical and dim_score.score < rules.critical_threshold:
                return EvaluationDecision.BLOCK

        # Score-based decisions
        if score >= 0.90:
            return EvaluationDecision.PROMOTE
        elif score >= 0.80:
            return EvaluationDecision.SHIP_READY
        elif score >= 0.70:
            return EvaluationDecision.ACCEPT
        elif score >= rules.pass_threshold:
            # Check for warnings
            warnings = sum(1 for s in dimension_scores if s.score < 0.6)
            if warnings > 0:
                return EvaluationDecision.ACCEPT_WITH_WARNINGS
            return EvaluationDecision.ACCEPT
        elif score >= 0.40:
            return EvaluationDecision.REVISE
        else:
            return EvaluationDecision.REJECT

    def _generate_warnings(
        self,
        input_data: EvaluationInput,
        rules: ArtifactEvaluationRules,
        dimension_scores: list[QualityDimensionScore],
    ) -> list[str]:
        """Generate warning messages.

        Args:
            input_data: Evaluation input
            rules: Evaluation rules
            dimension_scores: Dimension scores

        Returns:
            List of warnings
        """
        warnings = []

        # Missing fields
        missing = [f for f in rules.required_content_fields if f not in input_data.content]
        if missing:
            warnings.append(f"Missing required fields: {', '.join(missing)}")

        # Low dimension scores
        for dim_score in dimension_scores:
            if dim_score.score < 0.5:
                warnings.append(f"Low score in {dim_score.dimension}: {dim_score.score:.2f}")

        # Weak provenance
        if not input_data.provenance_metadata:
            warnings.append("No provenance metadata provided")

        return warnings

    def _determine_gate_recommendations(
        self,
        score: float,
        decision: EvaluationDecision,
        dimension_scores: list[QualityDimensionScore],
        rules: ArtifactEvaluationRules,
    ) -> tuple[str, str, str]:
        """Determine gate recommendations.

        Args:
            score: Overall score
            decision: Evaluation decision
            dimension_scores: Dimension scores
            rules: Evaluation rules

        Returns:
            Tuple of (promotion, shipping, kb) recommendations
        """
        # Promotion gate
        if score >= rules.promotion_threshold and decision not in (EvaluationDecision.BLOCK, EvaluationDecision.REJECT):
            promotion = GateDecision.PROMOTION_ALLOWED.value
        else:
            promotion = GateDecision.PROMOTION_BLOCKED.value

        # Shipping gate
        if score >= rules.shipping_threshold and decision in (EvaluationDecision.ACCEPT, EvaluationDecision.PROMOTE, EvaluationDecision.SHIP_READY):
            shipping = GateDecision.SHIPPING_ALLOWED.value
        else:
            shipping = GateDecision.SHIPPING_BLOCKED.value

        # KB update gate
        prov_ok = any(s.dimension == QualityDimension.PROVENANCE_QUALITY.value and s.score >= 0.5 for s in dimension_scores)
        novelty_ok = any(s.dimension == QualityDimension.NOVELTY.value and s.score >= 0.5 for s in dimension_scores)

        if score >= 0.65 and prov_ok and decision not in (EvaluationDecision.BLOCK, EvaluationDecision.REJECT):
            kb = GateDecision.KB_UPDATE_ALLOWED.value
        else:
            kb = GateDecision.KB_UPDATE_BLOCKED.value

        return promotion, shipping, kb

    def _check_reusable(self, dimension_scores: list[QualityDimensionScore]) -> bool:
        """Check if artifact is reusable.

        Args:
            dimension_scores: Dimension scores

        Returns:
            True if reusable
        """
        reusability = next((s for s in dimension_scores if s.dimension == QualityDimension.REUSABILITY.value), None)
        actionability = next((s for s in dimension_scores if s.dimension == QualityDimension.ACTIONABILITY.value), None)

        reuse_ok = reusability and reusability.score >= 0.5
        action_ok = actionability and actionability.score >= 0.5

        return reuse_ok or action_ok

    def _check_provenance(self, input_data: EvaluationInput) -> bool:
        """Check if provenance is acceptable.

        Args:
            input_data: Evaluation input

        Returns:
            True if provenance is ok
        """
        prov = input_data.provenance_metadata
        if not prov:
            return False

        # Need at least source and timestamp
        return bool(prov.get("source") or prov.get("created_at"))

    def _generate_rationale(
        self,
        score: float,
        decision: EvaluationDecision,
        strengths: list[str],
        weaknesses: list[str],
        critical_failures: list[str],
    ) -> str:
        """Generate evaluation rationale.

        Args:
            score: Overall score
            decision: Decision
            strengths: Strengths list
            weaknesses: Weaknesses list
            critical_failures: Critical failures

        Returns:
            Rationale string
        """
        parts = [f"Score: {score:.2f}, Decision: {decision.value}"]

        if critical_failures:
            parts.append(f"Critical issues: {len(critical_failures)}")

        if strengths:
            parts.append(f"Strengths: {len(strengths)}")

        if weaknesses:
            parts.append(f"Weaknesses: {len(weaknesses)}")

        return ". ".join(parts)