"""Behavioral tests for the public Qt-independent game engine."""

from collections.abc import Sequence
from dataclasses import FrozenInstanceError
from pathlib import Path
import random
import subprocess
import sys

import pytest

from src.core import (
    Board,
    Dice,
    Game,
    GameEngine,
    GameState,
    Pawn,
    Player,
    PlayerColor,
)
from src.core.exceptions import (
    GameOverError,
    InvalidMoveError,
    InvalidRollError,
    InvalidSetupError,
    InvalidTurnError,
)


class ScriptedDice(Dice):
    """Supply known results without relying on random luck."""

    def __init__(self, rolls: Sequence[int]) -> None:
        self._rolls = iter(rolls)

    def roll(self) -> int:
        return next(self._rolls)


def scenario(
    rolls: Sequence[int],
    positions: tuple[tuple[int, ...], ...] = (
        (-1, -1, -1, -1), (-1, -1, -1, -1)
    ),
    colors: tuple[PlayerColor, ...] = (PlayerColor.RED, PlayerColor.BLUE),
) -> GameEngine:
    """Build a validated snapshot for a focused board scenario."""
    assert len(positions) == len(colors)
    players = tuple(
        Player(color, tuple(Pawn(i, step) for i, step in enumerate(row)))
        for color, row in zip(colors, positions, strict=True)
    )
    return GameEngine.from_state(
        GameState(players), dice=ScriptedDice(rolls)
    )


@pytest.mark.parametrize("count", [2, 3, 4])
def test_new_game_initializes_four_base_pawns_per_player(count: int) -> None:
    colors = tuple(PlayerColor)[:count]
    game = GameEngine(colors)
    assert len(game.state.players) == count
    assert game.active_player.color == colors[0]
    assert game.state.pending_roll is None
    assert game.winner is None
    assert game.legal_moves() == ()
    for player in game.state.players:
        assert tuple(pawn.id for pawn in player.pawns) == (0, 1, 2, 3)
        assert all(pawn.in_base for pawn in player.pawns)


def test_color_offsets_are_independent_of_roster_order() -> None:
    game = GameEngine(("yellow", "blue"))
    assert game.active_player.starting_offset == 39
    assert game.state.players[1].starting_offset == 13
    assert Game is GameEngine


@pytest.mark.parametrize("roll", range(1, 6))
def test_non_six_cannot_leave_base_and_automatically_passes(roll: int) -> None:
    game = scenario([roll])
    before = game.state
    assert game.roll_dice() == roll
    assert game.state.players == before.players
    assert game.active_player.color == PlayerColor.BLUE
    assert game.state.pending_roll is None
    assert game.legal_moves() == ()
    with pytest.raises(InvalidTurnError):
        game.move_pawn(0)


def test_six_leaves_base_at_zero_and_preserves_the_extra_roll() -> None:
    game = scenario([6, 3])
    assert game.roll_dice() == 6
    assert game.legal_moves() == (0, 1, 2, 3)
    game.move_pawn(2)
    assert game.active_player.color == PlayerColor.RED
    assert tuple(p.progress for p in game.active_player.pawns) == (
        -1, -1, 0, -1
    )
    assert game.state.pending_roll is None
    game.roll_dice()
    assert game.legal_moves() == (2,)
    game.move_pawn(2)
    assert game.state.players[0].pawns[2].progress == 3
    assert game.active_player.color == PlayerColor.BLUE


def test_normal_movement_consumes_roll_and_switches_player() -> None:
    game = scenario([3], ((5, -1, -1, -1), (8, -1, -1, -1)))
    game.roll_dice()
    result = game.move_pawn(0)
    assert result is game.state
    assert game.state.players[0].pawns[0].progress == 8
    # Same relative progress is not the same absolute square.
    assert game.state.players[1].pawns[0].progress == 8
    assert game.active_player.color == PlayerColor.BLUE
    assert game.state.pending_roll is None


@pytest.mark.parametrize("roll, start", [(1, 13), (6, 8)])
def test_capture_uses_absolute_square_and_bonus_depends_only_on_die(
    roll: int, start: int
) -> None:
    game = scenario([roll], ((start, -1, -1, -1), (1, -1, -1, -1)))
    game.roll_dice()
    game.move_pawn(0)
    assert game.state.players[0].pawns[0].progress == 14
    assert game.state.players[1].pawns[0].in_base
    expected = PlayerColor.RED if roll == 6 else PlayerColor.BLUE
    assert game.active_player.color == expected
    assert game.state.pending_roll is None


def test_all_opponent_pawns_on_an_unsafe_square_are_captured() -> None:
    game = scenario([3], ((11, -1, -1, -1), (1, 1, -1, -1)))
    game.roll_dice()
    game.move_pawn(0)
    assert all(pawn.in_base for pawn in game.state.players[1].pawns)


@pytest.mark.parametrize("square", [0, 13, 26, 39])
def test_every_start_square_is_safe_even_for_unselected_colors(
    square: int,
) -> None:
    attacker = PlayerColor.BLUE if square == 0 else PlayerColor.RED
    defender = PlayerColor.RED if square == 0 else PlayerColor.BLUE
    offset = Player(attacker).starting_offset
    other_offset = Player(defender).starting_offset
    destination = (square - offset) % 52
    opponent_progress = (square - other_offset) % 52
    game = scenario(
        [1],
        (
            (destination - 1, -1, -1, -1),
            (opponent_progress, opponent_progress, -1, -1),
        ),
        (attacker, defender),
    )
    game.roll_dice()
    game.move_pawn(0)
    assert game.state.players[0].pawns[0].progress == destination
    assert tuple(p.progress for p in game.state.players[1].pawns) == (
        opponent_progress, opponent_progress, -1, -1
    )


def test_leaving_base_can_share_safe_start_with_opponents() -> None:
    game = scenario([6], ((-1, -1, -1, -1), (39, 39, -1, -1)))
    game.roll_dice()
    game.move_pawn(0)
    assert game.state.players[0].pawns[0].progress == 0
    assert tuple(p.progress for p in game.state.players[1].pawns) == (
        39, 39, -1, -1
    )


def test_friendly_pawns_can_stack_on_unsafe_squares() -> None:
    game = scenario([2], ((8, 10, -1, -1), (-1, -1, -1, -1)))
    game.roll_dice()
    assert game.legal_moves() == (0, 1)
    game.move_pawn(0)
    assert tuple(p.progress for p in game.state.players[0].pawns) == (
        10, 10, -1, -1
    )


def test_passing_stacked_opponents_neither_blocks_nor_captures() -> None:
    game = scenario([4], ((11, -1, -1, -1), (1, 1, -1, -1)))
    game.roll_dice()
    game.move_pawn(0)
    assert game.state.players[0].pawns[0].progress == 15
    assert tuple(p.progress for p in game.state.players[1].pawns) == (
        1, 1, -1, -1
    )


@pytest.mark.parametrize("progress, roll, expected", [
    (51, 1, 52), (50, 5, 55), (51, 6, 57),
])
def test_entering_home_stretch_uses_player_relative_progress(
    progress: int, roll: int, expected: int
) -> None:
    game = scenario([roll], ((progress, -1, -1, -1), (-1, -1, -1, -1)))
    game.roll_dice()
    game.move_pawn(0)
    pawn = game.state.players[0].pawns[0]
    assert pawn.progress == expected
    assert Board.shared_position(pawn.progress, 0) is None
    assert game.winner is None


def test_home_stretch_is_private_and_does_not_capture_track_pawns() -> None:
    game = scenario([1], ((53, -1, -1, -1), (41, -1, -1, -1)))
    game.roll_dice()
    game.move_pawn(0)
    assert game.state.players[0].pawns[0].progress == 54
    assert game.state.players[1].pawns[0].progress == 41


def test_players_can_occupy_same_relative_home_stretch_position() -> None:
    game = scenario([1], ((53, -1, -1, -1), (54, -1, -1, -1)))
    game.roll_dice()
    game.move_pawn(0)
    assert game.state.players[0].pawns[0].progress == 54
    assert game.state.players[1].pawns[0].progress == 54


@pytest.mark.parametrize("progress, roll", [
    (52, 5), (53, 4), (54, 3), (55, 2), (56, 1),
])
def test_exact_roll_reaches_finish(progress: int, roll: int) -> None:
    game = scenario([roll], ((progress, -1, -1, -1), (-1, -1, -1, -1)))
    game.roll_dice()
    game.move_pawn(0)
    assert game.state.players[0].pawns[0].finished
    assert game.winner is None


def test_overshooting_is_rejected_without_consuming_a_playable_roll() -> None:
    game = scenario([2], ((56, 10, 57, 57), (-1, -1, -1, -1)))
    game.roll_dice()
    assert game.legal_moves() == (1,)
    before = game.state
    with pytest.raises(InvalidMoveError):
        game.move_pawn(0)
    assert game.state is before
    assert game.state.pending_roll == 2
    game.move_pawn(1)
    assert game.state.players[0].pawns[1].progress == 12


def test_finished_pawns_cannot_move_or_leave_base_again() -> None:
    game = scenario([6], ((57, -1, -1, -1), (-1, -1, -1, -1)))
    game.roll_dice()
    assert game.legal_moves() == (1, 2, 3)
    before = game.state
    with pytest.raises(InvalidMoveError):
        game.move_pawn(0)
    assert game.state is before


def test_unplayable_non_six_passes_without_changing_pawns() -> None:
    game = scenario([2], ((56, 57, 57, 57), (-1, -1, -1, -1)))
    before = game.state
    game.roll_dice()
    assert game.state.players == before.players
    assert game.active_player.color == PlayerColor.BLUE
    assert game.state.pending_roll is None


def test_unplayable_six_preserves_bonus_and_allows_another_roll() -> None:
    game = scenario([6, 1], ((52, 53, 54, 55), (-1, -1, -1, -1)))
    before = game.state
    assert game.roll_dice() == 6
    assert game.state.players == before.players
    assert game.active_player.color == PlayerColor.RED
    assert game.state.pending_roll is None
    assert game.legal_moves() == ()
    assert game.roll_dice() == 1
    assert game.legal_moves() == (0, 1, 2, 3)


def test_three_consecutive_sixes_have_no_penalty() -> None:
    game = scenario([6, 6, 6, 2])
    for expected in (0, 6, 12):
        game.roll_dice()
        game.move_pawn(0)
        assert game.active_player.color == PlayerColor.RED
        assert game.active_player.pawns[0].progress == expected
    game.roll_dice()
    game.move_pawn(0)
    assert game.state.players[0].pawns[0].progress == 14
    assert game.active_player.color == PlayerColor.BLUE


@pytest.mark.parametrize("count", [2, 3, 4])
def test_turn_order_wraps_through_selected_players(count: int) -> None:
    colors = tuple(PlayerColor)[:count]
    game = GameEngine(colors, dice=ScriptedDice([1] * (count * 2)))
    for index in range(count * 2):
        assert game.active_player.color == colors[index % count]
        game.roll_dice()
    assert game.active_player.color == colors[0]


def test_only_the_active_players_pawn_is_moved() -> None:
    game = scenario([2, 1], ((5, -1, -1, -1), (10, -1, -1, -1)))
    game.roll_dice()
    game.move_pawn(0)
    game.roll_dice()
    game.move_pawn(0)
    assert game.state.players[0].pawns[0].progress == 7
    assert game.state.players[1].pawns[0].progress == 11
    assert game.active_player.color == PlayerColor.RED


@pytest.mark.parametrize("progress, roll", [(56, 1), (51, 6)])
def test_finishing_fourth_pawn_wins_and_prevents_further_actions(
    progress: int, roll: int
) -> None:
    game = scenario([roll], ((57, 57, 57, progress), (-1, -1, -1, -1)))
    assert game.winner is None
    game.roll_dice()
    assert game.legal_moves() == (3,)
    game.move_pawn(3)
    assert game.winner is game.active_player
    assert game.winner.color == PlayerColor.RED
    assert game.state.winner == PlayerColor.RED
    assert game.winner.has_won
    assert game.state.pending_roll is None
    assert game.legal_moves() == ()
    before = game.state
    for action in (game.roll_dice, lambda: game.move_pawn(3)):
        with pytest.raises(GameOverError):
            action()
        assert game.state is before


def test_three_finished_pawns_do_not_win() -> None:
    game = scenario([1], ((57, 57, 56, -1), (-1, -1, -1, -1)))
    game.roll_dice()
    game.move_pawn(2)
    assert tuple(p.finished for p in game.state.players[0].pawns) == (
        True, True, True, False
    )
    assert game.winner is None
    assert game.active_player.color == PlayerColor.BLUE


def test_reset_clears_positions_and_roll_but_keeps_roster_and_dice() -> None:
    colors = (PlayerColor.YELLOW, PlayerColor.GREEN)
    game = scenario([6, 2], colors=colors)
    game.roll_dice()
    reset = game.reset()
    assert reset == GameEngine(colors).state
    assert game.roll_dice() == 2
    assert game.active_player.color == PlayerColor.GREEN


def test_reset_after_victory_starts_a_fresh_game() -> None:
    game = scenario([1, 6], ((57, 57, 57, 56), (-1, -1, -1, -1)))
    game.roll_dice()
    game.move_pawn(3)
    game.reset()
    assert game.winner is None
    assert game.active_player.color == PlayerColor.RED
    assert all(
        p.in_base for player in game.state.players for p in player.pawns
    )
    assert game.roll_dice() == 6


def test_new_game_replaces_roster_and_discards_previous_turn() -> None:
    game = scenario([6])
    game.roll_dice()
    game.move_pawn(0)
    result = game.new_game(("green", "yellow", "blue"))
    assert result is game.state
    assert tuple(p.color.value for p in result.players) == (
        "green", "yellow", "blue"
    )
    assert game.active_player.starting_offset == 26
    assert all(p.in_base for player in result.players for p in player.pawns)


@pytest.mark.parametrize("colors", [
    (), ("red",), ("red", "red"), ("red", "purple"),
    ("red", "blue", "green", "yellow", "red"), "red", None,
])
def test_invalid_new_game_keeps_existing_state(colors: object) -> None:
    game = scenario([6])
    game.roll_dice()
    before = game.state
    with pytest.raises(InvalidSetupError):
        game.new_game(colors)
    assert game.state is before


@pytest.mark.parametrize("pawn_id", [-1, 4, True, 1.0, "0", None])
def test_invalid_pawn_ids_preserve_the_complete_state(pawn_id: object) -> None:
    game = scenario([6])
    game.roll_dice()
    before = game.state
    with pytest.raises(InvalidMoveError):
        game.move_pawn(pawn_id)
    assert game.state is before


def test_cannot_move_before_rolling_or_reroll_with_a_move_pending() -> None:
    game = scenario([6, 1])
    before = game.state
    with pytest.raises(InvalidTurnError):
        game.move_pawn(0)
    assert game.state is before
    game.roll_dice()
    pending = game.state
    with pytest.raises(InvalidTurnError):
        game.roll_dice()
    assert game.state is pending
    game.move_pawn(0)
    # The rejected roll did not even consume the next scripted dice value.
    assert game.roll_dice() == 1


@pytest.mark.parametrize("bad_roll", [0, 7, -1, True, 1.5, "6", None])
def test_invalid_roll_leaves_state_unchanged(bad_roll: object) -> None:
    game = scenario([bad_roll, 6])
    before = game.state
    with pytest.raises(InvalidRollError):
        game.roll_dice()
    assert game.state is before
    assert game.roll_dice() == 6


def test_snapshots_are_immutable_and_do_not_change_after_moves() -> None:
    game = scenario([6])
    initial = game.state
    game.roll_dice()
    pending = game.state
    game.move_pawn(0)
    assert initial.pending_roll is None
    assert pending.pending_roll == 6
    assert initial.players[0].pawns[0].in_base
    assert pending.players[0].pawns[0].in_base
    assert game.state.players[0].pawns[0].progress == 0
    with pytest.raises(FrozenInstanceError):
        game.state.players[0].pawns[0].progress = 20
    with pytest.raises(FrozenInstanceError):
        game.state.active_player_index = 1
    with pytest.raises(AttributeError):
        game.state = initial


def test_engine_imports_and_runs_with_no_third_party_packages() -> None:
    result = subprocess.run(
        [sys.executable, "-S", "-c", """
import random
import sys
from src.core import Dice, GameEngine
game = GameEngine(('red', 'blue'), dice=Dice(random.Random(0)))
assert game.roll_dice() == 4
assert game.active_player.color.value == 'blue'
assert not any(name.startswith('PySide6') for name in sys.modules)
"""],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("count", [2, 3, 4])
def test_complete_game_can_be_played_from_base_to_victory(count: int) -> None:
    """Exercise interacting rules over complete deterministic games."""
    game = GameEngine(
        tuple(PlayerColor)[:count], dice=Dice(random.Random(42))
    )
    for _ in range(2000):
        game.roll_dice()
        moves = game.legal_moves()
        if moves:
            pawn_id = max(
                moves, key=lambda item: game.active_player.pawns[item].progress
            )
            game.move_pawn(pawn_id)
        if game.winner is not None:
            break
    else:
        pytest.fail("The seeded game failed to reach a winner in 2000 rolls.")
    assert all(pawn.finished for pawn in game.winner.pawns)
    assert sum(player.has_won for player in game.state.players) == 1
    assert game.state.pending_roll is None
