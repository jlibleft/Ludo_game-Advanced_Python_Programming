"""Presentation and intent signals for local-human game controls."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from Ludo.core.player import PlayerColor
from Ludo.core.state import GameState
from Ludo.gui.styles import PLAYER_COLORS

__all__ = ("GameSidebar",)


class GameSidebar(QFrame):
    """Display turn information and emit human intentions without game rules."""

    roll_requested = Signal()
    new_game_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        """Build turn, roster, dice, feedback, and new-game controls.

        Args:
            parent: The owning Qt widget.
        """
        super().__init__(parent)
        self.setObjectName("gameSidebar")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(6)
        heading = QLabel("CURRENT PLAYER", self)
        heading.setProperty("role", "sectionHeading")
        layout.addWidget(heading)
        self._active_player = QLabel(self)
        self._active_player.setObjectName("activePlayer")
        layout.addWidget(self._active_player)

        self._player_rows: dict[PlayerColor, QWidget] = {}
        self._finish_counts: dict[PlayerColor, QLabel] = {}
        for color in PlayerColor:
            row = QWidget(self)
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            name = QLabel(f"●  {color.value.title()}", row)
            name.setProperty("role", "legend")
            name.setProperty("playerColor", color.value)
            row_layout.addWidget(name)
            row_layout.addStretch()
            count = QLabel("0/4 finished", row)
            count.setObjectName(f"{color.value}FinishCount")
            count.setProperty("role", "muted")
            row_layout.addWidget(count)
            self._player_rows[color] = row
            self._finish_counts[color] = count
            layout.addWidget(row)

        self._dice_result = QLabel("—", self)
        self._dice_result.setObjectName("diceResult")
        self._dice_result.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._dice_result)
        self._dice_owner = QLabel("Waiting for the first roll", self)
        self._dice_owner.setObjectName("diceOwner")
        self._dice_owner.setProperty("role", "muted")
        self._dice_owner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._dice_owner)
        self._roll_button = QPushButton("Roll Dice", self)
        self._roll_button.setObjectName("rollDiceButton")
        self._roll_button.setToolTip(
            "Roll once, then choose a highlighted pawn."
        )
        self._roll_button.clicked.connect(self.roll_requested)
        layout.addWidget(self._roll_button)

        status_heading = QLabel("GAME STATUS", self)
        status_heading.setProperty("role", "sectionHeading")
        layout.addWidget(status_heading)
        self._status = QLabel(self)
        self._status.setObjectName("gameStatus")
        self._status.setTextFormat(Qt.TextFormat.PlainText)
        self._status.setWordWrap(True)
        self._status.setMinimumHeight(52)
        layout.addWidget(self._status)
        layout.addStretch()

        players_heading = QLabel("PLAYERS FOR NEW GAME", self)
        players_heading.setProperty("role", "sectionHeading")
        layout.addWidget(players_heading)
        self._player_count = QComboBox(self)
        self._player_count.setObjectName("playerCount")
        for count in range(GameState.MIN_PLAYERS, GameState.MAX_PLAYERS + 1):
            self._player_count.addItem(f"{count} human players", count)
        layout.addWidget(self._player_count)
        new_game_button = QPushButton("New Game", self)
        new_game_button.setObjectName("newGameButton")
        new_game_button.clicked.connect(self.new_game_requested)
        layout.addWidget(new_game_button)
        self._displayed_player_count: int | None = None

    @property
    def selected_player_count(self) -> int:
        """Read the number of humans chosen for the next new game.

        Returns:
            The selected player count from the engine's supported range.
        """
        return int(self._player_count.currentData())

    def set_turn(
        self,
        state: GameState,
        last_roll: int | None,
        last_roller: PlayerColor | None,
        message: str,
        can_roll: bool,
    ) -> None:
        """Refresh the controls from controller-supplied presentation data.

        Args:
            state: The current immutable game snapshot.
            last_roll: The most recently rolled value, or None.
            last_roller: Who produced the last dice result, or None.
            message: Feedback and the next-action prompt.
            can_roll: The engine's authoritative permission to roll.
        """
        color = state.active_player.color
        name = color.value.title()
        self._active_player.setText(f"{name} wins!" if state.winner else name)
        self._active_player.setStyleSheet(f"color: {PLAYER_COLORS[color]};")
        self._active_player.setAccessibleName(f"Active player: {name}")
        self._dice_result.setText(
            str(last_roll) if last_roll is not None else "—"
        )
        self._dice_result.setAccessibleName(
            f"Dice result: {last_roll}"
            if last_roll is not None
            else "Die not rolled yet"
        )
        self._dice_owner.setText(
            f"Last roll · {last_roller.value.title()}"
            if last_roller is not None
            else "Waiting for the first roll"
        )
        self._roll_button.setEnabled(can_roll)
        self._status.setText(message)
        players = {player.color: player for player in state.players}
        for player_color, row in self._player_rows.items():
            row.setVisible(player_color in players)
            if player_color in players:
                finished = sum(
                    pawn.finished for pawn in players[player_color].pawns
                )
                self._finish_counts[player_color].setText(
                    f"{finished}/4 finished"
                )
        if self._displayed_player_count != len(state.players):
            # Keep the next game's selection while the current game advances.
            self._player_count.setCurrentIndex(
                self._player_count.findData(len(state.players))
            )
            self._displayed_player_count = len(state.players)
