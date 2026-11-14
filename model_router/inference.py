"""Conservative, zero-token classification of a new task's instruction text."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from model_router.types import TaskRequest


@dataclass(frozen=True, slots=True)
class TaskInference:
    request: TaskRequest
    rule: str


# Boundaries exclude letters and digits only, so snake_case identifiers such as
# api_key or auth_token match; `\b` treats `_` as a word character and missed them.
_B, _E = r"(?<![A-Za-z0-9])(?:", r")(?![A-Za-z0-9])"
_SEP = r"[ _-]?"

_RISK = re.compile(
    _B + r"auth(?:entications?|orizations?|n|z)?|security|secrets?|credentials?|"
    rf"api{_SEP}keys?|passwords?|passphrases?|mfa|2fa|ssh{_SEP}keys?|"
    r"certificates?|certs?|payments?|funds|kyc|pii|production|prod|prod deploy|irreversible|"
    r"delete|drop table|force push|iam|rbac|oidc|oauth|jwt|tls|mtls|ssl|kubeconfig|"
    rf"sudo|sudoers|privileges?|permissions?|security groups?|service{_SEP}accounts?|"
    rf"(?:(?:access|auth|bearer|refresh|api|session){_SEP})?tokens?" + _E,
    re.IGNORECASE,
)
# Checked across the whole prompt, not just the lead. Only terms that name a
# security asset qualify: broad action words such as "delete" or "production"
# appear in routine instructions ("do not delete files") and would send nearly
# every multi-line prompt to the top tier. Bare "token" is lead-only for the
# same reason: in a prompt body it usually means a token budget.
_RISK_ANYWHERE = re.compile(
    _B + r"authentication|authorization|authn|authz|credentials?|"
    rf"secrets?{_SEP}(?:manager|store|key)|api{_SEP}keys?|private{_SEP}keys?|ssh{_SEP}keys?|"
    rf"passwords?|passphrases?|mfa|(?:access|auth|bearer|refresh|session){_SEP}tokens?|"
    rf"service{_SEP}account{_SEP}tokens?|aws_access_key_id|aws_secret_access_key|"
    rf"tls{_SEP}cert(?:ificate)?s?|iam|rbac|oidc|oauth|jwt|kubeconfig|sudoers|"
    r"admin privileges?|kyc|pii" + _E,
    re.IGNORECASE,
)


def _normalise(prompt: str) -> str:
    """NFKC-fold, then drop format and combining characters.

    NFKC folds fullwidth and compatibility forms but keeps zero-width spaces,
    joiners and soft hyphens (category Cf) and combining marks (Mn), any of
    which can split a term ("i\u200bam"). Cross-script lookalikes are still not
    folded; see THREAT_MODEL section 1.
    """
    folded = unicodedata.normalize("NFKD", unicodedata.normalize("NFKC", prompt))
    return unicodedata.normalize("NFC", "".join(c for c in folded if unicodedata.category(c) not in {"Cf", "Mn"}))


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

    Intent is classified from the leading instruction. Risk is checked twice:
    broad risk terms in the lead, and high-precision security-asset terms
    (credentials, IAM, JWT, kubeconfig, ...) anywhere in the normalised prompt
    (NFKC, format and combining characters removed). The full prompt still reaches the router's conservative
    risk-keyword and length checks. Inferred metadata
    is untrusted, so it never masquerades as a caller-declared security override.
    """
    normalized = _normalise(prompt)
    lead = normalized.strip().splitlines()[0][:240] if normalized.strip() else ""
    tags = frozenset(topic for pattern, topic in _AI_TOPICS if pattern.search(lead))
    if _RISK.search(lead):
        category, rule = "security_review", "risk term in leading instruction"
    elif _RISK_ANYWHERE.search(normalized):
        category, rule = "security_review", "security asset named in prompt body"
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
