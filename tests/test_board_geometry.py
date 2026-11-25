"""Check the board route, progress mapping, scaling, and shared-square layout."""

from dataclasses import replace
from itertools import combinations
from math import hypot

import pytest

from Ludo.core.board import Board
from Ludo.core.game import GameEngine
from Ludo.core.pawn import Pawn
from Ludo.core.player import Player, PlayerColor
from Ludo.core.state import GameState
from Ludo.gui.board_geometry import BoardGeometry, GridCell


def _stack_state(count: int) -> GameState:
    """Create a valid snapshot with selected pawns on the red safe square.

    Args:
        count: Number of pawns to place on the shared safe square, up to 16.

    Returns:
        A four-player snapshot, with remaining pawns in their bases.
    """
    players = []
    for player_index, color in enumerate(PlayerColor):
        player = Player(color)
        progress = (-player.starting_offset) % Board.TRACK_LENGTH
        players.append(
            replace(
                player,
                pawns=tuple(
                    replace(pawn, progress=progress)
                    if player_index * Board.PAWNS_PER_PLAYER + pawn.id < count
                    else pawn
                    for pawn in player.pawns
                ),
            )
        )
    return GameState(tuple(players))


def test_shared_track_has_52_unique_connected_grid_cells() -> None:
    """Verify a complete closed route within the traditional cross."""
    track = BoardGeometry.SHARED_TRACK
    assert len(track) == 52
    assert len(set(track)) == 52
    assert all(0 <= row < 15 and 0 <= column < 15 for row, column in track)
    for current, following in zip(track, (*track[1:], track[0]), strict=True):
        assert (
            max(abs(current[0] - following[0]), abs(current[1] - following[1]))
            == 1
        )


def test_shared_track_and_home_stretches_exactly_fill_the_cross() -> None:
    """Verify that route cells have no duplicates, gaps, or shared home lanes."""
    shared = set(BoardGeometry.SHARED_TRACK)
    home_cells = [
        cell
        for cells in BoardGeometry.HOME_STRETCHES.values()
        for cell in cells
    ]
    center = {(row, column) for row in range(6, 9) for column in range(6, 9)}
    cross = {
        (row, column)
        for row in range(15)
        for column in range(15)
        if row in range(6, 9) or column in range(6, 9)
    }
    assert len(home_cells) == len(set(home_cells)) == 20
    assert shared.isdisjoint(home_cells)
    assert shared.isdisjoint(center)
    assert set(home_cells).isdisjoint(center)
    assert shared | set(home_cells) | center == cross


@pytest.mark.parametrize(
    ("color", "expected"),
    [
        (PlayerColor.RED, (6, 0)),
        (PlayerColor.BLUE, (0, 8)),
        (PlayerColor.GREEN, (8, 14)),
        (PlayerColor.YELLOW, (14, 6)),
    ],
)
def test_starting_cells_match_engine_color_offsets(
    color: PlayerColor, expected: GridCell
) -> None:
    """Verify the physical starting cell for each fixed engine offset.

    Args:
        color: The parametrized player color.
        expected: The expected starting (row, column) cell.
    """
    geometry = BoardGeometry(750, 750)
    player = Player(color)
    assert geometry.SHARED_TRACK[player.starting_offset] == expected
    assert geometry.cell_for(player, Pawn(0, 0)) == expected
    assert geometry.START_COLORS[player.starting_offset] == color
    assert set(geometry.START_COLORS) == Board.SAFE_SQUARES


@pytest.mark.parametrize(
    ("color", "progress", "expected"),
    [
        (PlayerColor.BLUE, 39, (6, 0)),
        (PlayerColor.GREEN, 26, (6, 0)),
        (PlayerColor.YELLOW, 13, (6, 0)),
        (PlayerColor.RED, 51, (7, 0)),
        (PlayerColor.BLUE, 51, (0, 7)),
        (PlayerColor.GREEN, 51, (7, 14)),
        (PlayerColor.YELLOW, 51, (14, 7)),
    ],
)
def test_progress_mapping_wraps_at_52_without_changing_grid_coordinates(
    color: PlayerColor, progress: int, expected: GridCell
) -> None:
    """Verify absolute-square mapping across different player offsets.

    Args:
        color: The parametrized pawn owner.
        progress: The owner's logical shared-track progress.
        expected: The expected absolute (row, column) cell.
    """
    geometry = BoardGeometry(750, 750)
    assert geometry.cell_for(Player(color), Pawn(0, progress)) == expected


@pytest.mark.parametrize(
    ("color", "expected"),
    [
        (PlayerColor.RED, ((7, 1), (7, 2), (7, 3), (7, 4), (7, 5))),
        (PlayerColor.BLUE, ((1, 7), (2, 7), (3, 7), (4, 7), (5, 7))),
        (PlayerColor.GREEN, ((7, 13), (7, 12), (7, 11), (7, 10), (7, 9))),
        (PlayerColor.YELLOW, ((13, 7), (12, 7), (11, 7), (10, 7), (9, 7))),
    ],
)
def test_private_home_stretches_follow_the_complete_shared_route(
    color: PlayerColor, expected: tuple[GridCell, ...]
) -> None:
    """Verify every home cell and continuity from shared progress 51.

    Args:
        color: The parametrized player color.
        expected: Five expected home cells in movement order.
    """
    geometry = BoardGeometry(750, 750)
    player = Player(color)
    assert geometry.HOME_STRETCHES[color] == expected
    assert (
        tuple(
            geometry.cell_for(player, Pawn(0, progress))
            for progress in range(52, 57)
        )
        == expected
    )
    previous = geometry.cell_for(player, Pawn(0, 51))
    assert previous is not None
    assert (
        sum(
            abs(left - right)
            for left, right in zip(previous, expected[0], strict=True)
        )
        == 1
    )


def test_base_and_finish_pawns_have_separate_dedicated_slots() -> None:
    """Verify that each of 16 pawns has distinct base and finish locations."""
    geometry = BoardGeometry(750, 750)
    bases, finishes = set(), set()
    for color in PlayerColor:
        player = Player(color)
        for pawn_id in range(4):
            base = Pawn(pawn_id)
            finished = Pawn(pawn_id, 57)
            assert geometry.cell_for(player, base) is None
            assert geometry.cell_for(player, finished) is None
            bases.add(geometry.pawn_center(player, base))
            finish = geometry.pawn_center(player, finished)
            finishes.add(finish)
            assert geometry.cell_at(*finish) in {
                (row, column) for row in range(6, 9) for column in range(6, 9)
            }
    assert len(bases) == len(finishes) == 16
    assert bases.isdisjoint(finishes)


@pytest.mark.parametrize(
    ("width", "height"),
    [
        (1100, 800),
        (400, 900),
        (640, 480),
        (1300, 300),
    ],
)
def test_square_viewport_and_inverse_mapping_survive_resizing(
    width: int, height: int
) -> None:
    """Verify centered bounds and all shared-cell pixel round trips.

    Args:
        width: The parametrized widget width.
        height: The parametrized widget height.
    """
    geometry = BoardGeometry(width, height)
    origin_x, origin_y = geometry.origin
    assert geometry.side == min(width, height) - 2 * geometry.padding
    assert origin_x + geometry.side / 2 == width / 2
    assert origin_y + geometry.side / 2 == height / 2
    for cell in geometry.SHARED_TRACK:
        assert geometry.cell_at(*geometry.cell_center(cell)) == cell
    assert geometry.cell_at(origin_x - 1, origin_y) is None
    assert geometry.cell_at(origin_x + geometry.side, origin_y) is None


def test_pixel_positions_and_pawn_radii_scale_together() -> None:
    """Verify that geometry and tokens share one uniform viewport transform."""
    state = GameEngine().state
    large = BoardGeometry(900, 900, padding=0)
    small = BoardGeometry(450, 450, padding=0)
    for full, half in zip(
        large.pawn_placements(state), small.pawn_placements(state), strict=True
    ):
        assert full.center_x == 2 * half.center_x
        assert full.center_y == 2 * half.center_y
        assert full.radius == 2 * half.radius


@pytest.mark.parametrize("count", range(1, 17))
def test_stacks_remain_distinguishable_and_fit_inside_the_shared_square(
    count: int,
) -> None:
    """Verify all legal stack sizes, including mixed-color safe-square stacks.

    Args:
        count: The parametrized number of pawns sharing a safe square.
    """
    geometry = BoardGeometry(900, 900)
    placements = geometry.pawn_placements(_stack_state(count))
    target = geometry.SHARED_TRACK[0]
    stacked = [
        pawn
        for pawn in placements
        if geometry.cell_at(pawn.center_x, pawn.center_y) == target
    ]
    assert len(placements) == 16
    assert len(stacked) == count
    assert len({(pawn.center_x, pawn.center_y) for pawn in stacked}) == count
    center_x, center_y = geometry.cell_center(target)
    for pawn in stacked:
        assert (
            abs(pawn.center_x - center_x) + pawn.radius
            < geometry.cell_size / 2
        )
        assert (
            abs(pawn.center_y - center_y) + pawn.radius
            < geometry.cell_size / 2
        )
        assert pawn.contains(pawn.center_x, pawn.center_y)
        assert not pawn.contains(
            pawn.center_x + 2 * pawn.radius, pawn.center_y
        )
    for first, second in combinations(stacked, 2):
        assert (
            hypot(
                first.center_x - second.center_x,
                first.center_y - second.center_y,
            )
            >= first.radius + second.radius
        )


@pytest.mark.parametrize(("width", "height"), [(0, 0), (20, 20)])
def test_collapsed_viewports_have_no_hit_target(
    width: int, height: int
) -> None:
    """Verify safe behavior before a widget has enough space for its board.

    Args:
        width: The parametrized small viewport width.
        height: The parametrized small viewport height.
    """
    geometry = BoardGeometry(width, height)
    assert geometry.side == 0
    assert geometry.cell_at(0, 0) is None


@pytest.mark.parametrize("width", [-1, float("nan"), float("inf")])
def test_invalid_viewport_dimensions_are_rejected(width: float) -> None:
    """Verify that invalid dimensions cannot produce unusable coordinates.

    Args:
        width: A negative or non-finite viewport width.
    """
    with pytest.raises(ValueError, match="finite and nonnegative"):
        BoardGeometry(width, 600)
