"""Runtime Memory Management Module.

Provides memory retrieval and writeback for runtime execution,
enabling success/failure pattern reuse across task executions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RuntimeMemoryContext:
    """Context for runtime memory retrieval and influence.

    This dataclass holds memory patterns retrieved before execution
    and tracks their influence on execution decisions.
    """

    memory_influenced: bool = False
    success_pattern_count: int = 0
    failure_pattern_count: int = 0
    repair_pattern_count: int = 0
    success_patterns: list[dict] = field(default_factory=list)
    failure_patterns: list[dict] = field(default_factory=list)
    repair_patterns: list[dict] = field(default_factory=list)
    domain: str = ""
    query: str = ""

    @property
    def total_patterns(self) -> int:
        """Total number of patterns retrieved."""
        return self.success_pattern_count + self.failure_pattern_count + self.repair_pattern_count

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "memory_influenced": self.memory_influenced,
            "success_pattern_count": self.success_pattern_count,
            "failure_pattern_count": self.failure_pattern_count,
            "repair_pattern_count": self.repair_pattern_count,
            "total_patterns": self.total_patterns,
            "success_patterns": self.success_patterns,
            "failure_patterns": self.failure_patterns,
            "repair_patterns": self.repair_patterns,
            "domain": self.domain,
            "query": self.query,
        }


def build_runtime_memory_context(
    domain: str,
    query: str,
    repo_root: str = ".",
    max_success: int = 3,
    max_failure: int = 3,
    max_repair: int = 2,
) -> RuntimeMemoryContext:
    """Build runtime memory context by retrieving relevant patterns.

    This function retrieves success, failure, and repair patterns from
    memory stores to influence execution decisions.

    Args:
        domain: Execution domain (e.g., "touchdesigner", "houdini")
        query: Query string to match against patterns
        repo_root: Repository root path for memory stores
        max_success: Maximum success patterns to retrieve
        max_failure: Maximum failure patterns to retrieve
        max_repair: Maximum repair patterns to retrieve

    Returns:
        RuntimeMemoryContext with retrieved patterns
    """
    context = RuntimeMemoryContext(
        domain=domain,
        query=query,
        memory_influenced=False,
    )

    # Try to load success patterns
    try:
        success_patterns = _load_patterns(
            repo_root=repo_root,
            pattern_type="success",
            domain=domain,
            query=query,
            limit=max_success,
        )
        context.success_patterns = success_patterns
        context.success_pattern_count = len(success_patterns)
    except Exception:
        # Memory store may not exist yet
        context.success_patterns = []
        context.success_pattern_count = 0

    # Try to load failure patterns
    try:
        failure_patterns = _load_patterns(
            repo_root=repo_root,
            pattern_type="failure",
            domain=domain,
            query=query,
            limit=max_failure,
        )
        context.failure_patterns = failure_patterns
        context.failure_pattern_count = len(failure_patterns)
    except Exception:
        context.failure_patterns = []
        context.failure_pattern_count = 0

    # Try to load repair patterns
    try:
        repair_patterns = _load_patterns(
            repo_root=repo_root,
            pattern_type="repair",
            domain=domain,
            query=query,
            limit=max_repair,
        )
        context.repair_patterns = repair_patterns
        context.repair_pattern_count = len(repair_patterns)
    except Exception:
        context.repair_patterns = []
        context.repair_pattern_count = 0

    # Mark as influenced if any patterns were retrieved
    context.memory_influenced = context.total_patterns > 0

    return context


def _load_patterns(
    repo_root: str,
    pattern_type: str,
    domain: str,
    query: str,
    limit: int,
) -> list[dict]:
    """Load patterns from memory store.

    Args:
        repo_root: Repository root path
        pattern_type: Type of pattern (success, failure, repair)
        domain: Domain to filter by
        query: Query string to match
        limit: Maximum patterns to return

    Returns:
        List of pattern dictionaries
    """
    import json
    import os

    # Define memory store paths
    memory_paths = {
        "success": os.path.join(repo_root, "data", "memory", "success_patterns.json"),
        "failure": os.path.join(repo_root, "data", "memory", "failure_patterns.json"),
        "repair": os.path.join(repo_root, "data", "memory", "repair_patterns.json"),
    }

    path = memory_paths.get(pattern_type)
    if not path or not os.path.exists(path):
        return []

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        patterns = data if isinstance(data, list) else data.get("patterns", [])

        # Filter by domain if specified
        if domain:
            patterns = [p for p in patterns if p.get("domain") == domain or not p.get("domain")]

        # Simple query matching (can be enhanced with semantic search)
        if query:
            query_lower = query.lower()
            patterns = [
                p for p in patterns
                if query_lower in str(p.get("description", "")).lower()
                or query_lower in str(p.get("query", "")).lower()
                or query_lower in str(p.get("tags", [])).__str__().lower()
            ]

        # Sort by relevance/score if available
        patterns.sort(key=lambda p: p.get("score", 0) or p.get("relevance", 0), reverse=True)

        return patterns[:limit]

    except (json.JSONDecodeError, IOError, OSError):
        return []


def get_memory_influence_summary(context: RuntimeMemoryContext) -> dict[str, Any]:
    """Get a summary of memory influence for reporting.

    Args:
        context: RuntimeMemoryContext to summarize

    Returns:
        Dictionary with memory influence summary
    """
    return {
        "memory_influenced": context.memory_influenced,
        "success_patterns_used": context.success_pattern_count,
        "failure_patterns_used": context.failure_pattern_count,
        "repair_patterns_used": context.repair_pattern_count,
        "total_patterns": context.total_patterns,
        "domain": context.domain,
    }


def save_execution_result(
    domain: str,
    query: str,
    success: bool,
    result_data: dict[str, Any],
    repo_root: str = ".",
) -> bool:
    """Save execution result to memory store for future retrieval.

    Args:
        domain: Execution domain
        query: Original query/task summary
        success: Whether execution was successful
        result_data: Result data to save
        repo_root: Repository root path

    Returns:
        True if saved successfully
    """
    import json
    import os
    from datetime import datetime

    # Determine pattern type
    pattern_type = "success" if success else "failure"

    # Build memory path
    memory_dir = os.path.join(repo_root, "data", "memory")
    memory_path = os.path.join(memory_dir, f"{pattern_type}_patterns.json")

    # Ensure directory exists
    os.makedirs(memory_dir, exist_ok=True)

    # Load existing patterns
    patterns = []
    if os.path.exists(memory_path):
        try:
            with open(memory_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                patterns = data if isinstance(data, list) else data.get("patterns", [])
        except (json.JSONDecodeError, IOError):
            patterns = []

    # Create new pattern entry
    new_pattern = {
        "id": f"{pattern_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(patterns)}",
        "domain": domain,
        "query": query,
        "description": result_data.get("description", query),
        "timestamp": datetime.now().isoformat(),
        "data": result_data,
        "tags": result_data.get("tags", []),
        "score": 1.0 if success else 0.0,
    }

    # Add to patterns
    patterns.append(new_pattern)

    # Keep only recent patterns (limit to 100)
    patterns = patterns[-100:]

    # Save back
    try:
        with open(memory_path, "w", encoding="utf-8") as f:
            json.dump({"patterns": patterns}, f, indent=2)
        return True
    except (IOError, OSError):
        return False
