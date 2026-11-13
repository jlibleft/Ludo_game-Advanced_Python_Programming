"""Domain errors callers can handle without depending on Qt."""


class GameError(Exception):
    """Base exception for invalid Ludo operations."""


class InvalidSetupError(GameError, ValueError):
    """A player roster or state snapshot is inconsistent."""


class InvalidTurnError(GameError, RuntimeError):
    """An action is not available in the current turn phase."""


class GameOverError(InvalidTurnError):
    """The game already has a winner."""


class InvalidMoveError(GameError, ValueError):
    """A pawn cannot make the requested move."""


class InvalidRollError(GameError, ValueError):
    """A dice source produced something other than an integer from 1 to 6."""
