from __future__ import annotations

from collections import Counter

from model_router import InMemorySink, TaskRequest, classify
from model_router.models import PRICING_PER_MTOK, Model

PILOT_TASKS: list[TaskRequest] = [
    TaskRequest(prompt="Classify this support ticket as billing/technical/other.", category="classification"),
    TaskRequest(prompt="Extract the invoice number and total from this receipt text.", category="extraction"),
    TaskRequest(prompt="Translate this paragraph to Spanish.", category="translation"),
    TaskRequest(prompt="What's the capital of France?", category="simple_qa"),
    TaskRequest(prompt="Summarize this 2-page incident postmortem.", category="summarization"),
    TaskRequest(prompt="Write a Python function to parse a CSV and dedupe rows by email.", category="coding_simple"),
    TaskRequest(prompt="Chat: help me draft a Slack message to my team about a schedule change.", category="chat"),
    TaskRequest(
        prompt="Refactor this service's dependency injection to remove the singleton.", category="architecture"
    ),
    TaskRequest(
        prompt="Debug why this async queue consumer occasionally drops messages under load.", category="debugging_hard"
    ),
    TaskRequest(prompt="Review this PR end to end for correctness and edge cases.", category="code_review"),
    TaskRequest(
        prompt="Run the full agentic migration of this service to the new API, verifying each step.",
        category="long_horizon_agentic",
        is_agentic=True,
        tool_schema_count=8,
    ),
    TaskRequest(prompt="Rotate the deploy credential for the auth service.", category="auth"),
    TaskRequest(prompt="Review this change to agent-guard's identity policy engine.", category="agent_guard"),
    TaskRequest(prompt="Draft the quarterly summary email for the team.", tags=frozenset({"internal"})),
    TaskRequest(prompt="We need to push this straight to production before the demo."),
    TaskRequest(prompt="Sort this list of 20 strings alphabetically."),
]

CHARS_PER_TOKEN_ESTIMATE = 4
ASSUMED_OUTPUT_TOKENS = 500


def estimate_cost_usd(model, prompt_chars: int) -> float:
    input_price, output_price = PRICING_PER_MTOK[model]
    input_tokens = prompt_chars / CHARS_PER_TOKEN_ESTIMATE
    return (input_tokens / 1_000_000) * input_price + (ASSUMED_OUTPUT_TOKENS / 1_000_000) * output_price


def main() -> None:
    sink = InMemorySink()
    routed_cost = 0.0
    baseline_cost = 0.0

    print(f"{'category':<22}{'tier':<10}{'model':<20}{'effort':<8}{'source':<16}reason")
    print("-" * 120)
    for task in PILOT_TASKS:
        decision = classify(task, emit=sink)
        routed_cost += estimate_cost_usd(decision.model, len(task.prompt))
        baseline_cost += estimate_cost_usd(Model.OPUS, len(task.prompt))
        print(
            f"{(task.category or '-'):<22}{decision.tier.value:<10}{decision.model.value:<20}"
            f"{decision.effort.value:<8}{decision.source.value:<16}{decision.reason}"
        )

    print()
    tier_counts = Counter(e.decision.tier.value for e in sink.events)
    source_counts = Counter(e.decision.source.value for e in sink.events)
    print(f"tier distribution:   {dict(tier_counts)}")
    print(f"source distribution: {dict(source_counts)}")
    print(f"keyword-flagged (audit these): {len(sink.keyword_flagged())}")
    print()
    print(f"estimated cost, routed:        ${routed_cost:.5f}")
    print(f"estimated cost, all-Opus baseline: ${baseline_cost:.5f}")
    print(f"estimated savings: {(1 - routed_cost / baseline_cost) * 100:.1f}%")


if __name__ == "__main__":
    main()
