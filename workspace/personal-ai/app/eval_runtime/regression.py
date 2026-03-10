"""Regression Detection Module.

Detects performance and behavior regressions between evaluation runs.

Usage:
    from app.eval_runtime.regression import RegressionDetector

    detector = RegressionDetector("data/eval_reports/baseline.json")
    report = detector.detect_regressions(current_report)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.eval_runtime.models import EvalSuiteReport, RegressionReport


class RegressionDetector:
    """Detect regressions between eval runs.

    Compares current evaluation results against a baseline to identify:
    - Test failures that were previously passing
    - Performance degradation
    - Tests that were fixed (improvements)
    """

    def __init__(
        self,
        baseline_report_path: Optional[str] = None,
        performance_threshold: float = 1.5,  # 50% slower = regression
    ) -> None:
        """Initialize the detector.

        Args:
            baseline_report_path: Path to baseline report JSON
            performance_threshold: Multiplier for performance regression (default 1.5 = 50% slower)
        """
        self.baseline: Optional[Dict[str, Any]] = None
        self.performance_threshold = performance_threshold

        if baseline_report_path:
            self.load_baseline(baseline_report_path)

    def load_baseline(self, path: str) -> bool:
        """Load baseline report from file.

        Args:
            path: Path to baseline JSON file

        Returns:
            True if loaded successfully
        """
        try:
            with open(path, "r", encoding="utf-8") as f:
                self.baseline = json.load(f)
            return True
        except (IOError, json.JSONDecodeError) as e:
            print(f"[REGRESSION] Failed to load baseline: {e}")
            return False

    def set_baseline(self, report: EvalSuiteReport) -> None:
        """Set baseline from a report object.

        Args:
            report: Report to use as baseline
        """
        self.baseline = report.to_dict()

    def save_baseline(self, path: str) -> bool:
        """Save current baseline to file.

        Args:
            path: Path to save baseline

        Returns:
            True if saved successfully
        """
        if not self.baseline:
            return False

        try:
            path_obj = Path(path)
            path_obj.parent.mkdir(parents=True, exist_ok=True)

            with open(path_obj, "w", encoding="utf-8") as f:
                json.dump(self.baseline, f, indent=2)

            print(f"[REGRESSION] Baseline saved: {path}")
            return True
        except IOError as e:
            print(f"[REGRESSION] Failed to save baseline: {e}")
            return False

    def detect_regressions(
        self,
        current_report: EvalSuiteReport,
    ) -> RegressionReport:
        """Detect regressions between current and baseline.

        Args:
            current_report: Current evaluation results

        Returns:
            RegressionReport with detected issues
        """
        if not self.baseline:
            return RegressionReport(
                regressions=[],
                improvements=[],
                has_critical_regressions=False,
            )

        regressions: List[Dict[str, Any]] = []
        improvements: List[Dict[str, Any]] = []

        baseline_results = {r["test"]: r for r in self.baseline.get("results", [])}

        for current_result in current_report.test_results:
            test_name = current_result.get("test", "")
            baseline_result = baseline_results.get(test_name)

            if not baseline_result:
                # New test, not in baseline
                continue

            # Check pass/fail status
            baseline_passed = baseline_result.get("status") == "PASS"
            current_passed = current_result.get("status") == "PASS"

            if baseline_passed and not current_passed:
                # Regression: test that passed now fails
                regressions.append({
                    "test": test_name,
                    "type": "failure_regression",
                    "baseline": "PASS",
                    "current": "FAIL",
                    "error": current_result.get("error"),
                    "domain": current_result.get("domain"),
                    "severity": current_result.get("severity"),
                })

            elif not baseline_passed and current_passed:
                # Improvement: test that failed now passes
                improvements.append({
                    "test": test_name,
                    "type": "fix",
                    "baseline": "FAIL",
                    "current": "PASS",
                })

            # Check performance regression (only for passing tests)
            if baseline_passed and current_passed:
                baseline_time = baseline_result.get("time_ms", 0)
                current_time = current_result.get("time_ms", 0)

                if baseline_time > 0 and current_time > baseline_time * self.performance_threshold:
                    slowdown_pct = (current_time / baseline_time - 1) * 100
                    regressions.append({
                        "test": test_name,
                        "type": "performance_regression",
                        "baseline_ms": baseline_time,
                        "current_ms": current_time,
                        "slowdown": f"{slowdown_pct:.0f}%",
                        "threshold_used": f"{self.performance_threshold}x",
                    })

        # Check for removed tests (tests in baseline but not in current)
        current_tests = {r.get("test") for r in current_report.test_results}
        for baseline_test in baseline_results:
            if baseline_test not in current_tests:
                regressions.append({
                    "test": baseline_test,
                    "type": "test_removed",
                    "baseline": baseline_results[baseline_test].get("status"),
                    "current": "MISSING",
                })

        has_critical = any(
            r.get("type") in ("failure_regression", "test_removed")
            and r.get("severity") == "critical"
            for r in regressions
        )

        return RegressionReport(
            regressions=regressions,
            improvements=improvements,
            has_critical_regressions=has_critical,
        )

    def compare_summaries(
        self,
        current_report: EvalSuiteReport,
    ) -> Dict[str, Any]:
        """Compare summary statistics between baseline and current.

        Args:
            current_report: Current evaluation results

        Returns:
            Dictionary with comparison data
        """
        if not self.baseline:
            return {
                "baseline_available": False,
                "comparison": None,
            }

        baseline_summary = self.baseline.get("summary", {})
        current_summary = current_report.to_dict().get("summary", {})

        return {
            "baseline_available": True,
            "comparison": {
                "total_tests": {
                    "baseline": baseline_summary.get("total", 0),
                    "current": current_summary.get("total", 0),
                    "change": current_summary.get("total", 0) - baseline_summary.get("total", 0),
                },
                "passed_tests": {
                    "baseline": baseline_summary.get("passed", 0),
                    "current": current_summary.get("passed", 0),
                    "change": current_summary.get("passed", 0) - baseline_summary.get("passed", 0),
                },
                "failed_tests": {
                    "baseline": baseline_summary.get("failed", 0),
                    "current": current_summary.get("failed", 0),
                    "change": current_summary.get("failed", 0) - baseline_summary.get("failed", 0),
                },
                "total_time": {
                    "baseline": baseline_summary.get("total_time_seconds", 0),
                    "current": current_summary.get("total_time_seconds", 0),
                },
            },
        }


def create_baseline(
    report: EvalSuiteReport,
    path: str = "data/eval_reports/baseline.json",
) -> bool:
    """Create a baseline file from a report.

    Args:
        report: Report to use as baseline
        path: Path to save baseline

    Returns:
        True if saved successfully
    """
    detector = RegressionDetector()
    detector.set_baseline(report)
    return detector.save_baseline(path)