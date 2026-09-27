from __future__ import annotations

from collections import Counter
from pathlib import Path

from model_router import JsonlSink, RoutingDecision, TaskRequest, classify
from model_router.config import CATEGORY_TIER
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

    Reports shares, not a verdict. It deliberately does not say whether a route
    was *correct*: nothing here observes the outcome of a call, so a correctness
    claim would be invented rather than measured. For the same reason it reports
    how often the keyword path fires, not whether those flags were warranted --
    that answer needs something about the task that nothing in this repo sees.
    A low flag rate makes the false-positive question moot; it does not answer it.

    fallback_share is the load-bearing number: the fraction of dispatches that
    reached the heuristic with no caller-declared category, which is a lower
    bound on the traffic a learned or model-backed classifier could improve. If
    it is small, that work has little headroom regardless of how good the
    classifier is.

    It is a lower bound, not the figure, for two reasons. Override-routed
    dispatches are excluded: they also carry no category -- sentinel, spock and
    worf are tagged rather than categorised -- but were decided deterministically,
    and counting them would overstate the headroom by the share of security
    reviews. And a category that was declared but is absent from CATEGORY_TIER is
    reported separately, because it routes to the same MODERATE default on no
    usable signal but has a different fix: correct the caller's mapping, not add
    a classifier.

    Shares are per dispatch, not per event. route_with_cascade re-emits through
    the same sink on every escalation, so a dispatch that escalated contributes
    two or more events; counting events deflated every share by the escalation
    rate, biasing fallback_share toward "no headroom" -- the wrong direction for
    a build-or-not decision.

    escalations_per_dispatch is a rate, not a fraction of dispatches. With
    max_escalations > 1 one dispatch can emit several escalated events, and the
    log carries no dispatch identity to join them back, so the fraction of
    dispatches that escalated is not recoverable from this data.
    """
    total = len(events)
    if total == 0:
        return {"total": 0}

    sources: Counter[str] = Counter(e["decision"]["source"] for e in events)
    tiers: Counter[str] = Counter(e["decision"]["tier"] for e in events)
    models: Counter[str] = Counter(e["decision"]["model"] for e in events)

    # An escalation is a re-emit for a dispatch already counted, so event count
    # is not dispatch count. Dividing by events deflates every share by the
    # escalation rate.
    escalations = sources.get("escalated", 0)
    dispatches = total - escalations

    heuristic = [e for e in events if e["decision"]["source"] == "heuristic"]
    improvable = sum(1 for e in heuristic if e["category"] is None)
    unrecognized = sum(1 for e in heuristic if e["category"] is not None and e["category"] not in CATEGORY_TIER)

    return {
        "total": total,
        "dispatches": dispatches,
        "fallback_share": improvable / dispatches,
        "unrecognized_category_share": unrecognized / dispatches,
        "sources": dict(sources),
        "tiers": dict(tiers),
        "models": dict(models),
        "keyword_flagged_share": sources.get("keyword_flagged", 0) / dispatches,
        "escalations_per_dispatch": escalations / dispatches,
    }
