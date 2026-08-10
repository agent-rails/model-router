from claude_code_subagents import task_for_subagent

from model_router import Model, RoutingSource, classify


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
