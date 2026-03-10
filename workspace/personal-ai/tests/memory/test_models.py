"""Unit tests for MemoryItem model."""

import pytest

from app.memory.models import (
    MemoryItem,
    MemoryItemBuilder,
    compute_relevance,
    create_pattern,
    create_recipe,
    create_technique,
    create_troubleshooting,
)


class TestMemoryItem:
    """Tests for MemoryItem dataclass."""

    def test_create_basic_item(self):
        """Test creating a basic memory item."""
        item = MemoryItem(
            id="test1",
            content="Test content",
            created_at="2024-01-01T00:00:00",
        )
        assert item.id == "test1"
        assert item.content == "Test content"
        assert item.confidence == 0.5
        assert item.validation_status == "unvalidated"

    def test_item_default_values(self):
        """Test default values are correct."""
        item = MemoryItem(
            id="test",
            content="Test",
            created_at="2024-01-01",
        )
        assert item.tags == ()
        assert item.domain == "general"
        assert item.knowledge_type is None
        assert item.steps == ()
        assert item.confidence == 0.5
        assert item.use_count == 0

    def test_success_rate_property(self):
        """Test success rate calculation."""
        # No usage
        item1 = MemoryItem(id="1", content="test", created_at="2024-01-01")
        assert item1.success_rate == 0.5  # Unknown

        # With usage
        item2 = MemoryItem(
            id="2",
            content="test",
            created_at="2024-01-01",
            use_count=10,
            successful_uses=8,
        )
        assert item2.success_rate == 0.8

    def test_avg_user_rating_property(self):
        """Test average rating calculation."""
        # No ratings
        item1 = MemoryItem(id="1", content="test", created_at="2024-01-01")
        assert item1.avg_user_rating == 0.5  # Unknown

        # With ratings
        item2 = MemoryItem(
            id="2",
            content="test",
            created_at="2024-01-01",
            user_ratings=(4.0, 5.0, 4.0),
        )
        # Average 4.33, normalized: (4.33 - 1) / 4 = 0.8325
        assert 0.8 < item2.avg_user_rating < 0.85

    def test_is_production_ready(self):
        """Test production ready check."""
        # Not ready: unvalidated
        item1 = MemoryItem(
            id="1",
            content="test",
            created_at="2024-01-01",
            validation_status="unvalidated",
            confidence=0.9,
        )
        assert item1.is_production_ready is False

        # Not ready: low confidence
        item2 = MemoryItem(
            id="2",
            content="test",
            created_at="2024-01-01",
            validation_status="approved",
            confidence=0.6,
        )
        assert item2.is_production_ready is False

        # Ready
        item3 = MemoryItem(
            id="3",
            content="test",
            created_at="2024-01-01",
            validation_status="approved",
            confidence=0.8,
        )
        assert item3.is_production_ready is True

    def test_needs_revalidation(self):
        """Test revalidation check."""
        # Low confidence
        item1 = MemoryItem(
            id="1",
            content="test",
            created_at="2024-01-01",
            confidence=0.5,
        )
        assert item1.needs_revalidation is True

        # No validation date
        item2 = MemoryItem(
            id="2",
            content="test",
            created_at="2024-01-01",
            confidence=0.8,
            last_validated=None,
        )
        assert item2.needs_revalidation is True

    def test_quality_score(self):
        """Test quality score calculation."""
        item = MemoryItem(
            id="1",
            content="test",
            created_at="2024-01-01",
            confidence=0.8,
            use_count=10,
            successful_uses=9,
            user_ratings=(4.0, 5.0),
        )
        # quality = 0.4 * confidence + 0.3 * success_rate + 0.3 * avg_rating
        # = 0.4 * 0.8 + 0.3 * 0.9 + 0.3 * ~0.75
        assert 0.7 < item.quality_score < 0.9

    def test_compute_fingerprint(self):
        """Test fingerprint computation."""
        item = MemoryItem(
            id="1",
            content="Test content for fingerprinting",
            created_at="2024-01-01",
        )
        fingerprint = item.compute_fingerprint()
        assert fingerprint.startswith("sha256:")
        assert len(fingerprint) > 10

    def test_to_dict_and_from_dict(self):
        """Test serialization round-trip."""
        original = MemoryItem(
            id="test1",
            content="Test content",
            created_at="2024-01-01",
            tags=("tag1", "tag2"),
            domain="houdini",
            knowledge_type="recipe",
            steps=({"order": 1, "name": "Step 1"},),
            confidence=0.85,
            validation_status="approved",
        )

        data = original.to_dict()
        restored = MemoryItem.from_dict(data)

        assert restored.id == original.id
        assert restored.content == original.content
        assert restored.tags == original.tags
        assert restored.domain == original.domain
        assert restored.knowledge_type == original.knowledge_type
        assert restored.steps == original.steps
        assert restored.confidence == original.confidence


class TestMemoryItemBuilder:
    """Tests for MemoryItemBuilder."""

    def test_build_basic_item(self):
        """Test building a basic item."""
        item = (
            MemoryItemBuilder()
            .content("Test content")
            .build()
        )
        assert item.content == "Test content"
        assert item.id  # Auto-generated

    def test_build_with_all_options(self):
        """Test building with all options."""
        item = (
            MemoryItemBuilder()
            .content("Recipe for success")
            .domain("houdini")
            .tags("vex", "sop")
            .knowledge_type("recipe")
            .add_step(1, "Create SOP", "Add geometry node")
            .add_step(2, "Add VEX", "Write wrangle")
            .prerequisites("Houdini basics", "VEX knowledge")
            .learning_objectives("Learn procedural modeling")
            .key_concepts("geometry", "procedural", "vex")
            .confidence(0.85, {"domain_match": 0.9, "completeness": 0.8})
            .validation_status("pending")
            .source_type("tutorial")
            .source("https://example.com/tutorial")
            .build()
        )

        assert item.content == "Recipe for success"
        assert item.domain == "houdini"
        assert "vex" in item.tags
        assert item.knowledge_type == "recipe"
        assert len(item.steps) == 2
        assert len(item.prerequisites) == 2
        assert len(item.learning_objectives) == 1
        assert "geometry" in item.key_concepts
        assert item.confidence == 0.85
        assert item.validation_status == "pending"
        assert item.source_type == "tutorial"

    def test_build_without_content_raises(self):
        """Test that building without content raises error."""
        with pytest.raises(ValueError, match="Content is required"):
            MemoryItemBuilder().build()


class TestFactoryFunctions:
    """Tests for factory functions."""

    def test_create_recipe(self):
        """Test creating a recipe item."""
        item = create_recipe(
            content="Procedural building generator",
            steps=[
                {"order": 1, "name": "Setup", "action": "Create base geometry"},
                {"order": 2, "name": "Procedural", "action": "Add procedural controls"},
            ],
            domain="houdini",
            prerequisites=["Houdini basics"],
            key_concepts=["procedural", "architecture"],
            confidence=0.9,
        )

        assert item.knowledge_type == "recipe"
        assert len(item.steps) == 2
        assert item.domain == "houdini"
        assert "procedural" in item.key_concepts

    def test_create_technique(self):
        """Test creating a technique item."""
        item = create_technique(
            content="Using VEX for point manipulation",
            domain="houdini",
            key_concepts=["vex", "points"],
            confidence=0.85,
        )

        assert item.knowledge_type == "technique"
        assert item.domain == "houdini"
        assert "vex" in item.key_concepts

    def test_create_troubleshooting(self):
        """Test creating a troubleshooting item."""
        item = create_troubleshooting(
            content="Fix for slow viewport performance",
            domain="houdini",
            error_pattern="slow_viewport",
            solution_steps=[
                {"order": 1, "name": "Check", "action": "Check display flags"},
            ],
        )

        assert item.knowledge_type == "troubleshooting"
        assert any("error:slow_viewport" in t for t in item.tags)

    def test_create_pattern(self):
        """Test creating a pattern item."""
        item = create_pattern(
            content="Observer pattern for event handling",
            pattern_name="observer",
            domain="code",
            use_cases=["Event systems", "Message passing"],
        )

        assert item.knowledge_type == "pattern"
        assert any("pattern:observer" in t for t in item.tags)


class TestComputeRelevance:
    """Tests for relevance computation."""

    def test_relevance_no_match(self):
        """Test relevance with no match."""
        item = MemoryItem(
            id="1",
            content="This is about houdini",
            created_at="2024-01-01",
        )
        relevance = compute_relevance("blender python", item)
        assert relevance == 0.0

    def test_relevance_partial_match(self):
        """Test relevance with partial match."""
        item = MemoryItem(
            id="1",
            content="Create procedural geometry in Houdini",
            created_at="2024-01-01",
            key_concepts=("geometry", "procedural"),
        )
        relevance = compute_relevance("procedural geometry houdini", item)
        assert relevance > 0.0

    def test_relevance_full_match(self):
        """Test relevance with good match."""
        item = MemoryItem(
            id="1",
            content="procedural geometry houdini vex",
            created_at="2024-01-01",
            key_concepts=("procedural", "geometry", "houdini", "vex"),
            tags=("sop", "vex"),
        )
        relevance = compute_relevance("procedural geometry houdini", item)
        assert relevance > 0.5