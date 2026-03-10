"""Evaluation Scoring Module.

Provides quality dimension scoring logic for evaluating artifacts.
Implements deterministic, heuristic-based scoring that is inspectable
and testable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.evaluation.models import (
    ArtifactKind,
    QualityDimension,
    QualityDimensionScore,
)


@dataclass
class ScoringConfig:
    """Configuration for scoring behavior."""

    # Weights for different dimensions
    dimension_weights: dict[str, float] = field(default_factory=lambda: {
        QualityDimension.CORRECTNESS.value: 1.5,
        QualityDimension.COMPLETENESS.value: 1.3,
        QualityDimension.USABILITY.value: 1.0,
        QualityDimension.CLARITY.value: 1.0,
        QualityDimension.STRUCTURAL_VALIDITY.value: 1.5,
        QualityDimension.SAFETY.value: 2.0,
        QualityDimension.PROVENANCE_QUALITY.value: 1.2,
        QualityDimension.REUSABILITY.value: 1.0,
        QualityDimension.CONSISTENCY.value: 0.8,
        QualityDimension.ACTIONABILITY.value: 1.1,
    })

    # Critical dimensions (failure in these blocks promotion)
    critical_dimensions: list[str] = field(default_factory=lambda: [
        QualityDimension.CORRECTNESS.value,
        QualityDimension.SAFETY.value,
        QualityDimension.STRUCTURAL_VALIDITY.value,
    ])

    # Minimum scores for passing
    min_pass_score: float = 0.60
    min_promotion_score: float = 0.70
    min_shipping_score: float = 0.80

    # Penalties
    missing_field_penalty: float = 0.1
    weak_provenance_penalty: float = 0.15
    low_completeness_penalty: float = 0.2


class DimensionScorer:
    """Scores individual quality dimensions."""

    def __init__(self, config: ScoringConfig | None = None):
        """Initialize the scorer.

        Args:
            config: Optional scoring configuration
        """
        self._config = config or ScoringConfig()

    def score_correctness(
        self,
        content: dict[str, Any],
        verification: dict[str, Any],
    ) -> tuple[float, list[str]]:
        """Score correctness dimension.

        Args:
            content: Artifact content
            verification: Verification metadata

        Returns:
            Tuple of (score, evidence)
        """
        evidence: list[str] = []
        score = 0.5  # Start neutral

        # Check verification status
        if verification.get("verified"):
            score += 0.3
            evidence.append("Verification passed")

        if verification.get("tests_passed"):
            test_ratio = verification.get("tests_passed", 0) / max(verification.get("tests_total", 1), 1)
            score += test_ratio * 0.2
            evidence.append(f"Tests passed: {verification.get('tests_passed')}/{verification.get('tests_total')}")

        # Check for error indicators
        if content.get("errors") or content.get("error_count", 0) > 0:
            score -= 0.2
            evidence.append("Errors present in content")

        # Check for validation
        if content.get("validated") or verification.get("schema_valid"):
            score += 0.1
            evidence.append("Schema validation passed")

        return min(1.0, max(0.0, score)), evidence

    def score_completeness(
        self,
        content: dict[str, Any],
        required_fields: list[str],
    ) -> tuple[float, list[str]]:
        """Score completeness dimension.

        Args:
            content: Artifact content
            required_fields: List of required field names

        Returns:
            Tuple of (score, evidence)
        """
        evidence: list[str] = []

        if not required_fields:
            return 0.7, ["No required fields specified"]

        present = sum(1 for f in required_fields if f in content and content[f])
        total = len(required_fields)
        score = present / total if total > 0 else 0.5

        missing = [f for f in required_fields if f not in content or not content[f]]

        if present == total:
            evidence.append(f"All {total} required fields present")
        else:
            evidence.append(f"{present}/{total} required fields present")
            if missing:
                evidence.append(f"Missing: {', '.join(missing[:3])}")

        return score, evidence

    def score_structural_validity(
        self,
        content: dict[str, Any],
        schema: dict[str, Any] | None = None,
    ) -> tuple[float, list[str]]:
        """Score structural validity dimension.

        Args:
            content: Artifact content
            schema: Optional schema to validate against

        Returns:
            Tuple of (score, evidence)
        """
        evidence: list[str] = []
        score = 1.0

        # Basic structure checks
        if not isinstance(content, dict):
            return 0.0, ["Content is not a dictionary"]

        if not content:
            return 0.2, ["Content is empty"]

        # Check for valid JSON-serializable structure
        try:
            import json
            json.dumps(content)
            evidence.append("Content is JSON-serializable")
        except (TypeError, ValueError):
            score -= 0.3
            evidence.append("Content is not JSON-serializable")

        # Check for required structure based on schema
        if schema:
            if schema.get("type") == "object" and "properties" in schema:
                required = schema.get("required", [])
                missing = [r for r in required if r not in content]
                if missing:
                    score -= len(missing) * 0.1
                    evidence.append(f"Missing required properties: {missing}")

        # Check for common structural issues
        if "steps" in content:
            steps = content.get("steps", [])
            if not isinstance(steps, list):
                score -= 0.3
                evidence.append("Steps is not a list")
            elif len(steps) == 0:
                score -= 0.2
                evidence.append("Steps list is empty")
            else:
                evidence.append(f"Steps list has {len(steps)} items")

        return min(1.0, max(0.0, score)), evidence

    def score_safety(
        self,
        content: dict[str, Any],
        safety_metadata: dict[str, Any],
    ) -> tuple[float, list[str]]:
        """Score safety dimension.

        Args:
            content: Artifact content
            safety_metadata: Safety-related metadata

        Returns:
            Tuple of (score, evidence)
        """
        evidence: list[str] = []
        score = 1.0

        # Check safety metadata
        if safety_metadata.get("safety_checked"):
            evidence.append("Safety check performed")
        else:
            score -= 0.1
            evidence.append("No safety check recorded")

        if safety_metadata.get("safety_level") == "safe":
            score += 0.0  # Already at 1.0
            evidence.append("Safety level: safe")
        elif safety_metadata.get("safety_level") == "caution":
            score -= 0.2
            evidence.append("Safety level: caution")
        elif safety_metadata.get("safety_level") == "unsafe":
            score -= 0.5
            evidence.append("Safety level: unsafe")

        # Check for dangerous patterns
        content_str = str(content).lower()
        dangerous_patterns = ["delete all", "format disk", "rm -rf", "drop table"]
        for pattern in dangerous_patterns:
            if pattern in content_str:
                score -= 0.3
                evidence.append(f"Dangerous pattern detected: {pattern}")
                break

        # Check killswitch/safety guards
        if safety_metadata.get("killswitch_tested"):
            evidence.append("Killswitch tested")
        if safety_metadata.get("window_guard_active"):
            evidence.append("Window guard active")

        return min(1.0, max(0.0, score)), evidence

    def score_provenance_quality(
        self,
        provenance: dict[str, Any],
    ) -> tuple[float, list[str]]:
        """Score provenance quality dimension.

        Args:
            provenance: Provenance metadata

        Returns:
            Tuple of (score, evidence)
        """
        evidence: list[str] = []
        score = 0.0

        if not provenance:
            evidence.append("No provenance metadata")
            return 0.2, evidence

        # Check provenance components
        if provenance.get("source"):
            score += 0.2
            evidence.append(f"Source: {provenance.get('source')}")

        if provenance.get("created_at") or provenance.get("timestamp"):
            score += 0.15
            evidence.append("Timestamp present")

        if provenance.get("creator") or provenance.get("author"):
            score += 0.15
            evidence.append("Creator identified")

        if provenance.get("version"):
            score += 0.1
            evidence.append(f"Version: {provenance.get('version')}")

        if provenance.get("domain"):
            score += 0.1
            evidence.append(f"Domain: {provenance.get('domain')}")

        if provenance.get("trace_id") or provenance.get("run_id"):
            score += 0.15
            evidence.append("Trace/run ID present")

        if provenance.get("checksum") or provenance.get("hash"):
            score += 0.15
            evidence.append("Checksum present")

        return min(1.0, score), evidence

    def score_reusability(
        self,
        content: dict[str, Any],
        runtime_metadata: dict[str, Any],
    ) -> tuple[float, list[str]]:
        """Score reusability dimension.

        Args:
            content: Artifact content
            runtime_metadata: Runtime metadata

        Returns:
            Tuple of (score, evidence)
        """
        evidence: list[str] = []
        score = 0.5

        # Check for parameterization
        if content.get("parameters") or content.get("config"):
            score += 0.15
            evidence.append("Parameterized")

        # Check for documentation
        if content.get("description") or content.get("documentation"):
            score += 0.1
            evidence.append("Documented")

        # Check for dependencies being explicit
        if content.get("dependencies"):
            score += 0.1
            evidence.append("Dependencies explicit")

        # Check for tags/metadata for discovery
        if content.get("tags") or content.get("metadata"):
            score += 0.1
            evidence.append("Tagged")

        # Check usage history
        usage_count = runtime_metadata.get("usage_count", 0)
        if usage_count > 0:
            score += min(0.15, usage_count * 0.05)
            evidence.append(f"Used {usage_count} times")

        return min(1.0, score), evidence

    def score_clarity(
        self,
        content: dict[str, Any],
    ) -> tuple[float, list[str]]:
        """Score clarity dimension.

        Args:
            content: Artifact content

        Returns:
            Tuple of (score, evidence)
        """
        evidence: list[str] = []
        score = 0.5

        # Check for clear naming
        if content.get("name") or content.get("title"):
            name = content.get("name") or content.get("title", "")
            if len(name) > 5 and not name.startswith("untitled"):
                score += 0.15
                evidence.append("Clear name")

        # Check for descriptions
        description = content.get("description", "")
        if description:
            if len(description) > 20:
                score += 0.15
                evidence.append("Description present")
            else:
                evidence.append("Description too short")

        # Check step descriptions for recipes
        if "steps" in content:
            steps = content.get("steps", [])
            described_steps = 0
            for s in steps:
                if isinstance(s, dict) and s.get("description"):
                    described_steps += 1
                elif isinstance(s, str) and len(s) > 10:
                    described_steps += 1

            if described_steps == len(steps) and len(steps) > 0:
                score += 0.2
                evidence.append("All steps described")
            elif described_steps > 0:
                score += 0.1
                evidence.append(f"{described_steps}/{len(steps)} steps described")

        return min(1.0, score), evidence

    def score_actionability(
        self,
        content: dict[str, Any],
        verification: dict[str, Any],
    ) -> tuple[float, list[str]]:
        """Score actionability dimension.

        Args:
            content: Artifact content
            verification: Verification metadata

        Returns:
            Tuple of (score, evidence)
        """
        evidence: list[str] = []
        score = 0.4

        # Check for executable steps
        if content.get("steps"):
            steps = content.get("steps", [])
            actionable = 0
            for s in steps:
                if isinstance(s, dict):
                    if s.get("action") or s.get("command"):
                        actionable += 1
                elif isinstance(s, str) and s.strip():
                    actionable += 1

            if actionable == len(steps) and len(steps) > 0:
                score += 0.3
                evidence.append("All steps actionable")
            elif actionable > 0:
                score += 0.15
                evidence.append(f"{actionable}/{len(steps)} steps actionable")

        # Check for preconditions
        if content.get("preconditions"):
            score += 0.1
            evidence.append("Preconditions defined")

        # Check for expected outcomes
        if content.get("expected_outcome") or content.get("success_criteria"):
            score += 0.1
            evidence.append("Success criteria defined")

        # Check verification available
        if verification.get("verification_steps"):
            score += 0.1
            evidence.append("Verification steps available")

        return min(1.0, score), evidence

    def score_information_density(
        self,
        content: dict[str, Any],
    ) -> tuple[float, list[str]]:
        """Score information density dimension.

        Args:
            content: Artifact content

        Returns:
            Tuple of (score, evidence)
        """
        evidence: list[str] = []

        # Count non-empty fields
        def count_non_empty(obj: Any, depth: int = 0) -> int:
            if depth > 5:
                return 0
            count = 0
            if isinstance(obj, dict):
                for v in obj.values():
                    if v:
                        count += 1 + count_non_empty(v, depth + 1)
            elif isinstance(obj, list):
                for item in obj:
                    count += count_non_empty(item, depth + 1)
            return count

        non_empty = count_non_empty(content)
        total_keys = len(str(content))

        # Simple density calculation
        if total_keys == 0:
            return 0.3, ["Content appears empty"]

        # Calculate filler ratio
        content_str = str(content).lower()
        filler_words = ["the", "a", "an", "is", "are", "was", "were", "be", "been", "being"]
        filler_count = sum(content_str.count(f" {w} ") for w in filler_words)

        # Higher non-empty ratio = higher density
        density = min(1.0, non_empty / 20)  # Normalize

        if density > 0.7:
            evidence.append("High information density")
        elif density > 0.4:
            evidence.append("Moderate information density")
        else:
            evidence.append("Low information density")

        # Adjust for filler
        if filler_count > 50:
            density -= 0.1
            evidence.append("High filler content")

        return max(0.0, density), evidence

    def score_novelty(
        self,
        content: dict[str, Any],
        existing_entries: list[dict[str, Any]] | None = None,
    ) -> tuple[float, list[str]]:
        """Score novelty dimension.

        Args:
            content: Artifact content
            existing_entries: Existing entries to compare against

        Returns:
            Tuple of (score, evidence)
        """
        evidence: list[str] = []

        if not existing_entries:
            return 0.7, ["No existing entries to compare"]

        # Check for duplicates
        content_str = str(content)
        for entry in existing_entries:
            entry_str = str(entry)
            if content_str == entry_str:
                return 0.0, ["Exact duplicate found"]

        # Check for high similarity
        similarity_scores = []
        for entry in existing_entries:
            # Simple Jaccard similarity on words
            content_words = set(content_str.lower().split())
            entry_words = set(str(entry).lower().split())
            if content_words and entry_words:
                intersection = len(content_words & entry_words)
                union = len(content_words | entry_words)
                similarity = intersection / union if union > 0 else 0
                similarity_scores.append(similarity)

        if similarity_scores:
            max_similarity = max(similarity_scores)
            if max_similarity > 0.9:
                evidence.append(f"High similarity ({max_similarity:.2f}) to existing entry")
                return 0.2, evidence
            elif max_similarity > 0.7:
                evidence.append(f"Moderate similarity ({max_similarity:.2f}) to existing entry")
                return 0.5, evidence

        evidence.append("Novel content")
        return 0.9, evidence


class CompositeScorer:
    """Calculates composite scores from dimension scores."""

    def __init__(self, config: ScoringConfig | None = None):
        """Initialize the composite scorer.

        Args:
            config: Optional scoring configuration
        """
        self._config = config or ScoringConfig()

    def calculate_overall_score(
        self,
        dimension_scores: list[QualityDimensionScore],
    ) -> float:
        """Calculate weighted overall score.

        Args:
            dimension_scores: List of dimension scores

        Returns:
            Weighted overall score
        """
        if not dimension_scores:
            return 0.0

        total_weight = 0.0
        weighted_sum = 0.0

        for dim_score in dimension_scores:
            weight = self._config.dimension_weights.get(dim_score.dimension, 1.0)
            weighted_sum += dim_score.score * weight
            total_weight += weight

        if total_weight == 0:
            return 0.0

        return weighted_sum / total_weight

    def identify_critical_failures(
        self,
        dimension_scores: list[QualityDimensionScore],
    ) -> list[str]:
        """Identify critical failures.

        Args:
            dimension_scores: List of dimension scores

        Returns:
            List of critical failure descriptions
        """
        failures = []

        for dim_score in dimension_scores:
            if dim_score.dimension in self._config.critical_dimensions:
                if dim_score.score < 0.5:
                    failures.append(
                        f"Critical dimension '{dim_score.dimension}' scored {dim_score.score:.2f}: {dim_score.rationale}"
                    )

        return failures

    def identify_strengths(
        self,
        dimension_scores: list[QualityDimensionScore],
    ) -> list[str]:
        """Identify strengths from dimension scores.

        Args:
            dimension_scores: List of dimension scores

        Returns:
            List of strength descriptions
        """
        strengths = []

        for dim_score in dimension_scores:
            if dim_score.score >= 0.8:
                strengths.append(f"Strong {dim_score.dimension}: {dim_score.rationale or 'High score'}")

        return strengths

    def identify_weaknesses(
        self,
        dimension_scores: list[QualityDimensionScore],
    ) -> list[str]:
        """Identify weaknesses from dimension scores.

        Args:
            dimension_scores: List of dimension scores

        Returns:
            List of weakness descriptions
        """
        weaknesses = []

        for dim_score in dimension_scores:
            if dim_score.score < 0.5:
                weaknesses.append(f"Weak {dim_score.dimension}: {dim_score.rationale or 'Low score'}")

        return weaknesses