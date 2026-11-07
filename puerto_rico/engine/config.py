"""Configuração de regras de uma partida."""

from __future__ import annotations

from dataclasses import dataclass

from .data import SETUP


@dataclass(frozen=True)
class RulesConfig:
    num_players: int = 4
    # Espaço para variantes futuras (expansões, prédios alternativos, PV ocultos...)

    def __post_init__(self) -> None:
        if self.num_players not in SETUP:
            raise ValueError(f"num_players deve ser 3, 4 ou 5 (recebido {self.num_players})")
