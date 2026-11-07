import pytest
from helpers import choose, fresh, give_building, give_goods, set_island

from puerto_rico.agents import HeuristicAgent, RandomAgent, make_agent
from puerto_rico.agents.evaluation import evaluate, progress
from puerto_rico.agents.profiles import PROFILES, get_level, get_profile
from puerto_rico.engine import Action, Good, Phase, Role, legal_actions, score, step, view_for
from puerto_rico.engine import ActionKind as K
from puerto_rico.engine import Building as B
from puerto_rico.engine.actions import PLACE_BUILDING_OFFSET as OFF
from puerto_rico.runner import play_game


def _decide(agent, s):
    return agent.choose(view_for(s, s.actor), legal_actions(s))


def test_profiles_and_levels_lookup():
    assert set(PROFILES) == {"balanced", "shipper", "builder", "trader"}
    assert get_level("hard").temperature == 0
    with pytest.raises(ValueError):
        get_profile("xyz")
    with pytest.raises(ValueError):
        get_level("xyz")
    agent = make_agent("heuristic:profile=shipper,level=easy", seed=1)
    assert agent.profile.name == "shipper" and not agent.lookahead


def test_evaluation_equals_score_at_game_end():
    result = play_game([RandomAgent(i) for i in range(3)], seed=2)
    s = result.final_state
    for p in range(3):
        assert evaluate(s, p, PROFILES["balanced"]) == score(s, p)
    assert progress(fresh()) == 0.0


def test_trader_sells_most_valuable_good():
    s = fresh()
    give_goods(s, 0, [1, 0, 0, 0, 1])
    choose(s, Role.TRADER)
    agent = HeuristicAgent(seed=0, level="hard")
    assert _decide(agent, s) == Action(K.SELL, Good.COFFEE)


def test_captain_ships_rather_than_wharf_waste():
    s = fresh()
    give_goods(s, 0, [4, 0, 0, 0, 0])
    choose(s, Role.CAPTAIN)
    agent = HeuristicAgent(seed=0, level="hard")
    action = _decide(agent, s)
    assert action.kind == K.SHIP


def test_builder_with_money_buys_something():
    s = fresh()
    s.money[0] = 8
    choose(s, Role.BUILDER)
    agent = HeuristicAgent(seed=0, level="hard")
    assert _decide(agent, s).kind == K.BUILD


def test_mayor_planner_prefers_production_pair():
    s = fresh()
    set_island(s, 0, [1, 1, 0, 0, 0, 0])  # corn and indigo, unmanned
    give_building(s, 0, B.SMALL_INDIGO_PLANT, manned=0)
    choose(s, Role.MAYOR)  # p0 gets 2 colonists for 3 slots
    assert s.phase == Phase.MAYOR and s.actor == 0
    agent = HeuristicAgent(seed=0, level="hard")
    while s.phase == Phase.MAYOR and s.actor == 0:
        step(s, _decide(agent, s))
    assert s.island_manned[0][Good.INDIGO] == 1
    assert s.city_manned[0][B.SMALL_INDIGO_PLANT] == 1
    assert s.island_manned[0][Good.CORN] == 0
    assert OFF + B.SMALL_INDIGO_PLANT > Good.INDIGO


@pytest.mark.parametrize("level", ["easy", "medium", "hard"])
def test_full_game_only_legal_actions(level):
    agents = [HeuristicAgent(seed=i, level=level) for i in range(3)]
    result = play_game(agents, seed=9)  # play_game validates every action
    assert result.final_state.is_terminal


def test_heuristic_beats_random():
    wins = 0
    for g in range(8):
        agents = [RandomAgent(g * 10 + i) for i in range(4)]
        seat = g % 4
        agents[seat] = HeuristicAgent(seed=g, level="medium")
        wins += seat in play_game(agents, seed=100 + g).winners
    assert wins >= 6
