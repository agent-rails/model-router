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
    assert task.category == "coding_simple"


def test_security_subagent_forces_opus_override():
    task = task_for_subagent("worf", "review this diff for auth bypass")
    decision = classify(task)
    assert decision.model == Model.OPUS
    assert decision.source == RoutingSource.OVERRIDE


def test_bounty_researcher_forces_opus_override():
    decision = classify(task_for_subagent("bounty-researcher", "reproduce this candidate locally"))
    assert decision.model == Model.OPUS
    assert decision.source == RoutingSource.OVERRIDE


def test_web_fetch_maps_to_extraction():
    assert task_for_subagent("web-fetch", "summarise this page").category == "extraction"


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


def test_a_recognised_category_in_mixed_case_is_not_reported_as_unrecognised():
    # classify normalises before the CATEGORY_TIER lookup, so a summary testing raw
    # membership flags correctly-mapped callers as mapping bugs -- and does it in the
    # direction that manufactures work. The library owns the recognition rule;
    # re-implementing it here is what drifted.
    sink = InMemorySink()
    decision_for_subagent("implementer", "add a field", category="Coding_Simple", emit=sink)
    summary = calibration_summary([event_to_json(e) for e in sink.events])

    assert summary["unrecognized_category_share"] == 0.0


def test_a_slice_of_only_escalations_declines_to_report_shares():
    # Reachable on a bounded tail of a growing log, or a filter down to escalations.
    # The empty-log case states the principle; this is the same hazard reintroduced
    # by counting dispatches instead of events.
    sink = InMemorySink()
    route_with_cascade(
        task_for_subagent("unmapped-agent", "do a thing"),
        call_fn=lambda model, effort, prompt: "unusable",
        validate_fn=lambda response: False,
        emit=sink,
    )
    escalations_only = [event_to_json(e) for e in sink.events if e.decision.source == RoutingSource.ESCALATED]
    summary = calibration_summary(escalations_only)

    assert summary["dispatches"] == 0
    assert "fallback_share" not in summary


def test_complex_instruction_raises_implementer_to_opus():
    task = task_for_subagent("implementer", "refactor the session store across services")
    assert task.category == "coding_complex"
    assert classify(task).model == Model.OPUS


def test_investigation_instruction_raises_general_purpose():
    assert task_for_subagent("general-purpose", "debug why the CI job is failing").category == "debugging_hard"


def test_inference_never_lowers_the_agent_default():
    assert task_for_subagent("general-purpose", "extract the title from this page").category == "chat"
    assert task_for_subagent("architect", "summarise this design").category == "architecture"


def test_unmapped_agent_can_be_raised_from_the_moderate_default():
    assert task_for_subagent("some-future-agent", "design the queue topology").category == "architecture"


def test_caller_category_disables_inference():
    assert task_for_subagent("implementer", "refactor everything", category="coding_simple").category == "coding_simple"


def test_non_complex_inference_does_not_raise():
    assert task_for_subagent("web-fetch", "summarise this page").category == "extraction"
    assert task_for_subagent("voltage-scribe", "add today's triage to the log").category == "summarization"


def test_risk_word_never_lowers_implementer_below_opus():
    for prompt in (
        "refactor the authentication module across services",
        "fix the authentication bypass in the login hook",
        "add secret redaction to the credentials loader",
    ):
        assert classify(task_for_subagent("implementer", prompt)).model == Model.OPUS, prompt


def test_risk_inference_is_untrusted_but_routes_opus():
    decision = classify(task_for_subagent("general-purpose", "rotate the credentials for the staging db"))
    assert decision.model == Model.OPUS
    assert decision.source == RoutingSource.KEYWORD_FLAGGED


def test_security_agent_keeps_trusted_override_source_with_risk_words():
    decision = classify(task_for_subagent("spock", "review the auth change"))
    assert decision.source == RoutingSource.OVERRIDE
