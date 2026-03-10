"""Tests for Recipe RAG Integration Module.

Tests the bridge between Recipe decomposition and RAG knowledge retrieval.
"""

import pytest

from app.agent_core.recipe_rag_integration import (
    ContextRequirement,
    MergedContext,
    RAGContext,
    RecipeKnowledge,
    RecipeRAGBridge,
    RecipeStep,
    RetrievedDocument,
    TaskType,
    build_context,
    decompose_task,
    example_integration,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def sample_recipe_step():
    """Create a sample recipe step."""
    return RecipeStep(
        name="Create geometry",
        action="create_node",
        inputs=["network_context"],
        outputs=["geometry_ref"],
        context_keys=["houdini_geometry_node"],
        depends_on=[],
        description="Create a Geometry node",
    )


@pytest.fixture
def sample_retrieved_doc():
    """Create a sample retrieved document."""
    return RetrievedDocument(
        source="SideFX Docs",
        content="The Geometry node creates a network of SOP operators.",
        relevance=0.95,
        context_keys=["houdini_geometry_node"],
    )


@pytest.fixture
def sample_recipe_knowledge(sample_recipe_step):
    """Create sample recipe knowledge."""
    return RecipeKnowledge(
        task_type="houdini_sop_chain",
        decomposed_steps=[
            sample_recipe_step,
            RecipeStep(
                name="Add noise",
                action="add_sop",
                context_keys=["houdini_sop", "houdini_vex"],
                depends_on=["Create geometry"],
            ),
        ],
        dependencies={"Add noise": ["Create geometry"]},
        context_requirements=["houdini_geometry_node", "houdini_sop"],
        domain="houdini",
        confidence=0.85,
    )


@pytest.fixture
def sample_rag_context(sample_retrieved_doc):
    """Create sample RAG context."""
    return RAGContext(
        domain="houdini",
        retrieved_docs=[
            sample_retrieved_doc,
            RetrievedDocument(
                source="Houdini VEX Docs",
                content="Use pnoise() for Perlin noise.",
                relevance=0.80,
                context_keys=["houdini_vex"],
            ),
        ],
        query_interpretation="Create procedural geometry",
        confidence_score=0.90,
    )


@pytest.fixture
def bridge():
    """Create a RecipeRAGBridge."""
    return RecipeRAGBridge(max_context_tokens=10000)


# ============================================================================
# RecipeStep Tests
# ============================================================================

class TestRecipeStep:
    """Tests for RecipeStep dataclass."""

    def test_create_step(self, sample_recipe_step):
        """Test creating a recipe step."""
        assert sample_recipe_step.name == "Create geometry"
        assert sample_recipe_step.action == "create_node"
        assert len(sample_recipe_step.inputs) == 1
        assert len(sample_recipe_step.outputs) == 1

    def test_step_serialization(self, sample_recipe_step):
        """Test step serialization roundtrip."""
        data = sample_recipe_step.to_dict()
        restored = RecipeStep.from_dict(data)

        assert restored.name == sample_recipe_step.name
        assert restored.action == sample_recipe_step.action
        assert restored.inputs == sample_recipe_step.inputs


# ============================================================================
# RecipeKnowledge Tests
# ============================================================================

class TestRecipeKnowledge:
    """Tests for RecipeKnowledge dataclass."""

    def test_create_knowledge(self, sample_recipe_knowledge):
        """Test creating recipe knowledge."""
        assert sample_recipe_knowledge.task_type == "houdini_sop_chain"
        assert sample_recipe_knowledge.step_count == 2
        assert sample_recipe_knowledge.has_dependencies

    def test_get_step_by_name(self, sample_recipe_knowledge):
        """Test getting step by name."""
        step = sample_recipe_knowledge.get_step_by_name("Create geometry")

        assert step is not None
        assert step.name == "Create geometry"

    def test_get_step_not_found(self, sample_recipe_knowledge):
        """Test getting non-existent step."""
        step = sample_recipe_knowledge.get_step_by_name("NonExistent")
        assert step is None

    def test_ordered_steps(self, sample_recipe_knowledge):
        """Test getting ordered steps."""
        ordered = sample_recipe_knowledge.get_ordered_steps()

        assert len(ordered) == 2
        # "Create geometry" should come before "Add noise"
        assert ordered[0].name == "Create geometry"

    def test_knowledge_serialization(self, sample_recipe_knowledge):
        """Test knowledge serialization roundtrip."""
        data = sample_recipe_knowledge.to_dict()
        restored = RecipeKnowledge.from_dict(data)

        assert restored.task_type == sample_recipe_knowledge.task_type
        assert len(restored.decomposed_steps) == len(sample_recipe_knowledge.decomposed_steps)


# ============================================================================
# RAGContext Tests
# ============================================================================

class TestRAGContext:
    """Tests for RAGContext dataclass."""

    def test_create_context(self, sample_rag_context):
        """Test creating RAG context."""
        assert sample_rag_context.domain == "houdini"
        assert sample_rag_context.doc_count == 2
        assert len(sample_rag_context.sources) == 2

    def test_get_docs_for_context(self, sample_rag_context):
        """Test getting docs for a context key."""
        docs = sample_rag_context.get_docs_for_context("houdini_geometry_node")

        assert len(docs) == 1
        assert docs[0].source == "SideFX Docs"

    def test_context_serialization(self, sample_rag_context):
        """Test context serialization roundtrip."""
        data = sample_rag_context.to_dict()
        restored = RAGContext.from_dict(data)

        assert restored.domain == sample_rag_context.domain
        assert len(restored.retrieved_docs) == len(sample_rag_context.retrieved_docs)


# ============================================================================
# RecipeRAGBridge Tests
# ============================================================================

class TestRecipeRAGBridge:
    """Tests for RecipeRAGBridge class."""

    def test_create_bridge(self, bridge):
        """Test creating bridge."""
        assert bridge.max_context_tokens == 10000

    def test_merge_contexts(self, bridge, sample_recipe_knowledge, sample_rag_context):
        """Test merging contexts."""
        merged = bridge.merge_contexts(
            sample_recipe_knowledge,
            sample_rag_context,
            "Create procedural geometry",
        )

        assert isinstance(merged, MergedContext)
        assert len(merged.system_prompt) > 0
        assert len(merged.recipe_knowledge_block) > 0
        assert len(merged.rag_knowledge_block) > 0
        assert len(merged.execution_roadmap) > 0
        assert merged.total_context_tokens > 0

    def test_inject_into_system_message(self, bridge, sample_recipe_knowledge, sample_rag_context):
        """Test injecting into system message."""
        merged = bridge.merge_contexts(
            sample_recipe_knowledge,
            sample_rag_context,
            "Create geometry",
        )

        base_system = "You are an AI assistant.\n{CONTEXT}"
        enhanced = bridge.inject_into_system_message(base_system, merged)

        assert "RECIPE KNOWLEDGE" in enhanced
        assert "RAG KNOWLEDGE" in enhanced
        assert "{CONTEXT}" not in enhanced

    def test_inject_without_placeholder(self, bridge, sample_recipe_knowledge, sample_rag_context):
        """Test injection without placeholder."""
        merged = bridge.merge_contexts(
            sample_recipe_knowledge,
            sample_rag_context,
            "Create geometry",
        )

        base_system = "You are an AI assistant."
        enhanced = bridge.inject_into_system_message(base_system, merged)

        # Should append context
        assert len(enhanced) > len(base_system)
        assert "RECIPE KNOWLEDGE" in enhanced

    def test_step_knowledge_mapping(self, bridge, sample_recipe_knowledge, sample_rag_context):
        """Test step-knowledge mapping is created."""
        merged = bridge.merge_contexts(
            sample_recipe_knowledge,
            sample_rag_context,
            "Create geometry",
        )

        assert len(merged.step_knowledge_mapping) > 0

        # "Create geometry" step should map to "SideFX Docs"
        geometry_docs = merged.step_knowledge_mapping.get("Create geometry", [])
        assert "SideFX Docs" in geometry_docs


# ============================================================================
# decompose_task Tests
# ============================================================================

class TestDecomposeTask:
    """Tests for decompose_task function."""

    def test_decompose_houdini_task(self):
        """Test decomposing Houdini task."""
        recipe = decompose_task(
            "Create a noise terrain in Houdini",
            domain="houdini",
            task_type=TaskType.HOUDINI_SOP_CHAIN,
        )

        assert recipe.task_type == "houdini_sop_chain"
        assert recipe.domain == "houdini"
        assert recipe.step_count >= 2

    def test_decompose_touchdesigner_task(self):
        """Test decomposing TouchDesigner task."""
        recipe = decompose_task(
            "Create a noise TOP",
            domain="touchdesigner",
            task_type=TaskType.TOUCHDESIGNER_TOP,
        )

        assert recipe.domain == "touchdesigner"
        assert recipe.step_count >= 2

    def test_decompose_generic_task(self):
        """Test decomposing generic task."""
        recipe = decompose_task(
            "Do something",
            domain="",
            task_type=TaskType.UNKNOWN,
        )

        assert recipe.step_count >= 2

    def test_decompose_with_noise_keyword(self):
        """Test decomposition detects noise keyword."""
        recipe = decompose_task(
            "Create noise terrain in Houdini",
            domain="houdini",
        )

        # Should have noise-related step
        step_names = [s.name.lower() for s in recipe.decomposed_steps]
        assert any("noise" in name or "procedural" in name for name in step_names)


# ============================================================================
# build_context Tests
# ============================================================================

class TestBuildContext:
    """Tests for build_context function."""

    def test_build_houdini_context(self):
        """Test building Houdini context."""
        context = build_context(
            "Create geometry",
            domain="houdini",
        )

        assert context.domain == "houdini"
        assert context.doc_count > 0

    def test_build_touchdesigner_context(self):
        """Test building TouchDesigner context."""
        context = build_context(
            "Create noise TOP",
            domain="touchdesigner",
        )

        assert context.domain == "touchdesigner"
        assert context.doc_count > 0

    def test_build_context_with_sources(self):
        """Test context has source list."""
        context = build_context(
            "Create geometry",
            domain="houdini",
        )

        assert len(context.sources) > 0


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Integration tests for the full flow."""

    def test_full_flow_houdini(self, bridge):
        """Test full integration flow for Houdini."""
        query = "Create a procedural noise terrain in Houdini using SOPs"

        # Decompose
        recipe = decompose_task(query, domain="houdini", task_type=TaskType.HOUDINI_SOP_CHAIN)

        # Get RAG context
        rag = build_context(query, domain="houdini")

        # Merge
        merged = bridge.merge_contexts(recipe, rag, query)

        # Inject
        system = bridge.inject_into_system_message("You are an AI.", merged)

        assert len(system) > 0
        assert "houdini" in system.lower()
        assert recipe.step_count >= 2

    def test_full_flow_touchdesigner(self, bridge):
        """Test full integration flow for TouchDesigner."""
        query = "Create a noise TOP with parameters"

        # Decompose
        recipe = decompose_task(query, domain="touchdesigner", task_type=TaskType.TOUCHDESIGNER_TOP)

        # Get RAG context
        rag = build_context(query, domain="touchdesigner")

        # Merge
        merged = bridge.merge_contexts(recipe, rag, query)

        assert len(merged.system_prompt) > 0
        assert "touchdesigner" in merged.system_prompt.lower()

    def test_example_integration(self):
        """Test the example integration function."""
        result = example_integration()

        assert "recipe" in result
        assert "rag" in result
        assert "merged" in result

        assert result["recipe"]["task_type"] == "houdini_sop_chain"
        assert result["rag"]["domain"] == "houdini"


# ============================================================================
# Edge Case Tests
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_recipe(self, bridge):
        """Test handling empty recipe."""
        recipe = RecipeKnowledge(task_type="unknown")
        rag = RAGContext(domain="unknown")

        merged = bridge.merge_contexts(recipe, rag, "test")

        # Should still produce valid output
        assert len(merged.system_prompt) > 0

    def test_empty_rag(self, bridge, sample_recipe_knowledge):
        """Test handling empty RAG context."""
        rag = RAGContext(domain="houdini")

        merged = bridge.merge_contexts(sample_recipe_knowledge, rag, "test")

        assert len(merged.system_prompt) > 0
        assert "RECIPE KNOWLEDGE" in merged.recipe_knowledge_block

    def test_token_limit(self):
        """Test token limit is respected."""
        bridge = RecipeRAGBridge(max_context_tokens=100)

        recipe = RecipeKnowledge(
            task_type="test",
            decomposed_steps=[
                RecipeStep(name=f"Step {i}", action=f"action_{i}")
                for i in range(20)
            ],
        )

        rag = RAGContext(
            domain="test",
            retrieved_docs=[
                RetrievedDocument(
                    source=f"Doc {i}",
                    content="x" * 1000,
                )
                for i in range(10)
            ],
        )

        merged = bridge.merge_contexts(recipe, rag, "test")

        # Should produce some output even with large content
        assert len(merged.system_prompt) > 0

    def test_circular_dependencies(self):
        """Test handling of dependency ordering."""
        step_a = RecipeStep(name="A", action="a", depends_on=["B"])
        step_b = RecipeStep(name="B", action="b", depends_on=["A"])

        recipe = RecipeKnowledge(
            task_type="test",
            decomposed_steps=[step_a, step_b],
            dependencies={"A": ["B"], "B": ["A"]},
        )

        ordered = recipe.get_ordered_steps()

        # Should still return all steps
        assert len(ordered) == 2