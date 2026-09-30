# Design

## Problem

Every Claude API call site picks a model (Haiku/Sonnet/Opus) and an effort level by hand, or defaults to whatever the last call site used. That either overpays (Opus for classification) or underpays (Haiku for security review). Need a router that picks both axes — model tier and effort — cheaply, with a hard floor for work where getting it wrong is expensive in ways that aren't just cost.

## Three-stage pipeline

```
TaskRequest -> [1: hard override] -> [2: heuristic tier] -> RoutingDecision
                                                            -> [3: cascade escalation] (optional, caller opts in)
```

### Stage 1 — hard override

Checked first, short-circuits everything below it. Two paths, deliberately **not equal in trust**:

- **Category or tag override** (`RoutingSource.OVERRIDE`) — caller explicitly declared the task belongs to a security-critical category (`agent_guard`, `warrant`, `auth`, `production_infra`, etc.). This is a trusted signal: it's a string literal in code, reviewed like any other code, not inferred from free text.
- **Keyword-in-prompt override** (`RoutingSource.KEYWORD_FLAGGED`) — no category declared, but the raw prompt text contains a flagged substring ("production", "agent-guard", "irreversible", ...). This is an *un*trusted signal — substring matching on free text is trivially evadable by paraphrase and just as trivially over-triggers on unrelated text. It still routes to Opus/high (fail-safe: a false positive here just spends more than needed, a false negative silently under-routes a sensitive task) — but it's tagged with a distinct `RoutingSource` specifically so it's auditable and distinguishable from the trusted path. See `THREAT_MODEL.md`.

Both land at the same model/effort (Opus, high or xhigh if agentic) — the distinction is provenance, not behavior. That's intentional: this is a v1 fail-safe default, not a claim that keyword scanning is a sound security boundary on its own.

### Stage 2 — heuristic tier

If no override fired: look up `category` in a flat `CATEGORY_TIER` dict (trivial/moderate/complex → haiku/sonnet/opus). No category → default to `moderate` (Sonnet), not `trivial` — an unknown task gets the safe middle, not the cheap floor.

Signal-based bumps apply on top of the base tier: agentic tasks always bump to `complex`; high tool-schema counts bump `moderate`→`complex`; long prompts bump one tier up. These are cheap, deterministic, and legible — no scoring model, no training data required.

Agentic tasks at Sonnet or Opus get `effort: xhigh` instead of the tier default — matches the model-migration guidance that `xhigh` is the recommended effort for coding/agentic work on current-generation models.

### Stage 3 — cascade escalation (opt-in)

Caller supplies `call_fn` (executes the actual API call) and optionally `validate_fn` (checks whether the response is acceptable). If `validate_fn` rejects the response, the router escalates one tier (Haiku→Sonnet→Opus) and retries, up to `max_escalations`. No escalation happens without a caller-supplied validator — the router will not silently retry on its own opinion of quality.

This is the efficiency lever: try cheap first, pay for the expensive retry only when the cheap attempt actually failed, rather than always paying for the safe tier "just in case."

## Trust boundary

The one thing that should never be true of this router: a heuristic guess quietly overriding an explicit caller decision. A caller-declared category wins at the CLI. `infer_task()` can supply a category only when the caller has none, and marks it untrusted so security matches keep `KEYWORD_FLAGGED` provenance. Keyword flagging never *downgrades* anything — it only ever pushes toward the safe (expensive) side. If you know your task type, declare `category` — the fallback path exists for callers that don't.

## Observability

`classify()` and `route_with_cascade()` accept an optional `emit: Callable[[RoutingEvent], None]`. Every decision (including escalations) is recorded with tier, source, reason, and task metadata (category, tags, prompt length, tool count) — **not** the raw prompt text, to avoid leaking prompt content into logs by default. `InMemorySink` is a minimal reference sink for tests/demos; production use should point `emit` at whatever logging/metrics pipeline is already in place.

Without this, there's no way to know whether the heuristic thresholds are actually calibrated, or whether `KEYWORD_FLAGGED` is mostly false positives. This is the hook a future learned-classifier stage would train against, if traffic volume ever justifies it — see "Not built" below.

### What the first 76 dispatches showed

Measured 2026-09-28 against this environment's advisory log (`~/.claude/model-routing.jsonl`), 76 dispatches, no escalations:

| | count |
|---|---|
| `KEYWORD_FLAGGED` recommendations | 28 (37%) |
| of those, that changed which model actually ran | **0** |
| recommendation matched what ran (`agreed`) | 63 (83%) |
| router recommended cheaper, a more expensive model ran | 8 |

The keyword path fired on 37% of dispatches and altered nothing. Each match resolved one of three ways: it agreed with a declared category that already reached `complex` (2); it fired on a caller with no declared category at all, where a later category mapping now reaches `complex` without it (22); or it recommended Opus for an agent whose own config pinned Sonnet, and the pin won (5, all summarisation/review agents).

That last group is the useful part. A keyword override that a caller-side pin silently outranks is not a fail-safe — it is an unenforced suggestion, and the log is the only place its ineffectiveness is visible. It does not follow that the keyword list should be trimmed: a mechanism that has never changed a decision has also never cost anything, and the 22 no-category matches are evidence it does real work exactly when category config is missing — which is the case it exists for.

The genuine overspend was elsewhere and was not the router's doing: 8 dispatches where the router recommended Sonnet and Opus ran, split evenly between a caller-side model pin and an explicit human choice. Both sit above this library. The router was right and advisory, in that order.

Revisit when the log passes ~300 dispatches, or on the first `KEYWORD_FLAGGED` match that does change which model runs — whichever is first. Until then the honest summary of stage 1's untrusted path is: correctly provenanced, and so far inert.

`JsonlSink` (`model_router/sinks.py`) is the reference persistent sink — appends one JSON line per `RoutingEvent` to a local file, same no-raw-prompt guarantee as the in-memory sink. `InMemorySink` is for tests/one-off scripts; `JsonlSink` is for anything meant to accumulate across runs.

## Harness integration

`examples/claude_code_subagents.py` is a worked integration for a specific caller (this Claude Code environment's named subagent roster — Explore, implementer, sentinel, worf, etc.) mapping each subagent type to a router category, with security-reviewer agents (sentinel, spock, worf) tagged to always hit the hard override regardless of task content. It's deliberately kept out of `model_router/` proper — the library's `CATEGORY_TIER` vocabulary (classification, coding_complex, architecture, ...) is meant to be generic; a specific harness's subagent-name-to-category mapping is caller-side config, not library surface. Any other integration should follow the same shape: a small local `SUBAGENT_CATEGORY`-style dict plus a `task_for_subagent()`-style helper, not a change to `model_router/config.py`.

## Not built (deliberately)

- **No ML classifier.** A learned router (embeddings + trained model, à la RouteLLM) needs labeled (prompt, best-model) pairs at volume. There's no such dataset yet. Building one now would be guessing at a cost function with no data to validate against. The heuristic + cascade design gets most of the savings without it; the observability hook above is the seam to revisit this once real traffic exists.
- **No automatic response-quality judge.** `validate_fn` is caller-supplied on purpose — inventing a generic "is this response good" check would itself need a model call (defeating the point of routing cheaply) or be too naive to trust for escalation decisions.
- **No persistence layer.** `InMemorySink` is intentionally not a database. Wiring the observability hook into real storage is a caller-side integration decision, not this library's job.
