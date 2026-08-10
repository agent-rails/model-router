from __future__ import annotations

from model_router import TaskRequest

SUBAGENT_CATEGORY: dict[str, str] = {
    "Explore": "data_analysis",
    "general-purpose": "chat",
    "claude": "chat",
    "implementer": "coding_complex",
    "debugger": "debugging_hard",
    "tester": "coding_simple",
    "researcher": "data_analysis",
    "architect": "architecture",
    "architect-reviewer": "code_review",
    "ai-architect": "architecture",
    "sentinel-fetcher": "extraction",
    "sentinel-scribe": "summarization",
    "scotty": "coding_complex",
    "senior-qa": "code_review",
    "context-manager": "summarization",
    "claude-code-guide": "simple_qa",
    "statusline-setup": "coding_simple",
    "voltage": "chat",
    "voltage-fetcher": "extraction",
    "voltage-reporter": "summarization",
    "voltage-scribe": "summarization",
    "Plan": "architecture",
    "orchestrator": "long_horizon_agentic",
    "caveman:cavecrew-investigator": "extraction",
    "caveman:cavecrew-builder": "coding_simple",
    "caveman:cavecrew-reviewer": "coding_simple",
}

SUBAGENT_OVERRIDE_TAGS: dict[str, frozenset[str]] = {
    "sentinel": frozenset({"security_review"}),
    "spock": frozenset({"security_review"}),
    "worf": frozenset({"security_review"}),
}

SUBAGENT_IS_AGENTIC: frozenset[str] = frozenset({"orchestrator"})


def task_for_subagent(subagent_type: str, prompt: str, **overrides: object) -> TaskRequest:
    fields: dict[str, object] = {
        "prompt": prompt,
        "category": SUBAGENT_CATEGORY.get(subagent_type),
        "tags": SUBAGENT_OVERRIDE_TAGS.get(subagent_type, frozenset()),
        "is_agentic": subagent_type in SUBAGENT_IS_AGENTIC,
    }
    fields.update(overrides)
    return TaskRequest(**fields)
