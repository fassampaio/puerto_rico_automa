"""Estatísticas incrementais de torneios (não guarda as partidas na memória)."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field


@dataclass
class AgentStats:
    games: int = 0  # participações (um agente pode ocupar vários assentos)
    wins: float = 0.0  # empates dividem a vitória
    score_sum: int = 0
    rank_sum: int = 0

    @property
    def win_rate(self) -> float:
        return self.wins / self.games if self.games else 0.0

    @property
    def avg_score(self) -> float:
        return self.score_sum / self.games if self.games else 0.0

    @property
    def avg_rank(self) -> float:
        return self.rank_sum / self.games if self.games else 0.0


@dataclass
class TournamentSummary:
    games: int = 0
    num_players: int = 0
    rounds_sum: int = 0
    agents: dict[str, AgentStats] = field(default_factory=lambda: defaultdict(AgentStats))
    seat_wins: Counter = field(default_factory=Counter)
    end_reasons: Counter = field(default_factory=Counter)

    def add(self, record: dict) -> None:
        self.games += 1
        self.num_players = record["num_players"]
        self.rounds_sum += record["rounds"]
        share = 1.0 / len(record["winners"])
        for w in record["winners"]:
            self.seat_wins[w] += share
        for reason in record["end_reasons"]:
            self.end_reasons[reason] += 1
        for pl in record["players"]:
            st = self.agents[pl["agent"]]
            st.games += 1
            st.score_sum += pl["score"]
            st.rank_sum += pl["rank"]
            if pl["seat"] in record["winners"]:
                st.wins += share

    def format(self) -> str:
        if not self.games:
            return "Nenhuma partida."
        avg_rounds = self.rounds_sum / self.games
        w = max(12, *(len(name) for name in self.agents))
        lines = [
            f"{self.games} partidas · {self.num_players} jogadores · {avg_rounds:.1f} rodadas",
            "",
            f"{'Agente':<{w}} {'Partic.':>8} {'Vitórias':>9} {'Taxa':>7} {'Pontos':>7} {'Posição':>8}",
        ]
        ordered = sorted(self.agents.items(), key=lambda kv: kv[1].win_rate, reverse=True)
        for name, st in ordered:
            lines.append(
                f"{name:<{w}} {st.games:>8} {st.wins:>9.1f} {st.win_rate:>6.1%} "
                f"{st.avg_score:>7.1f} {st.avg_rank:>8.2f}"
            )
        lines.append("")
        seats = " · ".join(
            f"J{s + 1} {self.seat_wins[s] / self.games:.1%}" for s in range(self.num_players)
        )
        lines.append(f"Vitórias por assento: {seats}")
        reasons = " · ".join(
            f"{_REASON_NAMES.get(r, r)} {c / self.games:.0%}"
            for r, c in self.end_reasons.most_common()
        )
        lines.append(f"Fim de jogo por: {reasons}")
        return "\n".join(lines)


_REASON_NAMES = {
    "vp_exhausted": "PV esgotados",
    "city_full": "cidade cheia",
    "colonists_exhausted": "colonos esgotados",
}
