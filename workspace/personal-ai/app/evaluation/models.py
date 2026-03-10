"""Evaluation Models Module.

Provides structured models for output evaluation including
artifacts, quality dimensions, scores, and decisions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
import uuid


class ArtifactKind(str, Enum):
    """Type of artifact being evaluated."""

    RECIPE_OUTPUT = "recipe_output"
    DOCUMENTATION_OUTPUT = "documentation_output"
    KB_CANDIDATE = "kb_candidate"
    RUNTIME_RESULT = "runtime_result"
    REPAIR_PATTERN = "repair_pattern"
    TUTORIAL_ARTIFACT = "tutorial_artifact"
    SHIPPING_ARTIFACT = "shipping_artifact"
    VERIFICATION_RESULT = "verification_result"
    UNKNOWN = "unknown"


class QualityDimension(str, Enum):
    """Quality dimensions for evaluation."""

    # Core dimensions
    CORRECTNESS = "correctness"
    COMPLETENESS = "completeness"
    USABILITY = "usability"
    CLARITY = "clarity"
    STRUCTURAL_VALIDITY = "structural_validity"
    SAFETY = "safety"
    PROVENANCE_QUALITY = "provenance_quality"
    REUSABILITY = "reusability"
    CONSISTENCY = "consistency"
    ACTIONABILITY = "actionability"

    # Domain-specific dimensions
    EXECUTOR_COMPATIBILITY = "executor_compatibility"
    SCHEMA_CONFORMANCE = "schema_conformance"
    VERIFICATION_ALIGNMENT = "verification_alignment"
    DOMAIN_COVERAGE = "domain_coverage"
    DEPENDENCY_INTEGRITY = "dependency_integrity"
    DOCUMENTATION_READABILITY = "documentation_readability"
    KB_DEDUPE_QUALITY = "kb_dedupe_quality"
    NOVELTY = "novelty"
    INFORMATION_DENSITY = "information_density"


class ScoreBand(str, Enum):
    """Score bands for categorizing evaluation results."""

    EXCELLENT = "excellent"  # 0.90 - 1.00
    STRONG = "strong"  # 0.75 - 0.89
    ACCEPTABLE = "acceptable"  # 0.60 - 0.74
    WEAK = "weak"  # 0.40 - 0.59
    POOR = "poor"  # 0.20 - 0.39
    INVALID = "invalid"  # 0.00 - 0.19


class EvaluationDecision(str, Enum):
    """Decision classes for evaluated artifacts."""

    ACCEPT = "accept"
    ACCEPT_WITH_WARNINGS = "accept_with_warnings"
    REVISE = "revise"
    BLOCK = "block"
    REJECT = "reject"
    PROMOTE = "promote"
    SHIP_READY = "ship_ready"
    KB_READY = "kb_ready"
    REUSABLE_PATTERN = "reusable_pattern"
    ARCHIVE_ONLY = "archive_only"


class GateDecision(str, Enum):
    """Gate-specific decisions."""

    PROMOTION_ALLOWED = "promotion_allowed"
    PROMOTION_BLOCKED = "promotion_blocked"
    SHIPPING_ALLOWED = "shipping_allowed"
    SHIPPING_BLOCKED = "shipping_blocked"
    KB_UPDATE_ALLOWED = "kb_update_allowed"
    KB_UPDATE_BLOCKED = "kb_update_blocked"
    REUSE_ALLOWED = "reuse_allowed"
    REUSE_BLOCKED = "reuse_blocked"


class SourceType(str, Enum):
    """Source type of the artifact."""

    EXECUTION = "execution"
    GENERATION = "generation"
    DISTILLATION = "distillation"
    EXTRACTION = "extraction"
    LEARNING = "learning"
    IMPORT = "import"
    UNKNOWN = "unknown"


# Score band thresholds
SCORE_BAND_THRESHOLDS: dict[ScoreBand, tuple[float, float]] = {
    ScoreBand.EXCELLENT: (0.90, 1.01),
    ScoreBand.STRONG: (0.75, 0.90),
    ScoreBand.ACCEPTABLE: (0.60, 0.75),
    ScoreBand.WEAK: (0.40, 0.60),
    ScoreBand.POOR: (0.20, 0.40),
    ScoreBand.INVALID: (0.00, 0.20),
}


def _generate_id(prefix: str = "eval") -> str:
    """Generate a unique ID with prefix."""
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def score_to_band(score: float) -> ScoreBand:
    """Convert a numeric score to a score band.

    Args:
        score: Numeric score (0.0 to 1.0)

    Returns:
        Corresponding ScoreBand
    """
    score = max(0.0, min(1.0, score))

    for band, (low, high) in SCORE_BAND_THRESHOLDS.items():
        if low <= score < high:
            return band

    return ScoreBand.POOR


@dataclass(slots=True)
class QualityDimensionScore:
    """Score for a single quality dimension."""

    dimension: str
    score: float
    weight: float = 1.0
    rationale: str = ""
    evidence: list[str] = field(default_factory=list)
    critical: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "dimension": self.dimension,
            "score": self.score,
            "weight": self.weight,
            "rationale": self.rationale,
            "evidence": self.evidence,
            "critical": self.critical,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "QualityDimensionScore":
        """Create from dictionary."""
        return cls(
            dimension=data["dimension"],
            score=data["score"],
            weight=data.get("weight", 1.0),
            rationale=data.get("rationale", ""),
            evidence=data.get("evidence", []),
            critical=data.get("critical", False),
        )


@dataclass(slots=True)
class EvaluationInput:
    """Normalized input for evaluation.

    Provides a common structure for evaluating different artifact types.
    """

    artifact_id: str
    artifact_kind: str  # ArtifactKind value
    domain: str
    source_type: str  # SourceType value
    source_id: str
    content: dict[str, Any] = field(default_factory=dict)
    content_ref: str = ""
    verification_metadata: dict[str, Any] = field(default_factory=dict)
    provenance_metadata: dict[str, Any] = field(default_factory=dict)
    runtime_metadata: dict[str, Any] = field(default_factory=dict)
    shipping_metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: str = "1.0.0"
    created_at: str = ""

    def __post_init__(self) -> None:
        """Set defaults after initialization."""
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    @classmethod
    def create(
        cls,
        artifact_id: str,
        artifact_kind: str | ArtifactKind,
        domain: str,
        source_type: str | SourceType,
        source_id: str,
        **kwargs: Any,
    ) -> "EvaluationInput":
        """Factory method to create EvaluationInput.

        Args:
            artifact_id: Unique artifact identifier
            artifact_kind: Type of artifact
            domain: Domain (houdini, touchdesigner, etc.)
            source_type: How the artifact was created
            source_id: ID of the source process/run
            **kwargs: Additional fields

        Returns:
            EvaluationInput instance
        """
        kind_value = artifact_kind.value if isinstance(artifact_kind, ArtifactKind) else artifact_kind
        source_value = source_type.value if isinstance(source_type, SourceType) else source_type

        return cls(
            artifact_id=artifact_id,
            artifact_kind=kind_value,
            domain=domain,
            source_type=source_value,
            source_id=source_id,
            created_at=datetime.now().isoformat(),
            **kwargs,
        )

    @property
    def is_recipe(self) -> bool:
        """Check if this is a recipe artifact."""
        return self.artifact_kind == ArtifactKind.RECIPE_OUTPUT.value

    @property
    def is_documentation(self) -> bool:
        """Check if this is a documentation artifact."""
        return self.artifact_kind == ArtifactKind.DOCUMENTATION_OUTPUT.value

    @property
    def is_kb_candidate(self) -> bool:
        """Check if this is a KB candidate."""
        return self.artifact_kind == ArtifactKind.KB_CANDIDATE.value

    @property
    def is_runtime_result(self) -> bool:
        """Check if this is a runtime result."""
        return self.artifact_kind == ArtifactKind.RUNTIME_RESULT.value

    @property
    def is_repair_pattern(self) -> bool:
        """Check if this is a repair pattern."""
        return self.artifact_kind == ArtifactKind.REPAIR_PATTERN.value

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "artifact_id": self.artifact_id,
            "artifact_kind": self.artifact_kind,
            "domain": self.domain,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "content": self.content,
            "content_ref": self.content_ref,
            "verification_metadata": self.verification_metadata,
            "provenance_metadata": self.provenance_metadata,
            "runtime_metadata": self.runtime_metadata,
            "shipping_metadata": self.shipping_metadata,
            "schema_version": self.schema_version,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvaluationInput":
        """Create from dictionary."""
        return cls(
            artifact_id=data["artifact_id"],
            artifact_kind=data["artifact_kind"],
            domain=data["domain"],
            source_type=data["source_type"],
            source_id=data["source_id"],
            content=data.get("content", {}),
            content_ref=data.get("content_ref", ""),
            verification_metadata=data.get("verification_metadata", {}),
            provenance_metadata=data.get("provenance_metadata", {}),
            runtime_metadata=data.get("runtime_metadata", {}),
            shipping_metadata=data.get("shipping_metadata", {}),
            schema_version=data.get("schema_version", "1.0.0"),
            created_at=data.get("created_at", ""),
        )


@dataclass(slots=True)
class EvaluationResult:
    """Structured result of artifact evaluation.

    Contains scores, decisions, rationale, and recommendations.
    """

    evaluation_id: str
    evaluated_at: str
    artifact_id: str
    artifact_kind: str
    domain: str
    passed: bool
    overall_score: float
    score_band: str  # ScoreBand value
    decision: str  # EvaluationDecision value
    quality_dimensions: list[QualityDimensionScore] = field(default_factory=list)
    critical_failures: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    rationale: str = ""
    promotion_recommendation: str = ""  # GateDecision value
    shipping_recommendation: str = ""  # GateDecision value
    kb_recommendation: str = ""  # GateDecision value
    reusable: bool = False
    requires_revision: bool = False
    provenance_ok: bool = True
    schema_version: str = "1.0.0"
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Set defaults after initialization."""
        if not self.evaluation_id:
            object.__setattr__(self, "evaluation_id", _generate_id("eval"))
        if not self.evaluated_at:
            object.__setattr__(self, "evaluated_at", datetime.now().isoformat())

    @classmethod
    def create(
        cls,
        artifact_id: str,
        artifact_kind: str,
        domain: str,
        overall_score: float,
        **kwargs: Any,
    ) -> "EvaluationResult":
        """Factory method to create EvaluationResult.

        Args:
            artifact_id: ID of evaluated artifact
            artifact_kind: Kind of artifact
            domain: Domain
            overall_score: Overall quality score
            **kwargs: Additional fields

        Returns:
            EvaluationResult instance
        """
        score_band = score_to_band(overall_score)
        passed = overall_score >= 0.60

        return cls(
            evaluation_id=_generate_id("eval"),
            evaluated_at=datetime.now().isoformat(),
            artifact_id=artifact_id,
            artifact_kind=artifact_kind,
            domain=domain,
            passed=passed,
            overall_score=overall_score,
            score_band=score_band.value,
            decision=kwargs.get("decision", EvaluationDecision.ACCEPT.value),
            quality_dimensions=kwargs.get("quality_dimensions", []),
            critical_failures=kwargs.get("critical_failures", []),
            warnings=kwargs.get("warnings", []),
            strengths=kwargs.get("strengths", []),
            weaknesses=kwargs.get("weaknesses", []),
            rationale=kwargs.get("rationale", ""),
            promotion_recommendation=kwargs.get("promotion_recommendation", ""),
            shipping_recommendation=kwargs.get("shipping_recommendation", ""),
            kb_recommendation=kwargs.get("kb_recommendation", ""),
            reusable=kwargs.get("reusable", False),
            requires_revision=kwargs.get("requires_revision", False),
            provenance_ok=kwargs.get("provenance_ok", True),
            metadata=kwargs.get("metadata", {}),
        )

    @property
    def is_excellent(self) -> bool:
        """Check if result is excellent."""
        return self.score_band == ScoreBand.EXCELLENT.value

    @property
    def is_strong(self) -> bool:
        """Check if result is strong or better."""
        return self.score_band in (ScoreBand.EXCELLENT.value, ScoreBand.STRONG.value)

    @property
    def is_weak(self) -> bool:
        """Check if result is weak or worse."""
        return self.score_band in (ScoreBand.WEAK.value, ScoreBand.POOR.value, ScoreBand.INVALID.value)

    @property
    def has_critical_failures(self) -> bool:
        """Check if there are critical failures."""
        return len(self.critical_failures) > 0

    @property
    def promotable(self) -> bool:
        """Check if artifact can be promoted."""
        return self.passed and not self.has_critical_failures and self.provenance_ok

    @property
    def shippable(self) -> bool:
        """Check if artifact can be shipped."""
        return self.is_strong and not self.has_critical_failures and self.provenance_ok

    @property
    def kb_updatable(self) -> bool:
        """Check if artifact can update KB."""
        return self.passed and self.reusable and self.provenance_ok

    def get_dimension_score(self, dimension: str) -> float | None:
        """Get score for a specific dimension.

        Args:
            dimension: Dimension name

        Returns:
            Score or None if not found
        """
        for dim_score in self.quality_dimensions:
            if dim_score.dimension == dimension:
                return dim_score.score
        return None

    def add_dimension_score(
        self,
        dimension: str,
        score: float,
        rationale: str = "",
        evidence: list[str] | None = None,
        critical: bool = False,
    ) -> None:
        """Add a dimension score.

        Args:
            dimension: Dimension name
            score: Score value
            rationale: Rationale for score
            evidence: Supporting evidence
            critical: Whether this is a critical dimension
        """
        dim_score = QualityDimensionScore(
            dimension=dimension,
            score=score,
            rationale=rationale,
            evidence=evidence or [],
            critical=critical,
        )
        self.quality_dimensions.append(dim_score)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "evaluation_id": self.evaluation_id,
            "evaluated_at": self.evaluated_at,
            "artifact_id": self.artifact_id,
            "artifact_kind": self.artifact_kind,
            "domain": self.domain,
            "passed": self.passed,
            "overall_score": self.overall_score,
            "score_band": self.score_band,
            "decision": self.decision,
            "quality_dimensions": [d.to_dict() for d in self.quality_dimensions],
            "critical_failures": self.critical_failures,
            "warnings": self.warnings,
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "rationale": self.rationale,
            "promotion_recommendation": self.promotion_recommendation,
            "shipping_recommendation": self.shipping_recommendation,
            "kb_recommendation": self.kb_recommendation,
            "reusable": self.reusable,
            "requires_revision": self.requires_revision,
            "provenance_ok": self.provenance_ok,
            "schema_version": self.schema_version,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvaluationResult":
        """Create from dictionary."""
        quality_dimensions = [
            QualityDimensionScore.from_dict(d)
            for d in data.get("quality_dimensions", [])
        ]

        return cls(
            evaluation_id=data["evaluation_id"],
            evaluated_at=data["evaluated_at"],
            artifact_id=data["artifact_id"],
            artifact_kind=data["artifact_kind"],
            domain=data["domain"],
            passed=data["passed"],
            overall_score=data["overall_score"],
            score_band=data["score_band"],
            decision=data["decision"],
            quality_dimensions=quality_dimensions,
            critical_failures=data.get("critical_failures", []),
            warnings=data.get("warnings", []),
            strengths=data.get("strengths", []),
            weaknesses=data.get("weaknesses", []),
            rationale=data.get("rationale", ""),
            promotion_recommendation=data.get("promotion_recommendation", ""),
            shipping_recommendation=data.get("shipping_recommendation", ""),
            kb_recommendation=data.get("kb_recommendation", ""),
            reusable=data.get("reusable", False),
            requires_revision=data.get("requires_revision", False),
            provenance_ok=data.get("provenance_ok", True),
            schema_version=data.get("schema_version", "1.0.0"),
            metadata=data.get("metadata", {}),
        )

    def summary(self) -> str:
        """Generate a human-readable summary.

        Returns:
            Summary string
        """
        lines = [
            f"Evaluation: {self.evaluation_id}",
            f"Artifact: {self.artifact_id} ({self.artifact_kind})",
            f"Score: {self.overall_score:.2f} ({self.score_band})",
            f"Decision: {self.decision}",
            f"Passed: {self.passed}",
        ]

        if self.strengths:
            lines.append(f"Strengths: {', '.join(self.strengths[:3])}")

        if self.weaknesses:
            lines.append(f"Weaknesses: {', '.join(self.weaknesses[:3])}")

        if self.critical_failures:
            lines.append(f"Critical: {', '.join(self.critical_failures)}")

        return "\n".join(lines)


@dataclass
class EvaluationSummary:
    """Summary report for evaluation results.

    Provides aggregated metrics for multiple evaluations.
    """

    total_evaluated: int = 0
    passed_count: int = 0
    failed_count: int = 0
    excellent_count: int = 0
    strong_count: int = 0
    acceptable_count: int = 0
    weak_count: int = 0
    poor_count: int = 0
    invalid_count: int = 0
    promoted_count: int = 0
    shipped_count: int = 0
    kb_updated_count: int = 0
    blocked_count: int = 0
    average_score: float = 0.0
    results: list[EvaluationResult] = field(default_factory=list)

    @property
    def pass_rate(self) -> float:
        """Calculate pass rate."""
        if self.total_evaluated == 0:
            return 0.0
        return self.passed_count / self.total_evaluated

    @property
    def promotion_rate(self) -> float:
        """Calculate promotion rate."""
        if self.total_evaluated == 0:
            return 0.0
        return self.promoted_count / self.total_evaluated

    def add_result(self, result: EvaluationResult) -> None:
        """Add a result to the summary.

        Args:
            result: EvaluationResult to add
        """
        self.results.append(result)
        self.total_evaluated += 1

        if result.passed:
            self.passed_count += 1
        else:
            self.failed_count += 1

        # Count by band
        if result.score_band == ScoreBand.EXCELLENT.value:
            self.excellent_count += 1
        elif result.score_band == ScoreBand.STRONG.value:
            self.strong_count += 1
        elif result.score_band == ScoreBand.ACCEPTABLE.value:
            self.acceptable_count += 1
        elif result.score_band == ScoreBand.WEAK.value:
            self.weak_count += 1
        elif result.score_band == ScoreBand.POOR.value:
            self.poor_count += 1
        else:
            self.invalid_count += 1

        # Count gate decisions
        if result.promotable:
            self.promoted_count += 1
        if result.shippable:
            self.shipped_count += 1
        if result.kb_updatable:
            self.kb_updated_count += 1
        if result.has_critical_failures:
            self.blocked_count += 1

        # Recalculate average
        total_score = sum(r.overall_score for r in self.results)
        self.average_score = total_score / len(self.results)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_evaluated": self.total_evaluated,
            "passed_count": self.passed_count,
            "failed_count": self.failed_count,
            "excellent_count": self.excellent_count,
            "strong_count": self.strong_count,
            "acceptable_count": self.acceptable_count,
            "weak_count": self.weak_count,
            "poor_count": self.poor_count,
            "invalid_count": self.invalid_count,
            "promoted_count": self.promoted_count,
            "shipped_count": self.shipped_count,
            "kb_updated_count": self.kb_updated_count,
            "blocked_count": self.blocked_count,
            "average_score": self.average_score,
            "pass_rate": self.pass_rate,
            "promotion_rate": self.promotion_rate,
            "results": [r.to_dict() for r in self.results],
        }