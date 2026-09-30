from enum import StrEnum


class Model(StrEnum):
    HAIKU = "claude-haiku-4-5"
    SONNET = "claude-sonnet-5-5"
    OPUS = "claude-opus-5-5"
    # Expressible so a caller can name it; not any tier's default. At 2.5x Opus
    # it only earns its cost on work Opus measurably cannot do.
    FABLE = "claude-fable-5-1"


class Effort(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    XHIGH = "xhigh"
    MAX = "max"


# (input, output) USD per million tokens. Verified against the Claude API model
# table 2026-09-30. SONNET was (3.00, 15.00) -- Sonnet 4.6's rate, not Sonnet 5's --
# which overstated the Sonnet tier by 50% inside a router whose whole job is
# choosing on cost.
PRICING_PER_MTOK: dict[Model, tuple[float, float]] = {
    Model.HAIKU: (1.00, 5.00),
    Model.SONNET: (2.00, 10.00),
    Model.OPUS: (4.00, 20.00),
    Model.FABLE: (10.00, 50.00),
}
