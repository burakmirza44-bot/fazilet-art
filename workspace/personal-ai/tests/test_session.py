"""Tests for Session Module.

Tests session metadata tracking, display formatting, and integration.
"""

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from app.session import (
    BridgeHealthMetrics,
    ErrorRecoveryMetrics,
    ExecutionPhase,
    ExecutionStepMetrics,
    KnowledgeHit,
    KnowledgeQualityMetrics,
    PlanningMetrics,
    RagRetrievalMetrics,
    SessionMetadata,
    SessionTracker,
    SessionDisplayFormatter,
    format_session_summary,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_session_metadata():
    """Create sample session metadata."""
    return SessionMetadata.create(
        session_id="test_session_001",
        goal="Create Houdini procedural geometry",
        domain="houdini",
    )


@pytest.fixture
def tracker():
    """Create a session tracker."""
    return SessionTracker(
        session_id="test_session_001",
        goal="Test goal",
        domain="houdini",
        verbose=False,
    )


@pytest.fixture
def temp_session_path():
    """Create a temporary file path for session data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield os.path.join(tmpdir, "session.json")


# ============================================================================
# ExecutionPhase Tests
# ============================================================================

class TestExecutionPhase:
    """Tests for ExecutionPhase enum."""

    def test_phase_values(self):
        """Test phase enum values."""
        assert ExecutionPhase.INITIALIZATION.value == "initialization"
        assert ExecutionPhase.PLANNING.value == "planning"
        assert ExecutionPhase.EXECUTION.value == "execution"
        assert ExecutionPhase.VERIFICATION.value == "verification"
        assert ExecutionPhase.RECOVERY.value == "recovery"
        assert ExecutionPhase.COMPLETION.value == "completion"


# ============================================================================
# KnowledgeHit Tests
# ============================================================================

class TestKnowledgeHit:
    """Tests for KnowledgeHit dataclass."""

    def test_create_hit(self):
        """Test creating a knowledge hit."""
        hit = KnowledgeHit(
            recipe_id="recipe_001",
            recipe_title="Noise Terrain",
            confidence=0.85,
            source="distilled",
            retrieval_phase="planning",
        )

        assert hit.recipe_id == "recipe_001"
        assert hit.confidence == 0.85
        assert hit.used is False

    def test_hit_serialization(self):
        """Test hit serialization roundtrip."""
        hit = KnowledgeHit(
            recipe_id="recipe_001",
            recipe_title="Test Recipe",
            confidence=0.75,
            source="rag",
            retrieval_phase="execution",
            used=True,
        )

        data = hit.to_dict()
        restored = KnowledgeHit.from_dict(data)

        assert restored.recipe_id == hit.recipe_id
        assert restored.confidence == hit.confidence
        assert restored.used == hit.used


# ============================================================================
# RagRetrievalMetrics Tests
# ============================================================================

class TestRagRetrievalMetrics:
    """Tests for RAG retrieval metrics."""

    def test_create_metrics(self):
        """Test creating RAG metrics."""
        metrics = RagRetrievalMetrics(
            total_queries=5,
            total_chunks_retrieved=23,
            avg_confidence=0.85,
        )

        assert metrics.total_queries == 5
        assert metrics.total_chunks_retrieved == 23

    def test_metrics_serialization(self):
        """Test metrics serialization."""
        metrics = RagRetrievalMetrics(
            total_queries=3,
            total_chunks_retrieved=15,
            avg_confidence=0.80,
            by_domain={"houdini": 2, "general": 1},
        )

        data = metrics.to_dict()
        restored = RagRetrievalMetrics.from_dict(data)

        assert restored.total_queries == 3
        assert restored.by_domain == {"houdini": 2, "general": 1}


# ============================================================================
# PlanningMetrics Tests
# ============================================================================

class TestPlanningMetrics:
    """Tests for planning metrics."""

    def test_create_metrics(self):
        """Test creating planning metrics."""
        metrics = PlanningMetrics(
            goal="Test goal",
            initial_complexity_score=7.5,
            subgoals_generated=4,
            final_plan_quality_score=0.85,
        )

        assert metrics.initial_complexity_score == 7.5
        assert metrics.subgoals_generated == 4

    def test_metrics_with_replanning(self):
        """Test metrics with replanning."""
        metrics = PlanningMetrics(
            goal="Test goal",
            replanning_triggered=True,
            replan_count=2,
            replanning_reasons=["goal_changed", "error_detected"],
        )

        assert metrics.replan_count == 2
        assert len(metrics.replanning_reasons) == 2


# ============================================================================
# ExecutionStepMetrics Tests
# ============================================================================

class TestExecutionStepMetrics:
    """Tests for execution step metrics."""

    def test_create_step(self):
        """Test creating an execution step."""
        step = ExecutionStepMetrics(
            order=1,
            action="Create geometry",
            bridge_type="houdini",
            duration_ms=156.0,
            success=True,
        )

        assert step.order == 1
        assert step.action == "Create geometry"
        assert step.success is True

    def test_step_with_error(self):
        """Test step with error."""
        step = ExecutionStepMetrics(
            order=2,
            action="Add noise",
            bridge_type="houdini",
            duration_ms=2340.0,
            success=False,
            error_message="Parameter invalid",
            retries_attempted=2,
        )

        assert step.success is False
        assert step.error_message == "Parameter invalid"
        assert step.retries_attempted == 2


# ============================================================================
# ErrorRecoveryMetrics Tests
# ============================================================================

class TestErrorRecoveryMetrics:
    """Tests for error recovery metrics."""

    def test_create_recovery(self):
        """Test creating recovery metrics."""
        recovery = ErrorRecoveryMetrics(
            error_type="bridge_timeout",
            error_message="Connection timed out",
            recovery_strategy="retry",
            success=True,
            attempts=2,
            duration_ms=500.0,
        )

        assert recovery.error_type == "bridge_timeout"
        assert recovery.recovery_strategy == "retry"
        assert recovery.success is True


# ============================================================================
# BridgeHealthMetrics Tests
# ============================================================================

class TestBridgeHealthMetrics:
    """Tests for bridge health metrics."""

    def test_create_health(self):
        """Test creating bridge health metrics."""
        health = BridgeHealthMetrics(
            touchdesigner_degraded_mode_activated=True,
            touchdesigner_retries_needed=3,
        )

        assert health.touchdesigner_degraded_mode_activated is True
        assert health.touchdesigner_retries_needed == 3


# ============================================================================
# SessionMetadata Tests
# ============================================================================

class TestSessionMetadata:
    """Tests for SessionMetadata."""

    def test_create_metadata(self, sample_session_metadata):
        """Test creating session metadata."""
        assert sample_session_metadata.session_id == "test_session_001"
        assert sample_session_metadata.goal == "Create Houdini procedural geometry"
        assert sample_session_metadata.domain == "houdini"

    def test_metadata_summary(self, sample_session_metadata):
        """Test metadata summary generation."""
        sample_session_metadata.total_duration_s = 5.68
        sample_session_metadata.success = True
        sample_session_metadata.knowledge.distilled_knowledge_hits = 2
        sample_session_metadata.knowledge.distilled_knowledge_preferred = 2

        summary = sample_session_metadata.summary()

        assert "Create Houdini procedural geometry" in summary
        assert "5.68s" in summary

    def test_metadata_to_dict(self, sample_session_metadata):
        """Test metadata serialization to dict."""
        sample_session_metadata.total_steps = 4
        sample_session_metadata.successful_steps = 3

        data = sample_session_metadata.to_dict()

        assert data["session_id"] == "test_session_001"
        assert data["total_steps"] == 4
        assert data["successful_steps"] == 3

    def test_metadata_from_dict(self):
        """Test creating metadata from dict."""
        data = {
            "session_id": "test_002",
            "timestamp": "2024-01-01T12:00:00",
            "goal": "Test goal",
            "domain": "touchdesigner",
            "total_duration_s": 10.0,
            "success": True,
            "knowledge": {"distilled_knowledge_hits": 3},
            "rag": {"total_queries": 2},
            "planning": {"subgoals_generated": 4},
        }

        metadata = SessionMetadata.from_dict(data)

        assert metadata.session_id == "test_002"
        assert metadata.knowledge.distilled_knowledge_hits == 3

    def test_metadata_file_operations(self, sample_session_metadata, temp_session_path):
        """Test saving and loading metadata."""
        sample_session_metadata.success = True

        # Save
        assert sample_session_metadata.to_file(temp_session_path) is True

        # Load
        loaded = SessionMetadata.from_file(temp_session_path)
        assert loaded is not None
        assert loaded.session_id == sample_session_metadata.session_id

    def test_metadata_factory(self):
        """Test factory method."""
        metadata = SessionMetadata.create(
            session_id="factory_test",
            goal="Factory goal",
            domain="general",
        )

        assert metadata.session_id == "factory_test"
        assert metadata.planning.goal == "Factory goal"


# ============================================================================
# SessionTracker Tests
# ============================================================================

class TestSessionTracker:
    """Tests for SessionTracker."""

    def test_tracker_creation(self, tracker):
        """Test tracker creation."""
        assert tracker.metadata.session_id == "test_session_001"
        assert tracker.metadata.goal == "Test goal"

    def test_record_phase(self, tracker):
        """Test phase recording."""
        tracker.record_phase_start(ExecutionPhase.PLANNING)
        assert "planning" in tracker.metadata.phases_executed

        tracker.record_phase_end(ExecutionPhase.PLANNING)
        assert "planning" in tracker.metadata.phase_timings

    def test_record_knowledge_hit(self, tracker):
        """Test knowledge hit recording."""
        tracker.record_knowledge_hit(
            recipe_id="recipe_001",
            recipe_title="Test Recipe",
            confidence=0.85,
            source="distilled",
            phase="planning",
        )

        assert tracker.metadata.knowledge.distilled_knowledge_hits == 1
        assert tracker.metadata.knowledge.distilled_knowledge_preferred == 1

    def test_record_low_confidence_hit(self, tracker):
        """Test low confidence hit recording."""
        tracker.record_knowledge_hit(
            recipe_id="recipe_low",
            recipe_title="Low Confidence",
            confidence=0.3,
            source="rag",
            phase="planning",
        )

        assert tracker.metadata.knowledge.low_confidence_hits == 1

    def test_record_rag_query(self, tracker):
        """Test RAG query recording."""
        tracker.record_rag_query(
            query="test query",
            chunks_retrieved=5,
            avg_confidence=0.85,
            latency_ms=24.5,
            domain="houdini",
        )

        assert tracker.metadata.rag.total_queries == 1
        assert tracker.metadata.rag.total_chunks_retrieved == 5
        assert tracker.metadata.rag.avg_confidence == 0.85

    def test_record_multiple_rag_queries(self, tracker):
        """Test multiple RAG queries with averaging."""
        tracker.record_rag_query("query1", 5, 0.8, 20.0)
        tracker.record_rag_query("query2", 3, 0.9, 30.0)

        assert tracker.metadata.rag.total_queries == 2
        assert tracker.metadata.rag.total_chunks_retrieved == 8
        assert tracker.metadata.rag.avg_latency_ms == 25.0

    def test_record_zero_result_query(self, tracker):
        """Test zero result query."""
        tracker.record_rag_query(
            query="no results query",
            chunks_retrieved=0,
            avg_confidence=0.0,
            latency_ms=10.0,
        )

        assert tracker.metadata.rag.zero_result_queries == 1

    def test_record_planning_step(self, tracker):
        """Test planning step recording."""
        tracker.record_planning_step(
            complexity_score=7.5,
            subgoals=4,
            plan_quality=0.85,
            strategy="decompose",
        )

        assert tracker.metadata.planning.initial_complexity_score == 7.5
        assert tracker.metadata.planning.subgoals_generated == 4

    def test_record_replanning(self, tracker):
        """Test replanning recording."""
        tracker.record_replanning("Goal changed")
        tracker.record_replanning("Error detected")

        assert tracker.metadata.planning.replan_count == 2
        assert tracker.metadata.planning.replanning_triggered is True
        assert len(tracker.metadata.planning.replanning_reasons) == 2

    def test_record_execution_step(self, tracker):
        """Test execution step recording."""
        tracker.record_execution_step(
            order=1,
            action="Create geometry",
            bridge="houdini",
            duration_ms=156.0,
            success=True,
        )

        assert tracker.metadata.total_steps == 1
        assert tracker.metadata.successful_steps == 1

    def test_record_failed_step(self, tracker):
        """Test failed step recording."""
        tracker.record_execution_step(
            order=1,
            action="Create geometry",
            bridge="houdini",
            duration_ms=500.0,
            success=False,
            error_message="Connection failed",
        )

        assert tracker.metadata.total_steps == 1
        assert tracker.metadata.successful_steps == 0

    def test_record_error_recovery(self, tracker):
        """Test error recovery recording."""
        tracker.record_error_recovery(
            error_type="bridge_timeout",
            error_message="Connection timed out",
            strategy="retry",
            success=True,
            attempts=2,
            duration_ms=500.0,
        )

        assert len(tracker.metadata.error_recoveries) == 1
        assert tracker.metadata.error_recoveries[0].success is True

    def test_record_bridge_degraded(self, tracker):
        """Test bridge degraded recording."""
        tracker.record_bridge_degraded("touchdesigner", "Connection unstable")

        assert tracker.metadata.bridge.touchdesigner_degraded_mode_activated is True

    def test_record_bridge_retry(self, tracker):
        """Test bridge retry recording."""
        tracker.record_bridge_retry("houdini", "Timeout")
        tracker.record_bridge_retry("houdini")

        assert tracker.metadata.bridge.houdini_retries_needed == 2

    def test_record_contradiction(self, tracker):
        """Test contradiction recording."""
        tracker.record_contradiction("knowledge_conflict", resolved=True)

        assert tracker.metadata.knowledge.contradictions_found == 1
        assert tracker.metadata.knowledge.contradictions_resolved == 1

    def test_record_fallback(self, tracker):
        """Test fallback recording."""
        tracker.record_fallback_used("rag_only", "No distilled recipes available")

        assert tracker.metadata.knowledge.rag_fallback_used == 1

    def test_record_error(self, tracker):
        """Test error recording."""
        tracker.record_error("execution_error", "Step failed", {"step": 2})

        assert len(tracker.metadata.errors) == 1

    def test_record_warning(self, tracker):
        """Test warning recording."""
        tracker.record_warning("This is a warning")

        assert len(tracker.metadata.warnings) == 1

    def test_add_tags_and_labels(self, tracker):
        """Test adding tags and labels."""
        tracker.add_tag("test")
        tracker.add_tag("integration")
        tracker.add_label("priority", "high")

        assert "test" in tracker.metadata.tags
        assert tracker.metadata.labels["priority"] == "high"

    def test_finalize(self, tracker):
        """Test finalization."""
        import time
        time.sleep(0.01)  # Small delay to ensure duration > 0
        tracker.finalize(success=True)

        assert tracker.metadata.success is True
        assert tracker.metadata.total_duration_s >= 0

    def test_export(self, tracker, temp_session_path):
        """Test export to file."""
        tracker.finalize(success=True)
        filepath = tracker.export(filepath=temp_session_path)

        assert os.path.exists(filepath)

        with open(filepath, "r") as f:
            data = json.load(f)

        assert data["session_id"] == "test_session_001"

    def test_get_summary_dict(self, tracker):
        """Test summary dictionary."""
        tracker.record_execution_step(1, "Test", "houdini", 100.0, True)
        tracker.finalize(success=True)

        summary = tracker.get_summary_dict()

        assert summary["session_id"] == "test_session_001"
        assert summary["success"] is True
        assert summary["steps"]["total"] == 1


# ============================================================================
# SessionDisplayFormatter Tests
# ============================================================================

class TestSessionDisplayFormatter:
    """Tests for display formatter."""

    def test_format_basic(self, sample_session_metadata):
        """Test basic formatting."""
        sample_session_metadata.success = True
        sample_session_metadata.total_duration_s = 5.0

        output = SessionDisplayFormatter.format_session_output(sample_session_metadata)

        assert "SUCCESS" in output
        assert "5.00s" in output

    def test_format_with_knowledge(self, sample_session_metadata):
        """Test formatting with knowledge hits."""
        sample_session_metadata.knowledge.distilled_knowledge_hits = 3
        sample_session_metadata.knowledge.distilled_knowledge_preferred = 2

        output = SessionDisplayFormatter.format_session_output(sample_session_metadata)

        assert "Knowledge:" in output
        assert "Recipes used: 3" in output

    def test_format_with_rag(self, sample_session_metadata):
        """Test formatting with RAG queries."""
        sample_session_metadata.rag.total_queries = 2
        sample_session_metadata.rag.total_chunks_retrieved = 10
        sample_session_metadata.rag.avg_confidence = 0.85

        output = SessionDisplayFormatter.format_session_output(sample_session_metadata)

        assert "Retrieval:" in output
        assert "RAG queries: 2" in output

    def test_format_with_planning(self, sample_session_metadata):
        """Test formatting with planning info."""
        sample_session_metadata.planning.subgoals_generated = 4
        sample_session_metadata.planning.replan_count = 1
        sample_session_metadata.planning.replanning_reasons = ["Goal changed"]

        output = SessionDisplayFormatter.format_session_output(sample_session_metadata, verbose=True)

        assert "Planning:" in output
        assert "Subgoals: 4" in output
        assert "Replans: 1" in output

    def test_format_with_execution(self, sample_session_metadata):
        """Test formatting with execution steps."""
        sample_session_metadata.execution_steps = [
            ExecutionStepMetrics(
                order=1,
                action="Create geometry",
                bridge_type="houdini",
                duration_ms=156.0,
                success=True,
            ),
            ExecutionStepMetrics(
                order=2,
                action="Add noise",
                bridge_type="houdini",
                duration_ms=89.0,
                success=True,
            ),
        ]
        sample_session_metadata.total_steps = 2
        sample_session_metadata.successful_steps = 2

        output = SessionDisplayFormatter.format_session_output(sample_session_metadata, verbose=True)

        assert "Execution:" in output
        assert "Steps: 2/2" in output

    def test_format_with_bridge_issues(self, sample_session_metadata):
        """Test formatting with bridge issues."""
        sample_session_metadata.bridge.touchdesigner_degraded_mode_activated = True
        sample_session_metadata.bridge.touchdesigner_retries_needed = 3

        output = SessionDisplayFormatter.format_session_output(sample_session_metadata)

        assert "Bridge Issues:" in output
        assert "TouchDesigner degraded" in output

    def test_format_verbose(self, sample_session_metadata):
        """Test verbose formatting."""
        sample_session_metadata.phase_timings = {
            "planning": 2.34,
            "execution": 2.78,
        }

        output = SessionDisplayFormatter.format_session_output(
            sample_session_metadata,
            verbose=True,
        )

        assert "Phase Timings:" in output
        assert "planning" in output

    def test_convenience_function(self, sample_session_metadata):
        """Test convenience function."""
        output = format_session_summary(sample_session_metadata)

        assert isinstance(output, str)
        assert len(output) > 0


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Integration tests for session tracking."""

    def test_full_tracking_workflow(self, temp_session_path):
        """Test full tracking workflow."""
        # Create tracker
        tracker = SessionTracker(
            session_id="integration_test",
            goal="Create Houdini geometry",
            domain="houdini",
            verbose=False,
        )

        # Phase 1: Planning
        tracker.record_phase_start(ExecutionPhase.PLANNING)
        tracker.record_knowledge_hit(
            "recipe_001",
            "Procedural Geometry",
            0.92,
            "distilled",
            "planning",
        )
        tracker.record_rag_query("houdini geometry", 3, 0.88, 24.0)
        tracker.record_planning_step(7.5, 4, 0.85)
        tracker.record_phase_end(ExecutionPhase.PLANNING)

        # Phase 2: Execution
        tracker.record_phase_start(ExecutionPhase.EXECUTION)
        tracker.record_execution_step(1, "Create geometry", "houdini", 156.0, True)
        tracker.record_execution_step(2, "Add noise", "houdini", 2340.0, False, "Parameter invalid")
        tracker.record_error_recovery("parameter_invalid", "Invalid parameter", "retry", True, 2, 500.0)
        tracker.record_execution_step(3, "Connect nodes", "houdini", 67.0, True)
        tracker.record_phase_end(ExecutionPhase.EXECUTION)

        # Finalize
        tracker.finalize(success=True)

        # Export
        filepath = tracker.export(filepath=temp_session_path)

        # Verify
        assert tracker.metadata.knowledge.distilled_knowledge_hits == 1
        assert tracker.metadata.rag.total_queries == 1
        assert tracker.metadata.total_steps == 3
        assert tracker.metadata.successful_steps == 2
        assert len(tracker.metadata.error_recoveries) == 1

    def test_bridge_failure_workflow(self):
        """Test workflow with bridge failures."""
        tracker = SessionTracker(
            session_id="bridge_test",
            goal="Create TD noise",
            domain="touchdesigner",
            verbose=False,
        )

        # Bridge issues
        tracker.record_bridge_connection_attempt("touchdesigner", False)
        tracker.record_bridge_retry("touchdesigner", "Connection refused")
        tracker.record_bridge_degraded("touchdesigner")
        tracker.record_fallback_to_ui("Bridge unavailable")

        tracker.finalize(success=False)

        assert tracker.metadata.bridge.touchdesigner_degraded_mode_activated is True
        assert tracker.metadata.bridge.touchdesigner_retries_needed == 1
        assert tracker.metadata.bridge.fallback_to_ui is True


# ============================================================================
# Edge Cases
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_session(self):
        """Test empty session with no activity."""
        tracker = SessionTracker(
            session_id="empty",
            goal="Empty goal",
            domain="general",
            verbose=False,
        )

        tracker.finalize(success=True)

        assert tracker.metadata.total_steps == 0
        assert tracker.metadata.knowledge.distilled_knowledge_hits == 0

    def test_all_failures(self):
        """Test session where everything fails."""
        tracker = SessionTracker(
            session_id="failures",
            goal="Failing goal",
            domain="houdini",
            verbose=False,
        )

        tracker.record_execution_step(1, "Step 1", "houdini", 100.0, False, "Error 1")
        tracker.record_execution_step(2, "Step 2", "houdini", 100.0, False, "Error 2")
        tracker.record_error_recovery("error", "Failed", "retry", False)

        tracker.finalize(success=False)

        assert tracker.metadata.successful_steps == 0
        assert tracker.metadata.total_steps == 2
        assert tracker.metadata.success is False

    def test_very_long_goal(self):
        """Test with very long goal string."""
        long_goal = "Create " * 100 + "geometry"

        tracker = SessionTracker(
            session_id="long_goal",
            goal=long_goal,
            domain="houdini",
            verbose=False,
        )

        tracker.finalize(success=True)

        assert len(tracker.metadata.goal) == len(long_goal)

    def test_special_characters(self):
        """Test with special characters."""
        tracker = SessionTracker(
            session_id="special",
            goal="Create geometry with special: cafe",
            domain="houdini",
            verbose=False,
        )

        tracker.record_warning("Warning with special chars")

        tracker.finalize(success=True)

        # Should not raise encoding errors
        output = format_session_summary(tracker.metadata)
        assert isinstance(output, str)