"""Complete state of a game."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum

from .data import (
    BUILDING_SIZE,
    BUILDING_SLOTS,
    NUM_BUILDINGS,
    NUM_TILE_TYPES,
    PRODUCTION_BY_GOOD,
    QUARRY,
    Good,
)


class Phase(IntEnum):
    ROLE_SELECTION = 0
    SETTLER_HACIENDA = 1
    SETTLER = 2
    MAYOR = 3
    BUILDER = 4
    CRAFT_BONUS = 5
    TRADER = 6
    CAPTAIN = 7
    CAPTAIN_STORE = 8
    GAME_OVER = 9


@dataclass(slots=True, eq=False)
class GameState:
    num_players: int
    seed: int
    # --- per player ---
    money: list[int]
    vp: list[int]  # VP chips
    island: list[list[int]]  # [p][tile type] count (type 5 = quarry)
    island_manned: list[list[int]]  # [p][tile type] how many of those tiles have a colonist
    city: list[list[int]]  # [p][building] 0/1
    city_manned: list[list[int]]  # [p][building] colonists in the building
    san_juan: list[int]  # colonists without a place
    goods: list[list[int]]  # [p][good]
    # --- supplies and board ---
    vp_supply: int  # may go negative (VP awarded beyond the supply)
    colonist_supply: int
    colonist_ship: int
    quarry_supply: int
    goods_supply: list[int]
    building_supply: list[int]
    plantation_stack: list[int]  # top = end of the list
    plantation_discard: list[int]
    faceup: list[int]
    reshuffles: int
    ship_capacity: list[int]
    ship_good: list[int]  # -1 = empty
    ship_load: list[int]
    trading_house: list[int]
    roles: tuple[int, ...]  # roles in play
    role_money: list[int]  # [role] accumulated doubloons
    role_taken: list[bool]
    # --- flow ---
    governor: int = 0
    picks: int = 0  # roles chosen this round
    round: int = 0
    phase: Phase = Phase.ROLE_SELECTION
    actor: int = 0
    role_player: int = -1  # who chose the role being resolved
    current_role: int = -1
    turn: int = 0  # offset from role_player within the current phase
    end_triggered: bool = False
    end_reasons: list[str] = field(default_factory=list)  # see rules.END_*
    hacienda_done: bool = False
    mayor_last: int = 0
    craft_options: list[int] = field(default_factory=list)
    captain_idle: int = 0  # consecutive players who did not ship
    captain_privilege_used: bool = False
    wharf_used: list[bool] = field(default_factory=list)
    legal_cache: list | None = None

    def clone(self) -> GameState:
        return GameState(
            num_players=self.num_players,
            seed=self.seed,
            money=self.money[:],
            vp=self.vp[:],
            island=[r[:] for r in self.island],
            island_manned=[r[:] for r in self.island_manned],
            city=[r[:] for r in self.city],
            city_manned=[r[:] for r in self.city_manned],
            san_juan=self.san_juan[:],
            goods=[r[:] for r in self.goods],
            vp_supply=self.vp_supply,
            colonist_supply=self.colonist_supply,
            colonist_ship=self.colonist_ship,
            quarry_supply=self.quarry_supply,
            goods_supply=self.goods_supply[:],
            building_supply=self.building_supply[:],
            plantation_stack=self.plantation_stack[:],
            plantation_discard=self.plantation_discard[:],
            faceup=self.faceup[:],
            reshuffles=self.reshuffles,
            ship_capacity=self.ship_capacity[:],
            ship_good=self.ship_good[:],
            ship_load=self.ship_load[:],
            trading_house=self.trading_house[:],
            roles=self.roles,
            role_money=self.role_money[:],
            role_taken=self.role_taken[:],
            governor=self.governor,
            picks=self.picks,
            round=self.round,
            phase=self.phase,
            actor=self.actor,
            role_player=self.role_player,
            current_role=self.current_role,
            turn=self.turn,
            end_triggered=self.end_triggered,
            end_reasons=self.end_reasons[:],
            hacienda_done=self.hacienda_done,
            mayor_last=self.mayor_last,
            craft_options=self.craft_options[:],
            captain_idle=self.captain_idle,
            captain_privilege_used=self.captain_privilege_used,
            wharf_used=self.wharf_used[:],
            legal_cache=self.legal_cache,  # never mutated in place
        )

    # --- queries ---
    @property
    def is_terminal(self) -> bool:
        return self.phase == Phase.GAME_OVER

    def is_manned(self, p: int, b: int) -> bool:
        return self.city_manned[p][b] > 0

    def island_used(self, p: int) -> int:
        return sum(self.island[p])

    def city_used(self, p: int) -> int:
        row = self.city[p]
        return sum(BUILDING_SIZE[b] for b in range(NUM_BUILDINGS) if row[b])

    def manned_quarries(self, p: int) -> int:
        return self.island_manned[p][QUARRY]

    def production(self, p: int, g: int) -> int:
        """Barrels of good g the player would produce in the Craftsman phase."""
        manned = self.island_manned[p][g]
        if g == Good.CORN:
            return manned
        cm = self.city_manned[p]
        return min(manned, sum(cm[b] for b in PRODUCTION_BY_GOOD[g]))

    def colonist_capacity(self, p: int) -> int:
        row = self.city[p]
        return sum(self.island[p]) + sum(
            BUILDING_SLOTS[b] for b in range(NUM_BUILDINGS) if row[b]
        )

    def total_colonists(self, p: int) -> int:
        return self.san_juan[p] + sum(self.island_manned[p]) + sum(self.city_manned[p])

    def free_slots(self, p: int) -> list[int]:
        """Free colonist slots per Mayor target (0-5 island tiles, 6+ buildings)."""
        isl, im = self.island[p], self.island_manned[p]
        row, cm = self.city[p], self.city_manned[p]
        free = [isl[t] - im[t] for t in range(NUM_TILE_TYPES)]
        free.extend(
            (BUILDING_SLOTS[b] - cm[b]) if row[b] else 0 for b in range(NUM_BUILDINGS)
        )
        return free
