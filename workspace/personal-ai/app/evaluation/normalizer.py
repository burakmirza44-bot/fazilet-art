"""Artifact Normalizer Module.

Provides normalization of different artifact types into a common
EvaluationInput structure for consistent evaluation.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.evaluation.models import (
    ArtifactKind,
    EvaluationInput,
    SourceType,
)


class ArtifactNormalizer:
    """Normalizes different artifact types into EvaluationInput.

    Provides a consistent interface for evaluating diverse output types.
    """

    def normalize(
        self,
        artifact: dict[str, Any] | Any,
        artifact_kind: str | ArtifactKind | None = None,
        domain: str = "",
        source_id: str = "",
    ) -> EvaluationInput:
        """Normalize an artifact into EvaluationInput.

        Args:
            artifact: The artifact to normalize (dict or object)
            artifact_kind: Optional explicit kind (auto-detected if not provided)
            domain: Optional domain hint
            source_id: Optional source process ID

        Returns:
            EvaluationInput ready for evaluation
        """
        # Handle dict vs object
        if isinstance(artifact, dict):
            return self._normalize_dict(artifact, artifact_kind, domain, source_id)
        else:
            return self._normalize_object(artifact, artifact_kind, domain, source_id)

    def _normalize_dict(
        self,
        artifact: dict[str, Any],
        artifact_kind: str | ArtifactKind | None,
        domain: str,
        source_id: str,
    ) -> EvaluationInput:
        """Normalize a dictionary artifact.

        Args:
            artifact: Dictionary artifact
            artifact_kind: Artifact kind
            domain: Domain hint
            source_id: Source ID

        Returns:
            EvaluationInput
        """
        # Auto-detect kind if not provided
        if artifact_kind is None:
            artifact_kind = self._detect_kind(artifact)

        kind_value = artifact_kind.value if isinstance(artifact_kind, ArtifactKind) else artifact_kind

        # Extract common fields
        artifact_id = artifact.get("id") or artifact.get("artifact_id") or artifact.get("recipe_id", "")
        detected_domain = artifact.get("domain", domain) or domain
        detected_source = artifact.get("source_id", source_id) or source_id
        source_type = artifact.get("source_type", SourceType.EXECUTION.value)

        return EvaluationInput.create(
            artifact_id=artifact_id,
            artifact_kind=kind_value,
            domain=detected_domain,
            source_type=source_type,
            source_id=detected_source,
            content=artifact.get("content", artifact),
            content_ref=artifact.get("content_ref", ""),
            verification_metadata=artifact.get("verification_metadata", {}),
            provenance_metadata=artifact.get("provenance_metadata", {}),
            runtime_metadata=artifact.get("runtime_metadata", {}),
            shipping_metadata=artifact.get("shipping_metadata", {}),
        )

    def _normalize_object(
        self,
        artifact: Any,
        artifact_kind: str | ArtifactKind | None,
        domain: str,
        source_id: str,
    ) -> EvaluationInput:
        """Normalize an object artifact.

        Args:
            artifact: Object artifact
            artifact_kind: Artifact kind
            domain: Domain hint
            source_id: Source ID

        Returns:
            EvaluationInput
        """
        # Try to extract common attributes
        artifact_id = getattr(artifact, "id", None) or getattr(artifact, "artifact_id", "")
        detected_domain = getattr(artifact, "domain", domain) or domain
        detected_source = getattr(artifact, "source_id", source_id) or source_id

        # Auto-detect kind if not provided
        if artifact_kind is None:
            artifact_kind = self._detect_kind_from_object(artifact)

        kind_value = artifact_kind.value if isinstance(artifact_kind, ArtifactKind) else artifact_kind

        # Try to get content via to_dict if available
        if hasattr(artifact, "to_dict"):
            content = artifact.to_dict()
        else:
            content = {}

        return EvaluationInput.create(
            artifact_id=str(artifact_id),
            artifact_kind=kind_value,
            domain=detected_domain,
            source_type=SourceType.EXECUTION.value,
            source_id=detected_source,
            content=content,
        )

    def _detect_kind(self, artifact: dict[str, Any]) -> ArtifactKind:
        """Detect artifact kind from dictionary content.

        Args:
            artifact: Dictionary artifact

        Returns:
            Detected ArtifactKind
        """
        # Check explicit kind field
        kind = artifact.get("kind") or artifact.get("artifact_kind") or artifact.get("type")
        if kind:
            try:
                return ArtifactKind(kind)
            except ValueError:
                pass

        # Heuristics for detection
        if "steps" in artifact and ("recipe" in str(artifact).lower() or "action" in artifact):
            return ArtifactKind.RECIPE_OUTPUT

        if "documentation" in str(artifact).lower() or "readme" in str(artifact).lower():
            return ArtifactKind.DOCUMENTATION_OUTPUT

        if "kb_" in str(artifact).lower() or "knowledge_base" in str(artifact).lower():
            return ArtifactKind.KB_CANDIDATE

        if "repair" in str(artifact).lower():
            return ArtifactKind.REPAIR_PATTERN

        if "runtime_result" in str(artifact).lower() or "execution_result" in str(artifact).lower():
            return ArtifactKind.RUNTIME_RESULT

        if "tutorial" in str(artifact).lower():
            return ArtifactKind.TUTORIAL_ARTIFACT

        return ArtifactKind.UNKNOWN

    def _detect_kind_from_object(self, obj: Any) -> ArtifactKind:
        """Detect artifact kind from object type.

        Args:
            obj: Object to detect kind from

        Returns:
            Detected ArtifactKind
        """
        class_name = type(obj).__name__.lower()

        if "recipe" in class_name:
            return ArtifactKind.RECIPE_OUTPUT
        if "doc" in class_name:
            return ArtifactKind.DOCUMENTATION_OUTPUT
        if "kb" in class_name or "knowledge" in class_name:
            return ArtifactKind.KB_CANDIDATE
        if "repair" in class_name:
            return ArtifactKind.REPAIR_PATTERN
        if "runtime" in class_name or "result" in class_name:
            return ArtifactKind.RUNTIME_RESULT
        if "tutorial" in class_name:
            return ArtifactKind.TUTORIAL_ARTIFACT

        return ArtifactKind.UNKNOWN


def normalize_recipe_output(
    recipe: dict[str, Any],
    domain: str = "",
    execution_id: str = "",
    verification: dict[str, Any] | None = None,
    provenance: dict[str, Any] | None = None,
) -> EvaluationInput:
    """Normalize a recipe output for evaluation.

    Args:
        recipe: Recipe dictionary
        domain: Domain
        execution_id: Execution/run ID
        verification: Verification metadata
        provenance: Provenance metadata

    Returns:
        EvaluationInput
    """
    return EvaluationInput.create(
        artifact_id=recipe.get("id") or recipe.get("recipe_id", ""),
        artifact_kind=ArtifactKind.RECIPE_OUTPUT,
        domain=domain or recipe.get("domain", ""),
        source_type=SourceType.EXECUTION,
        source_id=execution_id,
        content=recipe,
        verification_metadata=verification or {},
        provenance_metadata=provenance or {},
        runtime_metadata={
            "step_count": len(recipe.get("steps", [])),
            "has_preconditions": bool(recipe.get("preconditions")),
            "has_verification": bool(recipe.get("verification")),
        },
    )


def normalize_documentation_output(
    documentation: dict[str, Any],
    domain: str = "",
    source_id: str = "",
    provenance: dict[str, Any] | None = None,
) -> EvaluationInput:
    """Normalize a documentation output for evaluation.

    Args:
        documentation: Documentation dictionary
        domain: Domain
        source_id: Source ID
        provenance: Provenance metadata

    Returns:
        EvaluationInput
    """
    return EvaluationInput.create(
        artifact_id=documentation.get("id") or documentation.get("doc_id", ""),
        artifact_kind=ArtifactKind.DOCUMENTATION_OUTPUT,
        domain=domain,
        source_type=SourceType.GENERATION,
        source_id=source_id,
        content=documentation,
        provenance_metadata=provenance or {},
    )


def normalize_kb_candidate(
    candidate: dict[str, Any],
    domain: str = "",
    source_id: str = "",
    provenance: dict[str, Any] | None = None,
) -> EvaluationInput:
    """Normalize a KB update candidate for evaluation.

    Args:
        candidate: KB candidate dictionary
        domain: Domain
        source_id: Source ID
        provenance: Provenance metadata

    Returns:
        EvaluationInput
    """
    return EvaluationInput.create(
        artifact_id=candidate.get("id") or candidate.get("entry_id", ""),
        artifact_kind=ArtifactKind.KB_CANDIDATE,
        domain=domain or candidate.get("domain", ""),
        source_type=SourceType.LEARNING,
        source_id=source_id,
        content=candidate,
        provenance_metadata=provenance or candidate.get("provenance", {}),
    )


def normalize_runtime_result(
    result: dict[str, Any],
    domain: str = "",
    run_id: str = "",
) -> EvaluationInput:
    """Normalize a runtime result for evaluation.

    Args:
        result: Runtime result dictionary
        domain: Domain
        run_id: Run ID

    Returns:
        EvaluationInput
    """
    return EvaluationInput.create(
        artifact_id=result.get("run_id") or result.get("result_id", run_id),
        artifact_kind=ArtifactKind.RUNTIME_RESULT,
        domain=domain or result.get("domain", ""),
        source_type=SourceType.EXECUTION,
        source_id=run_id,
        content=result,
        runtime_metadata={
            "success": result.get("success", False),
            "step_count": result.get("step_count", 0),
            "error_count": result.get("error_count", 0),
        },
        verification_metadata=result.get("verification", {}),
    )


def normalize_repair_pattern(
    pattern: dict[str, Any],
    domain: str = "",
    source_id: str = "",
) -> EvaluationInput:
    """Normalize a repair pattern for evaluation.

    Args:
        pattern: Repair pattern dictionary
        domain: Domain
        source_id: Source ID

    Returns:
        EvaluationInput
    """
    return EvaluationInput.create(
        artifact_id=pattern.get("id") or pattern.get("pattern_id", ""),
        artifact_kind=ArtifactKind.REPAIR_PATTERN,
        domain=domain or pattern.get("domain", ""),
        source_type=SourceType.LEARNING,
        source_id=source_id,
        content=pattern,
        provenance_metadata=pattern.get("provenance", {}),
    )


def normalize_tutorial_artifact(
    artifact: dict[str, Any],
    domain: str = "",
    source_id: str = "",
) -> EvaluationInput:
    """Normalize a tutorial/distillation artifact for evaluation.

    Args:
        artifact: Tutorial artifact dictionary
        domain: Domain
        source_id: Source ID

    Returns:
        EvaluationInput
    """
    return EvaluationInput.create(
        artifact_id=artifact.get("id") or artifact.get("artifact_id", ""),
        artifact_kind=ArtifactKind.TUTORIAL_ARTIFACT,
        domain=domain,
        source_type=SourceType.DISTILLATION,
        source_id=source_id,
        content=artifact,
        provenance_metadata=artifact.get("provenance", {}),
    )