"""Avaliação heurística de um estado: pontos finais estimados de cada jogador.

valor = pontos atuais (fichas + prédios + bônus)
      + dinheiro convertido em PV (vale mais no começo)
      + barris guardados
      + capacidade de produção futura × rodadas restantes
      + utilidade dos prédios violeta × rodadas restantes
      + preferências do perfil

Na partida terminada, o valor é exatamente a pontuação final.
"""

from __future__ import annotations

from ..engine import GameState
from ..engine.data import (
    BUILDING_SLOTS,
    CITY_SPACES,
    FACTORY_BONUS,
    GOOD_PRICE,
    NUM_GOODS,
    PRODUCTION_BY_GOOD,
    QUARRY,
    SETUP,
)
from ..engine.data import Building as B
from ..engine.scoring import building_points, score
from .profiles import Profile

TYPICAL_ROUNDS = 15.0
_LARGE = (B.GUILD_HALL, B.RESIDENCE, B.FORTRESS, B.CUSTOMS_HOUSE, B.CITY_HALL)

# utilidade por rodada (em PV) dos prédios violeta: (prédio, grupo do perfil, valor)
_UTILITY = (
    (B.SMALL_MARKET, "trade", 0.10),
    (B.LARGE_MARKET, "trade", 0.18),
    (B.OFFICE, "trade", 0.08),
    (B.HACIENDA, "production", 0.12),
    (B.HOSPICE, "production", 0.12),
    (B.CONSTRUCTION_HUT, "build", 0.06),
    (B.UNIVERSITY, "build", 0.15),
    (B.SMALL_WAREHOUSE, "ship", 0.10),
    (B.LARGE_WAREHOUSE, "ship", 0.18),
    (B.HARBOR, "ship", 0.40),
    (B.WHARF, "ship", 0.45),
)
UNMANNED_FACTOR = 0.6  # prédio/lote sem colono: deve receber um mais tarde


def progress(s: GameState) -> float:
    """Fração estimada da partida já jogada (0 a 1)."""
    setup = SETUP[s.num_players]
    t_vp = 1.0 - s.vp_supply / setup.vp_chips
    t_col = 1.0 - s.colonist_supply / setup.colonists
    t_city = max(s.city_used(p) for p in range(s.num_players)) / CITY_SPACES
    return min(1.0, max(t_vp, t_col, t_city, 0.0))


def remaining_rounds(s: GameState) -> float:
    if s.is_terminal:
        return 0.0
    if s.end_triggered:
        return 0.3
    return TYPICAL_ROUNDS * (1.0 - progress(s)) + 0.5


def evaluate(s: GameState, p: int, profile: Profile, rounds: float | None = None) -> float:
    R = remaining_rounds(s) if rounds is None else rounds
    value = float(score(s, p))
    if R <= 0.0:
        return value

    frac = min(1.0, R / TYPICAL_ROUNDS)
    # dinheiro vira prédios: vale bem até as últimas rodadas
    money_rate = 0.20 + 0.50 * min(1.0, R / 8.0)
    value += s.money[p] * money_rate
    # o estilo "construtor" valoriza os prédios (não o dinheiro guardado)
    value += (profile.build - 1.0) * building_points(s, p) * frac

    # valor de um barril de cada bem (embarque + venda)
    barrel = [
        0.6 * profile.ship + 0.7 * profile.trade * GOOD_PRICE[g] * money_rate
        for g in range(NUM_GOODS)
    ]
    goods = s.goods[p]
    value += sum(goods[g] * barrel[g] for g in range(NUM_GOODS))

    # produção: atual e potencial (plantações + prédios ainda sem colono)
    isl, im, row, cm = s.island[p], s.island_manned[p], s.city[p], s.city_manned[p]
    prod_rate = 0.35 * R * profile.production
    kinds = 0
    for g in range(NUM_GOODS):
        prod = s.production(p, g)
        if prod:
            kinds += 1
        if g == 0:
            pot = isl[0]
        else:
            cap = sum(BUILDING_SLOTS[b] for b in PRODUCTION_BY_GOOD[g] if row[b])
            pot = min(isl[g], cap)
        value += prod_rate * barrel[g] * (prod + 0.35 * max(0, pot - prod))

    # lotes da ilha e pedreiras
    value += 0.03 * R * sum(isl)
    quarry_value = money_rate * R * 0.3 * profile.build
    manned_q = min(im[QUARRY], 4)
    value += quarry_value * (manned_q + 0.4 * max(0, min(isl[QUARRY], 4) - manned_q))

    # prédios violeta
    weights = {
        "trade": profile.trade,
        "ship": profile.ship,
        "build": profile.build,
        "production": profile.production,
    }
    for b, group, per_round in _UTILITY:
        if row[b]:
            value += per_round * R * weights[group] * (1.0 if cm[b] else UNMANNED_FACTOR)
    if row[B.FACTORY]:
        bonus = FACTORY_BONUS[kinds] * money_rate * 0.3 * R
        value += bonus if cm[B.FACTORY] else UNMANNED_FACTOR * bonus
    for b in _LARGE:  # prédio grande sem colono ainda pode render bônus
        if row[b] and not cm[b]:
            value += 2.0
    value += 0.05 * R * s.san_juan[p]

    if profile.favorite_bonus:
        value += profile.favorite_bonus * frac * sum(1 for b in profile.favorites if row[b])
    return value


def evaluate_all(s: GameState, profile: Profile) -> list[float]:
    R = remaining_rounds(s)
    return [evaluate(s, p, profile, R) for p in range(s.num_players)]


def relative_value(values: list[float], p: int, aggression: float) -> float:
    """Valor do jogador p descontando parte da média dos adversários."""
    others = [v for q, v in enumerate(values) if q != p]
    return values[p] - aggression * (sum(others) / len(others))
