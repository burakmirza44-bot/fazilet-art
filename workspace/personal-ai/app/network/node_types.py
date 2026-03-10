"""Node Type Implementations for Claude Network.

Provides executors for each node type: Agent, Tool, Memory, Router, Decomposer.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any

from app.network.context import NetworkContext
from app.network.models import (
    NetworkNode,
    NodeResult,
    NodeStatus,
    NodeType,
)


class NodeExecutor(ABC):
    """Abstract base class for node executors."""

    @abstractmethod
    async def execute(
        self,
        node: NetworkNode,
        inputs: dict[str, Any],
        context: NetworkContext,
    ) -> NodeResult:
        """Execute the node.

        Args:
            node: Node to execute
            inputs: Input data for the node
            context: Execution context

        Returns:
            NodeResult with execution outcome
        """
        pass


class AgentNodeExecutor(NodeExecutor):
    """Executor for agent nodes.

    Routes to appropriate LLM provider and executes with tools.
    """

    def __init__(self, provider_router: Any | None = None):
        """Initialize the agent executor.

        Args:
            provider_router: Optional provider router for LLM selection
        """
        self._provider_router = provider_router

    async def execute(
        self,
        node: NetworkNode,
        inputs: dict[str, Any],
        context: NetworkContext,
    ) -> NodeResult:
        """Execute an agent node.

        Args:
            node: Agent node configuration
            inputs: Input data
            context: Execution context

        Returns:
            NodeResult with agent response
        """
        start_time = time.perf_counter()
        result = NodeResult(node_id=node.node_id)

        try:
            # Get configuration
            provider = node.config.get("provider", "claude")
            system_prompt = node.config.get("system_prompt", "")
            tools = node.config.get("tools", [])
            model = node.config.get("model")
            temperature = node.config.get("temperature", 0.7)

            # Build prompt from inputs
            prompt = self._build_prompt(inputs, context)

            # Query memory for relevant patterns
            memory_patterns = context.query_memory(prompt, "success")

            # Enhance prompt with memory context
            if memory_patterns:
                memory_context = self._format_memory_patterns(memory_patterns)
                prompt = f"{memory_context}\n\n{prompt}"

            # Execute based on provider
            output = await self._execute_with_provider(
                provider=provider,
                system_prompt=system_prompt,
                prompt=prompt,
                tools=tools,
                model=model,
                temperature=temperature,
                context=context,
            )

            result.status = NodeStatus.COMPLETED
            result.outputs = {
                "output": output.get("text", ""),
                "structured": output.get("structured"),
            }
            result.execution_time_ms = (time.perf_counter() - start_time) * 1000

            # Save to memory
            context.save_to_memory(
                query=prompt[:200],  # Truncate for storage
                success=True,
                result_data={
                    "node_id": node.node_id,
                    "provider": provider,
                    "output_preview": output.get("text", "")[:100],
                },
            )

        except Exception as e:
            result.status = NodeStatus.FAILED
            result.error = str(e)
            result.error_details = {"exception_type": type(e).__name__}
            result.execution_time_ms = (time.perf_counter() - start_time) * 1000

            context.record_error(node.node_id, str(e), {"inputs": inputs})

        return result

    def _build_prompt(self, inputs: dict[str, Any], context: NetworkContext) -> str:
        """Build prompt from inputs and context."""
        parts = []

        # Add main input
        if "input" in inputs:
            parts.append(str(inputs["input"]))

        # Add any additional context variables
        domain = context.domain
        if domain:
            parts.append(f"\nDomain: {domain}")

        return "\n".join(parts)

    def _format_memory_patterns(self, patterns: list[dict]) -> str:
        """Format memory patterns for prompt injection."""
        if not patterns:
            return ""

        formatted = "Relevant past experiences:\n"
        for i, pattern in enumerate(patterns[:3], 1):
            desc = pattern.get("description", pattern.get("query", ""))
            formatted += f"{i}. {desc}\n"

        return formatted

    async def _execute_with_provider(
        self,
        provider: str,
        system_prompt: str,
        prompt: str,
        tools: list[str],
        model: str | None,
        temperature: float,
        context: NetworkContext,
    ) -> dict[str, Any]:
        """Execute with specific provider.

        Args:
            provider: Provider name (claude, ollama, gemini)
            system_prompt: System prompt
            prompt: User prompt
            tools: Available tools
            model: Optional model override
            temperature: Temperature setting
            context: Execution context

        Returns:
            Output dictionary with text and structured data
        """
        # Try to use actual provider integration
        if provider == "claude":
            return await self._execute_claude(
                system_prompt, prompt, tools, model, temperature
            )
        elif provider == "ollama":
            return await self._execute_ollama(
                system_prompt, prompt, tools, model, temperature
            )
        elif provider == "gemini":
            return await self._execute_gemini(
                system_prompt, prompt, tools, model, temperature
            )
        else:
            # Fallback to simulated response
            return {
                "text": f"[Simulated {provider} response] Based on the input, here is the analysis and recommendations.",
                "structured": None,
            }

    async def _execute_claude(
        self,
        system_prompt: str,
        prompt: str,
        tools: list[str],
        model: str | None,
        temperature: float,
    ) -> dict[str, Any]:
        """Execute with Claude API."""
        try:
            import anthropic

            client = anthropic.Anthropic()
            model_id = model or "claude-sonnet-4-20250514"

            message = client.messages.create(
                model=model_id,
                max_tokens=4096,
                system=system_prompt,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
            )

            text = "".join(
                block.text for block in message.content
                if hasattr(block, "text")
            )

            return {"text": text, "structured": None}

        except ImportError:
            return {
                "text": "[Claude API not available - simulated response]",
                "structured": None,
            }

    async def _execute_ollama(
        self,
        system_prompt: str,
        prompt: str,
        tools: list[str],
        model: str | None,
        temperature: float,
    ) -> dict[str, Any]:
        """Execute with Ollama."""
        try:
            import ollama

            model_id = model or "llama3.2"

            response = ollama.chat(
                model=model_id,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
            )

            return {
                "text": response.get("message", {}).get("content", ""),
                "structured": None,
            }

        except ImportError:
            return {
                "text": "[Ollama not available - simulated response]",
                "structured": None,
            }

    async def _execute_gemini(
        self,
        system_prompt: str,
        prompt: str,
        tools: list[str],
        model: str | None,
        temperature: float,
    ) -> dict[str, Any]:
        """Execute with Gemini."""
        try:
            import google.generativeai as genai

            model_id = model or "gemini-pro"
            genai.configure()

            model_instance = genai.GenerativeModel(
                model_name=model_id,
                system_instruction=system_prompt,
            )

            response = model_instance.generate_content(prompt)

            return {
                "text": response.text,
                "structured": None,
            }

        except ImportError:
            return {
                "text": "[Gemini API not available - simulated response]",
                "structured": None,
            }


class ToolNodeExecutor(NodeExecutor):
    """Executor for tool nodes.

    Executes tools with input validation and error handling.
    """

    def __init__(self, tool_registry: dict[str, Any] | None = None):
        """Initialize the tool executor.

        Args:
            tool_registry: Optional registry of available tools
        """
        self._tool_registry = tool_registry or {}

    def register_tool(self, name: str, tool_fn: Any) -> None:
        """Register a tool."""
        self._tool_registry[name] = tool_fn

    async def execute(
        self,
        node: NetworkNode,
        inputs: dict[str, Any],
        context: NetworkContext,
    ) -> NodeResult:
        """Execute a tool node.

        Args:
            node: Tool node configuration
            inputs: Input parameters
            context: Execution context

        Returns:
            NodeResult with tool output
        """
        start_time = time.perf_counter()
        result = NodeResult(node_id=node.node_id)

        try:
            tool_name = node.config.get("tool_name")
            if not tool_name:
                raise ValueError("Tool node missing 'tool_name' configuration")

            # Get tool function
            tool_fn = self._tool_registry.get(tool_name)
            if not tool_fn:
                # Try to find in context
                tool_fn = context.get_variable(f"tool_{tool_name}")

            if not tool_fn:
                raise ValueError(f"Tool '{tool_name}' not found in registry")

            # Get parameters
            params = inputs.get("params", inputs)

            # Execute tool
            if callable(tool_fn):
                tool_result = tool_fn(**params) if isinstance(params, dict) else tool_fn(params)
            else:
                raise ValueError(f"Tool '{tool_name}' is not callable")

            result.status = NodeStatus.COMPLETED
            result.outputs = {"result": tool_result}
            result.execution_time_ms = (time.perf_counter() - start_time) * 1000

        except Exception as e:
            result.status = NodeStatus.FAILED
            result.error = str(e)
            result.error_details = {"exception_type": type(e).__name__}
            result.execution_time_ms = (time.perf_counter() - start_time) * 1000

            context.record_error(node.node_id, str(e))

        return result


class MemoryNodeExecutor(NodeExecutor):
    """Executor for memory nodes.

    Queries and stores patterns in the memory system.
    """

    def __init__(self, memory_adapter: Any | None = None):
        """Initialize the memory executor.

        Args:
            memory_adapter: Optional memory adapter for storage
        """
        self._memory_adapter = memory_adapter

    async def execute(
        self,
        node: NetworkNode,
        inputs: dict[str, Any],
        context: NetworkContext,
    ) -> NodeResult:
        """Execute a memory node.

        Args:
            node: Memory node configuration
            inputs: Query input
            context: Execution context

        Returns:
            NodeResult with retrieved patterns
        """
        start_time = time.perf_counter()
        result = NodeResult(node_id=node.node_id)

        try:
            query_type = node.config.get("query_type", "success_patterns")
            max_results = node.config.get("max_results", 5)

            # Get query from inputs
            query = inputs.get("query", inputs.get("input", ""))

            # Query memory
            patterns = context.query_memory(query, query_type.replace("_patterns", ""))
            patterns = patterns[:max_results]

            # Build context from patterns
            memory_context = self._build_context(patterns, query_type)

            result.status = NodeStatus.COMPLETED
            result.outputs = {
                "patterns": patterns,
                "context": memory_context,
            }
            result.execution_time_ms = (time.perf_counter() - start_time) * 1000

        except Exception as e:
            result.status = NodeStatus.FAILED
            result.error = str(e)
            result.error_details = {"exception_type": type(e).__name__}
            result.execution_time_ms = (time.perf_counter() - start_time) * 1000

            context.record_error(node.node_id, str(e))

        return result

    def _build_context(self, patterns: list[dict], query_type: str) -> dict[str, Any]:
        """Build context dictionary from patterns."""
        return {
            "pattern_count": len(patterns),
            "pattern_type": query_type,
            "summaries": [
                p.get("description", p.get("query", ""))[:100]
                for p in patterns
            ],
        }


class RouterNodeExecutor(NodeExecutor):
    """Executor for router nodes.

    Routes tasks to appropriate domain experts.
    """

    def __init__(self, domain_router: Any | None = None):
        """Initialize the router executor.

        Args:
            domain_router: Optional domain router
        """
        self._domain_router = domain_router

    async def execute(
        self,
        node: NetworkNode,
        inputs: dict[str, Any],
        context: NetworkContext,
    ) -> NodeResult:
        """Execute a router node.

        Args:
            node: Router node configuration
            inputs: Task input
            context: Execution context

        Returns:
            NodeResult with routing decision
        """
        start_time = time.perf_counter()
        result = NodeResult(node_id=node.node_id)

        try:
            domains = node.config.get("domains", node.capabilities)
            strategy = node.config.get("routing_strategy", "first_match")

            # Get task from inputs
            task = inputs.get("task", inputs.get("input", ""))

            # Import and use domain router
            from app.network.routers import DomainRouter, create_router

            router = self._domain_router
            if router is None:
                router = create_router(domains=domains) if domains else DomainRouter()

            # Make routing decision
            decision = router.route(task, {"domain": context.domain})

            # Set routing variables in context
            context.set_variable("domain", decision.domain)
            context.set_variable("confidence", decision.confidence)

            result.status = NodeStatus.COMPLETED
            result.outputs = {
                "domain": decision.domain,
                "confidence": decision.confidence,
                "alternatives": decision.alternative_domains,
                "reasoning": decision.reasoning,
            }
            result.execution_time_ms = (time.perf_counter() - start_time) * 1000

        except Exception as e:
            result.status = NodeStatus.FAILED
            result.error = str(e)
            result.error_details = {"exception_type": type(e).__name__}
            result.execution_time_ms = (time.perf_counter() - start_time) * 1000

            context.record_error(node.node_id, str(e))

        return result


class DecomposerNodeExecutor(NodeExecutor):
    """Executor for decomposer nodes.

    Breaks down tasks into subtasks with dependency tracking.
    """

    def __init__(self, decomposition_strategy: Any | None = None):
        """Initialize the decomposer executor.

        Args:
            decomposition_strategy: Optional decomposition strategy
        """
        self._strategy = decomposition_strategy

    async def execute(
        self,
        node: NetworkNode,
        inputs: dict[str, Any],
        context: NetworkContext,
    ) -> NodeResult:
        """Execute a decomposer node.

        Args:
            node: Decomposer node configuration
            inputs: Task input
            context: Execution context

        Returns:
            NodeResult with subtasks
        """
        start_time = time.perf_counter()
        result = NodeResult(node_id=node.node_id)

        try:
            max_subtasks = node.config.get("max_subtasks", 5)
            strategy = node.config.get("strategy", "sequential")

            # Get task from inputs
            task = inputs.get("task", inputs.get("input", ""))

            # Decompose task
            subtasks, dependencies = self._decompose(
                task=task,
                max_subtasks=max_subtasks,
                strategy=strategy,
                context=context,
            )

            result.status = NodeStatus.COMPLETED
            result.outputs = {
                "subtasks": subtasks,
                "dependencies": dependencies,
            }
            result.execution_time_ms = (time.perf_counter() - start_time) * 1000

        except Exception as e:
            result.status = NodeStatus.FAILED
            result.error = str(e)
            result.error_details = {"exception_type": type(e).__name__}
            result.execution_time_ms = (time.perf_counter() - start_time) * 1000

            context.record_error(node.node_id, str(e))

        return result

    def _decompose(
        self,
        task: str,
        max_subtasks: int,
        strategy: str,
        context: NetworkContext,
    ) -> tuple[list[dict], dict[str, list[str]]]:
        """Decompose a task into subtasks.

        Args:
            task: Task description
            max_subtasks: Maximum number of subtasks
            strategy: Decomposition strategy
            context: Execution context

        Returns:
            Tuple of (subtasks, dependencies)
        """
        # Simple heuristic-based decomposition
        # In a real implementation, this would use an LLM

        subtasks = []
        dependencies: dict[str, list[str]] = {}

        # Split by common delimiters
        parts = task.replace("; ", ";").replace(". ", ".").split(";")
        parts = [p.strip() for p in parts if p.strip()]

        # If no clear split, try sentences
        if len(parts) <= 1:
            parts = task.split(".")
            parts = [p.strip() for p in parts if p.strip()]

        # Create subtasks
        for i, part in enumerate(parts[:max_subtasks]):
            subtask_id = f"subtask_{i}"

            subtasks.append({
                "id": subtask_id,
                "description": part,
                "order": i,
            })

            # Create dependencies based on strategy
            if strategy == "sequential" and i > 0:
                dependencies[subtask_id] = [f"subtask_{i-1}"]
            else:
                dependencies[subtask_id] = []

        return subtasks, dependencies


# Registry of node executors
NODE_EXECUTORS: dict[NodeType, type[NodeExecutor]] = {
    NodeType.AGENT: AgentNodeExecutor,
    NodeType.TOOL: ToolNodeExecutor,
    NodeType.MEMORY: MemoryNodeExecutor,
    NodeType.ROUTER: RouterNodeExecutor,
    NodeType.DECOMPOSER: DecomposerNodeExecutor,
}


def get_executor(node_type: NodeType, **kwargs: Any) -> NodeExecutor:
    """Get an executor for a node type.

    Args:
        node_type: Type of node
        **kwargs: Arguments for executor initialization

    Returns:
        NodeExecutor instance
    """
    executor_class = NODE_EXECUTORS.get(node_type)
    if executor_class is None:
        raise ValueError(f"No executor for node type: {node_type}")

    return executor_class(**kwargs)