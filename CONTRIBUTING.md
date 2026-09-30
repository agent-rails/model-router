# Contributing

## What this project has

- `model_router/inference.py` — conservative task-start category inference when the caller has no declared category.
- `model_router/router.py` — category-to-tier routing: hard override → heuristic tier → signal bumps.
- `model_router/cascade.py` — optional cheap-first/retry-on-failure escalation: `route_with_cascade(...)`.
- `model_router/telemetry.py` + `model_router/sinks.py` — observability hook (`RoutingEvent`, `InMemorySink`, `JsonlSink`) so routing decisions are auditable.
- `model_router/config.py` — the tunable surface: `OVERRIDE_CATEGORIES`, `OVERRIDE_KEYWORDS`, `CATEGORY_TIER`, `TIER_ROUTE`, `ESCALATION_PATH`. Most contributions that change routing *behavior* rather than *code* live here.
- `examples/pilot.py` — runs a representative task set through the router and prints a routing table + rough cost estimate.
- `examples/claude_code_subagents.py` — a worked example of mapping one caller's task types to router categories. Pattern to copy for your own integration, not something to extend in place.
- `docs/DESIGN.md` — architecture and the rationale for every non-obvious choice, including what was deliberately *not* built and why.
- `docs/THREAT_MODEL.md` — known limitations and residual risk. Read this before changing anything in the override path.

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Before opening a PR

```bash
ruff format .
ruff check .
python -m pytest -q
```

All three must be clean. New behavior needs a regression test — a happy-path test alone doesn't cover a routing-decision change.

## The one rule that matters most

Read `docs/DESIGN.md` § Trust boundary before touching `_override_reason` or `OVERRIDE_CATEGORIES`/`OVERRIDE_KEYWORDS`. Caller-declared `category`/`tag` is the trusted path (`RoutingSource.OVERRIDE`). Inferred metadata and prompt-text keyword matching are untrusted (`RoutingSource.KEYWORD_FLAGGED` for security matches) and must never be promoted to equal authority with the trusted path — see `docs/THREAT_MODEL.md` § 1–2 for why that distinction exists and what it costs.
