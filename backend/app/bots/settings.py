"""Configurable bot settings and the built-in presets.

Bots play "local" strategies: they decide from their own cards and the cards on the table,
never coordinating with teammates (no señas, no reading a partner's play).
"""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.truco.envido import EnvidoCall


class CardOrder(StrEnum):
    STRONGEST_FIRST = "strongest_first"  # strongest, then the second, then the third
    WEAKEST_FIRST = "weakest_first"
    CHEAPEST_WINNER = "cheapest_winner"  # the lowest card that beats the table, else the lowest
    RANDOM = "random"


class Policy(StrEnum):
    ALWAYS = "always"
    NEVER = "never"
    THRESHOLD = "threshold"


class BotSettings(BaseModel):
    """Envido thresholds are tantos (0–33). Truco thresholds compare the bot's best remaining
    card on the truco hierarchy, 1 (a 4) to 14 (1 de espadas), Anexo A."""

    # Every field is always present in responses (non-optional generated TS types).
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    card_order: CardOrder = CardOrder.STRONGEST_FIRST
    envido_sing: Policy = Policy.THRESHOLD
    envido_sing_threshold: int = Field(27, ge=0, le=33)
    envido_call: EnvidoCall = EnvidoCall.ENVIDO
    envido_accept: Policy = Policy.THRESHOLD
    envido_accept_threshold: int = Field(25, ge=0, le=33)
    envido_raise_threshold: int | None = Field(None, ge=0, le=33)  # None: never raises
    truco_sing: Policy = Policy.THRESHOLD
    truco_sing_threshold: int = Field(11, ge=1, le=14)
    truco_accept: Policy = Policy.THRESHOLD
    truco_accept_threshold: int = Field(10, ge=1, le=14)
    truco_raise_threshold: int | None = Field(None, ge=1, le=14)  # retruco/vale cuatro
    bluff: float = Field(0.0, ge=0, le=1)  # chance to sing truco below the threshold


class BotPreset(BaseModel):
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    key: str
    name: str
    settings: BotSettings


PRESETS: list[BotPreset] = [
    BotPreset(key="prolijo", name="Prolijo", settings=BotSettings()),
    BotPreset(
        key="envidioso",
        name="Envidioso",
        settings=BotSettings(
            envido_sing=Policy.ALWAYS,
            envido_accept=Policy.ALWAYS,
            envido_raise_threshold=28,
            truco_sing_threshold=12,
            truco_accept_threshold=11,
        ),
    ),
    BotPreset(
        key="cauteloso",
        name="Cauteloso",
        settings=BotSettings(
            card_order=CardOrder.WEAKEST_FIRST,
            envido_sing=Policy.NEVER,
            envido_accept=Policy.NEVER,
            truco_sing_threshold=13,
            truco_accept_threshold=12,
        ),
    ),
    BotPreset(
        key="mentiroso",
        name="Mentiroso",
        settings=BotSettings(
            card_order=CardOrder.RANDOM,
            envido_sing_threshold=21,
            envido_call=EnvidoCall.REAL_ENVIDO,
            envido_accept_threshold=22,
            truco_sing_threshold=12,
            truco_accept_threshold=8,
            truco_raise_threshold=12,
            bluff=0.5,
        ),
    ),
    BotPreset(
        key="ahorrativo",
        name="Ahorrativo",
        settings=BotSettings(
            card_order=CardOrder.CHEAPEST_WINNER,
            envido_sing_threshold=28,
            envido_accept_threshold=27,
            envido_raise_threshold=31,
            truco_sing_threshold=12,
            truco_raise_threshold=13,
        ),
    ),
]
