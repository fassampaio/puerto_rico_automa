"""Dados estáticos do jogo base (3 a 5 jogadores)."""

from __future__ import annotations

from enum import IntEnum
from typing import NamedTuple


class Good(IntEnum):
    CORN = 0
    INDIGO = 1
    SUGAR = 2
    TOBACCO = 3
    COFFEE = 4


NUM_GOODS = 5
QUARRY = 5  # índice extra da pedreira nas contagens da ilha
NUM_TILE_TYPES = 6  # 5 plantações + pedreira

GOOD_NAMES = ("milho", "anil", "açúcar", "tabaco", "café")
TILE_NAMES = GOOD_NAMES + ("pedreira",)

GOOD_PRICE = (0, 1, 2, 3, 4)
GOOD_SUPPLY = (10, 11, 11, 9, 9)
PLANTATION_COUNT = (10, 12, 11, 9, 8)
QUARRY_COUNT = 8
ISLAND_SPACES = 12
CITY_SPACES = 12
TRADING_HOUSE_SIZE = 4
NUM_SHIPS = 3

# Factory: bônus em dobrões por nº de tipos produzidos (índice = tipos)
FACTORY_BONUS = (0, 0, 1, 2, 3, 5)


class Role(IntEnum):
    SETTLER = 0
    MAYOR = 1
    BUILDER = 2
    CRAFTSMAN = 3
    TRADER = 4
    CAPTAIN = 5
    PROSPECTOR = 6
    PROSPECTOR_2 = 7


NUM_ROLES = 8
ROLE_NAMES = (
    "Colono",
    "Prefeito",
    "Construtor",
    "Artesão",
    "Comerciante",
    "Capitão",
    "Garimpeiro",
    "Garimpeiro 2",
)


class Building(IntEnum):
    SMALL_INDIGO_PLANT = 0
    SMALL_SUGAR_MILL = 1
    SMALL_MARKET = 2
    HACIENDA = 3
    CONSTRUCTION_HUT = 4
    SMALL_WAREHOUSE = 5
    LARGE_INDIGO_PLANT = 6
    LARGE_SUGAR_MILL = 7
    HOSPICE = 8
    OFFICE = 9
    LARGE_MARKET = 10
    LARGE_WAREHOUSE = 11
    TOBACCO_STORAGE = 12
    COFFEE_ROASTER = 13
    FACTORY = 14
    UNIVERSITY = 15
    HARBOR = 16
    WHARF = 17
    GUILD_HALL = 18
    RESIDENCE = 19
    FORTRESS = 20
    CUSTOMS_HOUSE = 21
    CITY_HALL = 22


class BuildingInfo(NamedTuple):
    name: str
    cost: int
    vp: int
    column: int  # coluna 1-4; também é o desconto máximo por pedreiras
    slots: int  # círculos para colonos
    copies: int
    size: int  # espaços ocupados na cidade
    produces: int  # Good produzido, ou -1 para prédios violeta
    large_production: bool  # conta 2 PV no Guild Hall


_V = -1  # violeta
BUILDINGS: tuple[BuildingInfo, ...] = (
    BuildingInfo("Small Indigo Plant", 1, 1, 1, 1, 4, 1, Good.INDIGO, False),
    BuildingInfo("Small Sugar Mill", 2, 1, 1, 1, 4, 1, Good.SUGAR, False),
    BuildingInfo("Small Market", 1, 1, 1, 1, 2, 1, _V, False),
    BuildingInfo("Hacienda", 2, 1, 1, 1, 2, 1, _V, False),
    BuildingInfo("Construction Hut", 2, 1, 1, 1, 2, 1, _V, False),
    BuildingInfo("Small Warehouse", 3, 1, 1, 1, 2, 1, _V, False),
    BuildingInfo("Large Indigo Plant", 3, 2, 2, 3, 3, 1, Good.INDIGO, True),
    BuildingInfo("Large Sugar Mill", 4, 2, 2, 3, 3, 1, Good.SUGAR, True),
    BuildingInfo("Hospice", 4, 2, 2, 1, 2, 1, _V, False),
    BuildingInfo("Office", 5, 2, 2, 1, 2, 1, _V, False),
    BuildingInfo("Large Market", 5, 2, 2, 1, 2, 1, _V, False),
    BuildingInfo("Large Warehouse", 6, 2, 2, 1, 2, 1, _V, False),
    BuildingInfo("Tobacco Storage", 5, 3, 3, 3, 3, 1, Good.TOBACCO, True),
    BuildingInfo("Coffee Roaster", 6, 3, 3, 2, 3, 1, Good.COFFEE, True),
    BuildingInfo("Factory", 7, 3, 3, 1, 2, 1, _V, False),
    BuildingInfo("University", 8, 3, 3, 1, 2, 1, _V, False),
    BuildingInfo("Harbor", 8, 3, 3, 1, 2, 1, _V, False),
    BuildingInfo("Wharf", 9, 3, 3, 1, 2, 1, _V, False),
    BuildingInfo("Guild Hall", 10, 4, 4, 1, 1, 2, _V, False),
    BuildingInfo("Residence", 10, 4, 4, 1, 1, 2, _V, False),
    BuildingInfo("Fortress", 10, 4, 4, 1, 1, 2, _V, False),
    BuildingInfo("Customs House", 10, 4, 4, 1, 1, 2, _V, False),
    BuildingInfo("City Hall", 10, 4, 4, 1, 1, 2, _V, False),
)
NUM_BUILDINGS = len(BUILDINGS)
assert NUM_BUILDINGS == len(Building)

BUILDING_SLOTS = tuple(b.slots for b in BUILDINGS)
BUILDING_SIZE = tuple(b.size for b in BUILDINGS)
PRODUCTION_BUILDINGS = tuple(i for i, b in enumerate(BUILDINGS) if b.produces >= 0)
VIOLET_BUILDINGS = tuple(i for i, b in enumerate(BUILDINGS) if b.produces < 0)
# prédios de produção por bem (milho não precisa de prédio)
PRODUCTION_BY_GOOD = tuple(
    tuple(i for i, b in enumerate(BUILDINGS) if b.produces == g) for g in range(NUM_GOODS)
)


class SetupInfo(NamedTuple):
    money: int
    vp_chips: int
    colonists: int  # na reserva, sem contar os do navio
    ship_colonists: int
    cargo_ships: tuple[int, int, int]
    roles: tuple[Role, ...]
    start_plantations: tuple[Good, ...]  # por assento, a partir do governador


_BASE_ROLES = (
    Role.SETTLER,
    Role.MAYOR,
    Role.BUILDER,
    Role.CRAFTSMAN,
    Role.TRADER,
    Role.CAPTAIN,
)
_I, _C = Good.INDIGO, Good.CORN

SETUP: dict[int, SetupInfo] = {
    3: SetupInfo(2, 75, 55, 3, (4, 5, 6), _BASE_ROLES, (_I, _I, _C)),
    4: SetupInfo(3, 100, 75, 4, (5, 6, 7), _BASE_ROLES + (Role.PROSPECTOR,), (_I, _I, _C, _C)),
    5: SetupInfo(
        4,
        122,
        95,
        5,
        (6, 7, 8),
        _BASE_ROLES + (Role.PROSPECTOR, Role.PROSPECTOR_2),
        (_I, _I, _I, _C, _C),
    ),
}
