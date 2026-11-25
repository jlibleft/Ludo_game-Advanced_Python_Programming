"""Qt action routing and feedback around the authoritative game engine."""

from collections.abc import Sequence

from PySide6.QtCore import QObject, Signal, Slot

from Ludo.core.exceptions import GameError
from Ludo.core.game import GameEngine
from Ludo.core.player import PlayerColor
from Ludo.core.state import GameState

__all__ = ("GameController",)


class GameController(QObject):
    """Translate human actions into engine calls and publish coherent updates."""

    updated = Signal()
    game_won = Signal(str)

    def __init__(
        self, engine: GameEngine | None = None, parent: QObject | None = None
    ) -> None:
        """Connect a playable game to Qt without adding movement rules.

        Args:
            engine: The game to control, or None for a fresh four-player game.
            parent: The QObject owning this controller.
        """
        super().__init__(parent)
        self._engine = engine if engine is not None else GameEngine()
        self._reset_feedback()
        self._message = self._turn_prompt()

    @property
    def state(self) -> GameState:
        """Read the current authoritative game snapshot.

        Returns:
            The immutable GameState owned by the engine.
        """
        return self._engine.state

    @property
    def can_roll(self) -> bool:
        """Expose the engine's roll permission for the dice button.

        Returns:
            True when the engine currently permits rolling.
        """
        return self._engine.can_roll

    @property
    def legal_moves(self) -> tuple[int, ...]:
        """Find pawn IDs that the engine currently permits selecting.

        Returns:
            Legal active-player pawn IDs, or an empty tuple.
        """
        return self._engine.legal_moves()

    @property
    def last_roll(self) -> int | None:
        """Read the most recent successfully rolled value.

        Returns:
            A dice result from 1 to 6, or None before the first roll.
        """
        return self._last_roll

    @property
    def last_roller(self) -> PlayerColor | None:
        """Identify who produced the displayed dice result.

        Returns:
            The rolling player's color, or None before the first roll.
        """
        return self._last_roller

    @property
    def selected_pawn(self) -> tuple[PlayerColor, int] | None:
        """Identify the pawn most recently selected and moved successfully.

        Returns:
            The owning color and pawn ID, or None after a roll or reset.
        """
        return self._selected_pawn

    @property
    def message(self) -> str:
        """Read the latest action feedback and next-action instruction.

        Returns:
            A human-readable status message for the game view.
        """
        return self._message

    @Slot()
    def roll_dice(self) -> None:
        """Ask the engine to roll and report its move or turn outcome."""
        roller = self.state.active_player.color
        try:
            rolled_value = self._engine.roll_dice()
        except GameError as error:
            self._reject(error)
            return
        self._last_roll = rolled_value
        self._last_roller = roller
        self._selected_pawn = None
        if self.legal_moves:
            self._message = (
                f"{roller.value.title()} rolled {rolled_value}. "
                "Choose a highlighted pawn."
            )
        elif self.state.active_player.color == roller:
            self._message = (
                f"{roller.value.title()} rolled {rolled_value}. "
                "No legal moves; roll again."
            )
        else:
            self._message = (
                f"{roller.value.title()} rolled {rolled_value}. "
                f"No legal moves. {self._turn_prompt()}"
            )
        self.updated.emit()

    @Slot(str, int)
    def move_pawn(self, color_name: str, pawn_id: int) -> None:
        """Route a pawn click to the engine and describe the actual result.

        Args:
            color_name: The clicked pawn owner's lowercase color name.
            pawn_id: The clicked pawn ID, from 0 to 3.
        """
        before = self.state
        mover = before.active_player.color
        if color_name != mover.value:
            self._message = (
                "Only the active player's highlighted pawns can move."
            )
            self.updated.emit()
            return
        try:
            self._engine.move_pawn(pawn_id)
        except GameError as error:
            self._reject(error)
            return
        self._selected_pawn = (mover, pawn_id)
        captured = self._capture_count(before, self.state, mover)
        action = f"{mover.value.title()} moved pawn {pawn_id + 1}."
        if captured:
            noun = "pawn" if captured == 1 else "pawns"
            action += f" Captured {captured} opponent {noun}."
        if (
            self.state.winner is None
            and self.state.active_player.color == mover
        ):
            self._message = (
                f"{action} {mover.value.title()} gets another roll."
            )
        else:
            self._message = f"{action} {self._turn_prompt()}"
        self.updated.emit()
        if self.state.winner is not None:
            self.game_won.emit(self.state.winner.value)

    @Slot(object)
    def new_game(
        self, colors: Sequence[PlayerColor | str] | None = None
    ) -> None:
        """Start a new game, allowing the engine to validate the roster.

        Args:
            colors: The new color order, or None to reset the existing roster.
        """
        try:
            if colors is None:
                self._engine.reset()
            else:
                self._engine.new_game(colors)
        except GameError as error:
            self._reject(error)
            return
        self._reset_feedback()
        self._message = f"New game. {self._turn_prompt()}"
        self.updated.emit()

    def load_state(self, state: GameState) -> None:
        """Replace the playable game with a validated in-memory snapshot.

        Args:
            state: The snapshot to load; a fresh default dice source is used.
        """
        self._engine = GameEngine.from_state(state)
        self._reset_feedback()
        self._message = self._turn_prompt()
        self.updated.emit()

    def _turn_prompt(self) -> str:
        """Describe the next action using the engine's current turn phase.

        Returns:
            A winner message, pawn-selection instruction, or rolling prompt.
        """
        color_name = self.state.active_player.color.value.title()
        if self.state.winner is not None:
            return f"{color_name} wins! All four pawns are finished."
        if self.legal_moves:
            return f"{color_name}: choose a highlighted pawn."
        return f"{color_name}'s turn. Roll the die."

    def _reset_feedback(self) -> None:
        """Reset die feedback from the snapshot and clear pawn selection."""
        self._last_roll: int | None = self.state.pending_roll
        self._last_roller: PlayerColor | None = None
        if self._last_roll is not None:
            self._last_roller = self.state.active_player.color
        self._selected_pawn: tuple[PlayerColor, int] | None = None

    def _reject(self, error: GameError) -> None:
        """Publish a rejected action while retaining the engine snapshot.

        Args:
            error: The domain error describing why the action was rejected.
        """
        self._message = str(error)
        self.updated.emit()

    @staticmethod
    def _capture_count(
        before: GameState, after: GameState, mover: PlayerColor
    ) -> int:
        """Count actual opponent returns to base for feedback, not legality.

        Args:
            before: The snapshot before the accepted move.
            after: The snapshot produced by the engine.
            mover: The moving player's color.

        Returns:
            The number of opposing pawns returned to base by this move.
        """
        captured_count = 0
        for old_player, new_player in zip(
            before.players, after.players, strict=True
        ):
            if old_player.color == mover:
                continue
            for old_pawn, new_pawn in zip(
                old_player.pawns, new_player.pawns, strict=True
            ):
                if not old_pawn.in_base and new_pawn.in_base:
                    captured_count += 1
        return captured_count
