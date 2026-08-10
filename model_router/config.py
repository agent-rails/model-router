from __future__ import annotations

from model_router.models import Effort, Model
from model_router.types import TaskTier

OVERRIDE_CATEGORIES: frozenset[str] = frozenset(
    {
        "security_review",
        "auth",
        "identity",
        "secrets_handling",
        "production_infra",
        "agent_guard",
        "warrant",
        "compliance",
        "financial_transaction",
        "irreversible_action",
    }
)

OVERRIDE_KEYWORDS: frozenset[str] = frozenset(
    {
        "api key",
        "access token",
        "auth token",
        "rotate cred",
        "production",
        "prod deploy",
        "irreversible",
        "drop table",
        "force push",
        "delete branch",
        "agent-guard",
        "agent_guard",
        "warrant",
        "compliance",
        "pii",
        "financial transaction",
    }
)

CATEGORY_TIER: dict[str, TaskTier] = {
    "classification": TaskTier.TRIVIAL,
    "extraction": TaskTier.TRIVIAL,
    "simple_qa": TaskTier.TRIVIAL,
    "formatting": TaskTier.TRIVIAL,
    "translation": TaskTier.TRIVIAL,
    "summarization": TaskTier.MODERATE,
    "chat": TaskTier.MODERATE,
    "data_analysis": TaskTier.MODERATE,
    "coding_simple": TaskTier.MODERATE,
    "coding_complex": TaskTier.COMPLEX,
    "architecture": TaskTier.COMPLEX,
    "debugging_hard": TaskTier.COMPLEX,
    "long_horizon_agentic": TaskTier.COMPLEX,
    "code_review": TaskTier.COMPLEX,
}

TIER_ROUTE: dict[TaskTier, tuple[Model, Effort]] = {
    TaskTier.TRIVIAL: (Model.HAIKU, Effort.LOW),
    TaskTier.MODERATE: (Model.SONNET, Effort.MEDIUM),
    TaskTier.COMPLEX: (Model.OPUS, Effort.HIGH),
}

ESCALATION_PATH: dict[Model, Model] = {
    Model.HAIKU: Model.SONNET,
    Model.SONNET: Model.OPUS,
    Model.OPUS: Model.OPUS,
}

AGENTIC_EFFORT_BUMP: dict[Model, Effort] = {
    Model.SONNET: Effort.XHIGH,
    Model.OPUS: Effort.XHIGH,
}

LONG_PROMPT_CHAR_THRESHOLD = 4000
MANY_TOOLS_THRESHOLD = 5
