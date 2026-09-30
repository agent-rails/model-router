# model-router

Task tier and effort recommendations for Claude API calls and Codex dispatches. Security-sensitive work has a stronger floor. Callers own execution and verification.

**Status: experimental.** The rules are tested, but no accepted-task quality or
cost comparison has shown that they save money. This package does not change
the model in an active chat. The caller owns the provider adapter, permissions,
project knowledge, and validation.

See `docs/DESIGN.md` for architecture and rationale, `docs/THREAT_MODEL.md` for known limitations and residual risk.
See `docs/CODEX_ROUTING.md` for the Codex/local policy and its qualification gate.

## Install

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Usage

```python
from model_router import TaskRequest, classify, route_with_cascade, InMemorySink

decision = classify(TaskRequest(prompt="classify this ticket", category="classification"))
# decision.model == Model.HAIKU, decision.effort == Effort.LOW

sink = InMemorySink()
result = route_with_cascade(
    TaskRequest(prompt="summarize this doc", category="summarization"),
    call_fn=lambda model, effort, prompt: call_claude(model, effort, prompt),
    validate_fn=lambda response: response_is_well_formed(response),
    emit=sink,
)
result.response
result.final_decision.model
result.escalations
```

To resolve a decision through an OpenAI-compatible gateway such as LiteLLM,
keep deployment aliases in caller configuration and map only tiers that have
passed that caller's evals:

```python
from model_router import TaskTier, gateway_alias

alias = gateway_alias(
    decision,
    {TaskTier.TRIVIAL: "ollama-default"},
)
```

Missing and blank mappings fail closed. The library does not assume that a
particular local or hosted deployment satisfies a quality tier.

Call sites that know their task type should still declare `category`. For a free-text
task at the CLI boundary, `infer_task(prompt)` uses conservative, zero-token rules:
clear bounded transformations may use Luna, unknown intent defaults to Sol/medium,
and security-sensitive instructions route to Sol/high. Inferred metadata is marked
untrusted. This is task-start routing, not a learned classifier or a measured
quality improvement. See `docs/DESIGN.md` § Trust boundary.

For persistent telemetry across runs, use `JsonlSink` instead of `InMemorySink`:

```python
from model_router import JsonlSink

sink = JsonlSink("~/.model_router/events.jsonl")
decision = classify(task, emit=sink)
```

See `examples/claude_code_subagents.py` for a worked example of mapping a specific caller's task types (this repo's Claude Code subagent roster) to router categories — that mapping is caller-side config, not part of the library.

## Codex and local inference

```python
from model_router import infer_task, plan_task

task = infer_task("Fix this small test").request
plan = plan_task(task)
# codex / gpt-6-sol / medium / implement_verify
```

`plan_codex()` recommends Luna/high for narrow non-code tasks, Sol/medium for
ordinary work, and Sol/high for complex or security-sensitive work. It recommends
a workflow. AI-system tags remain available to callers, which map them to their
own project knowledge. Delegation is suggested only when the caller declares
multiple independent workstreams. These
are task-start recommendations, not mid-turn control of an active Codex session.

`plan_task()` may select Ollama only when the caller supplies a current
`LocalQualification` for the exact installed model digest, task category, and
measured latency. By default there is no qualified local candidate. The prior
`llama3.1:8b` tool-use evaluation failed a no-tool-needed case, so its presence on
the host is not qualification. Security, agentic, tool-using, and structured-output
tasks stay with Codex in this initial policy. The caller must check the installed
digest at dispatch and re-evaluate after model or policy changes.

The sibling provider-router has `examples/smart_dispatch.py`, a dry-run CLI that
turns this plan into explicit Codex model/effort settings or a qualified local
request. See its README for invocation and qualification record format.

## Run tests

```bash
python -m pytest -q
```
