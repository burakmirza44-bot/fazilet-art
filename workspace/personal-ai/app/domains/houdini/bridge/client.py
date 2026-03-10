"""Houdini Bridge Client.

Provides client for sending recipes to Houdini via file-based protocol.
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from app.domains.houdini.bridge.models import (
    RecipeRequest,
    RecipeResult,
    RecipeStep,
)


@dataclass
class HoudiniBridgeClientConfig:
    """Configuration for the Houdini bridge client."""

    inbox_dir: str = "./data/inbox"
    outbox_dir: str = "./data/outbox"
    default_timeout: float = 30.0
    poll_interval: float = 0.5
    cleanup_files: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "inbox_dir": self.inbox_dir,
            "outbox_dir": self.outbox_dir,
            "default_timeout": self.default_timeout,
            "poll_interval": self.poll_interval,
            "cleanup_files": self.cleanup_files,
        }


class HoudiniBridgeClient:
    """Client for sending recipes to Houdini bridge server.

    Uses file-based inbox/outbox protocol:
    1. Write recipe to inbox_dir/recipe_*.json
    2. Wait for result in outbox_dir/result_*.json
    3. Return result to caller

    Usage:
        client = HoudiniBridgeClient()

        # Send a recipe
        steps = [
            RecipeStep(order=1, name="Create GEO", action="create_node",
                      node_type="geo", node_path="/obj/geo1"),
            RecipeStep(order=2, name="Add box", action="create_node",
                      node_type="box", node_path="/obj/geo1/box1"),
        ]
        result = client.send_recipe(steps)

        if result.success:
            print(f"Created: {result.output['created_nodes']}")
    """

    def __init__(
        self,
        config: HoudiniBridgeClientConfig | None = None,
        inbox_dir: str | None = None,
        outbox_dir: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        """Initialize the bridge client.

        Args:
            config: Optional configuration object
            inbox_dir: Override inbox directory
            outbox_dir: Override outbox directory
            timeout: Default timeout for waiting for results
        """
        self._config = config or HoudiniBridgeClientConfig()

        if inbox_dir:
            self._config.inbox_dir = inbox_dir
        if outbox_dir:
            self._config.outbox_dir = outbox_dir
        if timeout != 30.0:
            self._config.default_timeout = timeout

        self._inbox_path = Path(self._config.inbox_dir)
        self._outbox_path = Path(self._config.outbox_dir)

        # Create directories
        self._inbox_path.mkdir(parents=True, exist_ok=True)
        self._outbox_path.mkdir(parents=True, exist_ok=True)

    @property
    def inbox_path(self) -> Path:
        """Get inbox path."""
        return self._inbox_path

    @property
    def outbox_path(self) -> Path:
        """Get outbox path."""
        return self._outbox_path

    def send_recipe(
        self,
        steps: list[RecipeStep],
        context: dict[str, Any] | None = None,
        recipe_id: str | None = None,
        timeout: float | None = None,
    ) -> RecipeResult:
        """Send a recipe to Houdini and wait for the result.

        Args:
            steps: List of recipe steps to execute
            context: Optional execution context
            recipe_id: Optional recipe ID (auto-generated if None)
            timeout: Timeout in seconds (uses default if None)

        Returns:
            RecipeResult with execution outcome

        Raises:
            TimeoutError: If Houdini doesn't respond within timeout
        """
        # Create request
        request = RecipeRequest(
            recipe_id=recipe_id or f"recipe_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}",
            recipe_steps=steps,
            context=context or {},
        )

        return self.send_request(request, timeout)

    def send_request(
        self,
        request: RecipeRequest,
        timeout: float | None = None,
    ) -> RecipeResult:
        """Send a recipe request and wait for result.

        Args:
            request: RecipeRequest to send
            timeout: Timeout in seconds

        Returns:
            RecipeResult

        Raises:
            TimeoutError: If no response within timeout
        """
        timeout = timeout or self._config.default_timeout

        # Generate filenames
        timestamp = int(time.time() * 1000)
        recipe_filename = f"recipe_{timestamp}_{request.recipe_id}.json"
        result_filename = recipe_filename.replace("recipe_", "result_")

        recipe_path = self._inbox_path / recipe_filename
        result_path = self._outbox_path / result_filename

        # Clean up any existing result file
        if result_path.exists():
            result_path.unlink()

        # Write recipe to inbox
        with open(recipe_path, "w", encoding="utf-8") as f:
            json.dump(request.to_dict(), f, indent=2)

        # Wait for result
        start_time = time.time()
        while time.time() - start_time < timeout:
            if result_path.exists():
                try:
                    with open(result_path, "r", encoding="utf-8") as f:
                        result_data = json.load(f)

                    result = RecipeResult.from_dict(result_data)

                    # Clean up
                    if self._config.cleanup_files:
                        result_path.unlink()
                        if recipe_path.exists():
                            recipe_path.unlink()

                    return result

                except json.JSONDecodeError:
                    # Result file might be partially written, wait and retry
                    pass

            time.sleep(self._config.poll_interval)

        # Timeout
        raise TimeoutError(
            f"Houdini did not respond within {timeout}s for recipe {request.recipe_id}"
        )

    def send_recipe_async(
        self,
        steps: list[RecipeStep],
        context: dict[str, Any] | None = None,
        recipe_id: str | None = None,
    ) -> str:
        """Send a recipe without waiting for result.

        Args:
            steps: List of recipe steps
            context: Optional execution context
            recipe_id: Optional recipe ID

        Returns:
            Recipe ID for later result retrieval
        """
        request = RecipeRequest(
            recipe_id=recipe_id or f"recipe_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}",
            recipe_steps=steps,
            context=context or {},
        )

        timestamp = int(time.time() * 1000)
        recipe_filename = f"recipe_{timestamp}_{request.recipe_id}.json"
        recipe_path = self._inbox_path / recipe_filename

        with open(recipe_path, "w", encoding="utf-8") as f:
            json.dump(request.to_dict(), f, indent=2)

        return request.recipe_id

    def get_result(
        self,
        recipe_id: str,
        timeout: float | None = None,
    ) -> RecipeResult | None:
        """Get result for a previously sent recipe.

        Args:
            recipe_id: Recipe ID to get result for
            timeout: Timeout for waiting

        Returns:
            RecipeResult or None if not available
        """
        timeout = timeout or self._config.default_timeout

        # Find result file
        result_pattern = f"result_*_{recipe_id}.json"
        start_time = time.time()

        while time.time() - start_time < timeout:
            result_files = list(self._outbox_path.glob(result_pattern))

            if result_files:
                result_path = result_files[0]
                try:
                    with open(result_path, "r", encoding="utf-8") as f:
                        result_data = json.load(f)

                    result = RecipeResult.from_dict(result_data)

                    # Clean up
                    if self._config.cleanup_files:
                        result_path.unlink()

                    return result

                except json.JSONDecodeError:
                    pass

            time.sleep(self._config.poll_interval)

        return None

    def check_bridge_status(self) -> dict[str, Any]:
        """Check if bridge server is running and responsive.

        Returns:
            Status dictionary
        """
        # Send ping recipe
        ping_steps = [
            RecipeStep(
                order=1,
                name="Ping",
                action="run_script",
                script="# Ping - do nothing",
            ),
        ]

        try:
            result = self.send_recipe(
                ping_steps,
                recipe_id="ping",
                timeout=5.0,
            )

            return {
                "status": "running",
                "responsive": True,
                "houdini_version": list(result.houdini_version) if result.houdini_version else None,
            }

        except TimeoutError:
            return {
                "status": "not_responding",
                "responsive": False,
            }
        except Exception as e:
            return {
                "status": "error",
                "responsive": False,
                "error": str(e),
            }

    def list_pending_recipes(self) -> list[str]:
        """List recipe IDs pending in inbox."""
        recipe_files = list(self._inbox_path.glob("recipe_*.json"))
        return [f.stem for f in recipe_files]

    def clear_inbox(self) -> int:
        """Clear all pending recipes from inbox.

        Returns:
            Number of files removed
        """
        count = 0
        for recipe_file in self._inbox_path.glob("recipe_*.json"):
            recipe_file.unlink()
            count += 1
        return count


# Convenience function
def send_recipe_to_houdini(
    steps: list[RecipeStep],
    context: dict[str, Any] | None = None,
    inbox_dir: str = "./data/inbox",
    outbox_dir: str = "./data/outbox",
    timeout: float = 30.0,
) -> RecipeResult:
    """Send a recipe to Houdini and wait for result.

    Convenience function for one-off recipe execution.

    Args:
        steps: List of recipe steps
        context: Optional execution context
        inbox_dir: Inbox directory
        outbox_dir: Outbox directory
        timeout: Timeout in seconds

    Returns:
        RecipeResult with execution outcome

    Raises:
        TimeoutError: If Houdini doesn't respond
    """
    client = HoudiniBridgeClient(
        inbox_dir=inbox_dir,
        outbox_dir=outbox_dir,
        timeout=timeout,
    )

    return client.send_recipe(steps, context)


# Convenience functions for common operations

def create_geometry_node(
    node_type: str,
    node_path: str,
    parameters: dict[str, Any] | None = None,
    timeout: float = 30.0,
) -> RecipeResult:
    """Create a single geometry node.

    Args:
        node_type: Type of node (geo, box, sphere, etc.)
        node_path: Path for the new node
        parameters: Optional parameters to set
        timeout: Execution timeout

    Returns:
        RecipeResult
    """
    steps = [
        RecipeStep(
            order=1,
            name=f"Create {node_type}",
            action="create_node",
            node_type=node_type,
            node_path=node_path,
        ),
    ]

    order = 2
    if parameters:
        for param, value in parameters.items():
            steps.append(
                RecipeStep(
                    order=order,
                    name=f"Set {param}",
                    action="set_parameter",
                    target_node=node_path,
                    parameter=param,
                    value=value,
                )
            )
            order += 1

    return send_recipe_to_houdini(steps, timeout=timeout)


def create_node_chain(
    network_path: str,
    node_types: list[str],
    prefix: str = "node",
    timeout: float = 30.0,
) -> RecipeResult:
    """Create a chain of connected nodes.

    Args:
        network_path: Parent network path (e.g., "/obj/geo1")
        node_types: List of node types to create
        prefix: Prefix for node names
        timeout: Execution timeout

    Returns:
        RecipeResult
    """
    steps = []
    node_paths = []

    for i, node_type in enumerate(node_types):
        node_name = f"{prefix}{i + 1}"
        node_path = f"{network_path}/{node_name}"
        node_paths.append(node_path)

        steps.append(
            RecipeStep(
                order=i * 2 + 1,
                name=f"Create {node_type}",
                action="create_node",
                node_type=node_type,
                node_path=node_path,
            )
        )

        # Connect to previous node
        if i > 0:
            steps.append(
                RecipeStep(
                    order=i * 2,
                    name=f"Connect {node_paths[i-1]} to {node_path}",
                    action="make_connection",
                    source_node=node_paths[i - 1],
                    target_node=node_path,
                )
            )

    return send_recipe_to_houdini(steps, timeout=timeout)