import json
from collections import Counter

import pytest
from helpers import choose, fresh

from puerto_rico.agents import RandomAgent, make_agent, parse_spec
from puerto_rico.analysis import TournamentSummary
from puerto_rico.cli.main import main as cli_main
from puerto_rico.engine import Role, final_scores
from puerto_rico.engine.rules import END_COLONISTS
from puerto_rico.runner import (
    TournamentConfig,
    game_record,
    play_game,
    read_records,
    replay_record,
    run_tournament,
)
from puerto_rico.runner.tournament import game_seed, lineup


def test_parse_spec_and_make_agent():
    assert parse_spec("random") == ("random", {})
    assert parse_spec("mcts:budget=500,c=1.4,greedy=true,style=trader") == (
        "mcts",
        {"budget": 500, "c": 1.4, "greedy": True, "style": "trader"},
    )
    agent = make_agent("random", seed=3)
    assert isinstance(agent, RandomAgent) and agent.name == "random"
    with pytest.raises(ValueError):
        make_agent("nonexistent", seed=0)
    with pytest.raises(ValueError):
        parse_spec("random:novalue")


def test_end_reason_recorded():
    s = fresh()
    s.colonist_supply = 2
    choose(s, Role.MAYOR)
    assert s.end_reasons == [END_COLONISTS]


def test_record_roundtrip_replays_exactly():
    result = play_game([RandomAgent(i) for i in range(3)], seed=5)
    record = json.loads(json.dumps(game_record(result, game_index=7)))
    assert record["game"] == 7 and record["scores"] == result.scores
    assert record["end_reasons"]
    final = replay_record(record)
    assert final_scores(final) == result.scores
    ranks = sorted(p["rank"] for p in record["players"])
    assert ranks == [1, 2, 3]
    winner = record["winners"][0]
    assert record["players"][winner]["rank"] == 1


def test_lineup_rotates_seats_with_same_seed():
    cfg = TournamentConfig(agents=("a", "b", "c", "d"), games=8, num_players=4, seed=1)
    lineups = [lineup(cfg, i) for i in range(4)]
    assert len({game_seed(cfg, i) for i in range(4)}) == 1
    assert game_seed(cfg, 4) != game_seed(cfg, 0)
    for seat in range(4):  # every agent sits in every seat
        assert sorted(lu[seat] for lu in lineups) == ["a", "b", "c", "d"]


def test_lineup_with_more_agents_than_seats():
    cfg = TournamentConfig(agents=tuple("abcdef"), games=300, num_players=3, seed=2)
    counts = Counter(spec for i in range(cfg.games) for spec in lineup(cfg, i))
    assert set(counts) == set("abcdef")
    assert all(len(set(lineup(cfg, i))) == 3 for i in range(cfg.games))


def test_tournament_same_result_sequential_and_parallel(tmp_path):
    base = {"agents": ("random",), "games": 12, "num_players": 4, "seed": 3}
    seq = run_tournament(TournamentConfig(**base, workers=1), out=tmp_path / "seq.jsonl")
    par = run_tournament(TournamentConfig(**base, workers=2), out=tmp_path / "par.jsonl")
    key = lambda r: r["game"]
    a = sorted(read_records(tmp_path / "seq.jsonl"), key=key)
    b = sorted(read_records(tmp_path / "par.jsonl"), key=key)
    assert a == b and len(a) == 12
    assert seq.format() == par.format()


def test_summary_splits_ties():
    record = {
        "num_players": 3,
        "rounds": 10,
        "winners": [0, 2],
        "end_reasons": ["vp_exhausted"],
        "players": [
            {"seat": 0, "agent": "x", "score": 40, "rank": 1},
            {"seat": 1, "agent": "y", "score": 30, "rank": 3},
            {"seat": 2, "agent": "x", "score": 40, "rank": 2},
        ],
    }
    summary = TournamentSummary()
    summary.add(record)
    assert summary.agents["x"].games == 2 and summary.agents["x"].wins == 1.0
    assert summary.agents["y"].wins == 0
    assert summary.seat_wins[0] == 0.5


def test_cli_tournament_and_show(tmp_path, capsys):
    out = tmp_path / "t.jsonl"
    assert cli_main(["tournament", "-a", "random", "random", "random", "-g", "3", "-o", str(out)]) == 0
    assert "Wins by seat" in capsys.readouterr().out
    assert cli_main(["show", str(out), "--game", "2"]) == 0
    text = capsys.readouterr().out
    assert "Round 1" in text and "Result" in text
    assert text.isascii()


def test_logs_are_ascii_only(tmp_path):
    out = tmp_path / "t.jsonl"
    narration = tmp_path / "game.txt"
    cli_main(["tournament", "-a", "random", "random", "random", "-g", "3", "-o", str(out)])
    assert out.read_bytes().isascii()
    assert cli_main(["show", str(out), "--game", "1", "-o", str(narration)]) == 0
    data = narration.read_bytes()
    assert data.isascii() and b"Round 1" in data and b"Choose" in data


def test_to_ascii():
    from puerto_rico.text import to_ascii

    assert to_ascii("Café · Crème ← Naïve") == "Cafe | Creme <- Naive"
