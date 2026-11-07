"""Registro de agentes: cria agentes a partir de especificações em texto.

Formato: ``nome`` ou ``nome:param=valor,param2=valor`` (ex.: ``mcts:budget=500``).
A especificação completa vira o nome do agente nos registros e resumos.
Agentes recebem sempre um ``seed`` para que torneios sejam reproduzíveis.
"""

from __future__ import annotations

from collections.abc import Callable

from .base import Agent
from .heuristic import HeuristicAgent
from .random_agent import RandomAgent

AgentFactory = Callable[..., Agent]

AGENTS: dict[str, AgentFactory] = {
    "random": RandomAgent,
    "heuristic": HeuristicAgent,  # heuristic:profile=exportador,level=dificil
}


def register(name: str, factory: AgentFactory) -> None:
    AGENTS[name] = factory


def _convert(value: str) -> object:
    for cast in (int, float):
        try:
            return cast(value)
        except ValueError:
            pass
    if value.lower() in ("true", "false"):
        return value.lower() == "true"
    return value


def parse_spec(spec: str) -> tuple[str, dict[str, object]]:
    name, _, params = spec.partition(":")
    kwargs: dict[str, object] = {}
    if params:
        for item in params.split(","):
            key, sep, value = item.partition("=")
            if not sep or not key:
                raise ValueError(f"parâmetro inválido em '{spec}': '{item}'")
            kwargs[key.strip()] = _convert(value.strip())
    return name.strip(), kwargs


def make_agent(spec: str, seed: int) -> Agent:
    name, kwargs = parse_spec(spec)
    if name not in AGENTS:
        raise ValueError(f"agente desconhecido '{name}'. Disponíveis: {', '.join(sorted(AGENTS))}")
    agent = AGENTS[name](seed=seed, **kwargs)
    agent.name = spec
    return agent
