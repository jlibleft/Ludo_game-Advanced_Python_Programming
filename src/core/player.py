"""Player colors, fixed track offsets, and immutable pawn ownership."""

from dataclasses import dataclass, field
from enum import Enum

from src.core.board import Board
from src.core.exceptions import InvalidSetupError
from src.core.pawn import Pawn


class PlayerColor(str, Enum):
    """Color order fixes starting offsets independently of roster order."""

    RED = "red"
    BLUE = "blue"
    GREEN = "green"
    YELLOW = "yellow"


@dataclass(frozen=True, slots=True)
class Player:
    """A player with four ordered pawn IDs and a color-specific start."""

    color: PlayerColor
    pawns: tuple[Pawn, ...] = field(
        default_factory=lambda: tuple(
            Pawn(pawn_id) for pawn_id in range(Board.PAWNS_PER_PLAYER)
        )
    )

    def __post_init__(self) -> None:
        if not isinstance(self.color, PlayerColor):
            raise InvalidSetupError("Player color must be a PlayerColor.")
        if (
            not isinstance(self.pawns, tuple)
            or len(self.pawns) != Board.PAWNS_PER_PLAYER
            or any(not isinstance(pawn, Pawn) for pawn in self.pawns)
            or tuple(pawn.id for pawn in self.pawns) != (0, 1, 2, 3)
        ):
            raise InvalidSetupError("Each player needs pawn IDs 0, 1, 2, 3.")

    @property
    def starting_offset(self) -> int:
        return Board.START_OFFSETS[tuple(PlayerColor).index(self.color)]

    @property
    def has_won(self) -> bool:
        return all(pawn.finished for pawn in self.pawns)
