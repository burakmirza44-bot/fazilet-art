"""Evaluation Suite Runner.

Runs evaluation test suites and generates reports.

Usage:
    from app.eval_runtime.runner import EvalSuiteRunner

    runner = EvalSuiteRunner()

    # Run all tests
    report = await runner.run_all_tests()

    # Run tests for specific domain
    report = await runner.run_all_tests(domain=EvalDomain.HOUDINI)

    # Run with severity filter
    report = await runner.run_all_tests(severity=EvalSeverity.CRITICAL)
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime
from typing import List, Optional, Set

from app.eval_runtime.models import (
    EvalDomain,
    EvalSeverity,
    EvalSuiteReport,
    EvalTestCase,
    EvalTestResult,
)
from app.eval_runtime.registry import EVAL_TESTS


class EvalSuiteRunner:
    """Run evaluation test suites and generate reports.

    Features:
    - Parallel and sequential execution
    - Domain and severity filtering
    - Progress reporting
    - Comprehensive report generation
    """

    def __init__(self, verbose: bool = False) -> None:
        """Initialize the runner.

        Args:
            verbose: Enable verbose output
        """
        self.verbose = verbose
        self.results: List[EvalTestResult] = []
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None

    async def run_all_tests(
        self,
        domain: Optional[EvalDomain] = None,
        severity: Optional[EvalSeverity] = None,
        test_names: Optional[List[str]] = None,
        parallel: bool = True,
    ) -> EvalSuiteReport:
        """Run tests, optionally filtered by domain/severity.

        Args:
            domain: Filter by domain
            severity: Filter by minimum severity
            test_names: Specific test names to run
            parallel: Run tests in parallel (default: True)

        Returns:
            EvalSuiteReport with results
        """
        self.results = []
        self.start_time = time.time()

        # Filter tests
        tests_to_run = self._filter_tests(domain, severity, test_names)

        if self.verbose:
            print(f"[EVAL] Running {len(tests_to_run)} tests...")

        if not tests_to_run:
            self.end_time = time.time()
            return EvalSuiteReport.empty()

        if parallel:
            # Run tests in parallel
            tasks = [test.run() for test in tests_to_run]
            self.results = await asyncio.gather(*tasks)
        else:
            # Run tests sequentially
            for test in tests_to_run:
                result = await test.run()
                self.results.append(result)

                if self.verbose:
                    status = "OK" if result.success else "FAIL"
                    print(f"[EVAL] {test.name}: [{status}] ({result.execution_time:.2f}s)")

        self.end_time = time.time()

        return self._generate_report(tests_to_run)

    def run_all_tests_sync(
        self,
        domain: Optional[EvalDomain] = None,
        severity: Optional[EvalSeverity] = None,
        test_names: Optional[List[str]] = None,
    ) -> EvalSuiteReport:
        """Run tests synchronously (for non-async contexts).

        Args:
            domain: Filter by domain
            severity: Filter by minimum severity
            test_names: Specific test names to run

        Returns:
            EvalSuiteReport with results
        """
        self.results = []
        self.start_time = time.time()

        # Filter tests
        tests_to_run = self._filter_tests(domain, severity, test_names)

        if self.verbose:
            print(f"[EVAL] Running {len(tests_to_run)} tests...")

        if not tests_to_run:
            self.end_time = time.time()
            return EvalSuiteReport.empty()

        # Run tests sequentially
        for test in tests_to_run:
            result = test.run_sync()
            self.results.append(result)

            if self.verbose:
                status = "OK" if result.success else "FAIL"
                print(f"[EVAL] {test.name}: [{status}] ({result.execution_time:.2f}s)")

        self.end_time = time.time()

        return self._generate_report(tests_to_run)

    async def run_single_test(self, test_name: str) -> EvalSuiteReport:
        """Run a single test by name.

        Args:
            test_name: Name of test to run

        Returns:
            EvalSuiteReport with single test result

        Raises:
            KeyError: If test not found
        """
        if test_name not in EVAL_TESTS:
            raise KeyError(f"Test not found: {test_name}")

        test = EVAL_TESTS[test_name]
        result = await test.run()

        return EvalSuiteReport.single_test(result)

    def _filter_tests(
        self,
        domain: Optional[EvalDomain] = None,
        severity: Optional[EvalSeverity] = None,
        test_names: Optional[List[str]] = None,
    ) -> List[EvalTestCase]:
        """Filter tests by various criteria.

        Args:
            domain: Filter by domain
            severity: Filter by minimum severity
            test_names: Specific test names to include

        Returns:
            List of filtered test cases
        """
        if test_names:
            # Use specific test names
            tests = []
            for name in test_names:
                if name in EVAL_TESTS:
                    tests.append(EVAL_TESTS[name])
            return tests

        tests = list(EVAL_TESTS.values())

        if domain:
            tests = [t for t in tests if t.domain == domain]

        if severity:
            # Return tests with severity >= requested
            severity_order = EvalSeverity.severity_order()
            threshold_idx = severity.threshold_index()
            tests = [t for t in tests if severity_order.index(t.severity) <= threshold_idx]

        return tests

    def _generate_report(
        self,
        tests_run: List[EvalTestCase],
    ) -> EvalSuiteReport:
        """Generate comprehensive report.

        Args:
            tests_run: Tests that were executed

        Returns:
            EvalSuiteReport with aggregated results
        """
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.success)
        failed_tests = total_tests - passed_tests

        # Count critical failures
        test_severity_map = {t.name: t.severity for t in tests_run}
        critical_failures = sum(
            1 for r in self.results
            if not r.success and test_severity_map.get(r.test_name) == EvalSeverity.CRITICAL
        )

        total_time = (self.end_time - self.start_time) if self.end_time and self.start_time else 0.0

        return EvalSuiteReport(
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            critical_failures=critical_failures,
            test_results=[r.to_dict() for r in self.results],
            total_time=total_time,
            timestamp=datetime.now().isoformat(),
            success=failed_tests == 0,
        )

    def get_results_by_domain(self) -> dict:
        """Get results grouped by domain.

        Returns:
            Dictionary mapping domain to results
        """
        by_domain: dict = {}
        for result in self.results:
            domain = result.domain or "unknown"
            if domain not in by_domain:
                by_domain[domain] = []
            by_domain[domain].append(result)
        return by_domain

    def get_results_by_severity(self) -> dict:
        """Get results grouped by severity.

        Returns:
            Dictionary mapping severity to results
        """
        by_severity: dict = {}
        for result in self.results:
            severity = result.severity or "unknown"
            if severity not in by_severity:
                by_severity[severity] = []
            by_severity[severity].append(result)
        return by_severity


def run_quick_check() -> EvalSuiteReport:
    """Run a quick health check (critical tests only).

    Returns:
        EvalSuiteReport with critical test results
    """
    runner = EvalSuiteRunner()
    return runner.run_all_tests_sync(severity=EvalSeverity.CRITICAL)


async def run_full_suite() -> EvalSuiteReport:
    """Run the full evaluation suite.

    Returns:
        EvalSuiteReport with all test results
    """
    runner = EvalSuiteRunner(verbose=True)
    return await runner.run_all_tests(parallel=True)