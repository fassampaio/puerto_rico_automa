"""Ações atômicas do jogo."""

from __future__ import annotations

from enum import IntEnum
from typing import NamedTuple

from .data import BUILDINGS, GOOD_NAMES, NUM_GOODS, NUM_TILE_TYPES, ROLE_NAMES, TILE_NAMES


class ActionKind(IntEnum):
    CHOOSE_ROLE = 0  # a = Role
    PASS = 1
    HACIENDA = 2  # pegar plantação extra do monte
    SETTLE = 3  # a = tipo da plantação visível
    QUARRY = 4
    PLACE = 5  # a = alvo (ver place_target)
    BUILD = 6  # a = Building
    CRAFT_BONUS = 7  # a = Good
    SELL = 8  # a = Good
    SHIP = 9  # a = Good, b = navio (0-2) ou WHARF
    STORE = 10  # a = máscara de bens nos armazéns, b = bem do barril avulso (-1 = nenhum)


WHARF = 3
# Alvos do Prefeito: 0-5 = tipos de lote da ilha; 6+ = prédios
PLACE_BUILDING_OFFSET = NUM_TILE_TYPES


class Action(NamedTuple):
    kind: int
    a: int = -1
    b: int = -1

    def __str__(self) -> str:
        return describe(self)

    def to_json(self) -> list[int]:
        return [int(self.kind), self.a, self.b]

    @staticmethod
    def from_json(data: list[int]) -> Action:
        return Action(ActionKind(data[0]), data[1], data[2])


PASS = Action(ActionKind.PASS)


def place_target_name(code: int) -> str:
    if code < PLACE_BUILDING_OFFSET:
        return TILE_NAMES[code]
    return BUILDINGS[code - PLACE_BUILDING_OFFSET].name


def describe(a: Action) -> str:
    """Descrição da ação em inglês (termos do jogo)."""
    k = a.kind
    if k == ActionKind.CHOOSE_ROLE:
        return f"Choose {ROLE_NAMES[a.a]}"
    if k == ActionKind.PASS:
        return "Pass"
    if k == ActionKind.HACIENDA:
        return "Use Hacienda (extra plantation from the stack)"
    if k == ActionKind.SETTLE:
        return f"Take {GOOD_NAMES[a.a]} plantation"
    if k == ActionKind.QUARRY:
        return "Take quarry"
    if k == ActionKind.PLACE:
        return f"Place colonist on {place_target_name(a.a)}"
    if k == ActionKind.BUILD:
        return f"Build {BUILDINGS[a.a].name}"
    if k == ActionKind.CRAFT_BONUS:
        return f"Craftsman privilege: +1 {GOOD_NAMES[a.a]}"
    if k == ActionKind.SELL:
        return f"Sell {GOOD_NAMES[a.a]}"
    if k == ActionKind.SHIP:
        dest = "the Wharf" if a.b == WHARF else f"ship {a.b + 1}"
        return f"Ship {GOOD_NAMES[a.a]} on {dest}"
    if k == ActionKind.STORE:
        kept = [GOOD_NAMES[g] for g in range(NUM_GOODS) if a.a >> g & 1]
        parts = []
        if kept:
            parts.append("warehouses: " + ", ".join(kept))
        if a.b >= 0:
            parts.append(f"1 barrel of {GOOD_NAMES[a.b]}")
        return "Store " + ("; ".join(parts) if parts else "nothing")
    return repr(a)
