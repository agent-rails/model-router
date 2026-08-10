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

Always declare `category` at call sites that know their own task type — the heuristic fallback (no category given) is a safety net, not the primary mechanism. See `docs/DESIGN.md` § Trust boundary.

## Run tests

```bash
python -m pytest -q
```
