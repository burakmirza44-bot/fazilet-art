"""Advanced Retrieval Methods for Memory Store.

Provides enhanced retrieval capabilities including:
- Knowledge graph traversal
- Best practice chains
- RAG context building
- Validation-aware retrieval
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any

from app.memory.models import MemoryItem
from app.memory.store import MemoryStore


@dataclass
class RetrievalContext:
    """Context for retrieval operations."""

    domain: str = ""
    min_confidence: float = 0.5
    knowledge_types: list[str] = field(default_factory=list)
    validation_filter: str | None = None  # "approved", "pending", etc.
    limit: int = 10

    def to_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "min_confidence": self.min_confidence,
            "knowledge_types": self.knowledge_types,
            "validation_filter": self.validation_filter,
            "limit": self.limit,
        }


@dataclass
class RAGDocument:
    """A document for RAG context with metadata."""

    source: str
    content: str
    confidence: float
    validation: str
    success_rate: float
    knowledge_type: str | None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "content": self.content,
            "confidence": self.confidence,
            "validation": self.validation,
            "success_rate": self.success_rate,
            "knowledge_type": self.knowledge_type,
            "metadata": self.metadata,
        }


@dataclass
class RAGContext:
    """RAG context with retrieved documents and quality metrics."""

    domain: str
    retrieved_docs: list[RAGDocument] = field(default_factory=list)
    confidence_score: float = 0.0
    query: str = ""
    total_items_scanned: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "retrieved_docs": [d.to_dict() for d in self.retrieved_docs],
            "confidence_score": self.confidence_score,
            "query": self.query,
            "total_items_scanned": self.total_items_scanned,
        }

    def get_formatted_context(self) -> str:
        """Format documents for LLM context injection."""
        lines = []

        # Group by confidence level
        high_conf = [d for d in self.retrieved_docs if d.confidence >= 0.8]
        med_conf = [d for d in self.retrieved_docs if 0.5 <= d.confidence < 0.8]
        low_conf = [d for d in self.retrieved_docs if d.confidence < 0.5]

        if high_conf:
            lines.append("HIGH CONFIDENCE KNOWLEDGE (>= 80% confidence, validated):")
            for doc in high_conf:
                lines.append(f"  [{doc.knowledge_type or 'knowledge'}] {doc.content[:200]}...")
                lines.append(f"    Confidence: {doc.confidence:.0%}, Success: {doc.success_rate:.0%}")

        if med_conf:
            lines.append("\nMEDIUM CONFIDENCE KNOWLEDGE (50-80% confidence):")
            for doc in med_conf:
                lines.append(f"  [{doc.knowledge_type or 'knowledge'}] {doc.content[:200]}...")

        if low_conf:
            lines.append("\nEXPERIMENTAL KNOWLEDGE (< 50% confidence, needs validation):")
            for doc in low_conf:
                lines.append(f"  [{doc.knowledge_type or 'knowledge'}] {doc.content[:200]}...")

        return "\n".join(lines)


class AdvancedRetriever:
    """Advanced retrieval operations for MemoryStore."""

    def __init__(self, store: MemoryStore) -> None:
        """Initialize with a memory store.

        Args:
            store: MemoryStore instance
        """
        self._store = store

    def build_rag_context(
        self,
        query: str,
        domain: str = "",
        min_confidence: float = 0.7,
        limit: int = 10,
        validation_filter: str | None = "approved",
    ) -> RAGContext:
        """Build RAG context from memory store.

        Args:
            query: Search query
            domain: Domain filter
            min_confidence: Minimum confidence threshold
            limit: Maximum documents
            validation_filter: Validation status filter

        Returns:
            RAGContext with retrieved documents
        """
        # Perform semantic search
        results = self._store.semantic_search(
            query=query,
            min_confidence=min_confidence,
            limit=limit,
        )

        # Filter by domain and validation if specified
        filtered = []
        for item, score in results:
            if domain and item.domain != domain:
                continue
            if validation_filter and item.validation_status != validation_filter:
                continue
            filtered.append((item, score))

        # Build RAG documents
        docs = []
        for item, score in filtered:
            doc = RAGDocument(
                source=f"{item.knowledge_type or 'knowledge'}: {item.source or 'memory'}",
                content=item.content,
                confidence=item.confidence,
                validation=item.validation_status,
                success_rate=item.success_rate,
                knowledge_type=item.knowledge_type,
                metadata={
                    "prerequisites": list(item.prerequisites),
                    "learning_objectives": list(item.learning_objectives),
                    "related_items": list(item.related_items),
                    "steps": list(item.steps),
                },
            )
            docs.append(doc)

        # Calculate aggregate confidence
        if docs:
            avg_conf = sum(d.confidence for d in docs) / len(docs)
        else:
            avg_conf = 0.0

        return RAGContext(
            domain=domain,
            retrieved_docs=docs,
            confidence_score=avg_conf,
            query=query,
            total_items_scanned=len(self._store),
        )

    def get_workflow_chain(
        self,
        domain: str,
        workflow_type: str = "recipe",
        min_confidence: float = 0.7,
    ) -> list[MemoryItem]:
        """Get a chain of related workflow items.

        Args:
            domain: Domain to search
            workflow_type: Type of workflow (recipe, technique)
            min_confidence: Minimum confidence

        Returns:
            Ordered list of workflow items
        """
        # Get all recipes/techniques for domain
        items = self._store.retrieve_by_knowledge_type(workflow_type, domain)

        # Filter by confidence
        items = [i for i in items if i.confidence >= min_confidence]

        # Sort by quality score
        items.sort(key=lambda x: x.quality_score, reverse=True)

        # Build chain by following related items
        if not items:
            return []

        chain = [items[0]]
        visited = {items[0].id}

        current = items[0]
        while True:
            # Find next related item
            for related_id in current.related_items:
                if related_id not in visited:
                    related = self._store.get(related_id)
                    if related and related.confidence >= min_confidence:
                        chain.append(related)
                        visited.add(related_id)
                        current = related
                        break
            else:
                break

        return chain

    def get_knowledge_summary(self, domain: str) -> dict[str, Any]:
        """Get a summary of knowledge for a domain.

        Args:
            domain: Domain to summarize

        Returns:
            Summary statistics
        """
        items = self._store.retrieve_by_domain(domain)

        if not items:
            return {"domain": domain, "total": 0}

        # Calculate stats
        by_type: dict[str, int] = {}
        by_validation: dict[str, int] = {}
        avg_confidence = 0.0
        production_ready = 0
        needing_validation = 0

        for item in items:
            # By type
            ktype = item.knowledge_type or "unknown"
            by_type[ktype] = by_type.get(ktype, 0) + 1

            # By validation
            by_validation[item.validation_status] = by_validation.get(item.validation_status, 0) + 1

            # Confidence
            avg_confidence += item.confidence

            # Quality flags
            if item.is_production_ready:
                production_ready += 1
            if item.needs_revalidation:
                needing_validation += 1

        avg_confidence /= len(items)

        return {
            "domain": domain,
            "total": len(items),
            "by_type": by_type,
            "by_validation": by_validation,
            "avg_confidence": round(avg_confidence, 2),
            "production_ready": production_ready,
            "needing_validation": needing_validation,
            "most_used": max(items, key=lambda x: x.use_count).id if items else None,
            "highest_success": max(items, key=lambda x: x.success_rate).id if items else None,
        }

    def find_learning_path(
        self,
        domain: str,
        target_concepts: list[str],
        current_knowledge: list[str] | None = None,
    ) -> list[MemoryItem]:
        """Find a learning path to target concepts.

        Args:
            domain: Domain to search
            target_concepts: Concepts to learn
            current_knowledge: Already known concepts

        Returns:
            Ordered list of items forming a learning path
        """
        current = set(c.lower() for c in (current_knowledge or []))
        targets = set(c.lower() for c in target_concepts)

        # Find items that teach target concepts
        teaching_items = []
        for item in self._store.retrieve_by_domain(domain):
            if not item.learning_objectives:
                continue

            # Check if item teaches any target
            teaches = set(obj.lower() for obj in item.learning_objectives)
            if teaches & targets:
                # Check prerequisites
                prereqs = set(p.lower() for p in item.prerequisites)
                if prereqs <= current or not prereqs:
                    teaching_items.append(item)

        # Sort by confidence and prerequisite complexity
        teaching_items.sort(key=lambda x: (len(x.prerequisites), -x.confidence))

        return teaching_items

    def get_conflicting_knowledge(
        self,
        domain: str,
    ) -> list[tuple[MemoryItem, MemoryItem]]:
        """Find all conflicting knowledge pairs in a domain.

        Args:
            domain: Domain to check

        Returns:
            List of (item1, item2) conflict pairs
        """
        items = self._store.retrieve_by_domain(domain)
        conflicts = []
        seen_pairs = set()

        for item in items:
            for conflict_id in item.conflicting_items:
                pair = tuple(sorted([item.id, conflict_id]))
                if pair not in seen_pairs:
                    seen_pairs.add(pair)
                    conflict_item = self._store.get(conflict_id)
                    if conflict_item:
                        conflicts.append((item, conflict_item))

        return conflicts


class ValidationManager:
    """Manages validation workflow for memory items."""

    def __init__(self, store: MemoryStore) -> None:
        """Initialize with a memory store.

        Args:
            store: MemoryStore instance
        """
        self._store = store
        self._pending_reviews: list[str] = []

    def submit_for_review(
        self,
        item_id: str,
        reason: str = "",
        priority: str = "normal",
    ) -> bool:
        """Submit an item for validation review.

        Args:
            item_id: Item to validate
            reason: Reason for review
            priority: Priority level (high, normal, low)

        Returns:
            True if submitted successfully
        """
        item = self._store.get(item_id)
        if not item:
            return False

        # Update status to pending using dataclass replace
        updated = replace(
            item,
            validation_status="pending",
            metadata={**(item.metadata or {}), "review_reason": reason, "priority": priority},
        )

        self._store.update(item_id, updated)
        self._pending_reviews.append(item_id)

        return True

    def auto_submit_low_confidence(self, threshold: float = 0.7) -> int:
        """Auto-submit items below confidence threshold.

        Args:
            threshold: Confidence threshold

        Returns:
            Number of items submitted
        """
        count = 0
        for item in self._store.retrieve_by_confidence(0.0, threshold):
            if item.validation_status == "unvalidated":
                self.submit_for_review(
                    item.id,
                    reason="low_confidence",
                    priority="high",
                )
                count += 1

        return count

    def approve(
        self,
        item_id: str,
        notes: str = "",
        confidence_boost: float = 0.0,
    ) -> bool:
        """Approve a memory item.

        Args:
            item_id: Item to approve
            notes: Validator notes
            confidence_boost: Amount to increase confidence

        Returns:
            True if approved successfully
        """
        item = self._store.get(item_id)
        if not item:
            return False

        new_confidence = min(1.0, item.confidence + confidence_boost)

        updated = replace(
            item,
            validation_status="approved",
            confidence=new_confidence,
            last_validated=self._get_timestamp(),
            validator_notes=notes,
        )

        return self._store.update(item_id, updated)

    def reject(
        self,
        item_id: str,
        reason: str,
    ) -> bool:
        """Reject a memory item.

        Args:
            item_id: Item to reject
            reason: Rejection reason

        Returns:
            True if rejected successfully
        """
        item = self._store.get(item_id)
        if not item:
            return False

        updated = replace(
            item,
            validation_status="rejected",
            last_validated=self._get_timestamp(),
            validator_notes=reason,
        )

        return self._store.update(item_id, updated)

    def get_pending_reviews(self) -> list[MemoryItem]:
        """Get all items pending review."""
        return self._store.retrieve_by_validation_status("pending")

    def record_usage(
        self,
        item_id: str,
        success: bool,
        user_rating: float | None = None,
    ) -> bool:
        """Record usage of a memory item.

        Args:
            item_id: Item that was used
            success: Whether usage was successful
            user_rating: Optional user rating (1-5)

        Returns:
            True if recorded successfully
        """
        item = self._store.get(item_id)
        if not item:
            return False

        new_use_count = item.use_count + 1
        new_successful = item.successful_uses + (1 if success else 0)
        new_ratings = item.user_ratings

        if user_rating is not None:
            new_ratings = item.user_ratings + (user_rating,)

        # Auto-adjust confidence based on success rate
        new_confidence = 0.7 * item.confidence + 0.3 * (new_successful / new_use_count)

        updated = replace(
            item,
            use_count=new_use_count,
            successful_uses=new_successful,
            last_used=self._get_timestamp(),
            user_ratings=new_ratings,
            confidence=new_confidence,
        )

        return self._store.update(item_id, updated)

    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.now().isoformat()


def create_retriever(store: MemoryStore) -> AdvancedRetriever:
    """Create an advanced retriever for a store."""
    return AdvancedRetriever(store)


def create_validator(store: MemoryStore) -> ValidationManager:
    """Create a validation manager for a store."""
    return ValidationManager(store)