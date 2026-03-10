"""Evaluation Runtime Models.

Core data structures for the evaluation test framework.

Key Components:
- EvalDomain: Supported evaluation domains
- EvalSeverity: Test severity/importance levels
- EvalTestCase: Single evaluation test definition
- EvalTestResult: Result of running a test
- EvalSuiteReport: Complete evaluation report
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


class EvalDomain(str, Enum):
    """Supported evaluation domains."""

    TOUCHDESIGNER = "touchdesigner"
    HOUDINI = "houdini"
    VFX = "vfx"
    GENERAL = "general"


class EvalSeverity(str, Enum):
    """Test severity/importance levels.

    Order matters for severity filtering: CRITICAL > HIGH > MEDIUM > LOW
    """

    CRITICAL = "critical"  # Must pass, blocks deployment
    HIGH = "high"  # Should pass, blocking
    MEDIUM = "medium"  # Nice to have
    LOW = "low"  # Informational

    @classmethod
    def severity_order(cls) -> List["EvalSeverity"]:
        """Get severity order from highest to lowest."""
        return [cls.CRITICAL, cls.HIGH, cls.MEDIUM, cls.LOW]

    def threshold_index(self) -> int:
        """Get index in severity order for comparison."""
        return self.severity_order().index(self)


@dataclass
class EvalTestResult:
    """Result of running a single test."""

    test_name: str
    success: bool
    output: Optional[Dict[str, Any]] = None
    execution_time: float = 0.0
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    domain: str = ""
    severity: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "test": self.test_name,
            "status": "PASS" if self.success else "FAIL",
            "time_ms": int(self.execution_time * 1000),
            "error": self.error,
            "timestamp": self.timestamp,
            "domain": self.domain,
            "severity": self.severity,
            "output": self.output,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EvalTestResult":
        """Create from dictionary."""
        return cls(
            test_name=data["test"],
            success=data["status"] == "PASS",
            output=data.get("output"),
            execution_time=data.get("time_ms", 0) / 1000,
            error=data.get("error"),
            timestamp=data.get("timestamp", ""),
            domain=data.get("domain", ""),
            severity=data.get("severity", ""),
        )


@dataclass
class EvalTestCase:
    """Single evaluation test definition.

    Contains test configuration, execution logic, and output validation.
    """

    name: str
    description: str
    domain: EvalDomain
    severity: EvalSeverity
    test_function: Callable
    timeout: float = 30.0
    expected_output: Optional[Dict[str, Any]] = None
    tags: List[str] = field(default_factory=list)

    async def run(self) -> EvalTestResult:
        """Run test and return result."""
        start_time = time.time()

        try:
            # Handle both sync and async functions
            if asyncio.iscoroutinefunction(self.test_function):
                result = await asyncio.wait_for(
                    self.test_function(),
                    timeout=self.timeout,
                )
            else:
                # Run sync function in executor
                result = await asyncio.get_event_loop().run_in_executor(
                    None,
                    self.test_function,
                )

            execution_time = time.time() - start_time

            # Validate output if expected provided
            success = True
            if self.expected_output:
                success = self._validate_output(result, self.expected_output)
            else:
                # Default success check
                if isinstance(result, dict):
                    success = result.get("success", False)
                else:
                    success = bool(result)

            return EvalTestResult(
                test_name=self.name,
                success=success,
                output=result if isinstance(result, dict) else {"value": result},
                execution_time=execution_time,
                error=None,
                domain=self.domain.value,
                severity=self.severity.value,
            )

        except asyncio.TimeoutError:
            execution_time = time.time() - start_time
            return EvalTestResult(
                test_name=self.name,
                success=False,
                output=None,
                execution_time=execution_time,
                error=f"Timeout after {self.timeout}s",
                domain=self.domain.value,
                severity=self.severity.value,
            )

        except Exception as e:
            execution_time = time.time() - start_time
            return EvalTestResult(
                test_name=self.name,
                success=False,
                output=None,
                execution_time=execution_time,
                error=str(e),
                domain=self.domain.value,
                severity=self.severity.value,
            )

    def run_sync(self) -> EvalTestResult:
        """Run test synchronously (for non-async contexts)."""
        start_time = time.time()

        try:
            result = self.test_function()
            execution_time = time.time() - start_time

            # Validate output
            success = True
            if self.expected_output:
                success = self._validate_output(result, self.expected_output)
            elif isinstance(result, dict):
                success = result.get("success", False)
            else:
                success = bool(result)

            return EvalTestResult(
                test_name=self.name,
                success=success,
                output=result if isinstance(result, dict) else {"value": result},
                execution_time=execution_time,
                error=None,
                domain=self.domain.value,
                severity=self.severity.value,
            )

        except Exception as e:
            execution_time = time.time() - start_time
            return EvalTestResult(
                test_name=self.name,
                success=False,
                output=None,
                execution_time=execution_time,
                error=str(e),
                domain=self.domain.value,
                severity=self.severity.value,
            )

    def _validate_output(self, actual: Any, expected: Dict[str, Any]) -> bool:
        """Validate test output against expectations.

        Args:
            actual: Actual output from test
            expected: Expected output with optional callable validators

        Returns:
            True if validation passes
        """
        if not isinstance(actual, dict):
            return False

        for key, expected_value in expected.items():
            if key not in actual:
                return False

            actual_value = actual[key]

            if callable(expected_value):
                # Use callable as validator
                try:
                    if not expected_value(actual_value):
                        return False
                except Exception:
                    return False
            else:
                # Direct comparison
                if actual_value != expected_value:
                    return False

        return True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (for serialization, excludes function)."""
        return {
            "name": self.name,
            "description": self.description,
            "domain": self.domain.value,
            "severity": self.severity.value,
            "timeout": self.timeout,
            "expected_output": str(self.expected_output) if self.expected_output else None,
            "tags": self.tags,
        }


@dataclass
class EvalSuiteReport:
    """Complete evaluation report for a test suite run."""

    total_tests: int
    passed_tests: int
    failed_tests: int
    critical_failures: int
    test_results: List[Dict[str, Any]]
    total_time: float
    timestamp: str
    success: bool

    def summary(self) -> str:
        """Human-readable summary."""
        status_icon = "PASS" if self.success else "FAIL"
        status_emoji = "OK" if self.success else "!!"

        lines = [
            "",
            "=" * 55,
            "           EVALUATION REPORT",
            "=" * 55,
            f"  Total Tests:         {self.total_tests:3d}",
            f"  Passed:              {self.passed_tests:3d}  OK",
            f"  Failed:              {self.failed_tests:3d}  {'!!' if self.failed_tests else '  '}",
            f"  Critical Failures:   {self.critical_failures:3d}",
            f"  Total Time:          {self.total_time:5.1f}s",
            f"  Status:              {status_icon}",
            "=" * 55,
            "",
        ]

        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "summary": {
                "total": self.total_tests,
                "passed": self.passed_tests,
                "failed": self.failed_tests,
                "critical_failures": self.critical_failures,
                "success": self.success,
                "total_time_seconds": self.total_time,
            },
            "timestamp": self.timestamp,
            "results": self.test_results,
        }

    def to_json(self) -> str:
        """Export as JSON string."""
        import json

        return json.dumps(self.to_dict(), indent=2)

    def to_file(self, filepath: str) -> bool:
        """Save report to file.

        Args:
            filepath: Path to save report

        Returns:
            True if saved successfully
        """
        try:
            path = Path(filepath)
            path.parent.mkdir(parents=True, exist_ok=True)

            with open(path, "w", encoding="utf-8") as f:
                f.write(self.to_json())

            print(f"[EVAL] Report saved: {filepath}")
            return True
        except (IOError, OSError) as e:
            print(f"[EVAL] Failed to save report: {e}")
            return False

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EvalSuiteReport":
        """Create from dictionary."""
        summary = data.get("summary", {})
        return cls(
            total_tests=summary.get("total", 0),
            passed_tests=summary.get("passed", 0),
            failed_tests=summary.get("failed", 0),
            critical_failures=summary.get("critical_failures", 0),
            test_results=data.get("results", []),
            total_time=summary.get("total_time_seconds", 0.0),
            timestamp=data.get("timestamp", ""),
            success=summary.get("success", False),
        )

    @classmethod
    def from_file(cls, filepath: str) -> Optional["EvalSuiteReport"]:
        """Load report from file.

        Args:
            filepath: Path to load report from

        Returns:
            EvalSuiteReport or None if loading fails
        """
        try:
            import json

            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            return cls.from_dict(data)
        except (IOError, OSError, json.JSONDecodeError) as e:
            print(f"[EVAL] Failed to load report: {e}")
            return None

    @classmethod
    def empty(cls) -> "EvalSuiteReport":
        """Create an empty report."""
        return cls(
            total_tests=0,
            passed_tests=0,
            failed_tests=0,
            critical_failures=0,
            test_results=[],
            total_time=0.0,
            timestamp=datetime.now().isoformat(),
            success=True,
        )

    @classmethod
    def single_test(cls, result: EvalTestResult) -> "EvalSuiteReport":
        """Create a report from a single test result."""
        return cls(
            total_tests=1,
            passed_tests=1 if result.success else 0,
            failed_tests=0 if result.success else 1,
            critical_failures=0,
            test_results=[result.to_dict()],
            total_time=result.execution_time,
            timestamp=result.timestamp,
            success=result.success,
        )


@dataclass
class RegressionReport:
    """Report on detected regressions between eval runs."""

    regressions: List[Dict[str, Any]]
    improvements: List[Dict[str, Any]]
    has_critical_regressions: bool

    def summary(self) -> str:
        """Human-readable summary."""
        lines = ["", "REGRESSION ANALYSIS:"]

        if self.regressions:
            lines.append(f"  [X] {len(self.regressions)} regressions detected:")
            for r in self.regressions:
                lines.append(f"      - {r['test']}: {r['type']}")
                if "error" in r and r["error"]:
                    lines.append(f"        Error: {r['error']}")
                if "slowdown" in r:
                    lines.append(f"        Slowdown: {r['slowdown']}")

        if self.improvements:
            lines.append(f"  [OK] {len(self.improvements)} improvements:")
            for i in self.improvements:
                lines.append(f"      - {i['test']}: fixed")

        if not self.regressions and not self.improvements:
            lines.append("  [OK] No regressions or improvements detected")

        lines.append("")
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "has_critical_regressions": self.has_critical_regressions,
            "regression_count": len(self.regressions),
            "improvement_count": len(self.improvements),
            "regressions": self.regressions,
            "improvements": self.improvements,
        }