from __future__ import annotations

from collections import Counter
from pathlib import Path

from model_router import JsonlSink, RoutingDecision, TaskRequest, classify
from model_router.telemetry import EmitFn

SUBAGENT_CATEGORY: dict[str, str] = {
    "Explore": "data_analysis",
    "general-purpose": "chat",
    "claude": "chat",
    "implementer": "coding_complex",
    "debugger": "debugging_hard",
    "tester": "coding_simple",
    "researcher": "data_analysis",
    "architect": "architecture",
    "architect-reviewer": "code_review",
    "principal-architect": "architecture",
    "ai-architect": "architecture",
    "sentinel-fetcher": "extraction",
    "sentinel-scribe": "summarization",
    "scotty": "coding_complex",
    "senior-qa": "code_review",
    "context-manager": "summarization",
    "claude-code-guide": "simple_qa",
    "statusline-setup": "coding_simple",
    "voltage": "chat",
    "voltage-fetcher": "extraction",
    "voltage-reporter": "summarization",
    "voltage-scribe": "summarization",
    "Plan": "architecture",
    "orchestrator": "long_horizon_agentic",
    "caveman:cavecrew-investigator": "extraction",
    "caveman:cavecrew-builder": "coding_simple",
    "caveman:cavecrew-reviewer": "coding_simple",
}

SUBAGENT_OVERRIDE_TAGS: dict[str, frozenset[str]] = {
    "data": frozenset({"security_review"}),
    "sentinel": frozenset({"security_review"}),
    "spock": frozenset({"security_review"}),
    "worf": frozenset({"security_review"}),
}

SUBAGENT_IS_AGENTIC: frozenset[str] = frozenset({"orchestrator"})


def task_for_subagent(subagent_type: str, prompt: str, **overrides: object) -> TaskRequest:
    fields: dict[str, object] = {
        "prompt": prompt,
        "category": SUBAGENT_CATEGORY.get(subagent_type),
        "tags": SUBAGENT_OVERRIDE_TAGS.get(subagent_type, frozenset()),
        "is_agentic": subagent_type in SUBAGENT_IS_AGENTIC,
    }
    fields.update(overrides)
    return TaskRequest(**fields)


# Telemetry wiring for this caller.
#
# docs/DESIGN.md names the observability hook as the seam to revisit both
# deliberate omissions -- the absent ML classifier and the absent response-quality
# judge -- "once real traffic exists". Neither decision can be revisited without
# accumulated events, so the sink has to be on before either question is worth
# asking. This is caller-side config by the same rule that keeps
# SUBAGENT_CATEGORY out of model_router/: the path and the retention policy are
# this harness's business, not the library's.
EVENTS_PATH = "~/.model_router/claude_code_events.jsonl"


def subagent_sink(path: str | Path = EVENTS_PATH) -> JsonlSink:
    return JsonlSink(path)


def decision_for_subagent(
    subagent_type: str,
    prompt: str,
    emit: EmitFn | None = None,
    **overrides: object,
) -> RoutingDecision:
    """Classify a subagent dispatch and record it.

    Passing emit=None records nothing rather than defaulting to the shared sink:
    a helper that silently writes to a file in the caller's home directory is not
    something a test or a one-off script should have to opt out of.
    """
    return classify(task_for_subagent(subagent_type, prompt, **overrides), emit=emit)


def calibration_summary(events: list[dict]) -> dict[str, object]:
    """Answer the two questions docs/DESIGN.md says this hook exists to answer.

    Whether the heuristic thresholds are calibrated, and whether KEYWORD_FLAGGED
    is mostly false positives, are both questions about proportions rather than
    individual routes -- so this reports shares, not a verdict. It deliberately
    does not say whether a route was *correct*: nothing here observes the outcome
    of a call, so a correctness claim would be invented rather than measured.

    fallback_share is the load-bearing number: the fraction of traffic that
    reached the heuristic with no caller-declared category, which is the only
    traffic a learned or model-backed classifier could improve. If it is small,
    that work has no headroom regardless of how good the classifier is. It
    deliberately excludes override-routed dispatches, which also carry no
    category but were decided deterministically -- counting those would overstate
    the headroom by the share of security reviews.
    """
    total = len(events)
    if total == 0:
        return {"total": 0}

    # Only traffic that reached the heuristic *without* a declared category is
    # improvable by a classifier. An override-routed dispatch also carries no
    # category -- SUBAGENT_OVERRIDE_TAGS entries like sentinel are tagged rather
    # than categorised -- but it was decided deterministically, so counting it
    # here would overstate the headroom by the share of security reviews.
    improvable = sum(
        1
        for e in events
        if e.get("category") is None and e["decision"]["source"] == "heuristic"
    )
    sources: Counter[str] = Counter(e["decision"]["source"] for e in events)
    tiers: Counter[str] = Counter(e["decision"]["tier"] for e in events)
    models: Counter[str] = Counter(e["decision"]["model"] for e in events)

    return {
        "total": total,
        "fallback_share": improvable / total,
        "sources": dict(sources),
        "tiers": dict(tiers),
        "models": dict(models),
        "keyword_flagged_share": sources.get("keyword_flagged", 0) / total,
        "escalated_share": sources.get("escalated", 0) / total,
    }
