"""Playable desktop layout connecting controller intents and state views."""

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from Ludo.config import APP_CONFIG
from Ludo.core.game import GameEngine
from Ludo.core.player import PlayerColor
from Ludo.core.state import GameState
from Ludo.gui.board_widget import BoardWidget
from Ludo.gui.game_controller import GameController
from Ludo.gui.game_sidebar import GameSidebar

__all__ = ("MainWindow",)


class MainWindow(QMainWindow):
    """Host the board and controls for one local multiplayer game."""

    def __init__(
        self,
        state: GameState | None = None,
        *,
        engine: GameEngine | None = None,
    ) -> None:
        """Build the window around an engine or a validated scenario snapshot.

        Args:
            state: An optional starting snapshot with a fresh default die.
            engine: An existing playable engine, including its injected die.
                Supply either state or engine, not both.
        """
        if state is not None and engine is not None:
            raise ValueError("Supply either a starting state or an engine.")
        if state is not None:
            engine = GameEngine.from_state(state)
        super().__init__()
        self._controller = GameController(engine, parent=self)
        self.setWindowTitle(APP_CONFIG.title)
        self.resize(APP_CONFIG.width, APP_CONFIG.height)
        self.setMinimumSize(
            APP_CONFIG.minimum_width, APP_CONFIG.minimum_height
        )

        central_area = QWidget(self)
        central_area.setObjectName("centralArea")
        layout = QVBoxLayout(central_area)
        layout.setContentsMargins(28, 20, 28, 16)
        layout.setSpacing(8)
        header = QHBoxLayout()
        title = QLabel("Ludo", central_area)
        title.setObjectName("title")
        header.addWidget(title)
        header.addStretch()
        self._roster_summary = QLabel(central_area)
        self._roster_summary.setObjectName("rosterSummary")
        header.addWidget(self._roster_summary)
        layout.addLayout(header)
        subtitle = QLabel("Chińczyk · Local multiplayer", central_area)
        subtitle.setObjectName("subtitle")
        layout.addWidget(subtitle)
        layout.addSpacing(4)

        body = QHBoxLayout()
        body.setSpacing(16)
        self.board_widget = BoardWidget(
            central_area, state=self.controller.state
        )
        body.addWidget(self.board_widget, stretch=1)
        self._sidebar = GameSidebar(central_area)
        sidebar_scroll = QScrollArea(central_area)
        sidebar_scroll.setObjectName("sidebarScroll")
        sidebar_scroll.setFixedWidth(270)
        sidebar_scroll.setWidgetResizable(True)
        sidebar_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        sidebar_scroll.setFrameShape(QFrame.Shape.NoFrame)
        sidebar_scroll.setWidget(self._sidebar)
        body.addWidget(sidebar_scroll)
        layout.addLayout(body, stretch=1)
        legend = QLabel(
            "★ Safe starts    ◯ Gold rings show available moves", central_area
        )
        legend.setObjectName("safeLegend")
        layout.addWidget(legend)
        self.setCentralWidget(central_area)

        self._victory_dialog = QMessageBox(self)
        self._victory_dialog.setObjectName("victoryDialog")
        self._victory_dialog.setWindowTitle("Game over")
        self._victory_dialog.setIcon(QMessageBox.Icon.Information)
        self._victory_dialog.setStandardButtons(QMessageBox.StandardButton.Ok)
        self._victory_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self._sidebar.roll_requested.connect(self.controller.roll_dice)
        self._sidebar.new_game_requested.connect(self._start_new_game)
        self.board_widget.pawn_clicked.connect(self.controller.move_pawn)
        self.controller.updated.connect(self._refresh_view)
        self.controller.game_won.connect(self._announce_winner)
        self._refresh_view()

    @property
    def controller(self) -> GameController:
        """Expose the action controller without exposing mutable game data.

        Returns:
            The controller owning this window's playable game.
        """
        return self._controller

    def set_state(self, state: GameState) -> None:
        """Load a snapshot as the playable game and refresh all views together.

        Args:
            state: The validated snapshot to load with a fresh default die.
        """
        self.controller.load_state(state)
        self._victory_dialog.close()

    @Slot()
    def _refresh_view(self) -> None:
        """Synchronize board, input permissions, sidebar, and action feedback."""
        controller = self.controller
        state = controller.state
        self.board_widget.set_state(state)
        self.board_widget.set_available_moves(controller.legal_moves)
        self.board_widget.set_selected_pawn(controller.selected_pawn)
        self._sidebar.set_turn(
            state,
            controller.last_roll,
            controller.last_roller,
            controller.message,
            controller.can_roll,
        )
        pawn_count = sum(len(player.pawns) for player in state.players)
        self._roster_summary.setText(
            f"{len(state.players)} players · {pawn_count} pawns"
        )
        self.statusBar().showMessage(controller.message)
        if state.winner is None:
            self._victory_dialog.close()

    @Slot()
    def _start_new_game(self) -> None:
        """Apply the roster selected in the sidebar and start a fresh game."""
        count = self._sidebar.selected_player_count
        if count == len(self.controller.state.players):
            self.controller.new_game()
        else:
            self.controller.new_game(tuple(PlayerColor)[:count])

    @Slot(str)
    def _announce_winner(self, color_name: str) -> None:
        """Show a non-blocking Qt victory notification for the winning move.

        Args:
            color_name: The winner's lowercase engine color name.
        """
        self._victory_dialog.setText(f"{color_name.title()} wins!")
        self._victory_dialog.setInformativeText(
            "All four pawns reached the finish.\n"
            "Choose New Game to play again."
        )
        self._victory_dialog.open()

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802 - Qt override.
        """Close the owned victory notification with its game window.

        Args:
            event: The Qt request to close this window.
        """
        self._victory_dialog.close()
        super().closeEvent(event)
