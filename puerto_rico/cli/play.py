"""Play a game in the terminal against bots."""

from __future__ import annotations

import random
import time
from collections.abc import Callable, Sequence
from pathlib import Path

from ..agents.base import Agent
from ..agents.profiles import PROFILES
from ..agents.registry import make_agent
from ..engine import (
    Action,
    GameState,
    final_scores,
    legal_actions,
    new_game,
    score_breakdown,
    step,
    view_for,
    winners,
)
from ..engine.data import ROLE_NAMES
from ..runner.game import GameResult
from ..runner.records import dumps, game_record
from ..text import to_ascii
from .board import action_label, event_line, is_noise, render_board

InputFn = Callable[[str], str]
PrintFn = Callable[[str], None]

HELP = """Commands:
  <number>  choose that option
  b         show the full board (including the buildings available)
  h         show this help
  q         quit the game"""


class QuitGame(Exception):
    pass


class HumanCLIAgent:
    """A human player deciding through the terminal."""

    def __init__(
        self,
        names: list[str],
        name: str = "You",
        input_fn: InputFn = input,
        print_fn: PrintFn = print,
    ) -> None:
        self.name = f"human:{name}"
        self.names = names
        self.input_fn = input_fn
        self.print_fn = print_fn

    def _out(self, text: str = "") -> None:
        self.print_fn(to_ascii(text))

    def choose(self, state: GameState, actions: list[Action]) -> Action:
        me = state.actor
        self._out()
        self._out(render_board(state, self.names, me))
        self._out()
        role = ROLE_NAMES[state.current_role] if state.current_role >= 0 else "choose a role"
        self._out(f"Your move (P{me + 1}, {role}):")
        for i, a in enumerate(actions, start=1):
            self._out(f"  {i:>2}) {action_label(state, a)}")
        while True:
            answer = self.input_fn(f"Choose [1-{len(actions)}], b=board, h=help, q=quit: ")
            answer = answer.strip().lower()
            if answer.isdigit() and 1 <= int(answer) <= len(actions):
                return actions[int(answer) - 1]
            if answer == "b":
                self._out(render_board(state, self.names, me, full=True))
            elif answer == "h":
                self._out(HELP)
            elif answer == "q":
                raise QuitGame
            else:
                self._out("Invalid option.")


def default_bots(num_bots: int, level: str, rng: random.Random) -> list[str]:
    profiles = list(PROFILES)
    rng.shuffle(profiles)
    return [f"heuristic:profile={profiles[i % len(profiles)]},level={level}" for i in range(num_bots)]


def play(
    num_players: int = 4,
    seat: int | None = None,
    bots: Sequence[str] | None = None,
    level: str = "medium",
    seed: int | None = None,
    name: str = "You",
    log_path: str | Path | None = None,
    input_fn: InputFn = input,
    print_fn: PrintFn = print,
) -> GameResult | None:
    """Run an interactive game. Returns the result, or None if the human quit."""

    def out(text: str = "") -> None:
        print_fn(to_ascii(text))

    if seed is None:
        seed = random.SystemRandom().randrange(1_000_000)
    rng = random.Random(seed)
    if seat is None:
        seat = rng.randrange(num_players)
    if not 0 <= seat < num_players:
        raise ValueError(f"seat must be between 1 and {num_players}")
    bot_specs = list(bots) if bots else default_bots(num_players - 1, level, rng)
    if len(bot_specs) != num_players - 1:
        raise ValueError(f"need {num_players - 1} bot specifications, got {len(bot_specs)}")

    names: list[str] = []
    agents: list[Agent] = []
    specs = iter(bot_specs)
    for p in range(num_players):
        if p == seat:
            names.append(f"{name} (human)")
            agents.append(HumanCLIAgent(names, name, input_fn, print_fn))
        else:
            spec = next(specs)
            names.append(spec)
            agents.append(make_agent(spec, seed * 16 + p))

    out(f"Puerto Rico | {num_players} players | seed {seed}")
    for p in range(num_players):
        out(f"  P{p + 1}: {names[p]}{'  <- you' if p == seat else ''}")
    out("Type h at any prompt for help.")

    s = new_game(num_players, seed)
    s.history = []
    shown = 0
    actions: list[Action] = []
    last_round = -1
    try:
        while not s.is_terminal:
            shown, last_round = _flush(s, shown, last_round, out)
            p = s.actor
            action = agents[p].choose(view_for(s, p), legal_actions(s))
            step(s, action)
            actions.append(action)
        _flush(s, shown, last_round, out)
    except QuitGame:
        out("\nGame abandoned.")
        return None

    result = GameResult(
        seed=seed,
        num_players=num_players,
        agent_names=[a.name for a in agents],
        actions=actions,
        final_state=s,
        scores=final_scores(s),
        winners=winners(s),
        rounds=s.round + 1,
    )
    out("\n=== Final result ===")
    for p in sorted(range(num_players), key=lambda q: result.scores[q], reverse=True):
        bd = score_breakdown(s, p)
        mark = "  <- winner" if p in result.winners else ""
        out(
            f"  P{p + 1} {names[p]:<40} {bd['total']:>3} pts (VP chips {bd['chips']}, "
            f"buildings {bd['buildings']}, bonus {bd['bonus']}){mark}"
        )
    if log_path is not None:
        path = Path(log_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="ascii") as f:
            f.write(dumps(game_record(result)) + "\n")
        out(f"\nGame saved to {path} (replay it with: python -m puerto_rico show {path})")
    return result


def _flush(s: GameState, shown: int, last_round: int, out: PrintFn) -> tuple[int, int]:
    """Print the history entries not shown yet, with round headers."""
    history = s.history or []
    for entry in history[shown:]:
        if is_noise(entry):
            continue
        if entry[0] != last_round:
            last_round = entry[0]
            out(f"\n--- Round {last_round + 1} ---")
        out(event_line(entry))
    return len(history), last_round


def default_log_path() -> Path:
    return Path("logs") / f"play-{time.strftime('%Y%m%d-%H%M%S')}.jsonl"
