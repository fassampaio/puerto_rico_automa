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
    k = a.kind
    if k == ActionKind.CHOOSE_ROLE:
        return f"Escolher {ROLE_NAMES[a.a]}"
    if k == ActionKind.PASS:
        return "Passar"
    if k == ActionKind.HACIENDA:
        return "Usar Hacienda (plantação extra do monte)"
    if k == ActionKind.SETTLE:
        return f"Pegar plantação de {GOOD_NAMES[a.a]}"
    if k == ActionKind.QUARRY:
        return "Pegar quarry"
    if k == ActionKind.PLACE:
        return f"Colocar colono em {place_target_name(a.a)}"
    if k == ActionKind.BUILD:
        return f"Construir {BUILDINGS[a.a].name}"
    if k == ActionKind.CRAFT_BONUS:
        return f"Privilégio do Artesão: +1 {GOOD_NAMES[a.a]}"
    if k == ActionKind.SELL:
        return f"Vender {GOOD_NAMES[a.a]}"
    if k == ActionKind.SHIP:
        dest = "Wharf" if a.b == WHARF else f"navio {a.b + 1}"
        return f"Embarcar {GOOD_NAMES[a.a]} no {dest}"
    if k == ActionKind.STORE:
        kept = [GOOD_NAMES[g] for g in range(NUM_GOODS) if a.a >> g & 1]
        parts = []
        if kept:
            parts.append("armazéns: " + ", ".join(kept))
        if a.b >= 0:
            parts.append(f"1 barril de {GOOD_NAMES[a.b]}")
        return "Guardar " + ("; ".join(parts) if parts else "nada")
    return repr(a)
