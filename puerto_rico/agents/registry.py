"""Agent registry: builds agents from text specifications.

Format: ``name`` or ``name:param=value,param2=value`` (e.g. ``heuristic:level=hard``).
The full specification becomes the agent name in records and summaries.
Agents always receive a ``seed`` so tournaments are reproducible.
"""

from __future__ import annotations

from collections.abc import Callable

from .base import Agent
from .heuristic import HeuristicAgent
from .random_agent import RandomAgent

AgentFactory = Callable[..., Agent]

AGENTS: dict[str, AgentFactory] = {
    "random": RandomAgent,
    "heuristic": HeuristicAgent,  # heuristic:profile=shipper,level=hard
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
                raise ValueError(f"invalid parameter in '{spec}': '{item}'")
            kwargs[key.strip()] = _convert(value.strip())
    return name.strip(), kwargs


def make_agent(spec: str, seed: int) -> Agent:
    name, kwargs = parse_spec(spec)
    if name not in AGENTS:
        raise ValueError(f"unknown agent '{name}'. Available: {', '.join(sorted(AGENTS))}")
    agent = AGENTS[name](seed=seed, **kwargs)
    agent.name = spec
    return agent
