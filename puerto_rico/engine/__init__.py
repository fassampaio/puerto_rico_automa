"""Motor de regras de Puerto Rico (jogo base, 3 a 5 jogadores)."""

from .actions import PASS, WHARF, Action, ActionKind, describe
from .config import RulesConfig
from .data import Building, Good, Role
from .invariants import check_invariants
from .rules import (
    IllegalActionError,
    apply,
    building_cost,
    legal_actions,
    new_game,
    sale_price,
    shipping_options,
    step,
)
from .scoring import final_scores, ranking, score, score_breakdown, tiebreak, winners
from .state import GameState, Phase
from .view import view_for

__all__ = [
    "PASS",
    "WHARF",
    "Action",
    "ActionKind",
    "Building",
    "GameState",
    "Good",
    "IllegalActionError",
    "Phase",
    "Role",
    "RulesConfig",
    "apply",
    "building_cost",
    "check_invariants",
    "describe",
    "final_scores",
    "legal_actions",
    "new_game",
    "ranking",
    "sale_price",
    "score",
    "score_breakdown",
    "shipping_options",
    "step",
    "tiebreak",
    "view_for",
    "winners",
]
