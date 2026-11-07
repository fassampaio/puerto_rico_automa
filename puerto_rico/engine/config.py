"""Rules configuration for a game."""

from __future__ import annotations

from dataclasses import dataclass

from .data import SETUP


@dataclass(frozen=True)
class RulesConfig:
    num_players: int = 4
    # Room for future variants (expansions, alternative buildings, hidden VP...)

    def __post_init__(self) -> None:
        if self.num_players not in SETUP:
            raise ValueError(f"num_players must be 3, 4 or 5 (got {self.num_players})")
