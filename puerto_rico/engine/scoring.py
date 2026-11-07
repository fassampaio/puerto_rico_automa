"""Pontuação final e desempate."""

from __future__ import annotations

from .data import BUILDINGS, NUM_BUILDINGS, PRODUCTION_BUILDINGS, VIOLET_BUILDINGS
from .data import Building as B
from .state import GameState


def building_points(s: GameState, p: int) -> int:
    row = s.city[p]
    return sum(BUILDINGS[b].vp for b in range(NUM_BUILDINGS) if row[b])


def bonus_points(s: GameState, p: int) -> int:
    """Bônus dos prédios grandes (só contam se ocupados)."""
    row = s.city[p]
    pts = 0
    if s.is_manned(p, B.GUILD_HALL):
        pts += sum(
            2 if BUILDINGS[b].large_production else 1 for b in PRODUCTION_BUILDINGS if row[b]
        )
    if s.is_manned(p, B.RESIDENCE):
        used = s.island_used(p)
        pts += 4 if used <= 9 else used - 5  # 10→5, 11→6, 12→7
    if s.is_manned(p, B.FORTRESS):
        pts += s.total_colonists(p) // 3
    if s.is_manned(p, B.CUSTOMS_HOUSE):
        pts += s.vp[p] // 4
    if s.is_manned(p, B.CITY_HALL):
        pts += sum(1 for b in VIOLET_BUILDINGS if row[b])
    return pts


def score_breakdown(s: GameState, p: int) -> dict[str, int]:
    chips, bld, bonus = s.vp[p], building_points(s, p), bonus_points(s, p)
    return {"fichas": chips, "predios": bld, "bonus": bonus, "total": chips + bld + bonus}


def score(s: GameState, p: int) -> int:
    return s.vp[p] + building_points(s, p) + bonus_points(s, p)


def final_scores(s: GameState) -> list[int]:
    return [score(s, p) for p in range(s.num_players)]


def tiebreak(s: GameState, p: int) -> int:
    return s.money[p] + sum(s.goods[p])


def ranking(s: GameState) -> list[int]:
    """Jogadores do primeiro ao último colocado."""
    return sorted(
        range(s.num_players), key=lambda p: (score(s, p), tiebreak(s, p)), reverse=True
    )


def winners(s: GameState) -> list[int]:
    keys = [(score(s, p), tiebreak(s, p)) for p in range(s.num_players)]
    best = max(keys)
    return [p for p, k in enumerate(keys) if k == best]
