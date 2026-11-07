"""Interface comum dos agentes (bots e humano)."""

from __future__ import annotations

from typing import Protocol

from ..engine import Action, GameState


class Agent(Protocol):
    name: str

    def choose(self, state: GameState, actions: list[Action]) -> Action:
        """Recebe a visão do jogador (view_for) e as jogadas válidas; devolve uma delas."""
        ...
