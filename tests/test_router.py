from model_router import Effort, Model, RoutingSource, TaskRequest, TaskTier, classify


def test_known_category_maps_to_trivial_tier():
    decision = classify(TaskRequest(prompt="tag this ticket", category="classification"))
    assert decision.model == Model.HAIKU
    assert decision.tier == TaskTier.TRIVIAL
    assert decision.source == RoutingSource.HEURISTIC


def test_known_category_maps_to_moderate_tier():
    decision = classify(TaskRequest(prompt="summarize this doc", category="summarization"))
    assert decision.model == Model.SONNET
    assert decision.tier == TaskTier.MODERATE


def test_known_category_maps_to_complex_tier():
    decision = classify(TaskRequest(prompt="refactor this service", category="architecture"))
    assert decision.model == Model.OPUS
    assert decision.tier == TaskTier.COMPLEX


def test_unknown_category_defaults_to_moderate():
    decision = classify(TaskRequest(prompt="do something unusual"))
    assert decision.tier == TaskTier.MODERATE
    assert decision.model == Model.SONNET


def test_category_override_forces_opus_with_trusted_source():
    decision = classify(TaskRequest(prompt="rotate this", category="agent_guard"))
    assert decision.model == Model.OPUS
    assert decision.source == RoutingSource.OVERRIDE


def test_tag_override_forces_opus():
    decision = classify(TaskRequest(prompt="do the thing", tags=frozenset({"warrant"})))
    assert decision.model == Model.OPUS
    assert decision.source == RoutingSource.OVERRIDE


def test_keyword_hit_routes_safe_but_is_distinguishable_from_trusted_override():
    decision = classify(TaskRequest(prompt="prepare a production deploy plan"))
    assert decision.model == Model.OPUS
    assert decision.source == RoutingSource.KEYWORD_FLAGGED
    assert decision.source != RoutingSource.OVERRIDE


def test_category_override_takes_priority_over_keyword_scan():
    decision = classify(TaskRequest(prompt="just chatting, nothing about that other thing", category="warrant"))
    assert decision.source == RoutingSource.OVERRIDE


def test_agentic_task_bumps_to_complex_tier():
    decision = classify(TaskRequest(prompt="run this multi-step plan", is_agentic=True))
    assert decision.tier == TaskTier.COMPLEX
    assert decision.model == Model.OPUS
    assert decision.effort == Effort.XHIGH


def test_many_tool_schemas_bumps_moderate_to_complex():
    decision = classify(TaskRequest(prompt="do a thing", category="chat", tool_schema_count=6))
    assert decision.tier == TaskTier.COMPLEX


def test_long_prompt_bumps_trivial_to_moderate():
    long_prompt = "x" * 5000
    decision = classify(TaskRequest(prompt=long_prompt, category="classification"))
    assert decision.tier == TaskTier.MODERATE


def test_very_long_prompt_bumps_moderate_to_complex():
    long_prompt = "x" * 9000
    decision = classify(TaskRequest(prompt=long_prompt, category="chat"))
    assert decision.tier == TaskTier.COMPLEX


def test_agentic_task_gets_xhigh_effort_after_tier_bump_to_opus():
    decision = classify(TaskRequest(prompt="do a thing", category="summarization", is_agentic=True))
    assert decision.model == Model.OPUS
    assert decision.effort == Effort.XHIGH


def test_category_override_is_case_insensitive():
    decision = classify(TaskRequest(prompt="rotate this", category="Auth"))
    assert decision.model == Model.OPUS
    assert decision.source == RoutingSource.OVERRIDE


def test_category_override_ignores_surrounding_whitespace():
    decision = classify(TaskRequest(prompt="rotate this", category=" agent_guard "))
    assert decision.model == Model.OPUS
    assert decision.source == RoutingSource.OVERRIDE


def test_tag_override_is_case_insensitive():
    decision = classify(TaskRequest(prompt="do the thing", tags=frozenset({"WARRANT"})))
    assert decision.model == Model.OPUS
    assert decision.source == RoutingSource.OVERRIDE


def test_category_tier_lookup_is_case_insensitive():
    decision = classify(TaskRequest(prompt="tag this ticket", category="Classification"))
    assert decision.tier == TaskTier.TRIVIAL
    assert decision.model == Model.HAIKU


def test_unrecognized_category_reason_differs_from_absent_category_reason():
    unrecognized = classify(TaskRequest(prompt="do something", category="not_a_real_category"))
    absent = classify(TaskRequest(prompt="do something"))
    assert unrecognized.reason != absent.reason
    assert "not_a_real_category" in unrecognized.reason
    assert "not recognized" in unrecognized.reason
    assert "no category supplied" in absent.reason


def test_keyword_scan_matches_hyphen_and_underscore_variants():
    hyphen = classify(TaskRequest(prompt="review this agent-guard change"))
    underscore = classify(TaskRequest(prompt="review this agent_guard change"))
    assert hyphen.source == RoutingSource.KEYWORD_FLAGGED
    assert underscore.source == RoutingSource.KEYWORD_FLAGGED


def test_keyword_scan_matches_underscore_variant_of_multiword_keyword():
    decision = classify(TaskRequest(prompt="need a fresh api_key for this integration"))
    assert decision.source == RoutingSource.KEYWORD_FLAGGED
