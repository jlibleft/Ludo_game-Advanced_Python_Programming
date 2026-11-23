"""Validated immutable game snapshots; no engine or GUI dependencies."""

from dataclasses import dataclass
from typing import ClassVar

from Ludo.core.board import Board
from Ludo.core.exceptions import InvalidSetupError
from Ludo.core.player import Player, PlayerColor


@dataclass(frozen=True, slots=True)
class GameState:
    """A roster and turn phase; pending_roll=None means ready to roll."""

    players: tuple[Player, ...]
    active_player_index: int = 0
    pending_roll: int | None = None
    winner: PlayerColor | None = None

    MIN_PLAYERS: ClassVar[int] = 2
    MAX_PLAYERS: ClassVar[int] = 4

    def __post_init__(self) -> None:
        """Validate the roster, turn phase, winner, and board occupancy."""
        self._validate_player_count()
        self._validate_active_player_index()
        self._validate_player_colors()
        self._validate_pending_roll()
        self._validate_winner_state(self.winners)
        self._validate_occupancy()

    @property
    def active_player(self) -> Player:
        """Find the player selected by the active-player index.

        Returns:
            The Player whose turn is active in this snapshot.
        """
        return self.players[self.active_player_index]

    @property
    def winners(self) -> tuple[PlayerColor, ...]:
        """Find players whose four pawns have all finished.

        Returns:
            A tuple of finished player colors in roster order; empty before
            any player has finished all four pawns.
        """
        return tuple(player.color for player in self.players if player.has_won)

    def _validate_occupancy(self) -> None:
        """Reject opponents sharing an unsafe shared-track square."""
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

    def _validate_player_count(self) -> None:
        """Require an immutable roster containing two to four Players."""
        if (
            not isinstance(self.players, tuple)
            or not self.MIN_PLAYERS <= len(self.players) <= self.MAX_PLAYERS
            or any(not isinstance(player, Player) for player in self.players)
        ):
            raise InvalidSetupError("A game needs a tuple of 2 to 4 players.")

    def _validate_active_player_index(self) -> None:
        """Require an integer index identifying a player in the roster."""
        if type(
            self.active_player_index
        ) is not int or not 0 <= self.active_player_index < len(self.players):
            raise InvalidSetupError("The active player index is invalid.")

    def _validate_player_colors(self) -> None:
        """Reject repeated player colors in the roster."""
        if len({player.color for player in self.players}) != len(self.players):
            raise InvalidSetupError("Players must have distinct colors.")

    def _validate_pending_roll(self) -> None:
        """Require any pending roll to be valid and playable."""
        if self.pending_roll is not None:
            Board.validate_roll(self.pending_roll)
            if not any(
                Board.destination(pawn.progress, self.pending_roll) is not None
                for pawn in self.active_player.pawns
            ):
                raise InvalidSetupError("A pending roll needs a legal move.")

    def _validate_winner_state(self, winners: tuple[PlayerColor, ...]) -> None:
        """Check that finished players and the turn agree with the winner.

        Args:
            winners: Colors of players with four finished pawns, in roster
                order.
        """
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
