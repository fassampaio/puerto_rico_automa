"""Command line: python -m puerto_rico <command>."""

from __future__ import annotations

import argparse
import sys
import time
from contextlib import redirect_stdout
from pathlib import Path

from ..agents.profiles import LEVELS
from ..engine import new_game, score_breakdown, step
from ..runner.records import find_record, record_actions
from ..runner.tournament import TournamentConfig, run_tournament
from ..text import to_ascii
from .board import event_line, is_noise
from .play import default_log_path, play


def out(text: str = "") -> None:
    """All CLI output is plain ASCII (it may be redirected to a log)."""
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
            print(f"\r  {done}/{total} games", end="", file=sys.stderr, flush=True)

    summary = run_tournament(cfg, out=args.out, progress=progress)
    elapsed = time.perf_counter() - start
    print(file=sys.stderr)
    out(summary.format())
    out(f"\n{cfg.games} games in {elapsed:.1f}s ({cfg.games / elapsed:,.0f}/s)")
    if args.out:
        out(f"Log: {args.out}")
    return 0


def _cmd_show(args: argparse.Namespace) -> int:
    if args.out:
        path = Path(args.out)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="ascii", newline="\n") as f, redirect_stdout(f):
            _show(args)
        print(f"Narration saved to {path}")
        return 0
    _show(args)
    return 0


def _show(args: argparse.Namespace) -> None:
    """Narrate a recorded game move by move (forced moves included)."""
    record = find_record(args.file, args.game)
    names = record["agents"]
    s = new_game(record["num_players"], record["seed"])
    s.history = []
    out(f"Game {record['game']} | seed {record['seed']} | {record['num_players']} players")
    for p, name in enumerate(names):
        out(f"  P{p + 1}: {name}")
    for action in record_actions(record):
        step(s, action)
    last_round = -1
    for entry in s.history:
        if is_noise(entry):
            continue
        if entry[0] != last_round:
            last_round = entry[0]
            out(f"\n=== Round {last_round + 1} (governor P{last_round % s.num_players + 1}) ===")
        out(event_line(entry))
    out("\n=== Result ===")
    for p in range(s.num_players):
        bd = score_breakdown(s, p)
        mark = " <- winner" if p in record["winners"] else ""
        out(
            f"  P{p + 1} {names[p]:<20} {bd['total']:>3} pts "
            f"(VP chips {bd['chips']}, buildings {bd['buildings']}, bonus {bd['bonus']}){mark}"
        )


def _cmd_play(args: argparse.Namespace) -> int:
    log = None if args.no_log else (args.log or default_log_path())
    seat = None if args.seat is None else args.seat - 1
    try:
        play(
            num_players=args.players,
            seat=seat,
            bots=args.bots,
            level=args.level,
            seed=args.seed,
            name=args.name,
            log_path=log,
        )
    except (KeyboardInterrupt, EOFError):
        out("\nGame abandoned.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m puerto_rico")
    sub = parser.add_subparsers(dest="command", required=True)

    pl = sub.add_parser("play", help="play a game against bots in the terminal")
    pl.add_argument("--players", "-p", type=int, choices=(3, 4, 5), default=4)
    pl.add_argument("--seat", type=int, default=None, help="your seat, 1 = first governor")
    pl.add_argument("--level", "-l", choices=tuple(LEVELS), default="medium")
    pl.add_argument("--bots", "-b", nargs="+", default=None, help="bot specs (overrides --level)")
    pl.add_argument("--seed", type=int, default=None)
    pl.add_argument("--name", default="You")
    pl.add_argument("--log", default=None, help="JSONL file to save the game")
    pl.add_argument("--no-log", action="store_true", help="do not save the game")
    pl.set_defaults(func=_cmd_play)

    t = sub.add_parser("tournament", help="run a tournament between agents")
    t.add_argument("--agents", "-a", nargs="+", required=True, help="e.g. random random random")
    t.add_argument("--games", "-g", type=int, default=100)
    t.add_argument("--players", "-p", type=int, choices=(3, 4, 5), default=None)
    t.add_argument("--seed", type=int, default=0)
    t.add_argument("--workers", "-w", type=int, default=1)
    t.add_argument("--out", "-o", default=None, help="JSONL file to log the games")
    t.add_argument("--no-actions", action="store_true", help="do not log actions (smaller file)")
    t.set_defaults(func=_cmd_tournament)

    sh = sub.add_parser("show", help="narrate a recorded game")
    sh.add_argument("file")
    sh.add_argument("--game", type=int, default=0)
    sh.add_argument("--out", "-o", default=None, help="save the narration to a text file")
    sh.set_defaults(func=_cmd_show)
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        sys.stdout.reconfigure(errors="replace")
    except AttributeError:
        pass
    args = build_parser().parse_args(argv)
    return args.func(args)
