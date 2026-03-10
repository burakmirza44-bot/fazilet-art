"""Evaluation Test Registry.

Central registry for all evaluation tests.

Usage:
    from app.eval_runtime.registry import EVAL_TESTS, register_test

    # Get a test by name
    test = EVAL_TESTS["td_help"]

    # Register a custom test
    register_test("my_test", EvalTestCase(...))
"""

from __future__ import annotations

from typing import Dict, List, Optional

from app.eval_runtime.models import EvalDomain, EvalSeverity, EvalTestCase
from app.eval_runtime.test_functions import (
    evaluate_houdini_bridge_connection,
    evaluate_houdini_help,
    evaluate_td_bridge_connection,
    evaluate_td_help,
    test_goal_generator,
    test_memory_storage,
    test_output_evaluator,
    test_rag_retrieval,
    test_recipe_distillation,
    test_system_health,
)


# Global test registry
EVAL_TESTS: Dict[str, EvalTestCase] = {}


def register_test(name: str, test_case: EvalTestCase) -> None:
    """Register a test case.

    Args:
        name: Unique test name
        test_case: Test case to register
    """
    EVAL_TESTS[name] = test_case


def get_test(name: str) -> Optional[EvalTestCase]:
    """Get a test by name.

    Args:
        name: Test name

    Returns:
        EvalTestCase or None if not found
    """
    return EVAL_TESTS.get(name)


def list_tests(
    domain: Optional[EvalDomain] = None,
    severity: Optional[EvalSeverity] = None,
) -> List[EvalTestCase]:
    """List tests, optionally filtered.

    Args:
        domain: Filter by domain
        severity: Filter by minimum severity

    Returns:
        List of matching test cases
    """
    tests = list(EVAL_TESTS.values())

    if domain:
        tests = [t for t in tests if t.domain == domain]

    if severity:
        # Filter by severity threshold
        severity_order = EvalSeverity.severity_order()
        threshold_idx = severity.threshold_index()
        tests = [t for t in tests if severity_order.index(t.severity) <= threshold_idx]

    return tests


def list_test_names() -> List[str]:
    """Get all registered test names.

    Returns:
        List of test names
    """
    return list(EVAL_TESTS.keys())


# ============================================================================
# Default Test Registrations
# ============================================================================


def _register_default_tests() -> None:
    """Register default evaluation tests."""
    # TouchDesigner tests
    register_test(
        "td_help",
        EvalTestCase(
            name="TouchDesigner Help Integration",
            description="Verify TD help retrieval works",
            domain=EvalDomain.TOUCHDESIGNER,
            severity=EvalSeverity.HIGH,
            test_function=evaluate_td_help,
            timeout=10.0,
            expected_output={
                "success": True,
                "docs_found": lambda x: x > 0,
                "categories": lambda x: isinstance(x, list) and len(x) > 0,
            },
            tags=["touchdesigner", "help", "integration"],
        ),
    )

    register_test(
        "td_bridge",
        EvalTestCase(
            name="TouchDesigner Bridge Connection",
            description="Verify TD bridge is reachable",
            domain=EvalDomain.TOUCHDESIGNER,
            severity=EvalSeverity.CRITICAL,
            test_function=evaluate_td_bridge_connection,
            timeout=5.0,
            tags=["touchdesigner", "bridge", "connectivity"],
        ),
    )

    # Houdini tests
    register_test(
        "houdini_help",
        EvalTestCase(
            name="Houdini Help Integration",
            description="Verify Houdini help retrieval works",
            domain=EvalDomain.HOUDINI,
            severity=EvalSeverity.HIGH,
            test_function=evaluate_houdini_help,
            timeout=10.0,
            expected_output={
                "success": True,
                "nodes_found": lambda x: x > 0,
            },
            tags=["houdini", "help", "integration"],
        ),
    )

    register_test(
        "houdini_bridge",
        EvalTestCase(
            name="Houdini Bridge Connection",
            description="Verify Houdini bridge is reachable",
            domain=EvalDomain.HOUDINI,
            severity=EvalSeverity.CRITICAL,
            test_function=evaluate_houdini_bridge_connection,
            timeout=5.0,
            tags=["houdini", "bridge", "connectivity"],
        ),
    )

    # Recipe/Learning tests
    register_test(
        "recipe_distillation",
        EvalTestCase(
            name="Recipe Distillation",
            description="Test tutorial to recipe extraction",
            domain=EvalDomain.GENERAL,
            severity=EvalSeverity.MEDIUM,
            test_function=test_recipe_distillation,
            timeout=15.0,
            tags=["learning", "recipe", "distillation"],
        ),
    )

    register_test(
        "rag_retrieval",
        EvalTestCase(
            name="RAG Context Retrieval",
            description="Test RAG index retrieval",
            domain=EvalDomain.GENERAL,
            severity=EvalSeverity.MEDIUM,
            test_function=test_rag_retrieval,
            timeout=5.0,
            tags=["rag", "context", "retrieval"],
        ),
    )

    # System tests
    register_test(
        "memory_storage",
        EvalTestCase(
            name="Memory Storage",
            description="Test memory store functionality",
            domain=EvalDomain.GENERAL,
            severity=EvalSeverity.HIGH,
            test_function=test_memory_storage,
            timeout=5.0,
            tags=["memory", "storage", "persistence"],
        ),
    )

    register_test(
        "goal_generator",
        EvalTestCase(
            name="Goal Generator",
            description="Test goal generation functionality",
            domain=EvalDomain.GENERAL,
            severity=EvalSeverity.MEDIUM,
            test_function=test_goal_generator,
            timeout=5.0,
            tags=["goals", "generation", "planning"],
        ),
    )

    register_test(
        "output_evaluator",
        EvalTestCase(
            name="Output Evaluator",
            description="Test output evaluation functionality",
            domain=EvalDomain.GENERAL,
            severity=EvalSeverity.MEDIUM,
            test_function=test_output_evaluator,
            timeout=5.0,
            tags=["evaluation", "output", "quality"],
        ),
    )

    register_test(
        "system_health",
        EvalTestCase(
            name="System Health Check",
            description="Comprehensive system health check",
            domain=EvalDomain.GENERAL,
            severity=EvalSeverity.CRITICAL,
            test_function=test_system_health,
            timeout=30.0,
            tags=["system", "health", "comprehensive"],
        ),
    )


# Register defaults on module load
_register_default_tests()