"""Verificações de consistência do estado (usadas nos testes e para depuração)."""

from __future__ import annotations

from .data import (
    BUILDING_SLOTS,
    BUILDINGS,
    CITY_SPACES,
    GOOD_SUPPLY,
    ISLAND_SPACES,
    NUM_BUILDINGS,
    NUM_GOODS,
    NUM_SHIPS,
    NUM_TILE_TYPES,
    PLANTATION_COUNT,
    QUARRY,
    QUARRY_COUNT,
    SETUP,
    TRADING_HOUSE_SIZE,
)
from .state import GameState


def check_invariants(s: GameState) -> list[str]:
    """Devolve a lista de violações (vazia se o estado é consistente)."""
    errors: list[str] = []
    n = s.num_players
    setup = SETUP[n]
    players = range(n)

    total_col = s.colonist_supply + s.colonist_ship + sum(s.total_colonists(p) for p in players)
    if total_col != setup.colonists + setup.ship_colonists:
        errors.append(f"colonos: {total_col} != {setup.colonists + setup.ship_colonists}")

    for g in range(NUM_GOODS):
        on_ships = sum(s.ship_load[j] for j in range(NUM_SHIPS) if s.ship_good[j] == g)
        total = (
            s.goods_supply[g]
            + sum(s.goods[p][g] for p in players)
            + on_ships
            + s.trading_house.count(g)
        )
        if total != GOOD_SUPPLY[g]:
            errors.append(f"bem {g}: {total} != {GOOD_SUPPLY[g]}")
        if s.goods_supply[g] < 0:
            errors.append(f"reserva do bem {g} negativa")

    for t in range(NUM_GOODS):
        total = (
            s.plantation_stack.count(t)
            + s.plantation_discard.count(t)
            + s.faceup.count(t)
            + sum(s.island[p][t] for p in players)
        )
        if total != PLANTATION_COUNT[t]:
            errors.append(f"plantação {t}: {total} != {PLANTATION_COUNT[t]}")
    if s.quarry_supply + sum(s.island[p][QUARRY] for p in players) != QUARRY_COUNT:
        errors.append("pedreiras não conservadas")

    for b in range(NUM_BUILDINGS):
        if s.building_supply[b] + sum(s.city[p][b] for p in players) != BUILDINGS[b].copies:
            errors.append(f"prédio {b} não conservado")

    if s.vp_supply + sum(s.vp) != setup.vp_chips:
        errors.append("PV não conservados")

    for p in players:
        if s.money[p] < 0:
            errors.append(f"jogador {p}: dinheiro negativo")
        if min(s.goods[p]) < 0:
            errors.append(f"jogador {p}: bens negativos")
        if s.san_juan[p] < 0:
            errors.append(f"jogador {p}: San Juan negativo")
        if s.island_used(p) > ISLAND_SPACES:
            errors.append(f"jogador {p}: ilha com mais de 12 lotes")
        if s.city_used(p) > CITY_SPACES:
            errors.append(f"jogador {p}: cidade com mais de 12 espaços")
        for t in range(NUM_TILE_TYPES):
            if not 0 <= s.island_manned[p][t] <= s.island[p][t]:
                errors.append(f"jogador {p}: colonos inválidos no lote {t}")
        for b in range(NUM_BUILDINGS):
            limit = BUILDING_SLOTS[b] if s.city[p][b] else 0
            if not 0 <= s.city_manned[p][b] <= limit:
                errors.append(f"jogador {p}: colonos inválidos no prédio {b}")

    loaded = [s.ship_good[j] for j in range(NUM_SHIPS) if s.ship_good[j] >= 0]
    if len(loaded) != len(set(loaded)):
        errors.append("mesmo bem em dois navios")
    for j in range(NUM_SHIPS):
        if not 0 <= s.ship_load[j] <= s.ship_capacity[j]:
            errors.append(f"navio {j}: carga inválida")
        if (s.ship_load[j] == 0) != (s.ship_good[j] == -1):
            errors.append(f"navio {j}: bem e carga inconsistentes")
    if len(s.trading_house) > TRADING_HOUSE_SIZE:
        errors.append("casa de comércio lotada demais")
    if len(s.faceup) > n + 1:
        errors.append("plantações visíveis demais")
    if s.colonist_supply < 0 or s.colonist_ship < 0 or s.quarry_supply < 0:
        errors.append("reserva negativa")
    return errors
