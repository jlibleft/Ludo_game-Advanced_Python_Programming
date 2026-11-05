"""Validated immutable game snapshots; no engine or GUI dependencies."""

from dataclasses import dataclass

from src.core.board import Board
from src.core.exceptions import InvalidSetupError
from src.core.player import Player, PlayerColor


@dataclass(frozen=True, slots=True)
class GameState:
    """A roster and turn phase; pending_roll=None means ready to roll."""

    players: tuple[Player, ...]
    active_player_index: int = 0
    pending_roll: int | None = None
    winner: PlayerColor | None = None

    def __post_init__(self) -> None:
        if (
            not isinstance(self.players, tuple)
            or not 2 <= len(self.players) <= 4
            or any(not isinstance(player, Player) for player in self.players)
        ):
            raise InvalidSetupError("A game needs a tuple of 2 to 4 players.")
        if len({player.color for player in self.players}) != len(self.players):
            raise InvalidSetupError("Players must have distinct colors.")
        if (
            type(self.active_player_index) is not int
            or not 0 <= self.active_player_index < len(self.players)
        ):
            raise InvalidSetupError("The active player index is invalid.")
        if self.pending_roll is not None:
            Board.validate_roll(self.pending_roll)
            if not any(
                Board.destination(pawn.progress, self.pending_roll) is not None
                for pawn in self.active_player.pawns
            ):
                raise InvalidSetupError("A pending roll needs a legal move.")

        winners = tuple(
            player.color for player in self.players if player.has_won
        )
        if self.winner is None:
            if winners:
                raise InvalidSetupError("Finished players need a winner flag.")
        elif (
            not isinstance(self.winner, PlayerColor)
            or winners != (self.winner,)
            or self.active_player.color != self.winner
            or self.pending_roll is not None
        ):
            raise InvalidSetupError("Winner and turn state are inconsistent.")
        self._validate_occupancy()

    @property
    def active_player(self) -> Player:
        return self.players[self.active_player_index]

    def _validate_occupancy(self) -> None:
        """Opponents can share a track square only when that square is safe."""
        occupants: dict[int, PlayerColor] = {}
        for player in self.players:
            for pawn in player.pawns:
                square = Board.shared_position(
                    pawn.progress, player.starting_offset
                )
                if square is None or square in Board.SAFE_SQUARES:
                    continue
                if square in occupants and occupants[square] != player.color:
                    raise InvalidSetupError(
                        "Opponents cannot share an unsafe track square."
                    )
                occupants[square] = player.color
