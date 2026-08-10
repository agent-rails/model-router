---
name: Override false positive / false negative
about: A keyword or category incorrectly triggered (or failed to trigger) the security override
labels: security-review
---

## Which direction

- [ ] False positive — `KEYWORD_FLAGGED` fired on a prompt that wasn't actually sensitive (see `docs/THREAT_MODEL.md` § 2)
- [ ] False negative — a task that should have hit the override didn't (see `docs/THREAT_MODEL.md` § 1 and § 3)

## Task details

- `category` used (if any):
- Relevant prompt excerpt (redact anything sensitive):
- `decision.source` / `decision.reason` observed:

## Proposed fix

- [ ] Add/remove a keyword in `OVERRIDE_KEYWORDS` (`model_router/config.py`)
- [ ] Add/remove a category in `OVERRIDE_CATEGORIES` or `CATEGORY_TIER`
- [ ] Something else — describe below
