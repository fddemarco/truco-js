"""API models for game sessions: setup, per-seat views and actions."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.games.characters import Character
from app.truco.config import RuleMode
from app.truco.hand import ActionKind, Phase
from app.truco.scoring import DEFAULT_TARGET, MAX_CHAIN_POINTS, MAX_TARGET, MIN_TARGET
from app.truco.signals import BodySpot, Sena

READ = ConfigDict(json_schema_serialization_defaults_required=True)


class SeatSetup(BaseModel):
    kind: Literal["human", "bot"]
    name: str = Field("", max_length=40)
    character: Character | None = None  # default: a saved bot's, else one free
    bot_preset: str | None = None  # a preset key, or
    bot_id: int | None = None  # a saved bot


TeamName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=24)]


class ChainSetup(BaseModel):
    """Points for one canto chain, e.g. ["envido", "real_envido"]. None: the default."""

    chain: list[str] = Field(min_length=1, max_length=4)
    quiero: int | None = Field(None, ge=0, le=MAX_CHAIN_POINTS)
    no_quiero: int | None = Field(None, ge=0, le=MAX_CHAIN_POINTS)


class ScoringSetup(BaseModel):
    """Partido length and canto points; anything left out plays as the reglamento."""

    target: int = Field(DEFAULT_TARGET, ge=MIN_TARGET, le=MAX_TARGET)
    chains: list[ChainSetup] = Field([], max_length=32)


class ChainInfo(BaseModel):
    """A canto chain that can be configured, with the reglamento's points."""

    model_config = READ

    family: Literal["envido", "truco"]
    chain: list[str]
    quiero: int | None  # None: falta envido (what the leader lacks)
    no_quiero: int


class ScoringInfo(BaseModel):
    model_config = READ

    target: int
    chains: list[ChainInfo]


class GameCreate(BaseModel):
    mode: RuleMode = RuleMode.STRICT
    scoring: ScoringSetup | None = None  # default: the reglamento
    seats: list[SeatSetup] = Field(min_length=6, max_length=6)
    # Team 0, team 1. Default: drawn from a list.
    team_names: list[TeamName] | None = Field(None, min_length=2, max_length=2)


class GameCreated(BaseModel):
    id: str
    # Whoever created the game: frees a seat whose player lost their token (seat reset).
    host_token: str


class JoinRequest(BaseModel):
    seat: int = Field(ge=0, le=5)
    name: str = Field("", max_length=40)
    character: Character | None = None  # kept if no other seat has it


class Joined(BaseModel):
    seat: int
    token: str


class CardModel(BaseModel):
    number: int
    suit: str


class ActionModel(BaseModel):
    model_config = READ

    kind: ActionKind
    card: CardModel | None = None
    number: int | None = None
    sena: Sena | None = None


class TokenRequest(BaseModel):
    """A move's view options; the seat token goes in the X-Seat-Token header."""

    look: int | None = Field(None, ge=0, le=5)  # the seat the viewer's camera is on
    since: int | None = None  # the last step the client has (see GameView.steps)


class ActRequest(TokenRequest):
    action: ActionModel


class SenaRequest(TokenRequest):
    sena: Sena
    spot: BodySpot
    duration_ms: int = Field(ge=100, le=5000)
    target: int | None = Field(None, ge=0, le=5)


class SeatView(BaseModel):
    model_config = READ

    seat: int
    team: int
    number: int  # reserved number 1-2-3 (3.4)
    name: str
    character: Character
    kind: Literal["human", "bot"]
    joined: bool
    online: bool  # a bot, or a human seen in the last few seconds (a view or a move)
    in_play: bool  # takes part in the current mano or duelo
    active: bool
    cards_left: int
    shown: list[CardModel] = []  # cards shown to the table (mostrar)
    played: list[CardModel] = []  # cards this seat played this mano, in order


class PlayView(BaseModel):
    seat: int
    card: CardModel


class PendingView(BaseModel):
    model_config = READ

    family: Literal["envido", "truco"]
    chanter: int
    in_turn: bool
    irregular: bool


class EnvidoView(BaseModel):
    model_config = READ

    calls: list[str]
    accepted: bool
    team: int
    points: int
    winner_seat: int | None = None
    tantos: dict[int, int | None] = {}


class StatView(BaseModel):
    """A fun fact about the partido, for the end screen (see app/games/stats.py)."""

    model_config = READ

    key: str
    seat: int | None = None
    value: float | None = None
    mano: int | None = None
    cards: list[CardModel] = []


class SenaView(BaseModel):
    model_config = READ

    seat: int
    sena: Sena
    spot: BodySpot
    target: int | None = None
    start_ms: int
    duration_ms: int


class SenaSeenView(BaseModel):
    seat: int
    sena: Sena
    ronda: int


class EventView(BaseModel):
    model_config = READ

    seat: int | None = None
    kind: str
    card: CardModel | None = None
    number: int | None = None
    points: list[int] | None = None
    upheld: bool | None = None
    # envido canto: what quiero is worth if team 0 / team 1 wins it, then no quiero
    stakes: list[int] | None = None
    # envido result: each seat's envido (strict: real tantos; interactive: declared, None for
    # son buenas or not in it)
    tantos: list[int | None] | None = None
    hand_kind: str | None = None  # reparto: redonda or pica_pica


class ResultView(BaseModel):
    kind: str
    winner: int | None


class GameView(BaseModel):
    model_config = READ

    id: str
    mode: RuleMode
    version: int
    server_ms: int
    started: bool
    seats: list[SeatView]
    team_names: list[str]
    score: list[int]
    target: int = 30  # points to win the partido
    malas_max: int = 15  # the last point of malas
    hand_number: int
    hand_kind: str | None = None
    dealer: int
    mano: int | None = None
    pie: int | None = None  # the last to play in the mano or duelo
    phase: Phase | None = None  # of the mano (or current duelo) in progress
    to_act: int | None = None
    duel: list[int] | None = None  # the two seats of the current duelo de pica-pica
    rounds: list[list[PlayView]] = []
    results: list[int | None] = []  # ronda winners (team), None = parda
    pending: list[PendingView] = []
    envido_calls: list[str] = []
    truco_level: int = 0
    truco_accepted: int = 0
    envido: EnvidoView | None = None
    pies: list[int | None] = [None, None]  # each team's last to play in the mano or duelo
    stats: list[StatView] = []  # once the partido is over
    declarations: dict[int, int | None] = {}
    can_deal: bool = False
    # Between manos: when the table deals by itself (epoch ms, server clock) and who may cut
    # sooner (POST /deal).
    deal_at: int | None = None
    cutter: int | None = None
    result: ResultView | None = None
    events: list[EventView] = []
    senas: list[SenaView] = []
    # Private to the viewer.
    me: int | None = None
    my_cards: list[CardModel] = []
    my_tanto: int | None = None  # the viewer's real tanto, from the three cards dealt (11.1)
    actions: list[ActionModel] = []
    senas_seen: list[SenaSeenView] = []
    # Moves as steps, to show one at a time: the steps after the request's `since`, or on
    # arrival (no `since`) the current mano's since the viewer's last move, from `base`.
    step: int = -1  # the latest step
    steps: list["StepView"] = []
    base: "GameView | None" = None


class StepView(BaseModel):
    """One move (an action or a deal) and what it set off, with the table right after it as
    the viewer saw it (without señas, which are live)."""

    model_config = READ

    index: int
    seat: int | None = None  # who moved; None for a deal
    events: list[EventView]
    view: GameView


GameView.model_rebuild()
