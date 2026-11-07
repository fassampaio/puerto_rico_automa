from helpers import fresh, give_building, set_island

from puerto_rico.engine import Building as B
from puerto_rico.engine import score_breakdown, winners
from puerto_rico.engine.scoring import bonus_points, building_points


def test_guild_hall():
    s = fresh()
    give_building(s, 0, B.GUILD_HALL)
    give_building(s, 0, B.SMALL_INDIGO_PLANT, manned=0)
    give_building(s, 0, B.LARGE_SUGAR_MILL, manned=0)
    give_building(s, 0, B.TOBACCO_STORAGE, manned=0)
    assert bonus_points(s, 0) == 1 + 2 + 2
    assert building_points(s, 0) == 4 + 1 + 2 + 3


def test_large_building_bonus_requires_colonist():
    s = fresh()
    give_building(s, 0, B.GUILD_HALL, manned=0)
    give_building(s, 0, B.SMALL_INDIGO_PLANT, manned=0)
    assert bonus_points(s, 0) == 0


def test_residence():
    s = fresh()
    give_building(s, 1, B.RESIDENCE)
    set_island(s, 1, [4, 3, 3, 0, 0, 0])
    assert bonus_points(s, 1) == 5
    set_island(s, 1, [4, 4, 4, 0, 0, 0])
    assert bonus_points(s, 1) == 7
    set_island(s, 1, [3, 3, 2, 0, 0, 0])
    assert bonus_points(s, 1) == 4


def test_fortress_customs_city_hall():
    s = fresh()
    give_building(s, 2, B.FORTRESS)  # 1 colono
    s.san_juan[2] = 6
    assert bonus_points(s, 2) == 7 // 3

    give_building(s, 3, B.CUSTOMS_HOUSE)
    s.vp[3] = 9
    assert bonus_points(s, 3) == 2

    give_building(s, 0, B.CITY_HALL)
    give_building(s, 0, B.SMALL_MARKET, manned=0)
    give_building(s, 0, B.SMALL_INDIGO_PLANT, manned=0)  # produção não conta
    assert bonus_points(s, 0) == 2


def test_breakdown_and_tiebreak():
    s = fresh()
    s.vp = [5, 5, 0, 0]
    s.money = [1, 2, 0, 0]
    assert score_breakdown(s, 0)["total"] == 5
    assert winners(s) == [1]
