"""Tests for Goal Store Module.

Tests persistent storage of GoalArtifact instances with indexing,
lifecycle tracking, and retrieval.
"""

import json
import os
import tempfile
from datetime import datetime

import pytest

from app.agent_core.goal_models import (
    DomainHint,
    GoalArtifact,
    GoalSourceSignal,
    GoalStatus,
    GoalType,
)
from app.agent_core.goal_store import (
    GoalLifecycleEvent,
    GoalStats,
    GoalStore,
    create_goal_store,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def sample_goal():
    """Create a sample goal artifact."""
    return GoalArtifact.create(
        goal_type=GoalType.ROOT_GOAL,
        title="Create noise terrain",
        description="Create a procedural noise terrain in Houdini",
        domain="houdini",
        task_id="task_001",
        session_id="session_001",
        confidence=0.85,
    )


@pytest.fixture
def subgoal(sample_goal):
    """Create a sample subgoal."""
    return GoalArtifact.create(
        goal_type=GoalType.SUBGOAL,
        title="Add noise SOP",
        description="Add noise SOP to geometry",
        domain="houdini",
        task_id="task_001",
        session_id="session_001",
        parent_goal_id=sample_goal.goal_id,
        confidence=0.75,
    )


@pytest.fixture
def repair_goal():
    """Create a sample repair goal."""
    return GoalArtifact.create(
        goal_type=GoalType.REPAIR_GOAL,
        title="Fix bridge connection",
        description="Reconnect to TouchDesigner bridge",
        domain="touchdesigner",
        task_id="task_002",
        session_id="session_001",
        confidence=0.60,
    )


@pytest.fixture
def store():
    """Create an empty GoalStore."""
    return GoalStore()


@pytest.fixture
def store_with_goals(store, sample_goal, subgoal, repair_goal):
    """Create a GoalStore with sample goals."""
    store.add(sample_goal)
    store.add(subgoal)
    store.add(repair_goal)
    return store


@pytest.fixture
def temp_storage_path():
    """Create a temporary file path for storage."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield os.path.join(tmpdir, "goals.json")


# ============================================================================
# GoalLifecycleEvent Tests
# ============================================================================

class TestGoalLifecycleEvent:
    """Tests for GoalLifecycleEvent dataclass."""

    def test_create_event(self):
        """Test creating a lifecycle event."""
        event = GoalLifecycleEvent(
            goal_id="goal_001",
            from_status="generated",
            to_status="scheduled",
            timestamp="2024-01-01T12:00:00",
            reason="Ready for execution",
        )

        assert event.goal_id == "goal_001"
        assert event.from_status == "generated"
        assert event.to_status == "scheduled"

    def test_event_serialization(self):
        """Test event serialization roundtrip."""
        event = GoalLifecycleEvent(
            goal_id="goal_001",
            from_status="generated",
            to_status="completed",
            timestamp="2024-01-01T12:00:00",
            reason="Success",
            metadata={"duration_ms": 1500},
        )

        data = event.to_dict()
        restored = GoalLifecycleEvent.from_dict(data)

        assert restored.goal_id == event.goal_id
        assert restored.from_status == event.from_status
        assert restored.to_status == event.to_status
        assert restored.metadata == event.metadata


# ============================================================================
# GoalStore CRUD Tests
# ============================================================================

class TestGoalStoreCRUD:
    """Tests for GoalStore CRUD operations."""

    def test_add_goal(self, store, sample_goal):
        """Test adding a goal."""
        goal_id = store.add(sample_goal)

        assert goal_id == sample_goal.goal_id
        assert len(store) == 1

    def test_get_goal(self, store, sample_goal):
        """Test getting a goal by ID."""
        store.add(sample_goal)

        retrieved = store.get(sample_goal.goal_id)

        assert retrieved is not None
        assert retrieved.goal_id == sample_goal.goal_id
        assert retrieved.title == sample_goal.title

    def test_get_nonexistent_goal(self, store):
        """Test getting a nonexistent goal."""
        retrieved = store.get("nonexistent")

        assert retrieved is None

    def test_update_goal(self, store, sample_goal):
        """Test updating a goal."""
        store.add(sample_goal)

        # Update the goal
        updated = GoalArtifact(
            goal_id=sample_goal.goal_id,
            title="Updated title",
            description="Updated description",
            domain=sample_goal.domain,
            goal_type=sample_goal.goal_type,
            confidence=0.95,
        )

        result = store.update(updated)

        assert result is True
        retrieved = store.get(sample_goal.goal_id)
        assert retrieved.title == "Updated title"
        assert retrieved.confidence == 0.95

    def test_update_nonexistent_goal(self, store):
        """Test updating a nonexistent goal."""
        goal = GoalArtifact.create(
            goal_type=GoalType.ROOT_GOAL,
            title="Test",
            description="Test",
        )

        result = store.update(goal)

        assert result is False

    def test_delete_goal(self, store, sample_goal):
        """Test deleting a goal."""
        store.add(sample_goal)

        result = store.delete(sample_goal.goal_id)

        assert result is True
        assert store.get(sample_goal.goal_id) is None
        assert len(store) == 0

    def test_delete_nonexistent_goal(self, store):
        """Test deleting a nonexistent goal."""
        result = store.delete("nonexistent")

        assert result is False

    def test_goal_in_store(self, store, sample_goal):
        """Test checking if goal is in store."""
        store.add(sample_goal)

        assert sample_goal.goal_id in store
        assert "nonexistent" not in store


# ============================================================================
# GoalStore Status Tests
# ============================================================================

class TestGoalStoreStatus:
    """Tests for GoalStore status tracking."""

    def test_get_status(self, store, sample_goal):
        """Test getting goal status."""
        store.add(sample_goal)

        status = store.get_status(sample_goal.goal_id)

        assert status == GoalStatus.GENERATED.value

    def test_update_status(self, store, sample_goal):
        """Test updating goal status."""
        store.add(sample_goal)

        result = store.update_status(
            sample_goal.goal_id,
            GoalStatus.SCHEDULED.value,
            reason="Ready for execution",
        )

        assert result is True
        assert store.get_status(sample_goal.goal_id) == GoalStatus.SCHEDULED.value

    def test_status_lifecycle_events(self, store, sample_goal):
        """Test that status changes create lifecycle events."""
        store.add(sample_goal)

        store.update_status(sample_goal.goal_id, GoalStatus.VALIDATED.value, reason="Validated")
        store.update_status(sample_goal.goal_id, GoalStatus.SCHEDULED.value, reason="Scheduled")

        history = store.get_lifecycle_history(sample_goal.goal_id)

        assert len(history) == 2
        assert history[0].to_status == GoalStatus.VALIDATED.value
        assert history[1].to_status == GoalStatus.SCHEDULED.value

    def test_update_status_nonexistent(self, store):
        """Test updating status of nonexistent goal."""
        result = store.update_status("nonexistent", GoalStatus.COMPLETED.value)

        assert result is False


# ============================================================================
# GoalStore Index Tests
# ============================================================================

class TestGoalStoreIndexes:
    """Tests for GoalStore index operations."""

    def test_retrieve_by_session(self, store_with_goals, sample_goal, subgoal, repair_goal):
        """Test retrieving goals by session."""
        goals = store_with_goals.retrieve_by_session("session_001")

        assert len(goals) == 3

    def test_retrieve_by_task(self, store_with_goals, sample_goal, subgoal):
        """Test retrieving goals by task."""
        goals = store_with_goals.retrieve_by_task("task_001")

        assert len(goals) == 2

    def test_retrieve_by_domain(self, store_with_goals, sample_goal, subgoal):
        """Test retrieving goals by domain."""
        goals = store_with_goals.retrieve_by_domain("houdini")

        assert len(goals) == 2

        td_goals = store_with_goals.retrieve_by_domain("touchdesigner")
        assert len(td_goals) == 1

    def test_retrieve_by_type(self, store_with_goals, sample_goal):
        """Test retrieving goals by type."""
        goals = store_with_goals.retrieve_by_type(GoalType.ROOT_GOAL)

        assert len(goals) == 1
        assert goals[0].goal_type == GoalType.ROOT_GOAL.value

    def test_retrieve_by_status(self, store_with_goals):
        """Test retrieving goals by status."""
        # All goals start as GENERATED
        goals = store_with_goals.retrieve_by_status(GoalStatus.GENERATED)

        assert len(goals) == 3

        # Update one status
        first_goal = list(store_with_goals._goals.values())[0]
        store_with_goals.update_status(first_goal.goal_id, GoalStatus.COMPLETED.value)

        generated_goals = store_with_goals.retrieve_by_status(GoalStatus.GENERATED)
        completed_goals = store_with_goals.retrieve_by_status(GoalStatus.COMPLETED)

        assert len(generated_goals) == 2
        assert len(completed_goals) == 1

    def test_retrieve_by_parent(self, store_with_goals, sample_goal, subgoal):
        """Test retrieving goals by parent."""
        subgoals = store_with_goals.retrieve_by_parent(sample_goal.goal_id)

        assert len(subgoals) == 1
        assert subgoals[0].goal_id == subgoal.goal_id

    def test_retrieve_by_confidence(self, store_with_goals):
        """Test retrieving goals by confidence range."""
        high_confidence = store_with_goals.retrieve_by_confidence(min_confidence=0.7)

        assert len(high_confidence) == 2  # 0.85 and 0.75

        low_confidence = store_with_goals.retrieve_by_confidence(max_confidence=0.7)

        assert len(low_confidence) == 1  # 0.60

    def test_retrieve_blocked(self, store, sample_goal):
        """Test retrieving blocked goals."""
        blocked_goal = GoalArtifact.create(
            goal_type=GoalType.ROOT_GOAL,
            title="Blocked goal",
            description="A blocked goal",
        )
        blocked_goal.block("Precondition not met")

        store.add(sample_goal)
        store.add(blocked_goal)

        blocked = store.retrieve_blocked()

        assert len(blocked) == 1
        assert blocked[0].goal_id == blocked_goal.goal_id

    def test_retrieve_root_goals(self, store_with_goals):
        """Test retrieving root goals."""
        roots = store_with_goals.retrieve_root_goals()

        assert len(roots) == 2  # sample_goal and repair_goal (no parents)

    def test_retrieve_pending(self, store, sample_goal):
        """Test retrieving pending goals."""
        store.add(sample_goal, status=GoalStatus.SCHEDULED.value)

        pending = store.retrieve_pending()

        assert len(pending) == 1

    def test_retrieve_completed(self, store, sample_goal):
        """Test retrieving completed goals."""
        store.add(sample_goal)
        store.update_status(sample_goal.goal_id, GoalStatus.COMPLETED.value)

        completed = store.retrieve_completed()

        assert len(completed) == 1

    def test_retrieve_failed(self, store, sample_goal):
        """Test retrieving failed goals."""
        store.add(sample_goal)
        store.update_status(sample_goal.goal_id, GoalStatus.FAILED.value, reason="Execution error")

        failed = store.retrieve_failed()

        assert len(failed) == 1

    def test_rebuild_indexes(self, store_with_goals):
        """Test rebuilding indexes."""
        # Clear indexes manually
        store_with_goals._session_index.clear()
        store_with_goals._domain_index.clear()

        # Rebuild
        store_with_goals.rebuild_indexes()

        # Verify indexes are restored
        session_goals = store_with_goals.retrieve_by_session("session_001")
        assert len(session_goals) == 3


# ============================================================================
# GoalStore Tree Tests
# ============================================================================

class TestGoalStoreTree:
    """Tests for goal tree operations."""

    def test_get_goal_tree(self, store_with_goals, sample_goal, subgoal):
        """Test getting goal tree."""
        tree = store_with_goals.get_goal_tree(sample_goal.goal_id)

        assert tree["goal"].goal_id == sample_goal.goal_id
        assert len(tree["subgoals"]) == 1
        assert tree["subgoals"][0]["goal"].goal_id == subgoal.goal_id

    def test_get_goal_tree_nonexistent(self, store):
        """Test getting tree for nonexistent goal."""
        tree = store.get_goal_tree("nonexistent")

        assert tree["goal"] is None
        assert tree["subgoals"] == []

    def test_get_lifecycle_history(self, store, sample_goal):
        """Test getting lifecycle history."""
        store.add(sample_goal)
        store.update_status(sample_goal.goal_id, GoalStatus.VALIDATED.value)
        store.update_status(sample_goal.goal_id, GoalStatus.COMPLETED.value)

        history = store.get_lifecycle_history(sample_goal.goal_id)

        assert len(history) == 2


# ============================================================================
# GoalStore Analytics Tests
# ============================================================================

class TestGoalStoreAnalytics:
    """Tests for goal store analytics."""

    def test_get_stats(self, store_with_goals):
        """Test getting store statistics."""
        stats = store_with_goals.get_stats()

        assert stats.total_goals == 3
        assert stats.session_count == 1
        assert stats.task_count == 2
        assert stats.avg_confidence > 0

    def test_get_stats_empty(self, store):
        """Test getting stats for empty store."""
        stats = store.get_stats()

        assert stats.total_goals == 0
        assert stats.avg_confidence == 0.0

    def test_get_session_summary(self, store_with_goals):
        """Test getting session summary."""
        summary = store_with_goals.get_session_summary("session_001")

        assert summary["session_id"] == "session_001"
        assert summary["goal_count"] == 3
        assert "by_type" in summary
        assert "by_status" in summary

    def test_get_session_summary_empty(self, store):
        """Test getting summary for nonexistent session."""
        summary = store.get_session_summary("nonexistent")

        assert summary["goal_count"] == 0

    def test_get_task_summary(self, store_with_goals):
        """Test getting task summary."""
        summary = store_with_goals.get_task_summary("task_001")

        assert summary["task_id"] == "task_001"
        assert summary["goal_count"] == 2
        assert "houdini" in summary["domains"]


# ============================================================================
# GoalStore Persistence Tests
# ============================================================================

class TestGoalStorePersistence:
    """Tests for goal store persistence."""

    def test_save_and_load(self, store_with_goals, temp_storage_path):
        """Test saving and loading the store."""
        # Save
        result = store_with_goals.save(temp_storage_path)
        assert result is True

        # Create new store and load
        new_store = GoalStore()
        result = new_store.load(temp_storage_path)
        assert result is True

        # Verify data
        assert len(new_store) == 3
        assert new_store.get_status(list(new_store._goals.keys())[0]) is not None

    def test_save_without_path(self, store):
        """Test saving without a path set."""
        result = store.save()

        assert result is False

    def test_load_nonexistent_file(self, store):
        """Test loading from nonexistent file."""
        result = store.load("/nonexistent/path/goals.json")

        assert result is False

    def test_lifecycle_persistence(self, store, sample_goal, temp_storage_path):
        """Test that lifecycle events are persisted."""
        store.add(sample_goal)
        store.update_status(sample_goal.goal_id, GoalStatus.VALIDATED.value)
        store.update_status(sample_goal.goal_id, GoalStatus.COMPLETED.value)

        # Save and load
        store.save(temp_storage_path)

        new_store = GoalStore()
        new_store.load(temp_storage_path)

        history = new_store.get_lifecycle_history(sample_goal.goal_id)
        assert len(history) == 2

    def test_json_format(self, store_with_goals, temp_storage_path):
        """Test that saved JSON is valid and readable."""
        store_with_goals.save(temp_storage_path)

        with open(temp_storage_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "version" in data
        assert "goals" in data
        assert "statuses" in data
        assert "lifecycle_events" in data
        assert "stats" in data


# ============================================================================
# Factory Function Tests
# ============================================================================

class TestFactoryFunctions:
    """Tests for factory functions."""

    def test_create_goal_store(self):
        """Test create_goal_store factory function."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = create_goal_store(repo_root=tmpdir, filename="test_goals.json")

            assert store._storage_path is not None
            assert "test_goals.json" in store._storage_path


# ============================================================================
# Edge Case Tests
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_store_operations(self, store):
        """Test operations on empty store."""
        assert len(store) == 0
        assert list(store) == []
        assert store.retrieve_all() == []
        assert store.get_stats().total_goals == 0

    def test_multiple_status_updates(self, store, sample_goal):
        """Test multiple status updates in sequence."""
        store.add(sample_goal)

        statuses = [
            GoalStatus.VALIDATED,
            GoalStatus.SCHEDULED,
            GoalStatus.READY,
            GoalStatus.IN_PROGRESS,
            GoalStatus.COMPLETED,
        ]

        for status in statuses:
            result = store.update_status(sample_goal.goal_id, status.value)
            assert result is True

        assert store.get_status(sample_goal.goal_id) == GoalStatus.COMPLETED.value

    def test_deep_goal_tree(self, store):
        """Test goal tree with multiple levels."""
        root = GoalArtifact.create(
            goal_type=GoalType.ROOT_GOAL,
            title="Root",
            description="Root goal",
        )
        store.add(root)

        current_parent = root.goal_id
        for i in range(5):
            subgoal = GoalArtifact.create(
                goal_type=GoalType.SUBGOAL,
                title=f"Level {i+1}",
                description=f"Level {i+1} subgoal",
                parent_goal_id=current_parent,
            )
            store.add(subgoal)
            current_parent = subgoal.goal_id

        tree = store.get_goal_tree(root.goal_id)

        # Verify tree depth
        depth = 0
        current = tree
        while current["subgoals"]:
            depth += 1
            current = current["subgoals"][0]

        assert depth == 5

    def test_large_number_of_goals(self, store):
        """Test store with many goals."""
        for i in range(100):
            goal = GoalArtifact.create(
                goal_type=GoalType.ROOT_GOAL,
                title=f"Goal {i}",
                description=f"Description {i}",
                domain="houdini" if i % 2 == 0 else "touchdesigner",
                session_id=f"session_{i // 10}",
            )
            store.add(goal)

        assert len(store) == 100
        assert len(store.retrieve_by_domain("houdini")) == 50
        assert len(store.retrieve_by_domain("touchdesigner")) == 50

        stats = store.get_stats()
        assert stats.total_goals == 100
        assert stats.session_count == 10

    def test_goal_with_all_fields(self, store):
        """Test goal with all fields populated."""
        goal = GoalArtifact(
            goal_id="goal_complete",
            parent_goal_id="parent_001",
            task_id="task_complete",
            session_id="session_complete",
            domain="houdini",
            goal_type=GoalType.SUBGOAL.value,
            title="Complete Goal",
            description="A goal with all fields",
            rationale_summary="Full rationale",
            source_signals=(GoalSourceSignal.TASK.value, GoalSourceSignal.MEMORY.value),
            confidence=0.9,
            ambiguity_flags=("ambiguous_domain",),
            safety_summary="Safe to execute",
            execution_feasibility="high",
            backend_hint="houdini_bridge",
            verification_hint="Check node exists",
            repair_hint="Retry with delay",
            preconditions=("bridge_connected", "license_valid"),
            success_criteria={"node_created": True, "parameters_set": True},
            blocked_reason="",
            created_at=datetime.now().isoformat(),
            schema_version="1.0.0",
        )

        store.add(goal)
        retrieved = store.get(goal.goal_id)

        assert retrieved is not None
        assert retrieved.title == "Complete Goal"
        assert len(retrieved.source_signals) == 2
        assert len(retrieved.preconditions) == 2
        assert "node_created" in retrieved.success_criteria