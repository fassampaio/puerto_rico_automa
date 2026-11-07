"""Game records in JSONL (one game per line).

Each record holds every player's final summary (for quick analysis without
replaying) and, optionally, the action list (to replay or narrate the game
exactly).
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

from ..engine import Action, GameState, ranking, score_breakdown, tiebreak
from ..engine.data import Building
from ..text import to_ascii
from .game import GameResult, replay

RECORD_VERSION = 1


def player_summary(s: GameState, p: int) -> dict:
    bd = score_breakdown(s, p)
    return {
        "score": bd["total"],
        "vp_chips": bd["chips"],
        "building_vp": bd["buildings"],
        "bonus_vp": bd["bonus"],
        "money": s.money[p],
        "goods": sum(s.goods[p]),
        "tiebreak": tiebreak(s, p),
        "colonists": s.total_colonists(p),
        "plantations": list(s.island[p]),  # corn, indigo, sugar, tobacco, coffee, quarry
        "buildings": [b.name for b in Building if s.city[p][b]],
    }


def game_record(
    result: GameResult, game_index: int = 0, include_actions: bool = True
) -> dict:
    s = result.final_state
    order = ranking(s)
    players = []
    for p in range(s.num_players):
        summary = player_summary(s, p)
        summary["seat"] = p
        summary["agent"] = result.agent_names[p]
        summary["rank"] = order.index(p) + 1
        players.append(summary)
    record = {
        "v": RECORD_VERSION,
        "game": game_index,
        "seed": result.seed,
        "num_players": result.num_players,
        "agents": result.agent_names,
        "scores": result.scores,
        "winners": result.winners,
        "rounds": result.rounds,
        "end_reasons": list(s.end_reasons),
        "decisions": len(result.actions),
        "players": players,
    }
    if include_actions:
        record["actions"] = [a.to_json() for a in result.actions]
    return record


def record_actions(record: dict) -> list[Action]:
    if "actions" not in record:
        raise ValueError("record has no actions (written with --no-actions)")
    return [Action.from_json(a) for a in record["actions"]]


def replay_record(record: dict) -> GameState:
    return replay(record["num_players"], record["seed"], record_actions(record))


def _ascii_strings(value: object) -> object:
    if isinstance(value, str):
        return to_ascii(value)
    if isinstance(value, list):
        return [_ascii_strings(v) for v in value]
    if isinstance(value, dict):
        return {to_ascii(k): _ascii_strings(v) for k, v in value.items()}
    return value


def dumps(record: dict) -> str:
    """One JSON line, ASCII only (no accented characters)."""
    return json.dumps(_ascii_strings(record), ensure_ascii=True, separators=(",", ":"))


def read_records(path: str | Path) -> Iterator[dict]:
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def find_record(path: str | Path, game_index: int) -> dict:
    for record in read_records(path):
        if record["game"] == game_index:
            return record
    raise KeyError(f"game {game_index} not found in {path}")
