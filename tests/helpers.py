"""Helpers to set up specific situations in tests."""

from __future__ import annotations

from puerto_rico.engine import Action, ActionKind, GameState, legal_actions, new_game, step
from puerto_rico.engine.data import BUILDINGS, NUM_GOODS, NUM_TILE_TYPES


def fresh(n: int = 4, seed: int = 0) -> GameState:
    return new_game(n, seed)


def give_building(s: GameState, p: int, b: int, manned: int | None = None) -> None:
    """Give the player a building; fully manned by default (colonists from the supply)."""
    s.city[p][b] = 1
    s.building_supply[b] -= 1
    count = BUILDINGS[b].slots if manned is None else manned
    s.city_manned[p][b] = count
    s.colonist_supply -= count
    s.legal_cache = None


def set_island(s: GameState, p: int, tiles: list[int], manned: list[int] | None = None) -> None:
    """Replace the player's island (6 counts: 5 plantation types + quarry)."""
    assert len(tiles) == NUM_TILE_TYPES
    s.island[p] = list(tiles)
    s.island_manned[p] = list(manned) if manned is not None else [0] * NUM_TILE_TYPES
    s.legal_cache = None


def give_goods(s: GameState, p: int, goods: list[int]) -> None:
    assert len(goods) == NUM_GOODS
    for g, amount in enumerate(goods):
        s.goods[p][g] += amount
        s.goods_supply[g] -= amount
    s.legal_cache = None


def choose(s: GameState, role: int) -> None:
    step(s, Action(ActionKind.CHOOSE_ROLE, role))


def finish_round(s: GameState) -> None:
    """Play the first legal option until the current round ends."""
    start = s.round
    while not s.is_terminal and s.round == start:
        step(s, legal_actions(s)[0])


def legal_set(s: GameState) -> set[Action]:
    return set(legal_actions(s))
