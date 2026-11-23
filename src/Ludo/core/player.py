"""Player colors, fixed track offsets, and immutable pawn ownership."""

from dataclasses import dataclass, field
from enum import StrEnum

from Ludo.core.board import Board
from Ludo.core.exceptions import InvalidSetupError
from Ludo.core.pawn import Pawn

__all__ = ("Player", "PlayerColor")


class PlayerColor(StrEnum):
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
        """Validate the color and four ordered pawn IDs."""
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
        """Locate this color's fixed starting square on the shared track.

        Returns:
            The color offset: red 0, blue 13, green 26, or yellow 39.
        """
        return Board.START_OFFSETS[tuple(PlayerColor).index(self.color)]

    @property
    def has_won(self) -> bool:
        """Check whether every pawn has reached the finish.

        Returns:
            True when all four pawns are finished; otherwise False.
        """
        return all(pawn.finished for pawn in self.pawns)
