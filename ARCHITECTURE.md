# Architecture — Puerto Rico simulator with automated players

## Goals

1. **Play against bots** with different difficulty levels and styles.
2. **Analyze strategies** by running thousands of bot-vs-bot games.

v1 scope: base game, 3 to 5 players, terminal interface, Python 3.13.

## Layers

```
Interfaces   CLI to play · tournament CLI · (web in the future)
Execution    GameRunner · Tournament (parallel) · JSONL logs
Agents       Random · Heuristic+Profile · MCTS · Human · (Evolver)
Analysis     statistics · ratings (Elo/TrueSkill) · reports
Engine       pure rules, no I/O, deterministic, cloneable
```

Dependencies only point downwards. The engine knows nothing about bots, terminals or files.

## Rules engine (`puerto_rico/engine`)

| File | Contents |
|---|---|
| `data.py` | Static tables: goods, roles, buildings, setup per player count |
| `config.py` | `RulesConfig` (player count; future variants) |
| `state.py` | `GameState` (complete state, cheap `clone()`) and `Phase` |
| `actions.py` | `Action` (atomic action) and human-readable description |
| `rules.py` | `new_game`, `legal_actions`, `step`, `apply` and queries (`building_cost`, ...) |
| `scoring.py` | Final scoring, large building bonuses, tiebreak |
| `view.py` | `view_for(state, player)`: what a player can see |
| `invariants.py` | Consistency checks used by the tests |

**API:**
```python
s = new_game(num_players=4, seed=42)
s.actor                       # player deciding now
legal_actions(s)              # list of Action
step(s, action)               # mutates s (validates by default)
apply(s, action)              # returns a new state
s.is_terminal; final_scores(s); winners(s)
```

**Principles**
- **Atomic actions.** Every decision is small: choose a role, take a plantation, place *one* colonist, build one building, sell one good, ship (good + ship), store goods.
- **State machine.** `phase` + `actor` say who decides what. There are no loops waiting for input.
- **Forced decisions are automatic.** If there is only one legal action, the engine applies it. Agents only see real choices.
- **Determinism.** A game = `(num_players, seed, chosen actions)` and can be replayed exactly.
- **Hidden information.** Only the order of the plantation stack. `view_for` hides it (the stack is sorted and the seed zeroed).

## Agents (`puerto_rico/agents`)

```python
class Agent(Protocol):
    name: str
    def choose(self, state: GameState, actions: list[Action]) -> Action: ...
```
- `RandomAgent`: tests and baseline.
- `HeuristicAgent(profile, level)`: evaluation-based bot (see roadmap step 3); also the rollout policy for MCTS.
- `MCTSAgent(budget, profile)`: difficulty = budget + error rate; style = profile.
- `HumanCLIAgent`; `EvolverAgent` (optional).

Agents are built from text specifications (`agents/registry.py`), e.g. `heuristic:profile=shipper,level=hard`.

## Execution and analysis

- `runner/game.py`: `play_game`, `replay`.
- `runner/records.py`: JSONL game records (per-player summary + actions), ASCII only.
- `runner/tournament.py`: controlled seeds, deals with seat rotation, multiprocessing.
- `analysis/stats.py`: win rates, scores, ranks, wins by seat, game end reasons.
- `cli/main.py`: `python -m puerto_rico tournament` and `show`.

## Rule interpretation decisions

| Topic | Decision |
|---|---|
| Game end | At the end of the round in which: VP chips run out (Captain), a player fills their 12th city space, or there are not enough colonists to refill the ship (Mayor) |
| VP beyond the supply | Still awarded (the supply goes negative) |
| Mayor | Each player picks up all their colonists and places them again; colonists may not stay in San Juan while there is free space. Placements follow a canonical order (non-decreasing targets) to avoid duplicate permutations |
| Refilling the colonist ship | max(number of players, empty building circles) |
| Hospice / University | The colonist comes from the supply; if it is empty, from the ship |
| Hacienda | Optional, before the normal choice; no Hospice colonist for it |
| Captain | Shipping is mandatory if possible; for a given good, only the ships that take the most barrels are legal; a good already on a ship (even a full one) cannot go on an empty ship. The Wharf is optional |
| Captain privilege | +1 VP only on the first shipment |
| Storage | 1 barrel (windrose) + whole kinds in warehouses; the engine only offers options that keep as much as possible |
| Craftsman | Goods shortage: distributed in order starting with the role chooser. Factory counts the kinds actually received |
| Tiebreak | Money + goods |

## Quality and performance

- pytest: per-rule tests and invariant tests on random games (conservation of colonists, goods, plantations, buildings and VP).
- Performance: pure Python first. If speed runs short: PyPy, optimize hot spots, or a Rust engine with the same API.

## Roadmap

1. Engine + tests ✅ (~90 random games/s with 4 players — `scripts/bench.py`)
2. Runner, logs, tournaments ✅ (`python -m puerto_rico tournament` / `show`; deals with seat rotation; identical results with any number of processes)
3. Heuristic bot with profiles ✅ — `agents/heuristic.py`, `evaluation.py`, `mayor.py`, `profiles.py`
   - Judges each move by the resulting state (estimated final points, relative to the opponents).
   - Roles: simulates the whole phase with everyone playing the same heuristic (medium/hard).
   - Mayor: allocation planner with plantation+building pairs (hard).
   - Calibration (4 players, 120 games): hard 56% · medium 29% · easy 15% · random 0%.
     Styles at hard: shipper 38% · builder 22% · balanced 22% · trader 18%.
   - Note: with these bots, seats 3 and 4 (who start with corn) win more often.
4. Terminal UI to play
5. MCTS + levels + rating calibration
6. Analysis reports
7. Optional: EvolverAgent, web, expansions
