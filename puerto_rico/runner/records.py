"""Registro de partidas em JSONL (uma partida por linha).

Cada registro traz o resumo final de cada jogador (para análise rápida, sem
reproduzir a partida) e, opcionalmente, a lista de ações (para reproduzir ou
narrar a partida exatamente).
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

from ..engine import Action, GameState, ranking, score_breakdown, tiebreak
from ..engine.data import Building
from .game import GameResult, replay

RECORD_VERSION = 1


def player_summary(s: GameState, p: int) -> dict:
    bd = score_breakdown(s, p)
    return {
        "score": bd["total"],
        "vp_chips": bd["fichas"],
        "building_vp": bd["predios"],
        "bonus_vp": bd["bonus"],
        "money": s.money[p],
        "goods": sum(s.goods[p]),
        "tiebreak": tiebreak(s, p),
        "colonists": s.total_colonists(p),
        "plantations": list(s.island[p]),  # milho, anil, açúcar, tabaco, café, pedreira
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
        raise ValueError("registro sem ações (gerado com --no-actions)")
    return [Action.from_json(a) for a in record["actions"]]


def replay_record(record: dict) -> GameState:
    return replay(record["num_players"], record["seed"], record_actions(record))


def dumps(record: dict) -> str:
    return json.dumps(record, ensure_ascii=False, separators=(",", ":"))


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
    raise KeyError(f"partida {game_index} não encontrada em {path}")
