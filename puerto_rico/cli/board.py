"""Text rendering of the board, the players and the available actions."""

from __future__ import annotations

from ..engine import (
    WHARF,
    Action,
    ActionKind,
    GameState,
    Phase,
    building_cost,
    describe,
    sale_price,
)
from ..engine.data import (
    BUILDING_SLOTS,
    BUILDINGS,
    CITY_SPACES,
    GOOD_NAMES,
    ISLAND_SPACES,
    NUM_BUILDINGS,
    NUM_GOODS,
    NUM_SHIPS,
    NUM_TILE_TYPES,
    ROLE_NAMES,
    TILE_NAMES,
)
from ..engine.scoring import building_points

_PHASE_NAMES = {
    Phase.ROLE_SELECTION: "Role selection",
    Phase.SETTLER_HACIENDA: "Settler (Hacienda)",
    Phase.SETTLER: "Settler",
    Phase.MAYOR: "Mayor",
    Phase.BUILDER: "Builder",
    Phase.CRAFT_BONUS: "Craftsman (privilege)",
    Phase.TRADER: "Trader",
    Phase.CAPTAIN: "Captain",
    Phase.CAPTAIN_STORE: "Captain (storage)",
    Phase.GAME_OVER: "Game over",
}


def player_label(p: int, names: list[str]) -> str:
    return f"P{p + 1} {names[p]}"


def event_line(entry: tuple) -> str:
    """One narration line for a history entry (round, actor, role, action, forced)."""
    _round, actor, role, action, forced = entry
    context = f"[{ROLE_NAMES[role]}] " if role >= 0 else ""
    auto = " (forced)" if forced else ""
    return f"  P{actor + 1} {context}{describe(action)}{auto}"


def is_noise(entry: tuple) -> bool:
    """Forced moves that say nothing: automatic passes and storing nothing."""
    action, forced = entry[3], entry[4]
    if not forced:
        return False
    if action.kind == ActionKind.PASS:
        return True
    return action.kind == ActionKind.STORE and action.a == 0 and action.b < 0


def _goods_text(goods: list[int]) -> str:
    parts = [f"{GOOD_NAMES[g]} {goods[g]}" for g in range(NUM_GOODS) if goods[g]]
    return ", ".join(parts) if parts else "-"


def _island_text(s: GameState, p: int) -> str:
    isl, im = s.island[p], s.island_manned[p]
    parts = [f"{TILE_NAMES[t]} {im[t]}/{isl[t]}" for t in range(NUM_TILE_TYPES) if isl[t]]
    return (", ".join(parts) if parts else "-") + f"  ({s.island_used(p)}/{ISLAND_SPACES})"


def _city_text(s: GameState, p: int) -> str:
    row, cm = s.city[p], s.city_manned[p]
    parts = [
        f"{BUILDINGS[b].name} {cm[b]}/{BUILDING_SLOTS[b]}" for b in range(NUM_BUILDINGS) if row[b]
    ]
    used = s.city_used(p)
    return (", ".join(parts) if parts else "-") + f"  ({used}/{CITY_SPACES})"


def render_player(s: GameState, p: int, names: list[str], me: int) -> list[str]:
    you = " (you)" if p == me else ""
    gov = " [governor]" if p == s.governor else ""
    stats = (
        f"     ${s.money[p]}  VP chips {s.vp[p]}  building VP {building_points(s, p)}"
        f"  San Juan {s.san_juan[p]}  goods: {_goods_text(s.goods[p])}"
    )
    return [
        f"  {player_label(p, names)}{you}{gov}",
        stats,
        f"     island: {_island_text(s, p)}",
        f"     city:   {_city_text(s, p)}",
    ]


def _ship_text(s: GameState, j: int) -> str:
    good = GOOD_NAMES[s.ship_good[j]] if s.ship_good[j] >= 0 else "empty"
    return f"[{good} {s.ship_load[j]}/{s.ship_capacity[j]}]"


def render_header(s: GameState) -> str:
    phase = _PHASE_NAMES[s.phase]
    by = f" (chosen by P{s.role_player + 1})" if s.role_player >= 0 else ""
    return f"=== Round {s.round + 1} | Governor P{s.governor + 1} | {phase}{by} ==="


def render_supply(s: GameState) -> list[str]:
    roles = []
    for r in s.roles:
        name = ROLE_NAMES[r]
        if s.role_taken[r]:
            roles.append(f"({name})")
        elif s.role_money[r]:
            roles.append(f"{name}+{s.role_money[r]}$")
        else:
            roles.append(name)
    house = ", ".join(GOOD_NAMES[g] for g in s.trading_house) or "empty"
    faceup = ", ".join(GOOD_NAMES[t] for t in sorted(s.faceup)) or "-"
    ships = " ".join(_ship_text(s, j) for j in range(NUM_SHIPS))
    supply = (
        f"Supply: VP {s.vp_supply} | colonists {s.colonist_supply} (+{s.colonist_ship} on ship)"
        f" | quarries {s.quarry_supply} | goods {_goods_text(s.goods_supply)}"
    )
    return [
        f"Roles:  {' | '.join(roles)}   (taken in parentheses)",
        supply,
        f"Ships:  {ships}   Trading house: {house} ({len(s.trading_house)}/4)",
        f"Plantations: {faceup}   (stack {len(s.plantation_stack)})",
    ]


def render_buildings(s: GameState, me: int) -> list[str]:
    lines = ["Buildings available (base cost / VP / left -> your cost now):"]
    for col in range(1, 5):
        items = []
        for b in range(NUM_BUILDINGS):
            info = BUILDINGS[b]
            if info.column == col and s.building_supply[b] > 0:
                cost = building_cost(s, me, b)
                items.append(f"{info.name} {info.cost}/{info.vp}/x{s.building_supply[b]}->{cost}")
        if items:
            lines.append(f"  [{col}] " + "; ".join(items))
    return lines


def render_board(s: GameState, names: list[str], me: int, full: bool = False) -> str:
    lines = [render_header(s), *render_supply(s), "Players:"]
    for p in range(s.num_players):
        lines.extend(render_player(s, p, names, me))
    if full:
        lines.extend(render_buildings(s, me))
    return "\n".join(lines)


def action_label(s: GameState, a: Action) -> str:
    """describe() plus context useful for a human (cost, price, amount)."""
    p = s.actor
    k = a.kind
    if k == ActionKind.CHOOSE_ROLE and s.role_money[a.a]:
        return f"{describe(a)} (+{s.role_money[a.a]}$)"
    if k == ActionKind.BUILD:
        info = BUILDINGS[a.a]
        return f"{describe(a)} (cost {building_cost(s, p, a.a)}, {info.vp} VP)"
    if k == ActionKind.SELL:
        return f"{describe(a)} for {sale_price(s, p, a.a)}$"
    if k == ActionKind.SHIP:
        have = s.goods[p][a.a]
        amount = have if a.b == WHARF else min(have, s.ship_capacity[a.b] - s.ship_load[a.b])
        return f"{describe(a)} ({amount} barrels)"
    if k == ActionKind.PLACE:
        return f"{describe(a)} ({s.san_juan[p]} colonists left to place)"
    return describe(a)
