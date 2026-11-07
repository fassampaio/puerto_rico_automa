"""Perfis de estilo e níveis de dificuldade dos bots."""

from __future__ import annotations

from dataclasses import dataclass

from ..engine.data import Building as B


@dataclass(frozen=True)
class Profile:
    """Pesos de estilo usados pela função de avaliação (1.0 = neutro)."""

    name: str
    ship: float = 1.0  # valor de transformar barris em PV (embarque)
    trade: float = 1.0  # valor de transformar barris em dinheiro (comércio)
    build: float = 1.0  # valor dos prédios e das pedreiras
    production: float = 1.0  # valor da capacidade de produção
    aggression: float = 0.6  # quanto os ganhos dos adversários pesam contra
    favorites: tuple[int, ...] = ()  # prédios preferidos
    favorite_bonus: float = 0.0  # bônus por prédio preferido possuído


PROFILES: dict[str, Profile] = {
    p.name: p
    for p in (
        Profile("equilibrado"),
        Profile(
            "exportador",
            ship=1.4,
            trade=0.7,
            build=0.9,
            favorites=(B.HARBOR, B.WHARF, B.SMALL_WAREHOUSE, B.LARGE_WAREHOUSE),
            favorite_bonus=0.7,
        ),
        Profile(
            "construtor",
            ship=0.8,
            build=1.3,
            production=1.1,
            favorites=(B.UNIVERSITY, B.FACTORY, B.CONSTRUCTION_HUT, B.GUILD_HALL, B.CITY_HALL),
            favorite_bonus=0.7,
        ),
        Profile(
            "comerciante",
            ship=0.85,
            trade=1.3,
            favorites=(B.SMALL_MARKET, B.LARGE_MARKET, B.OFFICE, B.COFFEE_ROASTER),
            favorite_bonus=0.7,
        ),
    )
}


@dataclass(frozen=True)
class Level:
    name: str
    temperature: float  # 0 = sempre a melhor jogada; maior = mais aleatório
    lookahead: bool  # simula a fase inteira ao escolher papéis
    mayor_planning: bool  # planeja a alocação completa de colonos no Prefeito


LEVELS: dict[str, Level] = {
    lv.name: lv
    for lv in (
        Level("facil", temperature=1.5, lookahead=False, mayor_planning=False),
        Level("medio", temperature=0.8, lookahead=True, mayor_planning=False),
        Level("dificil", temperature=0.0, lookahead=True, mayor_planning=True),
    )
}


def get_profile(name: str) -> Profile:
    if name not in PROFILES:
        raise ValueError(f"perfil desconhecido '{name}'. Disponíveis: {', '.join(PROFILES)}")
    return PROFILES[name]


def get_level(name: str) -> Level:
    if name not in LEVELS:
        raise ValueError(f"nível desconhecido '{name}'. Disponíveis: {', '.join(LEVELS)}")
    return LEVELS[name]
