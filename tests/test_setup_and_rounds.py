import pytest
from helpers import choose, fresh

from puerto_rico.engine import Phase, Role, check_invariants, legal_actions
from puerto_rico.engine.data import Good


@pytest.mark.parametrize(
    "n, money, vp, colonists, ship, ships, roles",
    [
        (3, 2, 75, 55, 3, [4, 5, 6], 6),
        (4, 3, 100, 75, 4, [5, 6, 7], 7),
        (5, 4, 122, 95, 5, [6, 7, 8], 8),
    ],
)
def test_setup(n, money, vp, colonists, ship, ships, roles):
    s = fresh(n)
    assert s.money == [money] * n
    assert s.vp_supply == vp
    assert s.colonist_supply == colonists
    assert s.colonist_ship == ship
    assert s.ship_capacity == ships
    assert len(s.roles) == roles
    assert len(s.faceup) == n + 1
    assert s.phase == Phase.ROLE_SELECTION and s.actor == 0
    assert len(legal_actions(s)) == roles
    assert check_invariants(s) == []


def test_starting_plantations():
    s = fresh(5)
    indigo = [p for p in range(5) if s.island[p][Good.INDIGO] == 1]
    corn = [p for p in range(5) if s.island[p][Good.CORN] == 1]
    assert indigo == [0, 1, 2] and corn == [3, 4]
    assert all(sum(s.island_manned[p]) == 0 for p in range(5))


def test_unused_roles_gain_money_and_governor_rotates():
    s = fresh(4)
    choose(s, Role.PROSPECTOR)  # p0: +1
    choose(s, Role.CRAFTSMAN)  # nobody produces
    choose(s, Role.TRADER)  # nobody has goods
    choose(s, Role.CAPTAIN)  # nobody ships
    assert s.money == [4, 3, 3, 3]
    assert s.round == 1 and s.governor == 1 and s.actor == 1
    for r in (Role.SETTLER, Role.MAYOR, Role.BUILDER):
        assert s.role_money[r] == 1
    for r in (Role.PROSPECTOR, Role.CRAFTSMAN, Role.TRADER, Role.CAPTAIN):
        assert s.role_money[r] == 0
    assert not any(s.role_taken)


def test_role_money_goes_to_chooser():
    s = fresh(4)
    s.role_money[Role.BUILDER] = 2
    choose(s, Role.BUILDER)
    assert s.money[0] == 5
    assert s.role_money[Role.BUILDER] == 0


def test_taken_role_not_available_again_in_round():
    s = fresh(4)
    choose(s, Role.PROSPECTOR)
    from puerto_rico.engine import Action, ActionKind

    assert Action(ActionKind.CHOOSE_ROLE, Role.PROSPECTOR) not in legal_actions(s)
