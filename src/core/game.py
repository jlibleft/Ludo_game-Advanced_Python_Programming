"""Turn orchestration and atomic Ludo state transitions, without Qt."""

from collections.abc import Sequence
from dataclasses import replace

from src.core.board import Board
from src.core.dice import Dice
from src.core.exceptions import (
    GameOverError,
    InvalidMoveError,
    InvalidSetupError,
    InvalidTurnError,
)
from src.core.pawn import Pawn
from src.core.player import Player, PlayerColor
from src.core.state import GameState


class GameEngine:
    """Own a game snapshot and accept only valid roll/move operations."""

    def __init__(
        self,
        colors: Sequence[PlayerColor | str] = tuple(PlayerColor),
        *,
        dice: Dice | None = None,
    ) -> None:
        self._dice = dice if dice is not None else Dice()
        self.new_game(colors)

    @classmethod
    def from_state(
        cls, state: GameState, *, dice: Dice | None = None
    ) -> "GameEngine":
        """Start from a validated in-memory snapshot, useful for scenarios."""
        if not isinstance(state, GameState):
            raise InvalidSetupError("Expected a GameState snapshot.")
        colors = tuple(player.color for player in state.players)
        engine = cls(colors, dice=dice)
        engine._state = state
        return engine

    @property
    def state(self) -> GameState:
        """Read-only snapshot; earlier snapshots remain unchanged by moves."""
        return self._state

    @property
    def active_player(self) -> Player:
        return self._state.active_player

    @property
    def winner(self) -> Player | None:
        if self._state.winner is None:
            return None
        return self.active_player

    def new_game(self, colors: Sequence[PlayerColor | str]) -> GameState:
        """Replace the roster atomically; the first listed color starts."""
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
        """Reset the same roster to base, retaining the dice source."""
        colors = tuple(player.color for player in self.state.players)
        return self.new_game(colors)

    def roll_dice(self) -> int:
        """Roll once; auto-pass an unplayable roll, preserving extra sixes."""
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
        """Return active player's movable pawn IDs for the pending roll."""
        roll = self._state.pending_roll
        if roll is None or self._state.winner is not None:
            return ()
        return self._movable_pawns(roll)

    def move_pawn(self, pawn_id: int) -> GameState:
        """Move an active pawn, capture opponents, then resolve the turn."""
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
                players.append(replace(
                    player,
                    pawns=tuple(
                        replace(pawn, progress=Board.BASE)
                        if Board.shared_position(
                            pawn.progress, player.starting_offset
                        ) == square
                        else pawn
                        for pawn in player.pawns
                    ),
                ))
        return tuple(players)

    def _movable_pawns(self, roll: int) -> tuple[int, ...]:
        return tuple(
            pawn.id for pawn in self.active_player.pawns
            if Board.destination(pawn.progress, roll) is not None
        )

    def _next_player_index(self, roll: int) -> int:
        if roll == 6:
            return self._state.active_player_index
        return (self._state.active_player_index + 1) % len(self._state.players)

    def _require_running(self) -> None:
        if self._state.winner is not None:
            raise GameOverError("The game has ended; reset or start again.")


Game = GameEngine
