"""Coordinate mapping and validation of immutable game snapshots."""

from dataclasses import FrozenInstanceError, replace

import pytest

from src.core import Board, GameEngine, GameState, Pawn, Player, PlayerColor
from src.core.exceptions import (
    InvalidMoveError,
    InvalidRollError,
    InvalidSetupError,
)


@pytest.mark.parametrize("progress, offset, expected", [
    (0, 0, 0), (0, 13, 13), (0, 26, 26), (0, 39, 39),
    (51, 0, 51), (38, 13, 51), (39, 13, 0), (51, 39, 38),
    (-1, 0, None), (52, 13, None), (56, 26, None), (57, 39, None),
])
def test_shared_track_coordinates(
    progress: int, offset: int, expected: int | None
) -> None:
    assert Board.shared_position(progress, offset) == expected


@pytest.mark.parametrize("offset", [1, -13, 52, True, 0.0])
def test_invalid_starting_offsets_are_rejected(offset: object) -> None:
    with pytest.raises(InvalidMoveError):
        Board.shared_position(0, offset)


@pytest.mark.parametrize("progress", [-2, 58, True, 0.0, "0"])
def test_invalid_progress_is_rejected(progress: object) -> None:
    with pytest.raises(InvalidMoveError):
        Pawn(0, progress)


@pytest.mark.parametrize("pawn_id", [-1, 4, True, 0.0])
def test_invalid_pawn_identity_is_rejected(pawn_id: object) -> None:
    with pytest.raises(InvalidSetupError):
        Pawn(pawn_id)


def test_player_needs_four_ordered_pawns_and_an_immutable_color() -> None:
    with pytest.raises(InvalidSetupError):
        Player(PlayerColor.RED, (Pawn(0),))
    with pytest.raises(InvalidSetupError):
        Player(PlayerColor.RED, (Pawn(0), Pawn(0), Pawn(2), Pawn(3)))
    with pytest.raises(InvalidSetupError):
        Player("red")
    player = Player(PlayerColor.RED)
    with pytest.raises(FrozenInstanceError):
        player.color = PlayerColor.BLUE


@pytest.mark.parametrize("index", [-1, 2, True, 0.0])
def test_invalid_active_player_index_is_rejected(index: object) -> None:
    players = (Player(PlayerColor.RED), Player(PlayerColor.BLUE))
    with pytest.raises(InvalidSetupError):
        GameState(players, active_player_index=index)


def test_states_reject_mutable_collections_and_duplicate_colors() -> None:
    red = Player(PlayerColor.RED)
    blue = Player(PlayerColor.BLUE)
    with pytest.raises(InvalidSetupError):
        GameState([red, blue])
    with pytest.raises(InvalidSetupError):
        Player(PlayerColor.RED, list(red.pawns))
    with pytest.raises(InvalidSetupError):
        GameState((red, red))


def test_opponents_cannot_share_unsafe_track_squares_in_a_snapshot() -> None:
    red = Player(PlayerColor.RED, (Pawn(0, 14), Pawn(1), Pawn(2), Pawn(3)))
    blue = Player(PlayerColor.BLUE, (Pawn(0, 1), Pawn(1), Pawn(2), Pawn(3)))
    with pytest.raises(InvalidSetupError):
        GameState((red, blue))


def test_snapshot_cannot_have_an_unplayable_pending_roll() -> None:
    players = (Player(PlayerColor.RED), Player(PlayerColor.BLUE))
    with pytest.raises(InvalidSetupError):
        GameState(players, pending_roll=1)
    with pytest.raises(InvalidRollError):
        GameState(players, pending_roll=7)


def test_winner_flag_requires_four_finished_pawns_and_a_closed_turn() -> None:
    red = Player(PlayerColor.RED)
    blue = Player(PlayerColor.BLUE)
    with pytest.raises(InvalidSetupError):
        GameState((red, blue), winner=PlayerColor.RED)
    winner = replace(red, pawns=tuple(Pawn(i, 57) for i in range(4)))
    with pytest.raises(InvalidSetupError):
        GameState((winner, blue))
    with pytest.raises(InvalidSetupError):
        GameState(
            (winner, blue), active_player_index=1, winner=PlayerColor.RED
        )
    with pytest.raises(InvalidSetupError):
        GameState((winner, blue), pending_roll=6, winner=PlayerColor.RED)
    finished = GameState((winner, blue), winner=PlayerColor.RED)
    assert GameEngine.from_state(finished).winner == winner


def test_snapshot_rejects_multiple_winners() -> None:
    pawns = tuple(Pawn(i, 57) for i in range(4))
    players = (Player(PlayerColor.RED, pawns), Player(PlayerColor.BLUE, pawns))
    with pytest.raises(InvalidSetupError):
        GameState(players, winner=PlayerColor.RED)


def test_engine_rejects_objects_that_are_not_state_snapshots() -> None:
    with pytest.raises(InvalidSetupError):
        GameEngine.from_state(None)
