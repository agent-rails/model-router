import pytest

from model_router import CodexModel, RoutingSource, Workflow, infer_task, plan_codex


@pytest.mark.parametrize(
    ("prompt", "category", "model", "effort"),
    [
        ("Format this list as CSV", "formatting", CodexModel.LUNA, "high"),
        ("Classify these support tickets", "classification", CodexModel.LUNA, "high"),
        ("Fix the typo in the README", "coding_simple", CodexModel.SOL, "medium"),
        ("Design the model serving scheduler", "architecture", CodexModel.SOL, "high"),
        ("Build distributed job recovery", "coding_complex", CodexModel.SOL, "high"),
        ("Refactor this service's dependency injection", "coding_complex", CodexModel.SOL, "high"),
        ("Review this PR end to end", "code_review", CodexModel.SOL, "high"),
        ("Chat: help me draft a Slack message about a schedule change", "chat", CodexModel.SOL, "medium"),
        ("Summarize this postmortem", "summarization", CodexModel.SOL, "medium"),
        ("Review payment authentication", "security_review", CodexModel.SOL, "high"),
        ("Can you help with this?", None, CodexModel.SOL, "medium"),
    ],
)
def test_infer_safe_task_start(prompt, category, model, effort):
    inferred = infer_task(prompt)
    plan = plan_codex(inferred.request)
    assert inferred.request.category == category
    assert plan.model == model
    assert plan.effort.value == effort


def test_inferred_security_is_flagged_not_trusted_override():
    plan = plan_codex(infer_task("Review payment authentication").request)
    assert plan.source == RoutingSource.KEYWORD_FLAGGED
    assert plan.workflow == Workflow.INVESTIGATE_VERIFY


def test_full_prompt_still_triggers_existing_security_flag():
    plan = plan_codex(infer_task("Format this list\napi key: example").request)
    assert plan.model == CodexModel.SOL
    assert plan.source == RoutingSource.KEYWORD_FLAGGED


def test_ai_topic_is_available_to_caller_without_a_private_wiki_path():
    inferred = infer_task("Design an inference scheduler")
    assert "inference" in inferred.request.tags


def test_communication_task_uses_direct_workflow():
    plan = plan_codex(infer_task("Draft a status email to the team").request)
    assert plan.workflow == Workflow.DIRECT


@pytest.mark.parametrize(
    "prompt",
    [
        "Rotate the IAM role for prod",
        "Tighten RBAC on the authz service",
        "Update the OIDC trust policy",
        "Fix the jwt signature check",
        "Change the kubeconfig for the cluster",
        "Disable TLS verification in the client",
        "Fix the sudo access rule",
        "Refresh the bearer token handling",
    ],
)
def test_identity_and_infra_terms_in_lead_are_risk(prompt):
    assert infer_task(prompt).request.category == "security_review"


@pytest.mark.parametrize(
    "prompt",
    [
        "Implement the task below.\n\nContext: the login hook has an authentication bypass.",
        "Implement the task below.\n\nThen rotate the credentials.",
        "Update the client.\n\nIt reads the kubeconfig from disk.",
        "Write the handler.\n\nStore the private key in the vault.",
    ],
)
def test_high_precision_risk_terms_anywhere_in_prompt_are_risk(prompt):
    assert infer_task(prompt).request.category == "security_review"


@pytest.mark.parametrize(
    "prompt",
    [
        "Summarise the log.\n\nDo not delete any files.",
        "Summarise the log.\n\nKeep the token budget small.",
        "Summarise the log.\n\nThis is not for production.",
    ],
)
def test_broad_action_words_after_the_lead_are_not_risk(prompt):
    assert infer_task(prompt).request.category == "summarization"


def test_fullwidth_risk_term_is_normalised():
    assert infer_task("Rotate the ＩＡＭ role").request.category == "security_review"


@pytest.mark.parametrize(
    "prompt",
    [
        "Rotate token",
        "Rotate the password",
        "Enable MFA for admins",
        "Rotate the ssh key",
        "Edit sudoers",
        "Fix authentications",
        "Fix the api_key loader",
        "Handle auth_token expiry",
        "Renew the TLS certificate",
    ],
)
def test_more_lead_risk_terms(prompt):
    assert infer_task(prompt).request.category == "security_review"


@pytest.mark.parametrize(
    "prompt",
    [
        "Summarize the session below.\npassword=hunter2",
        "Summarize below.\nrotate the db password",
        "Write the loader.\nIt reads AWS_ACCESS_KEY_ID from env.",
        "Write the handler.\nMount the service account token.",
        "Update the client.\nPin the TLS cert.",
        "Fix the script.\nIt edits sudoers.",
        "Write the policy.\nGrant admin privileges and disable MFA.",
    ],
)
def test_more_body_risk_terms(prompt):
    assert infer_task(prompt).request.category == "security_review"


@pytest.mark.parametrize("prompt", ["Fix i\u200bam policy", "Fix the k‍ubeconfig", "Fix I­AM policy"])
def test_invisible_characters_do_not_split_risk_terms(prompt):
    assert infer_task(prompt).request.category == "security_review"


@pytest.mark.parametrize("prompt", ["William reviewed the product roadmap", "Summarise the authority matrix"])
def test_word_boundaries_hold(prompt):
    assert infer_task(prompt).request.category != "security_review"
