"""Bot style profiles and difficulty levels."""

from __future__ import annotations

from dataclasses import dataclass

from ..engine.data import Building as B


@dataclass(frozen=True)
class Profile:
    """Style weights used by the evaluation function (1.0 = neutral)."""

    name: str
    ship: float = 1.0  # value of turning barrels into VP (shipping)
    trade: float = 1.0  # value of turning barrels into money (trading)
    build: float = 1.0  # value of buildings and quarries
    production: float = 1.0  # value of production capacity
    aggression: float = 0.6  # how much opponents' gains count against
    favorites: tuple[int, ...] = ()  # preferred buildings
    favorite_bonus: float = 0.0  # bonus per preferred building owned


PROFILES: dict[str, Profile] = {
    p.name: p
    for p in (
        Profile("balanced"),
        Profile(
            "shipper",
            ship=1.4,
            trade=0.7,
            build=0.9,
            favorites=(B.HARBOR, B.WHARF, B.SMALL_WAREHOUSE, B.LARGE_WAREHOUSE),
            favorite_bonus=0.7,
        ),
        Profile(
            "builder",
            ship=0.8,
            build=1.3,
            production=1.1,
            favorites=(B.UNIVERSITY, B.FACTORY, B.CONSTRUCTION_HUT, B.GUILD_HALL, B.CITY_HALL),
            favorite_bonus=0.7,
        ),
        Profile(
            "trader",
            ship=0.85,
            trade=1.3,
            favorites=(B.SMALL_MARKET, B.LARGE_MARKET, B.OFFICE, B.COFFEE_ROASTER),
            favorite_bonus=0.7,
        ),
    )
}


@dataclass(frozen=True)
class Level:
    name: str
    temperature: float  # 0 = always the best move; higher = more random
    lookahead: bool  # simulate the whole phase when choosing roles
    mayor_planning: bool  # plan the full colonist allocation in the Mayor phase


LEVELS: dict[str, Level] = {
    lv.name: lv
    for lv in (
        Level("easy", temperature=1.5, lookahead=False, mayor_planning=False),
        Level("medium", temperature=0.8, lookahead=True, mayor_planning=False),
        Level("hard", temperature=0.0, lookahead=True, mayor_planning=True),
    )
}


def get_profile(name: str) -> Profile:
    if name not in PROFILES:
        raise ValueError(f"unknown profile '{name}'. Available: {', '.join(PROFILES)}")
    return PROFILES[name]


def get_level(name: str) -> Level:
    if name not in LEVELS:
        raise ValueError(f"unknown level '{name}'. Available: {', '.join(LEVELS)}")
    return LEVELS[name]
