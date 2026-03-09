"""Tests for memory runtime integration.

Tests RuntimeMemoryContext, build_runtime_memory_context, and
memory integration with execution loops.
"""

import json
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from app.core.memory_runtime import (
    RuntimeMemoryContext,
    build_runtime_memory_context,
    get_memory_influence_summary,
    save_execution_result,
)


class TestRuntimeMemoryContext:
    """Tests for RuntimeMemoryContext dataclass."""

    def test_runtime_memory_context_creation(self):
        """Test creating a RuntimeMemoryContext."""
        context = RuntimeMemoryContext(
            domain="touchdesigner",
            query="test query",
            memory_influenced=True,
            success_pattern_count=2,
            failure_pattern_count=1,
        )

        assert context.domain == "touchdesigner"
        assert context.query == "test query"
        assert context.memory_influenced is True
        assert context.success_pattern_count == 2
        assert context.failure_pattern_count == 1
        assert context.total_patterns == 3

    def test_runtime_memory_context_empty(self):
        """Test RuntimeMemoryContext with no patterns."""
        context = RuntimeMemoryContext(
            domain="houdini",
            query="another query",
            memory_influenced=False,
        )

        assert context.memory_influenced is False
        assert context.total_patterns == 0
        assert context.success_patterns == []
        assert context.failure_patterns == []

    def test_runtime_memory_context_to_dict(self):
        """Test converting RuntimeMemoryContext to dict."""
        context = RuntimeMemoryContext(
            domain="touchdesigner",
            query="test",
            memory_influenced=True,
            success_pattern_count=2,
            failure_pattern_count=1,
            repair_pattern_count=1,
        )

        data = context.to_dict()

        assert data["domain"] == "touchdesigner"
        assert data["query"] == "test"
        assert data["memory_influenced"] is True
        assert data["success_pattern_count"] == 2
        assert data["failure_pattern_count"] == 1
        assert data["repair_pattern_count"] == 1
        assert data["total_patterns"] == 4


class TestBuildRuntimeMemoryContext:
    """Tests for build_runtime_memory_context function."""

    def test_build_memory_context_no_files(self):
        """Test building context when memory files don't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            context = build_runtime_memory_context(
                domain="touchdesigner",
                query="test query",
                repo_root=tmpdir,
            )

            assert context.domain == "touchdesigner"
            assert context.query == "test query"
            assert context.memory_influenced is False
            assert context.total_patterns == 0

    def test_build_memory_context_with_success_patterns(self):
        """Test building context with success patterns."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create memory directory and file
            memory_dir = os.path.join(tmpdir, "data", "memory")
            os.makedirs(memory_dir)

            success_patterns = {
                "patterns": [
                    {
                        "id": "success_1",
                        "domain": "touchdesigner",
                        "query": "test",
                        "description": "Success pattern 1",
                        "score": 0.9,
                    },
                    {
                        "id": "success_2",
                        "domain": "touchdesigner",
                        "query": "other",
                        "description": "Other pattern",
                        "score": 0.8,
                    },
                ]
            }

            with open(os.path.join(memory_dir, "success_patterns.json"), "w") as f:
                json.dump(success_patterns, f)

            context = build_runtime_memory_context(
                domain="touchdesigner",
                query="test",
                repo_root=tmpdir,
            )

            # Should find the pattern with "test" in query or description
            assert context.memory_influenced is True
            assert context.success_pattern_count == 1
            assert len(context.success_patterns) == 1
            assert context.success_patterns[0]["id"] == "success_1"

    def test_build_memory_context_domain_filter(self):
        """Test that domain filtering works."""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory_dir = os.path.join(tmpdir, "data", "memory")
            os.makedirs(memory_dir)

            patterns = {
                "patterns": [
                    {
                        "id": "td_1",
                        "domain": "touchdesigner",
                        "query": "test",
                        "description": "TD pattern",
                    },
                    {
                        "id": "houdini_1",
                        "domain": "houdini",
                        "query": "test",
                        "description": "Houdini pattern",
                    },
                ]
            }

            with open(os.path.join(memory_dir, "success_patterns.json"), "w") as f:
                json.dump(patterns, f)

            context = build_runtime_memory_context(
                domain="touchdesigner",
                query="test",
                repo_root=tmpdir,
            )

            # Should only get touchdesigner patterns
            assert context.memory_influenced is True
            assert len(context.success_patterns) == 1
            assert context.success_patterns[0]["domain"] == "touchdesigner"

    def test_build_memory_context_limit(self):
        """Test that pattern limits are respected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory_dir = os.path.join(tmpdir, "data", "memory")
            os.makedirs(memory_dir)

            # Create many patterns
            patterns = {
                "patterns": [
                    {
                        "id": f"success_{i}",
                        "domain": "touchdesigner",
                        "query": "test",
                        "description": f"Pattern {i}",
                        "score": i,
                    }
                    for i in range(10)
                ]
            }

            with open(os.path.join(memory_dir, "success_patterns.json"), "w") as f:
                json.dump(patterns, f)

            context = build_runtime_memory_context(
                domain="touchdesigner",
                query="test",
                repo_root=tmpdir,
                max_success=3,
            )

            # Should only get 3 patterns
            assert context.success_pattern_count == 3
            assert len(context.success_patterns) == 3


class TestSaveExecutionResult:
    """Tests for save_execution_result function."""

    def test_save_success_result(self):
        """Test saving a successful execution result."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = save_execution_result(
                domain="touchdesigner",
                query="test task",
                success=True,
                result_data={
                    "description": "Test success",
                    "tags": ["tag1", "tag2"],
                },
                repo_root=tmpdir,
            )

            assert result is True

            # Verify file was created
            memory_path = os.path.join(tmpdir, "data", "memory", "success_patterns.json")
            assert os.path.exists(memory_path)

            # Verify content
            with open(memory_path) as f:
                data = json.load(f)

            assert "patterns" in data
            assert len(data["patterns"]) == 1
            assert data["patterns"][0]["domain"] == "touchdesigner"
            assert data["patterns"][0]["query"] == "test task"
            assert data["patterns"][0]["score"] == 1.0

    def test_save_failure_result(self):
        """Test saving a failed execution result."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = save_execution_result(
                domain="houdini",
                query="failed task",
                success=False,
                result_data={
                    "description": "Test failure",
                    "error_type": "bridge_unavailable",
                },
                repo_root=tmpdir,
            )

            assert result is True

            # Verify file was created
            memory_path = os.path.join(tmpdir, "data", "memory", "failure_patterns.json")
            assert os.path.exists(memory_path)

    def test_save_appends_to_existing(self):
        """Test that saving appends to existing patterns."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # First save
            save_execution_result(
                domain="touchdesigner",
                query="task1",
                success=True,
                result_data={"description": "First"},
                repo_root=tmpdir,
            )

            # Second save
            save_execution_result(
                domain="touchdesigner",
                query="task2",
                success=True,
                result_data={"description": "Second"},
                repo_root=tmpdir,
            )

            memory_path = os.path.join(tmpdir, "data", "memory", "success_patterns.json")
            with open(memory_path) as f:
                data = json.load(f)

            assert len(data["patterns"]) == 2

    def test_save_limits_pattern_count(self):
        """Test that pattern count is limited to 100."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create existing patterns
            memory_dir = os.path.join(tmpdir, "data", "memory")
            os.makedirs(memory_dir)

            existing_patterns = {
                "patterns": [
                    {"id": f"existing_{i}", "domain": "touchdesigner"}
                    for i in range(100)
                ]
            }

            with open(os.path.join(memory_dir, "success_patterns.json"), "w") as f:
                json.dump(existing_patterns, f)

            # Add one more
            save_execution_result(
                domain="touchdesigner",
                query="new task",
                success=True,
                result_data={"description": "New"},
                repo_root=tmpdir,
            )

            with open(os.path.join(memory_dir, "success_patterns.json")) as f:
                data = json.load(f)

            # Should still be 100 (oldest removed)
            assert len(data["patterns"]) == 100
            assert data["patterns"][-1]["query"] == "new task"


class TestMemoryInfluenceSummary:
    """Tests for get_memory_influence_summary function."""

    def test_get_summary(self):
        """Test getting memory influence summary."""
        context = RuntimeMemoryContext(
            domain="touchdesigner",
            query="test",
            memory_influenced=True,
            success_pattern_count=2,
            failure_pattern_count=1,
            repair_pattern_count=1,
        )

        summary = get_memory_influence_summary(context)

        assert summary["memory_influenced"] is True
        assert summary["success_patterns_used"] == 2
        assert summary["failure_patterns_used"] == 1
        assert summary["repair_patterns_used"] == 1
        assert summary["total_patterns"] == 4
        assert summary["domain"] == "touchdesigner"


class TestMemoryIntegration:
    """Tests for memory integration with execution loops."""

    def test_td_execution_loop_memory_in_report(self):
        """Test that TD execution loop includes memory in report."""
        with tempfile.TemporaryDirectory() as tmpdir:
            from app.domains.touchdesigner.td_execution_loop import (
                TDExecutionConfig,
                TDExecutionLoop,
            )

            config = TDExecutionConfig(
                repo_root=tmpdir,
                enable_memory=True,
                dry_run=True,
            )
            loop = TDExecutionLoop(config)

            task = MagicMock()
            task.task_summary = "test_task"
            task.task_id = "test_123"

            report = loop.run_basic_top_chain(task, dry_run=True)

            assert hasattr(report, "memory_influenced")
            assert hasattr(report, "success_patterns_used")
            assert hasattr(report, "failure_patterns_used")

    def test_houdini_execution_loop_memory_in_report(self):
        """Test that Houdini execution loop includes memory in report."""
        with tempfile.TemporaryDirectory() as tmpdir:
            from app.domains.houdini.houdini_execution_loop import (
                HoudiniExecutionConfig,
                HoudiniExecutionLoop,
            )

            config = HoudiniExecutionConfig(
                repo_root=tmpdir,
                enable_memory=True,
                dry_run=True,
            )
            loop = HoudiniExecutionLoop(config)

            task = MagicMock()
            task.task_summary = "test_sop"
            task.task_id = "houdini_123"

            report = loop.run_basic_sop_chain(task, dry_run=True)

            assert hasattr(report, "memory_influenced")
            assert hasattr(report, "success_patterns_used")
