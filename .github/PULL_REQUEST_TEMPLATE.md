## What changed and why

## Trust-boundary check

- [ ] Does this touch `OVERRIDE_CATEGORIES`, `OVERRIDE_KEYWORDS`, or `_override_reason`? If so, category/tag matching must stay the trusted path and keyword matching must stay `KEYWORD_FLAGGED`, never promoted to `OVERRIDE`.
- [ ] Does this change what `RoutingEvent` captures? If so, confirm no raw prompt text can reach it — see `docs/THREAT_MODEL.md` § 5.

## Tests

- [ ] `ruff format . && ruff check .` clean
- [ ] `python -m pytest -q` green
- [ ] New behavior has a regression test, not just a happy-path one
