from __future__ import annotations

from model_router.config import (
    AGENTIC_EFFORT_BUMP,
    CATEGORY_TIER,
    LONG_PROMPT_CHAR_THRESHOLD,
    MANY_TOOLS_THRESHOLD,
    OVERRIDE_CATEGORIES,
    OVERRIDE_KEYWORDS,
    TIER_ROUTE,
)
from model_router.models import Effort, Model
from model_router.telemetry import EmitFn, build_event
from model_router.types import RoutingDecision, RoutingSource, TaskRequest, TaskTier


def _normalize_identifier(value: str) -> str:
    return value.strip().casefold()


def _normalize_prompt(prompt: str) -> str:
    return prompt.casefold().replace("-", " ").replace("_", " ")


def _override_reason(task: TaskRequest) -> tuple[str, RoutingSource] | None:
    if task.category is not None and _normalize_identifier(task.category) in OVERRIDE_CATEGORIES:
        return f"category '{task.category}' is security-critical", RoutingSource.OVERRIDE

    normalized_tags = {_normalize_identifier(tag) for tag in task.tags}
    hit_tags = normalized_tags & OVERRIDE_CATEGORIES
    if hit_tags:
        return f"tag(s) {sorted(hit_tags)} are security-critical", RoutingSource.OVERRIDE

    normalized_prompt = _normalize_prompt(task.prompt)
    for keyword in OVERRIDE_KEYWORDS:
        if keyword in normalized_prompt:
            return (
                f"prompt text matched keyword '{keyword}' (unverified, flagged for audit)",
                RoutingSource.KEYWORD_FLAGGED,
            )

    return None


def _base_tier(task: TaskRequest) -> tuple[TaskTier, str]:
    if task.category is None:
        return TaskTier.MODERATE, "no category supplied, defaulted to moderate"

    normalized = _normalize_identifier(task.category)
    if normalized in CATEGORY_TIER:
        tier = CATEGORY_TIER[normalized]
        return tier, f"category '{task.category}' maps to {tier.value}"

    return (
        TaskTier.MODERATE,
        f"category '{task.category}' not recognized, defaulted to moderate",
    )


def _apply_signal_bumps(tier: TaskTier, task: TaskRequest, base_reason: str) -> tuple[TaskTier, str]:
    reasons = [base_reason]

    if task.is_agentic and tier != TaskTier.COMPLEX:
        tier = TaskTier.COMPLEX
        reasons.append("bumped to complex: agentic task")

    if task.tool_schema_count >= MANY_TOOLS_THRESHOLD and tier != TaskTier.COMPLEX:
        tier = TaskTier.COMPLEX
        reasons.append(f"bumped to complex: {task.tool_schema_count} tool schemas")

    prompt_len = len(task.prompt)
    if tier == TaskTier.TRIVIAL and prompt_len > LONG_PROMPT_CHAR_THRESHOLD:
        tier = TaskTier.MODERATE
        reasons.append(f"bumped to moderate: prompt length {prompt_len} chars")
    elif tier == TaskTier.MODERATE and prompt_len > LONG_PROMPT_CHAR_THRESHOLD * 2:
        tier = TaskTier.COMPLEX
        reasons.append(f"bumped to complex: prompt length {prompt_len} chars")

    return tier, "; ".join(reasons)


def classify(task: TaskRequest, emit: EmitFn | None = None) -> RoutingDecision:
    override = _override_reason(task)
    if override is not None:
        reason, source = override
        effort = Effort.XHIGH if task.is_agentic else Effort.HIGH
        decision = RoutingDecision(
            model=Model.OPUS,
            effort=effort,
            tier=TaskTier.COMPLEX,
            source=source,
            reason=reason,
        )
        if emit is not None:
            emit(build_event(task, decision))
        return decision

    tier, reason = _base_tier(task)
    tier, reason = _apply_signal_bumps(tier, task, reason)

    model, effort = TIER_ROUTE[tier]
    if task.is_agentic and model in AGENTIC_EFFORT_BUMP:
        effort = AGENTIC_EFFORT_BUMP[model]

    decision = RoutingDecision(
        model=model,
        effort=effort,
        tier=tier,
        source=RoutingSource.HEURISTIC,
        reason=reason,
    )
    if emit is not None:
        emit(build_event(task, decision))
    return decision
