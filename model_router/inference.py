"""Conservative, zero-token classification of a new task's instruction text."""

from __future__ import annotations

import re
from dataclasses import dataclass

from model_router.types import TaskRequest


@dataclass(frozen=True, slots=True)
class TaskInference:
    request: TaskRequest
    rule: str


_RISK = re.compile(
    r"\b(auth(?:entication|orization)?|security|secrets?|credentials?|api keys?|"
    r"payments?|funds|kyc|pii|production|prod deploy|irreversible|"
    r"delete|drop table|force push)\b",
    re.IGNORECASE,
)
_RESEARCH = re.compile(r"\b(research|investigate|evaluate|compare|survey)\b", re.IGNORECASE)
_DESIGN = re.compile(r"\b(design|architect|architecture|system design)\b", re.IGNORECASE)
_COMPLEX = re.compile(
    r"\b(distributed|concurrency|cross.repo|multi.repo|migration|state machine|race condition|end.to.end|refactor)\b",
    re.IGNORECASE,
)
_DEBUG = re.compile(r"\b(debug|failing|failure|root cause|why does|broken)\b", re.IGNORECASE)
_REVIEW = re.compile(r"^\s*(?:(?:can|could) you\s+|please\s+)?(?:review|audit)\b", re.IGNORECASE)
_SUMMARY = re.compile(r"^\s*(?:please\s+)?summari[sz]e\b", re.IGNORECASE)
_CHAT = re.compile(r"^\s*chat:|\b(?:draft|compose)\b.{0,100}\b(?:email|message|letter|post)\b", re.IGNORECASE)
_CODE = re.compile(r"\b(fix|implement|build|add|update|write|create)\b", re.IGNORECASE)
_NARROW = (
    (re.compile(r"^\s*(classify|label|tag)\b", re.IGNORECASE), "classification"),
    (re.compile(r"^\s*extract\b", re.IGNORECASE), "extraction"),
    (re.compile(r"^\s*(format|reformat)\b", re.IGNORECASE), "formatting"),
    (re.compile(r"^\s*translate\b", re.IGNORECASE), "translation"),
)
_AI_TOPICS = (
    (re.compile(r"\b(inference|model serving|vllm|kv cache)\b", re.IGNORECASE), "inference"),
    (re.compile(r"\b(orchestrat(?:e|ion)|agent workflow)\b", re.IGNORECASE), "orchestration"),
    (re.compile(r"\b(rout(?:e|er|ing)|litellm)\b", re.IGNORECASE), "routing"),
    (re.compile(r"\b(distributed ai|distributed agent)\b", re.IGNORECASE), "distributed_ai"),
)


def infer_task(prompt: str) -> TaskInference:
    """Infer a task-start route; unknown or mixed intent stays on Sol.

    Only the leading instruction is classified. The full prompt still reaches
    the router's conservative risk-keyword and length checks. Inferred metadata
    is untrusted, so it never masquerades as a caller-declared security override.
    """
    lead = prompt.strip().splitlines()[0][:240] if prompt.strip() else ""
    tags = frozenset(topic for pattern, topic in _AI_TOPICS if pattern.search(lead))
    if _RISK.search(lead):
        category, rule = "security_review", "risk term in leading instruction"
    elif _REVIEW.search(lead):
        category, rule = "code_review", "review intent"
    elif _DEBUG.search(lead):
        category, rule = "debugging_hard", "investigation intent"
    elif _DESIGN.search(lead):
        category, rule = "architecture", "design intent"
    elif _RESEARCH.search(lead):
        category, rule = "research", "research intent"
    elif _COMPLEX.search(lead):
        category, rule = "coding_complex", "complex implementation signal"
    elif _SUMMARY.search(lead):
        category, rule = "summarization", "summary intent"
    elif _CHAT.search(lead):
        category, rule = "chat", "communication intent"
    elif _CODE.search(lead):
        category, rule = "coding_simple", "implementation intent"
    else:
        narrow = next((name for pattern, name in _NARROW if pattern.search(lead)), None)
        category, rule = (narrow, "bounded transformation") if narrow else (None, "unknown intent; default moderate")
    return TaskInference(TaskRequest(prompt=prompt, category=category, tags=tags, metadata_trusted=False), rule)
