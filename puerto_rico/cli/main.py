"""Linha de comando: python -m puerto_rico <comando>."""

from __future__ import annotations

import argparse
import sys
import time
from contextlib import redirect_stdout
from pathlib import Path

from ..engine import Phase, describe, new_game, score_breakdown, step
from ..engine.data import ROLE_NAMES
from ..runner.records import find_record, record_actions
from ..runner.tournament import TournamentConfig, run_tournament
from ..text import to_ascii


def out(text: str = "") -> None:
    """Toda saída da CLI sai sem acentos/cedilha (pode ser redirecionada para log)."""
    print(to_ascii(text))


def _cmd_tournament(args: argparse.Namespace) -> int:
    players = args.players or (len(args.agents) if 3 <= len(args.agents) <= 5 else 4)
    cfg = TournamentConfig(
        agents=tuple(args.agents),
        games=args.games,
        num_players=players,
        seed=args.seed,
        workers=args.workers,
        include_actions=not args.no_actions,
    )
    start = time.perf_counter()
    step_size = max(1, cfg.games // 20)

    def progress(done: int, total: int) -> None:
        if done % step_size == 0 or done == total:
            print(f"\r  {done}/{total} partidas", end="", file=sys.stderr, flush=True)

    summary = run_tournament(cfg, out=args.out, progress=progress)
    elapsed = time.perf_counter() - start
    print(file=sys.stderr)
    out(summary.format())
    out(f"\n{cfg.games} partidas em {elapsed:.1f}s ({cfg.games / elapsed:,.0f}/s)")
    if args.out:
        out(f"Registro: {args.out}")
    return 0


def _cmd_show(args: argparse.Namespace) -> int:
    if args.out:
        path = Path(args.out)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="ascii", newline="\n") as f, redirect_stdout(f):
            _show(args)
        print(f"Narracao gravada em {path}")
        return 0
    _show(args)
    return 0


def _show(args: argparse.Namespace) -> None:
    record = find_record(args.file, args.game)
    names = record["agents"]
    s = new_game(record["num_players"], record["seed"])
    out(f"Partida {record['game']} | semente {record['seed']} | {record['num_players']} jogadores")
    for p, name in enumerate(names):
        out(f"  J{p + 1}: {name}")
    last_round = -1
    for action in record_actions(record):
        if s.round != last_round:
            last_round = s.round
            out(f"\n=== Rodada {s.round + 1} (governador J{s.governor + 1}) ===")
        context = "" if s.phase == Phase.ROLE_SELECTION else f"[{ROLE_NAMES[s.current_role]}] "
        out(f"  J{s.actor + 1} {context}{describe(action)}")
        step(s, action)
    out("\n=== Resultado ===")
    for p in range(s.num_players):
        bd = score_breakdown(s, p)
        mark = " <- vencedor" if p in record["winners"] else ""
        out(
            f"  J{p + 1} {names[p]:<20} {bd['total']:>3} pts "
            f"(fichas {bd['fichas']}, predios {bd['predios']}, bonus {bd['bonus']}){mark}"
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m puerto_rico")
    sub = parser.add_subparsers(dest="command", required=True)

    t = sub.add_parser("tournament", help="roda um torneio entre agentes")
    t.add_argument("--agents", "-a", nargs="+", required=True, help="ex.: random random random")
    t.add_argument("--games", "-g", type=int, default=100)
    t.add_argument("--players", "-p", type=int, choices=(3, 4, 5), default=None)
    t.add_argument("--seed", type=int, default=0)
    t.add_argument("--workers", "-w", type=int, default=1)
    t.add_argument("--out", "-o", default=None, help="arquivo JSONL para registrar as partidas")
    t.add_argument("--no-actions", action="store_true", help="não registra as ações (arquivo menor)")
    t.set_defaults(func=_cmd_tournament)

    sh = sub.add_parser("show", help="narra uma partida registrada")
    sh.add_argument("file")
    sh.add_argument("--game", type=int, default=0)
    sh.add_argument("--out", "-o", default=None, help="grava a narração num arquivo de texto")
    sh.set_defaults(func=_cmd_show)
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        sys.stdout.reconfigure(errors="replace")
    except AttributeError:
        pass
    args = build_parser().parse_args(argv)
    return args.func(args)
