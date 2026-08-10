from enum import StrEnum


class Model(StrEnum):
    HAIKU = "claude-haiku-4-5"
    SONNET = "claude-sonnet-5"
    OPUS = "claude-opus-4-8"
    FABLE = "claude-fable-5"


class Effort(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    XHIGH = "xhigh"
    MAX = "max"


PRICING_PER_MTOK: dict[Model, tuple[float, float]] = {
    Model.HAIKU: (1.00, 5.00),
    Model.SONNET: (3.00, 15.00),
    Model.OPUS: (5.00, 25.00),
    Model.FABLE: (10.00, 50.00),
}
