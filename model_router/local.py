"""Qualification-gated local inference selection."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from enum import StrEnum

from model_router.codex import CodexPlan, plan_codex
from model_router.types import RoutingSource, TaskRequest, TaskTier


class Runtime(StrEnum):
    CODEX = "codex"
    OLLAMA = "ollama"


@dataclass(frozen=True, slots=True)
class LocalQualification:
    """Operator-supplied evidence for one immutable local model artifact.

    This is an allowlist, not a model capability inferred from its name.
    """

    model: str
    digest: str
    categories: frozenset[str]
    evidence_ref: str
    valid_until: date
    max_prompt_chars: int
    p95_latency_ms: int


@dataclass(frozen=True, slots=True)
class TaskPlan:
    runtime: Runtime
    model: str
    effort: str | None
    codex: CodexPlan
    qualification_ref: str | None
    rejections: tuple[str, ...]
    reason: str


def plan_task(
    task: TaskRequest,
    *,
    local: LocalQualification | None = None,
    installed_digest: str | None = None,
    max_latency_ms: int | None = None,
    today: date | None = None,
) -> TaskPlan:
    """Choose a qualified local model or return the Codex plan.

    The caller must check the installed Ollama digest at dispatch time. Unmeasured,
    stale, uninstalled, slow, or high-impact candidates fail closed to Codex.
    """
    codex = plan_codex(task)
    fallback = TaskPlan(Runtime.CODEX, codex.model.value, codex.effort.value, codex, None, (), codex.reason)
    if local is None:
        return fallback
    category = (task.category or "").strip().casefold()
    rejections: list[str] = []
    if codex.tier != TaskTier.TRIVIAL or codex.source != RoutingSource.HEURISTIC:
        rejections.append("task tier or override is not eligible for local inference")
    if (
        task.is_agentic
        or task.tool_schema_count > 0
        or task.requires_structured_output
        or task.independent_workstreams > 1
    ):
        rejections.append("task requires unqualified agent, tool, structured-output, or multi-workstream capability")
    if category not in {name.strip().casefold() for name in local.categories}:
        rejections.append("category is not qualified")
    if not local.digest.strip() or installed_digest != local.digest:
        rejections.append("installed model digest is missing or different")
    if local.valid_until < (today or datetime.now(UTC).date()) or not local.evidence_ref.strip():
        rejections.append("qualification evidence is expired or missing")
    if not local.model.strip() or local.max_prompt_chars <= 0 or len(task.prompt) > local.max_prompt_chars:
        rejections.append("model or evaluated prompt-size bound is invalid")
    if local.p95_latency_ms <= 0 or (max_latency_ms is not None and local.p95_latency_ms > max_latency_ms):
        rejections.append("measured latency exceeds the task bound")
    if rejections:
        return TaskPlan(
            fallback.runtime, fallback.model, fallback.effort, codex, None, tuple(rejections), fallback.reason
        )
    return TaskPlan(
        Runtime.OLLAMA,
        local.model,
        None,
        codex,
        local.evidence_ref,
        (),
        f"qualified local model for category '{category}' at digest {local.digest}",
    )
