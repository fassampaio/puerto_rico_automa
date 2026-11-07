"""Torneios: muitas partidas entre agentes, com rotação de assentos e paralelismo.

Partidas são agrupadas em "mãos" de N jogos: a mesma semente (mesma distribuição
de plantações) é jogada N vezes, girando os agentes pelos assentos. Isso reduz a
variância da comparação entre agentes. O resultado de cada partida depende só de
(configuração, índice da partida), então o torneio dá o mesmo resultado com
qualquer número de processos.
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
    agents: tuple[str, ...]  # especificações (ver agents.registry)
    games: int
    num_players: int = 4
    seed: int = 0
    workers: int = 1
    include_actions: bool = True

    def __post_init__(self) -> None:
        if not self.agents:
            raise ValueError("informe pelo menos um agente")
        if self.num_players not in (3, 4, 5):
            raise ValueError("num_players deve ser 3, 4 ou 5")
        if self.games < 1:
            raise ValueError("games deve ser >= 1")


def game_seed(cfg: TournamentConfig, game_index: int) -> int:
    return cfg.seed * 1_000_000 + game_index // cfg.num_players


def lineup(cfg: TournamentConfig, game_index: int) -> list[str]:
    """Especificação do agente em cada assento para a partida game_index."""
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
    """Gera os registros das partidas (fora de ordem quando em paralelo)."""
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
