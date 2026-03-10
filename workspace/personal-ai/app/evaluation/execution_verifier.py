"""Execution Verifier Module.

Provides unified post-execution verification combining visual and state query methods.
This is the main entry point for post-execution verification.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Any

from app.evaluation.state_verifier import StateQueryVerifier
from app.evaluation.verification_models import (
    ExecutionVerificationReport,
    ExpectedState,
    StateQueryVerificationResult,
    VisualVerificationResult,
)
from app.evaluation.visual_verifier import VisualVerifier


@dataclass
class VerifierConfig:
    """Configuration for execution verification."""

    enable_visual: bool = True
    """Enable visual (screenshot) verification."""

    enable_state_query: bool = True
    """Enable state query verification."""

    visual_confidence_weight: float = 0.5
    """Weight for visual verification in overall confidence (0.0-1.0)."""

    state_confidence_weight: float = 0.5
    """Weight for state verification in overall confidence (0.0-1.0)."""

    min_confidence_threshold: float = 0.6
    """Minimum confidence required for verification to pass."""

    require_both_methods: bool = False
    """If True, both visual and state must pass for overall success."""

    use_vlm: bool = True
    """Use VLM for visual analysis."""

    screenshot_delay: float = 1.0
    """Delay between action and screenshot (seconds)."""


class ExecutionVerifier:
    """Complete post-execution verification pipeline.

    Combines visual verification (screenshot comparison) and state query
    verification (direct application queries) for robust post-execution
    verification with evidence collection.

    Example:
        verifier = ExecutionVerifier()

        # Take screenshot before action
        before_screenshot = take_screenshot("before")

        # Execute action
        execute_action(action)

        # Wait for UI update
        time.sleep(1)

        # Take screenshot after action
        after_screenshot = take_screenshot("after")

        # Define expected state
        expected = ExpectedState(
            new_elements_visible=["comp1"],
            node_count=1
        )

        # Verify
        report = verifier.verify_execution(
            action="Create comp1 node",
            before_screenshot=before_screenshot,
            after_screenshot=after_screenshot,
            expected_state=expected,
            app="touchdesigner"
        )

        if report.overall_success:
            print("Action succeeded!")
        else:
            print(f"Action failed: {report.all_assertions_failed}")
    """

    def __init__(self, config: VerifierConfig | None = None):
        """Initialize the execution verifier.

        Args:
            config: Optional verification configuration
        """
        self._config = config or VerifierConfig()

        # Initialize verifiers based on config
        self._visual_verifier: VisualVerifier | None = None
        self._state_verifier: StateQueryVerifier | None = None

        if self._config.enable_visual:
            from app.evaluation.visual_verifier import create_visual_verifier
            self._visual_verifier = create_visual_verifier(use_vlm=self._config.use_vlm)

        if self._config.enable_state_query:
            from app.evaluation.state_verifier import create_state_query_verifier
            self._state_verifier = create_state_query_verifier()

        self._verification_history: list[ExecutionVerificationReport] = []

    @property
    def config(self) -> VerifierConfig:
        """Get the configuration."""
        return self._config

    @property
    def history(self) -> list[ExecutionVerificationReport]:
        """Get verification history."""
        return self._verification_history.copy()

    def verify_execution(
        self,
        action: str,
        before_screenshot: str | None,
        after_screenshot: str | None,
        expected_state: ExpectedState,
        app: str = "touchdesigner",
        context: dict[str, Any] | None = None,
    ) -> ExecutionVerificationReport:
        """Complete verification: visual + state query.

        Args:
            action: Description of the action that was executed
            before_screenshot: Path to screenshot before action (or None)
            after_screenshot: Path to screenshot after action (or None)
            expected_state: Expected state after action
            app: Application type (touchdesigner or houdini)
            context: Additional context for verification

        Returns:
            ExecutionVerificationReport with complete verification results
        """
        start_time = time.perf_counter()
        context = context or {}

        print(f"[VERIFY] Action: {action}")
        print(f"[VERIFY] Expected: {expected_state.summary()}")

        report = ExecutionVerificationReport(
            action=action,
            expected_state=expected_state,
        )

        visual_result: VisualVerificationResult | None = None
        state_result: StateQueryVerificationResult | None = None

        # Method 1: Visual verification
        if self._config.enable_visual and self._visual_verifier:
            if before_screenshot and after_screenshot:
                print(f"[VERIFY] Method 1: Visual verification")
                try:
                    visual_result = self._visual_verifier.verify_visual_change(
                        before_screenshot,
                        after_screenshot,
                        expected_state,
                        app,
                    )
                    report.visual_result = visual_result
                    print(f"[VERIFY] Visual: {visual_result.summary()}")
                except Exception as e:
                    print(f"[VERIFY] Visual verification error: {e}")
            else:
                print(f"[VERIFY] Visual: Skipped (screenshots not provided)")

        # Method 2: State query verification
        if self._config.enable_state_query and self._state_verifier:
            print(f"[VERIFY] Method 2: State query verification")
            try:
                state_result = self._state_verifier.verify_state_query(
                    expected_state,
                    app,
                )
                report.state_result = state_result
                print(f"[VERIFY] State: {state_result.summary()}")
            except Exception as e:
                print(f"[VERIFY] State query error: {e}")

        # Combine results
        all_passed = []
        all_failed = []

        if visual_result:
            all_passed.extend(visual_result.assertions_passed)
            all_failed.extend(visual_result.assertions_failed)

        if state_result:
            # Prefix state assertions to distinguish from visual
            state_passed = [{**a, "source": "state"} for a in state_result.assertions_passed]
            state_failed = [{**a, "source": "state"} for a in state_result.assertions_failed]
            all_passed.extend(state_passed)
            all_failed.extend(state_failed)

        report.all_assertions_passed = all_passed
        report.all_assertions_failed = all_failed

        # Calculate overall confidence
        report.confidence = self._calculate_overall_confidence(visual_result, state_result)

        # Determine overall success
        report.overall_success = self._determine_success(
            visual_result,
            state_result,
            report.confidence,
        )

        # Generate recommendations
        report.recommendations = self._generate_recommendations(
            report,
            visual_result,
            state_result,
        )

        # Set execution time
        report.execution_time_ms = (time.perf_counter() - start_time) * 1000

        # Store in history
        self._verification_history.append(report)

        print(f"[VERIFY] {report.summary()}")

        return report

    def verify_execution_simple(
        self,
        action: str,
        expected_state: ExpectedState,
        app: str = "touchdesigner",
    ) -> ExecutionVerificationReport:
        """Simplified verification without screenshots (state query only).

        Args:
            action: Description of the action
            expected_state: Expected state
            app: Application type

        Returns:
            ExecutionVerificationReport
        """
        return self.verify_execution(
            action=action,
            before_screenshot=None,
            after_screenshot=None,
            expected_state=expected_state,
            app=app,
        )

    def infer_expected_state(self, action: str, goal_description: str = "") -> ExpectedState:
        """Infer expected state from action description.

        Uses pattern matching to extract expected outcomes from natural
        language action descriptions.

        Args:
            action: Action description (e.g., "Create comp1 and null1")
            goal_description: Optional broader goal context

        Returns:
            ExpectedState inferred from action
        """
        expected = ExpectedState()
        action_lower = action.lower()

        # Pattern: Create/Add X
        # Match: "Create comp1", "Add a new null1", "Make comp1"
        # Also handles: "Create comp1 and null1"
        create_pattern = r'(?:create|add|make)\s+(?:a\s+)?(?:new\s+)?([\w\d]+(?:\s+(?:and|or)\s+[\w\d]+)*)'
        matches = re.findall(create_pattern, action_lower)
        seen = set()
        for match in matches:
            if match:
                # Split by 'and' or 'or' to get multiple elements
                elements = re.split(r'\s+(?:and|or)\s+', match)
                for elem in elements:
                    elem = elem.strip()
                    if elem and elem not in ['a', 'new', 'the', 'and', 'or'] and elem not in seen:
                        expected.new_elements_visible.append(elem)
                        seen.add(elem)
                        # Increment node count expectation
                        if expected.node_count is None:
                            expected.node_count = 0
                        expected.node_count += 1

        # Pattern: Delete/Remove X
        delete_pattern = r'(?:delete|remove|destroy)\s+(?:the\s+)?(\w+[\w\d]*)'
        matches = re.findall(delete_pattern, action_lower)
        seen = set()
        for match in matches:
            if match and match not in ['the', 'a', 'and', 'or'] and match not in seen:
                expected.removed_elements.append(match)
                seen.add(match)

        # Pattern: Connect X to Y
        connect_pattern = r'connect\s+(\w+)\s+(?:to|→|->)\s+(\w+)'
        connect_matches = re.findall(connect_pattern, action_lower)
        if connect_matches:
            if expected.connection_count is None:
                expected.connection_count = 0
            expected.connection_count += len(connect_matches)

        # Pattern: Set X.Y to Z
        param_pattern = r'(?:set|change|update)\s+(\w+\.?\w*)\s+(?:to|=)\s+([\d.]+)'
        param_matches = re.findall(param_pattern, action_lower)
        for param_path, value in param_matches:
            try:
                expected.parameter_values[param_path] = float(value)
            except ValueError:
                expected.parameter_values[param_path] = value

        # Pattern: Close dialog/popup
        if any(word in action_lower for word in ['close', 'dismiss', 'cancel']):
            if any(word in action_lower for word in ['dialog', 'popup', 'window', 'modal']):
                expected.dialog_open = None  # Expect closed

        # Pattern: Open dialog
        if any(word in action_lower for word in ['open', 'show', 'display']):
            if any(word in action_lower for word in ['dialog', 'popup', 'window']):
                # Try to extract dialog name
                dialog_pattern = r'(?:open|show|display)\s+(?:the\s+)?(\w+\s+)?dialog'
                match = re.search(dialog_pattern, action_lower)
                if match and match.group(1):
                    expected.dialog_open = match.group(1).strip()
                else:
                    expected.dialog_open = "dialog"  # Generic

        # Pattern: Navigate to X
        nav_pattern = r'(?:navigate|go|switch)\s+(?:to\s+)?([\w/]+)'
        nav_match = re.search(nav_pattern, action_lower)
        if nav_match:
            expected.active_network = nav_match.group(1)

        # Pattern: Select X
        select_pattern = r'(?:select|click|choose)\s+(?:the\s+)?(\w+)'
        if re.search(select_pattern, action_lower):
            expected.selection_changed = True

        return expected

    def _calculate_overall_confidence(
        self,
        visual_result: VisualVerificationResult | None,
        state_result: StateQueryVerificationResult | None,
    ) -> float:
        """Calculate overall confidence from individual results.

        Args:
            visual_result: Visual verification result
            state_result: State query result

        Returns:
            Overall confidence score
        """
        visual_confidence = visual_result.confidence if visual_result else 0.0
        state_confidence = state_result.confidence if state_result else 0.0

        # If only one method is available, use it
        if not visual_result:
            return state_confidence
        if not state_result:
            return visual_confidence

        # Weighted average of both methods
        total_weight = self._config.visual_confidence_weight + self._config.state_confidence_weight
        if total_weight == 0:
            return 0.5

        weighted = (
            visual_confidence * self._config.visual_confidence_weight +
            state_confidence * self._config.state_confidence_weight
        ) / total_weight

        return weighted

    def _determine_success(
        self,
        visual_result: VisualVerificationResult | None,
        state_result: StateQueryVerificationResult | None,
        confidence: float,
    ) -> bool:
        """Determine if verification passed overall.

        Args:
            visual_result: Visual verification result
            state_result: State query result
            confidence: Overall confidence score

        Returns:
            True if verification passed
        """
        # Check confidence threshold
        if confidence < self._config.min_confidence_threshold:
            return False

        # If requiring both methods, both must succeed
        if self._config.require_both_methods:
            visual_success = visual_result.success if visual_result else True
            state_success = state_result.success if state_result else True
            return visual_success and state_success

        # Otherwise, at least one method must succeed
        if visual_result and visual_result.success:
            return True
        if state_result and state_result.success:
            return True

        # If no methods were run, fail
        if not visual_result and not state_result:
            return False

        return False

    def _generate_recommendations(
        self,
        report: ExecutionVerificationReport,
        visual_result: VisualVerificationResult | None,
        state_result: StateQueryVerificationResult | None,
    ) -> list[str]:
        """Generate recommendations based on verification results.

        Args:
            report: Verification report
            visual_result: Visual verification result
            state_result: State query result

        Returns:
            List of recommendation strings
        """
        recommendations = []

        if report.overall_success:
            if report.confidence < 0.9:
                recommendations.append(
                    "Verification passed but with lower confidence. "
                    "Consider adding more specific assertions."
                )
        else:
            # Failed - provide specific recommendations
            if visual_result and not visual_result.success:
                recommendations.append(
                    "Visual verification failed. Check if UI updated correctly."
                )

            if state_result and not state_result.success:
                recommendations.append(
                    "State query verification failed. Check if action executed correctly."
                )

            # Analyze specific failures
            for failure in report.all_assertions_failed:
                failure_type = failure.get("type", "")
                target = failure.get("target", "")

                if failure_type == "element_appeared":
                    recommendations.append(
                        f"Element '{target}' did not appear. "
                        f"Verify the action was executed and UI updated."
                    )
                elif failure_type == "element_removed":
                    recommendations.append(
                        f"Element '{target}' was not removed. "
                        f"Check if the action completed successfully."
                    )
                elif failure_type == "parameter_value":
                    recommendations.append(
                        f"Parameter '{target}' value mismatch. "
                        f"Check if parameter was actually set."
                    )
                elif failure_type == "node_count":
                    recommendations.append(
                        "Node count mismatch. Expected nodes may not have been created."
                    )

        return recommendations

    def get_statistics(self) -> dict[str, Any]:
        """Get verification statistics.

        Returns:
            Dictionary with verification statistics
        """
        total = len(self._verification_history)
        passed = sum(1 for r in self._verification_history if r.overall_success)
        failed = total - passed

        if total == 0:
            return {
                "total_verifications": 0,
                "passed": 0,
                "failed": 0,
                "pass_rate": 0.0,
            }

        avg_confidence = sum(r.confidence for r in self._verification_history) / total

        return {
            "total_verifications": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": passed / total,
            "avg_confidence": avg_confidence,
            "with_visual": sum(1 for r in self._verification_history if r.has_visual_verification),
            "with_state": sum(1 for r in self._verification_history if r.has_state_verification),
        }


def create_execution_verifier(
    enable_visual: bool = True,
    enable_state_query: bool = True,
    min_confidence: float = 0.6,
    use_vlm: bool = True,
) -> ExecutionVerifier:
    """Create a configured execution verifier.

    Args:
        enable_visual: Enable visual verification
        enable_state_query: Enable state query verification
        min_confidence: Minimum confidence threshold
        use_vlm: Use VLM for visual analysis

    Returns:
        Configured ExecutionVerifier instance
    """
    config = VerifierConfig(
        enable_visual=enable_visual,
        enable_state_query=enable_state_query,
        min_confidence_threshold=min_confidence,
        use_vlm=use_vlm,
    )

    return ExecutionVerifier(config=config)
