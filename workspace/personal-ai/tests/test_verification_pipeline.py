"""Tests for Post-Execution Verification Pipeline.

This test suite verifies:
1. ExpectedState dataclass creation and serialization
2. VisualVerifier screenshot comparison
3. StateQueryVerifier state queries
4. ExecutionVerifier unified pipeline
5. Screenshot capture utilities
"""

import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from app.evaluation import (
    ExecutionVerificationReport,
    ExecutionVerifier,
    ExpectedState,
    ScreenshotCapture,
    StateQueryVerificationResult,
    VerifierConfig,
    VisualVerificationResult,
    create_execution_verifier,
)


class TestExpectedState:
    """Tests for ExpectedState dataclass."""

    def test_create_expected_state(self):
        """Test creating ExpectedState with various fields."""
        state = ExpectedState(
            new_elements_visible=["comp1", "null1"],
            node_count=2,
            parameter_values={"blur1.amount": 5.0},
        )

        assert state.new_elements_visible == ["comp1", "null1"]
        assert state.node_count == 2
        assert state.parameter_values == {"blur1.amount": 5.0}

    def test_expected_state_defaults(self):
        """Test ExpectedState default values."""
        state = ExpectedState()

        assert state.new_elements_visible == []
        assert state.removed_elements == []
        assert state.node_count is None
        assert state.dialog_open is None
        assert state.selection_changed is False

    def test_expected_state_to_dict(self):
        """Test ExpectedState serialization."""
        state = ExpectedState(
            new_elements_visible=["comp1"],
            node_count=1,
        )

        data = state.to_dict()

        assert data["new_elements_visible"] == ["comp1"]
        assert data["node_count"] == 1
        assert data["removed_elements"] == []

    def test_expected_state_from_dict(self):
        """Test ExpectedState deserialization."""
        data = {
            "new_elements_visible": ["comp1"],
            "node_count": 1,
            "parameter_values": {"blur.amount": 5.0},
        }

        state = ExpectedState.from_dict(data)

        assert state.new_elements_visible == ["comp1"]
        assert state.node_count == 1
        assert state.parameter_values == {"blur.amount": 5.0}

    def test_expected_state_summary(self):
        """Test ExpectedState summary generation."""
        state = ExpectedState(
            new_elements_visible=["comp1", "null1"],
            node_count=2,
            active_network="/obj",
        )

        summary = state.summary()

        assert "comp1" in summary
        assert "nodes: 2" in summary
        assert "network: /obj" in summary


class TestVisualVerificationResult:
    """Tests for VisualVerificationResult."""

    def test_visual_result_success(self):
        """Test success property when all assertions pass."""
        result = VisualVerificationResult(
            before_screenshot="before.png",
            after_screenshot="after.png",
            assertions_passed=[{"type": "element_appeared"}],
            assertions_failed=[],
            confidence=1.0,
        )

        assert result.success is True

    def test_visual_result_failure(self):
        """Test success property when assertions fail."""
        result = VisualVerificationResult(
            before_screenshot="before.png",
            after_screenshot="after.png",
            assertions_passed=[],
            assertions_failed=[{"type": "element_appeared"}],
            confidence=0.0,
        )

        assert result.success is False

    def test_visual_result_summary(self):
        """Test summary generation."""
        result = VisualVerificationResult(
            before_screenshot="before.png",
            after_screenshot="after.png",
            assertions_passed=[{"type": "a"}, {"type": "b"}],
            assertions_failed=[{"type": "c"}],
            confidence=0.67,
        )

        summary = result.summary()

        assert "PASS" in summary or "FAIL" in summary
        assert "2 passed" in summary
        assert "1 failed" in summary
        assert "67%" in summary


class TestStateQueryVerificationResult:
    """Tests for StateQueryVerificationResult."""

    def test_state_result_success(self):
        """Test success property."""
        result = StateQueryVerificationResult(
            assertions_passed=[{"type": "node_count"}],
            assertions_failed=[],
            confidence=1.0,
        )

        assert result.success is True

    def test_state_result_summary(self):
        """Test summary generation."""
        result = StateQueryVerificationResult(
            assertions_passed=[{"type": "a"}],
            assertions_failed=[{"type": "b"}],
            confidence=0.5,
        )

        summary = result.summary()

        assert "State Query" in summary
        assert "1 passed" in summary
        assert "1 failed" in summary


class TestExecutionVerificationReport:
    """Tests for ExecutionVerificationReport."""

    def test_report_success(self):
        """Test overall success with both methods passing."""
        expected = ExpectedState(new_elements_visible=["comp1"])

        report = ExecutionVerificationReport(
            action="Create comp1",
            expected_state=expected,
            overall_success=True,
            confidence=0.9,
            all_assertions_passed=[{"type": "element"}],
            all_assertions_failed=[],
        )

        assert report.overall_success is True
        assert report.confidence == 0.9

    def test_report_summary(self):
        """Test summary generation."""
        expected = ExpectedState(new_elements_visible=["comp1"])

        report = ExecutionVerificationReport(
            action="Create comp1 node in TouchDesigner",
            expected_state=expected,
            overall_success=True,
            confidence=0.95,
            all_assertions_passed=[{"type": "a"}, {"type": "b"}],
            all_assertions_failed=[],
        )

        summary = report.summary()

        assert "PASS" in summary
        assert "Create comp1" in summary
        assert "95%" in summary


class TestExecutionVerifier:
    """Tests for ExecutionVerifier."""

    def test_create_verifier(self):
        """Test creating ExecutionVerifier."""
        verifier = create_execution_verifier(
            enable_visual=True,
            enable_state_query=True,
            min_confidence=0.7,
        )

        assert verifier.config.enable_visual is True
        assert verifier.config.enable_state_query is True
        assert verifier.config.min_confidence_threshold == 0.7

    def test_infer_expected_state_create(self):
        """Test inferring expected state from create action."""
        verifier = ExecutionVerifier()

        expected = verifier.infer_expected_state("Create comp1 and null1")

        assert "comp1" in expected.new_elements_visible
        assert "null1" in expected.new_elements_visible
        assert expected.node_count == 2

    def test_infer_expected_state_delete(self):
        """Test inferring expected state from delete action."""
        verifier = ExecutionVerifier()

        expected = verifier.infer_expected_state("Delete the old node")

        assert "old" in expected.removed_elements or "node" in expected.removed_elements

    def test_infer_expected_state_connect(self):
        """Test inferring expected state from connect action."""
        verifier = ExecutionVerifier()

        expected = verifier.infer_expected_state("Connect blur1 to comp1")

        assert expected.connection_count == 1

    def test_infer_expected_state_parameter(self):
        """Test inferring expected state from parameter set action."""
        verifier = ExecutionVerifier()

        expected = verifier.infer_expected_state("Set blur1.amount to 5.0")

        assert "blur1.amount" in expected.parameter_values
        assert expected.parameter_values["blur1.amount"] == 5.0

    def test_infer_expected_state_dialog(self):
        """Test inferring expected state from dialog action."""
        verifier = ExecutionVerifier()

        expected_close = verifier.infer_expected_state("Close the error dialog")
        assert expected_close.dialog_open is None

        expected_open = verifier.infer_expected_state("Open settings dialog")
        assert expected_open.dialog_open is not None


class TestScreenshotCapture:
    """Tests for ScreenshotCapture."""

    def test_create_capture(self):
        """Test creating ScreenshotCapture."""
        with tempfile.TemporaryDirectory() as tmpdir:
            capture = ScreenshotCapture(output_dir=tmpdir)
            assert capture._output_dir == tmpdir
            assert os.path.exists(tmpdir)

    def test_ensure_output_dir(self):
        """Test output directory creation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            nested_dir = os.path.join(tmpdir, "nested", "screenshots")
            capture = ScreenshotCapture(output_dir=nested_dir)
            assert os.path.exists(nested_dir)


class TestIntegration:
    """Integration tests for verification pipeline."""

    @patch("app.evaluation.visual_verifier.VisualUnderstandingPipeline")
    def test_verify_execution_with_mocks(self, mock_pipeline_class):
        """Test full verification flow with mocked VLM."""
        # Setup mock
        mock_pipeline = MagicMock()
        mock_pipeline_class.return_value = mock_pipeline

        # Mock understanding results
        before_state = MagicMock()
        before_state.combined_state = {"nodes_visible": []}
        after_state = MagicMock()
        after_state.combined_state = {"nodes_visible": ["comp1"]}

        mock_pipeline.understand_screenshot.side_effect = [before_state, after_state]

        # Create verifier with mocked pipeline
        from app.evaluation.visual_verifier import VisualVerifier
        verifier = VisualVerifier(vision_pipeline=mock_pipeline)

        # Test visual verification
        expected = ExpectedState(new_elements_visible=["comp1"], node_count=1)

        with tempfile.TemporaryDirectory() as tmpdir:
            before_path = os.path.join(tmpdir, "before.png")
            after_path = os.path.join(tmpdir, "after.png")

            # Create dummy files
            open(before_path, "w").close()
            open(after_path, "w").close()

            result = verifier.verify_visual_change(
                before_path,
                after_path,
                expected,
                "touchdesigner",
            )

            assert result.before_screenshot == before_path
            assert result.after_screenshot == after_path


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
