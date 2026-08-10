from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from model_router.models import Effort, Model


class TaskTier(StrEnum):
    TRIVIAL = "trivial"
    MODERATE = "moderate"
    COMPLEX = "complex"


class RoutingSource(StrEnum):
    OVERRIDE = "override"
    KEYWORD_FLAGGED = "keyword_flagged"
    HEURISTIC = "heuristic"
    ESCALATED = "escalated"


@dataclass(frozen=True, slots=True)
class TaskRequest:
    prompt: str
    category: str | None = None
    tags: frozenset[str] = field(default_factory=frozenset)
    tool_schema_count: int = 0
    requires_structured_output: bool = False
    is_agentic: bool = False


@dataclass(frozen=True, slots=True)
class RoutingDecision:
    model: Model
    effort: Effort
    tier: TaskTier
    source: RoutingSource
    reason: str
