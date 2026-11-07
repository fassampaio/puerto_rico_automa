"""Tournaments: many games between agents, with seat rotation and parallelism.

Games are grouped into "deals" of N games: the same seed (same plantation
order) is played N times, rotating the agents through the seats. This reduces
the variance when comparing agents. Each game's result depends only on
(configuration, game index), so the tournament gives the same result with any
number of processes.
"""

from __future__ import annotations

import multiprocessing as mp
import random
from collections.abc import Callable, Iterator
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path

from ..agents.registry import make_agent
from ..analysis.stats import TournamentSummary
from .game import play_game
from .records import dumps, game_record


@dataclass(frozen=True)
class TournamentConfig:
    agents: tuple[str, ...]  # specifications (see agents.registry)
    games: int
    num_players: int = 4
    seed: int = 0
    workers: int = 1
    include_actions: bool = True

    def __post_init__(self) -> None:
        if not self.agents:
            raise ValueError("give at least one agent")
        if self.num_players not in (3, 4, 5):
            raise ValueError("num_players must be 3, 4 or 5")
        if self.games < 1:
            raise ValueError("games must be >= 1")


def game_seed(cfg: TournamentConfig, game_index: int) -> int:
    return cfg.seed * 1_000_000 + game_index // cfg.num_players


def lineup(cfg: TournamentConfig, game_index: int) -> list[str]:
    """Agent specification in each seat for game game_index."""
    n, m = cfg.num_players, len(cfg.agents)
    group, shift = divmod(game_index, n)
    if m > n:
        base = random.Random(cfg.seed * 7_919 + group).sample(range(m), n)
    else:
        base = [k % m for k in range(n)]
    return [cfg.agents[base[(seat - shift) % n]] for seat in range(n)]


def run_game(cfg: TournamentConfig, game_index: int) -> dict:
    seed = game_seed(cfg, game_index)
    specs = lineup(cfg, game_index)
    agents = [make_agent(spec, seed * 16 + seat) for seat, spec in enumerate(specs)]
    result = play_game(agents, seed=seed)
    return game_record(result, game_index, cfg.include_actions)


def _run_game_args(args: tuple[TournamentConfig, int]) -> dict:
    return run_game(*args)


def iter_games(cfg: TournamentConfig) -> Iterator[dict]:
    """Yield the game records (out of order when running in parallel)."""
    tasks = [(cfg, i) for i in range(cfg.games)]
    if cfg.workers <= 1:
        for task in tasks:
            yield _run_game_args(task)
        return
    chunk = max(1, cfg.games // (cfg.workers * 20))
    with mp.get_context("spawn").Pool(cfg.workers) as pool:
        yield from pool.imap_unordered(_run_game_args, tasks, chunksize=chunk)


def run_tournament(
    cfg: TournamentConfig,
    out: str | Path | None = None,
    progress: Callable[[int, int], None] | None = None,
) -> TournamentSummary:
    summary = TournamentSummary()
    with ExitStack() as stack:
        f = None
        if out is not None:
            path = Path(out)
            path.parent.mkdir(parents=True, exist_ok=True)
            f = stack.enter_context(open(path, "w", encoding="utf-8"))
        for done, record in enumerate(iter_games(cfg), start=1):
            summary.add(record)
            if f is not None:
                f.write(dumps(record) + "\n")
            if progress is not None:
                progress(done, cfg.games)
    return summary
