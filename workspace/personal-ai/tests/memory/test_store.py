"""Unit tests for MemoryStore and retrieval methods."""

import pytest

from app.memory import (
    MemoryItem,
    MemoryItemBuilder,
    MemoryStore,
    create_retriever,
    create_validator,
)
from app.memory.models import create_recipe, create_technique
from app.memory.retrieval import ValidationManager


def create_test_item(
    item_id: str = "test",
    content: str = "Test content",
    domain: str = "general",
    confidence: float = 0.5,
    knowledge_type: str | None = None,
    validation_status: str = "unvalidated",
    key_concepts: tuple[str, ...] = (),
    use_count: int = 0,
    successful_uses: int = 0,
    related_items: tuple[str, ...] = (),
    conflicting_items: tuple[str, ...] = (),
    provenance_fingerprint: str | None = None,
) -> MemoryItem:
    """Helper to create test items."""
    return MemoryItem(
        id=item_id,
        content=content,
        created_at="2024-01-01",
        domain=domain,
        confidence=confidence,
        knowledge_type=knowledge_type,
        validation_status=validation_status,
        key_concepts=key_concepts,
        use_count=use_count,
        successful_uses=successful_uses,
        related_items=related_items,
        conflicting_items=conflicting_items,
        provenance_fingerprint=provenance_fingerprint,
    )


class TestMemoryStore:
    """Tests for MemoryStore."""

    def test_create_store(self):
        """Test creating a store."""
        store = MemoryStore()
        assert store.count == 0

    def test_add_item(self):
        """Test adding an item."""
        store = MemoryStore()
        item = create_test_item("item1")

        item_id = store.add(item)
        assert item_id == "item1"
        assert store.count == 1
        assert store.get("item1") == item

    def test_get_nonexistent(self):
        """Test getting nonexistent item."""
        store = MemoryStore()
        assert store.get("nonexistent") is None

    def test_update_item(self):
        """Test updating an item."""
        store = MemoryStore()
        store.add(create_test_item("item1", content="Original"))

        updated = create_test_item("item1", content="Updated")
        result = store.update("item1", updated)

        assert result is True
        assert store.get("item1").content == "Updated"

    def test_delete_item(self):
        """Test deleting an item."""
        store = MemoryStore()
        store.add(create_test_item("item1"))

        result = store.delete("item1")
        assert result is True
        assert store.count == 0
        assert store.get("item1") is None

    def test_iterate_items(self):
        """Test iterating over items."""
        store = MemoryStore()
        store.add(create_test_item("item1"))
        store.add(create_test_item("item2"))

        items = list(store)
        assert len(items) == 2


class TestMemoryStoreIndexes:
    """Tests for index functionality."""

    def test_knowledge_type_index(self):
        """Test knowledge type index."""
        store = MemoryStore()
        store.add(create_test_item("r1", knowledge_type="recipe"))
        store.add(create_test_item("r2", knowledge_type="recipe"))
        store.add(create_test_item("t1", knowledge_type="technique"))

        recipes = store.retrieve_by_knowledge_type("recipe")
        assert len(recipes) == 2

        techniques = store.retrieve_by_knowledge_type("technique")
        assert len(techniques) == 1

    def test_domain_index(self):
        """Test domain index."""
        store = MemoryStore()
        store.add(create_test_item("h1", domain="houdini"))
        store.add(create_test_item("h2", domain="houdini"))
        store.add(create_test_item("t1", domain="touchdesigner"))

        houdini_items = store.retrieve_by_domain("houdini")
        assert len(houdini_items) == 2

    def test_confidence_index(self):
        """Test confidence range queries."""
        store = MemoryStore()
        store.add(create_test_item("c1", confidence=0.9))
        store.add(create_test_item("c2", confidence=0.8))
        store.add(create_test_item("c3", confidence=0.6))
        store.add(create_test_item("c4", confidence=0.4))

        high = store.retrieve_by_confidence(min_confidence=0.7)
        assert len(high) == 2

        low = store.retrieve_by_confidence(min_confidence=0.0, max_confidence=0.5)
        assert len(low) == 1

    def test_validation_index(self):
        """Test validation status index."""
        store = MemoryStore()
        store.add(create_test_item("a1", validation_status="approved"))
        store.add(create_test_item("a2", validation_status="approved"))
        store.add(create_test_item("p1", validation_status="pending"))

        approved = store.retrieve_by_validation_status("approved")
        assert len(approved) == 2

        pending = store.retrieve_by_validation_status("pending")
        assert len(pending) == 1

    def test_concept_index(self):
        """Test concept index."""
        store = MemoryStore()
        store.add(create_test_item("g1", key_concepts=("geometry", "vex")))
        store.add(create_test_item("g2", key_concepts=("geometry", "python")))
        store.add(create_test_item("p1", key_concepts=("python", "scripting")))

        geometry_items = store.retrieve_by_concept("geometry")
        assert len(geometry_items) == 2

        python_items = store.retrieve_by_concept("python")
        assert len(python_items) == 2


class TestRetrievalMethods:
    """Tests for retrieval methods."""

    def test_retrieve_production_ready(self):
        """Test production ready retrieval."""
        store = MemoryStore()
        store.add(create_test_item("ready1", confidence=0.8, validation_status="approved"))
        store.add(create_test_item("ready2", confidence=0.9, validation_status="approved"))
        store.add(create_test_item("not_ready", confidence=0.8, validation_status="pending"))
        store.add(create_test_item("low_conf", confidence=0.6, validation_status="approved"))

        ready = store.retrieve_production_ready()
        assert len(ready) == 2

    def test_retrieve_needing_validation(self):
        """Test needing validation retrieval."""
        store = MemoryStore()
        store.add(create_test_item("needs1", confidence=0.5))  # Low confidence
        store.add(create_test_item("needs2", confidence=0.8, validation_status="unvalidated"))

        needs = store.retrieve_needing_validation()
        assert len(needs) >= 1

    def test_semantic_search(self):
        """Test semantic search."""
        store = MemoryStore()
        store.add(create_test_item(
            "g1",
            content="Create procedural geometry using VEX in Houdini",
            key_concepts=("geometry", "vex", "procedural"),
        ))
        store.add(create_test_item(
            "g2",
            content="Python scripting for automation",
            key_concepts=("python", "scripting"),
        ))

        results = store.semantic_search("procedural geometry houdini")
        assert len(results) >= 1
        assert results[0][0].id == "g1"

    def test_semantic_search_with_confidence_filter(self):
        """Test semantic search with confidence filter."""
        store = MemoryStore()
        store.add(create_test_item(
            "high",
            content="Houdini geometry VEX procedural",
            confidence=0.9,
            key_concepts=("geometry", "vex"),
        ))
        store.add(create_test_item(
            "low",
            content="Houdini geometry VEX procedural",
            confidence=0.3,
            key_concepts=("geometry", "vex"),
        ))

        results = store.semantic_search("houdini geometry", min_confidence=0.7)
        assert len(results) == 1
        assert results[0][0].id == "high"


class TestKnowledgeGraph:
    """Tests for knowledge graph traversal."""

    def test_traverse_related_items(self):
        """Test traversing related items."""
        store = MemoryStore()

        # Create related items
        item1 = create_test_item("parent", key_concepts=("geometry",))
        item2 = MemoryItem(
            id="child",
            content="Related content",
            created_at="2024-01-01",
            related_items=("parent",),
        )

        store.add(item1)
        store.add(item2)

        # Traverse from parent
        graph = store.traverse_knowledge_graph("parent", depth=1)
        assert graph["item"].id == "parent"

    def test_traverse_conflicts(self):
        """Test traversing conflicting items."""
        store = MemoryStore()

        # Create items with bidirectional conflict references
        item1 = create_test_item("item1", conflicting_items=("item2",))
        item2 = create_test_item("item2", conflicting_items=("item1",))

        store.add(item1)
        store.add(item2)

        conflicts = store.retrieve_conflicting("item1")
        assert len(conflicts) == 1
        assert conflicts[0].id == "item2"


class TestDeduplication:
    """Tests for deduplication."""

    def test_find_by_fingerprint(self):
        """Test finding by fingerprint."""
        store = MemoryStore()
        item = MemoryItem(
            id="test",
            content="Unique content",
            created_at="2024-01-01",
            provenance_fingerprint="sha256:abc123",
        )
        store.add(item)

        found = store.find_by_fingerprint("sha256:abc123")
        assert found is not None
        assert found.id == "test"

    def test_find_similar(self):
        """Test finding similar items."""
        store = MemoryStore()
        store.add(create_test_item("s1", content="Houdini procedural geometry VEX"))
        store.add(create_test_item("s2", content="Blender procedural geometry Python"))

        similar = store.find_similar("Houdini procedural geometry", threshold=0.5)
        assert len(similar) >= 1

    def test_add_with_dedup_exact_fingerprint(self):
        """Test dedup with exact fingerprint match."""
        store = MemoryStore()

        original = MemoryItem(
            id="orig",
            content="Original content",
            created_at="2024-01-01",
            provenance_fingerprint="sha256:test123",
            confidence=0.8,
        )
        store.add(original)

        duplicate = MemoryItem(
            id="dup",
            content="Original content",
            created_at="2024-01-02",
            provenance_fingerprint="sha256:test123",
            confidence=0.9,
        )

        result_id, action = store.add_with_dedup(duplicate, merge_strategy="keep_best")
        assert result_id == "orig"
        assert action in ("duplicate", "merged")


class TestPersistence:
    """Tests for save/load functionality."""

    def test_save_and_load(self, tmp_path):
        """Test saving and loading store."""
        store = MemoryStore()
        store.add(create_test_item("item1", content="Content 1"))
        store.add(create_test_item("item2", content="Content 2"))

        save_path = str(tmp_path / "memory.json")
        assert store.save(save_path) is True

        # Load into new store
        new_store = MemoryStore()
        assert new_store.load(save_path) is True
        assert new_store.count == 2
        assert new_store.get("item1") is not None


class TestAdvancedRetriever:
    """Tests for AdvancedRetriever."""

    def test_build_rag_context(self):
        """Test building RAG context."""
        store = MemoryStore()
        store.add(create_test_item(
            "r1",
            content="Create procedural geometry in Houdini using VEX",
            domain="houdini",
            knowledge_type="recipe",
            confidence=0.9,
            validation_status="approved",
            key_concepts=("geometry", "vex", "procedural"),
        ))

        retriever = create_retriever(store)
        ctx = retriever.build_rag_context(
            query="procedural geometry",
            domain="houdini",
            min_confidence=0.7,
        )

        assert ctx.domain == "houdini"
        assert len(ctx.retrieved_docs) >= 1
        assert ctx.confidence_score > 0.7

    def test_get_knowledge_summary(self):
        """Test getting knowledge summary."""
        store = MemoryStore()
        store.add(create_test_item("r1", domain="houdini", knowledge_type="recipe", confidence=0.9))
        store.add(create_test_item("r2", domain="houdini", knowledge_type="recipe", confidence=0.7))
        store.add(create_test_item("t1", domain="houdini", knowledge_type="technique", confidence=0.8))

        retriever = create_retriever(store)
        summary = retriever.get_knowledge_summary("houdini")

        assert summary["domain"] == "houdini"
        assert summary["total"] == 3
        assert summary["by_type"]["recipe"] == 2
        assert summary["by_type"]["technique"] == 1

    def test_get_workflow_chain(self):
        """Test getting workflow chain."""
        store = MemoryStore()

        item1 = create_test_item("step1", domain="houdini", knowledge_type="recipe", confidence=0.9)
        store.add(item1)

        item2 = MemoryItem(
            id="step2",
            content="Related step",
            created_at="2024-01-01",
            domain="houdini",
            knowledge_type="recipe",
            confidence=0.85,
            related_items=("step1",),
        )
        store.add(item2)

        retriever = create_retriever(store)
        chain = retriever.get_workflow_chain("houdini")

        assert len(chain) >= 1


class TestValidationManager:
    """Tests for ValidationManager."""

    def test_submit_for_review(self):
        """Test submitting item for review."""
        store = MemoryStore()
        store.add(create_test_item("item1", validation_status="unvalidated"))

        validator = create_validator(store)
        result = validator.submit_for_review("item1", reason="test")

        assert result is True
        item = store.get("item1")
        assert item.validation_status == "pending"

    def test_approve_item(self):
        """Test approving an item."""
        store = MemoryStore()
        store.add(create_test_item("item1", confidence=0.7, validation_status="pending"))

        validator = create_validator(store)
        result = validator.approve("item1", notes="Tested successfully", confidence_boost=0.1)

        assert result is True
        item = store.get("item1")
        assert item.validation_status == "approved"
        assert abs(item.confidence - 0.8) < 0.01  # Account for floating point precision

    def test_reject_item(self):
        """Test rejecting an item."""
        store = MemoryStore()
        store.add(create_test_item("item1", validation_status="pending"))

        validator = create_validator(store)
        result = validator.reject("item1", reason="Incorrect information")

        assert result is True
        item = store.get("item1")
        assert item.validation_status == "rejected"

    def test_record_usage(self):
        """Test recording usage."""
        store = MemoryStore()
        store.add(create_test_item("item1", use_count=0, successful_uses=0))

        validator = create_validator(store)

        # Record successful use
        validator.record_usage("item1", success=True, user_rating=4.5)

        item = store.get("item1")
        assert item.use_count == 1
        assert item.successful_uses == 1
        assert 4.5 in item.user_ratings

    def test_auto_submit_low_confidence(self):
        """Test auto-submitting low confidence items."""
        store = MemoryStore()
        store.add(create_test_item("low1", confidence=0.5, validation_status="unvalidated"))
        store.add(create_test_item("low2", confidence=0.6, validation_status="unvalidated"))
        store.add(create_test_item("high", confidence=0.8, validation_status="unvalidated"))

        validator = create_validator(store)
        count = validator.auto_submit_low_confidence(threshold=0.7)

        assert count == 2  # low1 and low2 submitted