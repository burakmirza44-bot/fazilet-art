"""Houdini Bridge Server.

Monitors file-based inbox, executes recipes via HOM API,
writes results to file-based outbox.

This server runs inside Houdini (called from HOM Python environment).
"""

from __future__ import annotations

import json
import os
import sys
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

# Handle import of models
try:
    from app.domains.houdini.bridge.models import (
        HoudiniBridgeConfig,
        RecipeRequest,
        RecipeResult,
        RecipeStep,
        StepResult,
    )
except ImportError:
    # When running inside Houdini, use relative imports
    from models import (
        HoudiniBridgeConfig,
        RecipeRequest,
        RecipeResult,
        RecipeStep,
        StepResult,
    )


class HoudiniBridgeServer:
    """Bridge server for Houdini recipe execution.

    Monitors file-based inbox, executes recipes via HOM API,
    writes results to file-based outbox.

    Usage:
        # From inside Houdini Python
        server = HoudiniBridgeServer()
        server.start()

        # Or via start_houdini_bridge() convenience function
    """

    def __init__(
        self,
        config: HoudiniBridgeConfig | None = None,
        inbox_dir: str | None = None,
        outbox_dir: str | None = None,
        poll_interval: float = 1.0,
        timeout: float = 30.0,
    ) -> None:
        """Initialize the bridge server.

        Args:
            config: Optional configuration object
            inbox_dir: Override inbox directory
            outbox_dir: Override outbox directory
            poll_interval: Override poll interval
            timeout: Override timeout
        """
        self._config = config or HoudiniBridgeConfig()

        # Allow parameter overrides
        if inbox_dir:
            self._config.inbox_dir = inbox_dir
        if outbox_dir:
            self._config.outbox_dir = outbox_dir
        if poll_interval != 1.0:
            self._config.poll_interval = poll_interval
        if timeout != 30.0:
            self._config.timeout = timeout

        self._inbox_path = Path(self._config.inbox_dir)
        self._outbox_path = Path(self._config.outbox_dir)
        self._running = False
        self._processed_files: set[str] = set()
        self._stats = {
            "recipes_processed": 0,
            "recipes_succeeded": 0,
            "recipes_failed": 0,
            "total_execution_time_ms": 0.0,
        }

        # Callbacks
        self._on_recipe_start: Callable[[RecipeRequest], None] | None = None
        self._on_recipe_complete: Callable[[RecipeResult], None] | None = None
        self._on_step_complete: Callable[[StepResult], None] | None = None
        self._on_error: Callable[[Exception], None] | None = None

        # Create directories
        self._inbox_path.mkdir(parents=True, exist_ok=True)
        self._outbox_path.mkdir(parents=True, exist_ok=True)

        self._log("INFO", f"Initialized")
        self._log("INFO", f"  Inbox: {self._inbox_path}")
        self._log("INFO", f"  Outbox: {self._outbox_path}")

    def _log(self, level: str, message: str) -> None:
        """Log a message."""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(f"[{timestamp}] [HOUDINI BRIDGE] [{level}] {message}")

    @property
    def stats(self) -> dict[str, Any]:
        """Get server statistics."""
        return self._stats.copy()

    @property
    def is_running(self) -> bool:
        """Check if server is running."""
        return self._running

    def set_callbacks(
        self,
        on_recipe_start: Callable[[RecipeRequest], None] | None = None,
        on_recipe_complete: Callable[[RecipeResult], None] | None = None,
        on_step_complete: Callable[[StepResult], None] | None = None,
        on_error: Callable[[Exception], None] | None = None,
    ) -> None:
        """Set event callbacks."""
        self._on_recipe_start = on_recipe_start
        self._on_recipe_complete = on_recipe_complete
        self._on_step_complete = on_step_complete
        self._on_error = on_error

    def start(self) -> None:
        """Start monitoring inbox for recipes."""
        self._running = True
        self._log("INFO", f"Started (poll interval: {self._config.poll_interval}s)")

        try:
            self._poll_loop()
        except KeyboardInterrupt:
            self._log("INFO", "Interrupted by user")
        except Exception as e:
            self._log("ERROR", f"Fatal error: {e}")
            traceback.print_exc()
            if self._on_error:
                self._on_error(e)
        finally:
            self.stop()

    def stop(self) -> None:
        """Stop monitoring."""
        self._running = False
        self._log("INFO", "Stopped")

    def _poll_loop(self) -> None:
        """Main polling loop."""
        while self._running:
            try:
                self._process_pending_recipes()
                time.sleep(self._config.poll_interval)
            except Exception as e:
                self._log("ERROR", f"Poll loop error: {e}")
                time.sleep(self._config.poll_interval)

    def _process_pending_recipes(self) -> None:
        """Process all pending recipe files."""
        recipe_files = list(self._inbox_path.glob("recipe_*.json"))

        for recipe_file in recipe_files:
            # Skip already processed files
            if recipe_file.name in self._processed_files:
                continue

            self._log("INFO", f"Processing: {recipe_file.name}")
            self._handle_recipe_file(recipe_file)

            # Mark as processed
            self._processed_files.add(recipe_file.name)

            # Clean up if configured
            if not self._config.keep_processed_files:
                try:
                    recipe_file.unlink()
                except Exception as e:
                    self._log("WARN", f"Could not remove {recipe_file.name}: {e}")

    def _handle_recipe_file(self, recipe_file: Path) -> None:
        """Process a single recipe file."""
        start_time = time.perf_counter()
        result: RecipeResult | None = None

        try:
            # Read and parse recipe
            with open(recipe_file, "r", encoding="utf-8") as f:
                recipe_data = json.load(f)

            request = RecipeRequest.from_dict(recipe_data)

            self._log("INFO", f"Recipe: {request.recipe_id}")
            self._log("INFO", f"Steps: {len(request.recipe_steps)}")

            # Callback
            if self._on_recipe_start:
                self._on_recipe_start(request)

            # Execute recipe
            result = self._execute_recipe(request)

        except json.JSONDecodeError as e:
            self._log("ERROR", f"Invalid JSON: {e}")
            result = RecipeResult(
                recipe_id="unknown",
                success=False,
                errors=[{"error": f"Invalid JSON: {str(e)}"}],
            )
        except Exception as e:
            self._log("ERROR", f"Recipe error: {e}")
            traceback.print_exc()
            result = RecipeResult(
                recipe_id="unknown",
                success=False,
                errors=[{"error": str(e), "traceback": traceback.format_exc()}],
            )

        # Add metadata
        if result:
            result.execution_time_ms = (time.perf_counter() - start_time) * 1000
            result.timestamp = datetime.now().isoformat()

            # Try to get Houdini version
            try:
                import hou

                result.houdini_version = tuple(hou.applicationVersion())
            except (ImportError, AttributeError):
                pass

            # Update stats
            self._stats["recipes_processed"] += 1
            self._stats["total_execution_time_ms"] += result.execution_time_ms
            if result.success:
                self._stats["recipes_succeeded"] += 1
            else:
                self._stats["recipes_failed"] += 1

            # Callback
            if self._on_recipe_complete:
                self._on_recipe_complete(result)

        # Write result
        self._write_result(recipe_file, result)

    def _execute_recipe(self, request: RecipeRequest) -> RecipeResult:
        """Execute a recipe in Houdini.

        Args:
            request: Recipe request to execute

        Returns:
            RecipeResult with execution outcome
        """
        result = RecipeResult(recipe_id=request.recipe_id)

        # Execution context tracking
        exec_context = {
            "created_nodes": [],
            "parameters_set": [],
            "connections_made": [],
            "scripts_executed": [],
        }

        # Get target network from context
        network_path = request.context.get("network", "/obj")

        # Validate network exists
        try:
            import hou

            network_node = hou.node(network_path)
            if not network_node:
                result.errors.append({
                    "error": f"Network {network_path} not found",
                    "phase": "initialization",
                })
                return result
        except ImportError:
            result.errors.append({
                "error": "Houdini (hou) module not available - running outside Houdini?",
                "phase": "initialization",
            })
            return result
        except Exception as e:
            result.errors.append({
                "error": f"Cannot access network: {str(e)}",
                "phase": "initialization",
            })
            return result

        # Execute each step
        for step in request.recipe_steps:
            step_result = self._execute_step(step, network_node, exec_context)

            result.step_results.append(step_result)

            if step_result.success:
                result.steps_executed.append(step.name)
            else:
                result.errors.append({
                    "step": step.name,
                    "error": step_result.error,
                })

                # Stop on error unless continue_on_error
                if not step.continue_on_error:
                    break

        # Set final result
        result.success = len(result.errors) == 0
        result.output = {
            "created_nodes": exec_context["created_nodes"],
            "parameters_set": exec_context["parameters_set"],
            "connections_made": exec_context["connections_made"],
            "scripts_executed": exec_context["scripts_executed"],
            "network": network_path,
        }

        return result

    def _execute_step(
        self,
        step: RecipeStep,
        network_node: Any,
        exec_context: dict[str, Any],
    ) -> StepResult:
        """Execute a single recipe step."""
        start_time = time.perf_counter()
        result = StepResult(step_name=step.name)

        try:
            action = step.action.lower()

            if action == "create_node":
                step_result = self._execute_create_node(step, network_node, exec_context)
                result.success = step_result.get("success", False)
                result.output = step_result.get("output", {})
                result.error = step_result.get("error")

            elif action == "set_parameter":
                step_result = self._execute_set_parameter(step, network_node, exec_context)
                result.success = step_result.get("success", False)
                result.output = step_result.get("output", {})
                result.error = step_result.get("error")

            elif action == "make_connection":
                step_result = self._execute_make_connection(step, network_node, exec_context)
                result.success = step_result.get("success", False)
                result.output = step_result.get("output", {})
                result.error = step_result.get("error")

            elif action == "run_script":
                step_result = self._execute_run_script(step, network_node, exec_context)
                result.success = step_result.get("success", False)
                result.output = step_result.get("output", {})
                result.error = step_result.get("error")

            elif action == "delete_node":
                step_result = self._execute_delete_node(step, network_node, exec_context)
                result.success = step_result.get("success", False)
                result.output = step_result.get("output", {})
                result.error = step_result.get("error")

            else:
                result.success = False
                result.error = f"Unknown action: {action}"

        except Exception as e:
            result.success = False
            result.error = str(e)
            self._log("ERROR", f"Step '{step.name}' failed: {e}")
            traceback.print_exc()

        result.execution_time_ms = (time.perf_counter() - start_time) * 1000

        # Callback
        if self._on_step_complete:
            self._on_step_complete(result)

        return result

    def _execute_create_node(
        self,
        step: RecipeStep,
        network_node: Any,
        exec_context: dict[str, Any],
    ) -> dict[str, Any]:
        """Create a node in the network."""
        import hou

        try:
            node_type = step.node_type
            if not node_type:
                return {"success": False, "error": "Missing node_type"}

            node_path = step.node_path or f"auto_node_{int(time.time() * 1000) % 10000}"

            # Determine parent and node name
            if "/" in node_path:
                # Absolute path provided
                parent_path = str(Path(node_path).parent)
                node_name = Path(node_path).name
                parent_node = hou.node(parent_path)

                if not parent_node:
                    return {"success": False, "error": f"Parent node not found: {parent_path}"}
            else:
                # Relative to network
                parent_node = network_node
                node_name = node_path

            # Check if node already exists
            existing = parent_node.node(node_name)
            if existing:
                self._log("WARN", f"Node already exists: {existing.path()}, using existing")
                exec_context["created_nodes"].append(existing.path())
                return {
                    "success": True,
                    "output": {
                        "created_node": existing.path(),
                        "node_type": node_type,
                        "existed": True,
                    },
                }

            # Create the node
            new_node = parent_node.createNode(node_type, node_name)

            if not new_node:
                return {"success": False, "error": f"Failed to create {node_type} node"}

            node_full_path = new_node.path()
            exec_context["created_nodes"].append(node_full_path)

            self._log("INFO", f"Created: {node_full_path}")

            return {
                "success": True,
                "output": {
                    "created_node": node_full_path,
                    "node_type": node_type,
                },
            }

        except Exception as e:
            return {"success": False, "error": f"Create node error: {str(e)}"}

    def _execute_set_parameter(
        self,
        step: RecipeStep,
        network_node: Any,
        exec_context: dict[str, Any],
    ) -> dict[str, Any]:
        """Set a parameter on a node."""
        import hou

        try:
            target_node_name = step.target_node
            param_name = step.parameter
            param_value = step.value

            if not target_node_name or not param_name or param_value is None:
                return {"success": False, "error": "Missing target_node, parameter, or value"}

            # Get target node
            if "/" in target_node_name:
                target_node = hou.node(target_node_name)
            else:
                target_node = network_node.node(target_node_name)

            if not target_node:
                return {"success": False, "error": f"Node not found: {target_node_name}"}

            # Get and set parameter
            parm = target_node.parm(param_name)
            if not parm:
                return {"success": False, "error": f"Parameter not found: {param_name}"}

            # Set value based on type
            if isinstance(param_value, (int, float)):
                parm.set(param_value)
            elif isinstance(param_value, str):
                parm.set(param_value)
            elif isinstance(param_value, (list, tuple)):
                # Multi-component parameter
                parm.set(tuple(param_value))
            else:
                parm.set(str(param_value))

            exec_context["parameters_set"].append({
                "node": target_node.path(),
                "parameter": param_name,
                "value": param_value,
            })

            self._log("INFO", f"Set: {target_node.path()}.{param_name} = {param_value}")

            return {
                "success": True,
                "output": {
                    "node": target_node.path(),
                    "parameter": param_name,
                    "value_set": param_value,
                },
            }

        except Exception as e:
            return {"success": False, "error": f"Set parameter error: {str(e)}"}

    def _execute_make_connection(
        self,
        step: RecipeStep,
        network_node: Any,
        exec_context: dict[str, Any],
    ) -> dict[str, Any]:
        """Connect two nodes."""
        import hou

        try:
            source_node_name = step.source_node
            target_node_name = step.target_node

            if not source_node_name or not target_node_name:
                return {"success": False, "error": "Missing source_node or target_node"}

            # Get nodes
            if "/" in source_node_name:
                source_node = hou.node(source_node_name)
            else:
                source_node = network_node.node(source_node_name)

            if "/" in target_node_name:
                target_node = hou.node(target_node_name)
            else:
                target_node = network_node.node(target_node_name)

            if not source_node:
                return {"success": False, "error": f"Source node not found: {source_node_name}"}
            if not target_node:
                return {"success": False, "error": f"Target node not found: {target_node_name}"}

            # Make connection
            source_out = step.source_output
            target_in = step.target_input

            target_node.setInput(target_in, source_node, source_out)

            exec_context["connections_made"].append({
                "source": f"{source_node.path()}:{source_out}",
                "target": f"{target_node.path()}:{target_in}",
            })

            self._log("INFO", f"Connected: {source_node.path()} -> {target_node.path()}")

            return {
                "success": True,
                "output": {
                    "source": source_node.path(),
                    "target": target_node.path(),
                    "source_output": source_out,
                    "target_input": target_in,
                },
            }

        except Exception as e:
            return {"success": False, "error": f"Connection error: {str(e)}"}

    def _execute_run_script(
        self,
        step: RecipeStep,
        network_node: Any,
        exec_context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a Python script in Houdini context."""
        try:
            script = step.script
            if not script:
                return {"success": False, "error": "Missing script"}

            # Create execution context
            script_globals = {
                "hou": __import__("hou"),
                "network": network_node,
                "step": step,
            }

            # Execute script
            exec(script, script_globals)

            exec_context["scripts_executed"].append({
                "step": step.name,
                "script_preview": script[:100] + "..." if len(script) > 100 else script,
            })

            self._log("INFO", f"Executed script: {step.name}")

            return {"success": True, "output": {"script_executed": True}}

        except Exception as e:
            return {"success": False, "error": f"Script error: {str(e)}"}

    def _execute_delete_node(
        self,
        step: RecipeStep,
        network_node: Any,
        exec_context: dict[str, Any],
    ) -> dict[str, Any]:
        """Delete a node from the network."""
        import hou

        try:
            node_path = step.node_path or step.target_node
            if not node_path:
                return {"success": False, "error": "Missing node_path or target_node"}

            # Get node
            if "/" in node_path:
                node = hou.node(node_path)
            else:
                node = network_node.node(node_path)

            if not node:
                return {"success": False, "error": f"Node not found: {node_path}"}

            node_path = node.path()
            node.destroy()

            self._log("INFO", f"Deleted: {node_path}")

            return {"success": True, "output": {"deleted_node": node_path}}

        except Exception as e:
            return {"success": False, "error": f"Delete error: {str(e)}"}

    def _write_result(self, recipe_file: Path, result: RecipeResult | None) -> None:
        """Write result to outbox."""
        if not result:
            return

        try:
            # Generate output filename
            recipe_name = recipe_file.stem
            result_name = recipe_name.replace("recipe_", "result_")
            result_file = self._outbox_path / f"{result_name}.json"

            # Write result
            with open(result_file, "w", encoding="utf-8") as f:
                json.dump(result.to_dict(), f, indent=2)

            self._log("INFO", f"Result written: {result_file.name}")

        except Exception as e:
            self._log("ERROR", f"Failed to write result: {e}")


def start_houdini_bridge(
    inbox_dir: str | None = None,
    outbox_dir: str | None = None,
) -> None:
    """Start the Houdini bridge server.

    This is the main entry point for starting the bridge from Houdini.

    Usage:
        # From Houdini Python Shell:
        from houdini_bridge import start_houdini_bridge
        start_houdini_bridge()

        # Or with custom paths:
        start_houdini_bridge(inbox_dir="/path/to/inbox", outbox_dir="/path/to/outbox")
    """
    import hou

    # Get paths from environment or use defaults
    if not inbox_dir:
        inbox_dir = hou.getenv("HOUDINI_BRIDGE_INBOX") or "./data/inbox"
    if not outbox_dir:
        outbox_dir = hou.getenv("HOUDINI_BRIDGE_OUTBOX") or "./data/outbox"

    server = HoudiniBridgeServer(
        inbox_dir=inbox_dir,
        outbox_dir=outbox_dir,
    )

    server.start()


def start_houdini_bridge_threaded(
    inbox_dir: str | None = None,
    outbox_dir: str | None = None,
) -> Any:
    """Start the bridge server in a background thread.

    Returns the thread object for management.

    Usage:
        import threading
        thread = start_houdini_bridge_threaded()
        # Bridge runs in background while Houdini is active
        # thread.join() to stop
    """
    import threading

    def run_server():
        start_houdini_bridge(inbox_dir, outbox_dir)

    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()

    return thread