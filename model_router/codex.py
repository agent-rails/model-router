"""Codex dispatch advice. The caller remains responsible for executing and verifying work."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from model_router.config import LONG_PROMPT_CHAR_THRESHOLD, MANY_TOOLS_THRESHOLD
from model_router.models import Effort
from model_router.router import _base_tier, _override_reason
from model_router.types import RoutingSource, TaskRequest, TaskTier


class CodexModel(StrEnum):
    LUNA = "gpt-6-luna"
    SOL = "gpt-6-sol"


class Workflow(StrEnum):
    DIRECT = "direct"
    IMPLEMENT_VERIFY = "implement_verify"
    INVESTIGATE_VERIFY = "investigate_verify"
    RESEARCH_DESIGN = "research_design"


@dataclass(frozen=True, slots=True)
class CodexPlan:
    model: CodexModel
    effort: Effort
    tier: TaskTier
    source: RoutingSource
    workflow: Workflow
    workflow_steps: tuple[str, ...]
    suggest_delegation: bool
    context_files: tuple[str, ...]
    reason: str


_AI_TAGS = frozenset({"ai_systems", "llm", "inference", "orchestration", "routing", "distributed_ai"})
_RESEARCH_CATEGORIES = frozenset({"architecture", "research", "design"})
_INVESTIGATE_CATEGORIES = frozenset({"debugging_hard", "code_review", "security_review"})
_WORKFLOW_STEPS: dict[Workflow, tuple[str, ...]] = {
    Workflow.DIRECT: ("complete the bounded task", "check the requested output"),
    Workflow.IMPLEMENT_VERIFY: ("inspect relevant files", "make a scoped change", "run relevant checks"),
    Workflow.INVESTIGATE_VERIFY: ("gather evidence", "reproduce or test", "report findings and limits"),
    Workflow.RESEARCH_DESIGN: (
        "read relevant wiki pages and current primary sources",
        "explain mechanisms and failure domains",
        "propose a small design and evaluation",
    ),
}


def _workflow(category: str | None, tier: TaskTier) -> Workflow:
    normalized = (category or "").strip().casefold()
    if normalized in _RESEARCH_CATEGORIES:
        return Workflow.RESEARCH_DESIGN
    if normalized in _INVESTIGATE_CATEGORIES:
        return Workflow.INVESTIGATE_VERIFY
    if tier == TaskTier.TRIVIAL and normalized not in {"coding_simple", "coding_complex"}:
        return Workflow.DIRECT
    return Workflow.IMPLEMENT_VERIFY


def _context_files(task: TaskRequest) -> tuple[str, ...]:
    tags = {tag.strip().casefold() for tag in task.tags}
    category = (task.category or "").strip().casefold()
    if not tags.intersection(_AI_TAGS) and category not in {"inference", "orchestration", "routing", "distributed_ai"}:
        return ()
    files = ["~/wiki/index.md", "~/wiki/foundations/ai-systems-foundations.md"]
    topic = next(
        (
            name
            for name in ("inference", "orchestration", "routing", "distributed_ai")
            if name in tags or name == category
        ),
        None,
    )
    relevant = {
        "inference": "~/wiki/foundations/inference-memory-and-compute.md",
        "orchestration": "~/wiki/foundations/orchestration-state-and-memory.md",
        "routing": "~/wiki/queries/llm-routing-gateway-handoff.md",
        "distributed_ai": "~/wiki/foundations/distributed-ai-systems.md",
    }
    if topic is not None:
        files.append(relevant[topic])
    return tuple(files)


def plan_codex(task: TaskRequest) -> CodexPlan:
    """Recommend a Codex model and a bounded workflow for one dispatch.

    A plan is advisory; explicit caller pins, access controls, and actual model
    availability are resolved by the caller. This does not change a running turn.
    """
    if task.independent_workstreams < 1:
        raise ValueError("independent_workstreams must be at least 1")

    override = _override_reason(task)
    if override is not None:
        reason, source = override
        tier = TaskTier.COMPLEX
    else:
        tier, reason = _base_tier(task)
        source = RoutingSource.HEURISTIC
        if task.tool_schema_count >= MANY_TOOLS_THRESHOLD and tier != TaskTier.COMPLEX:
            tier = TaskTier.COMPLEX
            reason += "; many tools"
        if tier == TaskTier.TRIVIAL and len(task.prompt) > LONG_PROMPT_CHAR_THRESHOLD:
            tier = TaskTier.MODERATE
            reason += "; long prompt"
        elif tier == TaskTier.MODERATE and len(task.prompt) > LONG_PROMPT_CHAR_THRESHOLD * 2:
            tier = TaskTier.COMPLEX
            reason += "; very long prompt"

    # Agentic is a workflow signal, not proof that every step needs the largest tier.
    model, effort = (
        (CodexModel.LUNA, Effort.HIGH)
        if tier == TaskTier.TRIVIAL
        else (CodexModel.SOL, Effort.MEDIUM)
        if tier == TaskTier.MODERATE
        else (CodexModel.SOL, Effort.HIGH)
    )
    workflow = _workflow(task.category, tier)
    return CodexPlan(
        model=model,
        effort=effort,
        tier=tier,
        source=source,
        workflow=workflow,
        workflow_steps=_WORKFLOW_STEPS[workflow],
        suggest_delegation=task.independent_workstreams >= 2 and tier != TaskTier.TRIVIAL,
        context_files=_context_files(task),
        reason=reason,
    )
