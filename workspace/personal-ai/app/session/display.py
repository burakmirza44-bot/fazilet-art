"""Session Display Formatter.

Formats session metadata for console output and display.

Usage:
    from app.session.display import SessionDisplayFormatter

    formatter = SessionDisplayFormatter()
    display = formatter.format_session_output(metadata, verbose=True)
    print(display)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.session.metadata import SessionMetadata


class SessionDisplayFormatter:
    """Format session metadata for display."""

    @staticmethod
    def format_session_output(
        metadata: "SessionMetadata",
        verbose: bool = False,
    ) -> str:
        """Format session for console output.

        Args:
            metadata: Session metadata to format
            verbose: Include detailed information

        Returns:
            Formatted string
        """
        lines = []

        # Header
        status = "[OK] SUCCESS" if metadata.success else "[FAIL] FAILED"
        lines.append(f"\n{status} - {metadata.goal}")
        lines.append(f"Duration: {metadata.total_duration_s:.2f}s")
        lines.append(f"Domain: {metadata.domain}")

        # Knowledge insights
        knowledge_lines = SessionDisplayFormatter._format_knowledge(metadata, verbose)
        lines.extend(knowledge_lines)

        # RAG metrics
        rag_lines = SessionDisplayFormatter._format_rag(metadata, verbose)
        lines.extend(rag_lines)

        # Planning insights
        planning_lines = SessionDisplayFormatter._format_planning(metadata, verbose)
        lines.extend(planning_lines)

        # Execution insights
        execution_lines = SessionDisplayFormatter._format_execution(metadata, verbose)
        lines.extend(execution_lines)

        # Error recovery
        recovery_lines = SessionDisplayFormatter._format_recovery(metadata, verbose)
        lines.extend(recovery_lines)

        # Bridge health
        bridge_lines = SessionDisplayFormatter._format_bridge(metadata, verbose)
        lines.extend(bridge_lines)

        # Phase timings (verbose only)
        if verbose and metadata.phase_timings:
            lines.append(f"\nPhase Timings:")
            for phase, duration in metadata.phase_timings.items():
                lines.append(f"  {phase}: {duration:.2f}s")

        # Warnings
        if metadata.warnings:
            lines.append(f"\nWarnings:")
            for warning in metadata.warnings[:3]:
                lines.append(f"  - {warning}")
            if len(metadata.warnings) > 3:
                lines.append(f"  ... and {len(metadata.warnings) - 3} more")

        # Errors
        if metadata.errors and verbose:
            lines.append(f"\nErrors:")
            for error in metadata.errors[:3]:
                lines.append(f"  - {error.get('type', 'unknown')}: {error.get('message', '')}")

        lines.append("")

        return "\n".join(lines)

    @staticmethod
    def _format_knowledge(
        metadata: "SessionMetadata",
        verbose: bool,
    ) -> list:
        """Format knowledge section."""
        lines = []

        if metadata.knowledge.distilled_knowledge_hits > 0:
            lines.append(f"\nKnowledge:")
            lines.append(f"  Recipes used: {metadata.knowledge.distilled_knowledge_hits}")
            lines.append(f"  High-confidence: {metadata.knowledge.distilled_knowledge_preferred}")

            if metadata.knowledge.tutorial_knowledge_hits > 0:
                lines.append(f"  Tutorial hits: {metadata.knowledge.tutorial_knowledge_hits}")

            if metadata.knowledge.memory_knowledge_hits > 0:
                lines.append(f"  Memory hits: {metadata.knowledge.memory_knowledge_hits}")

            if metadata.knowledge.raw_knowledge_only_fallback > 0:
                lines.append(f"  [WARN] Fallback to raw knowledge: {metadata.knowledge.raw_knowledge_only_fallback}x")

            if metadata.knowledge.contradictions_found > 0:
                lines.append(
                    f"  Contradictions: {metadata.knowledge.contraditions_found} "
                    f"({metadata.knowledge.contradictions_resolved} resolved)"
                )

        return lines

    @staticmethod
    def _format_rag(
        metadata: "SessionMetadata",
        verbose: bool,
    ) -> list:
        """Format RAG section."""
        lines = []

        if metadata.rag.total_queries > 0:
            lines.append(f"\nRetrieval:")
            lines.append(f"  RAG queries: {metadata.rag.total_queries}")
            lines.append(f"  Chunks retrieved: {metadata.rag.total_chunks_retrieved}")
            lines.append(f"  Avg confidence: {metadata.rag.avg_confidence:.0%}")
            lines.append(f"  Avg latency: {metadata.rag.avg_latency_ms:.1f}ms")

            if metadata.rag.zero_result_queries > 0:
                lines.append(f"  [WARN] No results: {metadata.rag.zero_result_queries}x")

            if verbose and metadata.rag.by_domain:
                lines.append(f"  By domain:")
                for domain, count in metadata.rag.by_domain.items():
                    lines.append(f"    {domain}: {count}")

        return lines

    @staticmethod
    def _format_planning(
        metadata: "SessionMetadata",
        verbose: bool,
    ) -> list:
        """Format planning section."""
        lines = []

        if metadata.planning.subgoals_generated > 0:
            lines.append(f"\nPlanning:")

            if metadata.planning.initial_complexity_score > 0:
                lines.append(f"  Complexity: {metadata.planning.initial_complexity_score:.1f}")

            lines.append(f"  Subgoals: {metadata.planning.subgoals_generated}")

            if metadata.planning.final_plan_quality_score > 0:
                lines.append(f"  Plan quality: {metadata.planning.final_plan_quality_score:.0%}")

            if metadata.planning.replan_count > 0:
                lines.append(f"  Replans: {metadata.planning.replan_count}")

                if verbose and metadata.planning.replanning_reasons:
                    lines.append(f"  Reasons:")
                    for reason in metadata.planning.replanning_reasons[:3]:
                        lines.append(f"    - {reason}")

        return lines

    @staticmethod
    def _format_execution(
        metadata: "SessionMetadata",
        verbose: bool,
    ) -> list:
        """Format execution section."""
        lines = []

        if metadata.execution_steps:
            lines.append(f"\nExecution:")
            lines.append(f"  Steps: {metadata.successful_steps}/{metadata.total_steps}")

            success_rate = (
                metadata.successful_steps / metadata.total_steps * 100
                if metadata.total_steps > 0
                else 0
            )
            lines.append(f"  Success rate: {success_rate:.0f}%")

            if verbose:
                # Show step details
                lines.append(f"  Steps:")
                for step in metadata.execution_steps[:5]:
                    status = "[OK]" if step.success else "[FAIL]"
                    lines.append(
                        f"    {step.order}. {status} {step.action} ({step.duration_ms:.0f}ms)"
                    )

                if len(metadata.execution_steps) > 5:
                    lines.append(f"    ... and {len(metadata.execution_steps) - 5} more")

        return lines

    @staticmethod
    def _format_recovery(
        metadata: "SessionMetadata",
        verbose: bool,
    ) -> list:
        """Format error recovery section."""
        lines = []

        if metadata.error_recoveries:
            lines.append(f"\nError Recovery:")
            lines.append(f"  Attempts: {len(metadata.error_recoveries)}")

            success_count = sum(1 for r in metadata.error_recoveries if r.success)
            lines.append(f"  Successful: {success_count}")

            if verbose:
                lines.append(f"  Details:")
                for recovery in metadata.error_recoveries[:3]:
                    status = "[OK]" if recovery.success else "[FAIL]"
                    lines.append(
                        f"    {status} {recovery.error_type} via {recovery.recovery_strategy}"
                    )

        return lines

    @staticmethod
    def _format_bridge(
        metadata: "SessionMetadata",
        verbose: bool,
    ) -> list:
        """Format bridge health section."""
        lines = []

        has_issues = (
            metadata.bridge.touchdesigner_degraded_mode_activated
            or metadata.bridge.houdini_degraded_mode_activated
            or metadata.bridge.fallback_to_queuing
            or metadata.bridge.fallback_to_ui
        )

        if has_issues:
            lines.append(f"\nBridge Issues:")

            if metadata.bridge.touchdesigner_degraded_mode_activated:
                lines.append(
                    f"  TouchDesigner degraded mode (retries: {metadata.bridge.touchdesigner_retries_needed})"
                )

            if metadata.bridge.houdini_degraded_mode_activated:
                lines.append(
                    f"  Houdini degraded mode (retries: {metadata.bridge.houdini_retries_needed})"
                )

            if metadata.bridge.fallback_to_queuing:
                lines.append(f"  Fallback to queuing used")

            if metadata.bridge.fallback_to_ui:
                lines.append(f"  Fallback to UI automation used")

        return lines


def format_session_summary(
    metadata: "SessionMetadata",
    verbose: bool = False,
) -> str:
    """Format session summary (convenience function).

    Args:
        metadata: Session metadata
        verbose: Include detailed information

    Returns:
        Formatted string
    """
    return SessionDisplayFormatter.format_session_output(metadata, verbose)


def print_session_summary(
    metadata: "SessionMetadata",
    verbose: bool = False,
) -> None:
    """Print session summary to console.

    Args:
        metadata: Session metadata
        verbose: Include detailed information
    """
    print(format_session_summary(metadata, verbose))