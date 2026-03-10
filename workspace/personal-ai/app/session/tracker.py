"""Session Tracker Module.

Tracks and records session metadata during execution for comprehensive
visibility into the runtime behavior.

Usage:
    tracker = SessionTracker("session_001", "Create geometry", "houdini")

    # Record phases
    tracker.record_phase_start(ExecutionPhase.PLANNING)
    # ... planning logic
    tracker.record_phase_end(ExecutionPhase.PLANNING)

    # Record knowledge hits
    tracker.record_knowledge_hit(
        recipe_id="recipe_001",
        recipe_title="Procedural Geometry",
        confidence=0.92,
        source="distilled",
        phase="planning"
    )

    # Finalize and export
    tracker.finalize(success=True)
    tracker.export()
"""

from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.session.metadata import (
    BridgeHealthMetrics,
    ErrorRecoveryMetrics,
    ExecutionPhase,
    ExecutionStepMetrics,
    KnowledgeHit,
    KnowledgeQualityMetrics,
    PlanningMetrics,
    RagRetrievalMetrics,
    SessionMetadata,
)


class SessionTracker:
    """Track and record session metadata during execution.

    Provides comprehensive tracking of:
    - Execution phases and timings
    - Knowledge retrieval hits
    - RAG queries
    - Planning metrics
    - Execution steps
    - Error recovery attempts
    - Bridge health status

    Example:
        tracker = SessionTracker("session_001", "Create noise terrain", "houdini")

        tracker.record_phase_start(ExecutionPhase.PLANNING)
        tracker.record_knowledge_hit("recipe_001", "Noise Terrain", 0.85, "distilled", "planning")
        tracker.record_phase_end(ExecutionPhase.PLANNING)

        tracker.record_phase_start(ExecutionPhase.EXECUTION)
        tracker.record_execution_step(1, "Create geometry", "houdini", 156.0, True)
        tracker.record_phase_end(ExecutionPhase.EXECUTION)

        tracker.finalize(success=True)
        tracker.export()
    """

    def __init__(
        self,
        session_id: str,
        goal: str,
        domain: str,
        verbose: bool = True,
    ) -> None:
        """Initialize the session tracker.

        Args:
            session_id: Unique session identifier
            goal: Execution goal
            domain: Target domain (houdini, touchdesigner, etc.)
            verbose: Print tracking output to console
        """
        self.metadata = SessionMetadata.create(
            session_id=session_id,
            goal=goal,
            domain=domain,
        )
        self.start_time = time.time()
        self.phase_start_time: Optional[float] = None
        self.current_phase: Optional[str] = None
        self.verbose = verbose

        # Running averages for RAG
        self._rag_total_latency = 0.0

    # -------------------------------------------------------------------------
    # Phase Tracking
    # -------------------------------------------------------------------------

    def record_phase_start(self, phase: ExecutionPhase) -> None:
        """Record when a phase starts.

        Args:
            phase: The execution phase starting
        """
        self.phase_start_time = time.time()
        self.current_phase = phase.value
        self.metadata.phases_executed.append(phase.value)

        if self.verbose:
            print(f"[PHASE] {phase.value}")

    def record_phase_end(self, phase: ExecutionPhase) -> None:
        """Record when a phase ends.

        Args:
            phase: The execution phase ending
        """
        if self.phase_start_time:
            duration = time.time() - self.phase_start_time
            self.metadata.phase_timings[phase.value] = duration

            if self.verbose:
                print(f"[PHASE] {phase.value} completed in {duration:.2f}s")

        self.phase_start_time = None
        self.current_phase = None

    # -------------------------------------------------------------------------
    # Knowledge Tracking
    # -------------------------------------------------------------------------

    def record_knowledge_hit(
        self,
        recipe_id: str,
        recipe_title: str,
        confidence: float,
        source: str,
        phase: str,
        used: bool = True,
        reason_not_used: Optional[str] = None,
    ) -> None:
        """Record when knowledge is retrieved.

        Args:
            recipe_id: Recipe/knowledge ID
            recipe_title: Human-readable title
            confidence: Confidence score (0-1)
            source: Source type (distilled, rag, memory, tutorial)
            phase: Phase when retrieved (planning, execution, recovery)
            used: Whether the knowledge was used
            reason_not_used: Reason if not used
        """
        hit = KnowledgeHit(
            recipe_id=recipe_id,
            recipe_title=recipe_title,
            confidence=confidence,
            source=source,
            retrieval_phase=phase,
            used=used,
            reason_not_used=reason_not_used,
        )

        self.metadata.knowledge_hits.append(hit)

        # Update quality metrics
        if source == "distilled":
            self.metadata.knowledge.distilled_knowledge_hits += 1
            if confidence >= 0.8:
                self.metadata.knowledge.distilled_knowledge_preferred += 1
        elif source == "tutorial":
            self.metadata.knowledge.tutorial_knowledge_hits += 1
        elif source == "memory":
            self.metadata.knowledge.memory_knowledge_hits += 1

        if confidence < 0.5:
            self.metadata.knowledge.low_confidence_hits += 1

        if self.verbose:
            used_str = "" if used else f" (not used: {reason_not_used})"
            print(f"[KNOWLEDGE] {recipe_title} (confidence: {confidence:.0%}, source: {source}){used_str}")

    def record_contradiction(
        self,
        contradiction_type: str = "knowledge_conflict",
        resolved: bool = False,
        resolution_strategy: Optional[str] = None,
    ) -> None:
        """Record contradiction detection.

        Args:
            contradiction_type: Type of contradiction
            resolved: Whether it was resolved
            resolution_strategy: How it was resolved
        """
        self.metadata.knowledge.contradictions_found += 1
        if resolved:
            self.metadata.knowledge.contradictions_resolved += 1

        if self.verbose:
            status = "resolved" if resolved else "unresolved"
            print(f"[CONTRADICTION] {contradiction_type} ({status})")

    def record_fallback_used(
        self,
        fallback_type: str,
        reason: str = "",
    ) -> None:
        """Record fallback strategy usage.

        Args:
            fallback_type: Type of fallback (rag_only, raw_only, generic)
            reason: Why fallback was needed
        """
        if fallback_type == "rag_only":
            self.metadata.knowledge.rag_fallback_used += 1
        elif fallback_type == "raw_only":
            self.metadata.knowledge.raw_knowledge_only_fallback += 1

        if self.verbose:
            print(f"[FALLBACK] {fallback_type} used{': ' + reason if reason else ''}")

    # -------------------------------------------------------------------------
    # RAG Tracking
    # -------------------------------------------------------------------------

    def record_rag_query(
        self,
        query: str,
        chunks_retrieved: int,
        avg_confidence: float,
        latency_ms: float,
        domain: Optional[str] = None,
        knowledge_type: Optional[str] = None,
    ) -> None:
        """Record RAG query.

        Args:
            query: The search query
            chunks_retrieved: Number of chunks retrieved
            avg_confidence: Average confidence of results
            latency_ms: Query latency in milliseconds
            domain: Domain if applicable
            knowledge_type: Knowledge type if applicable
        """
        self.metadata.rag.total_queries += 1
        self.metadata.rag.total_chunks_retrieved += chunks_retrieved

        # Update running average for confidence
        prev_count = self.metadata.rag.total_queries - 1
        self.metadata.rag.avg_confidence = (
            (self.metadata.rag.avg_confidence * prev_count + avg_confidence)
            / self.metadata.rag.total_queries
        )

        # Update running average for latency
        self._rag_total_latency += latency_ms
        self.metadata.rag.avg_latency_ms = self._rag_total_latency / self.metadata.rag.total_queries

        # Track zero results
        if chunks_retrieved == 0:
            self.metadata.rag.zero_result_queries += 1

        # Track by domain/type
        if domain:
            self.metadata.rag.by_domain[domain] = self.metadata.rag.by_domain.get(domain, 0) + 1

        if knowledge_type:
            self.metadata.rag.by_knowledge_type[knowledge_type] = (
                self.metadata.rag.by_knowledge_type.get(knowledge_type, 0) + 1
            )

        # Store query details
        self.metadata.rag.queries.append({
            "query": query[:100],  # Truncate long queries
            "chunks": chunks_retrieved,
            "confidence": avg_confidence,
            "latency_ms": latency_ms,
        })

        if self.verbose:
            if chunks_retrieved == 0:
                print(f"[RAG] No results for: {query[:50]}...")
            else:
                print(f"[RAG] Retrieved {chunks_retrieved} chunks ({avg_confidence:.0%} avg confidence)")

    # -------------------------------------------------------------------------
    # Planning Tracking
    # -------------------------------------------------------------------------

    def record_planning_step(
        self,
        complexity_score: float,
        subgoals: int,
        plan_quality: float,
        strategy: str = "",
    ) -> None:
        """Record planning completion.

        Args:
            complexity_score: Task complexity score
            subgoals: Number of subgoals generated
            plan_quality: Plan quality score
            strategy: Planning strategy used
        """
        self.metadata.planning.initial_complexity_score = complexity_score
        self.metadata.planning.subgoals_generated = subgoals
        self.metadata.planning.final_plan_quality_score = plan_quality
        self.metadata.planning.planning_strategy = strategy

        if self.verbose:
            print(f"[PLANNING] Complexity: {complexity_score:.1f}, Subgoals: {subgoals}, Quality: {plan_quality:.0%}")

    def record_replanning(
        self,
        reason: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record replanning event.

        Args:
            reason: Why replanning was triggered
            details: Additional details
        """
        self.metadata.planning.replan_count += 1
        self.metadata.planning.replanning_triggered = True
        self.metadata.planning.replanning_reasons.append(reason)

        if self.verbose:
            print(f"[REPLANNING] {reason}")

    def record_subgoal_confidence(self, confidence: float) -> None:
        """Record subgoal confidence for averaging.

        Args:
            confidence: Confidence score for a subgoal
        """
        # Running average
        count = self.metadata.planning.subgoals_generated
        if count > 0:
            self.metadata.planning.avg_subgoal_confidence = (
                (self.metadata.planning.avg_subgoal_confidence * (count - 1) + confidence) / count
            )

    # -------------------------------------------------------------------------
    # Execution Tracking
    # -------------------------------------------------------------------------

    def record_execution_step(
        self,
        order: int,
        action: str,
        bridge: str,
        duration_ms: float,
        success: bool,
        error_message: Optional[str] = None,
        knowledge_used: Optional[List[str]] = None,
        retries: int = 0,
    ) -> None:
        """Record execution step.

        Args:
            order: Step order (1-indexed)
            action: Action name/description
            bridge: Bridge type (touchdesigner, houdini, internal)
            duration_ms: Duration in milliseconds
            success: Whether step succeeded
            error_message: Error message if failed
            knowledge_used: List of recipe IDs used
            retries: Number of retries attempted
        """
        step = ExecutionStepMetrics(
            order=order,
            action=action,
            bridge_type=bridge,
            duration_ms=duration_ms,
            success=success,
            error_message=error_message,
            knowledge_used=knowledge_used or [],
            retries_attempted=retries,
        )

        self.metadata.execution_steps.append(step)
        self.metadata.total_steps += 1

        if success:
            self.metadata.successful_steps += 1

        if self.verbose:
            status = "[OK]" if success else "[FAIL]"
            print(f"[STEP] {status} {action} ({duration_ms:.0f}ms)")

    # -------------------------------------------------------------------------
    # Error Recovery Tracking
    # -------------------------------------------------------------------------

    def record_error_recovery(
        self,
        error_type: str,
        error_message: str,
        strategy: str,
        success: bool,
        attempts: int = 1,
        duration_ms: float = 0.0,
        knowledge_consulted: Optional[List[str]] = None,
    ) -> None:
        """Record error recovery attempt.

        Args:
            error_type: Type of error
            error_message: Error message
            strategy: Recovery strategy (retry, fallback, queue, skip)
            success: Whether recovery succeeded
            attempts: Number of attempts
            duration_ms: Duration in milliseconds
            knowledge_consulted: Knowledge sources consulted
        """
        recovery = ErrorRecoveryMetrics(
            error_type=error_type,
            error_message=error_message,
            recovery_strategy=strategy,
            success=success,
            attempts=attempts,
            duration_ms=duration_ms,
            knowledge_consulted=knowledge_consulted or [],
        )

        self.metadata.error_recoveries.append(recovery)

        if self.verbose:
            status = "[OK]" if success else "[FAIL]"
            print(f"[RECOVERY] {status} {error_type} via {strategy} (attempts: {attempts})")

    # -------------------------------------------------------------------------
    # Bridge Health Tracking
    # -------------------------------------------------------------------------

    def record_bridge_degraded(
        self,
        bridge: str,
        reason: str = "",
    ) -> None:
        """Record bridge degraded mode activation.

        Args:
            bridge: Bridge type (touchdesigner, houdini)
            reason: Why degraded mode was activated
        """
        if bridge == "touchdesigner":
            self.metadata.bridge.touchdesigner_degraded_mode_activated = True
        elif bridge == "houdini":
            self.metadata.bridge.houdini_degraded_mode_activated = True

        if self.verbose:
            print(f"[BRIDGE] {bridge} entered degraded mode{': ' + reason if reason else ''}")

    def record_bridge_retry(
        self,
        bridge: str,
        error: Optional[str] = None,
    ) -> None:
        """Record bridge retry attempt.

        Args:
            bridge: Bridge type
            error: Error that triggered retry
        """
        if bridge == "touchdesigner":
            self.metadata.bridge.touchdesigner_retries_needed += 1
        elif bridge == "houdini":
            self.metadata.bridge.houdini_retries_needed += 1

        if error:
            self.metadata.bridge.bridge_errors.append({
                "bridge": bridge,
                "error": error,
                "timestamp": datetime.now().isoformat(),
            })

    def record_bridge_connection_attempt(
        self,
        bridge: str,
        success: bool,
    ) -> None:
        """Record bridge connection attempt.

        Args:
            bridge: Bridge type
            success: Whether connection succeeded
        """
        if bridge == "touchdesigner":
            self.metadata.bridge.touchdesigner_connection_attempts += 1
        elif bridge == "houdini":
            self.metadata.bridge.houdini_connection_attempts += 1

    def record_fallback_to_queuing(self, reason: str = "") -> None:
        """Record fallback to queuing mode.

        Args:
            reason: Why queuing was needed
        """
        self.metadata.bridge.fallback_to_queuing = True

        if self.verbose:
            print(f"[BRIDGE] Fallback to queuing mode{': ' + reason if reason else ''}")

    def record_fallback_to_ui(self, reason: str = "") -> None:
        """Record fallback to UI automation.

        Args:
            reason: Why UI fallback was needed
        """
        self.metadata.bridge.fallback_to_ui = True

        if self.verbose:
            print(f"[BRIDGE] Fallback to UI automation{': ' + reason if reason else ''}")

    # -------------------------------------------------------------------------
    # General Tracking
    # -------------------------------------------------------------------------

    def record_error(
        self,
        error_type: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record error.

        Args:
            error_type: Type of error
            message: Error message
            details: Additional details
        """
        self.metadata.errors.append({
            "type": error_type,
            "message": message,
            "details": details,
            "timestamp": datetime.now().isoformat(),
        })

        if self.verbose:
            print(f"[ERROR] {error_type}: {message}")

    def record_warning(self, message: str) -> None:
        """Record warning.

        Args:
            message: Warning message
        """
        self.metadata.warnings.append(message)

        if self.verbose:
            print(f"[WARNING] {message}")

    def record_debug(self, key: str, value: Any) -> None:
        """Record debug information.

        Args:
            key: Debug key
            value: Debug value
        """
        self.metadata.debug_info[key] = value

    def add_tag(self, tag: str) -> None:
        """Add a tag to the session.

        Args:
            tag: Tag to add
        """
        if tag not in self.metadata.tags:
            self.metadata.tags.append(tag)

    def add_label(self, key: str, value: str) -> None:
        """Add a label to the session.

        Args:
            key: Label key
            value: Label value
        """
        self.metadata.labels[key] = value

    # -------------------------------------------------------------------------
    # Finalization
    # -------------------------------------------------------------------------

    def finalize(
        self,
        success: bool,
        tags: Optional[List[str]] = None,
    ) -> None:
        """Finalize session metadata.

        Args:
            success: Whether the session succeeded
            tags: Optional tags to add
        """
        self.metadata.success = success
        self.metadata.total_duration_s = time.time() - self.start_time

        if tags:
            for tag in tags:
                self.add_tag(tag)

        if self.verbose:
            print(f"\n[SESSION] {self.metadata.summary()}\n")

    def export(
        self,
        filepath: Optional[str] = None,
        repo_root: str = ".",
    ) -> str:
        """Export session metadata to JSON.

        Args:
            filepath: Optional specific path (default: auto-generated)
            repo_root: Repository root for default path

        Returns:
            Path to exported file
        """
        if not filepath:
            filepath = f"data/sessions/{self.metadata.session_id}.json"

        # Make path relative to repo_root if not absolute
        if not os.path.isabs(filepath):
            filepath = os.path.join(repo_root, filepath)

        # Ensure directory exists
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)

        # Write
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.metadata.to_dict(), f, indent=2)

        if self.verbose:
            print(f"[SESSION] Exported to {filepath}")

        return filepath

    def get_summary_dict(self) -> Dict[str, Any]:
        """Get summary as dictionary.

        Returns:
            Summary dictionary
        """
        return {
            "session_id": self.metadata.session_id,
            "goal": self.metadata.goal,
            "domain": self.metadata.domain,
            "success": self.metadata.success,
            "duration_s": self.metadata.total_duration_s,
            "steps": {
                "total": self.metadata.total_steps,
                "successful": self.metadata.successful_steps,
            },
            "knowledge_hits": self.metadata.knowledge.distilled_knowledge_hits,
            "rag_queries": self.metadata.rag.total_queries,
            "errors": len(self.metadata.errors),
            "recoveries": len(self.metadata.error_recoveries),
        }


# Import os for path handling
import os