"""Houdini Bridge - Live Bridge Communication.

Provides bridge server and client for Houdini automation via
file-based inbox/outbox protocol.
"""

from app.domains.houdini.bridge.server import (
    HoudiniBridgeServer,
    HoudiniBridgeConfig,
    start_houdini_bridge,
)
from app.domains.houdini.bridge.client import (
    HoudiniBridgeClient,
    send_recipe_to_houdini,
)
from app.domains.houdini.bridge.models import (
    RecipeRequest,
    RecipeResult,
    RecipeStep,
    StepResult,
)

__all__ = [
    # Server
    "HoudiniBridgeServer",
    "HoudiniBridgeConfig",
    "start_houdini_bridge",
    # Client
    "HoudiniBridgeClient",
    "send_recipe_to_houdini",
    # Models
    "RecipeRequest",
    "RecipeResult",
    "RecipeStep",
    "StepResult",
]