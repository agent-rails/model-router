# Codex and local routing: first slice

This is a task-start policy for bounded, read-only dispatched work. It does not
change the model or effort of an active Codex turn. The main agent remains free
to decide whether work needs a worker, and the caller remains responsible for
permissions, success criteria, and verification.

## Mechanism and ownership

```text
caller declares task category, tags, workstreams
  -> model-router: safety floor, tier, workflow, qualified local eligibility
  -> provider adapter: explicit Codex model/effort or Ollama model
  -> caller: objective check and acceptance decision
```

Claude routing is unchanged. Codex's initial map follows the [current Codex
subagent guidance](https://learn.chatgpt.com/docs/agent-configuration/subagents):
Luna/high for narrow work, Sol/medium as the general starting point, Sol/high
for complex work and review. These are recommendations, not measured optimal
settings for this repository. Astra and newer Sol variants are not automatic
defaults because account availability and task quality must be checked first.
Unknown categories default to Sol/medium. A trusted security category or tag
uses Sol/high. A prompt keyword can only raise the tier and is reported as
`keyword_flagged`, because free text is not a trusted security label.

Workflow labels convey a small execution contract: direct, implement and
verify, investigate and verify, or research and design. Delegation is suggested
only when a caller declares two or more independent workstreams, and remains
optional. AI-system tags return two discovery pages plus at most one relevant
wiki page; the caller reads only what the task needs. No wiki text is injected
automatically.

## Local model qualification

An installed model is not automatically eligible. The caller must supply a
qualification record tied to its current Ollama digest and a retained
evaluation report. The record declares tested categories, a maximum evaluated
prompt size, a measured p95 latency, and an expiration date. The planner rejects
stale or mismatched records, latency violations, and tasks requiring tools,
agent loops, structured output, multiple workstreams, or a higher safety tier.
It reports rejection reasons and returns the Codex recommendation.

The record is an operator assertion backed by evidence, not a cryptographic
proof of quality. Before adding one, evaluate the exact local artifact on a
representative held-out suite using the existing homelab harness. Include
absolute pass gates, tool-use negative cases where relevant, several runs,
latency, and model identity. The prior `llama3.1:8b` suite failed a no-tool-needed
case, so no default record ships. Requalify after a model, prompt, tool, runtime,
or evaluation policy change.

Local serving consumes no hosted model tokens but still has compute, latency,
and quality costs. A cheap first attempt is a loss if retries, supervision or
incorrect outcomes increase. The decision metric is total cost per accepted
task, not model price per token alone. Codex and Ollama adapters expose usage;
missing fields remain unknown. Subscription credits, API billing and local
compute should be accounted for separately.

## Failure boundaries and next measurement

The example dispatcher is dry-run by default and read-only when executed. It
does not automatically retry an entire agent task after a provider error. An
unknown result after a tool side effect needs reconciliation before replay.
Model selection must never widen sandbox permissions.

For the next evaluation, collect a small matched set of real tasks with
category, chosen route, actual model, cached/uncached input, output, latency,
validation result, retries and any human correction. Compare the current
workflow with the proposed policy at equal quality thresholds. Pin/version the
policy and qualification records. Keep any classifier or Jev suggestion in
shadow mode until deterministic routing has a measured failure mode it can fix.

Related shared knowledge: `~/wiki/designs/codex-cost-aware-harness.md` and
`~/wiki/designs/ai-component-build-priorities.md`.
