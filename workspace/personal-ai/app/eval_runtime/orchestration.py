"""Orchestration Integration for Evaluation.

Provides pre/post execution validation through evaluation tests.

Usage:
    from app.eval_runtime.orchestration import OrchestrationWithEval

    orchestration = OrchestrationWithEval()

    # Prepare for execution with validation
    ready = await orchestration.prepare_for_execution(
        goal="Create Houdini SOP chain",
        domain="houdini",
        require_eval_pass=True
    )

    # Execute with validation
    result = await orchestration.execute_with_validation(
        goal="Create noise terrain",
        domain="houdini"
    )
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, Optional

from app.eval_runtime.models import EvalDomain, EvalSeverity, EvalSuiteReport
from app.eval_runtime.runner import EvalSuiteRunner


@dataclass
class ExecutionResult:
    """Result of an orchestrated execution."""

    success: bool
    goal: str
    domain: str
    result_data: Optional[Dict[str, Any]] = None
    reason: str = ""
    pre_eval_report: Optional[EvalSuiteReport] = None
    post_eval_report: Optional[EvalSuiteReport] = None
    execution_time: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "goal": self.goal,
            "domain": self.domain,
            "reason": self.reason,
            "execution_time": self.execution_time,
            "timestamp": self.timestamp,
            "pre_eval_passed": self.pre_eval_report.success if self.pre_eval_report else None,
            "post_eval_passed": self.post_eval_report.success if self.post_eval_report else None,
        }


class OrchestrationWithEval:
    """Orchestration pipeline with pre/post execution validation.

    Integrates evaluation into the execution workflow:
    1. Pre-execution: Validate system is ready
    2. Execution: Run the goal
    3. Post-execution: Validate results

    Features:
    - Configurable validation requirements
    - Graceful degradation when eval fails
    - Detailed reporting
    """

    def __init__(
        self,
        require_pre_eval: bool = True,
        require_post_eval: bool = False,
        eval_severity: EvalSeverity = EvalSeverity.CRITICAL,
        on_validation_failure: Optional[Callable[[EvalSuiteReport], None]] = None,
    ) -> None:
        """Initialize orchestration with eval.

        Args:
            require_pre_eval: Block execution if pre-eval fails
            require_post_eval: Block success if post-eval fails
            eval_severity: Minimum severity to test
            on_validation_failure: Callback for validation failures
        """
        self.require_pre_eval = require_pre_eval
        self.require_post_eval = require_post_eval
        self.eval_severity = eval_severity
        self.on_validation_failure = on_validation_failure

        self.eval_runner = EvalSuiteRunner(verbose=True)

    async def prepare_for_execution(
        self,
        goal: str,
        domain: str,
        require_eval_pass: Optional[bool] = None,
    ) -> tuple[bool, Optional[EvalSuiteReport]]:
        """Prepare for execution: validate system is ready.

        Args:
            goal: Goal to execute
            domain: Execution domain
            require_eval_pass: Override require_pre_eval setting

        Returns:
            Tuple of (is_ready, eval_report)
        """
        print(f"[ORCHESTRATION] Preparing for execution: {goal}")

        # Determine if eval is required
        require_eval = require_eval_pass if require_eval_pass is not None else self.require_pre_eval

        # Run pre-execution eval
        print("[ORCHESTRATION] Running pre-execution validation...")

        domain_enum = self._get_domain_enum(domain)

        report = await self.eval_runner.run_all_tests(
            domain=domain_enum,
            severity=self.eval_severity,
            parallel=True,
        )

        print(report.summary())

        if not report.success:
            print("[ORCHESTRATION] Pre-execution validation FAILED")

            if self.on_validation_failure:
                self.on_validation_failure(report)

            if require_eval:
                print("[ORCHESTRATION] Blocking execution (validation required)")
                return False, report
            else:
                print("[ORCHESTRATION] Proceeding despite failures (validation not required)")
        else:
            print("[ORCHESTRATION] Pre-execution validation PASSED")

        return True, report

    async def execute_with_validation(
        self,
        goal: str,
        domain: str,
        executor: Optional[Callable[[str, str], Any]] = None,
    ) -> ExecutionResult:
        """Execute goal with built-in validation.

        Args:
            goal: Goal to execute
            domain: Execution domain
            executor: Optional custom executor function

        Returns:
            ExecutionResult with validation reports
        """
        import time

        start_time = time.time()

        # Pre-execution validation
        ready, pre_report = await self.prepare_for_execution(goal, domain)

        if not ready:
            return ExecutionResult(
                success=False,
                goal=goal,
                domain=domain,
                reason="Pre-execution validation failed",
                pre_eval_report=pre_report,
                execution_time=time.time() - start_time,
            )

        # Execute
        print(f"[ORCHESTRATION] Executing: {goal}")

        result_data = None
        execution_error = None

        try:
            if executor:
                # Use custom executor
                if asyncio.iscoroutinefunction(executor):
                    result_data = await executor(goal, domain)
                else:
                    result_data = executor(goal, domain)
            else:
                # Default mock execution
                result_data = {"executed": True, "goal": goal}

            print("[ORCHESTRATION] Execution completed")

        except Exception as e:
            execution_error = str(e)
            print(f"[ORCHESTRATION] Execution failed: {e}")

        # Post-execution validation
        print("[ORCHESTRATION] Running post-execution validation...")

        post_report = await self.eval_runner.run_all_tests(
            domain=self._get_domain_enum(domain),
            parallel=True,
        )

        if post_report.success:
            print("[ORCHESTRATION] Post-execution validation PASSED")
        else:
            print("[ORCHESTRATION] Post-execution validation FAILED")

            if self.on_validation_failure:
                self.on_validation_failure(post_report)

        # Determine final success
        success = execution_error is None
        if self.require_post_eval and not post_report.success:
            success = False

        return ExecutionResult(
            success=success,
            goal=goal,
            domain=domain,
            result_data=result_data,
            reason=execution_error or ("Post-eval failed" if not post_report.success and self.require_post_eval else ""),
            pre_eval_report=pre_report,
            post_eval_report=post_report,
            execution_time=time.time() - start_time,
        )

    def _get_domain_enum(self, domain: str) -> Optional[EvalDomain]:
        """Convert domain string to enum.

        Args:
            domain: Domain string

        Returns:
            EvalDomain or None
        """
        domain_map = {
            "touchdesigner": EvalDomain.TOUCHDESIGNER,
            "td": EvalDomain.TOUCHDESIGNER,
            "houdini": EvalDomain.HOUDINI,
            "ho": EvalDomain.HOUDINI,
            "vfx": EvalDomain.VFX,
            "general": EvalDomain.GENERAL,
        }
        return domain_map.get(domain.lower())


class EvalGuard:
    """Context manager for evaluation-guarded execution.

    Usage:
        async with EvalGuard(domain="houdini") as guard:
            if guard.ready:
                # Execute
                ...
            else:
                # Handle validation failure
                print(guard.report.summary())
    """

    def __init__(
        self,
        domain: str = "",
        severity: EvalSeverity = EvalSeverity.CRITICAL,
        require_pass: bool = True,
    ) -> None:
        """Initialize the guard.

        Args:
            domain: Domain for eval
            severity: Minimum severity
            require_pass: Block if eval fails
        """
        self.domain = domain
        self.severity = severity
        self.require_pass = require_pass

        self.runner = EvalSuiteRunner()
        self.report: Optional[EvalSuiteReport] = None
        self.ready = False

    async def __aenter__(self) -> "EvalGuard":
        """Enter context with pre-execution validation."""
        domain_enum = self._get_domain_enum(self.domain)

        self.report = await self.runner.run_all_tests(
            domain=domain_enum,
            severity=self.severity,
            parallel=True,
        )

        self.ready = self.report.success or not self.require_pass

        if not self.report.success:
            print(self.report.summary())

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context."""
        pass

    def _get_domain_enum(self, domain: str) -> Optional[EvalDomain]:
        """Convert domain string to enum."""
        domain_map = {
            "touchdesigner": EvalDomain.TOUCHDESIGNER,
            "houdini": EvalDomain.HOUDINI,
            "vfx": EvalDomain.VFX,
            "general": EvalDomain.GENERAL,
        }
        return domain_map.get(domain.lower())


# Convenience functions


async def validate_before_execution(
    domain: str = "",
    severity: str = "critical",
) -> tuple[bool, EvalSuiteReport]:
    """Validate system before execution.

    Args:
        domain: Optional domain filter
        severity: Minimum severity (critical, high, medium, low)

    Returns:
        Tuple of (passed, report)
    """
    runner = EvalSuiteRunner()

    domain_enum = None
    if domain:
        domain_map = {
            "touchdesigner": EvalDomain.TOUCHDESIGNER,
            "houdini": EvalDomain.HOUDINI,
            "vfx": EvalDomain.VFX,
            "general": EvalDomain.GENERAL,
        }
        domain_enum = domain_map.get(domain.lower())

    severity_enum = EvalSeverity(severity)

    report = await runner.run_all_tests(
        domain=domain_enum,
        severity=severity_enum,
        parallel=True,
    )

    return report.success, report