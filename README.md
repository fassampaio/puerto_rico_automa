# Puerto Rico Automa

A simulator of the board game **Puerto Rico** (base game, 3 to 5 players) with automated players, to:

- **play against bots** with different difficulty levels and styles;
- **analyze strategies** by running thousands of games between bots.

> Unofficial, non-commercial fan project. *Puerto Rico* is a game by Andreas Seyfarth; the name and trademark belong to its publishers. This repository only implements the rules mechanics for simulation purposes and contains no artwork, rulebook text or other material from the published game.

## Status

| Step | Status |
|---|---|
| 1. Rules engine + tests | ✅ |
| 2. Runner, game logs, tournaments | ✅ |
| 3. Heuristic bot with style profiles | ✅ |
| 4. Terminal UI to play | ✅ |
| 5. MCTS bot with difficulty levels | ⏳ |
| 6. Analysis reports | ⏳ |

Design details and rule interpretations are in [ARCHITECTURE.md](ARCHITECTURE.md).

## Requirements

Python 3.12 or newer. The engine has no dependencies; the tests use `pytest`.

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows  (Linux/macOS: source .venv/bin/activate)
pip install pytest ruff
```

## Usage

Play against bots in the terminal:
```bash
python -m puerto_rico play --players 4 --level hard --name Fabio
```

Options: `--seat N` (1 = first governor; random by default), `--level easy|medium|hard`,
`--bots SPEC SPEC ...` to pick the opponents, `--seed N` to replay the same deal, `--no-log`.
Each finished game is saved to `logs/play-<date>.jsonl` and can be narrated with `show`.
At any prompt: a number picks that option, `b` shows the full board (with the buildings
available), `h` shows help, `q` quits.

Tests:
```bash
python -m pytest
```

Tournament between agents (logs every game to JSONL and prints a summary):
```bash
python -m puerto_rico tournament --agents random random random random --games 1000 --workers 4 --out logs/tournament.jsonl
```

Available agents (specification `name:param=value,...`):

| Specification | Description |
|---|---|
| `random` | plays at random |
| `heuristic` | heuristic bot (default: `profile=balanced`, `level=medium`) |
| `heuristic:profile=shipper,level=hard` | profiles: `balanced`, `shipper`, `builder`, `trader` · levels: `easy`, `medium`, `hard` |

```bash
python -m puerto_rico tournament -a heuristic:level=hard heuristic:level=medium heuristic:level=easy random -g 120 -w 2
```

Narrate a recorded game (on screen, or to a text file with `-o`):
```bash
python -m puerto_rico show logs/tournament.jsonl --game 0 -o logs/game0.txt
```

Logs and narrations are written in plain ASCII.

Engine speed:
```bash
python scripts/bench.py 500 4
```

### Using the engine from code

```python
from puerto_rico.engine import new_game, legal_actions, step, final_scores

s = new_game(num_players=4, seed=42)
while not s.is_terminal:
    acts = legal_actions(s)   # only decisions with a real choice show up
    step(s, acts[0])
print(final_scores(s))
```

## Layout

```
puerto_rico/
  engine/     pure, deterministic, cloneable rules
  agents/     Agent interface, agent registry, random and heuristic bots
  runner/     games, JSONL records, parallel tournaments
  analysis/   tournament statistics
  cli/        command line (python -m puerto_rico)
tests/        per-rule, invariant, runner and bot tests
scripts/      utilities (benchmark)
```

## License

[MIT](LICENSE)
