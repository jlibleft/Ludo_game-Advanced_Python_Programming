"""Logical routes and move destinations, independent of board rendering."""

from src.core.exceptions import InvalidMoveError, InvalidRollError


class Board:
    """Translate player-relative progress into shared board coordinates."""

    BASE = -1
    TRACK_LENGTH = 52
    HOME_STRETCH_START = TRACK_LENGTH
    FINISH = 57
    START_OFFSETS = (0, 13, 26, 39)
    SAFE_SQUARES = frozenset(START_OFFSETS)
    PAWNS_PER_PLAYER = 4

    @classmethod
    def validate_progress(cls, progress: int) -> None:
        """Reject positions outside the single logical progress range."""
        if type(progress) is not int or not cls.BASE <= progress <= cls.FINISH:
            raise InvalidMoveError("Pawn progress must be an integer -1..57.")

    @staticmethod
    def validate_roll(value: int) -> None:
        """Reject invalid dice values, including bools masquerading as ints."""
        if type(value) is not int or not 1 <= value <= 6:
            raise InvalidRollError("Dice results must be integers in 1..6.")

    @classmethod
    def shared_position(
        cls, progress: int, starting_offset: int
    ) -> int | None:
        """Return an absolute track square, or None off the shared track."""
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
        """Return a legal destination, or None when this pawn cannot move."""
        cls.validate_progress(progress)
        cls.validate_roll(roll)
        if progress == cls.BASE:
            return 0 if roll == 6 else None
        if progress == cls.FINISH or progress + roll > cls.FINISH:
            return None
        return progress + roll
