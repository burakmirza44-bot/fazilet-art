"""Goal Generator Module.

Provides bounded, policy-aware goal generation from runtime context.
Integrates with memory, error normalization, checkpoints, and knowledge systems.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from app.agent_core.goal_errors import (
    GoalGenerationError,
    GoalGenerationErrorType,
    create_ambiguity_error,
    create_context_missing_error,
    create_domain_inference_error,
    create_generation_failed_error,
    create_no_usable_goal_error,
    create_safety_blocked_error,
)
from app.agent_core.goal_models import (
    DomainHint,
    ExecutionFeasibility,
    GoalArtifact,
    GoalGenerationMode,
    GoalGenerationResult,
    GoalRequest,
    GoalSourceSignal,
    GoalType,
)


# Domain keywords for inference
DOMAIN_KEYWORDS: dict[str, list[str]] = {
    DomainHint.HOUDINI.value: [
        "houdini", "geo", "sop", "dop", "cop", "vex", "pdg", "rop",
        "simulation", "particles", "pyro", "flip", "vellum", "heightfield",
        "procedural", "node network", "hda", "attribute", "group",
    ],
    DomainHint.TOUCHDESIGNER.value: [
        "touchdesigner", "td", "chop", "top", "dat", "sop", "mat",
        "visual", "realtime", "interactive", "animation", "channel",
        "texture", "table", "script", "panel", "parameter",
    ],
}

# Safety patterns to block
UNSAFE_PATTERNS: list[str] = [
    r"delete\s+all",
    r"remove\s+all",
    r"format\s+disk",
    r"rm\s+-rf",
    r"drop\s+table",
    r"truncate\s+table",
    r"delete\s+from\s+\*",
    r"shutdown",
    r"reboot",
    r"kill\s+-9",
    r"force\s+quit",
    r"terminate\s+all",
]

# Repair pattern templates
REPAIR_PATTERNS: dict[str, dict[str, Any]] = {
    "bridge_unavailable": {
        "title": "Restore Bridge Connection",
        "description": "Attempt to reconnect to the execution bridge",
        "repair_hint": "Check bridge process and retry connection",
    },
    "execution_failed": {
        "title": "Retry Execution",
        "description": "Retry the failed execution with adjusted parameters",
        "repair_hint": "Adjust parameters based on error context",
    },
    "timeout": {
        "title": "Handle Timeout",
        "description": "Handle timeout by breaking into smaller steps",
        "repair_hint": "Reduce scope or increase timeout",
    },
    "precondition_failed": {
        "title": "Satisfy Preconditions",
        "description": "Ensure preconditions are satisfied before retrying",
        "repair_hint": "Check and satisfy missing preconditions",
    },
}


@dataclass
class GoalGeneratorConfig:
    """Configuration for GoalGenerator."""

    enable_memory: bool = True
    enable_safety_checks: bool = True
    enable_ranking: bool = True
    max_goals_per_request: int = 5
    min_confidence_threshold: float = 0.3
    max_ambiguity_flags: int = 3
    enable_transcript_knowledge: bool = True
    enable_recipe_knowledge: bool = True


class GoalGenerator:
    """Bounded, policy-aware goal generation from runtime context.

    Integrates with:
    - MemoryRetrievalRequest/Result for memory-informed goals
    - NormalizedError for repair goals
    - Checkpoint for resume goals
    - Verification for verification goals

    Example:
        generator = GoalGenerator(repo_root="/path/to/repo")
        request = GoalRequest.create(
            task_id="task_001",
            session_id="session_001",
            domain_hint=DomainHint.HOUDINI,
            raw_task_summary="Create a procedural terrain with heightfield",
        )
        result = generator.generate_goals(request)
        if result.has_goals:
            goal = result.primary_goal
            print(f"Generated goal: {goal.title}")
    """

    def __init__(
        self,
        repo_root: str = ".",
        config: GoalGeneratorConfig | None = None,
    ):
        """Initialize the GoalGenerator.

        Args:
            repo_root: Repository root for memory stores
            config: Optional configuration
        """
        self._repo_root = repo_root
        self._config = config or GoalGeneratorConfig()
        self._error_log: list[GoalGenerationError] = []

    @property
    def config(self) -> GoalGeneratorConfig:
        """Get the configuration."""
        return self._config

    @property
    def error_log(self) -> list[GoalGenerationError]:
        """Get the error log."""
        return self._error_log.copy()

    def generate_goals(self, request: GoalRequest) -> GoalGenerationResult:
        """Generate goals from a goal request.

        Main entry point for goal generation. Routes to appropriate
        generation method based on goal_generation_mode.

        Args:
            request: GoalRequest with context and parameters

        Returns:
            GoalGenerationResult with generated goals and metadata
        """
        mode = request.goal_generation_mode

        # Validate request
        validation_error = self._validate_request(request)
        if validation_error:
            self._error_log.append(validation_error)
            return GoalGenerationResult.error_result(
                mode=mode,
                errors=[validation_error.to_dict()],
            )

        # Route to appropriate generation method
        try:
            if mode == GoalGenerationMode.ROOT_GOAL.value:
                goals = self.generate_root_goal(request)
            elif mode == GoalGenerationMode.SUBGOAL_GENERATION.value:
                parent = self._extract_parent_goal(request)
                goals = self.generate_subgoals(request, parent)
            elif mode == GoalGenerationMode.NEXT_GOAL.value:
                goals = self.generate_next_goal(request)
            elif mode == GoalGenerationMode.REPAIR_GOAL.value:
                goals = self.generate_repair_goal(request)
            elif mode == GoalGenerationMode.VERIFICATION_GOAL.value:
                goals = self.generate_verification_goal(request)
            elif mode == GoalGenerationMode.RESUME_GOAL.value:
                goals = self.generate_resume_goal(request)
            elif mode == GoalGenerationMode.MIXED.value:
                goals = self._generate_mixed_goals(request)
            else:
                goals = self.generate_root_goal(request)

        except Exception as e:
            error = create_generation_failed_error(
                reason=str(e),
                task_id=request.task_id,
                domain=request.domain_hint,
                original_error=e,
            )
            self._error_log.append(error)
            return GoalGenerationResult.error_result(
                mode=mode,
                errors=[error.to_dict()],
            )

        # Infer domain
        domain_inferred, domain_confidence = self._infer_domain(request)

        # Apply safety checks
        if self._config.enable_safety_checks:
            goals = self._apply_safety_checks(goals)

        # Rank goals
        if self._config.enable_ranking:
            goals = self._rank_goals(goals)

        # Filter blocked goals
        blocked_count = sum(1 for g in goals if g.is_blocked)
        active_goals = [g for g in goals if not g.is_blocked]

        # Apply max limit
        filtered_count = max(0, len(active_goals) - request.max_goal_count)
        selected_goals = active_goals[:request.max_goal_count]

        # Check for memory/knowledge influence
        memory_influenced = bool(request.memory_summary)
        transcript_used = bool(request.transcript_knowledge_summary)
        recipe_used = bool(request.recipe_knowledge_summary)

        # Build result
        return GoalGenerationResult(
            goal_generation_performed=True,
            generated_goal_count=len(goals),
            selected_goal_ids=[g.goal_id for g in selected_goals],
            selected_goal_summary=selected_goals[0].description if selected_goals else "",
            goal_generation_mode=mode,
            domain_inferred=domain_inferred,
            domain_confidence=domain_confidence,
            memory_influenced=memory_influenced,
            transcript_knowledge_used=transcript_used,
            recipe_knowledge_used=recipe_used,
            ambiguity_summary=self._get_ambiguity_summary(goals),
            blocked_goal_count=blocked_count,
            filtered_goal_count=filtered_count,
            generated_goals=goals,
            final_status="success" if selected_goals else "no_goals",
        )

    def generate_root_goal(self, request: GoalRequest) -> list[GoalArtifact]:
        """Generate a root goal from task context.

        Analyzes the raw task summary, infers domain, retrieves memory
        patterns, and generates a structured root goal.

        Args:
            request: GoalRequest with task context

        Returns:
            List of candidate root goals
        """
        goals: list[GoalArtifact] = []

        # Normalize task summary
        normalized = self._normalize_task(request.raw_task_summary)

        # Infer domain
        domain, confidence = self._infer_domain(request)

        # Generate primary goal
        goal = GoalArtifact.create(
            goal_type=GoalType.ROOT_GOAL,
            title=self._extract_title(normalized),
            description=normalized,
            domain=domain,
            task_id=request.task_id,
            session_id=request.session_id,
            confidence=confidence,
        )

        # Add source signals
        goal.add_source_signal(GoalSourceSignal.TASK)

        if request.memory_summary:
            goal.add_source_signal(GoalSourceSignal.MEMORY)

        if request.transcript_knowledge_summary:
            goal.add_source_signal(GoalSourceSignal.TRANSCRIPT_KNOWLEDGE)

        if request.recipe_knowledge_summary:
            goal.add_source_signal(GoalSourceSignal.RECIPE_KNOWLEDGE)

        # Infer execution feasibility
        goal.execution_feasibility = self._infer_feasibility(request, confidence).value

        # Extract preconditions from task
        preconditions = self._extract_preconditions(normalized)
        for precond in preconditions:
            goal.add_precondition(precond)

        # Extract success criteria
        goal.success_criteria = self._extract_success_criteria(normalized)

        goals.append(goal)

        # Generate alternative goals if ambiguity detected
        alternatives = self._generate_alternative_goals(request, goal)
        goals.extend(alternatives)

        return goals

    def generate_subgoals(
        self,
        request: GoalRequest,
        parent: GoalArtifact | None,
    ) -> list[GoalArtifact]:
        """Generate subgoals from a parent goal.

        Decomposes the parent goal into smaller, executable subgoals.

        Args:
            request: GoalRequest with context
            parent: Parent goal to decompose

        Returns:
            List of subgoals
        """
        if not parent:
            return self.generate_root_goal(request)

        goals: list[GoalArtifact] = []
        domain = parent.domain or request.domain_hint

        # Simple decomposition based on common patterns
        subgoal_templates = self._get_subgoal_templates(parent.description)

        for i, template in enumerate(subgoal_templates):
            subgoal = GoalArtifact.create(
                goal_type=GoalType.SUBGOAL,
                title=template["title"],
                description=template["description"],
                domain=domain,
                task_id=request.task_id,
                session_id=request.session_id,
                parent_goal_id=parent.goal_id,
                confidence=parent.confidence * (0.9 - i * 0.1),
            )

            subgoal.add_source_signal(GoalSourceSignal.TASK)

            if "backend_hint" in template:
                subgoal.backend_hint = template["backend_hint"]

            if "preconditions" in template:
                for precond in template["preconditions"]:
                    subgoal.add_precondition(precond)

            subgoal.execution_feasibility = ExecutionFeasibility.HIGH.value
            goals.append(subgoal)

        return goals

    def generate_next_goal(self, request: GoalRequest) -> list[GoalArtifact]:
        """Generate the next immediate action goal.

        Determines the next action based on current runtime state
        and active subgoal context.

        Args:
            request: GoalRequest with runtime state context

        Returns:
            List with next action goal
        """
        goals: list[GoalArtifact] = []

        # Check active subgoal context for next step
        active_context = request.active_subgoal_context
        current_state = request.current_runtime_state_summary

        # Generate next action from context
        next_action = self._determine_next_action(active_context, current_state)

        domain, confidence = self._infer_domain(request)

        goal = GoalArtifact.create(
            goal_type=GoalType.NEXT_ACTION_GOAL,
            title=next_action["title"],
            description=next_action["description"],
            domain=domain,
            task_id=request.task_id,
            session_id=request.session_id,
            confidence=confidence,
        )

        goal.add_source_signal(GoalSourceSignal.OBSERVATION)

        if "backend_hint" in next_action:
            goal.backend_hint = next_action["backend_hint"]

        goal.execution_feasibility = ExecutionFeasibility.HIGH.value
        goals.append(goal)

        return goals

    def generate_repair_goal(self, request: GoalRequest) -> list[GoalArtifact]:
        """Generate a repair goal from failure context.

        Analyzes the failure context and generates a goal to repair
        the failure and continue execution.

        Args:
            request: GoalRequest with failure_context

        Returns:
            List of repair goals
        """
        goals: list[GoalArtifact] = []

        failure_context = request.failure_context
        if not failure_context:
            # No failure context, generate fallback
            return self.generate_root_goal(request)

        error_type = failure_context.get("error_type", "unknown")
        error_message = failure_context.get("message", "")

        domain, confidence = self._infer_domain(request)

        # Match repair pattern
        repair_pattern = self._match_repair_pattern(error_type, error_message)

        goal = GoalArtifact.create(
            goal_type=GoalType.REPAIR_GOAL,
            title=repair_pattern["title"],
            description=repair_pattern["description"],
            domain=domain,
            task_id=request.task_id,
            session_id=request.session_id,
            confidence=confidence * 0.8,  # Slightly lower for repair
        )

        goal.add_source_signal(GoalSourceSignal.FAILURE_CONTEXT)
        goal.add_source_signal(GoalSourceSignal.REPAIR_CONTEXT)

        goal.repair_hint = repair_pattern["repair_hint"]

        # Link to failed goal if available
        if "failed_goal_id" in failure_context:
            goal.parent_goal_id = failure_context["failed_goal_id"]

        goal.execution_feasibility = ExecutionFeasibility.MEDIUM.value

        # Add preconditions from failure context
        if "missing_preconditions" in failure_context:
            for precond in failure_context["missing_preconditions"]:
                goal.add_precondition(precond)

        goals.append(goal)

        return goals

    def generate_verification_goal(self, request: GoalRequest) -> list[GoalArtifact]:
        """Generate a verification goal to collect missing evidence.

        Analyzes verification context and generates a goal to
        verify the outcome of a previous goal.

        Args:
            request: GoalRequest with verification_context

        Returns:
            List of verification goals
        """
        goals: list[GoalArtifact] = []

        verification_context = request.verification_context
        if not verification_context:
            return []

        domain, confidence = self._infer_domain(request)

        # Extract what needs verification
        evidence_gaps = verification_context.get("evidence_gaps", [])
        target_goal_id = verification_context.get("target_goal_id", "")
        verification_type = verification_context.get("verification_type", "outcome")

        for i, gap in enumerate(evidence_gaps[:3]):  # Max 3 verification goals
            goal = GoalArtifact.create(
                goal_type=GoalType.VERIFICATION_GOAL,
                title=f"Verify: {gap.get('description', 'outcome')}",
                description=f"Collect evidence for: {gap.get('description', 'verification')}",
                domain=domain,
                task_id=request.task_id,
                session_id=request.session_id,
                confidence=confidence * 0.9,
            )

            goal.add_source_signal(GoalSourceSignal.VERIFICATION_CONTEXT)
            goal.verification_hint = gap.get("hint", "")

            if target_goal_id:
                goal.parent_goal_id = target_goal_id

            goal.execution_feasibility = ExecutionFeasibility.HIGH.value
            goals.append(goal)

        return goals

    def generate_resume_goal(self, request: GoalRequest) -> list[GoalArtifact]:
        """Generate a resume goal from checkpoint context.

        Analyzes the checkpoint summary and generates a goal to
        resume execution from the checkpoint.

        Args:
            request: GoalRequest with checkpoint_summary

        Returns:
            List of resume goals
        """
        goals: list[GoalArtifact] = []

        checkpoint_summary = request.checkpoint_summary
        if not checkpoint_summary:
            return []

        domain = checkpoint_summary.get("domain", request.domain_hint)
        checkpoint_id = checkpoint_summary.get("checkpoint_id", "")

        # Get last completed and next pending steps
        last_completed = checkpoint_summary.get("last_completed_step", {})
        next_pending = checkpoint_summary.get("next_pending_step", {})
        remaining_steps = checkpoint_summary.get("remaining_steps", [])

        if not next_pending and remaining_steps:
            next_pending = remaining_steps[0]

        if next_pending:
            goal = GoalArtifact.create(
                goal_type=GoalType.RESUME_GOAL,
                title=f"Resume: {next_pending.get('description', 'execution')}",
                description=f"Resume execution from checkpoint {checkpoint_id}. "
                           f"Next step: {next_pending.get('description', 'unknown')}",
                domain=domain,
                task_id=request.task_id,
                session_id=request.session_id,
                confidence=0.9,
            )

            goal.add_source_signal(GoalSourceSignal.TASK)

            if checkpoint_id:
                goal.success_criteria["checkpoint_id"] = checkpoint_id

            goal.execution_feasibility = ExecutionFeasibility.HIGH.value

            goals.append(goal)

        return goals

    # Internal helper methods

    def _validate_request(self, request: GoalRequest) -> GoalGenerationError | None:
        """Validate a goal request.

        Args:
            request: Request to validate

        Returns:
            GoalGenerationError if invalid, None if valid
        """
        missing_fields = []

        if not request.task_id:
            missing_fields.append("task_id")

        if not request.session_id:
            missing_fields.append("session_id")

        if not request.raw_task_summary:
            missing_fields.append("raw_task_summary")

        if missing_fields:
            return create_context_missing_error(
                missing_fields=missing_fields,
                task_id=request.task_id,
                domain=request.domain_hint,
            )

        return None

    def _infer_domain(self, request: GoalRequest) -> tuple[str, float]:
        """Infer domain from request context.

        Args:
            request: GoalRequest with context

        Returns:
            Tuple of (domain, confidence)
        """
        # Check explicit hint first
        if request.domain_hint and request.domain_hint != DomainHint.UNKNOWN.value:
            return request.domain_hint, 0.95

        # Analyze task content
        text = f"{request.raw_task_summary} {request.observation_summary}".lower()

        scores: dict[str, int] = {}

        for domain, keywords in DOMAIN_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw.lower() in text)
            if score > 0:
                scores[domain] = score

        if scores:
            best_domain = max(scores, key=scores.get)
            total_matches = sum(scores.values())
            confidence = min(0.9, 0.5 + scores[best_domain] * 0.1)
            return best_domain, confidence

        return DomainHint.GENERIC.value, 0.3

    def _normalize_task(self, task: str) -> str:
        """Normalize task description.

        Args:
            task: Raw task string

        Returns:
            Normalized task string
        """
        # Remove extra whitespace
        normalized = " ".join(task.split())
        return normalized.strip()

    def _extract_title(self, description: str) -> str:
        """Extract a short title from description.

        Args:
            description: Full description

        Returns:
            Short title
        """
        # Take first sentence or first 50 chars
        sentences = description.split(". ")
        first = sentences[0]

        if len(first) <= 50:
            return first

        # Truncate to word boundary
        words = first[:50].split()
        return " ".join(words[:-1]) + "..." if len(words) > 1 else first[:50]

    def _infer_feasibility(
        self,
        request: GoalRequest,
        domain_confidence: float,
    ) -> ExecutionFeasibility:
        """Infer execution feasibility.

        Args:
            request: GoalRequest
            domain_confidence: Domain inference confidence

        Returns:
            ExecutionFeasibility level
        """
        if domain_confidence >= 0.8:
            return ExecutionFeasibility.HIGH
        elif domain_confidence >= 0.5:
            return ExecutionFeasibility.MEDIUM
        elif domain_confidence > 0:
            return ExecutionFeasibility.LOW
        return ExecutionFeasibility.UNKNOWN

    def _extract_preconditions(self, description: str) -> list[str]:
        """Extract preconditions from description.

        Args:
            description: Task description

        Returns:
            List of precondition strings
        """
        preconditions = []

        # Look for explicit precondition patterns
        patterns = [
            r"requires?\s+(.+?)(?:\s+before|\s+to|\.$)",
            r"needs?\s+(.+?)(?:\s+before|\s+to|\.$)",
            r"must\s+have\s+(.+?)(?:\s+before|\.$)",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, description.lower())
            preconditions.extend(matches)

        return preconditions[:3]  # Max 3

    def _extract_success_criteria(self, description: str) -> dict[str, Any]:
        """Extract success criteria from description.

        Args:
            description: Task description

        Returns:
            Dictionary of success criteria
        """
        criteria: dict[str, Any] = {}

        # Look for outcome patterns
        patterns = [
            (r"result\s+should\s+be\s+(.+?)(?:\.$)", "expected_result"),
            (r"output\s+(.+?)(?:\.$)", "expected_output"),
            (r"create\s+(.+?)(?:\.$)", "expected_artifact"),
        ]

        for pattern, key in patterns:
            match = re.search(pattern, description.lower())
            if match:
                criteria[key] = match.group(1).strip()

        return criteria

    def _apply_safety_checks(self, goals: list[GoalArtifact]) -> list[GoalArtifact]:
        """Apply safety checks to goals.

        Args:
            goals: Goals to check

        Returns:
            Goals with safety blocks applied
        """
        for goal in goals:
            safe, reason = self._safety_check(goal)
            if not safe:
                goal.block(reason)
                goal.safety_summary = reason

        return goals

    def _safety_check(self, goal: GoalArtifact) -> tuple[bool, str]:
        """Check if a goal is safe.

        Args:
            goal: Goal to check

        Returns:
            Tuple of (is_safe, reason)
        """
        text = f"{goal.title} {goal.description}".lower()

        for pattern in UNSAFE_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return False, f"Matches unsafe pattern: {pattern}"

        return True, ""

    def _rank_goals(self, goals: list[GoalArtifact]) -> list[GoalArtifact]:
        """Rank goals by composite score.

        Args:
            goals: Goals to rank

        Returns:
            Sorted goals by score
        """
        def score_goal(goal: GoalArtifact) -> float:
            score = goal.confidence

            # Boost for source signals
            signal_boost = len(goal.source_signals) * 0.05
            score += signal_boost

            # Boost for high feasibility
            if goal.has_high_feasibility:
                score += 0.1

            # Penalize for ambiguity
            ambiguity_penalty = len(goal.ambiguity_flags) * 0.05
            score -= ambiguity_penalty

            # Penalize for preconditions
            precondition_penalty = len(goal.preconditions) * 0.02
            score -= precondition_penalty

            return max(0, score)

        return sorted(goals, key=score_goal, reverse=True)

    def _generate_alternative_goals(
        self,
        request: GoalRequest,
        primary: GoalArtifact,
    ) -> list[GoalArtifact]:
        """Generate alternative goals if ambiguity detected.

        Args:
            request: Original request
            primary: Primary goal

        Returns:
            List of alternative goals
        """
        alternatives: list[GoalArtifact] = []

        # Check for ambiguity
        ambiguity_flags = self._detect_ambiguity(request.raw_task_summary)

        if len(ambiguity_flags) <= 1:
            return alternatives

        primary.add_ambiguity_flag(ambiguity_flags[0])

        # Generate alternative interpretations
        domain, _ = self._infer_domain(request)

        for i, flag in enumerate(ambiguity_flags[1:2]):  # Max 2 alternatives
            alt = GoalArtifact.create(
                goal_type=GoalType.ROOT_GOAL,
                title=f"Alternative: {primary.title}",
                description=f"Alternative interpretation: {primary.description}",
                domain=domain,
                task_id=request.task_id,
                session_id=request.session_id,
                confidence=primary.confidence * 0.7,
            )

            alt.add_ambiguity_flag(flag)
            alt.add_source_signal(GoalSourceSignal.TASK)
            alternatives.append(alt)

        return alternatives

    def _detect_ambiguity(self, text: str) -> list[str]:
        """Detect ambiguity in text.

        Args:
            text: Text to analyze

        Returns:
            List of ambiguity flags
        """
        flags = []

        # Check for vague terms
        vague_terms = ["something", "some", "maybe", "perhaps", "possibly"]
        text_lower = text.lower()
        for term in vague_terms:
            if term in text_lower:
                flags.append(f"vague_term:{term}")

        # Check for multiple domains
        domain_count = 0
        for domain_keywords in DOMAIN_KEYWORDS.values():
            if any(kw in text_lower for kw in domain_keywords):
                domain_count += 1

        if domain_count > 1:
            flags.append("multiple_domains")

        # Check for missing specifics
        if not re.search(r"\d+", text):  # No numbers
            flags.append("no_specifics")

        return flags

    def _get_ambiguity_summary(self, goals: list[GoalArtifact]) -> str:
        """Get summary of ambiguity across goals.

        Args:
            goals: Goals to summarize

        Returns:
            Ambiguity summary string
        """
        all_flags: list[str] = []
        for goal in goals:
            all_flags.extend(goal.ambiguity_flags)

        if not all_flags:
            return ""

        unique_flags = list(set(all_flags))
        return f"Ambiguity detected: {', '.join(unique_flags)}"

    def _get_subgoal_templates(self, description: str) -> list[dict[str, Any]]:
        """Get subgoal templates for decomposition.

        Args:
            description: Parent goal description

        Returns:
            List of subgoal templates
        """
        # Simple decomposition: prepare, execute, verify
        return [
            {
                "title": "Prepare environment",
                "description": f"Set up environment for: {description[:50]}",
                "backend_hint": "setup",
                "preconditions": ["Environment accessible"],
            },
            {
                "title": "Execute main action",
                "description": f"Execute: {description[:60]}",
                "backend_hint": "execute",
            },
            {
                "title": "Verify result",
                "description": "Verify the execution result",
                "backend_hint": "verify",
            },
        ]

    def _determine_next_action(
        self,
        active_context: dict[str, Any],
        current_state: str,
    ) -> dict[str, Any]:
        """Determine next action from context.

        Args:
            active_context: Active subgoal context
            current_state: Current runtime state

        Returns:
            Next action dictionary
        """
        # Check for pending steps
        pending_steps = active_context.get("pending_steps", [])
        if pending_steps:
            next_step = pending_steps[0]
            return {
                "title": next_step.get("title", "Execute next step"),
                "description": next_step.get("description", ""),
                "backend_hint": next_step.get("action", ""),
            }

        # Default next action
        return {
            "title": "Continue execution",
            "description": f"Continue with: {current_state[:50] if current_state else 'next step'}",
            "backend_hint": "continue",
        }

    def _match_repair_pattern(
        self,
        error_type: str,
        error_message: str,
    ) -> dict[str, Any]:
        """Match error to repair pattern.

        Args:
            error_type: Type of error
            error_message: Error message

        Returns:
            Repair pattern dictionary
        """
        error_lower = error_type.lower()

        for pattern_key, pattern in REPAIR_PATTERNS.items():
            if pattern_key in error_lower:
                return pattern

        # Check message for hints
        message_lower = error_message.lower()
        if "timeout" in message_lower:
            return REPAIR_PATTERNS["timeout"]
        if "unavailable" in message_lower or "connection" in message_lower:
            return REPAIR_PATTERNS["bridge_unavailable"]

        # Default repair pattern
        return {
            "title": "Recover from error",
            "description": f"Recover from error: {error_type}",
            "repair_hint": "Analyze error and retry with adjusted approach",
        }

    def _extract_parent_goal(self, request: GoalRequest) -> GoalArtifact | None:
        """Extract parent goal from request context.

        Args:
            request: GoalRequest

        Returns:
            Parent GoalArtifact or None
        """
        parent_context = request.current_goal_context
        if not parent_context:
            return None

        # Reconstruct parent from context
        return GoalArtifact(
            goal_id=parent_context.get("goal_id", "parent_goal"),
            title=parent_context.get("title", ""),
            description=parent_context.get("description", ""),
            domain=parent_context.get("domain", request.domain_hint),
            goal_type=parent_context.get("goal_type", GoalType.ROOT_GOAL.value),
        )

    def _generate_mixed_goals(self, request: GoalRequest) -> list[GoalArtifact]:
        """Generate goals in mixed mode.

        Combines multiple generation modes based on available context.

        Args:
            request: GoalRequest

        Returns:
            List of goals from multiple modes
        """
        goals: list[GoalArtifact] = []

        # Check for failure context (priority)
        if request.failure_context:
            repair_goals = self.generate_repair_goal(request)
            goals.extend(repair_goals)

        # Check for checkpoint context
        if request.checkpoint_summary:
            resume_goals = self.generate_resume_goal(request)
            goals.extend(resume_goals)

        # Check for verification context
        if request.verification_context:
            verification_goals = self.generate_verification_goal(request)
            goals.extend(verification_goals)

        # If no special context, generate root goal
        if not goals:
            root_goals = self.generate_root_goal(request)
            goals.extend(root_goals)

        return goals


def build_goal_request_from_task(
    task: str,
    task_id: str,
    session_id: str,
    domain: str = "",
    memory_context: dict[str, Any] | None = None,
    checkpoint: dict[str, Any] | None = None,
    failure_context: dict[str, Any] | None = None,
    **kwargs: Any,
) -> GoalRequest:
    """Build a GoalRequest from task parameters.

    Convenience function for creating GoalRequest with common parameters.

    Args:
        task: Task description
        task_id: Task ID
        session_id: Session ID
        domain: Optional domain hint
        memory_context: Optional memory context
        checkpoint: Optional checkpoint summary
        failure_context: Optional failure context
        **kwargs: Additional parameters

    Returns:
        GoalRequest instance
    """
    mode = GoalGenerationMode.ROOT_GOAL.value

    if failure_context:
        mode = GoalGenerationMode.REPAIR_GOAL.value
    elif checkpoint:
        mode = GoalGenerationMode.RESUME_GOAL.value

    return GoalRequest.create(
        task_id=task_id,
        session_id=session_id,
        domain_hint=domain or DomainHint.UNKNOWN.value,
        raw_task_summary=task,
        memory_summary=memory_context or {},
        checkpoint_summary=checkpoint or {},
        failure_context=failure_context or {},
        goal_generation_mode=mode,
        **kwargs,
    )