"""Behavioral tests for the public Qt-independent game engine."""

import random
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from Ludo.core.board import Board
from Ludo.core.dice import Dice
from Ludo.core.exceptions import (
    GameOverError,
    InvalidMoveError,
    InvalidRollError,
    InvalidSetupError,
    InvalidTurnError,
)
from Ludo.core.game import Game, GameEngine
from Ludo.core.pawn import Pawn
from Ludo.core.player import Player, PlayerColor
from Ludo.core.state import GameState


class _ScriptedDice(Dice):
    """Supply known results without relying on random luck."""

    def __init__(self, rolls: Sequence[int]) -> None:
        """Prepare an iterator over predetermined dice results.

        Args:
            rolls: Dice results to supply in order, including invalid test
                values when needed.
        """
        self._rolls = iter(rolls)

    def roll(self) -> int:
        """Consume the next scripted dice result.

        Returns:
            The next supplied result, without validation so engine checks
            can be tested.
        """
        return next(self._rolls)


def _scenario(
    rolls: Sequence[int],
    positions: tuple[tuple[int, ...], ...] = (
        (-1, -1, -1, -1),
        (-1, -1, -1, -1),
    ),
    colors: tuple[PlayerColor, ...] = (PlayerColor.RED, PlayerColor.BLUE),
) -> GameEngine:
    """Build a validated game scenario with scripted dice.

    Args:
        rolls: Dice results to supply in order.
        positions: One row of four logical pawn positions per player,
            in roster order. Defaults to two players with all pawns in
            base.
        colors: Player colors in turn order, matching the position
            rows. Defaults to red followed by blue.

    Returns:
        A GameEngine initialized from the scenario snapshot and
        scripted dice.
    """
    assert len(positions) == len(colors)
    players = tuple(
        Player(
            color,
            tuple(Pawn(pawn_id, step) for pawn_id, step in enumerate(row)),
        )
        for color, row in zip(colors, positions, strict=True)
    )
    return GameEngine.from_state(GameState(players), dice=_ScriptedDice(rolls))


@pytest.mark.parametrize("count", [2, 3, 4])
def test_new_game_initializes_four_base_pawns_per_player(count: int) -> None:
    """Verify that each selected player starts with four base pawns.

    Args:
        count: The parametrized player count: 2, 3, or 4.
    """
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
    """Verify fixed color offsets and the legacy Game alias."""
    game = GameEngine(("yellow", "blue"))
    assert game.active_player.starting_offset == 39
    assert game.state.players[1].starting_offset == 13
    assert Game is GameEngine


@pytest.mark.parametrize("roll", range(1, 6))
def test_non_six_cannot_leave_base_and_automatically_passes(roll: int) -> None:
    """Verify that a non-six leaves base pawns unchanged and passes.

    Args:
        roll: The parametrized non-six dice value from 1 to 5.
    """
    game = _scenario([roll])
    before = game.state
    assert game.roll_dice() == roll
    assert game.state.players == before.players
    assert game.active_player.color == PlayerColor.BLUE
    assert game.state.pending_roll is None
    assert game.legal_moves() == ()
    with pytest.raises(InvalidTurnError):
        game.move_pawn(0)


def test_six_leaves_base_at_zero_and_preserves_the_extra_roll() -> None:
    """Verify that a six releases a pawn at zero and grants another roll."""
    game = _scenario([6, 3])
    assert game.roll_dice() == 6
    assert game.legal_moves() == (0, 1, 2, 3)
    game.move_pawn(2)
    assert game.active_player.color == PlayerColor.RED
    assert tuple(pawn.progress for pawn in game.active_player.pawns) == (
        -1,
        -1,
        0,
        -1,
    )
    assert game.state.pending_roll is None
    game.roll_dice()
    assert game.legal_moves() == (2,)
    game.move_pawn(2)
    assert game.state.players[0].pawns[2].progress == 3
    assert game.active_player.color == PlayerColor.BLUE


def test_normal_movement_consumes_roll_and_switches_player() -> None:
    """Verify ordinary movement, roll consumption, and turn switching."""
    game = _scenario([3], ((5, -1, -1, -1), (8, -1, -1, -1)))
    game.roll_dice()
    result = game.move_pawn(0)
    assert result is game.state
    assert game.state.players[0].pawns[0].progress == 8
    # Same relative progress is not the same absolute square.
    assert game.state.players[1].pawns[0].progress == 8
    assert game.active_player.color == PlayerColor.BLUE
    assert game.state.pending_roll is None


@pytest.mark.parametrize(("roll", "start"), [(1, 13), (6, 8)])
def test_capture_uses_absolute_square_and_bonus_depends_only_on_die(
    roll: int, start: int
) -> None:
    """Verify absolute-square capture and dice-based bonus rolls.

    Args:
        roll: The parametrized dice result: 1 or 6.
        start: The moving pawn's initial progress, chosen to land at
            14.
    """
    game = _scenario([roll], ((start, -1, -1, -1), (1, -1, -1, -1)))
    game.roll_dice()
    game.move_pawn(0)
    assert game.state.players[0].pawns[0].progress == 14
    assert game.state.players[1].pawns[0].in_base
    expected = PlayerColor.RED if roll == 6 else PlayerColor.BLUE
    assert game.active_player.color == expected
    assert game.state.pending_roll is None


def test_all_opponent_pawns_on_an_unsafe_square_are_captured() -> None:
    """Verify capture of every opponent pawn on an unsafe destination."""
    game = _scenario([3], ((11, -1, -1, -1), (1, 1, -1, -1)))
    game.roll_dice()
    game.move_pawn(0)
    assert all(pawn.in_base for pawn in game.state.players[1].pawns)


@pytest.mark.parametrize("square", [0, 13, 26, 39])
def test_every_start_square_is_safe_even_for_unselected_colors(
    square: int,
) -> None:
    """Verify that all four starting squares protect opposing stacks.

    Args:
        square: The parametrized absolute safe square: 0, 13, 26, or
            39.
    """
    attacker = PlayerColor.BLUE if square == 0 else PlayerColor.RED
    defender = PlayerColor.RED if square == 0 else PlayerColor.BLUE
    offset = Player(attacker).starting_offset
    other_offset = Player(defender).starting_offset
    destination = (square - offset) % 52
    opponent_progress = (square - other_offset) % 52
    game = _scenario(
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
    assert tuple(pawn.progress for pawn in game.state.players[1].pawns) == (
        opponent_progress,
        opponent_progress,
        -1,
        -1,
    )


def test_leaving_base_can_share_safe_start_with_opponents() -> None:
    """Verify that releasing a pawn does not capture on its safe start."""
    game = _scenario([6], ((-1, -1, -1, -1), (39, 39, -1, -1)))
    game.roll_dice()
    game.move_pawn(0)
    assert game.state.players[0].pawns[0].progress == 0
    assert tuple(pawn.progress for pawn in game.state.players[1].pawns) == (
        39,
        39,
        -1,
        -1,
    )


def test_friendly_pawns_can_stack_on_unsafe_squares() -> None:
    """Verify that friendly pawns may share an unsafe square."""
    game = _scenario([2], ((8, 10, -1, -1), (-1, -1, -1, -1)))
    game.roll_dice()
    assert game.legal_moves() == (0, 1)
    game.move_pawn(0)
    assert tuple(pawn.progress for pawn in game.state.players[0].pawns) == (
        10,
        10,
        -1,
        -1,
    )


def test_passing_stacked_opponents_neither_blocks_nor_captures() -> None:
    """Verify that passing an opposing stack is allowed without capture."""
    game = _scenario([4], ((11, -1, -1, -1), (1, 1, -1, -1)))
    game.roll_dice()
    game.move_pawn(0)
    assert game.state.players[0].pawns[0].progress == 15
    assert tuple(pawn.progress for pawn in game.state.players[1].pawns) == (
        1,
        1,
        -1,
        -1,
    )


@pytest.mark.parametrize(
    ("progress", "roll", "expected"),
    [
        (51, 1, 52),
        (50, 5, 55),
        (51, 6, 57),
    ],
)
def test_entering_home_stretch_uses_player_relative_progress(
    progress: int, roll: int, expected: int
) -> None:
    """Verify transitions from the shared track into private positions.

    Args:
        progress: The moving pawn's parametrized initial logical
            progress.
        roll: The dice result used to enter or cross the home stretch.
        expected: The expected logical destination, outside the shared
            track.
    """
    game = _scenario([roll], ((progress, -1, -1, -1), (-1, -1, -1, -1)))
    game.roll_dice()
    game.move_pawn(0)
    pawn = game.state.players[0].pawns[0]
    assert pawn.progress == expected
    assert Board.shared_position(pawn.progress, 0) is None
    assert game.winner is None


def test_home_stretch_is_private_and_does_not_capture_track_pawns() -> None:
    """Verify that home-stretch movement cannot capture track pawns."""
    game = _scenario([1], ((53, -1, -1, -1), (41, -1, -1, -1)))
    game.roll_dice()
    game.move_pawn(0)
    assert game.state.players[0].pawns[0].progress == 54
    assert game.state.players[1].pawns[0].progress == 41


def test_players_can_occupy_same_relative_home_stretch_position() -> None:
    """Verify that different players have independent home stretches."""
    game = _scenario([1], ((53, -1, -1, -1), (54, -1, -1, -1)))
    game.roll_dice()
    game.move_pawn(0)
    assert game.state.players[0].pawns[0].progress == 54
    assert game.state.players[1].pawns[0].progress == 54


@pytest.mark.parametrize(
    ("progress", "roll"),
    [
        (52, 5),
        (53, 4),
        (54, 3),
        (55, 2),
        (56, 1),
    ],
)
def test_exact_roll_reaches_finish(progress: int, roll: int) -> None:
    """Verify that an exact roll finishes a pawn in the home stretch.

    Args:
        progress: The parametrized starting progress from 52 to 56.
        roll: The exact dice result needed to reach progress 57.
    """
    game = _scenario([roll], ((progress, -1, -1, -1), (-1, -1, -1, -1)))
    game.roll_dice()
    game.move_pawn(0)
    assert game.state.players[0].pawns[0].finished
    assert game.winner is None


def test_overshooting_is_rejected_without_consuming_a_playable_roll() -> None:
    """Verify that a rejected overshoot preserves a pending legal move."""
    game = _scenario([2], ((56, 10, 57, 57), (-1, -1, -1, -1)))
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
    """Verify that finished pawns are excluded from legal moves."""
    game = _scenario([6], ((57, -1, -1, -1), (-1, -1, -1, -1)))
    game.roll_dice()
    assert game.legal_moves() == (1, 2, 3)
    before = game.state
    with pytest.raises(InvalidMoveError):
        game.move_pawn(0)
    assert game.state is before


def test_unplayable_non_six_passes_without_changing_pawns() -> None:
    """Verify that an unplayable non-six passes without moving pawns."""
    game = _scenario([2], ((56, 57, 57, 57), (-1, -1, -1, -1)))
    before = game.state
    game.roll_dice()
    assert game.state.players == before.players
    assert game.active_player.color == PlayerColor.BLUE
    assert game.state.pending_roll is None


def test_unplayable_six_preserves_bonus_and_allows_another_roll() -> None:
    """Verify that an unplayable six allows the same player to reroll."""
    game = _scenario([6, 1], ((52, 53, 54, 55), (-1, -1, -1, -1)))
    before = game.state
    assert game.roll_dice() == 6
    assert game.state.players == before.players
    assert game.active_player.color == PlayerColor.RED
    assert game.state.pending_roll is None
    assert game.legal_moves() == ()
    assert game.roll_dice() == 1
    assert game.legal_moves() == (0, 1, 2, 3)


def test_three_consecutive_sixes_have_no_penalty() -> None:
    """Verify that three consecutive sixes preserve bonus rolls."""
    game = _scenario([6, 6, 6, 2])
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
    """Verify automatic passes follow the roster and wrap to its start.

    Args:
        count: The parametrized player count: 2, 3, or 4.
    """
    colors = tuple(PlayerColor)[:count]
    game = GameEngine(colors, dice=_ScriptedDice([1] * (count * 2)))
    for index in range(count * 2):
        assert game.active_player.color == colors[index % count]
        game.roll_dice()
    assert game.active_player.color == colors[0]


def test_only_the_active_players_pawn_is_moved() -> None:
    """Verify that a pawn ID always refers to the active player's pawn."""
    game = _scenario([2, 1], ((5, -1, -1, -1), (10, -1, -1, -1)))
    game.roll_dice()
    game.move_pawn(0)
    game.roll_dice()
    game.move_pawn(0)
    assert game.state.players[0].pawns[0].progress == 7
    assert game.state.players[1].pawns[0].progress == 11
    assert game.active_player.color == PlayerColor.RED


@pytest.mark.parametrize(("progress", "roll"), [(56, 1), (51, 6)])
def test_finishing_fourth_pawn_wins_and_prevents_further_actions(
    progress: int, roll: int
) -> None:
    """Verify that finishing the fourth pawn ends the game immediately.

    Args:
        progress: The final unfinished pawn's parametrized starting
            progress.
        roll: The exact winning roll, including a six to test bonus
            cancellation.
    """
    game = _scenario([roll], ((57, 57, 57, progress), (-1, -1, -1, -1)))
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
    """Verify that three finished pawns do not satisfy victory."""
    game = _scenario([1], ((57, 57, 56, -1), (-1, -1, -1, -1)))
    game.roll_dice()
    game.move_pawn(2)
    assert tuple(pawn.finished for pawn in game.state.players[0].pawns) == (
        True,
        True,
        True,
        False,
    )
    assert game.winner is None
    assert game.active_player.color == PlayerColor.BLUE


def test_reset_clears_positions_and_roll_but_keeps_roster_and_dice() -> None:
    """Verify reset clears the turn while retaining colors and dice."""
    colors = (PlayerColor.YELLOW, PlayerColor.GREEN)
    game = _scenario([6, 2], colors=colors)
    game.roll_dice()
    reset = game.reset()
    assert reset == GameEngine(colors).state
    assert game.roll_dice() == 2
    assert game.active_player.color == PlayerColor.GREEN


def test_reset_after_victory_starts_a_fresh_game() -> None:
    """Verify that reset clears victory and restores all pawns to base."""
    game = _scenario([1, 6], ((57, 57, 57, 56), (-1, -1, -1, -1)))
    game.roll_dice()
    game.move_pawn(3)
    game.reset()
    assert game.winner is None
    assert game.active_player.color == PlayerColor.RED
    assert all(
        pawn.in_base for player in game.state.players for pawn in player.pawns
    )
    assert game.roll_dice() == 6


def test_new_game_replaces_roster_and_discards_previous_turn() -> None:
    """Verify that a new game replaces the roster and clears progress."""
    game = _scenario([6])
    game.roll_dice()
    game.move_pawn(0)
    result = game.new_game(("green", "yellow", "blue"))
    assert result is game.state
    assert tuple(pawn.color.value for pawn in result.players) == (
        "green",
        "yellow",
        "blue",
    )
    assert game.active_player.starting_offset == 26
    assert all(
        pawn.in_base for player in result.players for pawn in player.pawns
    )


@pytest.mark.parametrize(
    "colors",
    [
        (),
        ("red",),
        ("red", "red"),
        ("red", "purple"),
        ("red", "blue", "green", "yellow", "red"),
        "red",
        None,
    ],
)
def test_invalid_new_game_keeps_existing_state(colors: object) -> None:
    """Verify that rejecting a roster preserves the complete snapshot.

    Args:
        colors: A parametrized invalid roster or object supplied as a
            roster.
    """
    game = _scenario([6])
    game.roll_dice()
    before = game.state
    with pytest.raises(InvalidSetupError):
        game.new_game(colors)
    assert game.state is before


@pytest.mark.parametrize("pawn_id", [-1, 4, True, 1.0, "0", None])
def test_invalid_pawn_ids_preserve_the_complete_state(pawn_id: object) -> None:
    """Verify that rejecting a pawn ID leaves the snapshot unchanged.

    Args:
        pawn_id: A parametrized invalid pawn ID or value of the wrong
            type.
    """
    game = _scenario([6])
    game.roll_dice()
    before = game.state
    with pytest.raises(InvalidMoveError):
        game.move_pawn(pawn_id)
    assert game.state is before


def test_cannot_move_before_rolling_or_reroll_with_a_move_pending() -> None:
    """Verify that rejected turn actions preserve state and dice order."""
    game = _scenario([6, 1])
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
    """Verify that rejecting a dice result leaves the snapshot unchanged.

    Args:
        bad_roll: A parametrized result outside the accepted integer
            range 1..6.
    """
    game = _scenario([bad_roll, 6])
    before = game.state
    with pytest.raises(InvalidRollError):
        game.roll_dice()
    assert game.state is before
    assert game.roll_dice() == 6


def test_snapshots_are_immutable_and_do_not_change_after_moves() -> None:
    """Verify snapshot stability and rejection of direct reassignment."""
    game = _scenario([6])
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
    """Verify engine startup without site-packages or Qt imports."""
    result = subprocess.run(
        [
            sys.executable,
            "-S",
            "-c",
            """
import random
import sys
from Ludo.core.dice import Dice
from Ludo.core.game import GameEngine
game = GameEngine(('red', 'blue'), dice=Dice(random.Random(0)))
assert game.roll_dice() == 4
assert game.active_player.color.value == 'blue'
assert not any(name.startswith('PySide6') for name in sys.modules)
""",
        ],
        cwd=Path(__file__).resolve().parents[1] / "src",
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_package_markers_do_not_eagerly_import_implementation_modules() -> (
    None
):
    """Verify package imports do not initialize the engine or GUI modules."""
    result = subprocess.run(
        [
            sys.executable,
            "-S",
            "-c",
            """
import sys
import Ludo
import Ludo.core
import Ludo.gui
assert not any(
    name.startswith(('Ludo.core.', 'Ludo.gui.', 'PySide6'))
    for name in sys.modules
)
""",
        ],
        cwd=Path(__file__).resolve().parents[1] / "src",
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("count", [2, 3, 4])
def test_complete_game_can_be_played_from_base_to_victory(count: int) -> None:
    """Verify that a complete seeded game reaches exactly one winner.

    Args:
        count: The parametrized player count: 2, 3, or 4.
    """
    game = GameEngine(tuple(PlayerColor)[:count], dice=Dice(random.Random(42)))
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
