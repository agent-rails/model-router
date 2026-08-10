# Threat Model

Lightweight, proportional to what this library actually does: pick a model + effort level. It does not execute the call, does not sanitize prompt content, and does not gate on anything the underlying model API doesn't already gate on. Scope is the routing decision only.

## 1. Keyword-scan evasion

`KEYWORD_FLAGGED` is substring matching on raw prompt text. Paraphrase, translation, or just not using the listed words evades it entirely. **This is expected, not a bug** — the keyword scan was never meant to be the trust boundary; category declaration is. Residual risk only materializes when a caller has a genuinely security-critical task *and* fails to declare `category` *and* the prompt happens to dodge every listed keyword. Mitigation: category declaration is the real control (see `DESIGN.md` § Trust boundary); treat the keyword path as defense-in-depth, not primary coverage. Audit exposure periodically via `InMemorySink.keyword_flagged()` (or the caller's own sink) to see what's slipping through unflagged.

## 2. Keyword-scan over-triggering

The flip side of #1: common words ("production", "compliance") appear in plenty of unrelated prompts and force a Opus/high route that wasn't needed. Accepted as the correct failure direction — worst case is spending more than necessary, never under-protecting. If this becomes a real expense, the fix is pruning `OVERRIDE_KEYWORDS`, not weakening the override behavior itself. Monitor via the same sink.

## 3. Silent under-routing from an unrecognized category string

A typo'd or unknown `category` (not in `CATEGORY_TIER`, not in `OVERRIDE_CATEGORIES`) falls through to the `moderate` default rather than erroring. A genuinely sensitive task with a misspelled category name gets Sonnet, not the override path, and nothing crashes to flag it. Mitigation: the decision `reason` field distinguishes "category mapped to X" from "no category supplied, defaulted to moderate" — greppable in telemetry. Not yet built: a lint/static check that call-site category strings match the known set. Recommended before this is trusted at scale.

## 4. Escalation-path cost amplification

An adversarial or pathological input that always fails `validate_fn` forces every escalation step on every call. Bounded by two things: `max_escalations` (caller-set, defaults low) and the hard ceiling at Opus (`ESCALATION_PATH[Opus] == Opus`, loop terminates — see `test_no_infinite_loop_once_already_at_opus_ceiling`). Residual risk lives in a naive `validate_fn` (e.g. "did the model produce any text") that fails on legitimate-but-hard inputs as often as on adversarial ones — that's a caller-side tuning problem, not a router bug, but worth calling out since the router can't verify the quality of a validator it didn't write.

## 5. Prompt content in observability

`RoutingEvent` deliberately excludes the raw prompt — only `prompt_chars` (length), category, tags, and decision fields. If a downstream sink is wired to a lower-trust logging pipeline than the prompt itself flows through, this bounds what leaks: routing metadata, not content.

## 6. Config integrity

`OVERRIDE_CATEGORIES`, `OVERRIDE_KEYWORDS`, `CATEGORY_TIER` are static Python dicts shipped in the package — not loaded from a remote or user-writable file at runtime. No injection path for tampering with routing rules short of modifying the installed package itself, which is a supply-chain concern out of scope for this document.

## Explicitly out of scope

- Prompt injection into the underlying model call — this router picks `(model, effort)` and hands the prompt through unchanged; it is not a content filter.
- Anything downstream of the model response (the response itself, tool execution, etc.) — `validate_fn` is the caller's hook for that, not this library's responsibility.
