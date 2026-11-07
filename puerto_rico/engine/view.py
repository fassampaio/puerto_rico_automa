"""A player's view: the state without hidden information."""

from __future__ import annotations

from .state import GameState


def view_for(s: GameState, player: int) -> GameState:
    """Copy of the state in which the order of the plantation stack is unknown.

    The stack contents are public (they can be deduced by counting), but the order
    is not: the stack is sorted and the seed zeroed, so an agent cannot predict
    draws. Simulations run on a view should shuffle the stack first.
    """
    v = s.clone()
    v.plantation_stack.sort()
    v.seed = 0
    return v
