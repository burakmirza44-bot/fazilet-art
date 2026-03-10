"""State Query Verifier Module.

Provides state verification by querying application directly.
Faster than visual verification and more reliable for numerical values.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Optional

import urllib.request
from urllib.error import URLError

from app.evaluation.verification_models import (
    ExpectedState,
    StateQueryVerificationResult,
)


@dataclass
class ApplicationState:
    """Complete application state from query."""

    nodes: list[dict[str, Any]] = None
    """List of nodes/operators with their properties."""

    connections: list[dict[str, Any]] = None
    """List of connections between nodes."""

    parameters: dict[str, Any] = None
    """Parameter values by path."""

    dialogs: list[str] = None
    """Currently open dialogs."""

    active_network: str = ""
    """Current active network path."""

    selected_nodes: list[str] = None
    """Currently selected node names."""

    def __post_init__(self) -> None:
        """Initialize mutable defaults."""
        if self.nodes is None:
            object.__setattr__(self, "nodes", [])
        if self.connections is None:
            object.__setattr__(self, "connections", [])
        if self.parameters is None:
            object.__setattr__(self, "parameters", {})
        if self.dialogs is None:
            object.__setattr__(self, "dialogs", [])
        if self.selected_nodes is None:
            object.__setattr__(self, "selected_nodes", [])


class StateQueryVerifier:
    """Verify state by querying application directly.

    Uses bridge connections or APIs to query actual application state
    and verify against expected state. Faster and more precise than
    visual verification for numerical values.
    """

    def __init__(
        self,
        td_bridge_host: str = "127.0.0.1",
        td_bridge_port: int = 9988,
        houdini_bridge_host: str = "127.0.0.1",
        houdini_bridge_port: int = 9989,
        timeout: float = 5.0,
    ):
        """Initialize the state query verifier.

        Args:
            td_bridge_host: TouchDesigner bridge host
            td_bridge_port: TouchDesigner bridge port
            houdini_bridge_host: Houdini bridge host
            houdini_bridge_port: Houdini bridge port
            timeout: Query timeout in seconds
        """
        self._td_host = td_bridge_host
        self._td_port = td_bridge_port
        self._houdini_host = houdini_bridge_host
        self._houdini_port = houdini_bridge_port
        self._timeout = timeout

    def verify_state_query(
        self,
        expected_state: ExpectedState,
        app: str = "touchdesigner",
    ) -> StateQueryVerificationResult:
        """Query application state and verify expected state.

        Args:
            expected_state: Expected state after action
            app: Application type (touchdesigner or houdini)

        Returns:
            StateQueryVerificationResult with verification outcome
        """
        result = StateQueryVerificationResult()

        # Query current state
        try:
            if app == "touchdesigner":
                current_state = self._query_td_state()
            elif app == "houdini":
                current_state = self._query_houdini_state()
            else:
                current_state = ApplicationState()

            result.queried_state = {
                "nodes": current_state.nodes,
                "connections": current_state.connections,
                "parameters": current_state.parameters,
                "dialogs": current_state.dialogs,
                "active_network": current_state.active_network,
                "selected_nodes": current_state.selected_nodes,
            }

        except Exception as e:
            result.queried_state = {"error": str(e)}
            result.assertions_failed.append({
                "type": "state_query",
                "target": "application",
                "expected": "successful query",
                "actual": f"error: {str(e)}",
                "status": "fail",
            })
            result.confidence = 0.0
            return result

        # Verify node count
        if expected_state.node_count is not None:
            actual_count = len(current_state.nodes)

            if actual_count >= expected_state.node_count:
                result.assertions_passed.append({
                    "type": "node_count",
                    "expected": expected_state.node_count,
                    "actual": actual_count,
                    "status": "pass",
                })
            else:
                result.assertions_failed.append({
                    "type": "node_count",
                    "expected": expected_state.node_count,
                    "actual": actual_count,
                    "status": "fail",
                })

        # Verify connection count
        if expected_state.connection_count is not None:
            actual_count = len(current_state.connections)

            if actual_count >= expected_state.connection_count:
                result.assertions_passed.append({
                    "type": "connection_count",
                    "expected": expected_state.connection_count,
                    "actual": actual_count,
                    "status": "pass",
                })
            else:
                result.assertions_failed.append({
                    "type": "connection_count",
                    "expected": expected_state.connection_count,
                    "actual": actual_count,
                    "status": "fail",
                })

        # Verify new elements visible (exist as nodes)
        node_names = {n.get("name", "").lower() for n in current_state.nodes}
        for element in expected_state.new_elements_visible:
            if element.lower() in node_names:
                result.assertions_passed.append({
                    "type": "element_exists",
                    "target": element,
                    "status": "pass",
                })
            else:
                result.assertions_failed.append({
                    "type": "element_exists",
                    "target": element,
                    "expected": "exists",
                    "actual": "not found",
                    "available_nodes": list(node_names),
                    "status": "fail",
                })

        # Verify removed elements (should NOT exist)
        for element in expected_state.removed_elements:
            if element.lower() not in node_names:
                result.assertions_passed.append({
                    "type": "element_removed",
                    "target": element,
                    "status": "pass",
                })
            else:
                result.assertions_failed.append({
                    "type": "element_removed",
                    "target": element,
                    "expected": "removed",
                    "actual": "still exists",
                    "status": "fail",
                })

        # Verify parameter values
        for param_path, expected_value in expected_state.parameter_values.items():
            actual_value = self._query_parameter(param_path, app, current_state)

            if actual_value is not None:
                # Handle numerical values with tolerance
                if isinstance(expected_value, (int, float)) and isinstance(actual_value, (int, float)):
                    tolerance = expected_value * 0.1 if expected_value != 0 else 0.1
                    if abs(actual_value - expected_value) <= tolerance:
                        result.assertions_passed.append({
                            "type": "parameter_value",
                            "parameter": param_path,
                            "expected": expected_value,
                            "actual": actual_value,
                            "status": "pass",
                        })
                    else:
                        result.assertions_failed.append({
                            "type": "parameter_value",
                            "parameter": param_path,
                            "expected": expected_value,
                            "actual": actual_value,
                            "tolerance": tolerance,
                            "status": "fail",
                        })
                else:
                    # Exact match for non-numerical values
                    if actual_value == expected_value:
                        result.assertions_passed.append({
                            "type": "parameter_value",
                            "parameter": param_path,
                            "expected": expected_value,
                            "actual": actual_value,
                            "status": "pass",
                        })
                    else:
                        result.assertions_failed.append({
                            "type": "parameter_value",
                            "parameter": param_path,
                            "expected": expected_value,
                            "actual": actual_value,
                            "status": "fail",
                        })
            else:
                result.assertions_failed.append({
                    "type": "parameter_value",
                    "parameter": param_path,
                    "expected": expected_value,
                    "actual": "not found",
                    "status": "fail",
                })

        # Verify active network
        if expected_state.active_network is not None:
            if current_state.active_network == expected_state.active_network:
                result.assertions_passed.append({
                    "type": "active_network",
                    "expected": expected_state.active_network,
                    "actual": current_state.active_network,
                    "status": "pass",
                })
            else:
                result.assertions_failed.append({
                    "type": "active_network",
                    "expected": expected_state.active_network,
                    "actual": current_state.active_network,
                    "status": "fail",
                })

        # Verify dialogs
        if expected_state.dialog_open is not None:
            if expected_state.dialog_open == "":  # Expecting no dialogs
                if not current_state.dialogs:
                    result.assertions_passed.append({
                        "type": "dialog_state",
                        "expected": "closed",
                        "actual": "closed",
                        "status": "pass",
                    })
                else:
                    result.assertions_failed.append({
                        "type": "dialog_state",
                        "expected": "closed",
                        "actual": f"open: {current_state.dialogs}",
                        "status": "fail",
                    })
            else:  # Expecting specific dialog
                if expected_state.dialog_open in current_state.dialogs:
                    result.assertions_passed.append({
                        "type": "dialog_state",
                        "target": expected_state.dialog_open,
                        "expected": "open",
                        "actual": "open",
                        "status": "pass",
                    })
                else:
                    result.assertions_failed.append({
                        "type": "dialog_state",
                        "target": expected_state.dialog_open,
                        "expected": "open",
                        "actual": f"not found, have: {current_state.dialogs}",
                        "status": "fail",
                    })

        # Verify selection changed
        if expected_state.selection_changed:
            if current_state.selected_nodes:
                result.assertions_passed.append({
                    "type": "selection_changed",
                    "selected": current_state.selected_nodes,
                    "status": "pass",
                })
            else:
                result.assertions_failed.append({
                    "type": "selection_changed",
                    "expected": "selection",
                    "actual": "nothing selected",
                    "status": "fail",
                })

        # Calculate confidence
        total = len(result.assertions_passed) + len(result.assertions_failed)
        result.confidence = len(result.assertions_passed) / total if total > 0 else 0.5

        return result

    def _query_td_state(self) -> ApplicationState:
        """Query TouchDesigner state via bridge.

        Returns:
            ApplicationState with current TD state
        """
        state = ApplicationState()

        try:
            # Query nodes
            nodes_response = self._send_bridge_request(
                self._td_host,
                self._td_port,
                {"command": "list_nodes"},
            )
            if nodes_response and "nodes" in nodes_response:
                state.nodes = nodes_response["nodes"]

            # Query connections
            connections_response = self._send_bridge_request(
                self._td_host,
                self._td_port,
                {"command": "list_connections"},
            )
            if connections_response and "connections" in connections_response:
                state.connections = connections_response["connections"]

            # Query active network
            network_response = self._send_bridge_request(
                self._td_host,
                self._td_port,
                {"command": "get_active_network"},
            )
            if network_response and "path" in network_response:
                state.active_network = network_response["path"]

            # Query selected nodes
            selection_response = self._send_bridge_request(
                self._td_host,
                self._td_port,
                {"command": "get_selected"},
            )
            if selection_response and "selected" in selection_response:
                state.selected_nodes = selection_response["selected"]

        except Exception as e:
            # Bridge not available - return empty state
            state.nodes = []

        return state

    def _query_houdini_state(self) -> ApplicationState:
        """Query Houdini state via HOM API or bridge.

        Returns:
            ApplicationState with current Houdini state
        """
        state = ApplicationState()

        try:
            # Try HOM API first (if running inside Houdini)
            import hou

            # Get nodes in current network
            pwd = hou.pwd()
            if pwd:
                state.active_network = pwd.path()
                for child in pwd.children():
                    state.nodes.append({
                        "name": child.name(),
                        "type": child.type().name(),
                        "path": child.path(),
                    })

            # Get selected nodes
            for node in hou.selectedNodes():
                state.selected_nodes.append(node.name())

            # Get connections
            for node in pwd.children() if pwd else []:
                for input_idx, input_node in enumerate(node.inputs()):
                    if input_node:
                        state.connections.append({
                            "from": input_node.path(),
                            "to": node.path(),
                            "input_index": input_idx,
                        })

        except ImportError:
            # HOM not available, try bridge
            try:
                nodes_response = self._send_bridge_request(
                    self._houdini_host,
                    self._houdini_port,
                    {"command": "list_nodes"},
                )
                if nodes_response and "nodes" in nodes_response:
                    state.nodes = nodes_response["nodes"]

            except Exception:
                pass

        return state

    def _query_parameter(
        self,
        param_path: str,
        app: str,
        current_state: ApplicationState,
    ) -> Optional[Any]:
        """Query single parameter value.

        Args:
            param_path: Parameter path (e.g., "blur1.amount")
            app: Application type
            current_state: Current application state

        Returns:
            Parameter value or None if not found
        """
        # First check in current state
        if param_path in current_state.parameters:
            return current_state.parameters[param_path]

        # Try to query directly via bridge
        try:
            if app == "touchdesigner":
                response = self._send_bridge_request(
                    self._td_host,
                    self._td_port,
                    {"command": "get_parameter", "path": param_path},
                )
                if response and "value" in response:
                    return response["value"]

            elif app == "houdini":
                # Try HOM first
                try:
                    import hou
                    parts = param_path.split(".")
                    if len(parts) >= 2:
                        node_path = "/".join(parts[:-1])
                        parm_name = parts[-1]
                        node = hou.node(node_path)
                        if node:
                            parm = node.parm(parm_name)
                            if parm:
                                return parm.eval()
                except ImportError:
                    pass

                # Try bridge
                response = self._send_bridge_request(
                    self._houdini_host,
                    self._houdini_port,
                    {"command": "get_parameter", "path": param_path},
                )
                if response and "value" in response:
                    return response["value"]

        except Exception:
            pass

        return None

    def _send_bridge_request(
        self,
        host: str,
        port: int,
        request_data: dict[str, Any],
    ) -> Optional[dict[str, Any]]:
        """Send request to bridge.

        Args:
            host: Bridge host
            port: Bridge port
            request_data: Request payload

        Returns:
            Response data or None on failure
        """
        try:
            url = f"http://{host}:{port}/execute"
            data = json.dumps(request_data).encode("utf-8")

            req = urllib.request.Request(
                url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=self._timeout) as response:
                return json.loads(response.read().decode("utf-8"))

        except URLError:
            return None
        except Exception:
            return None


def create_state_query_verifier(
    td_bridge_host: str = "127.0.0.1",
    td_bridge_port: int = 9988,
    houdini_bridge_host: str = "127.0.0.1",
    houdini_bridge_port: int = 9989,
) -> StateQueryVerifier:
    """Create a configured state query verifier.

    Args:
        td_bridge_host: TouchDesigner bridge host
        td_bridge_port: TouchDesigner bridge port
        houdini_bridge_host: Houdini bridge host
        houdini_bridge_port: Houdini bridge port

    Returns:
        Configured StateQueryVerifier instance
    """
    return StateQueryVerifier(
        td_bridge_host=td_bridge_host,
        td_bridge_port=td_bridge_port,
        houdini_bridge_host=houdini_bridge_host,
        houdini_bridge_port=houdini_bridge_port,
    )
