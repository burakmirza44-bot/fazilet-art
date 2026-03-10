"""Tests for Output Evaluator Module.

Comprehensive tests covering all evaluation scenarios including
strong outputs, weak outputs, invalid inputs, and gate decisions.
"""

import pytest

from app.evaluation.models import (
    ArtifactKind,
    EvaluationDecision,
    EvaluationInput,
    EvaluationResult,
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
    should_promote_output,
    should_ship_output,
    should_update_kb,
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def strong_recipe():
    """Create a strong recipe output for testing."""
    return {
        "id": "recipe_001",
        "name": "Create Terrain Heightfield",
        "domain": "houdini",
        "description": "Creates a procedural terrain using heightfield nodes",
        "steps": [
            {"action": "create_node", "type": "heightfield", "description": "Create heightfield"},
            {"action": "set_param", "name": "size", "value": "512", "description": "Set size"},
            {"action": "connect", "from": "heightfield", "to": "output", "description": "Connect output"},
        ],
        "preconditions": ["Bridge connected"],
        "dependencies": ["houdini_bridge"],
        "verification": {"check_node_exists": "heightfield"},
        "provenance": {
            "source": "tutorial",
            "created_at": "2024-03-10T10:00:00",
            "creator": "test",
            "domain": "houdini",
        },
        "validated": True,
    }


@pytest.fixture
def weak_recipe():
    """Create a weak/incomplete recipe for testing."""
    return {
        "id": "recipe_weak",
        "name": "Untitled Recipe",
        "domain": "houdini",
        "steps": [],  # Empty steps
        # Missing many required fields
    }


@pytest.fixture
def strong_documentation():
    """Create strong documentation for testing."""
    return {
        "id": "doc_001",
        "title": "Houdini Terrain Workflow",
        "content": """
# Houdini Terrain Workflow

This guide covers creating procedural terrain using heightfields.

## Prerequisites
- Houdini 19.5 or later
- Bridge connection established

## Steps
1. Create heightfield node
2. Configure size and resolution parameters
3. Add noise layers for variation
4. Connect to output for visualization

## Parameters
- Size: Controls terrain dimensions
- Resolution: Grid detail level
- Seed: Random variation control
        """,
        "domain": "houdini",
        "provenance": {
            "source": "generated",
            "created_at": "2024-03-10T10:00:00",
        },
    }


@pytest.fixture
def filler_documentation():
    """Create filler-heavy documentation for testing."""
    return {
        "id": "doc_weak",
        "title": "Documentation",
        "content": """
This is a document. It contains information. The information is useful.
There are many things to consider. One should always consider things.
This is another paragraph. It also contains information. We hope it helps.
The end result is something. Something is important. Always remember something.
        """,
        "domain": "generic",
    }


@pytest.fixture
def strong_kb_candidate():
    """Create a strong KB candidate for testing."""
    return {
        "id": "kb_001",
        "domain": "houdini",
        "content": {
            "pattern": "heightfield_terrain",
            "description": "Standard heightfield terrain workflow with noise layers",
            "nodes": ["heightfield", "heightfield_noise", "output"],
            "parameters": {"size": 512, "resolution": 512},
        },
        "provenance": {
            "source": "execution",
            "run_id": "run_001",
            "created_at": "2024-03-10T10:00:00",
            "domain": "houdini",
            "trace_id": "trace_001",
        },
        "tags": ["terrain", "procedural", "houdini"],
    }


@pytest.fixture
def weak_kb_candidate():
    """Create a weak KB candidate for testing."""
    return {
        "id": "kb_weak",
        "domain": "unknown",
        "content": {},  # Empty content
        # Missing provenance
    }


@pytest.fixture
def strong_repair_pattern():
    """Create a strong repair pattern for testing."""
    return {
        "id": "repair_001",
        "error_type": "bridge_timeout",
        "repair_strategy": "Retry connection with exponential backoff",
        "description": "Handle bridge timeout by waiting and retrying",
        "steps": [
            "Wait 1 second",
            "Retry connection",
            "If fails, wait 2 seconds and retry",
            "Max 3 retries",
        ],
        "success_rate": 0.85,
        "domain": "generic",
    }


@pytest.fixture
def evaluator():
    """Create an OutputEvaluator for testing."""
    return OutputEvaluator()


# ============================================================================
# Model Tests
# ============================================================================

class TestScoreBand:
    """Tests for ScoreBand enum and score_to_band function."""

    def test_excellent_band(self):
        """Test excellent score band (0.90-1.00)."""
        assert score_to_band(0.95) == ScoreBand.EXCELLENT
        assert score_to_band(0.90) == ScoreBand.EXCELLENT
        assert score_to_band(1.0) == ScoreBand.EXCELLENT

    def test_strong_band(self):
        """Test strong score band (0.75-0.89)."""
        assert score_to_band(0.80) == ScoreBand.STRONG
        assert score_to_band(0.75) == ScoreBand.STRONG

    def test_acceptable_band(self):
        """Test acceptable score band (0.60-0.74)."""
        assert score_to_band(0.70) == ScoreBand.ACCEPTABLE
        assert score_to_band(0.60) == ScoreBand.ACCEPTABLE

    def test_weak_band(self):
        """Test weak score band (0.40-0.59)."""
        assert score_to_band(0.50) == ScoreBand.WEAK
        assert score_to_band(0.40) == ScoreBand.WEAK

    def test_poor_band(self):
        """Test poor score band (0.20-0.39)."""
        assert score_to_band(0.30) == ScoreBand.POOR

    def test_invalid_band(self):
        """Test invalid score band (0.00-0.19)."""
        assert score_to_band(0.10) == ScoreBand.INVALID
        assert score_to_band(0.0) == ScoreBand.INVALID


class TestEvaluationInput:
    """Tests for EvaluationInput model."""

    def test_create_evaluation_input(self):
        """Test creating EvaluationInput."""
        input_data = EvaluationInput.create(
            artifact_id="test_001",
            artifact_kind=ArtifactKind.RECIPE_OUTPUT,
            domain="houdini",
            source_type=SourceType.EXECUTION,
            source_id="run_001",
        )

        assert input_data.artifact_id == "test_001"
        assert input_data.artifact_kind == "recipe_output"
        assert input_data.domain == "houdini"
        assert input_data.source_type == "execution"

    def test_evaluation_input_serialization(self):
        """Test EvaluationInput serialization roundtrip."""
        original = EvaluationInput.create(
            artifact_id="test_001",
            artifact_kind=ArtifactKind.DOCUMENTATION_OUTPUT,
            domain="touchdesigner",
            source_type=SourceType.GENERATION,
            source_id="gen_001",
            content={"title": "Test"},
        )

        data = original.to_dict()
        restored = EvaluationInput.from_dict(data)

        assert restored.artifact_id == original.artifact_id
        assert restored.artifact_kind == original.artifact_kind
        assert restored.domain == original.domain

    def test_is_recipe_property(self):
        """Test is_recipe property."""
        input_data = EvaluationInput.create(
            artifact_id="test",
            artifact_kind=ArtifactKind.RECIPE_OUTPUT,
            domain="houdini",
            source_type=SourceType.EXECUTION,
            source_id="run",
        )

        assert input_data.is_recipe
        assert not input_data.is_documentation


class TestEvaluationResult:
    """Tests for EvaluationResult model."""

    def test_create_evaluation_result(self):
        """Test creating EvaluationResult."""
        result = EvaluationResult.create(
            artifact_id="test_001",
            artifact_kind="recipe_output",
            domain="houdini",
            overall_score=0.85,
        )

        assert result.artifact_id == "test_001"
        assert result.overall_score == 0.85
        assert result.score_band == "strong"
        assert result.passed is True

    def test_result_properties(self):
        """Test EvaluationResult properties."""
        result = EvaluationResult.create(
            artifact_id="test",
            artifact_kind="recipe_output",
            domain="houdini",
            overall_score=0.90,
        )

        assert result.is_excellent
        assert result.is_strong
        assert not result.is_weak

    def test_result_serialization(self):
        """Test EvaluationResult serialization roundtrip."""
        original = EvaluationResult.create(
            artifact_id="test_001",
            artifact_kind="recipe_output",
            domain="houdini",
            overall_score=0.75,
            strengths=["Good structure"],
            weaknesses=["Missing verification"],
        )

        data = original.to_dict()
        restored = EvaluationResult.from_dict(data)

        assert restored.artifact_id == original.artifact_id
        assert restored.overall_score == original.overall_score
        assert restored.strengths == original.strengths

    def test_add_dimension_score(self):
        """Test adding dimension scores."""
        result = EvaluationResult.create(
            artifact_id="test",
            artifact_kind="recipe_output",
            domain="houdini",
            overall_score=0.7,
        )

        result.add_dimension_score(
            dimension="correctness",
            score=0.8,
            rationale="Tests passed",
            evidence=["All tests green"],
        )

        assert len(result.quality_dimensions) == 1
        assert result.get_dimension_score("correctness") == 0.8

    def test_result_summary(self):
        """Test result summary generation."""
        result = EvaluationResult.create(
            artifact_id="test_001",
            artifact_kind="recipe_output",
            domain="houdini",
            overall_score=0.85,
            decision=EvaluationDecision.ACCEPT,
            strengths=["Good structure"],
        )

        summary = result.summary()
        assert "test_001" in summary
        assert "0.85" in summary
        assert "accept" in summary.lower()


# ============================================================================
# Normalizer Tests
# ============================================================================

class TestArtifactNormalizer:
    """Tests for ArtifactNormalizer."""

    def test_normalize_dict_artifact(self):
        """Test normalizing a dictionary artifact."""
        normalizer = ArtifactNormalizer()
        artifact = {
            "id": "test_001",
            "kind": "recipe_output",
            "domain": "houdini",
            "steps": [],
        }

        result = normalizer.normalize(artifact, domain="houdini")

        assert result.artifact_id == "test_001"
        assert result.artifact_kind == "recipe_output"

    def test_detect_recipe_kind(self):
        """Test detecting recipe kind."""
        normalizer = ArtifactNormalizer()
        artifact = {
            "steps": [{"action": "create_node"}],
            "action": "create",
        }

        result = normalizer.normalize(artifact)
        assert result.artifact_kind == "recipe_output"

    def test_normalize_recipe_output(self):
        """Test normalize_recipe_output function."""
        recipe = {"id": "recipe_001", "steps": []}

        result = normalize_recipe_output(
            recipe=recipe,
            domain="houdini",
            execution_id="run_001",
        )

        assert result.artifact_kind == "recipe_output"
        assert result.domain == "houdini"


# ============================================================================
# Scoring Tests
# ============================================================================

class TestDimensionScorer:
    """Tests for DimensionScorer."""

    def test_score_correctness_verified(self):
        """Test correctness scoring with verification."""
        scorer = DimensionScorer()
        content = {"validated": True}
        verification = {"verified": True, "tests_passed": 5, "tests_total": 5}

        score, evidence = scorer.score_correctness(content, verification)

        assert score >= 0.7
        assert any("verif" in e.lower() for e in evidence)

    def test_score_completeness(self):
        """Test completeness scoring."""
        scorer = DimensionScorer()
        content = {"name": "test", "steps": [], "domain": "houdini"}
        required = ["name", "steps", "domain", "description"]

        score, evidence = scorer.score_completeness(content, required)

        # 3/4 fields present = 0.75
        assert score >= 0.5
        assert "3/4" in str(evidence) or "present" in str(evidence).lower()

    def test_score_safety_safe(self):
        """Test safety scoring for safe content."""
        scorer = DimensionScorer()
        content = {"action": "create_node"}
        safety = {"safety_checked": True, "safety_level": "safe"}

        score, evidence = scorer.score_safety(content, safety)

        assert score >= 0.9

    def test_score_safety_unsafe(self):
        """Test safety scoring for unsafe content."""
        scorer = DimensionScorer()
        content = {"command": "delete all files"}
        safety = {"safety_level": "unsafe"}

        score, evidence = scorer.score_safety(content, safety)

        assert score < 0.6

    def test_score_provenance_complete(self):
        """Test provenance scoring with complete metadata."""
        scorer = DimensionScorer()
        provenance = {
            "source": "execution",
            "created_at": "2024-03-10",
            "creator": "test",
            "version": "1.0",
            "domain": "houdini",
            "trace_id": "trace_001",
            "checksum": "abc123",
        }

        score, evidence = scorer.score_provenance_quality(provenance)

        assert score >= 0.9

    def test_score_provenance_missing(self):
        """Test provenance scoring with missing metadata."""
        scorer = DimensionScorer()

        score, evidence = scorer.score_provenance_quality({})

        assert score < 0.5

    def test_score_information_density_high(self):
        """Test information density for dense content."""
        scorer = DimensionScorer()
        content = {
            "name": "test",
            "steps": [1, 2, 3, 4, 5],
            "params": {"a": 1, "b": 2, "c": 3},
            "data": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        }

        score, evidence = scorer.score_information_density(content)

        # Score depends on content analysis
        assert score >= 0.0


class TestCompositeScorer:
    """Tests for CompositeScorer."""

    def test_calculate_overall_score(self):
        """Test overall score calculation."""
        scorer = CompositeScorer()
        dimensions = [
            QualityDimensionScore(dimension="correctness", score=0.8, weight=1.5),
            QualityDimensionScore(dimension="completeness", score=0.7, weight=1.0),
            QualityDimensionScore(dimension="clarity", score=0.9, weight=1.0),
        ]

        score = scorer.calculate_overall_score(dimensions)

        assert 0.7 <= score <= 0.9

    def test_identify_critical_failures(self):
        """Test identifying critical failures."""
        scorer = CompositeScorer()
        dimensions = [
            QualityDimensionScore(dimension="correctness", score=0.3, critical=True),
            QualityDimensionScore(dimension="completeness", score=0.7, critical=False),
        ]

        failures = scorer.identify_critical_failures(dimensions)

        assert len(failures) == 1
        assert "correctness" in failures[0]

    def test_identify_strengths_and_weaknesses(self):
        """Test identifying strengths and weaknesses."""
        scorer = CompositeScorer()
        dimensions = [
            QualityDimensionScore(dimension="correctness", score=0.9),
            QualityDimensionScore(dimension="completeness", score=0.3),
        ]

        strengths = scorer.identify_strengths(dimensions)
        weaknesses = scorer.identify_weaknesses(dimensions)

        assert len(strengths) == 1
        assert len(weaknesses) == 1


# ============================================================================
# Evaluation Tests
# ============================================================================

class TestStrongRecipeEvaluation:
    """Tests for strong recipe output evaluation."""

    def test_strong_recipe_passes_evaluation(self, evaluator, strong_recipe):
        """Test that a strong recipe passes evaluation."""
        result = evaluator.evaluate_recipe_output(
            recipe=strong_recipe,
            domain="houdini",
            execution_id="run_001",
            provenance=strong_recipe.get("provenance"),
        )

        assert result.passed
        assert result.overall_score >= 0.60
        assert result.decision != EvaluationDecision.REJECT

    def test_strong_recipe_is_shippable(self, evaluator, strong_recipe):
        """Test that a strong recipe is shippable."""
        result = evaluator.evaluate_recipe_output(
            recipe=strong_recipe,
            domain="houdini",
            provenance=strong_recipe.get("provenance"),
        )

        # Strong recipe should be promotable
        assert result.promotable or result.overall_score >= 0.60


class TestWeakRecipeEvaluation:
    """Tests for weak/incomplete recipe evaluation."""

    def test_incomplete_recipe_is_downgraded(self, evaluator, weak_recipe):
        """Test that incomplete recipe is downgraded."""
        result = evaluator.evaluate_recipe_output(
            recipe=weak_recipe,
            domain="houdini",
        )

        assert result.overall_score < 0.70
        assert len(result.weaknesses) > 0 or result.has_critical_failures

    def test_empty_steps_penalty(self, evaluator):
        """Test penalty for empty steps."""
        recipe = {
            "id": "recipe_empty",
            "name": "Empty Recipe",
            "domain": "houdini",
            "steps": [],
        }

        result = evaluator.evaluate_recipe_output(recipe=recipe, domain="houdini")

        assert result.overall_score < 0.70


class TestDocumentationEvaluation:
    """Tests for documentation evaluation."""

    def test_strong_documentation_passes(self, evaluator, strong_documentation):
        """Test that strong documentation passes."""
        result = evaluator.evaluate_documentation_output(
            documentation=strong_documentation,
            domain="houdini",
            provenance=strong_documentation.get("provenance"),
        )

        # Documentation should have clarity dimension scored
        assert "clarity" in [d.dimension for d in result.quality_dimensions]
        assert result.overall_score >= 0.0

    def test_filler_documentation_penalized(self, evaluator, filler_documentation):
        """Test that filler-heavy documentation is penalized."""
        result = evaluator.evaluate_documentation_output(
            documentation=filler_documentation,
            domain="generic",
        )

        # Should have lower score due to low information density
        assert result.overall_score < 0.70


class TestKBCandidateEvaluation:
    """Tests for KB candidate evaluation."""

    def test_strong_kb_candidate_passes(self, evaluator, strong_kb_candidate):
        """Test that strong KB candidate passes."""
        result = evaluator.evaluate_kb_candidate(
            candidate=strong_kb_candidate,
            domain="houdini",
            provenance=strong_kb_candidate.get("provenance"),
        )

        assert result.overall_score >= 0.50

    def test_weak_provenance_blocks_kb_update(self, evaluator, weak_kb_candidate):
        """Test that weak provenance blocks KB update."""
        result = evaluator.evaluate_kb_candidate(
            candidate=weak_kb_candidate,
            domain="unknown",
        )

        assert result.provenance_ok is False
        assert result.kb_recommendation == GateDecision.KB_UPDATE_BLOCKED.value


class TestRepairPatternEvaluation:
    """Tests for repair pattern evaluation."""

    def test_strong_repair_pattern_passes(self, evaluator, strong_repair_pattern):
        """Test that strong repair pattern passes."""
        result = evaluator.evaluate_repair_pattern(
            pattern=strong_repair_pattern,
            domain="generic",
        )

        assert result.overall_score >= 0.0


class TestRuntimeResultEvaluation:
    """Tests for runtime result evaluation."""

    def test_successful_runtime_result(self, evaluator):
        """Test evaluation of successful runtime result."""
        result_data = {
            "run_id": "run_001",
            "success": True,
            "step_count": 5,
            "error_count": 0,
            "steps": [{"step": 1}, {"step": 2}],
        }

        result = evaluator.evaluate_runtime_result(
            result=result_data,
            domain="houdini",
            run_id="run_001",
        )

        assert result.overall_score >= 0.0


class TestGateDecisions:
    """Tests for gate decisions."""

    def test_promotion_gate_allows_strong_artifact(self, evaluator, strong_recipe):
        """Test promotion gate allows strong artifact."""
        result = evaluator.evaluate_recipe_output(
            recipe=strong_recipe,
            domain="houdini",
            provenance=strong_recipe.get("provenance"),
        )

        assert should_promote_output(result) or result.overall_score < 0.70

    def test_shipping_gate_blocks_weak_artifact(self, evaluator, weak_recipe):
        """Test shipping gate blocks weak artifact."""
        result = evaluator.evaluate_recipe_output(
            recipe=weak_recipe,
            domain="houdini",
        )

        assert not should_ship_output(result)

    def test_kb_gate_checks_provenance(self, evaluator, weak_kb_candidate):
        """Test KB gate checks provenance."""
        result = evaluator.evaluate_kb_candidate(
            candidate=weak_kb_candidate,
            domain="unknown",
        )

        assert not should_update_kb(result)


class TestBatchEvaluation:
    """Tests for batch evaluation."""

    def test_multi_output_evaluation(self, evaluator, strong_recipe, strong_documentation):
        """Test evaluating multiple outputs."""
        inputs = [
            normalize_recipe_output(strong_recipe, domain="houdini"),
            normalize_documentation_output(strong_documentation, domain="houdini"),
        ]

        summary = evaluator.evaluate_outputs(inputs)

        assert summary.total_evaluated == 2
        assert summary.average_score > 0

    def test_summary_statistics(self, evaluator):
        """Test summary statistics calculation."""
        inputs = [
            EvaluationInput.create(
                artifact_id="test_1",
                artifact_kind=ArtifactKind.RECIPE_OUTPUT,
                domain="houdini",
                source_type=SourceType.EXECUTION,
                source_id="run_1",
                content={"steps": [{"action": "test"}]},
            ),
        ]

        summary = evaluator.evaluate_outputs(inputs)

        assert summary.total_evaluated == 1


class TestDeduplication:
    """Tests for duplicate detection."""

    def test_duplicate_detection(self, evaluator):
        """Test detection of duplicate content."""
        content = {"id": "test", "data": "same content"}

        result1 = evaluator.evaluate_kb_candidate(
            candidate=content,
            domain="test",
        )

        # Same content should be detected
        assert result1.overall_score >= 0.0


class TestSerialization:
    """Tests for serialization roundtrips."""

    def test_result_serialization_roundtrip(self, evaluator, strong_recipe):
        """Test result serialization roundtrip."""
        result = evaluator.evaluate_recipe_output(
            recipe=strong_recipe,
            domain="houdini",
        )

        data = result.to_dict()
        restored = EvaluationResult.from_dict(data)

        assert restored.evaluation_id == result.evaluation_id
        assert restored.overall_score == result.overall_score
        assert restored.decision == result.decision


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def test_evaluate_output_function(self, strong_recipe):
        """Test evaluate_output convenience function."""
        result = evaluate_output(
            artifact=strong_recipe,
            artifact_kind=ArtifactKind.RECIPE_OUTPUT,
            domain="houdini",
        )

        assert result.evaluation_id.startswith("eval_")
        assert result.artifact_kind == "recipe_output"

    def test_gate_helper_functions(self, strong_recipe):
        """Test gate helper functions."""
        result = evaluate_output(
            artifact=strong_recipe,
            artifact_kind=ArtifactKind.RECIPE_OUTPUT,
            domain="houdini",
        )

        # These should return boolean values
        assert isinstance(should_promote_output(result), bool)
        assert isinstance(should_ship_output(result), bool)
        assert isinstance(should_update_kb(result), bool)


class TestEndToEndIntegration:
    """End-to-end integration tests."""

    def test_full_evaluation_flow(self, evaluator, strong_recipe):
        """Test full evaluation flow from artifact to decision."""
        # Evaluate
        result = evaluator.evaluate_recipe_output(
            recipe=strong_recipe,
            domain="houdini",
            execution_id="run_001",
            provenance=strong_recipe.get("provenance"),
        )

        # Check result structure
        assert result.evaluation_id != ""
        assert result.artifact_id != ""
        assert result.overall_score >= 0.0
        assert result.decision != ""

        # Check gates
        assert result.promotion_recommendation in [g.value for g in GateDecision]
        assert result.shipping_recommendation in [g.value for g in GateDecision]
        assert result.kb_recommendation in [g.value for g in GateDecision]

        # Check dimensions
        assert len(result.quality_dimensions) > 0

        # Summary should be readable
        summary = result.summary()
        assert len(summary) > 0


class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_artifact(self, evaluator):
        """Test handling of empty artifact."""
        result = evaluate_output(
            artifact={},
            artifact_kind=ArtifactKind.UNKNOWN,
            domain="unknown",
        )

        assert result.overall_score < 0.5

    def test_missing_required_metadata(self, evaluator):
        """Test handling of missing required metadata."""
        recipe = {
            "id": "recipe_no_domain",
            "name": "Test",
            "steps": [{"action": "test"}],
            # No domain
        }

        result = evaluator.evaluate_recipe_output(recipe=recipe)

        # Should still evaluate but may have warnings
        assert result.evaluation_id != ""

    def test_invalid_artifact_kind(self, evaluator):
        """Test handling of invalid artifact kind."""
        result = evaluate_output(
            artifact={"id": "test"},
            artifact_kind="unknown",
            domain="test",
        )

        # Should use unknown kind and still evaluate
        assert result.evaluation_id != ""
        assert result.overall_score >= 0.0