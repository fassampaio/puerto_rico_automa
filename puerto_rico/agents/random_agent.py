"""Agente que escolhe jogadas ao acaso (testes e linha de base)."""

from __future__ import annotations

import random

from ..engine import Action, GameState


class RandomAgent:
    def __init__(self, seed: int | None = None, name: str = "random") -> None:
        self.rng = random.Random(seed)
        self.name = name

    def choose(self, state: GameState, actions: list[Action]) -> Action:
        return self.rng.choice(actions)
