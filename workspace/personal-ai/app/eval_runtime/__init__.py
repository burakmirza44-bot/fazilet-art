"""Evaluation Runtime Module.

Provides a comprehensive evaluation framework for testing and validating
the personal-ai system before and during execution.

Key Components:
- EvalDomain: Supported evaluation domains (TouchDesigner, Houdini, VFX, General)
- EvalSeverity: Test importance levels (Critical, High, Medium, Low)
- EvalTestCase: Single test definition with execution logic
- EvalTestResult: Result of running a test
- EvalSuiteReport: Complete evaluation report
- EvalSuiteRunner: Execute tests and generate reports
- RegressionDetector: Compare results against baselines
- OrchestrationWithEval: Pre/post execution validation

Usage:
    # CLI
    python -m app.eval_runtime --test td_help
    python -m app.eval_runtime --severity critical

    # Programmatic
    from app.eval_runtime import EvalSuiteRunner, EvalDomain

    runner = EvalSuiteRunner()
    report = await runner.run_all_tests(domain=EvalDomain.HOUDINI)
    print(report.summary())

    # Orchestration
    from app.eval_runtime import OrchestrationWithEval

    orchestration = OrchestrationWithEval()
    result = await orchestration.execute_with_validation(
        goal="Create noise terrain",
        domain="houdini"
    )
"""

from app.eval_runtime.models import (
    EvalDomain,
    EvalSeverity,
    EvalSuiteReport,
    EvalTestCase,
    EvalTestResult,
    RegressionReport,
)
from app.eval_runtime.registry import (
    EVAL_TESTS,
    get_test,
    list_test_names,
    list_tests,
    register_test,
)
from app.eval_runtime.runner import (
    EvalSuiteRunner,
    run_full_suite,
    run_quick_check,
)
from app.eval_runtime.regression import (
    RegressionDetector,
    create_baseline,
)
from app.eval_runtime.orchestration import (
    EvalGuard,
    ExecutionResult,
    OrchestrationWithEval,
    validate_before_execution,
)

__all__ = [
    # Models
    "EvalDomain",
    "EvalSeverity",
    "EvalTestCase",
    "EvalTestResult",
    "EvalSuiteReport",
    "RegressionReport",
    # Registry
    "EVAL_TESTS",
    "register_test",
    "get_test",
    "list_tests",
    "list_test_names",
    # Runner
    "EvalSuiteRunner",
    "run_full_suite",
    "run_quick_check",
    # Regression
    "RegressionDetector",
    "create_baseline",
    # Orchestration
    "OrchestrationWithEval",
    "EvalGuard",
    "ExecutionResult",
    "validate_before_execution",
]

__version__ = "1.0.0"