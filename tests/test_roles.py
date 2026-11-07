from helpers import choose, finish_round, fresh, give_building, give_goods, legal_set, set_island

from puerto_rico.engine import (
    PASS,
    WHARF,
    Action,
    Good,
    Phase,
    Role,
    building_cost,
    legal_actions,
    step,
)
from puerto_rico.engine import (
    ActionKind as K,
)
from puerto_rico.engine import (
    Building as B,
)
from puerto_rico.engine.actions import PLACE_BUILDING_OFFSET as OFF
from puerto_rico.engine.data import QUARRY

C, I, S, T, F = Good.CORN, Good.INDIGO, Good.SUGAR, Good.TOBACCO, Good.COFFEE


# ---------------------------------------------------------------- Colono
def test_settler_quarry_privilege_only_for_chooser():
    s = fresh()
    choose(s, Role.SETTLER)
    assert s.phase == Phase.SETTLER and s.actor == 0
    assert Action(K.QUARRY) in legal_actions(s)
    step(s, Action(K.QUARRY))
    assert s.island[0][QUARRY] == 1 and s.quarry_supply == 7
    assert s.actor == 1
    assert Action(K.QUARRY) not in legal_actions(s)


def test_construction_hut_allows_quarry():
    s = fresh()
    give_building(s, 1, B.CONSTRUCTION_HUT)
    choose(s, Role.SETTLER)
    step(s, PASS)
    assert s.actor == 1 and Action(K.QUARRY) in legal_actions(s)


def test_hospice_mans_new_plantation_and_faceup_refills():
    s = fresh()
    give_building(s, 1, B.HOSPICE)
    supply = s.colonist_supply
    choose(s, Role.SETTLER)
    step(s, Action(K.QUARRY))
    t = s.faceup[0]
    step(s, Action(K.SETTLE, t))
    assert s.island_manned[1][t] == 1
    assert s.colonist_supply == supply - 1
    finish_round(s)  # demais passam / jogam
    assert len(s.faceup) == 5


def test_faceup_discarded_and_redrawn_after_settler():
    s = fresh()
    choose(s, Role.SETTLER)
    step(s, Action(K.QUARRY))
    step(s, Action(K.SETTLE, s.faceup[0]))
    step(s, PASS)
    step(s, PASS)
    assert s.phase == Phase.ROLE_SELECTION
    assert len(s.plantation_discard) == 4
    assert len(s.faceup) == 5


def test_hacienda_draws_from_stack_before_normal_choice():
    s = fresh()
    give_building(s, 0, B.HACIENDA)
    choose(s, Role.SETTLER)
    assert s.phase == Phase.SETTLER_HACIENDA
    top = s.plantation_stack[-1]
    before = s.island[0][top]
    step(s, Action(K.HACIENDA))
    assert s.island[0][top] == before + 1
    assert s.phase == Phase.SETTLER and s.actor == 0


# ---------------------------------------------------------------- Prefeito
def test_mayor_privilege_distribution_and_refill():
    s = fresh()  # navio com 4, reserva 75
    choose(s, Role.MAYOR)
    # tudo automático: cada um ocupa sua única plantação
    assert [s.island_manned[p][I] + s.island_manned[p][C] for p in range(4)] == [1, 1, 1, 1]
    assert s.san_juan == [1, 0, 0, 0]
    assert s.colonist_ship == 4  # max(4 jogadores, 0 círculos vazios)
    assert s.colonist_supply == 75 - 1 - 4


def test_mayor_canonical_placement_and_choice():
    s = fresh()
    give_building(s, 0, B.SMALL_MARKET, manned=0)
    give_building(s, 0, B.HACIENDA, manned=0)
    choose(s, Role.MAYOR)  # p0 recebe 2 colonos para 3 vagas
    assert s.phase == Phase.MAYOR and s.actor == 0
    market, hacienda = OFF + B.SMALL_MARKET, OFF + B.HACIENDA
    assert legal_set(s) == {Action(K.PLACE, I), Action(K.PLACE, market)}
    step(s, Action(K.PLACE, market))  # o resto vai para a Hacienda automaticamente
    assert s.city_manned[0][B.SMALL_MARKET] == 1
    assert s.city_manned[0][B.HACIENDA] == 1
    assert s.island_manned[0][I] == 0
    assert hacienda > market


def test_mayor_refill_counts_empty_building_circles():
    s = fresh()
    give_building(s, 1, B.LARGE_INDIGO_PLANT, manned=0)
    give_building(s, 2, B.LARGE_SUGAR_MILL, manned=0)
    supply_before = s.colonist_supply
    choose(s, Role.MAYOR)
    # p1 e p2 têm 1 colono cada para 4 vagas: escolhem onde
    while s.phase == Phase.MAYOR:
        step(s, legal_actions(s)[-1])  # coloca nos prédios
    empty = 6 - 2  # 6 círculos, 2 ocupados
    assert s.colonist_ship == max(4, empty)
    assert s.colonist_supply == supply_before - 1 - 4


def test_mayor_triggers_game_end_when_supply_short():
    s = fresh()
    s.colonist_supply = 2
    choose(s, Role.MAYOR)
    assert s.end_triggered and s.colonist_supply == 0 and s.colonist_ship == 1
    finish_round(s)
    assert s.is_terminal and s.round == 0


# ---------------------------------------------------------------- Construtor
def test_builder_costs_with_privilege_and_quarries():
    s = fresh()
    set_island(s, 0, [0, 1, 0, 0, 0, 1], [0, 0, 0, 0, 0, 1])
    s.quarry_supply -= 1
    choose(s, Role.BUILDER)
    assert building_cost(s, 0, B.LARGE_INDIGO_PLANT) == 1  # 3 - 1 privilégio - 1 pedreira
    acts = legal_set(s)
    assert Action(K.BUILD, B.TOBACCO_STORAGE) in acts  # 5 - 2 = 3
    assert Action(K.BUILD, B.COFFEE_ROASTER) not in acts  # 6 - 2 = 4 > 3
    assert Action(K.BUILD, B.GUILD_HALL) not in acts


def test_quarry_discount_capped_by_column():
    s = fresh()
    set_island(s, 1, [0, 0, 0, 0, 0, 3], [0, 0, 0, 0, 0, 3])
    assert building_cost(s, 1, B.SMALL_MARKET, privilege=False) == 0  # 1 - 1
    assert building_cost(s, 1, B.LARGE_INDIGO_PLANT, privilege=False) == 1  # 3 - 2
    assert building_cost(s, 1, B.WHARF, privilege=False) == 6  # 9 - 3


def test_cannot_build_same_building_twice():
    s = fresh()
    give_building(s, 0, B.SMALL_MARKET)
    choose(s, Role.BUILDER)
    assert Action(K.BUILD, B.SMALL_MARKET) not in legal_actions(s)


def test_university_mans_new_building():
    s = fresh()
    give_building(s, 0, B.UNIVERSITY)
    s.money[0] = 10
    choose(s, Role.BUILDER)
    step(s, Action(K.BUILD, B.SMALL_MARKET))
    assert s.city_manned[0][B.SMALL_MARKET] == 1


def test_filling_city_triggers_end_after_round():
    s = fresh()
    for b in (B.GUILD_HALL, B.RESIDENCE, B.FORTRESS, B.CUSTOMS_HOUSE, B.CITY_HALL, B.SMALL_MARKET):
        give_building(s, 0, b)
    assert s.city_used(0) == 11
    s.money[0] = 5
    choose(s, Role.BUILDER)
    step(s, Action(K.BUILD, B.HACIENDA))
    assert s.end_triggered
    finish_round(s)
    assert s.is_terminal and s.round == 0


# ---------------------------------------------------------------- Artesão
def test_craftsman_production_privilege_and_factory():
    s = fresh()
    set_island(s, 0, [2, 2, 1, 0, 0, 0], [2, 2, 1, 0, 0, 0])
    give_building(s, 0, B.SMALL_INDIGO_PLANT)
    give_building(s, 0, B.FACTORY)
    choose(s, Role.CRAFTSMAN)
    # milho 2 (sem prédio), anil min(2,1)=1, açúcar 0 (sem engenho)
    assert s.goods[0] == [2, 1, 0, 0, 0]
    assert s.money[0] == 3 + 1  # Factory com 2 tipos
    assert s.phase == Phase.CRAFT_BONUS
    assert legal_set(s) == {Action(K.CRAFT_BONUS, C), Action(K.CRAFT_BONUS, I)}
    step(s, Action(K.CRAFT_BONUS, C))
    assert s.goods[0] == [3, 1, 0, 0, 0]


def test_craftsman_shortage_served_in_order():
    s = fresh()
    set_island(s, 0, [2, 0, 0, 0, 0, 0], [2, 0, 0, 0, 0, 0])
    set_island(s, 1, [2, 1, 0, 0, 0, 0], [2, 0, 0, 0, 0, 0])
    s.goods_supply[C] = 3
    choose(s, Role.CRAFTSMAN)
    assert s.goods[0][C] == 2 and s.goods[1][C] == 1
    assert s.phase == Phase.ROLE_SELECTION  # reserva vazia: sem privilégio


# ---------------------------------------------------------------- Comerciante
def test_trader_privilege_and_no_duplicates():
    s = fresh()
    give_goods(s, 0, [0, 1, 0, 0, 0])
    give_goods(s, 1, [1, 1, 0, 0, 0])
    give_goods(s, 2, [0, 0, 1, 0, 0])
    choose(s, Role.TRADER)
    step(s, Action(K.SELL, I))
    assert s.money[0] == 3 + 2  # anil 1 + privilégio
    assert legal_set(s) == {Action(K.SELL, C), PASS}  # anil já está na casa
    step(s, Action(K.SELL, C))
    step(s, Action(K.SELL, S))
    assert s.money[1] == 3 and s.money[2] == 5
    assert s.trading_house == [I, C, S]
    assert s.phase == Phase.ROLE_SELECTION


def test_office_allows_duplicate_and_markets_add_bonus():
    s = fresh()
    give_goods(s, 0, [0, 1, 0, 0, 0])
    give_goods(s, 1, [0, 1, 0, 0, 0])
    give_building(s, 0, B.SMALL_MARKET)
    give_building(s, 0, B.LARGE_MARKET)
    give_building(s, 1, B.OFFICE)
    choose(s, Role.TRADER)
    step(s, Action(K.SELL, I))
    assert s.money[0] == 3 + 1 + 1 + 1 + 2
    assert Action(K.SELL, I) in legal_actions(s)


def test_full_trading_house_is_emptied():
    s = fresh()
    s.trading_house = [C, S, T]
    for g in (C, S, T):
        s.goods_supply[g] -= 1
    give_goods(s, 0, [0, 1, 0, 0, 0])
    choose(s, Role.TRADER)
    step(s, Action(K.SELL, I))
    assert s.trading_house == []
    assert s.goods_supply[I] == 11


# ---------------------------------------------------------------- Capitão
def test_captain_must_use_ship_that_takes_most():
    s = fresh()  # navios 5, 6, 7
    give_goods(s, 0, [6, 0, 0, 0, 0])
    choose(s, Role.CAPTAIN)
    assert legal_set(s) == {Action(K.SHIP, C, 1), Action(K.SHIP, C, 2)}


def test_good_on_full_ship_cannot_go_to_empty_ship():
    s = fresh()
    s.ship_good[0], s.ship_load[0] = C, 5
    s.goods_supply[C] -= 5
    give_goods(s, 0, [3, 2, 0, 0, 0])
    choose(s, Role.CAPTAIN)
    assert legal_set(s) == {Action(K.SHIP, I, 1), Action(K.SHIP, I, 2)}


def test_captain_privilege_once_and_harbor_each_shipment():
    s = fresh()
    give_building(s, 0, B.HARBOR)
    give_goods(s, 0, [0, 2, 1, 0, 0])
    choose(s, Role.CAPTAIN)
    step(s, Action(K.SHIP, I, 0))
    assert s.vp[0] == 2 + 1 + 1
    assert legal_set(s) == {Action(K.SHIP, S, 1), Action(K.SHIP, S, 2)}
    step(s, Action(K.SHIP, S, 1))
    assert s.vp[0] == 4 + 1 + 1
    assert s.vp_supply == 100 - 6


def test_wharf_ships_everything_and_returns_goods():
    s = fresh()
    give_building(s, 0, B.WHARF)
    give_goods(s, 0, [3, 0, 0, 0, 0])
    choose(s, Role.CAPTAIN)
    assert Action(K.SHIP, C, WHARF) in legal_actions(s)
    step(s, Action(K.SHIP, C, WHARF))
    assert s.vp[0] == 3 + 1
    assert s.goods_supply[C] == 10
    assert s.ship_load == [0, 0, 0]


def test_full_ships_unloaded_after_captain():
    s = fresh()
    give_goods(s, 0, [5, 0, 0, 0, 0])
    give_goods(s, 1, [0, 2, 0, 0, 0])
    choose(s, Role.CAPTAIN)
    step(s, Action(K.SHIP, C, 0))  # enche o navio de 5
    # p1 embarca anil (escolha entre navios 1 e 2)
    step(s, Action(K.SHIP, I, 1))
    assert s.ship_load == [0, 2, 0]  # o navio cheio foi esvaziado
    assert s.ship_good == [-1, I, -1]
    assert s.goods_supply[C] == 10


def test_vp_running_out_ends_game_after_round():
    s = fresh()
    s.vp_supply = 2
    give_goods(s, 0, [3, 0, 0, 0, 0])
    choose(s, Role.CAPTAIN)
    step(s, Action(K.SHIP, C, 0))
    assert s.end_triggered and s.vp[0] == 4 and s.vp_supply == -2
    finish_round(s)
    assert s.is_terminal and s.round == 0


def _enter_store_phase(s, p=0):
    s.phase = Phase.CAPTAIN_STORE
    s.current_role = Role.CAPTAIN
    s.role_player = p
    s.actor = p
    s.turn = 0
    s.legal_cache = None


def test_storage_keeps_one_barrel_without_warehouse():
    s = fresh()
    give_goods(s, 0, [3, 2, 0, 0, 0])
    _enter_store_phase(s)
    assert legal_set(s) == {Action(K.STORE, 0, C), Action(K.STORE, 0, I)}
    step(s, Action(K.STORE, 0, I))
    assert s.goods[0] == [0, 1, 0, 0, 0]
    assert s.goods_supply[C] == 10 and s.goods_supply[I] == 10


def test_storage_with_small_warehouse():
    s = fresh()
    give_building(s, 0, B.SMALL_WAREHOUSE)
    give_goods(s, 0, [3, 2, 0, 0, 0])
    _enter_store_phase(s)
    assert legal_set(s) == {Action(K.STORE, 1 << C, I), Action(K.STORE, 1 << I, C)}
    step(s, Action(K.STORE, 1 << C, I))
    assert s.goods[0] == [3, 1, 0, 0, 0]


def test_storage_all_kept_with_enough_warehouses():
    s = fresh()
    give_building(s, 0, B.LARGE_WAREHOUSE)
    give_goods(s, 0, [3, 2, 0, 0, 0])
    _enter_store_phase(s)
    assert legal_set(s) == {Action(K.STORE, (1 << C) | (1 << I), -1)}
    step(s, legal_actions(s)[0])
    assert s.goods[0] == [3, 2, 0, 0, 0]
