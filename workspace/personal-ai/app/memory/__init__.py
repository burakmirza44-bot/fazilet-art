"""Memory Module - Structured Knowledge Storage and Retrieval.

Provides:
- MemoryItem: Structured knowledge with confidence, validation, provenance
- MemoryStore: Multi-index storage for efficient retrieval
- AdvancedRetriever: RAG context building, knowledge graph traversal
- ValidationManager: Quality tracking and approval workflow

Quick Start:
    from app.memory import MemoryStore, MemoryItemBuilder, create_retriever

    # Create and store knowledge
    store = MemoryStore()

    recipe = (
        MemoryItemBuilder()
        .content("How to create procedural geometry in Houdini")
        .domain("houdini")
        .knowledge_type("recipe")
        .add_step(1, "Create SOP", "Add a geometry node")
        .add_step(2, "Add VEX", "Write wrangle code")
        .confidence(0.85)
        .key_concepts("geometry", "procedural", "sop")
        .build()
    )
    store.add(recipe)

    # Retrieve with quality filtering
    retriever = create_retriever(store)
    rag_ctx = retriever.build_rag_context(
        query="procedural geometry",
        domain="houdini",
        min_confidence=0.7,
    )
"""

from app.memory.models import (
    MemoryItem,
    MemoryItemBuilder,
    compute_relevance,
    create_pattern,
    create_recipe,
    create_technique,
    create_troubleshooting,
)
from app.memory.retrieval import (
    AdvancedRetriever,
    RAGContext,
    RAGDocument,
    RetrievalContext,
    ValidationManager,
    create_retriever,
    create_validator,
)
from app.memory.store import (
    MemoryStore,
    SortedIndex,
)

__all__ = [
    # Models
    "MemoryItem",
    "MemoryItemBuilder",
    "compute_relevance",
    "create_recipe",
    "create_technique",
    "create_troubleshooting",
    "create_pattern",
    # Store
    "MemoryStore",
    "SortedIndex",
    # Retrieval
    "AdvancedRetriever",
    "RetrievalContext",
    "RAGDocument",
    "RAGContext",
    "ValidationManager",
    "create_retriever",
    "create_validator",
]

__version__ = "2.0.0"