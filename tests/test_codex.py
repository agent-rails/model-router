import pytest

from model_router import CodexModel, Effort, RoutingSource, TaskRequest, TaskTier, Workflow, plan_codex


def test_narrow_work_routes_to_luna_with_direct_workflow():
    plan = plan_codex(TaskRequest(prompt="format this list", category="formatting", is_agentic=True))
    assert (plan.model, plan.effort, plan.workflow) == (CodexModel.LUNA, Effort.HIGH, Workflow.DIRECT)
    assert not plan.suggest_delegation


def test_ordinary_code_routes_to_sol_and_verification():
    plan = plan_codex(TaskRequest(prompt="fix the typo", category="coding_simple"))
    assert (plan.model, plan.effort, plan.workflow) == (CodexModel.SOL, Effort.MEDIUM, Workflow.IMPLEMENT_VERIFY)
    assert plan.workflow_steps[-1] == "run relevant checks"


def test_security_override_keeps_strong_floor_and_provenance():
    plan = plan_codex(TaskRequest(prompt="review this change", category="security_review"))
    assert (plan.model, plan.effort, plan.tier) == (CodexModel.SOL, Effort.HIGH, TaskTier.COMPLEX)
    assert plan.source == RoutingSource.OVERRIDE
    assert plan.workflow == Workflow.INVESTIGATE_VERIFY


def test_keyword_flag_is_not_presented_as_trusted_category():
    plan = plan_codex(TaskRequest(prompt="check the production deployment"))
    assert plan.source == RoutingSource.KEYWORD_FLAGGED
    assert plan.model == CodexModel.SOL


def test_delegation_requires_explicit_workstreams():
    plan = plan_codex(
        TaskRequest(
            prompt="design the serving path",
            category="architecture",
            tags=frozenset({"inference"}),
            independent_workstreams=2,
        )
    )
    assert plan.workflow == Workflow.RESEARCH_DESIGN
    assert plan.suggest_delegation


def test_unrecognized_task_defaults_to_sol_medium():
    plan = plan_codex(TaskRequest(prompt="something new"))
    assert (plan.model, plan.effort) == (CodexModel.SOL, Effort.MEDIUM)


def test_research_category_gets_design_workflow_and_complex_effort():
    plan = plan_codex(TaskRequest(prompt="investigate serving tradeoffs", category="research"))
    assert (plan.model, plan.effort, plan.workflow) == (CodexModel.SOL, Effort.HIGH, Workflow.RESEARCH_DESIGN)


def test_invalid_workstream_count_is_rejected():
    with pytest.raises(ValueError, match="independent_workstreams"):
        plan_codex(TaskRequest(prompt="x", independent_workstreams=0))
