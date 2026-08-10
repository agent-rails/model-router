import pytest

from model_router import InMemorySink, Model, RoutingSource, TaskRequest, route_with_cascade


def test_no_escalation_when_validator_passes_first_try():
    task = TaskRequest(prompt="classify this", category="classification")
    calls = []

    def call_fn(model, effort, prompt):
        calls.append(model)
        return "ok"

    result = route_with_cascade(task, call_fn, validate_fn=lambda r: True)
    assert result.escalations == 0
    assert len(calls) == 1
    assert result.final_decision.model == Model.HAIKU


def test_no_escalation_when_no_validator_supplied():
    task = TaskRequest(prompt="classify this", category="classification")
    result = route_with_cascade(task, lambda model, effort, prompt: "whatever")
    assert result.escalations == 0
    assert result.response == "whatever"


def test_escalates_once_on_validation_failure_then_succeeds():
    task = TaskRequest(prompt="summarize this", category="summarization")
    outcomes = iter(["bad", "good"])
    models_called = []

    def call_fn(model, effort, prompt):
        models_called.append(model)
        return next(outcomes)

    result = route_with_cascade(task, call_fn, validate_fn=lambda r: r == "good")
    assert result.escalations == 1
    assert models_called == [Model.SONNET, Model.OPUS]
    assert result.final_decision.source == RoutingSource.ESCALATED


def test_respects_max_escalations_cap():
    task = TaskRequest(prompt="classify this", category="classification")
    models_called = []

    def call_fn(model, effort, prompt):
        models_called.append(model)
        return "always bad"

    result = route_with_cascade(task, call_fn, validate_fn=lambda r: False, max_escalations=2)
    assert result.escalations == 2
    assert models_called == [Model.HAIKU, Model.SONNET, Model.OPUS]


def test_no_infinite_loop_once_already_at_opus_ceiling():
    task = TaskRequest(prompt="rotate this", category="agent_guard")
    call_count = 0

    def call_fn(model, effort, prompt):
        nonlocal call_count
        call_count += 1
        return "still bad"

    result = route_with_cascade(task, call_fn, validate_fn=lambda r: False, max_escalations=5)
    assert call_count == 1
    assert result.escalations == 0
    assert result.final_decision.model == Model.OPUS


def test_max_escalations_zero_makes_exactly_one_call():
    task = TaskRequest(prompt="classify this", category="classification")
    call_count = 0

    def call_fn(model, effort, prompt):
        nonlocal call_count
        call_count += 1
        return "always bad"

    result = route_with_cascade(task, call_fn, validate_fn=lambda r: False, max_escalations=0)
    assert call_count == 1
    assert result.escalations == 0


def test_negative_max_escalations_makes_exactly_one_call():
    task = TaskRequest(prompt="classify this", category="classification")
    call_count = 0

    def call_fn(model, effort, prompt):
        nonlocal call_count
        call_count += 1
        return "always bad"

    result = route_with_cascade(task, call_fn, validate_fn=lambda r: False, max_escalations=-3)
    assert call_count == 1
    assert result.escalations == 0


def test_validate_fn_exception_propagates():
    task = TaskRequest(prompt="classify this", category="classification")

    def raising_validate(response):
        raise ValueError("bad response shape")

    with pytest.raises(ValueError, match="bad response shape"):
        route_with_cascade(task, lambda model, effort, prompt: "ok", validate_fn=raising_validate)


def test_call_fn_exception_propagates():
    task = TaskRequest(prompt="classify this", category="classification")

    def raising_call_fn(model, effort, prompt):
        raise RuntimeError("api unreachable")

    with pytest.raises(RuntimeError, match="api unreachable"):
        route_with_cascade(task, raising_call_fn)


def test_emits_telemetry_for_initial_and_escalated_decisions():
    task = TaskRequest(prompt="classify this", category="classification")
    outcomes = iter(["bad", "good"])
    sink = InMemorySink()

    result = route_with_cascade(
        task,
        lambda model, effort, prompt: next(outcomes),
        validate_fn=lambda r: r == "good",
        emit=sink,
    )
    assert len(sink.events) == 2
    assert len(sink.escalations()) == 1
    assert result.escalations == 1
