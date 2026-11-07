"""Motor de regras: criação da partida, jogadas válidas e transições de estado.

O motor é puro (sem I/O) e determinístico: uma partida é totalmente definida por
(num_players, seed, ações escolhidas). Decisões com uma única opção válida são
aplicadas automaticamente, então os agentes só são consultados em escolhas reais.
As interpretações de regras estão documentadas em ARQUITETURA.md.
"""

from __future__ import annotations

import random
from itertools import combinations

from .actions import PASS, PLACE_BUILDING_OFFSET, WHARF, Action
from .actions import ActionKind as K
from .config import RulesConfig
from .data import (
    BUILDING_SLOTS,
    BUILDINGS,
    CITY_SPACES,
    FACTORY_BONUS,
    GOOD_PRICE,
    GOOD_SUPPLY,
    ISLAND_SPACES,
    NUM_BUILDINGS,
    NUM_GOODS,
    NUM_ROLES,
    NUM_SHIPS,
    NUM_TILE_TYPES,
    PLANTATION_COUNT,
    QUARRY,
    QUARRY_COUNT,
    SETUP,
    TRADING_HOUSE_SIZE,
    Role,
)
from .data import Building as B
from .state import GameState, Phase


class IllegalActionError(ValueError):
    pass


# ======================================================================
# API pública
# ======================================================================


def new_game(num_players: int = 4, seed: int = 0, config: RulesConfig | None = None) -> GameState:
    cfg = config if config is not None else RulesConfig(num_players=num_players)
    n = cfg.num_players
    setup = SETUP[n]
    rng = random.Random(seed)

    island = [[0] * NUM_TILE_TYPES for _ in range(n)]
    remaining = list(PLANTATION_COUNT)
    for p, g in enumerate(setup.start_plantations):
        island[p][g] += 1
        remaining[g] -= 1
    stack = [g for g in range(NUM_GOODS) for _ in range(remaining[g])]
    rng.shuffle(stack)

    s = GameState(
        num_players=n,
        seed=seed,
        money=[setup.money] * n,
        vp=[0] * n,
        island=island,
        island_manned=[[0] * NUM_TILE_TYPES for _ in range(n)],
        city=[[0] * NUM_BUILDINGS for _ in range(n)],
        city_manned=[[0] * NUM_BUILDINGS for _ in range(n)],
        san_juan=[0] * n,
        goods=[[0] * NUM_GOODS for _ in range(n)],
        vp_supply=setup.vp_chips,
        colonist_supply=setup.colonists,
        colonist_ship=setup.ship_colonists,
        quarry_supply=QUARRY_COUNT,
        goods_supply=list(GOOD_SUPPLY),
        building_supply=[b.copies for b in BUILDINGS],
        plantation_stack=stack,
        plantation_discard=[],
        faceup=[],
        reshuffles=0,
        ship_capacity=list(setup.cargo_ships),
        ship_good=[-1] * NUM_SHIPS,
        ship_load=[0] * NUM_SHIPS,
        trading_house=[],
        roles=tuple(int(r) for r in setup.roles),
        role_money=[0] * NUM_ROLES,
        role_taken=[False] * NUM_ROLES,
        wharf_used=[False] * n,
    )
    _refill_faceup(s)
    _auto(s)
    return s


def legal_actions(s: GameState) -> list[Action]:
    if s.legal_cache is None:
        s.legal_cache = _compute_legal(s)
    return list(s.legal_cache)


def step(s: GameState, action: Action, validate: bool = True) -> None:
    """Aplica a ação no próprio estado e avança até a próxima decisão real."""
    if s.phase == Phase.GAME_OVER:
        raise IllegalActionError("a partida já terminou")
    if validate and action not in legal_actions(s):
        raise IllegalActionError(f"ação inválida em {s.phase.name}: {action!r}")
    _do(s, action)
    _auto(s)


def apply(s: GameState, action: Action, validate: bool = True) -> GameState:
    """Versão funcional de step: devolve um novo estado."""
    c = s.clone()
    step(c, action, validate)
    return c


def building_cost(s: GameState, p: int, b: int, privilege: bool | None = None) -> int:
    if privilege is None:
        privilege = s.current_role == Role.BUILDER and p == s.role_player
    info = BUILDINGS[b]
    discount = min(s.manned_quarries(p), info.column) + (1 if privilege else 0)
    return max(0, info.cost - discount)


def sale_price(s: GameState, p: int, g: int, privilege: bool | None = None) -> int:
    if privilege is None:
        privilege = s.current_role == Role.TRADER and p == s.role_player
    price = GOOD_PRICE[g] + (1 if privilege else 0)
    if s.is_manned(p, B.SMALL_MARKET):
        price += 1
    if s.is_manned(p, B.LARGE_MARKET):
        price += 2
    return price


def shipping_options(s: GameState, p: int) -> tuple[list[Action], list[Action]]:
    """(embarques em navios, embarques no Wharf) válidos para o jogador p."""
    cargo: list[Action] = []
    goods = s.goods[p]
    for g in range(NUM_GOODS):
        have = goods[g]
        if not have:
            continue
        best, ships = 0, []
        for j in range(NUM_SHIPS):
            sg = s.ship_good[j]
            if sg == g:
                room = s.ship_capacity[j] - s.ship_load[j]
            elif sg == -1 and g not in s.ship_good:
                room = s.ship_capacity[j]
            else:
                continue
            amount = min(have, room)
            if amount <= 0:
                continue
            if amount > best:
                best, ships = amount, [j]
            elif amount == best:
                ships.append(j)
        cargo.extend(Action(K.SHIP, g, j) for j in ships)
    wharf: list[Action] = []
    if s.is_manned(p, B.WHARF) and not s.wharf_used[p]:
        wharf = [Action(K.SHIP, g, WHARF) for g in range(NUM_GOODS) if goods[g]]
    return cargo, wharf


# ======================================================================
# Laço interno
# ======================================================================


def _auto(s: GameState) -> None:
    while s.phase != Phase.GAME_OVER:
        acts = _compute_legal(s)
        if len(acts) != 1:
            s.legal_cache = acts
            return
        _do(s, acts[0])
    s.legal_cache = []


def _compute_legal(s: GameState) -> list[Action]:
    ph = s.phase
    if ph == Phase.ROLE_SELECTION:
        return [Action(K.CHOOSE_ROLE, r) for r in s.roles if not s.role_taken[r]]
    if ph == Phase.SETTLER_HACIENDA:
        return [Action(K.HACIENDA), PASS]
    if ph == Phase.SETTLER:
        return _settler_legal(s)
    if ph == Phase.MAYOR:
        return _mayor_legal(s)
    if ph == Phase.BUILDER:
        return _builder_legal(s)
    if ph == Phase.CRAFT_BONUS:
        return [Action(K.CRAFT_BONUS, g) for g in s.craft_options]
    if ph == Phase.TRADER:
        return _trader_legal(s)
    if ph == Phase.CAPTAIN:
        cargo, wharf = shipping_options(s, s.actor)
        return cargo + wharf + ([] if cargo else [PASS])
    if ph == Phase.CAPTAIN_STORE:
        return _store_legal(s)
    return []


def _do(s: GameState, a: Action) -> None:
    s.legal_cache = None
    ph = s.phase
    if ph == Phase.ROLE_SELECTION:
        _choose_role(s, a.a)
    elif ph == Phase.SETTLER_HACIENDA:
        _do_hacienda(s, a)
    elif ph == Phase.SETTLER:
        _do_settle(s, a)
    elif ph == Phase.MAYOR:
        _do_place(s, a.a)
    elif ph == Phase.BUILDER:
        _do_build(s, a)
    elif ph == Phase.CRAFT_BONUS:
        _do_craft_bonus(s, a.a)
    elif ph == Phase.TRADER:
        _do_sell(s, a)
    elif ph == Phase.CAPTAIN:
        _do_ship(s, a)
    elif ph == Phase.CAPTAIN_STORE:
        _do_store(s, a)
    else:
        raise IllegalActionError("a partida já terminou")


def _player_at(s: GameState, offset: int) -> int:
    return (s.role_player + offset) % s.num_players


# ======================================================================
# Escolha de papéis e rodadas
# ======================================================================


def _choose_role(s: GameState, r: int) -> None:
    p = s.actor
    s.money[p] += s.role_money[r]
    s.role_money[r] = 0
    s.role_taken[r] = True
    s.role_player = p
    s.current_role = r
    s.turn = 0
    if r == Role.SETTLER:
        s.hacienda_done = False
        _settler_next(s)
    elif r == Role.MAYOR:
        _mayor_begin(s)
    elif r == Role.BUILDER:
        _builder_next(s)
    elif r == Role.CRAFTSMAN:
        _craftsman_begin(s)
    elif r == Role.TRADER:
        _trader_next(s)
    elif r == Role.CAPTAIN:
        _captain_begin(s)
    else:  # Garimpeiro
        s.money[p] += 1
        _finish_role(s)


def _finish_role(s: GameState) -> None:
    s.picks += 1
    s.current_role = -1
    s.role_player = -1
    if s.picks < s.num_players:
        s.phase = Phase.ROLE_SELECTION
        s.actor = (s.governor + s.picks) % s.num_players
        return
    _end_round(s)


def _end_round(s: GameState) -> None:
    if s.end_triggered:
        s.phase = Phase.GAME_OVER
        s.actor = -1
        return
    for r in s.roles:
        if s.role_taken[r]:
            s.role_taken[r] = False
        else:
            s.role_money[r] += 1
    s.governor = (s.governor + 1) % s.num_players
    s.picks = 0
    s.round += 1
    s.phase = Phase.ROLE_SELECTION
    s.actor = s.governor


def _take_colonist(s: GameState) -> bool:
    """Colono para Hospice/University: da reserva; se vazia, do navio."""
    if s.colonist_supply > 0:
        s.colonist_supply -= 1
        return True
    if s.colonist_ship > 0:
        s.colonist_ship -= 1
        return True
    return False


# ======================================================================
# Colono (Settler)
# ======================================================================


def _draw(s: GameState) -> int | None:
    if not s.plantation_stack:
        if not s.plantation_discard:
            return None
        rng = random.Random(s.seed * 1_000_003 + s.reshuffles + 1)
        s.reshuffles += 1
        s.plantation_stack = s.plantation_discard
        s.plantation_discard = []
        rng.shuffle(s.plantation_stack)
    return s.plantation_stack.pop()


def _refill_faceup(s: GameState) -> None:
    for _ in range(s.num_players + 1):
        t = _draw(s)
        if t is None:
            break
        s.faceup.append(t)


def _settler_next(s: GameState) -> None:
    n = s.num_players
    while s.turn < n:
        p = _player_at(s, s.turn)
        if s.island_used(p) >= ISLAND_SPACES:
            s.turn += 1
            s.hacienda_done = False
            continue
        s.actor = p
        if (
            not s.hacienda_done
            and s.is_manned(p, B.HACIENDA)
            and (s.plantation_stack or s.plantation_discard)
        ):
            s.phase = Phase.SETTLER_HACIENDA
        else:
            s.phase = Phase.SETTLER
        return
    s.plantation_discard.extend(s.faceup)
    s.faceup = []
    _refill_faceup(s)
    _finish_role(s)


def _settler_legal(s: GameState) -> list[Action]:
    p = s.actor
    acts = [Action(K.SETTLE, t) for t in sorted(set(s.faceup))]
    if s.quarry_supply > 0 and (p == s.role_player or s.is_manned(p, B.CONSTRUCTION_HUT)):
        acts.append(Action(K.QUARRY))
    acts.append(PASS)
    return acts


def _do_hacienda(s: GameState, a: Action) -> None:
    if a.kind == K.HACIENDA:
        t = _draw(s)
        if t is not None:
            s.island[s.actor][t] += 1
    s.hacienda_done = True
    _settler_next(s)


def _do_settle(s: GameState, a: Action) -> None:
    p = s.actor
    tile = -1
    if a.kind == K.SETTLE:
        tile = a.a
        s.faceup.remove(tile)
    elif a.kind == K.QUARRY:
        tile = QUARRY
        s.quarry_supply -= 1
    if tile >= 0:
        s.island[p][tile] += 1
        if s.is_manned(p, B.HOSPICE) and _take_colonist(s):
            s.island_manned[p][tile] += 1
    s.turn += 1
    s.hacienda_done = False
    _settler_next(s)


# ======================================================================
# Prefeito (Mayor)
# ======================================================================


def _mayor_begin(s: GameState) -> None:
    n, rp = s.num_players, s.role_player
    if s.colonist_supply > 0:  # privilégio
        s.colonist_supply -= 1
        s.san_juan[rp] += 1
    i = 0
    while s.colonist_ship > 0:
        s.san_juan[(rp + i) % n] += 1
        s.colonist_ship -= 1
        i += 1
    _mayor_next(s)


def _mayor_next(s: GameState) -> None:
    n = s.num_players
    while s.turn < n:
        p = _player_at(s, s.turn)
        isl, im = s.island[p], s.island_manned[p]
        row, cm = s.city[p], s.city_manned[p]
        pool = s.san_juan[p] + sum(im) + sum(cm)
        cap = s.colonist_capacity(p)
        if pool >= cap:  # sem escolha: tudo ocupado
            for t in range(NUM_TILE_TYPES):
                im[t] = isl[t]
            for b in range(NUM_BUILDINGS):
                cm[b] = BUILDING_SLOTS[b] if row[b] else 0
            s.san_juan[p] = pool - cap
            s.turn += 1
            continue
        for t in range(NUM_TILE_TYPES):
            im[t] = 0
        for b in range(NUM_BUILDINGS):
            cm[b] = 0
        s.san_juan[p] = pool
        if pool == 0:
            s.turn += 1
            continue
        s.phase = Phase.MAYOR
        s.actor = p
        s.mayor_last = 0
        return
    _mayor_end(s)


def _mayor_legal(s: GameState) -> list[Action]:
    p = s.actor
    pool = s.san_juan[p]
    free = s.free_slots(p)
    suffix = [0] * (len(free) + 1)
    for i in range(len(free) - 1, -1, -1):
        suffix[i] = suffix[i + 1] + free[i]
    # ordem canônica (alvos não decrescentes) e só alvos que deixam lugar para o resto
    return [
        Action(K.PLACE, code)
        for code in range(s.mayor_last, len(free))
        if free[code] > 0 and suffix[code] >= pool
    ]


def _do_place(s: GameState, code: int) -> None:
    p = s.actor
    if code < PLACE_BUILDING_OFFSET:
        s.island_manned[p][code] += 1
    else:
        s.city_manned[p][code - PLACE_BUILDING_OFFSET] += 1
    s.san_juan[p] -= 1
    s.mayor_last = code
    if s.san_juan[p] == 0:
        s.turn += 1
        _mayor_next(s)


def _mayor_end(s: GameState) -> None:
    empty = 0
    for p in range(s.num_players):
        row, cm = s.city[p], s.city_manned[p]
        for b in range(NUM_BUILDINGS):
            if row[b]:
                empty += BUILDING_SLOTS[b] - cm[b]
    need = max(s.num_players, empty)
    if s.colonist_supply >= need:
        s.colonist_ship = need
        s.colonist_supply -= need
    else:
        s.colonist_ship = s.colonist_supply
        s.colonist_supply = 0
        s.end_triggered = True
    _finish_role(s)


# ======================================================================
# Construtor (Builder)
# ======================================================================


def _builder_next(s: GameState) -> None:
    if s.turn >= s.num_players:
        _finish_role(s)
        return
    s.phase = Phase.BUILDER
    s.actor = _player_at(s, s.turn)


def _builder_legal(s: GameState) -> list[Action]:
    p = s.actor
    free_city = CITY_SPACES - s.city_used(p)
    money = s.money[p]
    privilege = p == s.role_player
    acts = [
        Action(K.BUILD, b)
        for b in range(NUM_BUILDINGS)
        if s.building_supply[b] > 0
        and not s.city[p][b]
        and BUILDINGS[b].size <= free_city
        and building_cost(s, p, b, privilege) <= money
    ]
    acts.append(PASS)
    return acts


def _do_build(s: GameState, a: Action) -> None:
    p = s.actor
    if a.kind == K.BUILD:
        b = a.a
        s.money[p] -= building_cost(s, p, b, p == s.role_player)
        s.building_supply[b] -= 1
        s.city[p][b] = 1
        if s.is_manned(p, B.UNIVERSITY) and _take_colonist(s):
            s.city_manned[p][b] = 1
        if s.city_used(p) >= CITY_SPACES:
            s.end_triggered = True
    s.turn += 1
    _builder_next(s)


# ======================================================================
# Artesão (Craftsman)
# ======================================================================


def _craftsman_begin(s: GameState) -> None:
    n, rp = s.num_players, s.role_player
    produced_by_rp: list[int] = []
    for i in range(n):
        p = (rp + i) % n
        kinds = 0
        for g in range(NUM_GOODS):
            amount = min(s.production(p, g), s.goods_supply[g])
            if amount > 0:
                s.goods[p][g] += amount
                s.goods_supply[g] -= amount
                kinds += 1
                if p == rp:
                    produced_by_rp.append(g)
        if kinds >= 2 and s.is_manned(p, B.FACTORY):
            s.money[p] += FACTORY_BONUS[kinds]
    s.craft_options = [g for g in produced_by_rp if s.goods_supply[g] > 0]
    if s.craft_options:
        s.phase = Phase.CRAFT_BONUS
        s.actor = rp
        return
    _finish_role(s)


def _do_craft_bonus(s: GameState, g: int) -> None:
    s.goods[s.actor][g] += 1
    s.goods_supply[g] -= 1
    s.craft_options = []
    _finish_role(s)


# ======================================================================
# Comerciante (Trader)
# ======================================================================


def _trader_next(s: GameState) -> None:
    if s.turn >= s.num_players:
        if len(s.trading_house) >= TRADING_HOUSE_SIZE:
            for g in s.trading_house:
                s.goods_supply[g] += 1
            s.trading_house = []
        _finish_role(s)
        return
    s.phase = Phase.TRADER
    s.actor = _player_at(s, s.turn)


def _trader_legal(s: GameState) -> list[Action]:
    p = s.actor
    acts = []
    if len(s.trading_house) < TRADING_HOUSE_SIZE:
        office = s.is_manned(p, B.OFFICE)
        acts = [
            Action(K.SELL, g)
            for g in range(NUM_GOODS)
            if s.goods[p][g] > 0 and (office or g not in s.trading_house)
        ]
    acts.append(PASS)
    return acts


def _do_sell(s: GameState, a: Action) -> None:
    p = s.actor
    if a.kind == K.SELL:
        g = a.a
        s.money[p] += sale_price(s, p, g, p == s.role_player)
        s.goods[p][g] -= 1
        s.trading_house.append(g)
    s.turn += 1
    _trader_next(s)


# ======================================================================
# Capitão (Captain)
# ======================================================================


def _captain_begin(s: GameState) -> None:
    s.captain_idle = 0
    s.captain_privilege_used = False
    s.wharf_used = [False] * s.num_players
    _captain_next(s)


def _captain_next(s: GameState) -> None:
    n = s.num_players
    while s.captain_idle < n:
        p = _player_at(s, s.turn)
        cargo, wharf = shipping_options(s, p)
        if cargo or wharf:
            s.phase = Phase.CAPTAIN
            s.actor = p
            return
        s.captain_idle += 1
        s.turn += 1
    _captain_cleanup(s)


def _do_ship(s: GameState, a: Action) -> None:
    p = s.actor
    if a.kind == K.PASS:  # só possível quando a única opção é o Wharf
        s.captain_idle += 1
        s.turn += 1
        _captain_next(s)
        return
    g, j = a.a, a.b
    if j == WHARF:
        amount = s.goods[p][g]
        s.goods_supply[g] += amount
        s.wharf_used[p] = True
    else:
        amount = min(s.goods[p][g], s.ship_capacity[j] - s.ship_load[j])
        s.ship_load[j] += amount
        s.ship_good[j] = g
    s.goods[p][g] -= amount
    gain = amount
    if s.is_manned(p, B.HARBOR):
        gain += 1
    if p == s.role_player and not s.captain_privilege_used:
        s.captain_privilege_used = True
        gain += 1
    s.vp[p] += gain
    s.vp_supply -= gain
    if s.vp_supply <= 0:
        s.end_triggered = True
    s.captain_idle = 0
    s.turn += 1
    _captain_next(s)


def _captain_cleanup(s: GameState) -> None:
    for j in range(NUM_SHIPS):
        if s.ship_load[j] >= s.ship_capacity[j]:
            s.goods_supply[s.ship_good[j]] += s.ship_load[j]
            s.ship_load[j] = 0
            s.ship_good[j] = -1
    s.turn = 0
    _store_next(s)


def _store_next(s: GameState) -> None:
    if s.turn >= s.num_players:
        _finish_role(s)
        return
    s.phase = Phase.CAPTAIN_STORE
    s.actor = _player_at(s, s.turn)


def _warehouse_capacity(s: GameState, p: int) -> int:
    return (1 if s.is_manned(p, B.SMALL_WAREHOUSE) else 0) + (
        2 if s.is_manned(p, B.LARGE_WAREHOUSE) else 0
    )


def _store_legal(s: GameState) -> list[Action]:
    p = s.actor
    types = [g for g in range(NUM_GOODS) if s.goods[p][g] > 0]
    w = _warehouse_capacity(s, p)
    if len(types) <= w:
        return [Action(K.STORE, sum(1 << g for g in types), -1)]
    acts = []
    for combo in combinations(types, w):
        mask = sum(1 << g for g in combo)
        for g in types:
            if g not in combo:
                acts.append(Action(K.STORE, mask, g))
    return acts


def _do_store(s: GameState, a: Action) -> None:
    p = s.actor
    goods = s.goods[p]
    for g in range(NUM_GOODS):
        if a.a >> g & 1:
            keep = goods[g]
        elif g == a.b:
            keep = min(1, goods[g])
        else:
            keep = 0
        s.goods_supply[g] += goods[g] - keep
        goods[g] = keep
    s.turn += 1
    _store_next(s)
