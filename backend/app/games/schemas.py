"""API models for game sessions: setup, per-seat views and actions."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.games.characters import Character
from app.truco.config import RuleMode
from app.truco.hand import ActionKind, Phase
from app.truco.match import MatchPhase
from app.truco.signals import BodySpot, Sena

READ = ConfigDict(json_schema_serialization_defaults_required=True)


class SeatSetup(BaseModel):
    kind: Literal["human", "bot"]
    name: str = Field("", max_length=40)
    character: Character | None = None  # default: a saved bot's, else one free
    bot_preset: str | None = None  # a preset key, or
    bot_id: int | None = None  # a saved bot


TeamName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=24)]


class GameCreate(BaseModel):
    mode: RuleMode = RuleMode.STRICT
    seats: list[SeatSetup] = Field(min_length=6, max_length=6)
    # Team 0, team 1. Default: drawn from a list.
    team_names: list[TeamName] | None = Field(None, min_length=2, max_length=2)


class GameCreated(BaseModel):
    id: str


class JoinRequest(BaseModel):
    seat: int = Field(ge=0, le=5)
    name: str = Field("", max_length=40)


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
    token: str
    look: int | None = Field(None, ge=0, le=5)  # the seat the viewer's camera is on


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
    match_phase: MatchPhase
    seats: list[SeatView]
    team_names: list[str]
    score: list[int]
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
    declarations: dict[int, int | None] = {}
    can_deal: bool = False
    result: ResultView | None = None
    events: list[EventView] = []
    senas: list[SenaView] = []
    # Private to the viewer.
    me: int | None = None
    my_cards: list[CardModel] = []
    actions: list[ActionModel] = []
    senas_seen: list[SenaSeenView] = []
