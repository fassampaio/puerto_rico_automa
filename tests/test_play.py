"""Interactive play with scripted input."""

import pytest
from helpers import choose, fresh, give_goods

from puerto_rico.cli.board import action_label, render_board
from puerto_rico.cli.play import HumanCLIAgent, QuitGame, play
from puerto_rico.engine import Action, ActionKind, Good, Role, legal_actions, new_game, step
from puerto_rico.runner import read_records, replay_record


class Script:
    """Feeds answers to input(); repeats the last one forever."""

    def __init__(self, *answers: str) -> None:
        self.answers = list(answers)
        self.prompts = 0

    def __call__(self, prompt: str) -> str:
        self.prompts += 1
        return self.answers.pop(0) if len(self.answers) > 1 else self.answers[0]


def test_full_game_against_bots_is_saved_and_replayable(tmp_path):
    lines: list[str] = []
    log = tmp_path / "game.jsonl"
    script = Script("1")
    result = play(
        num_players=3,
        seat=1,
        bots=["random", "heuristic:level=easy"],
        seed=7,
        name="Tester",
        log_path=log,
        input_fn=script,
        print_fn=lines.append,
    )
    assert result is not None and result.final_state.is_terminal
    assert script.prompts > 20
    text = "\n".join(lines)
    assert text.isascii()
    assert "Your move (P2" in text and "Final result" in text and "Round 1" in text
    (record,) = list(read_records(log))
    assert record["agents"][1] == "human:Tester"
    assert replay_record(record).round == result.final_state.round


def test_invalid_input_board_and_help():
    lines: list[str] = []
    names = ["You (human)", "bot", "bot", "bot"]
    agent = HumanCLIAgent(names, input_fn=Script("x", "99", "b", "h", "2"), print_fn=lines.append)
    s = new_game(4, 1)
    action = agent.choose(s, legal_actions(s))
    assert action == legal_actions(s)[1]
    text = "\n".join(lines)
    assert text.count("Invalid option.") == 2
    assert "Buildings available" in text and "Commands:" in text


def test_quit_returns_none():
    lines: list[str] = []
    result = play(num_players=3, seat=0, bots=["random", "random"], seed=1,
                  input_fn=Script("q"), print_fn=lines.append)
    assert result is None
    assert "Game abandoned." in lines[-1]


def test_quit_raises_inside_agent():
    agent = HumanCLIAgent(["a", "b", "c"], input_fn=Script("q"), print_fn=lambda _: None)
    s = new_game(3, 0)
    with pytest.raises(QuitGame):
        agent.choose(s, legal_actions(s))


def test_action_labels_show_costs_and_prices():
    s = fresh()
    give_goods(s, 0, [0, 0, 0, 0, 1])
    choose(s, Role.TRADER)
    labels = [action_label(s, a) for a in legal_actions(s)]
    assert "Sell coffee for 5$" in labels  # 4 + privilege
    s2 = fresh()
    choose(s2, Role.BUILDER)
    label = action_label(s2, Action(ActionKind.BUILD, 0))
    assert label == "Build Small Indigo Plant (cost 0, 1 VP)"


def test_board_mentions_every_player_and_ships():
    s = new_game(5, 3)
    text = render_board(s, [f"n{i}" for i in range(5)], me=2, full=True)
    for p in range(1, 6):
        assert f"P{p} " in text
    assert "[empty 0/6]" in text and "(you)" in text


def test_history_records_forced_moves():
    s = fresh()
    s.history = []
    give_goods(s, 0, [3, 0, 0, 0, 0])
    s.ship_good[0], s.ship_load[0] = Good.INDIGO, 1  # only ships 1 and 2 left for corn
    s.goods_supply[Good.INDIGO] -= 1
    s.ship_good[1], s.ship_load[1] = Good.SUGAR, 1
    s.goods_supply[Good.SUGAR] -= 1
    s.legal_cache = None
    choose(s, Role.CAPTAIN)  # the corn shipment is forced: applied automatically
    kinds = [entry[3].kind for entry in s.history]
    assert kinds[0] == ActionKind.CHOOSE_ROLE and ActionKind.SHIP in kinds
    assert s.clone().history is None
    step(s, legal_actions(s)[0])
