"""Memory Item Models with Structured Knowledge Support.

Provides MemoryItem dataclass with knowledge metadata, confidence tracking,
validation status, provenance, and relationships for intelligent retrieval.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4


@dataclass(frozen=True, slots=True)
class MemoryItem:
    """A memory item with structured knowledge support.

    Supports:
    - Knowledge structure: type, steps, prerequisites, objectives
    - Quality tracking: confidence, validation status
    - Provenance: source type, extraction method, fingerprint
    - Reuse metrics: use count, success rate, ratings
    - Relationships: related items, conflicting items
    """

    # Core (required)
    id: str
    content: str
    created_at: str

    # Metadata (optional, backward compatible)
    tags: tuple[str, ...] = ()
    domain: str = "general"
    source: str | None = None

    # Knowledge Structure
    knowledge_type: str | None = None  # "recipe", "technique", "pattern", "troubleshooting"
    steps: tuple[dict[str, Any], ...] = ()
    prerequisites: tuple[str, ...] = ()
    learning_objectives: tuple[str, ...] = ()
    key_concepts: tuple[str, ...] = ()  # For RAG indexing

    # Quality & Confidence
    confidence: float = 0.5  # 0.0-1.0, default = unknown
    confidence_factors: dict[str, float] | None = None

    # Validation
    validation_status: str = "unvalidated"  # "pending", "validating", "approved", "rejected"
    last_validated: str | None = None  # ISO 8601 timestamp
    validator_notes: str | None = None

    # Provenance
    source_type: str | None = None  # "tutorial", "rag_doc", "llm_generation", "user_input"
    extraction_method: str | None = None  # "pattern_matching", "semantic_search", "llm_inference"
    provenance_fingerprint: str | None = None  # SHA256 for deduplication
    parent_item_id: str | None = None

    # Reuse Tracking
    use_count: int = 0
    successful_uses: int = 0
    last_used: str | None = None
    user_ratings: tuple[float, ...] = ()  # 1-5 star ratings

    # Relationships
    related_items: tuple[str, ...] = ()
    conflicting_items: tuple[str, ...] = ()

    # Repair Knowledge (for troubleshooting and error recovery)
    repair_hints: tuple[str, ...] = ()  # ["If noise too high, reduce amplitude", ...]
    error_patterns: tuple[str, ...] = ()  # ["node_not_found", "parameter_invalid", ...]
    common_pitfalls: tuple[str, ...] = ()  # ["Don't forget to bake transforms", ...]

    # Additional metadata
    metadata: dict[str, Any] | None = None

    @property
    def success_rate(self) -> float:
        """Calculate success rate from use history."""
        if self.use_count == 0:
            return 0.5  # Unknown
        return self.successful_uses / self.use_count

    @property
    def avg_user_rating(self) -> float:
        """Average user rating normalized to 0-1 scale."""
        if not self.user_ratings:
            return 0.5  # Unknown
        avg = sum(self.user_ratings) / len(self.user_ratings)
        return (avg - 1) / 4  # Normalize 1-5 to 0-1

    @property
    def is_production_ready(self) -> bool:
        """Check if item is approved and high confidence."""
        return (
            self.validation_status == "approved"
            and self.confidence >= 0.7
        )

    @property
    def needs_revalidation(self) -> bool:
        """Check if item should be revalidated."""
        if self.confidence < 0.7:
            return True
        if self.last_validated is None:
            return True
        try:
            last = datetime.fromisoformat(self.last_validated)
            days_since = (datetime.now() - last).days
            return days_since > 30
        except (ValueError, TypeError):
            return True

    @property
    def quality_score(self) -> float:
        """Combined quality metric for ranking.

        Combines confidence, success_rate, avg_user_rating with weights.
        """
        return (
            0.4 * self.confidence +
            0.3 * self.success_rate +
            0.3 * self.avg_user_rating
        )

    def compute_fingerprint(self) -> str:
        """Compute SHA256 fingerprint of content for deduplication."""
        content_hash = hashlib.sha256(self.content.encode()).hexdigest()
        return f"sha256:{content_hash[:16]}"

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for JSON storage."""
        return {
            "id": self.id,
            "content": self.content,
            "created_at": self.created_at,
            "tags": list(self.tags),
            "domain": self.domain,
            "source": self.source,
            "knowledge_type": self.knowledge_type,
            "steps": list(self.steps),
            "prerequisites": list(self.prerequisites),
            "learning_objectives": list(self.learning_objectives),
            "key_concepts": list(self.key_concepts),
            "confidence": self.confidence,
            "confidence_factors": self.confidence_factors,
            "validation_status": self.validation_status,
            "last_validated": self.last_validated,
            "validator_notes": self.validator_notes,
            "source_type": self.source_type,
            "extraction_method": self.extraction_method,
            "provenance_fingerprint": self.provenance_fingerprint,
            "parent_item_id": self.parent_item_id,
            "use_count": self.use_count,
            "successful_uses": self.successful_uses,
            "last_used": self.last_used,
            "user_ratings": list(self.user_ratings),
            "related_items": list(self.related_items),
            "conflicting_items": list(self.conflicting_items),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MemoryItem:
        """Deserialize from dictionary."""
        return cls(
            id=data.get("id", str(uuid4())[:8]),
            content=data["content"],
            created_at=data.get("created_at", datetime.now().isoformat()),
            tags=tuple(data.get("tags", [])),
            domain=data.get("domain", "general"),
            source=data.get("source"),
            knowledge_type=data.get("knowledge_type"),
            steps=tuple(data.get("steps", [])),
            prerequisites=tuple(data.get("prerequisites", [])),
            learning_objectives=tuple(data.get("learning_objectives", [])),
            key_concepts=tuple(data.get("key_concepts", [])),
            confidence=data.get("confidence", 0.5),
            confidence_factors=data.get("confidence_factors"),
            validation_status=data.get("validation_status", "unvalidated"),
            last_validated=data.get("last_validated"),
            validator_notes=data.get("validator_notes"),
            source_type=data.get("source_type"),
            extraction_method=data.get("extraction_method"),
            provenance_fingerprint=data.get("provenance_fingerprint"),
            parent_item_id=data.get("parent_item_id"),
            use_count=data.get("use_count", 0),
            successful_uses=data.get("successful_uses", 0),
            last_used=data.get("last_used"),
            user_ratings=tuple(data.get("user_ratings", [])),
            related_items=tuple(data.get("related_items", [])),
            conflicting_items=tuple(data.get("conflicting_items", [])),
            metadata=data.get("metadata"),
        )


@dataclass
class MemoryItemBuilder:
    """Builder for creating MemoryItem instances with fluent API."""

    _content: str = ""
    _domain: str = "general"
    _tags: list[str] = field(default_factory=list)
    _knowledge_type: str | None = None
    _steps: list[dict[str, Any]] = field(default_factory=list)
    _prerequisites: list[str] = field(default_factory=list)
    _learning_objectives: list[str] = field(default_factory=list)
    _key_concepts: list[str] = field(default_factory=list)
    _confidence: float = 0.5
    _confidence_factors: dict[str, float] | None = None
    _validation_status: str = "unvalidated"
    _source_type: str | None = None
    _source: str | None = None
    _metadata: dict[str, Any] | None = None

    def content(self, content: str) -> MemoryItemBuilder:
        """Set the content."""
        self._content = content
        return self

    def domain(self, domain: str) -> MemoryItemBuilder:
        """Set the domain."""
        self._domain = domain
        return self

    def tags(self, *tags: str) -> MemoryItemBuilder:
        """Add tags."""
        self._tags.extend(tags)
        return self

    def knowledge_type(self, ktype: str) -> MemoryItemBuilder:
        """Set knowledge type (recipe, technique, pattern, troubleshooting)."""
        self._knowledge_type = ktype
        return self

    def steps(self, *steps: dict[str, Any]) -> MemoryItemBuilder:
        """Add steps for recipes."""
        self._steps.extend(steps)
        return self

    def add_step(self, order: int, name: str, action: str, **kwargs: Any) -> MemoryItemBuilder:
        """Add a single step."""
        step = {"order": order, "name": name, "action": action, **kwargs}
        self._steps.append(step)
        return self

    def prerequisites(self, *prereqs: str) -> MemoryItemBuilder:
        """Add prerequisites."""
        self._prerequisites.extend(prereqs)
        return self

    def learning_objectives(self, *objectives: str) -> MemoryItemBuilder:
        """Add learning objectives."""
        self._learning_objectives.extend(objectives)
        return self

    def key_concepts(self, *concepts: str) -> MemoryItemBuilder:
        """Add key concepts for RAG indexing."""
        self._key_concepts.extend(concepts)
        return self

    def confidence(self, confidence: float, factors: dict[str, float] | None = None) -> MemoryItemBuilder:
        """Set confidence level (0.0-1.0)."""
        self._confidence = max(0.0, min(1.0, confidence))
        self._confidence_factors = factors
        return self

    def validation_status(self, status: str) -> MemoryItemBuilder:
        """Set validation status."""
        self._validation_status = status
        return self

    def source_type(self, stype: str) -> MemoryItemBuilder:
        """Set source type (tutorial, rag_doc, llm_generation, user_input)."""
        self._source_type = stype
        return self

    def source(self, source: str) -> MemoryItemBuilder:
        """Set source identifier."""
        self._source = source
        return self

    def metadata(self, **kwargs: Any) -> MemoryItemBuilder:
        """Add metadata."""
        if self._metadata is None:
            self._metadata = {}
        self._metadata.update(kwargs)
        return self

    def build(self) -> MemoryItem:
        """Build the MemoryItem."""
        if not self._content:
            raise ValueError("Content is required")

        now = datetime.now().isoformat()
        fingerprint = hashlib.sha256(self._content.encode()).hexdigest()[:16]

        return MemoryItem(
            id=str(uuid4())[:8],
            content=self._content,
            created_at=now,
            tags=tuple(self._tags),
            domain=self._domain,
            source=self._source,
            knowledge_type=self._knowledge_type,
            steps=tuple(self._steps),
            prerequisites=tuple(self._prerequisites),
            learning_objectives=tuple(self._learning_objectives),
            key_concepts=tuple(self._key_concepts),
            confidence=self._confidence,
            confidence_factors=self._confidence_factors,
            validation_status=self._validation_status,
            source_type=self._source_type,
            provenance_fingerprint=f"sha256:{fingerprint}",
            metadata=self._metadata,
        )


# Factory functions for common memory types

def create_recipe(
    content: str,
    steps: list[dict[str, Any]],
    domain: str = "general",
    prerequisites: list[str] | None = None,
    key_concepts: list[str] | None = None,
    confidence: float = 0.5,
    source: str | None = None,
) -> MemoryItem:
    """Create a recipe-type memory item."""
    builder = (
        MemoryItemBuilder()
        .content(content)
        .domain(domain)
        .knowledge_type("recipe")
        .confidence(confidence)
    )

    for step in steps:
        builder.add_step(**step)

    if prerequisites:
        builder.prerequisites(*prerequisites)
    if key_concepts:
        builder.key_concepts(*key_concepts)
    if source:
        builder.source(source)

    return builder.build()


def create_technique(
    content: str,
    domain: str = "general",
    key_concepts: list[str] | None = None,
    confidence: float = 0.5,
    source: str | None = None,
) -> MemoryItem:
    """Create a technique-type memory item."""
    builder = (
        MemoryItemBuilder()
        .content(content)
        .domain(domain)
        .knowledge_type("technique")
        .confidence(confidence)
    )

    if key_concepts:
        builder.key_concepts(*key_concepts)
    if source:
        builder.source(source)

    return builder.build()


def create_troubleshooting(
    content: str,
    domain: str = "general",
    error_pattern: str | None = None,
    solution_steps: list[dict[str, Any]] | None = None,
    confidence: float = 0.5,
) -> MemoryItem:
    """Create a troubleshooting-type memory item."""
    builder = (
        MemoryItemBuilder()
        .content(content)
        .domain(domain)
        .knowledge_type("troubleshooting")
        .confidence(confidence)
    )

    if error_pattern:
        builder.tags(f"error:{error_pattern}")

    if solution_steps:
        for step in solution_steps:
            builder.add_step(**step)

    return builder.build()


def create_pattern(
    content: str,
    pattern_name: str,
    domain: str = "general",
    use_cases: list[str] | None = None,
    confidence: float = 0.5,
) -> MemoryItem:
    """Create a pattern-type memory item."""
    builder = (
        MemoryItemBuilder()
        .content(content)
        .domain(domain)
        .knowledge_type("pattern")
        .confidence(confidence)
        .tags(f"pattern:{pattern_name}")
    )

    if use_cases:
        builder.learning_objectives(*use_cases)

    return builder.build()


# Helper function for computing relevance
def compute_relevance(query: str, item: MemoryItem) -> float:
    """Compute relevance score between query and item.

    Args:
        query: Search query
        item: Memory item to score

    Returns:
        Relevance score between 0 and 1
    """
    query_terms = set(query.lower().split())
    if not query_terms:
        return 0.0

    # Check content
    content_terms = set(item.content.lower().split())
    content_match = len(query_terms & content_terms) / len(query_terms)

    # Check key concepts
    concept_match = 0.0
    if item.key_concepts:
        concepts_lower = set(c.lower() for c in item.key_concepts)
        concept_match = len(query_terms & concepts_lower) / len(query_terms)

    # Check tags
    tag_match = 0.0
    if item.tags:
        tags_lower = set(t.lower() for t in item.tags)
        tag_match = len(query_terms & tags_lower) / len(query_terms)

    # Weighted combination
    return 0.5 * content_match + 0.3 * concept_match + 0.2 * tag_match