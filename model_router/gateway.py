from collections.abc import Mapping

from model_router.config import TIER_ROUTE
from model_router.types import RoutingDecision, TaskTier


def gateway_alias(decision: RoutingDecision, aliases: Mapping[TaskTier, str]) -> str:
    tier_model, _ = TIER_ROUTE[decision.tier]
    if decision.model != tier_model:
        raise ValueError(
            f"decision model '{decision.model.value}' is not the '{decision.tier.value}' tier model "
            f"'{tier_model.value}'; a tier alias would run a different model"
        )
    alias = aliases.get(decision.tier)
    if alias is None or not alias.strip():
        raise ValueError(f"no gateway alias configured for tier '{decision.tier.value}'")
    return alias
