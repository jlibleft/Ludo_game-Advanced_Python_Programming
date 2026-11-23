"""Turn orchestration and atomic Ludo state transitions, without Qt."""

from collections.abc import Sequence
from dataclasses import replace

from Ludo.core.board import Board
from Ludo.core.dice import Dice
from Ludo.core.exceptions import (
    GameOverError,
    InvalidMoveError,
    InvalidSetupError,
    InvalidTurnError,
)
from Ludo.core.pawn import Pawn
from Ludo.core.player import Player, PlayerColor
from Ludo.core.state import GameState

__all__ = ("Game", "GameEngine")


class GameEngine:
    """Own a game snapshot and accept only valid roll/move operations."""

    MAX_DICE = 6

    def __init__(
        self,
        colors: Sequence[PlayerColor | str] = tuple(PlayerColor),
        *,
        dice: Dice | None = None,
    ) -> None:
        """Create a fresh game with the selected player colors.

        Args:
            colors: Two to four distinct PlayerColor values or lowercase
                color names, in turn order. Defaults to all four colors.
            dice: The dice instance to use. Creates a Dice instance when
                None.
        """
        self._dice = dice if dice is not None else Dice()
        self.new_game(colors)

    @classmethod
    def from_state(
        cls, state: GameState, *, dice: Dice | None = None
    ) -> "GameEngine":
        """Create an engine from a validated in-memory snapshot.

        Args:
            state: The immutable GameState snapshot to begin with.
            dice: The dice instance to use. Creates a Dice instance when
                None.

        Returns:
            A new engine using the supplied snapshot and dice source.
        """
        if not isinstance(state, GameState):
            raise InvalidSetupError("Expected a GameState snapshot.")
        colors = tuple(player.color for player in state.players)
        engine = cls(colors, dice=dice)
        engine._state = state
        return engine

    @property
    def state(self) -> GameState:
        """Expose the current game snapshot for reading.

        Returns:
            The immutable GameState; later actions do not change this
            snapshot.
        """
        return self._state

    @property
    def active_player(self) -> Player:
        """Identify the player whose turn is active.

        Returns:
            The active Player from the current snapshot.
        """
        return self._state.active_player

    @property
    def winner(self) -> Player | None:
        """Identify the player who has won the game.

        Returns:
            The winning Player, or None while the game is unfinished.
        """
        if self._state.winner is None:
            return None
        return self.active_player

    def new_game(self, colors: Sequence[PlayerColor | str]) -> GameState:
        """Replace the roster atomically; the first listed color starts.

        Args:
            colors: Two to four distinct PlayerColor values or lowercase
                color names, in turn order.

        Returns:
            The new GameState with all pawns in base and no pending roll or
            winner.
        """
        if isinstance(colors, (str, bytes)):
            raise InvalidSetupError("Provide a sequence of 2 to 4 colors.")
        try:
            players = tuple(Player(PlayerColor(color)) for color in colors)
        except (TypeError, ValueError) as error:
            raise InvalidSetupError(
                "Use red, blue, green or yellow."
            ) from error
        state = GameState(players=players)
        self._state = state
        return state

    def reset(self) -> GameState:
        """Restart the same roster while retaining the dice source.

        Returns:
            The reset GameState with the first player active and all pawns
            in base.
        """
        colors = tuple(player.color for player in self.state.players)
        return self.new_game(colors)

    def roll_dice(self) -> int:
        """Roll once and resolve automatic passes or preserved bonuses.

        Returns:
            The integer dice result from 1 to 6. Unplayable rolls
            automatically resolve the turn; a six preserves the same
            player.
        """
        self._require_running()
        if self._state.pending_roll is not None:
            raise InvalidTurnError("Move a pawn before rolling again.")
        roll = self._dice.roll()
        Board.validate_roll(roll)
        if self._movable_pawns(roll):
            self._state = replace(self._state, pending_roll=roll)
        else:
            self._state = replace(
                self._state,
                active_player_index=self._next_player_index(roll),
            )
        return roll

    def legal_moves(self) -> tuple[int, ...]:
        """Find active-player pawns that can use the pending roll.

        Returns:
            A tuple of legal pawn IDs. Empty when no roll is pending or the
            game has ended.
        """
        roll = self._state.pending_roll
        if roll is None or self._state.winner is not None:
            return ()
        return self._movable_pawns(roll)

    def move_pawn(self, pawn_id: int) -> GameState:
        """Move an active pawn, capture opponents, and resolve the turn.

        Args:
            pawn_id: The active player's pawn ID, from 0 to 3, selected
                from legal_moves().

        Returns:
            The updated GameState after movement, captures, and turn or
            victory resolution.
        """
        self._require_running()
        roll = self._state.pending_roll
        if roll is None:
            raise InvalidTurnError("Roll the die before choosing a pawn.")
        if type(pawn_id) is not int or pawn_id not in self.legal_moves():
            raise InvalidMoveError("Choose a pawn ID from legal_moves().")

        pawn = self.active_player.pawns[pawn_id]
        destination = Board.destination(pawn.progress, roll)
        # Membership in legal_moves guarantees a destination exists.
        assert destination is not None
        moved_pawn = replace(pawn, progress=destination)
        moved_player = replace(
            self.active_player,
            pawns=tuple(
                moved_pawn if item.id == pawn_id else item
                for item in self.active_player.pawns
            ),
        )
        players = self._players_after_capture(moved_player, moved_pawn)
        winner = moved_player.color if moved_player.has_won else None
        state = GameState(
            players=players,
            active_player_index=(
                self._state.active_player_index
                if winner is not None
                else self._next_player_index(roll)
            ),
            winner=winner,
        )
        self._state = state
        return state

    def _players_after_capture(
        self, moved_player: Player, moved_pawn: Pawn
    ) -> tuple[Player, ...]:
        """Build the roster after a move and any resulting captures.

        Args:
            moved_player: The active player with the selected pawn already
                moved.
            moved_pawn: The moved pawn at its destination.

        Returns:
            Players in their existing turn order, with all captured
            opponent pawns returned to base. Safe and private squares cause
            no captures.
        """
        square = Board.shared_position(
            moved_pawn.progress, moved_player.starting_offset
        )
        players = []
        for player in self._state.players:
            if player.color == moved_player.color:
                players.append(moved_player)
            elif square is None or square in Board.SAFE_SQUARES:
                players.append(player)
            else:
                players.append(
                    replace(
                        player,
                        pawns=tuple(
                            replace(pawn, progress=Board.BASE)
                            if Board.shared_position(
                                pawn.progress, player.starting_offset
                            )
                            == square
                            else pawn
                            for pawn in player.pawns
                        ),
                    )
                )
        return tuple(players)

    def _movable_pawns(self, roll: int) -> tuple[int, ...]:
        """Find active-player pawns with a legal destination for a roll.

        Args:
            roll: The validated dice result from 1 to 6.

        Returns:
            A tuple of movable pawn IDs, or an empty tuple if none can
            move.
        """
        return tuple(
            pawn.id
            for pawn in self.active_player.pawns
            if Board.destination(pawn.progress, roll) is not None
        )

    def _next_player_index(self, roll: int) -> int:
        """Determine who acts after the current roll is resolved.

        Args:
            roll: The dice result used to determine whether a bonus roll
                applies.

        Returns:
            The current player index for a six; otherwise the next index,
            wrapping to the first player when necessary.
        """
        if roll == self.MAX_DICE:
            return self._state.active_player_index
        return (self._state.active_player_index + 1) % len(self._state.players)

    def _require_running(self) -> None:
        """Reject an action when the current game already has a winner."""
        if self._state.winner is not None:
            raise GameOverError("The game has ended; reset or start again.")


Game = GameEngine
