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
    decision = classify(
        TaskRequest(prompt="just chatting, nothing about that other thing", category="warrant")
    )
    assert decision.source == RoutingSource.OVERRIDE


def test_agentic_task_bumps_to_complex_tier():
    decision = classify(TaskRequest(prompt="run this multi-step plan", is_agentic=True))
    assert decision.tier == TaskTier.COMPLEX
    assert decision.model == Model.OPUS
    assert decision.effort == Effort.XHIGH


def test_many_tool_schemas_bumps_moderate_to_complex():
    decision = classify(
        TaskRequest(prompt="do a thing", category="chat", tool_schema_count=6)
    )
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
    decision = classify(
        TaskRequest(prompt="do a thing", category="summarization", is_agentic=True)
    )
    assert decision.model == Model.OPUS
    assert decision.effort == Effort.XHIGH
