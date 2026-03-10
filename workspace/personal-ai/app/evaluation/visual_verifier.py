"""Visual Verifier Module.

Provides visual verification of post-execution state through
screenshot comparison and VLM analysis.
"""

from __future__ import annotations

import base64
import os
import re
from dataclasses import dataclass, field
from typing import Any

from app.evaluation.verification_models import (
    ExpectedState,
    VisualVerificationResult,
)


@dataclass
class VisualUnderstandingResult:
    """Result of visual understanding analysis."""

    nodes_visible: list[str] = field(default_factory=list)
    """List of visible nodes/operators."""

    connections_visible: list[str] = field(default_factory=list)
    """List of visible connections."""

    parameters_visible: dict[str, Any] = field(default_factory=dict)
    """Visible parameter values."""

    dialogs_visible: list[str] = field(default_factory=list)
    """Visible dialogs/windows."""

    active_network: str = ""
    """Currently active network path."""

    selected_elements: list[str] = field(default_factory=list)
    """Currently selected elements."""

    combined_state: dict[str, Any] = field(default_factory=dict)
    """Combined state dictionary for easy access."""


class VisualUnderstandingPipeline:
    """Pipeline for understanding application state from screenshots.

    Analyzes screenshots to extract visible elements, nodes, parameters,
    and other relevant state information.
    """

    def __init__(self, use_vlm: bool = True):
        """Initialize the pipeline.

        Args:
            use_vlm: Whether to use VLM for analysis (fallback to heuristics if False)
        """
        self._use_vlm = use_vlm

    def understand_screenshot(self, screenshot_path: str, app: str = "touchdesigner") -> VisualUnderstandingResult:
        """Analyze screenshot to understand application state.

        Args:
            screenshot_path: Path to screenshot image
            app: Application type (touchdesigner or houdini)

        Returns:
            VisualUnderstandingResult with extracted state
        """
        result = VisualUnderstandingResult()

        if not os.path.exists(screenshot_path):
            return result

        if self._use_vlm:
            # Use VLM for analysis
            vlm_result = self._analyze_with_vlm(screenshot_path, app)
            result = self._parse_vlm_response(vlm_result, app)
        else:
            # Use heuristic analysis (placeholder)
            result = self._heuristic_analysis(screenshot_path, app)

        # Build combined state
        result.combined_state = {
            "nodes_visible": result.nodes_visible,
            "connections_visible": result.connections_visible,
            "parameters_visible": result.parameters_visible,
            "dialogs_visible": result.dialogs_visible,
            "active_network": result.active_network,
            "selected_elements": result.selected_elements,
        }

        return result

    def _analyze_with_vlm(self, screenshot_path: str, app: str) -> str:
        """Use VLM to analyze screenshot.

        Args:
            screenshot_path: Path to screenshot
            app: Application type

        Returns:
            VLM response text
        """
        try:
            # Try to use Anthropic Claude for VLM analysis
            from anthropic import Anthropic

            with open(screenshot_path, "rb") as f:
                image_b64 = base64.standard_b64encode(f.read()).decode()

            client = Anthropic()

            prompt = f"""Analyze this {app} screenshot and describe:

1. What nodes/operators are visible? (list their names)
2. What connections exist between nodes?
3. What parameters are visible and their values?
4. Are any dialogs or popups open?
5. What network/path is currently active?
6. What elements are selected?

Format your response as structured data that can be parsed."""

            message = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1024,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": image_b64,
                                },
                            },
                            {"type": "text", "text": prompt},
                        ],
                    }
                ],
            )

            return message.content[0].text

        except ImportError:
            return "VLM not available"
        except Exception as e:
            return f"VLM error: {str(e)}"

    def _parse_vlm_response(self, response: str, app: str) -> VisualUnderstandingResult:
        """Parse VLM response into structured result.

        Args:
            response: VLM response text
            app: Application type

        Returns:
            VisualUnderstandingResult
        """
        result = VisualUnderstandingResult()

        # Extract nodes using regex patterns
        node_patterns = [
            r'nodes?[;:](.+?)(?=\n\d|\Z)',
            r'visible nodes?[;:](.+?)(?=\n\d|\Z)',
            r'(\w+\d+)[\s-]+(?:node|operator|comp|null|blur)',
        ]

        for pattern in node_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE | re.DOTALL)
            for match in matches:
                if isinstance(match, str):
                    # Split by common delimiters
                    nodes = re.split(r'[,;\n]+', match)
                    for node in nodes:
                        node = node.strip().strip('-* ')
                        if node and len(node) > 1:
                            result.nodes_visible.append(node)

        # Extract parameters
        param_pattern = r'(\w+\.?\w*)\s*[=:]\s*([\d.]+)'
        param_matches = re.findall(param_pattern, response)
        for param_name, param_value in param_matches:
            try:
                result.parameters_visible[param_name] = float(param_value)
            except ValueError:
                result.parameters_visible[param_name] = param_value

        # Extract network path
        network_patterns = [
            r'(?:active network|network path|current path)[;: ]+([\w/]+)',
            r'path[;: ]+([\w/]+)',
        ]
        for pattern in network_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                result.active_network = match.group(1)
                break

        # Extract dialogs
        if "dialog" in response.lower() or "popup" in response.lower():
            dialog_pattern = r'(?:dialog|popup|window)[;: ]+(\w+)'
            matches = re.findall(dialog_pattern, response, re.IGNORECASE)
            result.dialogs_visible.extend(matches)

        return result

    def _heuristic_analysis(self, screenshot_path: str, app: str) -> VisualUnderstandingResult:
        """Heuristic analysis without VLM (placeholder).

        Args:
            screenshot_path: Path to screenshot
            app: Application type

        Returns:
            VisualUnderstandingResult
        """
        # Placeholder for OCR or computer vision based analysis
        # In a full implementation, this would use OCR to extract text
        # from the screenshot and identify UI elements
        return VisualUnderstandingResult()


class VisualVerifier:
    """Verify post-execution state visually.

    Takes screenshots before and after action execution, then compares
them to verify that the expected state changes occurred.
    """

    def __init__(self, vision_pipeline: VisualUnderstandingPipeline | None = None):
        """Initialize the visual verifier.

        Args:
            vision_pipeline: Optional custom vision pipeline
        """
        self._vision_pipeline = vision_pipeline or VisualUnderstandingPipeline()

    def verify_visual_change(
        self,
        before_screenshot: str,
        after_screenshot: str,
        expected_state: ExpectedState,
        app: str = "touchdesigner",
    ) -> VisualVerificationResult:
        """Compare before/after screenshots to verify state change.

        Args:
            before_screenshot: Path to screenshot before action
            after_screenshot: Path to screenshot after action
            expected_state: Expected state after action
            app: Application type

        Returns:
            VisualVerificationResult with pass/fail status
        """
        result = VisualVerificationResult(
            before_screenshot=before_screenshot,
            after_screenshot=after_screenshot,
        )

        # Analyze both screenshots
        before = self._vision_pipeline.understand_screenshot(before_screenshot, app)
        after = self._vision_pipeline.understand_screenshot(after_screenshot, app)

        # Check new elements visible
        for element in expected_state.new_elements_visible:
            was_visible_before = element in before.combined_state.get("nodes_visible", [])
            is_visible_now = element in after.combined_state.get("nodes_visible", [])

            if not was_visible_before and is_visible_now:
                result.assertions_passed.append({
                    "type": "element_appeared",
                    "target": element,
                    "evidence": f"{element} visible in after screenshot",
                })
            else:
                result.assertions_failed.append({
                    "type": "element_appeared",
                    "target": element,
                    "expected": "visible",
                    "actual": "not visible" if not is_visible_now else "was already visible",
                    "evidence": {
                        "before": before.combined_state.get("nodes_visible", []),
                        "after": after.combined_state.get("nodes_visible", []),
                    },
                })

        # Check removed elements
        for element in expected_state.removed_elements:
            was_visible_before = element in before.combined_state.get("nodes_visible", [])
            is_visible_now = element in after.combined_state.get("nodes_visible", [])

            if was_visible_before and not is_visible_now:
                result.assertions_passed.append({
                    "type": "element_removed",
                    "target": element,
                    "evidence": f"{element} no longer visible",
                })
            else:
                result.assertions_failed.append({
                    "type": "element_removed",
                    "target": element,
                    "expected": "not visible",
                    "actual": "still visible" if is_visible_now else "was not visible before",
                    "evidence": {
                        "before": before.combined_state.get("nodes_visible", []),
                        "after": after.combined_state.get("nodes_visible", []),
                    },
                })

        # Check node count
        if expected_state.node_count is not None:
            before_count = len(before.combined_state.get("nodes_visible", []))
            after_count = len(after.combined_state.get("nodes_visible", []))

            if after_count >= expected_state.node_count:
                result.assertions_passed.append({
                    "type": "node_count",
                    "target": "network",
                    "expected": expected_state.node_count,
                    "actual": after_count,
                    "evidence": f"Node count: {before_count} → {after_count}",
                })
            else:
                result.assertions_failed.append({
                    "type": "node_count",
                    "target": "network",
                    "expected": expected_state.node_count,
                    "actual": after_count,
                    "evidence": f"Expected ≥{expected_state.node_count}, got {after_count}",
                })

        # Check connection count
        if expected_state.connection_count is not None:
            before_count = len(before.combined_state.get("connections_visible", []))
            after_count = len(after.combined_state.get("connections_visible", []))

            if after_count >= expected_state.connection_count:
                result.assertions_passed.append({
                    "type": "connection_count",
                    "target": "network",
                    "expected": expected_state.connection_count,
                    "actual": after_count,
                    "evidence": f"Connection count: {before_count} → {after_count}",
                })
            else:
                result.assertions_failed.append({
                    "type": "connection_count",
                    "target": "network",
                    "expected": expected_state.connection_count,
                    "actual": after_count,
                    "evidence": f"Expected ≥{expected_state.connection_count}, got {after_count}",
                })

        # Check dialogs
        if expected_state.dialog_open is not None:
            after_dialogs = after.combined_state.get("dialogs_visible", [])
            dialog_name = expected_state.dialog_open

            if dialog_name:  # Expecting dialog to be open
                if dialog_name in after_dialogs:
                    result.assertions_passed.append({
                        "type": "dialog_state",
                        "target": dialog_name,
                        "expected": "open",
                        "actual": "open",
                        "evidence": f"Dialog {dialog_name} is visible",
                    })
                else:
                    result.assertions_failed.append({
                        "type": "dialog_state",
                        "target": dialog_name,
                        "expected": "open",
                        "actual": "closed",
                        "evidence": f"Expected dialog {dialog_name}, found {after_dialogs}",
                    })
            else:  # Expecting no dialogs
                if not after_dialogs:
                    result.assertions_passed.append({
                        "type": "dialog_state",
                        "target": "any",
                        "expected": "closed",
                        "actual": "closed",
                        "evidence": "No dialogs visible",
                    })
                else:
                    result.assertions_failed.append({
                        "type": "dialog_state",
                        "target": "any",
                        "expected": "closed",
                        "actual": f"open: {after_dialogs}",
                        "evidence": f"Unexpected dialogs: {after_dialogs}",
                    })

        # Use VLM for detailed comparison
        try:
            vlm_comparison = self._ask_vlm_for_comparison(
                before_screenshot,
                after_screenshot,
                expected_state,
                app,
            )
            result.vlm_analysis = vlm_comparison

            if vlm_comparison.get("changes_detected"):
                result.assertions_passed.append({
                    "type": "vlm_analysis",
                    "evidence": vlm_comparison.get("changes_description", ""),
                })

        except Exception as e:
            # VLM comparison failed, but we still have basic verification
            result.vlm_analysis = {"error": str(e)}

        # Calculate confidence
        result.confidence = self._calculate_confidence(result)

        return result

    def _ask_vlm_for_comparison(
        self,
        before_path: str,
        after_path: str,
        expected: ExpectedState,
        app: str,
    ) -> dict[str, Any]:
        """Use VLM to compare screenshots and detect changes.

        Args:
            before_path: Path to before screenshot
            after_path: Path to after screenshot
            expected: Expected state changes
            app: Application type

        Returns:
            Dictionary with VLM analysis results
        """
        try:
            from anthropic import Anthropic

            with open(before_path, "rb") as f:
                before_b64 = base64.standard_b64encode(f.read()).decode()

            with open(after_path, "rb") as f:
                after_b64 = base64.standard_b64encode(f.read()).decode()

            prompt = f"""Compare these two {app} screenshots (BEFORE and AFTER).

BEFORE (first image) shows the state before an action.
AFTER (second image) shows the state after the action.

What changed? Describe:
1. New elements that appeared
2. Elements that disappeared
3. Changes to existing elements
4. Parameter values that changed

Expected changes (user's expectation):
- New elements: {expected.new_elements_visible}
- Removed elements: {expected.removed_elements}
- Node count should be ≥ {expected.node_count}
- Connection count should be ≥ {expected.connection_count}

Report:
1. Did expected changes occur?
2. Any unexpected changes?
3. Did the action succeed overall?
4. Confidence level (high/medium/low)"""

            client = Anthropic()

            message = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1024,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": before_b64,
                                },
                            },
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": after_b64,
                                },
                            },
                            {"type": "text", "text": prompt},
                        ],
                    }
                ],
            )

            response = message.content[0].text

            return {
                "changes_detected": "changed" in response.lower() or "appeared" in response.lower(),
                "changes_description": response,
                "action_succeeded": "succeeded" in response.lower() or "success" in response.lower(),
                "raw_response": response,
            }

        except ImportError:
            return {
                "changes_detected": False,
                "error": "Anthropic client not available",
            }
        except Exception as e:
            return {
                "changes_detected": False,
                "error": str(e),
            }

    def _calculate_confidence(self, result: VisualVerificationResult) -> float:
        """Calculate verification confidence score.

        Args:
            result: Visual verification result

        Returns:
            Confidence score between 0.0 and 1.0
        """
        total = len(result.assertions_passed) + len(result.assertions_failed)

        if total == 0:
            # No assertions - check VLM analysis
            if result.vlm_analysis.get("action_succeeded"):
                return 0.7  # VLM says it succeeded
            return 0.5  # Unknown

        return len(result.assertions_passed) / total


def create_visual_verifier(use_vlm: bool = True) -> VisualVerifier:
    """Create a configured visual verifier.

    Args:
        use_vlm: Whether to use VLM for analysis

    Returns:
        Configured VisualVerifier instance
    """
    pipeline = VisualUnderstandingPipeline(use_vlm=use_vlm)
    return VisualVerifier(vision_pipeline=pipeline)
