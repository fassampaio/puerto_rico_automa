"""Planning the colonist allocation in the Mayor phase.

Placing one colonist at a time greedily fails when the value lies in pairs
(plantation + production building of the same good). The planner considers
single moves (1 colonist) and pairs (plantation + building) and, in thorough
mode, tries every first move followed by a greedy completion.
"""

from __future__ import annotations

from ..engine import GameState
from ..engine.actions import PLACE_BUILDING_OFFSET as OFF
from ..engine.data import NUM_GOODS, PRODUCTION_BY_GOOD
from .evaluation import evaluate, remaining_rounds
from .profiles import Profile


def _add(w: GameState, p: int, code: int, delta: int) -> None:
    if code < OFF:
        w.island_manned[p][code] += delta
    else:
        w.city_manned[p][code - OFF] += delta
    w.san_juan[p] -= delta


def _moves(free: list[int], last: int, pool: int) -> list[tuple[int, ...]]:
    moves: list[tuple[int, ...]] = [(c,) for c in range(last, len(free)) if free[c] > 0]
    if pool >= 2:
        for g in range(1, NUM_GOODS):  # corn needs no building
            if g < last or free[g] <= 0:
                continue
            for b in PRODUCTION_BY_GOOD[g]:
                cb = OFF + b
                if cb >= last and free[cb] > 0:
                    moves.append((g, cb))
    return moves


def _apply_move(w: GameState, p: int, move: tuple[int, ...], free: list[int], d: int) -> None:
    for c in move:
        _add(w, p, c, d)
        free[c] -= d


def _greedy(
    w: GameState, p: int, profile: Profile, R: float, free: list[int], last: int, pool: int
) -> list[int]:
    """Complete the allocation greedily (by absolute gain); mutates w and free."""
    placed: list[int] = []
    base = evaluate(w, p, profile, R)
    while pool > 0:
        best_gain, best_move = None, None
        for move in _moves(free, last, pool):
            _apply_move(w, p, move, free, +1)
            gain = evaluate(w, p, profile, R) - base
            _apply_move(w, p, move, free, -1)
            if best_gain is None or gain > best_gain:
                best_gain, best_move = gain, move
        assert best_move is not None
        _apply_move(w, p, best_move, free, +1)
        placed.extend(best_move)
        pool -= len(best_move)
        base += best_gain
    return placed


def plan_placements(s: GameState, p: int, profile: Profile, thorough: bool = True) -> list[int]:
    """List of targets (Mayor codes) for the colonists still to be placed."""
    R = remaining_rounds(s)
    pool, last = s.san_juan[p], s.mayor_last
    if not thorough:
        return _greedy(s.clone(), p, profile, R, s.free_slots(p), last, pool)

    best_value, best_plan = None, None
    base_free = s.free_slots(p)
    for first in _moves(base_free, last, pool):
        w = s.clone()
        free = base_free[:]
        _apply_move(w, p, first, free, +1)
        rest = _greedy(w, p, profile, R, free, last, pool - len(first))
        value = evaluate(w, p, profile, R)
        if best_value is None or value > best_value:
            best_value, best_plan = value, list(first) + rest
    assert best_plan is not None
    return best_plan
