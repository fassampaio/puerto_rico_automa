"""Common interface for agents (bots and humans)."""

from __future__ import annotations

from typing import Protocol

from ..engine import Action, GameState


class Agent(Protocol):
    name: str

    def choose(self, state: GameState, actions: list[Action]) -> Action:
        """Receive the player's view (view_for) and the legal actions; return one of them."""
        ...
