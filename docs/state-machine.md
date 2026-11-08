# Hand state machine

Before this refactor, `Contest` (`backend/app/truco/hand.py`) derives its state from flags (`finished`,
`declaration`, `pending` + `_blocking()`, `turn`, `claims_open`, `_undo`, `forfeited_to`,
`annulled`), and the legal moves are rebuilt from those flags twice (`_strict_actions`,
`_interactive_actions`). Now `Contest.phase` is stored, transitions go through `_enter` /
`_settle_cantos`, and `actions_for(seat)` dispatches to one `_moves_<phase>` method shared by
both modes. `tests/truco/test_phases.py` pins the table below.

## States of one contest (mano redonda or one duelo)

| Phase | Who acts | Legal moves (strict / interactive) | Leaves to |
|---|---|---|---|
| `PLAYING` | `turn` (interactive: any active player for cantos, mazo, tapar, mostrar, pardon) | jugar (only `turn`), envido family if `_envido_open`, truco or its raise if the team holds the right, mazo, nos vamos (redonda), seña (strict, once per turn); interactive adds out-of-turn cantos, tapar, mostrar, pedir/aceptar perdón | `ANSWERING` (canto in turn), `PLAYING` (next player / next ronda), `FINISHED` |
| `ANSWERING` | the first active rival after the chanter (interactive: any active rival) | quiero, no quiero; envido pending: a higher envido; truco pending: retruco/vale cuatro (raise = accept), envido if still open (envido first, 13.6); objetar if irregular (12.3); mazo, nos vamos | `PLAYING`, `DECLARING` (interactive envido querido), `ANSWERING` (raise), `FINISHED` |
| `DECLARING` (interactive) | `declaration.current` | declarar N, son buenas (once someone declared) | `PLAYING` (envido scored, reclamos open) |
| `FINISHED` | nobody, except reclamos | reclamar (interactive, until the next cut / duelo start) | — |

Cross-cutting: out-of-turn cantos lapse when a card is played (13.5); 30 points ends the
contest at once (11.10); a team leaving entirely folds pending cantos (8.5).

## Above it

- `PicaPicaHand`: `DUEL(i)` for i = 1..3, then `FINISHED`. Players of later duelos may
  concede (mazo, 15.5); reclamos on duelo i stay open until duelo i+1 starts (15.9).
- `Match`: `DEALING` → `IN_HAND` → `CLAIMS_OPEN` (interactive, until the next deal) →
  `DEALING` …, or `OVER` (sporting or administrative result) → `HOMOLOGATED`.
- `GameSession` / UI prompt (`frontend/src/lib/game.ts` `prompt`) should read the phase
  instead of re-deriving it from `actions`.

## Status

1. Done: `Phase` enum, table tests for both modes (`tests/truco/test_phases.py`).
2. Done: `_moves_playing`, `_moves_answering`, `_moves_declaring` (+ `_answers`, `_pardon`,
   `_anytime`), mode differences as explicit branches.
3. Done: `phase` is stored; `_enter(phase)` replaces `finished` / `declaration` / `_blocking()`
   checks (`finished` is now a property).
4. Done: `PicaPicaHand.phase` (the current duelo's), derived from its few flags, which are
   simple enough not to need explicit transitions. `GameView` carries `phase`; the UI prompt
   and the bot read it.
