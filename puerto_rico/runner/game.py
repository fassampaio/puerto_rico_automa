"""Playing a game between agents and replaying it from a record."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from ..agents.base import Agent
from ..engine import (
    Action,
    GameState,
    final_scores,
    legal_actions,
    new_game,
    step,
    view_for,
    winners,
)


@dataclass
class GameResult:
    seed: int
    num_players: int
    agent_names: list[str]
    actions: list[Action] = field(repr=False)
    final_state: GameState = field(repr=False)
    scores: list[int]
    winners: list[int]
    rounds: int


def play_game(agents: Sequence[Agent], seed: int = 0, max_decisions: int = 20_000) -> GameResult:
    n = len(agents)
    s = new_game(n, seed)
    actions: list[Action] = []
    while not s.is_terminal:
        p = s.actor
        action = agents[p].choose(view_for(s, p), legal_actions(s))
        step(s, action)
        actions.append(action)
        if len(actions) > max_decisions:
            raise RuntimeError("game exceeded the decision limit")
    return GameResult(
        seed=seed,
        num_players=n,
        agent_names=[a.name for a in agents],
        actions=actions,
        final_state=s,
        scores=final_scores(s),
        winners=winners(s),
        rounds=s.round + 1,
    )


def replay(num_players: int, seed: int, actions: Sequence[Action]) -> GameState:
    s = new_game(num_players, seed)
    for a in actions:
        step(s, a)
    return s
