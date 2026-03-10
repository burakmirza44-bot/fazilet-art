"""Session Metadata Models.

Comprehensive metadata capture during execution for visibility,
debugging, and learning from runs.

Key Components:
- ExecutionPhase: Phases of execution lifecycle
- KnowledgeHit: Record of knowledge retrieval
- RagRetrievalMetrics: RAG query metrics
- PlanningMetrics: Planning execution metrics
- ExecutionStepMetrics: Single step metrics
- ErrorRecoveryMetrics: Error recovery attempt data
- KnowledgeQualityMetrics: Knowledge quality during execution
- BridgeHealthMetrics: Bridge health status
- SessionMetadata: Complete session metadata
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class ExecutionPhase(str, Enum):
    """Execution phases in the lifecycle."""

    INITIALIZATION = "initialization"
    PLANNING = "planning"
    KNOWLEDGE_RETRIEVAL = "knowledge_retrieval"
    EXECUTION = "execution"
    VERIFICATION = "verification"
    RECOVERY = "recovery"
    COMPLETION = "completion"


@dataclass
class KnowledgeHit:
    """A hit when retrieving knowledge."""

    recipe_id: str
    recipe_title: str
    confidence: float
    source: str  # "rag", "memory", "distilled", "tutorial"
    retrieval_phase: str  # "planning", "execution", "recovery"
    used: bool = False
    reason_not_used: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "recipe_id": self.recipe_id,
            "recipe_title": self.recipe_title,
            "confidence": self.confidence,
            "source": self.source,
            "retrieval_phase": self.retrieval_phase,
            "used": self.used,
            "reason_not_used": self.reason_not_used,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KnowledgeHit":
        """Create from dictionary."""
        return cls(
            recipe_id=data["recipe_id"],
            recipe_title=data["recipe_title"],
            confidence=data["confidence"],
            source=data["source"],
            retrieval_phase=data["retrieval_phase"],
            used=data.get("used", False),
            reason_not_used=data.get("reason_not_used"),
            timestamp=data.get("timestamp", ""),
        )


@dataclass
class RagRetrievalMetrics:
    """RAG retrieval metrics for session."""

    total_queries: int = 0
    total_chunks_retrieved: int = 0
    avg_confidence: float = 0.0
    avg_latency_ms: float = 0.0
    by_domain: Dict[str, int] = field(default_factory=dict)
    by_knowledge_type: Dict[str, int] = field(default_factory=dict)
    zero_result_queries: int = 0
    queries: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_queries": self.total_queries,
            "total_chunks_retrieved": self.total_chunks_retrieved,
            "avg_confidence": self.avg_confidence,
            "avg_latency_ms": self.avg_latency_ms,
            "by_domain": self.by_domain,
            "by_knowledge_type": self.by_knowledge_type,
            "zero_result_queries": self.zero_result_queries,
            "queries": self.queries,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RagRetrievalMetrics":
        """Create from dictionary."""
        return cls(
            total_queries=data.get("total_queries", 0),
            total_chunks_retrieved=data.get("total_chunks_retrieved", 0),
            avg_confidence=data.get("avg_confidence", 0.0),
            avg_latency_ms=data.get("avg_latency_ms", 0.0),
            by_domain=data.get("by_domain", {}),
            by_knowledge_type=data.get("by_knowledge_type", {}),
            zero_result_queries=data.get("zero_result_queries", 0),
            queries=data.get("queries", []),
        )


@dataclass
class PlanningMetrics:
    """Planning execution metrics."""

    goal: str = ""
    initial_complexity_score: float = 0.0
    decomposition_iterations: int = 1
    subgoals_generated: int = 0
    avg_subgoal_confidence: float = 0.0
    replanning_triggered: bool = False
    replan_count: int = 0
    final_plan_quality_score: float = 0.0
    replanning_reasons: List[str] = field(default_factory=list)
    planning_strategy: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "goal": self.goal,
            "initial_complexity_score": self.initial_complexity_score,
            "decomposition_iterations": self.decomposition_iterations,
            "subgoals_generated": self.subgoals_generated,
            "avg_subgoal_confidence": self.avg_subgoal_confidence,
            "replanning_triggered": self.replanning_triggered,
            "replan_count": self.replan_count,
            "final_plan_quality_score": self.final_plan_quality_score,
            "replanning_reasons": self.replanning_reasons,
            "planning_strategy": self.planning_strategy,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PlanningMetrics":
        """Create from dictionary."""
        return cls(
            goal=data.get("goal", ""),
            initial_complexity_score=data.get("initial_complexity_score", 0.0),
            decomposition_iterations=data.get("decomposition_iterations", 1),
            subgoals_generated=data.get("subgoals_generated", 0),
            avg_subgoal_confidence=data.get("avg_subgoal_confidence", 0.0),
            replanning_triggered=data.get("replanning_triggered", False),
            replan_count=data.get("replan_count", 0),
            final_plan_quality_score=data.get("final_plan_quality_score", 0.0),
            replanning_reasons=data.get("replanning_reasons", []),
            planning_strategy=data.get("planning_strategy", ""),
        )


@dataclass
class ExecutionStepMetrics:
    """Metrics for single execution step."""

    order: int
    action: str
    bridge_type: str  # "touchdesigner", "houdini", "internal"
    duration_ms: float
    success: bool
    error_message: Optional[str] = None
    retries_attempted: int = 0
    verification_passed: bool = True
    knowledge_used: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "order": self.order,
            "action": self.action,
            "bridge_type": self.bridge_type,
            "duration_ms": self.duration_ms,
            "success": self.success,
            "error_message": self.error_message,
            "retries_attempted": self.retries_attempted,
            "verification_passed": self.verification_passed,
            "knowledge_used": self.knowledge_used,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExecutionStepMetrics":
        """Create from dictionary."""
        return cls(
            order=data["order"],
            action=data["action"],
            bridge_type=data["bridge_type"],
            duration_ms=data["duration_ms"],
            success=data["success"],
            error_message=data.get("error_message"),
            retries_attempted=data.get("retries_attempted", 0),
            verification_passed=data.get("verification_passed", True),
            knowledge_used=data.get("knowledge_used", []),
            timestamp=data.get("timestamp", ""),
        )


@dataclass
class ErrorRecoveryMetrics:
    """Error recovery attempt metrics."""

    error_type: str
    error_message: str
    recovery_strategy: str  # "retry", "fallback", "queue", "skip"
    success: bool
    attempts: int = 1
    duration_ms: float = 0.0
    knowledge_consulted: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "error_type": self.error_type,
            "error_message": self.error_message,
            "recovery_strategy": self.recovery_strategy,
            "success": self.success,
            "attempts": self.attempts,
            "duration_ms": self.duration_ms,
            "knowledge_consulted": self.knowledge_consulted,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ErrorRecoveryMetrics":
        """Create from dictionary."""
        return cls(
            error_type=data["error_type"],
            error_message=data["error_message"],
            recovery_strategy=data["recovery_strategy"],
            success=data["success"],
            attempts=data.get("attempts", 1),
            duration_ms=data.get("duration_ms", 0.0),
            knowledge_consulted=data.get("knowledge_consulted", []),
            timestamp=data.get("timestamp", ""),
        )


@dataclass
class KnowledgeQualityMetrics:
    """Knowledge quality during execution."""

    distilled_knowledge_hits: int = 0
    distilled_knowledge_preferred: int = 0
    tutorial_knowledge_hits: int = 0
    memory_knowledge_hits: int = 0
    rag_fallback_used: int = 0
    raw_knowledge_only_fallback: int = 0
    contradictions_found: int = 0
    contradictions_resolved: int = 0
    low_confidence_hits: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "distilled_knowledge_hits": self.distilled_knowledge_hits,
            "distilled_knowledge_preferred": self.distilled_knowledge_preferred,
            "tutorial_knowledge_hits": self.tutorial_knowledge_hits,
            "memory_knowledge_hits": self.memory_knowledge_hits,
            "rag_fallback_used": self.rag_fallback_used,
            "raw_knowledge_only_fallback": self.raw_knowledge_only_fallback,
            "contradictions_found": self.contradictions_found,
            "contradictions_resolved": self.contradictions_resolved,
            "low_confidence_hits": self.low_confidence_hits,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KnowledgeQualityMetrics":
        """Create from dictionary."""
        return cls(
            distilled_knowledge_hits=data.get("distilled_knowledge_hits", 0),
            distilled_knowledge_preferred=data.get("distilled_knowledge_preferred", 0),
            tutorial_knowledge_hits=data.get("tutorial_knowledge_hits", 0),
            memory_knowledge_hits=data.get("memory_knowledge_hits", 0),
            rag_fallback_used=data.get("rag_fallback_used", 0),
            raw_knowledge_only_fallback=data.get("raw_knowledge_only_fallback", 0),
            contradictions_found=data.get("contradictions_found", 0),
            contradictions_resolved=data.get("contradictions_resolved", 0),
            low_confidence_hits=data.get("low_confidence_hits", 0),
        )


@dataclass
class BridgeHealthMetrics:
    """Bridge health during execution."""

    touchdesigner_degraded_mode_activated: bool = False
    touchdesigner_retries_needed: int = 0
    touchdesigner_connection_attempts: int = 0
    houdini_degraded_mode_activated: bool = False
    houdini_retries_needed: int = 0
    houdini_connection_attempts: int = 0
    fallback_to_queuing: bool = False
    fallback_to_ui: bool = False
    bridge_errors: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "touchdesigner_degraded_mode_activated": self.touchdesigner_degraded_mode_activated,
            "touchdesigner_retries_needed": self.touchdesigner_retries_needed,
            "touchdesigner_connection_attempts": self.touchdesigner_connection_attempts,
            "houdini_degraded_mode_activated": self.houdini_degraded_mode_activated,
            "houdini_retries_needed": self.houdini_retries_needed,
            "houdini_connection_attempts": self.houdini_connection_attempts,
            "fallback_to_queuing": self.fallback_to_queuing,
            "fallback_to_ui": self.fallback_to_ui,
            "bridge_errors": self.bridge_errors,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BridgeHealthMetrics":
        """Create from dictionary."""
        return cls(
            touchdesigner_degraded_mode_activated=data.get("touchdesigner_degraded_mode_activated", False),
            touchdesigner_retries_needed=data.get("touchdesigner_retries_needed", 0),
            touchdesigner_connection_attempts=data.get("touchdesigner_connection_attempts", 0),
            houdini_degraded_mode_activated=data.get("houdini_degraded_mode_activated", False),
            houdini_retries_needed=data.get("houdini_retries_needed", 0),
            houdini_connection_attempts=data.get("houdini_connection_attempts", 0),
            fallback_to_queuing=data.get("fallback_to_queuing", False),
            fallback_to_ui=data.get("fallback_to_ui", False),
            bridge_errors=data.get("bridge_errors", []),
        )


@dataclass
class SessionMetadata:
    """Complete session metadata."""

    session_id: str
    timestamp: str
    goal: str
    domain: str

    # Overall metrics
    total_duration_s: float = 0.0
    success: bool = False

    # Phase tracking
    phases_executed: List[str] = field(default_factory=list)
    phase_timings: Dict[str, float] = field(default_factory=dict)

    # Knowledge metrics
    knowledge: KnowledgeQualityMetrics = field(default_factory=KnowledgeQualityMetrics)
    knowledge_hits: List[KnowledgeHit] = field(default_factory=list)

    # RAG metrics
    rag: RagRetrievalMetrics = field(default_factory=RagRetrievalMetrics)

    # Planning metrics
    planning: PlanningMetrics = field(default_factory=PlanningMetrics)

    # Execution metrics
    execution_steps: List[ExecutionStepMetrics] = field(default_factory=list)
    total_steps: int = 0
    successful_steps: int = 0

    # Error recovery
    error_recoveries: List[ErrorRecoveryMetrics] = field(default_factory=list)

    # Bridge health
    bridge: BridgeHealthMetrics = field(default_factory=BridgeHealthMetrics)

    # Other
    errors: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    debug_info: Dict[str, Any] = field(default_factory=dict)

    # Tags and labels
    tags: List[str] = field(default_factory=list)
    labels: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "goal": self.goal,
            "domain": self.domain,
            "total_duration_s": self.total_duration_s,
            "success": self.success,
            "phases_executed": self.phases_executed,
            "phase_timings": self.phase_timings,
            "knowledge": self.knowledge.to_dict(),
            "knowledge_hits": [h.to_dict() for h in self.knowledge_hits],
            "rag": self.rag.to_dict(),
            "planning": self.planning.to_dict(),
            "execution_steps": [s.to_dict() for s in self.execution_steps],
            "total_steps": self.total_steps,
            "successful_steps": self.successful_steps,
            "error_recoveries": [r.to_dict() for r in self.error_recoveries],
            "bridge": self.bridge.to_dict(),
            "errors": self.errors,
            "warnings": self.warnings,
            "debug_info": self.debug_info,
            "tags": self.tags,
            "labels": self.labels,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionMetadata":
        """Create from dictionary."""
        return cls(
            session_id=data["session_id"],
            timestamp=data["timestamp"],
            goal=data["goal"],
            domain=data["domain"],
            total_duration_s=data.get("total_duration_s", 0.0),
            success=data.get("success", False),
            phases_executed=data.get("phases_executed", []),
            phase_timings=data.get("phase_timings", {}),
            knowledge=KnowledgeQualityMetrics.from_dict(data.get("knowledge", {})),
            knowledge_hits=[KnowledgeHit.from_dict(h) for h in data.get("knowledge_hits", [])],
            rag=RagRetrievalMetrics.from_dict(data.get("rag", {})),
            planning=PlanningMetrics.from_dict(data.get("planning", {})),
            execution_steps=[ExecutionStepMetrics.from_dict(s) for s in data.get("execution_steps", [])],
            total_steps=data.get("total_steps", 0),
            successful_steps=data.get("successful_steps", 0),
            error_recoveries=[ErrorRecoveryMetrics.from_dict(r) for r in data.get("error_recoveries", [])],
            bridge=BridgeHealthMetrics.from_dict(data.get("bridge", {})),
            errors=data.get("errors", []),
            warnings=data.get("warnings", []),
            debug_info=data.get("debug_info", {}),
            tags=data.get("tags", []),
            labels=data.get("labels", {}),
        )

    def summary(self) -> str:
        """Human-readable summary."""
        lines = []

        status = "[OK]" if self.success else "[FAIL]"
        lines.append(f"{status} {self.goal}")
        lines.append(f"  Duration: {self.total_duration_s:.2f}s")

        if self.knowledge.distilled_knowledge_hits > 0:
            lines.append(f"  Knowledge: {self.knowledge.distilled_knowledge_hits} recipes used")
            lines.append(f"      - {self.knowledge.distilled_knowledge_preferred} high-confidence")

        if self.rag.total_queries > 0:
            lines.append(f"  RAG queries: {self.rag.total_queries} ({self.rag.total_chunks_retrieved} chunks)")

        if self.planning.replan_count > 0:
            lines.append(f"  Replanned: {self.planning.replan_count}x")

        if self.error_recoveries:
            success_count = sum(1 for r in self.error_recoveries if r.success)
            lines.append(f"  Error recovery: {success_count}/{len(self.error_recoveries)} successful")

        if self.bridge.touchdesigner_degraded_mode_activated:
            lines.append(f"  [WARN] TD degraded mode (retries: {self.bridge.touchdesigner_retries_needed})")

        if self.bridge.houdini_degraded_mode_activated:
            lines.append(f"  [WARN] Houdini degraded mode (retries: {self.bridge.houdini_retries_needed})")

        return "\n".join(lines)

    def to_file(self, filepath: str) -> bool:
        """Save to JSON file.

        Args:
            filepath: Path to save

        Returns:
            True if saved successfully
        """
        try:
            path = Path(filepath)
            path.parent.mkdir(parents=True, exist_ok=True)

            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.to_dict(), f, indent=2)

            return True
        except (IOError, OSError) as e:
            print(f"[SESSION] Failed to save: {e}")
            return False

    @classmethod
    def from_file(cls, filepath: str) -> Optional["SessionMetadata"]:
        """Load from JSON file.

        Args:
            filepath: Path to load

        Returns:
            SessionMetadata or None if loading fails
        """
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            return cls.from_dict(data)
        except (IOError, json.JSONDecodeError) as e:
            print(f"[SESSION] Failed to load: {e}")
            return None

    @classmethod
    def create(
        cls,
        session_id: str,
        goal: str,
        domain: str,
    ) -> "SessionMetadata":
        """Factory method to create new session metadata.

        Args:
            session_id: Unique session identifier
            goal: Execution goal
            domain: Target domain

        Returns:
            New SessionMetadata instance
        """
        return cls(
            session_id=session_id,
            timestamp=datetime.now().isoformat(),
            goal=goal,
            domain=domain,
            planning=PlanningMetrics(goal=goal),
        )