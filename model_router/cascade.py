from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

from model_router.config import ESCALATION_PATH
from model_router.models import Effort, Model
from model_router.router import classify
from model_router.telemetry import EmitFn, build_event
from model_router.types import RoutingDecision, RoutingSource, TaskRequest, TaskTier

ResponseT = TypeVar("ResponseT")

_TIER_ORDER = [TaskTier.TRIVIAL, TaskTier.MODERATE, TaskTier.COMPLEX]


def _next_tier(tier: TaskTier) -> TaskTier:
    index = _TIER_ORDER.index(tier)
    return _TIER_ORDER[min(index + 1, len(_TIER_ORDER) - 1)]


def _escalate(decision: RoutingDecision, task: TaskRequest) -> RoutingDecision:
    next_model = ESCALATION_PATH[decision.model]
    next_tier = _next_tier(decision.tier)
    effort = Effort.XHIGH if task.is_agentic else Effort.HIGH
    return RoutingDecision(
        model=next_model,
        effort=effort,
        tier=next_tier,
        source=RoutingSource.ESCALATED,
        reason=f"escalated from {decision.model.value} after validation failure",
    )


@dataclass(frozen=True, slots=True)
class CascadeResult(Generic[ResponseT]):
    response: ResponseT
    attempts: tuple[RoutingDecision, ...]

    @property
    def final_decision(self) -> RoutingDecision:
        return self.attempts[-1]

    @property
    def escalations(self) -> int:
        return len(self.attempts) - 1


def route_with_cascade(
    task: TaskRequest,
    call_fn: Callable[[Model, Effort, str], ResponseT],
    validate_fn: Callable[[ResponseT], bool] | None = None,
    max_escalations: int = 1,
    emit: EmitFn | None = None,
) -> CascadeResult[ResponseT]:
    decision = classify(task, emit=emit)
    attempts = [decision]
    response = call_fn(decision.model, decision.effort, task.prompt)

    while (
        validate_fn is not None
        and not validate_fn(response)
        and len(attempts) - 1 < max_escalations
        and decision.model != ESCALATION_PATH[decision.model]
    ):
        decision = _escalate(decision, task)
        if emit is not None:
            emit(build_event(task, decision))
        attempts.append(decision)
        response = call_fn(decision.model, decision.effort, task.prompt)

    return CascadeResult(response=response, attempts=tuple(attempts))
