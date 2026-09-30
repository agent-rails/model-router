from datetime import date

from model_router import LocalQualification, Runtime, TaskRequest, plan_task

QUALIFICATION = LocalQualification(
    model="test:small",
    digest="sha256:tested",
    categories=frozenset({"classification"}),
    evidence_ref="eval/run-42",
    valid_until=date(2026, 10, 30),
    max_prompt_chars=1000,
    p95_latency_ms=800,
)


def test_qualified_local_candidate_is_selected():
    plan = plan_task(
        TaskRequest(prompt="tag this", category="classification"),
        local=QUALIFICATION,
        installed_digest="sha256:tested",
        max_latency_ms=1000,
        today=date(2026, 9, 30),
    )
    assert plan.runtime == Runtime.OLLAMA
    assert plan.qualification_ref == "eval/run-42"
    assert not plan.rejections


def test_local_selection_fails_closed_on_digest_age_and_quality_scope():
    base = TaskRequest(prompt="tag this", category="classification")
    for task, digest, today in (
        (base, "sha256:other", date(2026, 9, 30)),
        (base, "sha256:tested", date(2026, 11, 1)),
        (TaskRequest(prompt="review auth", category="auth"), "sha256:tested", date(2026, 9, 30)),
        (
            TaskRequest(prompt="tag this", category="classification", tool_schema_count=1),
            "sha256:tested",
            date(2026, 9, 30),
        ),
        (
            TaskRequest(prompt="tag this", category="classification", is_agentic=True),
            "sha256:tested",
            date(2026, 9, 30),
        ),
    ):
        plan = plan_task(task, local=QUALIFICATION, installed_digest=digest, today=today)
        assert plan.runtime == Runtime.CODEX
        assert plan.rejections


def test_local_slow_or_missing_evidence_does_not_consume_task():
    task = TaskRequest(prompt="tag this", category="classification")
    assert (
        plan_task(
            task, local=QUALIFICATION, installed_digest="sha256:tested", max_latency_ms=500, today=date(2026, 9, 30)
        ).runtime
        == Runtime.CODEX
    )
    assert plan_task(task, local=QUALIFICATION, today=date(2026, 9, 30)).runtime == Runtime.CODEX
