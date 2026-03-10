"""Domain Expert Routing for Claude Network.

Provides intelligent routing to domain-specific agents based on
task content, capabilities, and availability.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class RoutingDecision:
    """Result of a routing decision."""

    domain: str
    confidence: float
    reasoning: str = ""
    alternative_domains: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "domain": self.domain,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "alternative_domains": self.alternative_domains,
            "metadata": self.metadata,
        }


@dataclass
class DomainProfile:
    """Profile for a domain expert."""

    name: str
    keywords: list[str]
    capabilities: list[str]
    priority: int = 0
    description: str = ""
    fallback_domains: list[str] = field(default_factory=list)

    def match_score(self, task: str) -> float:
        """Calculate match score for a task.

        Args:
            task: Task description

        Returns:
            Match score between 0 and 1
        """
        task_lower = task.lower()
        score = 0.0

        # Keyword matching
        keyword_matches = sum(1 for kw in self.keywords if kw.lower() in task_lower)
        keyword_score = keyword_matches / max(len(self.keywords), 1)

        # Capability matching (if task mentions specific capabilities)
        capability_matches = sum(1 for cap in self.capabilities if cap.lower() in task_lower)
        capability_score = capability_matches / max(len(self.capabilities), 1)

        # Weighted combination
        score = 0.6 * keyword_score + 0.4 * capability_score

        return min(score, 1.0)


# Pre-defined domain profiles
DOMAIN_PROFILES: dict[str, DomainProfile] = {
    "houdini": DomainProfile(
        name="houdini",
        keywords=[
            "houdini", "vex", "sop", "dop", "cop", "pop", "vop", "geo",
            "particle", "simulation", "procedural", "node", "houdini engine",
            "hda", "attribute", "wrangle", "solver", "pyro", "flip", "vdb",
            "mantra", "karma", "usd", "solaris", "crowd", "cloth", "wire",
        ],
        capabilities=[
            "sop", "dop", "cop", "pop", "vop", "vex", "python", "hscript",
            "usd", "solaris", "karma", "mantra", "crowds", "pyro", "flip",
            "vdb", "heightfield", "terrain", "destruction", "particles",
        ],
        priority=1,
        description="Houdini 3D animation and VFX software expert",
        fallback_domains=["code"],
    ),
    "touchdesigner": DomainProfile(
        name="touchdesigner",
        keywords=[
            "touchdesigner", "td", "top", "chop", "sop", "dat", "mat",
            "visual", "realtime", "interactive", "projection", "mapping",
            "led", "dmx", "osc", "midi", "spout", "ndi", "kinect", "gpu",
            "shader", "glsl", "compute", "texture", "feedback", "timeline",
        ],
        capabilities=[
            "top", "chop", "sop", "dat", "mat", "glsl", "python", "cuda",
            "osc", "midi", "dmx", "spout", "ndi", "kinect", "realtime",
            "interactive", "projection", "mapping", "audio", "visual",
        ],
        priority=1,
        description="TouchDesigner real-time visual development expert",
        fallback_domains=["code"],
    ),
    "code": DomainProfile(
        name="code",
        keywords=[
            "python", "javascript", "typescript", "rust", "go", "java",
            "function", "class", "module", "api", "database", "web", "server",
            "script", "program", "algorithm", "debug", "test", "refactor",
            "git", "npm", "pip", "package", "library", "framework",
        ],
        capabilities=[
            "python", "javascript", "typescript", "rust", "go", "java",
            "sql", "html", "css", "json", "yaml", "toml", "api", "cli",
            "testing", "debugging", "refactoring", "documentation",
        ],
        priority=0,
        description="General-purpose coding and software development expert",
        fallback_domains=[],
    ),
    "blender": DomainProfile(
        name="blender",
        keywords=[
            "blender", "cycles", "eevee", "geometry nodes", "shader nodes",
            "compositing", "rigging", "animation", "sculpting", "uv",
            "texture", "render", "bake", "armature", "bone", "weight paint",
        ],
        capabilities=[
            "modeling", "sculpting", "animation", "rigging", "rendering",
            "compositing", "geometry_nodes", "python", "cycles", "eevee",
        ],
        priority=1,
        description="Blender 3D creation suite expert",
        fallback_domains=["code"],
    ),
    "unreal": DomainProfile(
        name="unreal",
        keywords=[
            "unreal", "ue4", "ue5", "blueprint", "umg", "niagara", "lumen",
            "nanite", "metahuman", "chaos", "physics", "game", "level",
            "actor", "component", "widget", "material", "postprocess",
        ],
        capabilities=[
            "blueprints", "cpp", "umg", "niagara", "lumen", "nanite",
            "animation", "physics", "ai", "networking", "vr", "ar",
        ],
        priority=1,
        description="Unreal Engine game development expert",
        fallback_domains=["code"],
    ),
}


class DomainRouter:
    """Routes tasks to appropriate domain experts.

    Analyzes task content and routes to the best-matching domain
    based on keywords, capabilities, and priorities.
    """

    def __init__(
        self,
        profiles: dict[str, DomainProfile] | None = None,
        default_domain: str = "code",
        min_confidence: float = 0.3,
    ):
        """Initialize the domain router.

        Args:
            profiles: Custom domain profiles (defaults to DOMAIN_PROFILES)
            default_domain: Default domain when no good match
            min_confidence: Minimum confidence threshold
        """
        self._profiles = profiles or DOMAIN_PROFILES
        self._default_domain = default_domain
        self._min_confidence = min_confidence
        self._availability: dict[str, bool] = {name: True for name in self._profiles}

    def route(self, task: str, context: dict[str, Any] | None = None) -> RoutingDecision:
        """Route a task to the best-matching domain.

        Args:
            task: Task description
            context: Optional routing context

        Returns:
            RoutingDecision with selected domain and confidence
        """
        # Score all domains
        scores: list[tuple[str, float]] = []

        for name, profile in self._profiles.items():
            if not self._availability.get(name, True):
                continue

            score = profile.match_score(task)

            # Apply priority boost
            score += profile.priority * 0.05

            # Apply context-based adjustments
            if context:
                # Boost if domain is explicitly mentioned in context
                if context.get("domain") == name:
                    score += 0.2

                # Boost if task capabilities match domain
                task_capabilities = context.get("capabilities", [])
                if task_capabilities:
                    cap_overlap = sum(1 for c in task_capabilities if c in profile.capabilities)
                    score += cap_overlap * 0.1

            scores.append((name, min(score, 1.0)))

        # Sort by score descending
        scores.sort(key=lambda x: x[1], reverse=True)

        if not scores:
            return RoutingDecision(
                domain=self._default_domain,
                confidence=0.0,
                reasoning="No domains available",
            )

        # Get best match
        best_domain, best_score = scores[0]

        # Check if score meets minimum confidence
        if best_score < self._min_confidence:
            return RoutingDecision(
                domain=self._default_domain,
                confidence=best_score,
                reasoning=f"No domain met minimum confidence ({self._min_confidence}), using default",
                alternative_domains=[d for d, s in scores[:3]],
            )

        # Build decision
        alternatives = [d for d, s in scores[1:4] if s >= self._min_confidence]

        return RoutingDecision(
            domain=best_domain,
            confidence=best_score,
            reasoning=f"Matched keywords and capabilities for {best_domain}",
            alternative_domains=alternatives,
            metadata={
                "all_scores": {d: s for d, s in scores[:5]},
            },
        )

    def route_with_fallback(self, task: str, failed_domain: str | None = None) -> RoutingDecision:
        """Route with fallback support.

        Args:
            task: Task description
            failed_domain: Previously failed domain (to avoid)

        Returns:
            RoutingDecision with fallback handling
        """
        decision = self.route(task)

        # If we should try fallback
        if failed_domain and decision.domain == failed_domain:
            profile = self._profiles.get(failed_domain)
            if profile and profile.fallback_domains:
                fallback = profile.fallback_domains[0]
                if fallback in self._profiles:
                    return RoutingDecision(
                        domain=fallback,
                        confidence=decision.confidence * 0.8,
                        reasoning=f"Fallback from {failed_domain}",
                        alternative_domains=profile.fallback_domains[1:],
                    )

        return decision

    def set_domain_availability(self, domain: str, available: bool) -> None:
        """Set availability for a domain.

        Args:
            domain: Domain name
            available: Whether domain is available
        """
        self._availability[domain] = available

    def get_available_domains(self) -> list[str]:
        """Get list of available domains."""
        return [name for name, avail in self._availability.items() if avail]

    def add_domain_profile(self, profile: DomainProfile) -> None:
        """Add or update a domain profile.

        Args:
            profile: Domain profile to add
        """
        self._profiles[profile.name] = profile
        self._availability[profile.name] = True


class LoadBalancingRouter:
    """Router with load balancing across multiple agents.

    Distributes tasks across multiple agents for the same domain
    based on load and performance.
    """

    def __init__(
        self,
        domain_router: DomainRouter | None = None,
    ):
        """Initialize the load-balancing router.

        Args:
            domain_router: Optional domain router to use
        """
        self._domain_router = domain_router or DomainRouter()
        self._agent_load: dict[str, int] = {}
        self._agent_performance: dict[str, list[float]] = {}

    def register_agent(self, agent_id: str, domain: str) -> None:
        """Register an agent for a domain.

        Args:
            agent_id: Agent identifier
            domain: Domain the agent handles
        """
        key = f"{domain}:{agent_id}"
        self._agent_load[key] = 0
        self._agent_performance[key] = []

    def route(self, task: str, context: dict[str, Any] | None = None) -> RoutingDecision:
        """Route with load balancing.

        Args:
            task: Task description
            context: Optional routing context

        Returns:
            RoutingDecision with agent assignment
        """
        # First, route to domain
        decision = self._domain_router.route(task, context)

        # Then, select best agent for the domain
        agent_id = self._select_agent(decision.domain)

        if agent_id:
            decision.metadata["agent_id"] = agent_id

        return decision

    def _select_agent(self, domain: str) -> str | None:
        """Select the best agent for a domain.

        Args:
            domain: Domain to select agent for

        Returns:
            Agent ID or None if no agents available
        """
        # Find agents for this domain
        domain_agents = [
            (key, self._agent_load.get(key, 0))
            for key in self._agent_load
            if key.startswith(f"{domain}:")
        ]

        if not domain_agents:
            return None

        # Sort by load (ascending)
        domain_agents.sort(key=lambda x: x[1])

        # Select agent with lowest load
        selected_key = domain_agents[0][0]
        agent_id = selected_key.split(":")[1]

        # Increment load
        self._agent_load[selected_key] = self._agent_load.get(selected_key, 0) + 1

        return agent_id

    def report_completion(self, agent_id: str, domain: str, success: bool, duration_ms: float) -> None:
        """Report task completion for load balancing.

        Args:
            agent_id: Agent that completed the task
            domain: Domain of the task
            success: Whether task was successful
            duration_ms: Task duration in milliseconds
        """
        key = f"{domain}:{agent_id}"

        # Decrement load
        if key in self._agent_load and self._agent_load[key] > 0:
            self._agent_load[key] -= 1

        # Track performance
        if key not in self._agent_performance:
            self._agent_performance[key] = []

        performance_score = 1.0 if success else 0.0
        # Factor in duration (normalized)
        duration_factor = max(0, 1.0 - (duration_ms / 60000))  # Normalize to 1 minute
        combined_score = 0.7 * performance_score + 0.3 * duration_factor

        self._agent_performance[key].append(combined_score)

        # Keep only last 10 performance samples
        self._agent_performance[key] = self._agent_performance[key][-10:]

    def get_agent_stats(self, agent_id: str, domain: str) -> dict[str, Any]:
        """Get statistics for an agent.

        Args:
            agent_id: Agent identifier
            domain: Domain of the agent

        Returns:
            Statistics dictionary
        """
        key = f"{domain}:{agent_id}"

        performances = self._agent_performance.get(key, [])
        avg_performance = sum(performances) / len(performances) if performances else 0.0

        return {
            "agent_id": agent_id,
            "domain": domain,
            "current_load": self._agent_load.get(key, 0),
            "average_performance": avg_performance,
            "sample_count": len(performances),
        }


def create_router(
    domains: list[str] | None = None,
    default_domain: str = "code",
) -> DomainRouter:
    """Create a domain router with specified domains.

    Args:
        domains: List of domain names to include (defaults to all)
        default_domain: Default domain for routing

    Returns:
        Configured DomainRouter
    """
    if domains is None:
        return DomainRouter(default_domain=default_domain)

    # Filter profiles to specified domains
    profiles = {
        name: profile
        for name, profile in DOMAIN_PROFILES.items()
        if name in domains
    }

    # Ensure default domain is included
    if default_domain not in profiles:
        profiles[default_domain] = DOMAIN_PROFILES.get(default_domain, DomainProfile(
            name=default_domain,
            keywords=[],
            capabilities=[],
        ))

    return DomainRouter(profiles=profiles, default_domain=default_domain)