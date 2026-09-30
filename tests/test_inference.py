import pytest

from model_router import CodexModel, RoutingSource, Workflow, infer_task, plan_codex


@pytest.mark.parametrize(
    ("prompt", "category", "model", "effort"),
    [
        ("Format this list as CSV", "formatting", CodexModel.LUNA, "high"),
        ("Classify these support tickets", "classification", CodexModel.LUNA, "high"),
        ("Fix the typo in the README", "coding_simple", CodexModel.SOL, "medium"),
        ("Design the model serving scheduler", "architecture", CodexModel.SOL, "high"),
        ("Build distributed job recovery", "coding_complex", CodexModel.SOL, "high"),
        ("Refactor this service's dependency injection", "coding_complex", CodexModel.SOL, "high"),
        ("Review this PR end to end", "code_review", CodexModel.SOL, "high"),
        ("Chat: help me draft a Slack message about a schedule change", "chat", CodexModel.SOL, "medium"),
        ("Summarize this postmortem", "summarization", CodexModel.SOL, "medium"),
        ("Review payment authentication", "security_review", CodexModel.SOL, "high"),
        ("Can you help with this?", None, CodexModel.SOL, "medium"),
    ],
)
def test_infer_safe_task_start(prompt, category, model, effort):
    inferred = infer_task(prompt)
    plan = plan_codex(inferred.request)
    assert inferred.request.category == category
    assert plan.model == model
    assert plan.effort.value == effort


def test_inferred_security_is_flagged_not_trusted_override():
    plan = plan_codex(infer_task("Review payment authentication").request)
    assert plan.source == RoutingSource.KEYWORD_FLAGGED
    assert plan.workflow == Workflow.INVESTIGATE_VERIFY


def test_full_prompt_still_triggers_existing_security_flag():
    plan = plan_codex(infer_task("Format this list\napi key: example").request)
    assert plan.model == CodexModel.SOL
    assert plan.source == RoutingSource.KEYWORD_FLAGGED


def test_ai_topic_is_available_to_caller_without_a_private_wiki_path():
    inferred = infer_task("Design an inference scheduler")
    assert "inference" in inferred.request.tags


def test_communication_task_uses_direct_workflow():
    plan = plan_codex(infer_task("Draft a status email to the team").request)
    assert plan.workflow == Workflow.DIRECT
