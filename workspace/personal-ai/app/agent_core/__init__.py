"""Agent Core Module.

Provides core agent functionality including action dispatch,
backend selection, and safety mechanisms.
"""

from app.agent_core.backend_policy import BackendPolicy, BackendType
from app.agent_core.backend_result import (
    BackendSelectionResult,
    BridgeHealthResult,
    SafetyCheckResult,
    SelectionStatus,
)
from app.agent_core.backend_selector import BackendSelector, get_default_selector, select_backend

__all__ = [
    # Policy
    "BackendPolicy",
    "BackendType",
    # Result
    "BackendSelectionResult",
    "BridgeHealthResult",
    "SafetyCheckResult",
    "SelectionStatus",
    # Selector
    "BackendSelector",
    "get_default_selector",
    "select_backend",
]