"""Full random games: invariants, termination, determinism and cloning."""

import random
from dataclasses import asdict

import pytest

from puerto_rico.agents import RandomAgent
from puerto_rico.engine import apply, check_invariants, legal_actions, new_game, step, view_for
from puerto_rico.runner import play_game, replay


def _snapshot(s):
    d = asdict(s)
    d.pop("legal_cache")
    return d


@pytest.mark.parametrize("n", [3, 4, 5])
def test_random_games_keep_invariants(n):
    for seed in range(40):
        rng = random.Random(seed)
        s = new_game(n, seed)
        decisions = 0
        while not s.is_terminal:
            acts = legal_actions(s)
            assert len(acts) >= 2, f"decision without a real choice in {s.phase.name}"
            step(s, rng.choice(acts))
            errors = check_invariants(s)
            assert errors == [], f"seed={seed} decision={decisions}: {errors}"
            decisions += 1
            assert decisions < 5000
        assert s.round < 40


def test_play_game_is_deterministic_and_replayable():
    agents = [RandomAgent(i) for i in range(4)]
    r1 = play_game(agents, seed=42)
    r2 = play_game([RandomAgent(i) for i in range(4)], seed=42)
    assert r1.actions == r2.actions and r1.scores == r2.scores
    final = replay(4, 42, r1.actions)
    assert _snapshot(final) == _snapshot(r1.final_state)


def test_clone_and_apply_do_not_touch_original():
    s = new_game(4, 7)
    rng = random.Random(1)
    for _ in range(30):
        before = _snapshot(s)
        child = apply(s, rng.choice(legal_actions(s)))
        assert _snapshot(s) == before
        s = child


def test_view_hides_stack_order():
    s = new_game(4, 3)
    v = view_for(s, 0)
    assert v.plantation_stack == sorted(s.plantation_stack)
    assert v.seed == 0
    assert s.plantation_stack != sorted(s.plantation_stack)  # the original stays shuffled
