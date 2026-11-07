"""Measure engine speed with random agents.

Usage: python scripts/bench.py [number of games] [number of players]
"""

from __future__ import annotations

import random
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from puerto_rico.engine import (
    final_scores,
    legal_actions,
    new_game,
    step,
)


def main() -> None:
    games = int(sys.argv[1]) if len(sys.argv) > 1 else 500
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    rng = random.Random(0)
    decisions, rounds, scores, clones = 0, [], [], 0
    t0 = time.perf_counter()
    for seed in range(games):
        s = new_game(n, seed)
        while not s.is_terminal:
            step(s, rng.choice(legal_actions(s)), validate=False)
            decisions += 1
        rounds.append(s.round + 1)
        scores.extend(final_scores(s))
    elapsed = time.perf_counter() - t0

    s = new_game(n, 1)
    t1 = time.perf_counter()
    while time.perf_counter() - t1 < 1.0:
        s.clone()
        clones += 1

    print(f"{games} games with {n} players in {elapsed:.2f}s")
    print(f"  {games / elapsed:,.0f} games/s | {decisions / elapsed:,.0f} decisions/s")
    print(f"  {decisions / games:.0f} decisions per game | {statistics.mean(rounds):.1f} rounds")
    print(f"  average score (random): {statistics.mean(scores):.1f}")
    print(f"  clone(): {clones:,} per second")


if __name__ == "__main__":
    main()
