"""Recipe RAG Integration Module.

Provides a bridge between Recipe decomposition and RAG knowledge retrieval,
enabling structured context injection for LLM calls.

Key Components:
- RecipeKnowledge: Structured task decomposition
- RAGContext: Retrieved knowledge from RAG
- MergedContext: Combined recipe + RAG context
- RecipeRAGBridge: Main integration class

Usage:
    bridge = RecipeRAGBridge(max_context_tokens=10000)

    # Get recipe decomposition
    recipe_kn = decompose_task(query, domain="houdini", task_type="sop_chain")

    # Get RAG context
    rag_ctx = build_context(query, domain="houdini")

    # Merge and inject
    merged = bridge.merge_contexts(recipe_kn, rag_ctx, query)
    system_prompt = bridge.inject_into_system_message(base_system, merged)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
import re


class TaskType(str, Enum):
    """Types of tasks that can be decomposed."""

    HOUDINI_SOP_CHAIN = "houdini_sop_chain"
    HOUDINI_DOP_SIMULATION = "houdini_dop_simulation"
    HOUDINI_VEX_SCRIPT = "houdini_vex_script"
    HOUDINI_PDGRAPH = "houdini_pdgraph"
    TOUCHDESIGNER_NETWORK = "touchdesigner_network"
    TOUCHDESIGNER_CHOP = "touchdesigner_chop"
    TOUCHDESIGNER_TOP = "touchdesigner_top"
    TOUCHDESIGNER_DAT = "touchdesigner_dat"
    GENERAL_AUTOMATION = "general_automation"
    UNKNOWN = "unknown"


class ContextRequirement(str, Enum):
    """Context requirements for recipe steps."""

    HOUDINI_GEOMETRY_NODE = "houdini_geometry_node"
    HOUDINI_SOP = "houdini_sop"
    HOUDINI_DOP = "houdini_dop"
    HOUDINI_VEX = "houdini_vex"
    HOUDINI_EXPRESSIONS = "houdini_expressions"
    TOUCHDESIGNER_CHOP = "touchdesigner_chop"
    TOUCHDESIGNER_TOP = "touchdesigner_top"
    TOUCHDESIGNER_DAT = "touchdesigner_dat"
    TOUCHDESIGNER_PYTHON = "touchdesigner_python"
    GENERAL_PROGRAMMING = "general_programming"
    BRIDGE_CONNECTION = "bridge_connection"


@dataclass(slots=True)
class RecipeStep:
    """A single step in a recipe.

    Attributes:
        name: Human-readable step name
        action: Action to perform
        inputs: Required inputs
        outputs: Expected outputs
        context_keys: Required context/knowledge
        depends_on: Steps this depends on
        description: Detailed description
    """

    name: str
    action: str
    inputs: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    context_keys: list[str] = field(default_factory=list)
    depends_on: list[str] = field(default_factory=list)
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "action": self.action,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "context_keys": self.context_keys,
            "depends_on": self.depends_on,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RecipeStep":
        """Create from dictionary."""
        return cls(
            name=data["name"],
            action=data["action"],
            inputs=data.get("inputs", []),
            outputs=data.get("outputs", []),
            context_keys=data.get("context_keys", []),
            depends_on=data.get("depends_on", []),
            description=data.get("description", ""),
        )


@dataclass(slots=True)
class RecipeKnowledge:
    """Structured knowledge from recipe decomposition.

    Represents a task broken down into executable steps with
    dependencies and context requirements.

    Attributes:
        task_type: Type of task being performed
        decomposed_steps: List of RecipeStep objects
        dependencies: Step dependency mapping
        context_requirements: Required context/knowledge
        estimated_tokens: Estimated token count
        domain: Target domain
        confidence: Decomposition confidence
    """

    task_type: str
    decomposed_steps: list[RecipeStep] = field(default_factory=list)
    dependencies: dict[str, list[str]] = field(default_factory=dict)
    context_requirements: list[str] = field(default_factory=list)
    estimated_tokens: int = 0
    domain: str = ""
    confidence: float = 0.0

    @property
    def step_count(self) -> int:
        """Get number of steps."""
        return len(self.decomposed_steps)

    @property
    def has_dependencies(self) -> bool:
        """Check if there are dependencies."""
        return bool(self.dependencies)

    def get_step_by_name(self, name: str) -> RecipeStep | None:
        """Get a step by name.

        Args:
            name: Step name

        Returns:
            RecipeStep or None
        """
        for step in self.decomposed_steps:
            if step.name == name:
                return step
        return None

    def get_ordered_steps(self) -> list[RecipeStep]:
        """Get steps in dependency order.

        Handles circular dependencies by detecting cycles and breaking them.

        Returns:
            List of steps sorted by dependencies
        """
        if not self.dependencies:
            return self.decomposed_steps

        ordered: list[RecipeStep] = []
        added_names: set[str] = set()
        visiting: set[str] = set()  # Track currently visiting to detect cycles

        def add_step(step: RecipeStep) -> None:
            if step.name in added_names:
                return
            # Cycle detection - skip if already visiting this step
            if step.name in visiting:
                return

            visiting.add(step.name)

            # Add dependencies first
            for dep_name in step.depends_on:
                dep_step = self.get_step_by_name(dep_name)
                if dep_step and dep_name not in added_names:
                    add_step(dep_step)

            visiting.remove(step.name)
            ordered.append(step)
            added_names.add(step.name)

        for step in self.decomposed_steps:
            add_step(step)

        return ordered

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "task_type": self.task_type,
            "decomposed_steps": [s.to_dict() for s in self.decomposed_steps],
            "dependencies": self.dependencies,
            "context_requirements": self.context_requirements,
            "estimated_tokens": self.estimated_tokens,
            "domain": self.domain,
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RecipeKnowledge":
        """Create from dictionary."""
        steps = [RecipeStep.from_dict(s) for s in data.get("decomposed_steps", [])]
        return cls(
            task_type=data["task_type"],
            decomposed_steps=steps,
            dependencies=data.get("dependencies", {}),
            context_requirements=data.get("context_requirements", []),
            estimated_tokens=data.get("estimated_tokens", 0),
            domain=data.get("domain", ""),
            confidence=data.get("confidence", 0.0),
        )


@dataclass(slots=True)
class RetrievedDocument:
    """A retrieved document from RAG.

    Attributes:
        source: Document source
        content: Document content
        relevance: Relevance score
        context_keys: Related context keys
    """

    source: str
    content: str
    relevance: float = 0.0
    context_keys: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "source": self.source,
            "content": self.content,
            "relevance": self.relevance,
            "context_keys": self.context_keys,
        }


@dataclass(slots=True)
class RAGContext:
    """Context from RAG retrieval.

    Represents knowledge retrieved from a RAG system.

    Attributes:
        domain: Target domain
        retrieved_docs: List of retrieved documents
        query_interpretation: Semantic analysis of query
        confidence_score: Retrieval confidence
        total_tokens: Total tokens in documents
    """

    domain: str
    retrieved_docs: list[RetrievedDocument] = field(default_factory=list)
    query_interpretation: str = ""
    confidence_score: float = 0.0
    total_tokens: int = 0

    @property
    def doc_count(self) -> int:
        """Get number of documents."""
        return len(self.retrieved_docs)

    @property
    def sources(self) -> list[str]:
        """Get list of sources."""
        return [doc.source for doc in self.retrieved_docs]

    def get_docs_for_context(self, context_key: str) -> list[RetrievedDocument]:
        """Get documents matching a context key.

        Args:
            context_key: Context key to match

        Returns:
            List of matching documents
        """
        return [
            doc for doc in self.retrieved_docs
            if context_key in doc.context_keys
        ]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "domain": self.domain,
            "retrieved_docs": [d.to_dict() for d in self.retrieved_docs],
            "query_interpretation": self.query_interpretation,
            "confidence_score": self.confidence_score,
            "total_tokens": self.total_tokens,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RAGContext":
        """Create from dictionary."""
        docs = [RetrievedDocument(**d) for d in data.get("retrieved_docs", [])]
        return cls(
            domain=data["domain"],
            retrieved_docs=docs,
            query_interpretation=data.get("query_interpretation", ""),
            confidence_score=data.get("confidence_score", 0.0),
            total_tokens=data.get("total_tokens", 0),
        )


@dataclass(slots=True)
class MergedContext:
    """Merged context from recipe and RAG.

    Represents the combined knowledge ready for injection.

    Attributes:
        system_prompt: Enhanced system message
        recipe_knowledge_block: Formatted recipe steps
        rag_knowledge_block: Formatted retrieved docs
        execution_roadmap: Steps + mapped knowledge
        total_context_tokens: Token count for whole context
        step_knowledge_mapping: Mapping of steps to relevant docs
    """

    system_prompt: str = ""
    recipe_knowledge_block: str = ""
    rag_knowledge_block: str = ""
    execution_roadmap: str = ""
    total_context_tokens: int = 0
    step_knowledge_mapping: dict[str, list[str]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "system_prompt": self.system_prompt,
            "recipe_knowledge_block": self.recipe_knowledge_block,
            "rag_knowledge_block": self.rag_knowledge_block,
            "execution_roadmap": self.execution_roadmap,
            "total_context_tokens": self.total_context_tokens,
            "step_knowledge_mapping": self.step_knowledge_mapping,
        }


class RecipeRAGBridge:
    """Bridge between Recipe decomposition and RAG retrieval.

    Merges structured recipe knowledge with retrieved RAG documents
    and injects the combined context into LLM prompts.

    Example:
        bridge = RecipeRAGBridge(max_context_tokens=10000)

        recipe_kn = RecipeKnowledge(
            task_type="houdini_sop_chain",
            decomposed_steps=[
                RecipeStep(name="Create geometry", action="create_node", ...),
                RecipeStep(name="Add noise", action="add_sop", ...),
            ],
        )

        rag_ctx = RAGContext(
            domain="houdini",
            retrieved_docs=[
                RetrievedDocument(source="SideFX Docs", content="..."),
            ],
        )

        merged = bridge.merge_contexts(recipe_kn, rag_ctx, "Create a noise terrain")
        system = bridge.inject_into_system_message(base_system, merged)
    """

    def __init__(
        self,
        max_context_tokens: int = 10000,
        token_estimate_ratio: float = 4.0,  # chars per token
    ):
        """Initialize the bridge.

        Args:
            max_context_tokens: Maximum tokens for context
            token_estimate_ratio: Characters per token estimate
        """
        self.max_context_tokens = max_context_tokens
        self.token_estimate_ratio = token_estimate_ratio

    def merge_contexts(
        self,
        recipe_knowledge: RecipeKnowledge,
        rag_context: RAGContext,
        user_query: str,
    ) -> MergedContext:
        """Merge recipe and RAG contexts.

        Args:
            recipe_knowledge: Recipe decomposition
            rag_context: RAG retrieved context
            user_query: Original user query

        Returns:
            MergedContext with combined knowledge
        """
        # Format individual blocks
        recipe_block = self._format_recipe_block(recipe_knowledge)
        rag_block = self._format_rag_block(rag_context)

        # Build execution roadmap
        roadmap, mapping = self._build_execution_roadmap(
            recipe_knowledge,
            rag_context,
        )

        # Build system prompt
        system_prompt = self._build_system_prompt(
            recipe_block,
            rag_block,
            roadmap,
            user_query,
        )

        # Estimate tokens
        total_text = recipe_block + rag_block + roadmap + system_prompt
        estimated_tokens = int(len(total_text) / self.token_estimate_ratio)

        return MergedContext(
            system_prompt=system_prompt,
            recipe_knowledge_block=recipe_block,
            rag_knowledge_block=rag_block,
            execution_roadmap=roadmap,
            total_context_tokens=estimated_tokens,
            step_knowledge_mapping=mapping,
        )

    def inject_into_system_message(
        self,
        base_system: str,
        merged_context: MergedContext,
    ) -> str:
        """Inject merged context into system message.

        Args:
            base_system: Base system prompt
            merged_context: Merged context

        Returns:
            Enhanced system message
        """
        # Build the context section
        context_section = "\n\n" + "=" * 50 + "\n"
        context_section += "CONTEXT FOR TASK EXECUTION\n"
        context_section += "=" * 50 + "\n\n"

        if merged_context.recipe_knowledge_block:
            context_section += merged_context.recipe_knowledge_block
            context_section += "\n\n"

        if merged_context.rag_knowledge_block:
            context_section += merged_context.rag_knowledge_block
            context_section += "\n\n"

        if merged_context.execution_roadmap:
            context_section += merged_context.execution_roadmap

        # Inject into base system
        if "{CONTEXT}" in base_system:
            return base_system.replace("{CONTEXT}", context_section)
        else:
            # Append to end
            return base_system + "\n" + context_section

    def _format_recipe_block(self, recipe: RecipeKnowledge) -> str:
        """Format recipe knowledge as text block.

        Args:
            recipe: Recipe knowledge

        Returns:
            Formatted text block
        """
        lines = [
            "=== RECIPE KNOWLEDGE (Task Decomposition) ===",
            f"Task Type: {recipe.task_type}",
            f"Domain: {recipe.domain}",
            f"Estimated Steps: {recipe.step_count}",
            f"Confidence: {recipe.confidence:.2f}",
            "",
        ]

        if recipe.decomposed_steps:
            lines.append("STEP STRUCTURE:")
            for i, step in enumerate(recipe.get_ordered_steps(), 1):
                dep_str = ""
                if step.depends_on:
                    dep_str = f" [depends: {', '.join(step.depends_on)}]"
                lines.append(f"  {i}. {step.name}{dep_str}")

                if step.action:
                    lines.append(f"     Action: {step.action}")

                if step.context_keys:
                    lines.append(f"     Context needed: {', '.join(step.context_keys)}")

        if recipe.context_requirements:
            lines.append("")
            lines.append("CONTEXT REQUIREMENTS:")
            for req in recipe.context_requirements:
                lines.append(f"  - {req}")

        return "\n".join(lines)

    def _format_rag_block(self, rag: RAGContext) -> str:
        """Format RAG context as text block.

        Args:
            rag: RAG context

        Returns:
            Formatted text block
        """
        lines = [
            "=== RAG KNOWLEDGE (Retrieved Documents) ===",
            f"Domain: {rag.domain}",
            f"Documents Retrieved: {rag.doc_count}",
            f"Confidence: {rag.confidence_score:.2f}",
            "",
        ]

        if rag.query_interpretation:
            lines.append(f"Query Interpretation: {rag.query_interpretation}")
            lines.append("")

        if rag.retrieved_docs:
            lines.append("RETRIEVED DOCUMENTS:")
            lines.append("-" * 40)

            for i, doc in enumerate(rag.retrieved_docs, 1):
                lines.append(f"\n[{i}] Source: {doc.source}")
                lines.append(f"    Relevance: {doc.relevance:.2f}")

                # Truncate content if too long
                content = doc.content
                if len(content) > 500:
                    content = content[:500] + "..."

                lines.append(f"    Content: {content}")

        return "\n".join(lines)

    def _build_execution_roadmap(
        self,
        recipe: RecipeKnowledge,
        rag: RAGContext,
    ) -> tuple[str, dict[str, list[str]]]:
        """Build execution roadmap with knowledge mapping.

        Args:
            recipe: Recipe knowledge
            rag: RAG context

        Returns:
            Tuple of (roadmap text, step->docs mapping)
        """
        lines = [
            "=== EXECUTION ROADMAP ===",
            "Step-by-step execution with relevant knowledge:",
            "",
        ]

        mapping: dict[str, list[str]] = {}

        for i, step in enumerate(recipe.get_ordered_steps(), 1):
            lines.append(f"STEP {i}: {step.name}")
            lines.append(f"  Action: {step.action}")

            # Find relevant docs
            relevant_docs: list[str] = []
            for context_key in step.context_keys:
                matching_docs = rag.get_docs_for_context(context_key)
                for doc in matching_docs:
                    if doc.source not in relevant_docs:
                        relevant_docs.append(doc.source)

            if relevant_docs:
                lines.append(f"  Reference Knowledge: {relevant_docs}")
                mapping[step.name] = relevant_docs
            else:
                lines.append("  Reference Knowledge: [general domain knowledge]")
                mapping[step.name] = []

            if step.depends_on:
                lines.append(f"  Prerequisites: {', '.join(step.depends_on)}")

            lines.append("")

        return "\n".join(lines), mapping

    def _build_system_prompt(
        self,
        recipe_block: str,
        rag_block: str,
        roadmap: str,
        user_query: str,
    ) -> str:
        """Build enhanced system prompt.

        Args:
            recipe_block: Recipe knowledge block
            rag_block: RAG knowledge block
            roadmap: Execution roadmap
            user_query: User query

        Returns:
            Enhanced system prompt
        """
        return f"""You are an AI assistant with access to structured task knowledge.

{recipe_block}

{rag_block}

{roadmap}

USER QUERY: {user_query}

Execute the task following the recipe steps in order, using the retrieved knowledge as reference.
Ensure each step's prerequisites are satisfied before execution.
"""


# ============================================================================
# Helper Functions for Integration
# ============================================================================

def decompose_task(
    query: str,
    domain: str = "",
    task_type: str | TaskType = TaskType.UNKNOWN,
) -> RecipeKnowledge:
    """Decompose a task into structured recipe steps.

    This is a heuristic-based decomposition that can be enhanced
    with LLM-based decomposition for complex tasks.

    Args:
        query: User query/task
        domain: Target domain (houdini, touchdesigner, etc.)
        task_type: Task type hint

    Returns:
        RecipeKnowledge with decomposed steps
    """
    task_type_value = task_type.value if isinstance(task_type, TaskType) else task_type

    # Heuristic decomposition based on keywords
    steps: list[RecipeStep] = []
    context_reqs: list[str] = []

    query_lower = query.lower()

    # Houdini SOP chain detection
    if domain == "houdini" or "houdini" in query_lower or "sop" in query_lower:
        steps.extend(_decompose_houdini_task(query, query_lower))
        context_reqs.extend([ContextRequirement.HOUDINI_GEOMETRY_NODE.value,
                            ContextRequirement.HOUDINI_SOP.value])

    # TouchDesigner detection
    elif domain == "touchdesigner" or "touchdesigner" in query_lower or "top" in query_lower or "chop" in query_lower:
        steps.extend(_decompose_touchdesigner_task(query, query_lower))
        context_reqs.extend([ContextRequirement.TOUCHDESIGNER_TOP.value])

    # Generic decomposition
    else:
        steps.extend(_decompose_generic_task(query))
        context_reqs.extend([ContextRequirement.GENERAL_PROGRAMMING.value])

    # Build dependencies
    dependencies: dict[str, list[str]] = {}
    for i, step in enumerate(steps):
        if step.depends_on:
            dependencies[step.name] = step.depends_on

    # Estimate tokens
    estimated = sum(len(step.name) + len(step.action) for step in steps) * 2

    return RecipeKnowledge(
        task_type=task_type_value,
        decomposed_steps=steps,
        dependencies=dependencies,
        context_requirements=context_reqs,
        estimated_tokens=estimated,
        domain=domain,
        confidence=0.8 if steps else 0.3,
    )


def _decompose_houdini_task(query: str, query_lower: str) -> list[RecipeStep]:
    """Decompose a Houdini task.

    Args:
        query: Original query
        query_lower: Lowercase query

    Returns:
        List of RecipeStep
    """
    steps = []

    # Common Houdini workflow
    steps.append(RecipeStep(
        name="Create geometry container",
        action="geometry node creation",
        inputs=["network_context"],
        outputs=["geometry_ref"],
        context_keys=[ContextRequirement.HOUDINI_GEOMETRY_NODE.value],
        depends_on=[],
        description="Create a Geometry node to contain the SOP network",
    ))

    if "noise" in query_lower or "terrain" in query_lower or "procedural" in query_lower:
        steps.append(RecipeStep(
            name="Add noise/procedural operators",
            action="add SOP operators for procedural generation",
            inputs=["geometry_ref"],
            outputs=["sop_chain"],
            context_keys=[ContextRequirement.HOUDINI_SOP.value, ContextRequirement.HOUDINI_VEX.value],
            depends_on=["Create geometry container"],
            description="Add SOP operators for noise and procedural effects",
        ))

    if "instancing" in query_lower or "copy" in query_lower:
        steps.append(RecipeStep(
            name="Setup instancing",
            action="configure copy/instance SOPs",
            inputs=["sop_chain"],
            outputs=["instanced_geometry"],
            context_keys=[ContextRequirement.HOUDINI_SOP.value],
            depends_on=["Add noise/procedural operators"] if len(steps) > 1 else ["Create geometry container"],
            description="Setup instancing with copy SOP",
        ))

    steps.append(RecipeStep(
        name="Configure output",
        action="set display/render flags",
        inputs=["sop_chain"] if len(steps) > 1 else ["geometry_ref"],
        outputs=["final_output"],
        context_keys=[ContextRequirement.HOUDINI_SOP.value],
        depends_on=[steps[-1].name] if steps else [],
        description="Set display flag and configure output",
    ))

    return steps


def _decompose_touchdesigner_task(query: str, query_lower: str) -> list[RecipeStep]:
    """Decompose a TouchDesigner task.

    Args:
        query: Original query
        query_lower: Lowercase query

    Returns:
        List of RecipeStep
    """
    steps = []

    # Determine operator type
    if "top" in query_lower or "texture" in query_lower or "image" in query_lower:
        op_type = "TOP"
        context_key = ContextRequirement.TOUCHDESIGNER_TOP.value
    elif "chop" in query_lower or "channel" in query_lower or "audio" in query_lower:
        op_type = "CHOP"
        context_key = ContextRequirement.TOUCHDESIGNER_CHOP.value
    else:
        op_type = "TOP"
        context_key = ContextRequirement.TOUCHDESIGNER_TOP.value

    steps.append(RecipeStep(
        name=f"Create {op_type} network",
        action=f"create {op_type} container and operators",
        inputs=["network_context"],
        outputs=["operator_ref"],
        context_keys=[context_key],
        depends_on=[],
        description=f"Create a {op_type} network with required operators",
    ))

    if "noise" in query_lower:
        steps.append(RecipeStep(
            name="Configure noise parameters",
            action="set noise operator parameters",
            inputs=["operator_ref"],
            outputs=["configured_operator"],
            context_keys=[context_key],
            depends_on=[f"Create {op_type} network"],
            description="Configure noise parameters (resolution, type, period)",
        ))

    steps.append(RecipeStep(
        name="Verify output",
        action="verify operator output",
        inputs=["configured_operator"] if len(steps) > 1 else ["operator_ref"],
        outputs=["verified_output"],
        context_keys=[context_key],
        depends_on=[steps[-1].name] if steps else [],
        description="Verify the operator network is working correctly",
    ))

    return steps


def _decompose_generic_task(query: str) -> list[RecipeStep]:
    """Decompose a generic task.

    Args:
        query: Original query

    Returns:
        List of RecipeStep
    """
    return [
        RecipeStep(
            name="Analyze requirements",
            action="analyze task requirements",
            inputs=["task_description"],
            outputs=["requirements"],
            context_keys=[ContextRequirement.GENERAL_PROGRAMMING.value],
            depends_on=[],
            description="Analyze what the task requires",
        ),
        RecipeStep(
            name="Execute task",
            action="perform task execution",
            inputs=["requirements"],
            outputs=["result"],
            context_keys=[ContextRequirement.GENERAL_PROGRAMMING.value],
            depends_on=["Analyze requirements"],
            description="Execute the main task",
        ),
        RecipeStep(
            name="Verify result",
            action="verify execution result",
            inputs=["result"],
            outputs=["verified_result"],
            context_keys=[ContextRequirement.GENERAL_PROGRAMMING.value],
            depends_on=["Execute task"],
            description="Verify the result is correct",
        ),
    ]


def build_context(
    query: str,
    domain: str = "",
    context_type: str = "knowledge_retrieval",
) -> RAGContext:
    """Build RAG context for a query.

    This is a placeholder that returns mock context.
    In production, this would query an actual RAG system.

    Args:
        query: User query
        domain: Target domain
        context_type: Type of context to retrieve

    Returns:
        RAGContext with retrieved documents
    """
    docs: list[RetrievedDocument] = []

    # Mock documents based on domain
    if domain == "houdini" or "houdini" in query.lower():
        docs.extend([
            RetrievedDocument(
                source="SideFX Docs: Geometry Node",
                content="The Geometry node creates a network of SOP operators. It is the primary container for procedural geometry creation in Houdini.",
                relevance=0.95,
                context_keys=[ContextRequirement.HOUDINI_GEOMETRY_NODE.value],
            ),
            RetrievedDocument(
                source="Houdini VEX: Noise Functions",
                content="Use pnoise() for Perlin noise, snoise() for simplex noise. These can be used in VEX expressions within SOP nodes.",
                relevance=0.85,
                context_keys=[ContextRequirement.HOUDINI_VEX.value],
            ),
        ])

    if domain == "touchdesigner" or "touchdesigner" in query.lower() or "top" in query.lower():
        docs.extend([
            RetrievedDocument(
                source="Derivative Docs: TOP Operators",
                content="TOP operators process textures and images. The Noise TOP generates procedural noise patterns with customizable parameters.",
                relevance=0.90,
                context_keys=[ContextRequirement.TOUCHDESIGNER_TOP.value],
            ),
        ])

    # Interpret query
    interpretation = f"User wants to: {query}"

    return RAGContext(
        domain=domain,
        retrieved_docs=docs,
        query_interpretation=interpretation,
        confidence_score=0.85 if docs else 0.3,
        total_tokens=sum(len(d.content) for d in docs) // 4,
    )


# ============================================================================
# Example / Test Function
# ============================================================================

def example_integration() -> dict[str, Any]:
    """Run an example integration for testing.

    Returns:
        Dictionary with integration results
    """
    print("=" * 60)
    print("Recipe RAG Integration Example")
    print("=" * 60)

    # Create bridge
    bridge = RecipeRAGBridge(max_context_tokens=10000)

    # Example query
    query = "Create a procedural noise terrain in Houdini using SOPs"

    print(f"\nQuery: {query}")
    print("-" * 60)

    # Decompose task
    recipe_kn = decompose_task(query, domain="houdini", task_type=TaskType.HOUDINI_SOP_CHAIN)

    print(f"\nRecipe decomposed into {recipe_kn.step_count} steps")
    for step in recipe_kn.decomposed_steps:
        print(f"  - {step.name}: {step.action}")

    # Build RAG context
    rag_ctx = build_context(query, domain="houdini")

    print(f"\nRAG retrieved {rag_ctx.doc_count} documents")
    for doc in rag_ctx.retrieved_docs:
        print(f"  - {doc.source} (relevance: {doc.relevance:.2f})")

    # Merge contexts
    merged = bridge.merge_contexts(recipe_kn, rag_ctx, query)

    print("\n" + "=" * 60)
    print(merged.recipe_knowledge_block)
    print("\n" + merged.rag_knowledge_block)
    print("\n" + merged.execution_roadmap)

    print(f"\nTotal context tokens: {merged.total_context_tokens}")

    return {
        "recipe": recipe_kn.to_dict(),
        "rag": rag_ctx.to_dict(),
        "merged": merged.to_dict(),
    }


if __name__ == "__main__":
    example_integration()