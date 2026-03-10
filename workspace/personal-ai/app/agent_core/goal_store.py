"""Goal Persistence Module.

Provides persistent storage for GoalArtifact instances with indexing,
lifecycle tracking, and integration with goal generation.

Key Features:
- Persistent storage to disk (JSON)
- Multi-index architecture for efficient retrieval
- Goal lifecycle tracking (status transitions)
- Session and task grouping
- Analytics and statistics
"""

from __future__ import annotations

import json
import os
from bisect import insort
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Iterator

from app.agent_core.goal_models import (
    GoalArtifact,
    GoalStatus,
    GoalType,
)


@dataclass
class GoalLifecycleEvent:
    """A lifecycle event for a goal.

    Tracks status transitions and timestamps.
    """

    goal_id: str
    from_status: str
    to_status: str
    timestamp: str
    reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "goal_id": self.goal_id,
            "from_status": self.from_status,
            "to_status": self.to_status,
            "timestamp": self.timestamp,
            "reason": self.reason,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GoalLifecycleEvent":
        """Create from dictionary."""
        return cls(
            goal_id=data["goal_id"],
            from_status=data["from_status"],
            to_status=data["to_status"],
            timestamp=data["timestamp"],
            reason=data.get("reason", ""),
            metadata=data.get("metadata", {}),
        )


@dataclass
class GoalStats:
    """Statistics about stored goals."""

    total_goals: int = 0
    by_status: dict[str, int] = field(default_factory=dict)
    by_type: dict[str, int] = field(default_factory=dict)
    by_domain: dict[str, int] = field(default_factory=dict)
    avg_confidence: float = 0.0
    blocked_count: int = 0
    completed_count: int = 0
    failed_count: int = 0
    session_count: int = 0
    task_count: int = 0
    last_modified: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_goals": self.total_goals,
            "by_status": self.by_status,
            "by_type": self.by_type,
            "by_domain": self.by_domain,
            "avg_confidence": self.avg_confidence,
            "blocked_count": self.blocked_count,
            "completed_count": self.completed_count,
            "failed_count": self.failed_count,
            "session_count": self.session_count,
            "task_count": self.task_count,
            "last_modified": self.last_modified,
        }


class GoalStore:
    """Persistent storage for GoalArtifact instances.

    Provides:
    - CRUD operations for goals
    - Multi-index retrieval (by session, task, domain, type, status)
    - Lifecycle tracking with status transitions
    - Persistence to disk (JSON)
    - Statistics and analytics

    Indexes:
    - session_index: O(1) lookup by session_id
    - task_index: O(1) lookup by task_id
    - domain_index: O(1) lookup by domain
    - type_index: O(1) lookup by goal_type
    - status_index: O(1) lookup by status
    - parent_index: O(1) lookup by parent_goal_id
    - confidence_index: Sorted index for confidence queries
    """

    def __init__(self, storage_path: str | None = None) -> None:
        """Initialize the goal store.

        Args:
            storage_path: Optional path for persistence (JSON file)
        """
        self._goals: dict[str, GoalArtifact] = {}
        self._storage_path = storage_path

        # Status tracking (stored separately from GoalArtifact)
        self._goal_status: dict[str, str] = {}
        self._lifecycle_events: list[GoalLifecycleEvent] = []

        # Multi-index architecture
        self._session_index: dict[str, list[str]] = defaultdict(list)
        self._task_index: dict[str, list[str]] = defaultdict(list)
        self._domain_index: dict[str, list[str]] = defaultdict(list)
        self._type_index: dict[str, list[str]] = defaultdict(list)
        self._status_index: dict[str, list[str]] = defaultdict(list)
        self._parent_index: dict[str, list[str]] = defaultdict(list)
        self._confidence_keys: list[float] = []
        self._confidence_index: dict[float, list[str]] = defaultdict(list)

        self._last_modified: str | None = None

    # -------------------------------------------------------------------------
    # CRUD Operations
    # -------------------------------------------------------------------------

    def add(self, goal: GoalArtifact, status: str = GoalStatus.GENERATED.value) -> str:
        """Add a goal to the store.

        Args:
            goal: GoalArtifact to add
            status: Initial status (default: GENERATED)

        Returns:
            Goal ID
        """
        self._goals[goal.goal_id] = goal
        self._goal_status[goal.goal_id] = status

        self._add_to_indexes(goal)
        self._last_modified = datetime.now().isoformat()

        return goal.goal_id

    def get(self, goal_id: str) -> GoalArtifact | None:
        """Get a goal by ID.

        Args:
            goal_id: Goal ID

        Returns:
            GoalArtifact or None if not found
        """
        return self._goals.get(goal_id)

    def get_status(self, goal_id: str) -> str | None:
        """Get the current status of a goal.

        Args:
            goal_id: Goal ID

        Returns:
            Status string or None if not found
        """
        return self._goal_status.get(goal_id)

    def update(self, goal: GoalArtifact) -> bool:
        """Update an existing goal.

        Args:
            goal: Updated GoalArtifact

        Returns:
            True if updated, False if not found
        """
        if goal.goal_id not in self._goals:
            return False

        old_goal = self._goals[goal.goal_id]
        self._remove_from_indexes(old_goal)

        self._goals[goal.goal_id] = goal
        self._add_to_indexes(goal)

        self._last_modified = datetime.now().isoformat()
        return True

    def update_status(
        self,
        goal_id: str,
        new_status: str,
        reason: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Update the status of a goal with lifecycle tracking.

        Args:
            goal_id: Goal ID
            new_status: New status value
            reason: Reason for status change
            metadata: Additional metadata

        Returns:
            True if updated, False if not found
        """
        if goal_id not in self._goals:
            return False

        old_status = self._goal_status.get(goal_id, GoalStatus.GENERATED.value)

        # Remove from old status index
        if goal_id in self._status_index.get(old_status, []):
            self._status_index[old_status].remove(goal_id)

        # Update status
        self._goal_status[goal_id] = new_status

        # Add to new status index
        self._status_index[new_status].append(goal_id)

        # Record lifecycle event
        event = GoalLifecycleEvent(
            goal_id=goal_id,
            from_status=old_status,
            to_status=new_status,
            timestamp=datetime.now().isoformat(),
            reason=reason,
            metadata=metadata or {},
        )
        self._lifecycle_events.append(event)

        self._last_modified = datetime.now().isoformat()
        return True

    def delete(self, goal_id: str) -> bool:
        """Delete a goal from the store.

        Args:
            goal_id: Goal ID to delete

        Returns:
            True if deleted, False if not found
        """
        if goal_id not in self._goals:
            return False

        goal = self._goals[goal_id]
        self._remove_from_indexes(goal)

        del self._goals[goal_id]
        if goal_id in self._goal_status:
            del self._goal_status[goal_id]

        self._last_modified = datetime.now().isoformat()
        return True

    # -------------------------------------------------------------------------
    # Index Management
    # -------------------------------------------------------------------------

    def _add_to_indexes(self, goal: GoalArtifact) -> None:
        """Add goal to all indexes."""
        # Session index
        if goal.session_id:
            self._session_index[goal.session_id].append(goal.goal_id)

        # Task index
        if goal.task_id:
            self._task_index[goal.task_id].append(goal.goal_id)

        # Domain index
        if goal.domain:
            self._domain_index[goal.domain].append(goal.goal_id)

        # Type index
        self._type_index[goal.goal_type].append(goal.goal_id)

        # Status index
        status = self._goal_status.get(goal.goal_id, GoalStatus.GENERATED.value)
        self._status_index[status].append(goal.goal_id)

        # Parent index
        if goal.parent_goal_id:
            self._parent_index[goal.parent_goal_id].append(goal.goal_id)

        # Confidence index (sorted)
        confidence_key = round(goal.confidence, 4)
        if confidence_key not in self._confidence_index:
            insort(self._confidence_keys, confidence_key)
        self._confidence_index[confidence_key].append(goal.goal_id)

    def _remove_from_indexes(self, goal: GoalArtifact) -> None:
        """Remove goal from all indexes."""
        # Session index
        if goal.session_id and goal.goal_id in self._session_index.get(goal.session_id, []):
            self._session_index[goal.session_id].remove(goal.goal_id)

        # Task index
        if goal.task_id and goal.goal_id in self._task_index.get(goal.task_id, []):
            self._task_index[goal.task_id].remove(goal.goal_id)

        # Domain index
        if goal.domain and goal.goal_id in self._domain_index.get(goal.domain, []):
            self._domain_index[goal.domain].remove(goal.goal_id)

        # Type index
        if goal.goal_id in self._type_index.get(goal.goal_type, []):
            self._type_index[goal.goal_type].remove(goal.goal_id)

        # Status index
        status = self._goal_status.get(goal.goal_id, GoalStatus.GENERATED.value)
        if goal.goal_id in self._status_index.get(status, []):
            self._status_index[status].remove(goal.goal_id)

        # Parent index
        if goal.parent_goal_id and goal.goal_id in self._parent_index.get(goal.parent_goal_id, []):
            self._parent_index[goal.parent_goal_id].remove(goal.goal_id)

        # Confidence index
        confidence_key = round(goal.confidence, 4)
        if goal.goal_id in self._confidence_index.get(confidence_key, []):
            self._confidence_index[confidence_key].remove(goal.goal_id)

    def rebuild_indexes(self) -> None:
        """Rebuild all indexes from scratch."""
        self._session_index.clear()
        self._task_index.clear()
        self._domain_index.clear()
        self._type_index.clear()
        self._status_index.clear()
        self._parent_index.clear()
        self._confidence_keys.clear()
        self._confidence_index.clear()

        for goal in self._goals.values():
            self._add_to_indexes(goal)

    # -------------------------------------------------------------------------
    # Retrieval Methods
    # -------------------------------------------------------------------------

    def retrieve_all(self) -> list[GoalArtifact]:
        """Get all goals."""
        return list(self._goals.values())

    def retrieve_by_session(self, session_id: str) -> list[GoalArtifact]:
        """Get all goals for a session.

        Args:
            session_id: Session ID

        Returns:
            List of goals for the session
        """
        ids = self._session_index.get(session_id, [])
        return [self._goals[i] for i in ids if i in self._goals]

    def retrieve_by_task(self, task_id: str) -> list[GoalArtifact]:
        """Get all goals for a task.

        Args:
            task_id: Task ID

        Returns:
            List of goals for the task
        """
        ids = self._task_index.get(task_id, [])
        return [self._goals[i] for i in ids if i in self._goals]

    def retrieve_by_domain(self, domain: str) -> list[GoalArtifact]:
        """Get all goals for a domain.

        Args:
            domain: Domain name

        Returns:
            List of goals for the domain
        """
        ids = self._domain_index.get(domain, [])
        return [self._goals[i] for i in ids if i in self._goals]

    def retrieve_by_type(self, goal_type: str | GoalType) -> list[GoalArtifact]:
        """Get all goals of a specific type.

        Args:
            goal_type: Goal type (string or GoalType)

        Returns:
            List of goals of that type
        """
        type_value = goal_type.value if isinstance(goal_type, GoalType) else goal_type
        ids = self._type_index.get(type_value, [])
        return [self._goals[i] for i in ids if i in self._goals]

    def retrieve_by_status(self, status: str | GoalStatus) -> list[GoalArtifact]:
        """Get all goals with a specific status.

        Args:
            status: Status (string or GoalStatus)

        Returns:
            List of goals with that status
        """
        status_value = status.value if isinstance(status, GoalStatus) else status
        ids = self._status_index.get(status_value, [])
        return [self._goals[i] for i in ids if i in self._goals]

    def retrieve_by_parent(self, parent_goal_id: str) -> list[GoalArtifact]:
        """Get all subgoals of a parent goal.

        Args:
            parent_goal_id: Parent goal ID

        Returns:
            List of subgoals
        """
        ids = self._parent_index.get(parent_goal_id, [])
        return [self._goals[i] for i in ids if i in self._goals]

    def retrieve_by_confidence(
        self,
        min_confidence: float = 0.0,
        max_confidence: float = 1.0,
        sort_descending: bool = True,
    ) -> list[GoalArtifact]:
        """Get goals with confidence in the specified range.

        Args:
            min_confidence: Minimum confidence threshold
            max_confidence: Maximum confidence threshold
            sort_descending: Sort by confidence descending

        Returns:
            List of matching goals
        """
        from bisect import bisect_left, bisect_right

        min_key = round(min_confidence, 4)
        max_key = round(max_confidence, 4)

        left = bisect_left(self._confidence_keys, min_key)
        right = bisect_right(self._confidence_keys, max_key)

        ids = []
        for i in range(left, right):
            key = self._confidence_keys[i]
            ids.extend(self._confidence_index[key])

        goals = [self._goals[i] for i in ids if i in self._goals]

        if sort_descending:
            goals.sort(key=lambda g: g.confidence, reverse=True)

        return goals

    def retrieve_blocked(self) -> list[GoalArtifact]:
        """Get all blocked goals.

        Returns:
            List of blocked goals
        """
        return [g for g in self._goals.values() if g.is_blocked]

    def retrieve_root_goals(self) -> list[GoalArtifact]:
        """Get all root goals (no parent).

        Returns:
            List of root goals
        """
        return [g for g in self._goals.values() if g.parent_goal_id is None]

    def retrieve_pending(self) -> list[GoalArtifact]:
        """Get all goals that are pending execution.

        Returns:
            List of pending goals (GENERATED, VALIDATED, SCHEDULED, READY)
        """
        pending_statuses = {
            GoalStatus.GENERATED.value,
            GoalStatus.VALIDATED.value,
            GoalStatus.SCHEDULED.value,
            GoalStatus.READY.value,
        }

        ids = []
        for status in pending_statuses:
            ids.extend(self._status_index.get(status, []))

        return [self._goals[i] for i in ids if i in self._goals]

    def retrieve_completed(self) -> list[GoalArtifact]:
        """Get all completed goals.

        Returns:
            List of completed goals
        """
        return self.retrieve_by_status(GoalStatus.COMPLETED)

    def retrieve_failed(self) -> list[GoalArtifact]:
        """Get all failed goals.

        Returns:
            List of failed goals
        """
        return self.retrieve_by_status(GoalStatus.FAILED)

    def get_goal_tree(self, goal_id: str) -> dict[str, Any]:
        """Get the goal tree starting from a root goal.

        Args:
            goal_id: Root goal ID

        Returns:
            Dictionary with goal and nested subgoals
        """
        goal = self._goals.get(goal_id)
        if not goal:
            return {"goal": None, "subgoals": []}

        subgoals = self.retrieve_by_parent(goal_id)

        return {
            "goal": goal,
            "status": self._goal_status.get(goal_id, GoalStatus.GENERATED.value),
            "subgoals": [self.get_goal_tree(sg.goal_id) for sg in subgoals],
        }

    def get_lifecycle_history(self, goal_id: str) -> list[GoalLifecycleEvent]:
        """Get the lifecycle history for a goal.

        Args:
            goal_id: Goal ID

        Returns:
            List of lifecycle events for the goal
        """
        return [e for e in self._lifecycle_events if e.goal_id == goal_id]

    # -------------------------------------------------------------------------
    # Analytics
    # -------------------------------------------------------------------------

    def get_stats(self) -> GoalStats:
        """Get statistics about stored goals.

        Returns:
            GoalStats with aggregated metrics
        """
        if not self._goals:
            return GoalStats()

        by_status: dict[str, int] = {}
        for status, ids in self._status_index.items():
            by_status[status] = len(ids)

        by_type: dict[str, int] = {}
        for goal_type, ids in self._type_index.items():
            by_type[goal_type] = len(ids)

        by_domain: dict[str, int] = {}
        for domain, ids in self._domain_index.items():
            by_domain[domain] = len(ids)

        total_confidence = sum(g.confidence for g in self._goals.values())
        avg_confidence = total_confidence / len(self._goals) if self._goals else 0.0

        sessions = set(g.session_id for g in self._goals.values() if g.session_id)
        tasks = set(g.task_id for g in self._goals.values() if g.task_id)

        return GoalStats(
            total_goals=len(self._goals),
            by_status=by_status,
            by_type=by_type,
            by_domain=by_domain,
            avg_confidence=avg_confidence,
            blocked_count=len(self.retrieve_blocked()),
            completed_count=len(self.retrieve_completed()),
            failed_count=len(self.retrieve_failed()),
            session_count=len(sessions),
            task_count=len(tasks),
            last_modified=self._last_modified or "",
        )

    def get_session_summary(self, session_id: str) -> dict[str, Any]:
        """Get a summary of goals for a session.

        Args:
            session_id: Session ID

        Returns:
            Dictionary with session goal summary
        """
        goals = self.retrieve_by_session(session_id)

        if not goals:
            return {
                "session_id": session_id,
                "goal_count": 0,
                "summary": "No goals for session",
            }

        by_type: dict[str, int] = defaultdict(int)
        by_status: dict[str, int] = defaultdict(int)

        for goal in goals:
            by_type[goal.goal_type] += 1
            status = self._goal_status.get(goal.goal_id, GoalStatus.GENERATED.value)
            by_status[status] += 1

        return {
            "session_id": session_id,
            "goal_count": len(goals),
            "by_type": dict(by_type),
            "by_status": dict(by_status),
            "root_goals": [g.goal_id for g in goals if g.parent_goal_id is None],
            "blocked_goals": [g.goal_id for g in goals if g.is_blocked],
            "avg_confidence": sum(g.confidence for g in goals) / len(goals),
        }

    def get_task_summary(self, task_id: str) -> dict[str, Any]:
        """Get a summary of goals for a task.

        Args:
            task_id: Task ID

        Returns:
            Dictionary with task goal summary
        """
        goals = self.retrieve_by_task(task_id)

        if not goals:
            return {
                "task_id": task_id,
                "goal_count": 0,
                "summary": "No goals for task",
            }

        by_type: dict[str, int] = defaultdict(int)
        by_status: dict[str, int] = defaultdict(int)

        for goal in goals:
            by_type[goal.goal_type] += 1
            status = self._goal_status.get(goal.goal_id, GoalStatus.GENERATED.value)
            by_status[status] += 1

        return {
            "task_id": task_id,
            "goal_count": len(goals),
            "by_type": dict(by_type),
            "by_status": dict(by_status),
            "domains": list(set(g.domain for g in goals if g.domain)),
            "avg_confidence": sum(g.confidence for g in goals) / len(goals),
        }

    # -------------------------------------------------------------------------
    # Persistence
    # -------------------------------------------------------------------------

    def save(self, path: str | None = None) -> bool:
        """Save goal store to disk.

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
            "version": "1.0.0",
            "goals": [g.to_dict() for g in self._goals.values()],
            "statuses": self._goal_status,
            "lifecycle_events": [e.to_dict() for e in self._lifecycle_events],
            "stats": self.get_stats().to_dict(),
            "last_modified": self._last_modified,
        }

        try:
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            return True
        except (IOError, OSError):
            return False

    def load(self, path: str | None = None) -> bool:
        """Load goal store from disk.

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
            self._goals.clear()
            self._goal_status.clear()
            self._lifecycle_events.clear()

            # Load goals
            for goal_data in data.get("goals", []):
                goal = GoalArtifact.from_dict(goal_data)
                self._goals[goal.goal_id] = goal

            # Load statuses
            self._goal_status = data.get("statuses", {})

            # Load lifecycle events
            for event_data in data.get("lifecycle_events", []):
                event = GoalLifecycleEvent.from_dict(event_data)
                self._lifecycle_events.append(event)

            # Rebuild indexes
            self.rebuild_indexes()
            self._last_modified = data.get("last_modified")

            return True
        except (json.JSONDecodeError, IOError, OSError, KeyError):
            return False

    # -------------------------------------------------------------------------
    # Magic Methods
    # -------------------------------------------------------------------------

    def __iter__(self) -> Iterator[GoalArtifact]:
        """Iterate over all goals."""
        return iter(self._goals.values())

    def __len__(self) -> int:
        """Get goal count."""
        return len(self._goals)

    def __contains__(self, goal_id: str) -> bool:
        """Check if goal exists."""
        return goal_id in self._goals


# -------------------------------------------------------------------------
# Factory Functions
# -------------------------------------------------------------------------

def create_goal_store(
    repo_root: str = ".",
    filename: str = "goals.json",
) -> GoalStore:
    """Create a GoalStore with default storage path.

    Args:
        repo_root: Repository root directory
        filename: Storage filename

    Returns:
        GoalStore instance
    """
    storage_path = os.path.join(repo_root, "data", "goals", filename)
    return GoalStore(storage_path=storage_path)