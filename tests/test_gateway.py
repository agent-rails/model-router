import pytest

from model_router import TaskRequest, TaskTier, classify, gateway_alias


def test_gateway_alias_resolves_classified_tier():
    decision = classify(TaskRequest(prompt="tag this", category="classification"))

    assert gateway_alias(decision, {TaskTier.TRIVIAL: "ollama-default"}) == "ollama-default"


def test_gateway_alias_fails_closed_when_tier_is_not_configured():
    decision = classify(TaskRequest(prompt="design this", category="architecture"))

    with pytest.raises(ValueError, match="no gateway alias configured for tier 'complex'"):
        gateway_alias(decision, {TaskTier.TRIVIAL: "ollama-default"})


def test_gateway_alias_rejects_blank_alias():
    decision = classify(TaskRequest(prompt="tag this", category="classification"))

    with pytest.raises(ValueError, match="no gateway alias configured for tier 'trivial'"):
        gateway_alias(decision, {TaskTier.TRIVIAL: "  "})


def test_gateway_alias_refuses_a_fable_decision_on_the_complex_tier():
    decision = classify(TaskRequest(prompt="break this", tags=frozenset({"adversarial_review"})))

    with pytest.raises(ValueError, match="decision model 'claude-fable-5-1' is not the 'complex' tier model"):
        gateway_alias(decision, {TaskTier.COMPLEX: "claude-opus-5-5"})


def test_gateway_alias_resolves_an_opus_decision_on_the_complex_tier():
    decision = classify(TaskRequest(prompt="design this", category="architecture"))

    assert gateway_alias(decision, {TaskTier.COMPLEX: "opus-deployment"}) == "opus-deployment"
