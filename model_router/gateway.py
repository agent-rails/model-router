from collections.abc import Mapping

from model_router.types import RoutingDecision, TaskTier


def gateway_alias(decision: RoutingDecision, aliases: Mapping[TaskTier, str]) -> str:
    alias = aliases.get(decision.tier)
    if alias is None or not alias.strip():
        raise ValueError(f"no gateway alias configured for tier '{decision.tier.value}'")
    return alias
