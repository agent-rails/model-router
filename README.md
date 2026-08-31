# model-router

Cost-efficient model + effort routing for Claude API calls. Picks the cheapest model/effort tier that's fit for a task, with a hard override for security-critical work and an optional cascade-escalation path for when the cheap tier turns out wrong.

See `docs/DESIGN.md` for architecture and rationale, `docs/THREAT_MODEL.md` for known limitations and residual risk.

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

Always declare `category` at call sites that know their own task type — the heuristic fallback (no category given) is a safety net, not the primary mechanism. See `docs/DESIGN.md` § Trust boundary.

For persistent telemetry across runs, use `JsonlSink` instead of `InMemorySink`:

```python
from model_router import JsonlSink

sink = JsonlSink("~/.model_router/events.jsonl")
decision = classify(task, emit=sink)
```

See `examples/claude_code_subagents.py` for a worked example of mapping a specific caller's task types (this repo's Claude Code subagent roster) to router categories — that mapping is caller-side config, not part of the library.

## Run tests

```bash
python -m pytest -q
```
