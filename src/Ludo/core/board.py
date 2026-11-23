"""Logical routes and move destinations, independent of board rendering."""

from Ludo.core.exceptions import InvalidMoveError, InvalidRollError

__all__ = ("Board",)


class Board:
    """Translate player-relative progress into shared board coordinates."""

    BASE = -1
    TRACK_LENGTH = 52
    HOME_STRETCH_START = TRACK_LENGTH
    FINISH = 57
    START_OFFSETS = (0, 13, 26, 39)
    SAFE_SQUARES = frozenset(START_OFFSETS)
    PAWNS_PER_PLAYER = 4
    MIN_DICE = 1
    MAX_DICE = 6

    @classmethod
    def validate_progress(cls, progress: int) -> None:
        """Reject positions outside the logical pawn progress range.

        Args:
            progress: Player-relative position: -1 for base, 0..51 for
                track, 52..56 for home stretch, or 57 for finish.
        """
        if type(progress) is not int or not cls.BASE <= progress <= cls.FINISH:
            raise InvalidMoveError("Pawn progress must be an integer -1..57.")

    @staticmethod
    def validate_roll(value: int) -> None:
        """Reject dice values outside the integer range 1..6.

        Args:
            value: Dice result to validate; bool values are not accepted.
        """
        if (
            type(value) is not int
            or not Board.MIN_DICE <= value <= Board.MAX_DICE
        ):
            raise InvalidRollError("Dice results must be integers in 1..6.")

    @classmethod
    def shared_position(
        cls, progress: int, starting_offset: int
    ) -> int | None:
        """Translate player-relative progress to a shared-track square.

        Args:
            progress: Logical pawn position from -1 to 57.
            starting_offset: The player's fixed starting square: 0, 13, 26,
                or 39.

        Returns:
            The absolute square in 0..51, or None for base, home stretch,
            or finish.
        """
        cls.validate_progress(progress)
        if (
            type(starting_offset) is not int
            or starting_offset not in cls.START_OFFSETS
        ):
            raise InvalidMoveError("Starting offset must be 0, 13, 26 or 39.")
        if 0 <= progress < cls.TRACK_LENGTH:
            return (starting_offset + progress) % cls.TRACK_LENGTH
        return None

    @classmethod
    def destination(cls, progress: int, roll: int) -> int | None:
        """Calculate the destination permitted by a dice roll.

        Args:
            progress: The pawn's current logical position from -1 to 57.
            roll: An integer dice result from 1 to 6.

        Returns:
            The new logical position, or None if the pawn cannot move. A
            six releases a base pawn to position 0.
        """
        cls.validate_progress(progress)
        cls.validate_roll(roll)
        if progress == cls.BASE:
            return 0 if roll == cls.MAX_DICE else None
        if progress == cls.FINISH or progress + roll > cls.FINISH:
            return None
        return progress + roll
