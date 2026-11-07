"""Heuristic state evaluation: estimated final points for each player.

value = current points (VP chips + buildings + bonus)
      + money converted to VP (worth more early on)
      + stored barrels
      + future production capacity x remaining rounds
      + violet building utility x remaining rounds
      + profile preferences

When the game is over, the value is exactly the final score.
"""

from __future__ import annotations

from ..engine import GameState
from ..engine.data import (
    BUILDING_SLOTS,
    CITY_SPACES,
    FACTORY_BONUS,
    GOOD_PRICE,
    NUM_GOODS,
    PRODUCTION_BY_GOOD,
    QUARRY,
    SETUP,
)
from ..engine.data import Building as B
from ..engine.scoring import building_points, score
from .profiles import Profile

TYPICAL_ROUNDS = 15.0
_LARGE = (B.GUILD_HALL, B.RESIDENCE, B.FORTRESS, B.CUSTOMS_HOUSE, B.CITY_HALL)

# per-round utility (in VP) of violet buildings: (building, profile group, value)
_UTILITY = (
    (B.SMALL_MARKET, "trade", 0.10),
    (B.LARGE_MARKET, "trade", 0.18),
    (B.OFFICE, "trade", 0.08),
    (B.HACIENDA, "production", 0.12),
    (B.HOSPICE, "production", 0.12),
    (B.CONSTRUCTION_HUT, "build", 0.06),
    (B.UNIVERSITY, "build", 0.15),
    (B.SMALL_WAREHOUSE, "ship", 0.10),
    (B.LARGE_WAREHOUSE, "ship", 0.18),
    (B.HARBOR, "ship", 0.40),
    (B.WHARF, "ship", 0.45),
)
UNMANNED_FACTOR = 0.6  # unmanned building/tile: should get a colonist later


def progress(s: GameState) -> float:
    """Estimated fraction of the game already played (0 to 1)."""
    setup = SETUP[s.num_players]
    t_vp = 1.0 - s.vp_supply / setup.vp_chips
    t_col = 1.0 - s.colonist_supply / setup.colonists
    t_city = max(s.city_used(p) for p in range(s.num_players)) / CITY_SPACES
    return min(1.0, max(t_vp, t_col, t_city, 0.0))


def remaining_rounds(s: GameState) -> float:
    if s.is_terminal:
        return 0.0
    if s.end_triggered:
        return 0.3
    return TYPICAL_ROUNDS * (1.0 - progress(s)) + 0.5


def evaluate(s: GameState, p: int, profile: Profile, rounds: float | None = None) -> float:
    R = remaining_rounds(s) if rounds is None else rounds
    value = float(score(s, p))
    if R <= 0.0:
        return value

    frac = min(1.0, R / TYPICAL_ROUNDS)
    # money turns into buildings: it stays valuable until the last rounds
    money_rate = 0.20 + 0.50 * min(1.0, R / 8.0)
    value += s.money[p] * money_rate
    # the "builder" style values buildings (not hoarded money)
    value += (profile.build - 1.0) * building_points(s, p) * frac

    # value of one barrel of each good (shipping + selling)
    barrel = [
        0.6 * profile.ship + 0.7 * profile.trade * GOOD_PRICE[g] * money_rate
        for g in range(NUM_GOODS)
    ]
    goods = s.goods[p]
    value += sum(goods[g] * barrel[g] for g in range(NUM_GOODS))

    # production: current and potential (plantations + buildings not yet manned)
    isl, im, row, cm = s.island[p], s.island_manned[p], s.city[p], s.city_manned[p]
    prod_rate = 0.35 * R * profile.production
    kinds = 0
    for g in range(NUM_GOODS):
        prod = s.production(p, g)
        if prod:
            kinds += 1
        if g == 0:
            pot = isl[0]
        else:
            cap = sum(BUILDING_SLOTS[b] for b in PRODUCTION_BY_GOOD[g] if row[b])
            pot = min(isl[g], cap)
        value += prod_rate * barrel[g] * (prod + 0.35 * max(0, pot - prod))

    # island tiles and quarries
    value += 0.03 * R * sum(isl)
    quarry_value = money_rate * R * 0.3 * profile.build
    manned_q = min(im[QUARRY], 4)
    value += quarry_value * (manned_q + 0.4 * max(0, min(isl[QUARRY], 4) - manned_q))

    # violet buildings
    weights = {
        "trade": profile.trade,
        "ship": profile.ship,
        "build": profile.build,
        "production": profile.production,
    }
    for b, group, per_round in _UTILITY:
        if row[b]:
            value += per_round * R * weights[group] * (1.0 if cm[b] else UNMANNED_FACTOR)
    if row[B.FACTORY]:
        bonus = FACTORY_BONUS[kinds] * money_rate * 0.3 * R
        value += bonus if cm[B.FACTORY] else UNMANNED_FACTOR * bonus
    for b in _LARGE:  # an unmanned large building may still score its bonus
        if row[b] and not cm[b]:
            value += 2.0
    value += 0.05 * R * s.san_juan[p]

    if profile.favorite_bonus:
        value += profile.favorite_bonus * frac * sum(1 for b in profile.favorites if row[b])
    return value


def evaluate_all(s: GameState, profile: Profile) -> list[float]:
    R = remaining_rounds(s)
    return [evaluate(s, p, profile, R) for p in range(s.num_players)]


def relative_value(values: list[float], p: int, aggression: float) -> float:
    """Value of player p minus part of the opponents' average."""
    others = [v for q, v in enumerate(values) if q != p]
    return values[p] - aggression * (sum(others) / len(others))
