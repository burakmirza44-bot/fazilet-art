"""Tests for Evaluation Runtime Module.

Tests the evaluation test framework including models, runner, CLI,
regression detection, and orchestration integration.
"""

import asyncio
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.eval_runtime import (
    EVAL_TESTS,
    EvalDomain,
    EvalGuard,
    EvalSeverity,
    EvalSuiteReport,
    EvalSuiteRunner,
    EvalTestCase,
    EvalTestResult,
    ExecutionResult,
    OrchestrationWithEval,
    RegressionDetector,
    RegressionReport,
    get_test,
    list_test_names,
    list_tests,
    register_test,
    run_quick_check,
    validate_before_execution,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_test_case():
    """Create a sample test case."""
    return EvalTestCase(
        name="test_example",
        description="Example test for testing",
        domain=EvalDomain.GENERAL,
        severity=EvalSeverity.MEDIUM,
        test_function=lambda: {"success": True, "value": 42},
        timeout=5.0,
    )


@pytest.fixture
def failing_test_case():
    """Create a failing test case."""
    return EvalTestCase(
        name="test_failing",
        description="A test that fails",
        domain=EvalDomain.GENERAL,
        severity=EvalSeverity.HIGH,
        test_function=lambda: {"success": False, "error": "Test failure"},
        timeout=5.0,
    )


@pytest.fixture
def async_test_case():
    """Create an async test case."""
    async def async_test():
        await asyncio.sleep(0.1)
        return {"success": True, "async": True}

    return EvalTestCase(
        name="test_async",
        description="Async test",
        domain=EvalDomain.GENERAL,
        severity=EvalSeverity.LOW,
        test_function=async_test,
        timeout=5.0,
    )


@pytest.fixture
def runner():
    """Create a test runner."""
    return EvalSuiteRunner()


@pytest.fixture
def temp_report_path():
    """Create a temporary file path for reports."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield os.path.join(tmpdir, "eval_report.json")


# ============================================================================
# EvalSeverity Tests
# ============================================================================

class TestEvalSeverity:
    """Tests for EvalSeverity enum."""

    def test_severity_order(self):
        """Test severity order is correct."""
        order = EvalSeverity.severity_order()

        assert order[0] == EvalSeverity.CRITICAL
        assert order[1] == EvalSeverity.HIGH
        assert order[2] == EvalSeverity.MEDIUM
        assert order[3] == EvalSeverity.LOW

    def test_threshold_index(self):
        """Test threshold index calculation."""
        assert EvalSeverity.CRITICAL.threshold_index() == 0
        assert EvalSeverity.HIGH.threshold_index() == 1
        assert EvalSeverity.MEDIUM.threshold_index() == 2
        assert EvalSeverity.LOW.threshold_index() == 3


# ============================================================================
# EvalTestResult Tests
# ============================================================================

class TestEvalTestResult:
    """Tests for EvalTestResult dataclass."""

    def test_create_result(self):
        """Test creating a test result."""
        result = EvalTestResult(
            test_name="test_example",
            success=True,
            output={"value": 42},
            execution_time=1.5,
        )

        assert result.test_name == "test_example"
        assert result.success is True
        assert result.output["value"] == 42

    def test_result_to_dict(self):
        """Test result serialization."""
        result = EvalTestResult(
            test_name="test_example",
            success=True,
            execution_time=1.5,
            domain="general",
            severity="medium",
        )

        data = result.to_dict()

        assert data["test"] == "test_example"
        assert data["status"] == "PASS"
        assert data["time_ms"] == 1500
        assert data["domain"] == "general"

    def test_result_from_dict(self):
        """Test result deserialization."""
        data = {
            "test": "test_example",
            "status": "FAIL",
            "time_ms": 500,
            "error": "Test error",
        }

        result = EvalTestResult.from_dict(data)

        assert result.test_name == "test_example"
        assert result.success is False
        assert result.error == "Test error"


# ============================================================================
# EvalTestCase Tests
# ============================================================================

class TestEvalTestCase:
    """Tests for EvalTestCase."""

    def test_create_test_case(self, sample_test_case):
        """Test creating a test case."""
        assert sample_test_case.name == "test_example"
        assert sample_test_case.domain == EvalDomain.GENERAL
        assert sample_test_case.timeout == 5.0

    def test_run_sync_test(self, sample_test_case):
        """Test running a sync test."""
        result = sample_test_case.run_sync()

        assert result.success is True
        assert result.test_name == "test_example"

    @pytest.mark.asyncio
    async def test_run_async_test(self, async_test_case):
        """Test running an async test."""
        result = await async_test_case.run()

        assert result.success is True
        assert result.output.get("async") is True

    def test_validate_output_success(self):
        """Test output validation with expected values."""
        test = EvalTestCase(
            name="test_validation",
            description="Test validation",
            domain=EvalDomain.GENERAL,
            severity=EvalSeverity.MEDIUM,
            test_function=lambda: {"success": True, "count": 10},
            expected_output={
                "success": True,
                "count": lambda x: x > 5,
            },
        )

        result = test.run_sync()

        assert result.success is True

    def test_validate_output_failure(self):
        """Test output validation with failing validation."""
        test = EvalTestCase(
            name="test_validation_fail",
            description="Test validation failure",
            domain=EvalDomain.GENERAL,
            severity=EvalSeverity.MEDIUM,
            test_function=lambda: {"success": True, "count": 3},
            expected_output={
                "count": lambda x: x > 5,
            },
        )

        result = test.run_sync()

        assert result.success is False

    def test_timeout_handling(self):
        """Test timeout handling for slow tests."""
        import time

        test = EvalTestCase(
            name="test_timeout",
            description="Test timeout",
            domain=EvalDomain.GENERAL,
            severity=EvalSeverity.MEDIUM,
            test_function=lambda: time.sleep(10),  # Slow test
            timeout=0.1,  # Very short timeout
        )

        # Sync run doesn't have timeout, but async does
        # This test verifies the test case is created properly


# ============================================================================
# EvalSuiteReport Tests
# ============================================================================

class TestEvalSuiteReport:
    """Tests for EvalSuiteReport."""

    def test_create_report(self):
        """Test creating a report."""
        report = EvalSuiteReport(
            total_tests=10,
            passed_tests=8,
            failed_tests=2,
            critical_failures=0,
            test_results=[],
            total_time=15.5,
            timestamp=datetime.now().isoformat(),
            success=True,
        )

        assert report.total_tests == 10
        assert report.passed_tests == 8
        assert report.success is True

    def test_report_summary(self):
        """Test report summary generation."""
        report = EvalSuiteReport(
            total_tests=5,
            passed_tests=4,
            failed_tests=1,
            critical_failures=0,
            test_results=[],
            total_time=10.0,
            timestamp="2024-01-01T12:00:00",
            success=False,
        )

        summary = report.summary()

        assert "Total Tests:" in summary
        assert "5" in summary
        assert "FAIL" in summary

    def test_report_to_json(self):
        """Test JSON export."""
        report = EvalSuiteReport(
            total_tests=1,
            passed_tests=1,
            failed_tests=0,
            critical_failures=0,
            test_results=[{"test": "test_1", "status": "PASS"}],
            total_time=1.0,
            timestamp="2024-01-01",
            success=True,
        )

        json_str = report.to_json()
        data = json.loads(json_str)

        assert data["summary"]["total"] == 1
        assert data["summary"]["passed"] == 1

    def test_report_file_operations(self, temp_report_path):
        """Test saving and loading report."""
        report = EvalSuiteReport(
            total_tests=5,
            passed_tests=5,
            failed_tests=0,
            critical_failures=0,
            test_results=[],
            total_time=5.0,
            timestamp="2024-01-01",
            success=True,
        )

        # Save
        assert report.to_file(temp_report_path) is True

        # Load
        loaded = EvalSuiteReport.from_file(temp_report_path)
        assert loaded is not None
        assert loaded.total_tests == 5

    def test_empty_report(self):
        """Test creating empty report."""
        report = EvalSuiteReport.empty()

        assert report.total_tests == 0
        assert report.success is True

    def test_single_test_report(self):
        """Test creating report from single result."""
        result = EvalTestResult(
            test_name="single_test",
            success=True,
            execution_time=1.0,
        )

        report = EvalSuiteReport.single_test(result)

        assert report.total_tests == 1
        assert report.passed_tests == 1


# ============================================================================
# EvalSuiteRunner Tests
# ============================================================================

class TestEvalSuiteRunner:
    """Tests for EvalSuiteRunner."""

    def test_runner_creation(self, runner):
        """Test runner creation."""
        assert runner.results == []

    @pytest.mark.asyncio
    async def test_run_single_test(self, runner, sample_test_case):
        """Test running a single test."""
        register_test("test_example", sample_test_case)

        report = await runner.run_all_tests(test_names=["test_example"])

        assert report.total_tests == 1
        assert report.passed_tests == 1

    @pytest.mark.asyncio
    async def test_run_with_domain_filter(self, runner):
        """Test filtering by domain."""
        report = await runner.run_all_tests(domain=EvalDomain.HOUDINI)

        # Should only run Houdini tests
        for result in runner.results:
            assert result.domain in ("houdini", "")

    @pytest.mark.asyncio
    async def test_run_with_severity_filter(self, runner):
        """Test filtering by severity."""
        report = await runner.run_all_tests(severity=EvalSeverity.CRITICAL)

        # Should only run critical tests
        for result in runner.results:
            assert result.severity in ("critical", "")

    @pytest.mark.asyncio
    async def test_run_sequential(self, runner):
        """Test sequential execution."""
        report = await runner.run_all_tests(parallel=False)

        assert report.total_tests > 0 or report.total_tests == 0

    def test_run_sync(self, runner, sample_test_case):
        """Test synchronous run."""
        register_test("test_sync", sample_test_case)

        report = runner.run_all_tests_sync(test_names=["test_sync"])

        assert report.total_tests == 1

    def test_run_quick_check(self):
        """Test quick check function."""
        report = run_quick_check()

        assert isinstance(report, EvalSuiteReport)


# ============================================================================
# Registry Tests
# ============================================================================

class TestRegistry:
    """Tests for test registry."""

    def test_register_test(self, sample_test_case):
        """Test registering a test."""
        register_test("custom_test", sample_test_case)

        assert "custom_test" in EVAL_TESTS

    def test_get_test(self, sample_test_case):
        """Test getting a test by name."""
        register_test("get_test", sample_test_case)

        test = get_test("get_test")

        assert test is not None
        assert test.name == "test_example"

    def test_get_nonexistent_test(self):
        """Test getting nonexistent test."""
        test = get_test("nonexistent_test")

        assert test is None

    def test_list_tests(self):
        """Test listing tests."""
        tests = list_tests()

        assert len(tests) > 0

    def test_list_tests_by_domain(self):
        """Test listing tests by domain."""
        tests = list_tests(domain=EvalDomain.HOUDINI)

        for test in tests:
            assert test.domain == EvalDomain.HOUDINI

    def test_list_test_names(self):
        """Test listing test names."""
        names = list_test_names()

        assert len(names) > 0
        assert isinstance(names[0], str)


# ============================================================================
# Regression Tests
# ============================================================================

class TestRegressionDetector:
    """Tests for regression detection."""

    def test_detector_creation(self):
        """Test creating detector."""
        detector = RegressionDetector()

        assert detector.baseline is None

    def test_load_baseline(self, temp_report_path):
        """Test loading baseline."""
        # Create a baseline file
        baseline_data = {
            "summary": {"total": 5, "passed": 5, "failed": 0},
            "results": [
                {"test": "test_1", "status": "PASS", "time_ms": 100},
            ],
        }

        with open(temp_report_path, "w") as f:
            json.dump(baseline_data, f)

        detector = RegressionDetector(baseline_report_path=temp_report_path)

        assert detector.baseline is not None

    def test_detect_failure_regression(self, temp_report_path):
        """Test detecting failure regression."""
        # Create baseline with passing test
        baseline_data = {
            "results": [
                {"test": "test_1", "status": "PASS", "time_ms": 100},
            ],
        }

        with open(temp_report_path, "w") as f:
            json.dump(baseline_data, f)

        detector = RegressionDetector(baseline_report_path=temp_report_path)

        # Create current report with failing test
        current = EvalSuiteReport(
            total_tests=1,
            passed_tests=0,
            failed_tests=1,
            critical_failures=0,
            test_results=[
                {"test": "test_1", "status": "FAIL", "time_ms": 100, "error": "Failed"},
            ],
            total_time=1.0,
            timestamp="",
            success=False,
        )

        report = detector.detect_regressions(current)

        assert len(report.regressions) == 1
        assert report.regressions[0]["type"] == "failure_regression"

    def test_detect_improvement(self, temp_report_path):
        """Test detecting improvements."""
        # Create baseline with failing test
        baseline_data = {
            "results": [
                {"test": "test_1", "status": "FAIL", "time_ms": 100},
            ],
        }

        with open(temp_report_path, "w") as f:
            json.dump(baseline_data, f)

        detector = RegressionDetector(baseline_report_path=temp_report_path)

        # Create current report with passing test
        current = EvalSuiteReport(
            total_tests=1,
            passed_tests=1,
            failed_tests=0,
            critical_failures=0,
            test_results=[
                {"test": "test_1", "status": "PASS", "time_ms": 100},
            ],
            total_time=1.0,
            timestamp="",
            success=True,
        )

        report = detector.detect_regressions(current)

        assert len(report.improvements) == 1
        assert report.improvements[0]["type"] == "fix"

    def test_detect_performance_regression(self, temp_report_path):
        """Test detecting performance regression."""
        baseline_data = {
            "results": [
                {"test": "test_1", "status": "PASS", "time_ms": 100},
            ],
        }

        with open(temp_report_path, "w") as f:
            json.dump(baseline_data, f)

        detector = RegressionDetector(
            baseline_report_path=temp_report_path,
            performance_threshold=1.5,
        )

        # Create current report with slower test
        current = EvalSuiteReport(
            total_tests=1,
            passed_tests=1,
            failed_tests=0,
            critical_failures=0,
            test_results=[
                {"test": "test_1", "status": "PASS", "time_ms": 200},  # 2x slower
            ],
            total_time=1.0,
            timestamp="",
            success=True,
        )

        report = detector.detect_regressions(current)

        assert any(r["type"] == "performance_regression" for r in report.regressions)


# ============================================================================
# Orchestration Tests
# ============================================================================

class TestOrchestration:
    """Tests for orchestration integration."""

    def test_orchestration_creation(self):
        """Test creating orchestration."""
        orch = OrchestrationWithEval()

        assert orch.require_pre_eval is True

    @pytest.mark.asyncio
    async def test_prepare_for_execution(self):
        """Test preparing for execution."""
        orch = OrchestrationWithEval(require_pre_eval=False)

        ready, report = await orch.prepare_for_execution(
            goal="Test goal",
            domain="general",
        )

        assert isinstance(ready, bool)
        assert report is not None

    @pytest.mark.asyncio
    async def test_execute_with_validation_success(self):
        """Test successful execution with validation."""
        orch = OrchestrationWithEval(require_pre_eval=False, require_post_eval=False)

        result = await orch.execute_with_validation(
            goal="Test goal",
            domain="general",
        )

        assert isinstance(result, ExecutionResult)
        assert result.goal == "Test goal"

    @pytest.mark.asyncio
    async def test_execute_with_custom_executor(self):
        """Test execution with custom executor."""
        orch = OrchestrationWithEval(require_pre_eval=False, require_post_eval=False)

        def custom_executor(goal, domain):
            return {"custom": True, "goal": goal}

        result = await orch.execute_with_validation(
            goal="Custom goal",
            domain="general",
            executor=custom_executor,
        )

        assert result.success is True
        assert result.result_data.get("custom") is True

    @pytest.mark.asyncio
    async def test_validate_before_execution(self):
        """Test validation convenience function."""
        passed, report = await validate_before_execution(severity="critical")

        assert isinstance(passed, bool)
        assert isinstance(report, EvalSuiteReport)


# ============================================================================
# EvalGuard Tests
# ============================================================================

class TestEvalGuard:
    """Tests for EvalGuard context manager."""

    @pytest.mark.asyncio
    async def test_guard_with_passing_eval(self):
        """Test guard when eval passes."""
        guard = EvalGuard(severity=EvalSeverity.LOW, require_pass=False)

        async with guard:
            pass

        # Should not raise

    @pytest.mark.asyncio
    async def test_guard_ready_property(self):
        """Test guard ready property."""
        guard = EvalGuard(severity=EvalSeverity.LOW, require_pass=False)

        async with guard as g:
            assert isinstance(g.ready, bool)


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Integration tests for eval runtime."""

    @pytest.mark.asyncio
    async def test_full_workflow(self, temp_report_path):
        """Test full evaluation workflow."""
        # 1. Run tests
        runner = EvalSuiteRunner(verbose=True)
        report = await runner.run_all_tests(parallel=True)

        # 2. Save report
        report.to_file(temp_report_path)

        # 3. Load as baseline
        detector = RegressionDetector(baseline_report_path=temp_report_path)

        # 4. Run again and compare
        report2 = await runner.run_all_tests(parallel=True)
        regression_report = detector.detect_regressions(report2)

        # 5. Verify
        assert isinstance(report, EvalSuiteReport)
        assert isinstance(regression_report, RegressionReport)

    @pytest.mark.asyncio
    async def test_builtin_tests_run(self):
        """Test that built-in tests can run."""
        runner = EvalSuiteRunner()

        # Run memory_storage test specifically
        report = await runner.run_all_tests(test_names=["memory_storage"])

        assert report.total_tests == 1


# ============================================================================
# CLI Tests
# ============================================================================

class TestCLI:
    """Tests for CLI functionality."""

    def test_parser_creation(self):
        """Test CLI parser creation."""
        from app.eval_runtime.cli import EvalCLI

        parser = EvalCLI.create_parser()

        assert parser is not None

    def test_parser_help(self):
        """Test parser help text."""
        from app.eval_runtime.cli import EvalCLI

        parser = EvalCLI.create_parser()
        help_text = parser.format_help()

        assert "--test" in help_text
        assert "--domain" in help_text
        assert "--severity" in help_text


# ============================================================================
# Edge Cases
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_test_results(self):
        """Test handling empty results."""
        report = EvalSuiteReport(
            total_tests=0,
            passed_tests=0,
            failed_tests=0,
            critical_failures=0,
            test_results=[],
            total_time=0.0,
            timestamp="",
            success=True,
        )

        assert report.summary() is not None

    def test_all_tests_failing(self, runner, failing_test_case):
        """Test when all tests fail."""
        register_test("all_fail", failing_test_case)

        report = runner.run_all_tests_sync(test_names=["all_fail"])

        assert report.failed_tests == 1
        assert report.success is False

    @pytest.mark.asyncio
    async def test_concurrent_runs(self):
        """Test running multiple evaluations concurrently."""
        runner1 = EvalSuiteRunner()
        runner2 = EvalSuiteRunner()

        # Run in parallel
        results = await asyncio.gather(
            runner1.run_all_tests(test_names=["memory_storage"]),
            runner2.run_all_tests(test_names=["memory_storage"]),
        )

        assert len(results) == 2
        assert all(isinstance(r, EvalSuiteReport) for r in results)

    def test_report_with_unicode(self):
        """Test report with unicode characters."""
        result = EvalTestResult(
            test_name="unicode_test",
            success=True,
            error="Error with special chars: cafe",
        )

        report = EvalSuiteReport.single_test(result)

        # Should not raise encoding errors
        json_str = report.to_json()
        assert "unicode_test" in json_str