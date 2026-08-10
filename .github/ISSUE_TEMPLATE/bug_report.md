---
name: Bug report
about: Something routed wrong, or the library behaved unexpectedly
labels: bug
---

## What happened

## What you expected

## Minimal repro

```python
from model_router import TaskRequest, classify

decision = classify(TaskRequest(prompt="...", category="..."))
```

## If this is a misrouting (wrong model/effort/override)

- `decision.tier`, `decision.model`, `decision.effort`, `decision.source`, `decision.reason`:
- Was `category` set? To what?
- Was this expected to hit the hard override (`docs/DESIGN.md` § Trust boundary)?
