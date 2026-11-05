"""Immutable player-relative pawn positions."""

from dataclasses import dataclass

from src.core.board import Board
from src.core.exceptions import InvalidSetupError


@dataclass(frozen=True, slots=True)
class Pawn:
    """One of four pawns: base -1, track 0..51, stretch 52..56, finish 57."""

    id: int
    progress: int = Board.BASE

    def __post_init__(self) -> None:
        if (
            type(self.id) is not int
            or not 0 <= self.id < Board.PAWNS_PER_PLAYER
        ):
            raise InvalidSetupError("Pawn IDs must be integers from 0 to 3.")
        Board.validate_progress(self.progress)

    @property
    def in_base(self) -> bool:
        return self.progress == Board.BASE

    @property
    def finished(self) -> bool:
        return self.progress == Board.FINISH
