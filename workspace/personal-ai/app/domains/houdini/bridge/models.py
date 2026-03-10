"""Houdini Bridge Models.

Data models for recipe requests, results, and step definitions.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class RecipeStep:
    """A single step in a Houdini recipe.

    Step types:
    - create_node: Create a new node
    - set_parameter: Set a parameter value
    - make_connection: Connect two nodes
    - run_script: Execute HOM/Python code
    - delete_node: Delete a node
    """

    order: int
    name: str
    action: str  # "create_node", "set_parameter", "make_connection", "run_script", "delete_node"

    # For create_node
    node_type: str | None = None
    node_path: str | None = None

    # For set_parameter
    target_node: str | None = None
    parameter: str | None = None
    value: Any = None

    # For make_connection
    source_node: str | None = None
    source_output: int = 0
    target_input: int = 0

    # For run_script
    script: str | None = None

    # Additional options
    continue_on_error: bool = False
    verify: bool = False
    timeout: float = 10.0

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "order": self.order,
            "name": self.name,
            "action": self.action,
            "node_type": self.node_type,
            "node_path": self.node_path,
            "target_node": self.target_node,
            "parameter": self.parameter,
            "value": self.value,
            "source_node": self.source_node,
            "source_output": self.source_output,
            "target_input": self.target_input,
            "script": self.script,
            "continue_on_error": self.continue_on_error,
            "verify": self.verify,
            "timeout": self.timeout,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RecipeStep:
        """Deserialize from dictionary."""
        return cls(
            order=data.get("order", 0),
            name=data.get("name", ""),
            action=data.get("action", ""),
            node_type=data.get("node_type"),
            node_path=data.get("node_path"),
            target_node=data.get("target_node"),
            parameter=data.get("parameter"),
            value=data.get("value"),
            source_node=data.get("source_node"),
            source_output=data.get("source_output", 0),
            target_input=data.get("target_input", 0),
            script=data.get("script"),
            continue_on_error=data.get("continue_on_error", False),
            verify=data.get("verify", False),
            timeout=data.get("timeout", 10.0),
        )


@dataclass
class RecipeRequest:
    """A request to execute a recipe in Houdini."""

    recipe_id: str
    recipe_steps: list[RecipeStep]
    context: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    timeout: float = 30.0
    priority: str = "normal"  # "low", "normal", "high"

    def __post_init__(self):
        if not self.recipe_id:
            self.recipe_id = f"recipe_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "recipe_id": self.recipe_id,
            "recipe_steps": [s.to_dict() for s in self.recipe_steps],
            "context": self.context,
            "timestamp": self.timestamp,
            "timeout": self.timeout,
            "priority": self.priority,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RecipeRequest:
        """Deserialize from dictionary."""
        steps = [RecipeStep.from_dict(s) for s in data.get("recipe_steps", [])]
        return cls(
            recipe_id=data.get("recipe_id", ""),
            recipe_steps=steps,
            context=data.get("context", {}),
            timestamp=data.get("timestamp", datetime.now().isoformat()),
            timeout=data.get("timeout", 30.0),
            priority=data.get("priority", "normal"),
        )


@dataclass
class StepResult:
    """Result of executing a single step."""

    step_name: str
    success: bool = False
    output: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    execution_time_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "step_name": self.step_name,
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "execution_time_ms": self.execution_time_ms,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StepResult:
        """Deserialize from dictionary."""
        return cls(
            step_name=data.get("step_name", ""),
            success=data.get("success", False),
            output=data.get("output", {}),
            error=data.get("error"),
            execution_time_ms=data.get("execution_time_ms", 0.0),
        )


@dataclass
class RecipeResult:
    """Result of executing a recipe in Houdini."""

    recipe_id: str
    success: bool = False
    output: dict[str, Any] = field(default_factory=dict)
    steps_executed: list[str] = field(default_factory=list)
    step_results: list[StepResult] = field(default_factory=list)
    errors: list[dict[str, Any]] = field(default_factory=list)
    execution_time_ms: float = 0.0
    houdini_version: tuple[int, ...] = field(default_factory=tuple)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "recipe_id": self.recipe_id,
            "success": self.success,
            "output": self.output,
            "steps_executed": self.steps_executed,
            "step_results": [s.to_dict() for s in self.step_results],
            "errors": self.errors,
            "execution_time_ms": self.execution_time_ms,
            "houdini_version": list(self.houdini_version) if self.houdini_version else [],
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RecipeResult:
        """Deserialize from dictionary."""
        step_results = [StepResult.from_dict(s) for s in data.get("step_results", [])]
        houdini_version = tuple(data.get("houdini_version", []))
        return cls(
            recipe_id=data.get("recipe_id", ""),
            success=data.get("success", False),
            output=data.get("output", {}),
            steps_executed=data.get("steps_executed", []),
            step_results=step_results,
            errors=data.get("errors", []),
            execution_time_ms=data.get("execution_time_ms", 0.0),
            houdini_version=houdini_version,
            timestamp=data.get("timestamp", datetime.now().isoformat()),
        )


@dataclass
class HoudiniBridgeConfig:
    """Configuration for the Houdini bridge server."""

    inbox_dir: str = "./data/inbox"
    outbox_dir: str = "./data/outbox"
    poll_interval: float = 1.0
    timeout: float = 30.0
    max_concurrent_recipes: int = 1
    keep_processed_files: bool = False
    log_level: str = "INFO"

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "inbox_dir": self.inbox_dir,
            "outbox_dir": self.outbox_dir,
            "poll_interval": self.poll_interval,
            "timeout": self.timeout,
            "max_concurrent_recipes": self.max_concurrent_recipes,
            "keep_processed_files": self.keep_processed_files,
            "log_level": self.log_level,
        }


# Factory functions for common step types

def create_node_step(
    order: int,
    node_type: str,
    node_path: str,
    name: str | None = None,
) -> RecipeStep:
    """Create a node creation step."""
    return RecipeStep(
        order=order,
        name=name or f"Create {node_type} node",
        action="create_node",
        node_type=node_type,
        node_path=node_path,
    )


def set_parameter_step(
    order: int,
    target_node: str,
    parameter: str,
    value: Any,
    name: str | None = None,
) -> RecipeStep:
    """Create a parameter setting step."""
    return RecipeStep(
        order=order,
        name=name or f"Set {parameter} on {target_node}",
        action="set_parameter",
        target_node=target_node,
        parameter=parameter,
        value=value,
    )


def connect_nodes_step(
    order: int,
    source_node: str,
    target_node: str,
    source_output: int = 0,
    target_input: int = 0,
    name: str | None = None,
) -> RecipeStep:
    """Create a node connection step."""
    return RecipeStep(
        order=order,
        name=name or f"Connect {source_node} to {target_node}",
        action="make_connection",
        source_node=source_node,
        target_node=target_node,
        source_output=source_output,
        target_input=target_input,
    )


def run_script_step(
    order: int,
    script: str,
    name: str | None = None,
) -> RecipeStep:
    """Create a script execution step."""
    return RecipeStep(
        order=order,
        name=name or "Run script",
        action="run_script",
        script=script,
    )