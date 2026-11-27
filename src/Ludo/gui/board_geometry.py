"""Qt-independent board coordinates, viewport transforms, and pawn placement."""

from collections.abc import Mapping
from dataclasses import dataclass
from math import ceil, hypot, isfinite, sqrt
from types import MappingProxyType
from typing import ClassVar, TypeAlias

from Ludo.core.board import Board
from Ludo.core.pawn import Pawn
from Ludo.core.player import Player, PlayerColor
from Ludo.core.state import GameState

__all__ = ("BoardGeometry", "GridCell", "PawnPlacement", "Point")

GridCell: TypeAlias = tuple[int, int]
Point: TypeAlias = tuple[float, float]
_GRID_SIZE = 15
_RED_TRACK_QUARTER: tuple[GridCell, ...] = (
    (6, 0),
    (6, 1),
    (6, 2),
    (6, 3),
    (6, 4),
    (6, 5),
    (6, 6),
    (5, 6),
    (4, 6),
    (3, 6),
    (2, 6),
    (1, 6),
    (0, 6),
    (0, 7),
)
_RED_FINISH_SLOTS: tuple[Point, ...] = (
    (6.4, 6.75),
    (6.4, 7.25),
    (6.4, 7.75),
    (6.4, 8.25),
)


def _rotate_cell(cell: GridCell, quarter_turns: int) -> GridCell:
    """Rotate a row/column cell clockwise around the board.

    Args:
        cell: The original (row, column) cell.
        quarter_turns: Number of clockwise 90-degree turns.

    Returns:
        The rotated (row, column) cell.
    """
    row, column = cell
    for _ in range(quarter_turns % 4):
        row, column = column, _GRID_SIZE - 1 - row
    return row, column


def _rotate_point(point: Point, quarter_turns: int) -> Point:
    """Rotate a continuous grid point clockwise around the board center.

    Args:
        point: The original (column, row) point in grid units.
        quarter_turns: Number of clockwise 90-degree turns.

    Returns:
        The rotated (column, row) point in grid units.
    """
    column, row = point
    for _ in range(quarter_turns % 4):
        column, row = _GRID_SIZE - row, column
    return column, row


@dataclass(frozen=True, slots=True)
class PawnPlacement:
    """A visible pawn circle and identity used for painting and hit testing."""

    color: PlayerColor
    pawn_id: int
    center_x: float
    center_y: float
    radius: float

    def contains(self, position_x: float, position_y: float) -> bool:
        """Check whether a pixel point lies within this pawn's circle.

        Args:
            position_x: Horizontal widget coordinate.
            position_y: Vertical widget coordinate.

        Returns:
            True when the point lies on or inside the visible circle.
        """
        return (
            hypot(position_x - self.center_x, position_y - self.center_y)
            <= self.radius
        )


@dataclass(frozen=True, slots=True)
class BoardGeometry:
    """Map a fixed 15 by 15 board to a centered square viewport."""

    width: float
    height: float
    padding: float = 18.0

    GRID_SIZE: ClassVar[int] = _GRID_SIZE
    BASE_SIZE: ClassVar[int] = 6
    SHARED_TRACK: ClassVar[tuple[GridCell, ...]] = tuple(
        _rotate_cell(cell, quarter_turn)
        for quarter_turn in range(4)
        for cell in _RED_TRACK_QUARTER
    )
    START_COLORS: ClassVar[Mapping[int, PlayerColor]] = MappingProxyType(
        dict(zip(Board.START_OFFSETS, PlayerColor, strict=True))
    )
    BASE_ORIGINS: ClassVar[Mapping[PlayerColor, GridCell]] = MappingProxyType(
        {
            PlayerColor.RED: (0, 0),
            PlayerColor.BLUE: (0, 9),
            PlayerColor.GREEN: (9, 9),
            PlayerColor.YELLOW: (9, 0),
        }
    )
    HOME_STRETCHES: ClassVar[Mapping[PlayerColor, tuple[GridCell, ...]]] = (
        MappingProxyType(
            {
                color: tuple(
                    _rotate_cell((7, column), turn) for column in range(1, 6)
                )
                for turn, color in enumerate(PlayerColor)
            }
        )
    )
    BASE_SLOTS: ClassVar[tuple[Point, ...]] = (
        (2.0, 2.4),
        (4.0, 2.4),
        (2.0, 4.3),
        (4.0, 4.3),
    )
    FINISH_SLOTS: ClassVar[Mapping[PlayerColor, tuple[Point, ...]]] = (
        MappingProxyType(
            {
                color: tuple(
                    _rotate_point(point, turn) for point in _RED_FINISH_SLOTS
                )
                for turn, color in enumerate(PlayerColor)
            }
        )
    )
    FINISH_POLYGONS: ClassVar[Mapping[PlayerColor, tuple[Point, ...]]] = (
        MappingProxyType(
            {
                color: tuple(
                    _rotate_point(point, turn)
                for point in (
                    (6.0, 7.0),
                    (6.0, 8.0),
                    (7.0, 8.0),
                    (7.5, 7.5), 
                    (7.0, 7.0),
)
                )
                for turn, color in enumerate(PlayerColor)
            }
        )
    )
    HOME_DIRECTIONS: ClassVar[Mapping[PlayerColor, Point]] = MappingProxyType(
        {
            PlayerColor.RED: (1.0, 0.0),
            PlayerColor.BLUE: (0.0, 1.0),
            PlayerColor.GREEN: (-1.0, 0.0),
            PlayerColor.YELLOW: (0.0, -1.0),
        }
    )

    def __post_init__(self) -> None:
        """Reject negative or non-finite viewport dimensions and padding."""
        if any(
            not isfinite(value) or value < 0
            for value in (self.width, self.height, self.padding)
        ):
            raise ValueError(
                "Viewport dimensions must be finite and nonnegative."
            )

    @property
    def side(self) -> float:
        """Find the square board size after reserving its outer padding.

        Returns:
            The nonnegative board side length in widget pixels.
        """
        return max(0.0, min(self.width, self.height) - 2 * self.padding)

    @property
    def cell_size(self) -> float:
        """Find the scaled width and height of one grid cell.

        Returns:
            The cell size in widget pixels.
        """
        return self.side / self.GRID_SIZE

    @property
    def origin(self) -> Point:
        """Locate the board's upper-left corner in the widget.

        Returns:
            The (horizontal, vertical) pixel offset of the board.
        """
        return (self.width - self.side) / 2, (self.height - self.side) / 2

    def point(self, column: float, row: float) -> Point:
        """Convert continuous grid coordinates into widget pixels.

        Args:
            column: Horizontal coordinate measured in grid cells.
            row: Vertical coordinate measured in grid cells.

        Returns:
            The corresponding (horizontal, vertical) pixel point.
        """
        origin_x, origin_y = self.origin
        return (
            origin_x + column * self.cell_size,
            origin_y + row * self.cell_size,
        )

    def cell_center(self, cell: GridCell) -> Point:
        """Convert a grid cell into its pixel center.

        Args:
            cell: The (row, column) cell to locate.

        Returns:
            The cell center as a (horizontal, vertical) pixel point.
        """
        row, column = cell
        return self.point(column + 0.5, row + 0.5)

    def cell_at(self, position_x: float, position_y: float) -> GridCell | None:
        """Locate the grid cell containing a pixel point.

        Args:
            position_x: Horizontal widget coordinate.
            position_y: Vertical widget coordinate.

        Returns:
            The (row, column) cell, or None outside a nonempty board.
        """
        origin_x, origin_y = self.origin
        if not self.side or not (
            origin_x <= position_x < origin_x + self.side
            and origin_y <= position_y < origin_y + self.side
        ):
            return None
        return (
            int((position_y - origin_y) / self.cell_size),
            int((position_x - origin_x) / self.cell_size),
        )

    def cell_for(self, player: Player, pawn: Pawn) -> GridCell | None:
        """Map a pawn on the track or home stretch into its grid cell.

        Args:
            player: The pawn's owning player, providing the starting offset.
            pawn: The pawn whose logical progress should be displayed.

        Returns:
            A (row, column) cell, or None for base and finished pawns.
        """
        shared_square = Board.shared_position(
            pawn.progress, player.starting_offset
        )
        if shared_square is not None:
            return self.SHARED_TRACK[shared_square]
        if Board.HOME_STRETCH_START <= pawn.progress < Board.FINISH:
            return self.HOME_STRETCHES[player.color][
                pawn.progress - Board.HOME_STRETCH_START
            ]
        return None

    def pawn_center(self, player: Player, pawn: Pawn) -> Point:
        """Locate a pawn before applying any shared-square stack offsets.

        Args:
            player: The pawn's owning player.
            pawn: The pawn to display in base, on a route, or at finish.

        Returns:
            The unstacked (horizontal, vertical) center in widget pixels.
        """
        return self.point(*self._pawn_grid_point(player, pawn))

    def pawn_placements(self, state: GameState) -> tuple[PawnPlacement, ...]:
        """Lay out every active pawn without hiding co-occupying pawns.

        Args:
            state: The immutable game snapshot to display.

        Returns:
            Pixel circles with player colors and pawn IDs for drawing.
        """
        occupants: dict[Point, list[tuple[Player, Pawn]]] = {}
        for player in state.players:
            for pawn in player.pawns:
                point = self._pawn_grid_point(player, pawn)
                occupants.setdefault(point, []).append((player, pawn))
        placements = []
        for (column, row), pawns in occupants.items():
            pawn_count = len(pawns)
            column_count = ceil(sqrt(pawn_count))
            row_count = ceil(pawn_count / column_count)
            for index, (player, pawn) in enumerate(pawns):
                offset_x, offset_y = 0.0, 0.0
                radius = 0.46 if pawn.in_base else 0.34
                if pawn.finished:
                    radius = 0.18
                if pawn_count > 1:
                    stack_row, stack_column = divmod(index, column_count)
                    pawns_in_row = min(
                        column_count, pawn_count - stack_row * column_count
                    )
                    # Center an incomplete final row inside the same square.
                    offset_x = (
                        (stack_column - (pawns_in_row - 1) / 2)
                        * 0.82
                        / column_count
                    )
                    offset_y = (
                        (stack_row - (row_count - 1) / 2) * 0.82 / row_count
                    )
                    radius = 0.36 / max(column_count, row_count)
                center_x, center_y = self.point(
                    column + offset_x, row + offset_y
                )
                placements.append(
                    PawnPlacement(
                        player.color,
                        pawn.id,
                        center_x,
                        center_y,
                        radius * self.cell_size,
                    )
                )
        return tuple(placements)

    def _pawn_grid_point(self, player: Player, pawn: Pawn) -> Point:
        """Locate a pawn in continuous board coordinates.

        Args:
            player: The owning player.
            pawn: The pawn whose location should be mapped.

        Returns:
            The (column, row) point measured in grid units.
        """
        if pawn.in_base:
            base_row, base_column = self.BASE_ORIGINS[player.color]
            column, row = self.BASE_SLOTS[pawn.id]
            return base_column + column, base_row + row
        if pawn.finished:
            return self.FINISH_SLOTS[player.color][pawn.id]
        cell = self.cell_for(player, pawn)
        assert cell is not None
        row, column = cell
        return column + 0.5, row + 0.5
