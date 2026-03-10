"""Memory Store with Multi-Index Architecture.

Provides efficient storage and retrieval of MemoryItem instances with
multiple indexes for O(1) lookups and range queries.
"""

from __future__ import annotations

import json
import os
from bisect import bisect_left, bisect_right, insort
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Iterator

from app.memory.models import MemoryItem, compute_relevance


@dataclass
class IndexStats:
    """Statistics about an index."""

    name: str
    entry_count: int
    unique_keys: int
    last_updated: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "entry_count": self.entry_count,
            "unique_keys": self.unique_keys,
            "last_updated": self.last_updated,
        }


class SortedIndex:
    """A sorted index for range queries on numeric values.

    Maintains items sorted by a numeric key for efficient range queries.
    """

    def __init__(self) -> None:
        self._keys: list[float] = []
        self._items: dict[float, list[str]] = defaultdict(list)

    def add(self, key: float, item_id: str) -> None:
        """Add an item to the sorted index."""
        # Round key for bucketing (avoid float precision issues)
        bucket_key = round(key, 4)

        if bucket_key not in self._items:
            insort(self._keys, bucket_key)
        self._items[bucket_key].append(item_id)

    def remove(self, key: float, item_id: str) -> None:
        """Remove an item from the index."""
        bucket_key = round(key, 4)

        if bucket_key in self._items:
            if item_id in self._items[bucket_key]:
                self._items[bucket_key].remove(item_id)
            if not self._items[bucket_key]:
                del self._items[bucket_key]
                self._keys.remove(bucket_key)

    def range_query(self, min_key: float, max_key: float) -> list[str]:
        """Get all item IDs in the key range [min_key, max_key]."""
        min_bucket = round(min_key, 4)
        max_bucket = round(max_key, 4)

        # Find range in sorted keys
        left = bisect_left(self._keys, min_bucket)
        right = bisect_right(self._keys, max_bucket)

        result = []
        for i in range(left, right):
            key = self._keys[i]
            result.extend(self._items[key])

        return result

    def get_stats(self) -> dict[str, Any]:
        """Get index statistics."""
        return {
            "entry_count": sum(len(v) for v in self._items.values()),
            "unique_keys": len(self._keys),
        }


class MemoryStore:
    """Memory store with multi-index architecture.

    Indexes:
    - knowledge_type_index: O(1) lookup by type
    - domain_index: O(1) lookup by domain
    - confidence_index: Range queries on confidence
    - validation_index: O(1) lookup by validation status
    - concept_index: O(1) lookup by key concept
    - content_index: Full-text index for content search
    - provenance_index: O(1) lookup by source type
    """

    def __init__(self, storage_path: str | None = None) -> None:
        """Initialize the memory store.

        Args:
            storage_path: Optional path for persistence
        """
        self._memories: dict[str, MemoryItem] = {}
        self._storage_path = storage_path

        # Multi-index architecture
        self._knowledge_type_index: dict[str, list[str]] = defaultdict(list)
        self._domain_index: dict[str, list[str]] = defaultdict(list)
        self._confidence_index = SortedIndex()
        self._validation_index: dict[str, list[str]] = defaultdict(list)
        self._concept_index: dict[str, list[str]] = defaultdict(list)
        self._content_index: dict[str, list[str]] = defaultdict(list)
        self._provenance_index: dict[str, list[str]] = defaultdict(list)
        self._fingerprint_index: dict[str, str] = {}  # fingerprint -> item_id

        self._index_built = False
        self._last_modified: str | None = None

    @property
    def count(self) -> int:
        """Total number of items."""
        return len(self._memories)

    def add(self, item: MemoryItem, update_indexes: bool = True) -> str:
        """Add a memory item to the store.

        Args:
            item: MemoryItem to add
            update_indexes: Whether to update indexes (default True)

        Returns:
            Item ID
        """
        self._memories[item.id] = item

        if update_indexes:
            self._add_to_indexes(item)

        self._last_modified = datetime.now().isoformat()
        return item.id

    def get(self, item_id: str) -> MemoryItem | None:
        """Get an item by ID."""
        return self._memories.get(item_id)

    def update(self, item_id: str, updated_item: MemoryItem) -> bool:
        """Update an existing item.

        Args:
            item_id: ID of item to update
            updated_item: New item data

        Returns:
            True if updated, False if not found
        """
        if item_id not in self._memories:
            return False

        # Remove old item from indexes
        old_item = self._memories[item_id]
        self._remove_from_indexes(old_item)

        # Add updated item
        self._memories[item_id] = updated_item
        self._add_to_indexes(updated_item)

        self._last_modified = datetime.now().isoformat()
        return True

    def delete(self, item_id: str) -> bool:
        """Delete an item from the store.

        Args:
            item_id: ID of item to delete

        Returns:
            True if deleted, False if not found
        """
        if item_id not in self._memories:
            return False

        item = self._memories[item_id]
        self._remove_from_indexes(item)
        del self._memories[item_id]

        self._last_modified = datetime.now().isoformat()
        return True

    def _add_to_indexes(self, item: MemoryItem) -> None:
        """Add item to all indexes."""
        # Knowledge type index
        if item.knowledge_type:
            self._knowledge_type_index[item.knowledge_type].append(item.id)

        # Domain index
        self._domain_index[item.domain].append(item.id)

        # Confidence index
        self._confidence_index.add(item.confidence, item.id)

        # Validation index
        self._validation_index[item.validation_status].append(item.id)

        # Concept index
        for concept in item.key_concepts:
            concept_lower = concept.lower()
            self._concept_index[concept_lower].append(item.id)

        # Content index (word-based)
        words = set(item.content.lower().split())
        for word in words:
            if len(word) > 2:  # Skip very short words
                self._content_index[word].append(item.id)

        # Provenance index
        if item.source_type:
            self._provenance_index[item.source_type].append(item.id)

        # Fingerprint index
        if item.provenance_fingerprint:
            self._fingerprint_index[item.provenance_fingerprint] = item.id

    def _remove_from_indexes(self, item: MemoryItem) -> None:
        """Remove item from all indexes."""
        # Knowledge type index
        if item.knowledge_type and item.id in self._knowledge_type_index.get(item.knowledge_type, []):
            self._knowledge_type_index[item.knowledge_type].remove(item.id)

        # Domain index
        if item.id in self._domain_index.get(item.domain, []):
            self._domain_index[item.domain].remove(item.id)

        # Confidence index
        self._confidence_index.remove(item.confidence, item.id)

        # Validation index
        if item.id in self._validation_index.get(item.validation_status, []):
            self._validation_index[item.validation_status].remove(item.id)

        # Concept index
        for concept in item.key_concepts:
            concept_lower = concept.lower()
            if item.id in self._concept_index.get(concept_lower, []):
                self._concept_index[concept_lower].remove(item.id)

        # Content index
        words = set(item.content.lower().split())
        for word in words:
            if word in self._content_index and item.id in self._content_index[word]:
                self._content_index[word].remove(item.id)

        # Provenance index
        if item.source_type and item.id in self._provenance_index.get(item.source_type, []):
            self._provenance_index[item.source_type].remove(item.id)

        # Fingerprint index
        if item.provenance_fingerprint and self._fingerprint_index.get(item.provenance_fingerprint) == item.id:
            del self._fingerprint_index[item.provenance_fingerprint]

    def rebuild_indexes(self) -> None:
        """Rebuild all indexes from scratch."""
        # Clear indexes
        self._knowledge_type_index.clear()
        self._domain_index.clear()
        self._confidence_index = SortedIndex()
        self._validation_index.clear()
        self._concept_index.clear()
        self._content_index.clear()
        self._provenance_index.clear()
        self._fingerprint_index.clear()

        # Rebuild
        for item in self._memories.values():
            self._add_to_indexes(item)

        self._index_built = True

    # -------------------------------------------------------------------------
    # Retrieval Methods
    # -------------------------------------------------------------------------

    def retrieve_all(self) -> list[MemoryItem]:
        """Get all memory items."""
        return list(self._memories.values())

    def retrieve_by_knowledge_type(
        self,
        knowledge_type: str,
        domain: str | None = None,
    ) -> list[MemoryItem]:
        """Get all items of a specific knowledge type.

        Args:
            knowledge_type: Type to filter by (recipe, technique, etc.)
            domain: Optional domain filter

        Returns:
            List of matching items
        """
        ids = self._knowledge_type_index.get(knowledge_type, [])

        if domain:
            domain_ids = set(self._domain_index.get(domain, []))
            ids = [i for i in ids if i in domain_ids]

        return [self._memories[i] for i in ids if i in self._memories]

    def retrieve_by_domain(self, domain: str) -> list[MemoryItem]:
        """Get all items for a domain."""
        ids = self._domain_index.get(domain, [])
        return [self._memories[i] for i in ids if i in self._memories]

    def retrieve_by_confidence(
        self,
        min_confidence: float = 0.7,
        max_confidence: float = 1.0,
        sort_descending: bool = True,
    ) -> list[MemoryItem]:
        """Get items with confidence in the specified range.

        Args:
            min_confidence: Minimum confidence threshold
            max_confidence: Maximum confidence threshold
            sort_descending: Sort by confidence descending

        Returns:
            List of matching items, sorted by confidence
        """
        ids = self._confidence_index.range_query(min_confidence, max_confidence)
        items = [self._memories[i] for i in ids if i in self._memories]

        if sort_descending:
            items.sort(key=lambda x: x.confidence, reverse=True)

        return items

    def retrieve_by_validation_status(self, status: str) -> list[MemoryItem]:
        """Get items by validation status."""
        ids = self._validation_index.get(status, [])
        return [self._memories[i] for i in ids if i in self._memories]

    def retrieve_by_concept(self, concept: str) -> list[MemoryItem]:
        """Get items containing a key concept."""
        ids = self._concept_index.get(concept.lower(), [])
        return [self._memories[i] for i in ids if i in self._memories]

    def retrieve_by_source_type(self, source_type: str) -> list[MemoryItem]:
        """Get items by source type."""
        ids = self._provenance_index.get(source_type, [])
        return [self._memories[i] for i in ids if i in self._memories]

    def retrieve_production_ready(self) -> list[MemoryItem]:
        """Get all production-ready items (approved, high confidence)."""
        approved = set(self._validation_index.get("approved", []))
        high_confidence = set(self._confidence_index.range_query(0.7, 1.0))
        ids = approved & high_confidence
        return [self._memories[i] for i in ids if i in self._memories]

    def retrieve_needing_validation(self) -> list[MemoryItem]:
        """Get items that need revalidation."""
        return [item for item in self._memories.values() if item.needs_revalidation]

    def retrieve_related(self, item_id: str) -> list[MemoryItem]:
        """Get items related to a specific item."""
        item = self._memories.get(item_id)
        if not item:
            return []

        related = []
        for related_id in item.related_items:
            if related_id in self._memories:
                related.append(self._memories[related_id])

        return related

    def retrieve_conflicting(self, item_id: str) -> list[MemoryItem]:
        """Get items that conflict with a specific item."""
        item = self._memories.get(item_id)
        if not item:
            return []

        conflicts = []
        for conflict_id in item.conflicting_items:
            if conflict_id in self._memories:
                conflicts.append(self._memories[conflict_id])

        return conflicts

    def semantic_search(
        self,
        query: str,
        min_confidence: float = 0.0,
        limit: int = 10,
    ) -> list[tuple[MemoryItem, float]]:
        """Search for items matching query with confidence filtering.

        Args:
            query: Search query
            min_confidence: Minimum confidence threshold
            limit: Maximum results to return

        Returns:
            List of (item, relevance_score) tuples, sorted by relevance * confidence
        """
        # Get high-confidence items first
        if min_confidence > 0:
            candidate_ids = set(self._confidence_index.range_query(min_confidence, 1.0))
        else:
            candidate_ids = set(self._memories.keys())

        # Score candidates
        scored: list[tuple[MemoryItem, float]] = []
        for item_id in candidate_ids:
            item = self._memories.get(item_id)
            if item:
                relevance = compute_relevance(query, item)
                if relevance > 0:
                    # Combine relevance with confidence
                    score = relevance * item.confidence
                    scored.append((item, score))

        # Sort by score descending
        scored.sort(key=lambda x: x[1], reverse=True)

        return scored[:limit]

    def semantic_search_with_confidence(
        self,
        query: str,
        min_confidence: float = 0.7,
        limit: int = 10,
    ) -> list[tuple[MemoryItem, float]]:
        """Search with confidence threshold (convenience method)."""
        return self.semantic_search(query, min_confidence, limit)

    def traverse_knowledge_graph(
        self,
        start_item_id: str,
        depth: int = 2,
    ) -> dict[str, Any]:
        """Traverse knowledge relationships from a starting item.

        Args:
            start_item_id: Starting item ID
            depth: How many levels to traverse

        Returns:
            Dictionary with item, related items, and conflicts at each level
        """
        result: dict[str, Any] = {
            "item": None,
            "related": [],
            "conflicts": [],
            "depth_traversed": 0,
        }

        start_item = self._memories.get(start_item_id)
        if not start_item:
            return result

        result["item"] = start_item

        visited = {start_item_id}
        queue: list[tuple[str, int]] = [(start_item_id, 0)]

        while queue:
            current_id, current_depth = queue.pop(0)

            if current_depth >= depth:
                continue

            current = self._memories.get(current_id)
            if not current:
                continue

            # Process related items
            for related_id in current.related_items:
                if related_id not in visited and related_id in self._memories:
                    visited.add(related_id)
                    related_item = self._memories[related_id]
                    result["related"].append({
                        "item": related_item,
                        "depth": current_depth + 1,
                        "relationship": "related",
                    })
                    queue.append((related_id, current_depth + 1))

            # Process conflicts
            for conflict_id in current.conflicting_items:
                if conflict_id not in visited and conflict_id in self._memories:
                    visited.add(conflict_id)
                    conflict_item = self._memories[conflict_id]
                    result["conflicts"].append({
                        "item": conflict_item,
                        "depth": current_depth + 1,
                        "relationship": "conflict",
                    })
                    queue.append((conflict_id, current_depth + 1))

        result["depth_traversed"] = depth
        return result

    def get_best_practice_chain(
        self,
        domain: str,
        goal_keywords: list[str],
        limit: int = 5,
    ) -> list[MemoryItem]:
        """Find best practices for a goal within a domain.

        Args:
            domain: Domain to search
            goal_keywords: Keywords describing the goal
            limit: Maximum results

        Returns:
            List of items ordered by quality_score
        """
        # Get domain items
        domain_ids = set(self._domain_index.get(domain, []))

        # Filter by approved status
        approved_ids = set(self._validation_index.get("approved", []))
        candidate_ids = domain_ids & approved_ids

        # Score by relevance to goal
        query = " ".join(goal_keywords)
        scored: list[tuple[MemoryItem, float]] = []

        for item_id in candidate_ids:
            item = self._memories.get(item_id)
            if item:
                relevance = compute_relevance(query, item)
                # Combine relevance with quality score
                score = relevance * item.quality_score
                scored.append((item, score))

        # Sort by score
        scored.sort(key=lambda x: x[1], reverse=True)

        return [item for item, _ in scored[:limit]]

    # -------------------------------------------------------------------------
    # Deduplication Methods
    # -------------------------------------------------------------------------

    def find_by_fingerprint(self, fingerprint: str) -> MemoryItem | None:
        """Find item by provenance fingerprint."""
        item_id = self._fingerprint_index.get(fingerprint)
        if item_id:
            return self._memories.get(item_id)
        return None

    def find_similar(
        self,
        content: str,
        threshold: float = 0.8,
        limit: int = 5,
    ) -> list[tuple[MemoryItem, float]]:
        """Find items with similar content.

        Args:
            content: Content to match
            threshold: Similarity threshold (0-1)
            limit: Maximum results

        Returns:
            List of (item, similarity) tuples
        """
        content_words = set(content.lower().split())
        if not content_words:
            return []

        scored: list[tuple[MemoryItem, float]] = []

        for item in self._memories.values():
            item_words = set(item.content.lower().split())
            if not item_words:
                continue

            # Jaccard similarity
            intersection = len(content_words & item_words)
            union = len(content_words | item_words)
            similarity = intersection / union if union > 0 else 0

            if similarity >= threshold:
                scored.append((item, similarity))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:limit]

    def find_conflicts(self, item: MemoryItem) -> list[MemoryItem]:
        """Find items that might conflict with the given item.

        Conflict detection is based on:
        - Same knowledge_type
        - Similar key_concepts
        - Different/conflicting content patterns

        Args:
            item: Item to check for conflicts

        Returns:
            List of potentially conflicting items
        """
        conflicts = []

        # Same knowledge type in same domain
        same_type = self.retrieve_by_knowledge_type(
            item.knowledge_type or "",
            domain=item.domain,
        ) if item.knowledge_type else []

        for candidate in same_type:
            if candidate.id == item.id:
                continue

            # Check concept overlap
            if item.key_concepts and candidate.key_concepts:
                item_concepts = set(c.lower() for c in item.key_concepts)
                cand_concepts = set(c.lower() for c in candidate.key_concepts)
                overlap = item_concepts & cand_concepts

                # High overlap might indicate conflict
                if len(overlap) >= 2:
                    conflicts.append(candidate)

        return conflicts

    def add_with_dedup(
        self,
        item: MemoryItem,
        merge_strategy: str = "keep_best",
    ) -> tuple[str, str]:
        """Add item with deduplication check.

        Args:
            item: Item to add
            merge_strategy: How to handle duplicates ("keep_best", "merge", "link")

        Returns:
            Tuple of (item_id or existing_id, action_taken)
        """
        # Check fingerprint match
        if item.provenance_fingerprint:
            existing = self.find_by_fingerprint(item.provenance_fingerprint)
            if existing:
                if merge_strategy == "keep_best":
                    # Keep the one with higher quality
                    if item.quality_score > existing.quality_score:
                        self.update(existing.id, item)
                        return existing.id, "merged"
                    return existing.id, "duplicate"

        # Check content similarity
        similar = self.find_similar(item.content, threshold=0.95, limit=1)
        if similar:
            existing, similarity = similar[0]
            if merge_strategy == "link":
                # Add as related
                updated_existing = MemoryItem(
                    **{k: v for k, v in existing.__dict__.items() if k != "related_items"},
                    related_items=existing.related_items + (item.id,),
                )
                updated_new = MemoryItem(
                    **{k: v for k, v in item.__dict__.items() if k != "related_items"},
                    related_items=item.related_items + (existing.id,),
                )
                self.update(existing.id, updated_existing)
                self.add(updated_new)
                return updated_new.id, "linked"
            return existing.id, "similar"

        # Check for conflicts
        conflicts = self.find_conflicts(item)
        if conflicts:
            # Mark as conflicting and add
            conflict_ids = tuple(c.id for c in conflicts)
            updated_item = MemoryItem(
                **{k: v for k, v in item.__dict__.items() if k != "conflicting_items"},
                conflicting_items=conflict_ids,
            )
            self.add(updated_item)

            # Update conflicts to reference this item
            for conflict in conflicts:
                updated_conflict = MemoryItem(
                    **{k: v for k, v in conflict.__dict__.items() if k != "conflicting_items"},
                    conflicting_items=conflict.conflicting_items + (updated_item.id,),
                )
                self.update(conflict.id, updated_conflict)

            return updated_item.id, "added_with_conflicts"

        # No duplicates or conflicts
        self.add(item)
        return item.id, "added"

    # -------------------------------------------------------------------------
    # Persistence Methods
    # -------------------------------------------------------------------------

    def save(self, path: str | None = None) -> bool:
        """Save memory store to disk.

        Args:
            path: Optional path override

        Returns:
            True if saved successfully
        """
        save_path = path or self._storage_path
        if not save_path:
            return False

        os.makedirs(os.path.dirname(save_path), exist_ok=True)

        data = {
            "version": "2.0",
            "items": [item.to_dict() for item in self._memories.values()],
            "last_modified": self._last_modified,
            "stats": self.get_stats(),
        }

        try:
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            return True
        except (IOError, OSError):
            return False

    def load(self, path: str | None = None) -> bool:
        """Load memory store from disk.

        Args:
            path: Optional path override

        Returns:
            True if loaded successfully
        """
        load_path = path or self._storage_path
        if not load_path or not os.path.exists(load_path):
            return False

        try:
            with open(load_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Clear existing
            self._memories.clear()
            self.rebuild_indexes()

            # Load items
            items = data.get("items", [])
            for item_data in items:
                item = MemoryItem.from_dict(item_data)
                self._memories[item.id] = item

            # Rebuild indexes
            self.rebuild_indexes()
            self._last_modified = data.get("last_modified")

            return True
        except (json.JSONDecodeError, IOError, OSError, KeyError):
            return False

    def get_stats(self) -> dict[str, Any]:
        """Get store statistics."""
        return {
            "total_items": len(self._memories),
            "knowledge_types": dict((k, len(v)) for k, v in self._knowledge_type_index.items()),
            "domains": dict((k, len(v)) for k, v in self._domain_index.items()),
            "validation_status": dict((k, len(v)) for k, v in self._validation_index.items()),
            "confidence_distribution": self._confidence_index.get_stats(),
            "last_modified": self._last_modified,
        }

    def __iter__(self) -> Iterator[MemoryItem]:
        """Iterate over all items."""
        return iter(self._memories.values())

    def __len__(self) -> int:
        """Get item count."""
        return len(self._memories)

    def __contains__(self, item_id: str) -> bool:
        """Check if item exists."""
        return item_id in self._memories