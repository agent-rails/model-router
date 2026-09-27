from claude_code_subagents import (
    calibration_summary,
    decision_for_subagent,
    task_for_subagent,
)

from model_router import (
    InMemorySink,
    Model,
    RoutingSource,
    classify,
    route_with_cascade,
)
from model_router.sinks import event_to_json


def test_known_subagent_maps_to_expected_category():
    task = task_for_subagent("implementer", "add a retry loop to this client")
    assert task.category == "coding_complex"


def test_security_subagent_forces_opus_override():
    task = task_for_subagent("worf", "review this diff for auth bypass")
    decision = classify(task)
    assert decision.model == Model.OPUS
    assert decision.source == RoutingSource.OVERRIDE


def test_unknown_subagent_falls_back_to_no_category():
    task = task_for_subagent("some-future-agent", "do a thing")
    assert task.category is None
    decision = classify(task)
    assert "no category supplied" in decision.reason


def test_orchestrator_is_marked_agentic():
    task = task_for_subagent("orchestrator", "coordinate this multi-step build")
    assert task.is_agentic is True


def test_caller_overrides_win_over_defaults():
    task = task_for_subagent("Explore", "quick lookup", category="simple_qa")
    assert task.category == "simple_qa"


def test_decision_for_subagent_passes_no_sink_by_default(monkeypatch):
    # A helper that silently appends to a file in the caller's home directory is
    # not something a test should have to opt out of, so emit=None is the default.
    # Asserting on a sink that was never passed would pass no matter what the
    # helper did with emit, so this spies on the seam instead.
    seen: list[object] = []

    def spy(task, emit=None):
        seen.append(emit)
        return classify(task)

    monkeypatch.setattr("claude_code_subagents.classify", spy)
    decision_for_subagent("implementer", "add a retry loop")
    assert seen == [None]


def test_decision_for_subagent_records_through_a_supplied_sink():
    sink = InMemorySink()
    decision_for_subagent("implementer", "add a retry loop", emit=sink)
    assert len(sink.events) == 1


def test_shares_are_per_dispatch_not_per_event():
    # route_with_cascade re-emits through the same sink on every escalation, so a
    # dispatch that escalated contributes two events. Counting events deflated
    # every share by the escalation rate -- biasing fallback_share toward "no
    # headroom", the wrong direction for a build-or-not decision.
    sink = InMemorySink()
    route_with_cascade(
        task_for_subagent("unmapped-agent", "do a thing"),
        call_fn=lambda model, effort, prompt: "unusable",
        validate_fn=lambda response: False,
        emit=sink,
    )
    summary = calibration_summary([event_to_json(e) for e in sink.events])

    assert summary["total"] == 2
    assert summary["dispatches"] == 1
    assert summary["fallback_share"] == 1.0
    assert summary["escalations_per_dispatch"] == 1.0


def test_a_declared_but_unrecognised_category_is_reported_separately():
    # It routes to the same MODERATE default on no usable signal, but the fix is
    # to correct the caller's mapping, not to add a classifier -- so folding it
    # into fallback_share would point the reader at the wrong work.
    sink = InMemorySink()
    decision_for_subagent("implementer", "add a field", category="frobnicate", emit=sink)
    summary = calibration_summary([event_to_json(e) for e in sink.events])

    assert summary["unrecognized_category_share"] == 1.0
    assert summary["fallback_share"] == 0.0


def test_fallback_share_counts_only_traffic_a_classifier_could_improve():
    # sentinel carries no category -- it is tagged, not categorised -- but it
    # routes by override, deterministically. Counting it as fallback would
    # overstate the headroom for a classifier by the share of security reviews.
    sink = InMemorySink()
    decision_for_subagent("sentinel", "review this diff", emit=sink)
    decision_for_subagent("implementer", "add a field", emit=sink)
    decision_for_subagent("unmapped-agent", "do a thing", emit=sink)

    summary = calibration_summary([event_to_json(e) for e in sink.events])

    assert summary["total"] == 3
    assert summary["sources"]["override"] == 1
    # Only the unmapped agent reached the heuristic with nothing declared.
    assert summary["fallback_share"] == 1 / 3


def test_calibration_summary_reports_no_shares_for_an_empty_log():
    # Dividing by zero to report a share of nothing would be worse than
    # declining to answer, so the empty case returns the count alone.
    assert calibration_summary([]) == {"total": 0}
