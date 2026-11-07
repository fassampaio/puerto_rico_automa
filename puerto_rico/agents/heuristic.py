"""Heuristic bot: judges each move by the resulting state.

- Decisions inside a phase: apply the move and evaluate the state (1-ply).
- Role selection (medium/hard levels): simulate the role's whole phase, with
  every player deciding by the same heuristic, and evaluate the outcome.
  This weighs the bot's own gain against what the role gives the opponents.
- The value is relative: own gain minus part of the opponents' average.
- Mayor: plans the full colonist allocation (see mayor.py).
- The plantation stack order is unknown: the bot shuffles it before simulating.
"""

from __future__ import annotations

import math
import random

from ..engine import Action, ActionKind, GameState, Phase, apply, legal_actions, step
from .evaluation import evaluate_all, relative_value
from .mayor import plan_placements
from .profiles import Profile, get_level, get_profile


class HeuristicAgent:
    def __init__(
        self,
        seed: int | None = None,
        profile: str | Profile = "balanced",
        level: str = "medium",
        temperature: float | None = None,
        lookahead: bool | None = None,
        name: str | None = None,
    ) -> None:
        self.rng = random.Random(seed)
        self.profile = get_profile(profile) if isinstance(profile, str) else profile
        lv = get_level(level)
        self.temperature = lv.temperature if temperature is None else float(temperature)
        self.lookahead = lv.lookahead if lookahead is None else bool(lookahead)
        self.mayor_planning = lv.mayor_planning
        self.name = name or f"heuristic:{self.profile.name}:{lv.name}"
        self._mayor_cache: dict[tuple, list[int]] = {}

    # ------------------------------------------------------------------
    def choose(self, state: GameState, actions: list[Action]) -> Action:
        if len(actions) == 1:
            return actions[0]
        if state.phase == Phase.MAYOR:
            return self.mayor_action(state, actions, thorough=self.mayor_planning)
        sim = state.clone()
        self.rng.shuffle(sim.plantation_stack)
        p = state.actor
        if state.phase == Phase.ROLE_SELECTION and self.lookahead:
            scores = [self.role_value(sim, a, p) for a in actions]
        else:
            scores = [self.action_value(sim, a, p) for a in actions]
        return self._pick(actions, scores)

    def action_value(self, s: GameState, action: Action, p: int) -> float:
        child = apply(s, action, validate=False)
        return relative_value(evaluate_all(child, self.profile), p, self.profile.aggression)

    def greedy(self, s: GameState) -> Action:
        acts = legal_actions(s)
        if len(acts) == 1:
            return acts[0]
        if s.phase == Phase.MAYOR:
            return self.mayor_action(s, acts, thorough=False)
        q = s.actor
        return max(acts, key=lambda a: self.action_value(s, a, q))

    def mayor_action(self, s: GameState, actions: list[Action], thorough: bool) -> Action:
        """Follow the allocation plan: place on the lowest planned target (canonical order)."""
        key = (s.round, s.picks, s.actor, s.san_juan[s.actor], s.mayor_last)
        plan = self._mayor_cache.get(key) if thorough else None
        if plan is None:
            plan = sorted(plan_placements(s, s.actor, self.profile, thorough))
        action = Action(ActionKind.PLACE, plan[0])
        if action not in actions:  # should not happen; safety net
            q = s.actor
            return max(actions, key=lambda a: self.action_value(s, a, q))
        if thorough:
            self._mayor_cache = {
                (s.round, s.picks, s.actor, s.san_juan[s.actor] - 1, plan[0]): plan[1:]
            }
        return action

    def role_value(self, s: GameState, action: Action, p: int) -> float:
        c = apply(s, action, validate=False)
        while c.phase not in (Phase.ROLE_SELECTION, Phase.GAME_OVER):
            step(c, self.greedy(c), validate=False)
        return relative_value(evaluate_all(c, self.profile), p, self.profile.aggression)

    def _pick(self, actions: list[Action], scores: list[float]) -> Action:
        if self.temperature <= 0:
            best = max(scores)
            top = [a for a, v in zip(actions, scores) if v >= best - 1e-9]
            return top[0] if len(top) == 1 else self.rng.choice(top)
        m = max(scores)
        weights = [math.exp((v - m) / self.temperature) for v in scores]
        return self.rng.choices(actions, weights=weights)[0]
