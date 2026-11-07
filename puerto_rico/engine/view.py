"""Visão de um jogador: o estado sem informação oculta."""

from __future__ import annotations

from .state import GameState


def view_for(s: GameState, player: int) -> GameState:
    """Cópia do estado em que a ordem da pilha de plantações é desconhecida.

    O conteúdo da pilha é público (dá para deduzir contando), mas a ordem não:
    a pilha é ordenada e a semente zerada, para que um agente não consiga prever
    os sorteios. Simulações feitas sobre a visão devem embaralhar a pilha.
    """
    v = s.clone()
    v.plantation_stack.sort()
    v.seed = 0
    return v
