from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime

from model_router.types import RoutingDecision, RoutingSource, TaskRequest


@dataclass(frozen=True, slots=True)
class RoutingEvent:
    decision: RoutingDecision
    category: str | None
    tags: frozenset[str]
    prompt_chars: int
    is_agentic: bool
    tool_schema_count: int
    timestamp: datetime


def build_event(task: TaskRequest, decision: RoutingDecision) -> RoutingEvent:
    return RoutingEvent(
        decision=decision,
        category=task.category,
        tags=task.tags,
        prompt_chars=len(task.prompt),
        is_agentic=task.is_agentic,
        tool_schema_count=task.tool_schema_count,
        timestamp=datetime.now(UTC),
    )


EmitFn = Callable[[RoutingEvent], None]


@dataclass(slots=True)
class InMemorySink:
    events: list[RoutingEvent] = field(default_factory=list)

    def __call__(self, event: RoutingEvent) -> None:
        self.events.append(event)

    def keyword_flagged(self) -> tuple[RoutingEvent, ...]:
        return tuple(e for e in self.events if e.decision.source == RoutingSource.KEYWORD_FLAGGED)

    def escalations(self) -> tuple[RoutingEvent, ...]:
        return tuple(e for e in self.events if e.decision.source == RoutingSource.ESCALATED)
