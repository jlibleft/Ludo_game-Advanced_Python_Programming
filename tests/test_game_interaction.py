"""Exercise human button/mouse actions, controller safety, and whole games."""

import random
from collections.abc import Callable, Iterator, Sequence
from unittest.mock import Mock

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QSignalSpy, QTest
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
)

from Ludo.core.dice import Dice
from Ludo.core.game import GameEngine
from Ludo.core.pawn import Pawn
from Ludo.core.player import Player, PlayerColor
from Ludo.core.state import GameState
from Ludo.gui.main_window import MainWindow

_WindowFactory = Callable[[GameEngine], MainWindow]


def _game(
    rolls: Sequence[int],
    positions: tuple[tuple[int, ...], ...] | None = None,
    colors: tuple[PlayerColor, ...] = (PlayerColor.RED, PlayerColor.BLUE),
) -> GameEngine:
    """Create a validated GUI scenario with controlled dice results.

    Args:
        rolls: The sequence of results supplied by the injected random source.
        positions: Four pawn positions per player, or None for all bases.
        colors: The player colors in turn order.

    Returns:
        An engine initialized with the requested scenario and dice source.
    """
    source = Mock()
    source.randint.side_effect = rolls
    if positions is None:
        return GameEngine(colors, dice=Dice(random_source=source))
    players = tuple(
        Player(
            color,
            tuple(
                Pawn(pawn_id, progress) for pawn_id, progress in enumerate(row)
            ),
        )
        for color, row in zip(colors, positions, strict=True)
    )
    return GameEngine.from_state(
        GameState(players), dice=Dice(random_source=source)
    )


@pytest.fixture
def make_window(application: QApplication) -> Iterator[_WindowFactory]:
    """Open playable test windows and close any owned victory dialogs.

    Args:
        application: The shared offscreen QApplication fixture.

    Yields:
        A factory creating windows around injected game engines.
    """
    windows: list[MainWindow] = []

    def create(engine: GameEngine) -> MainWindow:
        """Show a playable window using a supplied engine.

        Args:
            engine: The controlled game for this window.

        Returns:
            The shown MainWindow after initial layout processing.
        """
        window = MainWindow(engine=engine)
        windows.append(window)
        window.show()
        application.processEvents()
        return window

    yield create
    for window in windows:
        window.close()
    application.processEvents()


def _button(window: MainWindow, name: str = "rollDiceButton") -> QPushButton:
    """Find a named game button through Qt's public object tree.

    Args:
        window: The game window to inspect.
        name: The Qt object name of the desired button.

    Returns:
        The existing QPushButton with that name.
    """
    button = window.findChild(QPushButton, name)
    assert button is not None
    return button


def _text(window: MainWindow, name: str) -> str:
    """Read a named label without depending on private widget attributes.

    Args:
        window: The game window to inspect.
        name: The label's Qt object name.

    Returns:
        The label's displayed text.
    """
    label = window.findChild(QLabel, name)
    assert label is not None
    return label.text()


def _roll(window: MainWindow) -> None:
    """Press Roll Dice with a real Qt mouse event and flush the repaint.

    Args:
        window: The playable window receiving the action.
    """
    QTest.mouseClick(_button(window), Qt.MouseButton.LeftButton)
    QApplication.processEvents()


def _click_pawn(
    window: MainWindow,
    color: PlayerColor,
    pawn_id: int,
    button: Qt.MouseButton = Qt.MouseButton.LeftButton,
) -> None:
    """Click a pawn at its current scaled position, including within stacks.

    Args:
        window: The game window receiving the action.
        color: The pawn owner's color.
        pawn_id: The owner's pawn ID to locate.
        button: The mouse button used for the selection attempt.
    """
    QApplication.processEvents()
    placement = next(
        pawn
        for pawn in window.board_widget.pawn_placements
        if pawn.color == color and pawn.pawn_id == pawn_id
    )
    QTest.mouseClick(
        window.board_widget,
        button,
        pos=QPoint(round(placement.center_x), round(placement.center_y)),
    )
    QApplication.processEvents()


def test_roll_move_bonus_and_turn_switch_stay_synchronized(
    make_window: _WindowFactory,
) -> None:
    """Verify controls, die ownership, highlighting, selection, and a bonus.

    Args:
        make_window: The fixture creating and cleaning up game windows.
    """
    engine = _game([6, 2])
    window = make_window(engine)
    controller = window.controller
    original = controller.state
    assert _button(window).isEnabled()
    assert _text(window, "diceResult") == "—"
    assert _text(window, "activePlayer") == "Red"
    _click_pawn(window, PlayerColor.RED, 0)
    assert controller.state is original
    _roll(window)
    assert controller.last_roll == 6
    assert _text(window, "diceResult") == "6"
    assert controller.state.pending_roll == 6
    assert window.board_widget.movable_pawn_ids == (0, 1, 2, 3)
    assert not _button(window).isEnabled()
    placement = window.board_widget.pawn_placements[0]
    image = window.board_widget.grab().toImage()
    ratio = image.devicePixelRatio()
    halo = image.pixelColor(
        round((placement.center_x + placement.radius * 1.12) * ratio),
        round(placement.center_y * ratio),
    )
    assert halo.red() > halo.blue() + 60
    assert halo.green() > halo.blue() + 40
    pending = controller.state
    _roll(window)
    assert controller.state is pending
    controller.roll_dice()
    assert controller.state is pending
    assert controller.last_roll == 6
    _click_pawn(window, PlayerColor.RED, 0)
    assert controller.state.players[0].pawns[0].progress == 0
    assert controller.state.active_player.color == PlayerColor.RED
    assert window.board_widget.selected_pawn == (PlayerColor.RED, 0)
    assert window.board_widget.movable_pawn_ids == ()
    assert "another roll" in _text(window, "gameStatus")
    assert _button(window).isEnabled()
    _roll(window)
    assert controller.last_roll == 2
    assert window.board_widget.movable_pawn_ids == (0,)
    _click_pawn(window, PlayerColor.RED, 0)
    assert controller.state.players[0].pawns[0].progress == 2
    assert controller.state.active_player.color == PlayerColor.BLUE
    assert _text(window, "activePlayer") == "Blue"
    assert _text(window, "diceOwner") == "Last roll · Red"
    assert window.board_widget.state is engine.state


def test_invalid_mouse_and_forged_controller_selections_preserve_the_turn(
    make_window: _WindowFactory,
) -> None:
    """Reject base, finished, opposing, right-clicked, and invalid pawn IDs.

    Args:
        make_window: The game-window factory fixture.
    """
    window = make_window(_game([3], ((57, 10, -1, -1), (10, -1, -1, -1))))
    _roll(window)
    before = window.controller.state
    clicks = QSignalSpy(window.board_widget.pawn_clicked)
    for color, pawn_id in (
        (PlayerColor.RED, 0),
        (PlayerColor.RED, 2),
        (PlayerColor.BLUE, 0),
    ):
        _click_pawn(window, color, pawn_id)
        assert window.controller.state is before
    _click_pawn(window, PlayerColor.RED, 1, Qt.MouseButton.RightButton)
    QTest.mouseClick(
        window.board_widget, Qt.MouseButton.LeftButton, pos=QPoint(0, 0)
    )
    assert clicks.count() == 0
    window.controller.move_pawn("blue", 1)
    window.controller.move_pawn("red", 4)
    assert window.controller.state is before
    assert window.board_widget.movable_pawn_ids == (1,)
    assert not _button(window).isEnabled()
    _click_pawn(window, PlayerColor.RED, 1)
    assert clicks.count() == 1
    assert window.controller.state.players[0].pawns[1].progress == 13


def test_unplayable_rolls_automatically_change_the_active_player(
    make_window: _WindowFactory,
) -> None:
    """Verify no-move feedback and next-player rolling without an End Turn action.

    Args:
        make_window: The game-window factory fixture.
    """
    window = make_window(_game([3, 6]))
    _roll(window)
    assert window.controller.state.active_player.color == PlayerColor.BLUE
    assert window.controller.last_roller == PlayerColor.RED
    assert "No legal moves" in _text(window, "gameStatus")
    assert _button(window).isEnabled()
    assert window.board_widget.movable_pawn_ids == ()
    _roll(window)
    assert window.board_widget.movable_pawn_ids == (0, 1, 2, 3)
    _click_pawn(window, PlayerColor.BLUE, 0)
    assert window.controller.state.players[1].pawns[0].progress == 0
    assert window.controller.state.active_player.color == PlayerColor.BLUE


def test_unplayable_six_keeps_the_extra_roll_without_enabling_pawn_clicks(
    make_window: _WindowFactory,
) -> None:
    """Verify a bonus survives when no home-stretch pawn can use a six.

    Args:
        make_window: The game-window factory fixture.
    """
    window = make_window(_game([6, 1], ((52, 53, 54, 55), (-1, -1, -1, -1))))
    _roll(window)
    before = window.controller.state
    assert before.active_player.color == PlayerColor.RED
    assert before.pending_roll is None
    assert "roll again" in _text(window, "gameStatus")
    assert _button(window).isEnabled()
    _click_pawn(window, PlayerColor.RED, 0)
    assert window.controller.state is before
    _roll(window)
    _click_pawn(window, PlayerColor.RED, 3)
    assert window.controller.state.players[0].pawns[3].progress == 56
    assert window.controller.state.active_player.color == PlayerColor.BLUE


@pytest.mark.parametrize(
    ("roll", "start", "active"),
    [
        (3, 11, PlayerColor.BLUE),
        (6, 8, PlayerColor.RED),
    ],
)
def test_capture_feedback_and_turn_outcome_come_from_the_engine(
    make_window: _WindowFactory,
    roll: int,
    start: int,
    active: PlayerColor,
) -> None:
    """Verify stacked captures repaint victims in base without extra bonuses.

    Args:
        make_window: The game-window factory fixture.
        roll: The parametrized capturing dice result.
        start: Initial moving-pawn progress, selected to land at 14.
        active: The expected next active color after this roll.
    """
    window = make_window(_game([roll], ((start, -1, -1, -1), (1, 1, -1, -1))))
    _roll(window)
    _click_pawn(window, PlayerColor.RED, 0)
    assert window.controller.state.players[0].pawns[0].progress == 14
    assert all(
        pawn.in_base for pawn in window.controller.state.players[1].pawns
    )
    assert window.controller.state.active_player.color == active
    assert "Captured 2 opponent pawns" in _text(window, "gameStatus")
    assert window.board_widget.state is window.controller.state
    assert _button(window).isEnabled()


def test_safe_stacks_allow_only_the_active_owners_pawn_to_be_selected(
    make_window: _WindowFactory,
) -> None:
    """Verify safe-square coexistence and accurate mixed-stack hit testing.

    Args:
        make_window: The game-window factory fixture.
    """
    window = make_window(_game([1, 6], ((12, -1, -1, -1), (0, 0, -1, -1))))
    _roll(window)
    _click_pawn(window, PlayerColor.RED, 0)
    state = window.controller.state
    assert state.players[0].pawns[0].progress == 13
    assert state.players[1].pawns[0].progress == 0
    assert state.players[1].pawns[1].progress == 0
    assert "Captured" not in window.controller.message
    _roll(window)
    pending = window.controller.state
    _click_pawn(window, PlayerColor.RED, 0)
    assert window.controller.state is pending
    _click_pawn(window, PlayerColor.BLUE, 1)
    assert window.controller.state.players[1].pawns[1].progress == 6
    assert window.controller.state.players[0].pawns[0].progress == 13


def test_overshooting_pawns_are_not_clickable_even_when_another_move_exists(
    make_window: _WindowFactory,
) -> None:
    """Verify exact-finish restrictions are reflected by the input filter.

    Args:
        make_window: The game-window factory fixture.
    """
    window = make_window(_game([2], ((56, 10, 57, 57), (-1, -1, -1, -1))))
    _roll(window)
    pending = window.controller.state
    assert window.board_widget.movable_pawn_ids == (1,)
    _click_pawn(window, PlayerColor.RED, 0)
    assert window.controller.state is pending
    _click_pawn(window, PlayerColor.RED, 1)
    assert window.controller.state.players[0].pawns[1].progress == 12


def test_victory_disables_play_notifies_once_and_new_game_resets_everything(
    make_window: _WindowFactory,
) -> None:
    """Verify the winning click, notification, terminal guards, and restart.

    Args:
        make_window: The game-window factory fixture.
    """
    window = make_window(_game([1], ((57, 57, 57, 56), (-1, -1, -1, -1))))
    wins = QSignalSpy(window.controller.game_won)
    _roll(window)
    _click_pawn(window, PlayerColor.RED, 3)
    assert window.controller.state.winner == PlayerColor.RED
    assert not _button(window).isEnabled()
    assert window.board_widget.movable_pawn_ids == ()
    assert _text(window, "activePlayer") == "Red wins!"
    assert _text(window, "redFinishCount") == "4/4 finished"
    assert wins.count() == 1
    dialog = window.findChild(QMessageBox, "victoryDialog")
    assert dialog is not None
    assert dialog.isVisible()
    assert dialog.text() == "Red wins!"
    finished = window.controller.state
    window.controller.roll_dice()
    window.controller.move_pawn("red", 3)
    assert window.controller.state is finished
    assert wins.count() == 1
    QTest.mouseClick(
        dialog.button(QMessageBox.StandardButton.Ok), Qt.MouseButton.LeftButton
    )
    QTest.mouseClick(
        _button(window, "newGameButton"), Qt.MouseButton.LeftButton
    )
    QApplication.processEvents()
    assert window.controller.state.winner is None
    assert all(
        pawn.in_base
        for player in window.controller.state.players
        for pawn in player.pawns
    )
    assert window.controller.state.active_player.color == PlayerColor.RED
    assert window.controller.last_roll is None
    assert window.board_widget.selected_pawn is None
    assert _text(window, "diceResult") == "—"
    assert _button(window).isEnabled()
    assert not dialog.isVisible()


@pytest.mark.parametrize("count", [2, 3, 4])
def test_new_game_applies_the_selected_roster_and_clears_a_pending_move(
    make_window: _WindowFactory,
    count: int,
) -> None:
    """Verify player selection persists through rolls and applies on restart.

    Args:
        make_window: The game-window factory fixture.
        count: The parametrized new-game player count.
    """
    window = make_window(_game([6], colors=tuple(PlayerColor)))
    selector = window.findChild(QComboBox, "playerCount")
    assert selector is not None
    selector.setCurrentIndex(selector.findData(count))
    _roll(window)
    assert selector.currentData() == count
    QTest.mouseClick(
        _button(window, "newGameButton"), Qt.MouseButton.LeftButton
    )
    assert len(window.controller.state.players) == count
    assert window.controller.state.pending_roll is None
    assert window.controller.last_roll is None
    assert window.board_widget.movable_pawn_ids == ()
    assert len(window.board_widget.pawn_placements) == count * 4


def test_rejected_controller_actions_do_not_discard_a_pending_roll(
    make_window: _WindowFactory,
) -> None:
    """Verify error handling retains both legal choices and the displayed die.

    Args:
        make_window: The game-window factory fixture.
    """
    window = make_window(_game([6]))
    _roll(window)
    pending = window.controller.state
    window.controller.new_game(("red",))
    assert window.controller.state is pending
    assert window.controller.last_roll == 6
    assert window.board_widget.movable_pawn_ids == (0, 1, 2, 3)
    assert not _button(window).isEnabled()


def test_hover_and_selection_use_fresh_coordinates_after_resizing(
    make_window: _WindowFactory,
) -> None:
    """Verify pointing feedback and hit testing after a viewport change.

    Args:
        make_window: The game-window factory fixture.
    """
    window = make_window(_game([6]))
    _roll(window)
    window.resize(1300, 900)
    QApplication.processEvents()
    placement = next(
        pawn
        for pawn in window.board_widget.pawn_placements
        if pawn.color == PlayerColor.RED and pawn.pawn_id == 2
    )
    QTest.mouseMove(
        window.board_widget,
        QPoint(round(placement.center_x), round(placement.center_y)),
    )
    QApplication.processEvents()
    assert (
        window.board_widget.cursor().shape()
        == Qt.CursorShape.PointingHandCursor
    )
    assert "red pawn 3" in window.board_widget.toolTip()
    QTest.mouseMove(window.board_widget, QPoint(2, 2))
    QApplication.processEvents()
    assert window.board_widget.cursor().shape() == Qt.CursorShape.ArrowCursor
    _click_pawn(window, PlayerColor.RED, 2)
    assert window.controller.state.players[0].pawns[2].progress == 0
    assert window.controller.state.players[0].pawns[0].in_base


def test_loaded_snapshots_replace_the_playable_engine_and_all_view_permissions(
    make_window: _WindowFactory,
) -> None:
    """Verify the earlier snapshot API cannot leave a stale input controller.

    Args:
        make_window: The game-window factory fixture.
    """
    original_engine = _game([6])
    window = make_window(original_engine)
    original = original_engine.state
    loaded = GameState(
        (Player(PlayerColor.GREEN), Player(PlayerColor.YELLOW)), pending_roll=6
    )
    window.set_state(loaded)
    assert window.controller.state is loaded
    assert window.board_widget.state is loaded
    assert _text(window, "activePlayer") == "Green"
    assert window.board_widget.movable_pawn_ids == (0, 1, 2, 3)
    assert not _button(window).isEnabled()
    _click_pawn(window, PlayerColor.GREEN, 3)
    assert window.controller.state.players[0].pawns[3].progress == 0
    assert original_engine.state is original
    QTest.mouseClick(
        _button(window, "newGameButton"), Qt.MouseButton.LeftButton
    )
    assert tuple(
        player.color for player in window.controller.state.players
    ) == (
        PlayerColor.GREEN,
        PlayerColor.YELLOW,
    )
    assert all(
        pawn.in_base
        for player in window.controller.state.players
        for pawn in player.pawns
    )


def test_opening_a_pending_turn_preserves_the_die_and_injected_random_source(
    make_window: _WindowFactory,
) -> None:
    """Continue an already rolled scenario through its move and bonus roll.

    Args:
        make_window: The game-window factory fixture.
    """
    source = Mock()
    source.randint.return_value = 1
    state = GameState(
        (Player(PlayerColor.GREEN), Player(PlayerColor.YELLOW)), pending_roll=6
    )
    engine = GameEngine.from_state(state, dice=Dice(random_source=source))
    window = make_window(engine)
    assert window.controller.state is state
    assert _text(window, "diceResult") == "6"
    assert _text(window, "diceOwner") == "Last roll · Green"
    assert window.board_widget.movable_pawn_ids == (0, 1, 2, 3)
    assert not _button(window).isEnabled()
    source.randint.assert_not_called()
    _click_pawn(window, PlayerColor.GREEN, 0)
    assert _button(window).isEnabled()
    _roll(window)
    assert window.controller.last_roll == 1
    source.randint.assert_called_once_with(1, 6)
    _click_pawn(window, PlayerColor.GREEN, 0)
    assert engine.state.players[0].pawns[0].progress == 1
    assert engine.state.active_player.color == PlayerColor.YELLOW


def test_invalid_dice_results_are_reported_without_breaking_the_controls(
    make_window: _WindowFactory,
) -> None:
    """Verify a faulty injected die cannot alter the game or trap its UI.

    Args:
        make_window: The game-window factory fixture.
    """
    window = make_window(_game([7, 6]))
    before = window.controller.state
    _roll(window)
    assert window.controller.state is before
    assert window.controller.last_roll is None
    assert _text(window, "diceResult") == "—"
    assert "integers" in window.controller.message
    assert _button(window).isEnabled()
    _roll(window)
    assert window.controller.last_roll == 6
    assert window.board_widget.movable_pawn_ids == (0, 1, 2, 3)


def test_small_window_keeps_roll_and_new_game_reachable_by_scrolling(
    make_window: _WindowFactory,
) -> None:
    """Verify the sidebar remains usable at the existing minimum window size.

    Args:
        make_window: The game-window factory fixture.
    """
    window = make_window(_game([6]))
    window.resize(window.minimumSize())
    QApplication.processEvents()
    scroll = window.findChild(QScrollArea, "sidebarScroll")
    assert scroll is not None
    for name in ("newGameButton", "rollDiceButton"):
        button = _button(window, name)
        scroll.ensureWidgetVisible(button)
        QApplication.processEvents()
        center = button.mapTo(scroll.viewport(), button.rect().center())
        assert scroll.viewport().rect().contains(center)
        QTest.mouseClick(button, Qt.MouseButton.LeftButton)
    assert window.controller.last_roll == 6


def test_two_local_players_can_complete_a_game_using_only_buttons_and_pawn_clicks(
    make_window: _WindowFactory,
) -> None:
    """Play from all bases to victory through the same inputs as two humans.

    Args:
        make_window: The game-window factory fixture.
    """
    window = make_window(
        GameEngine(dice=Dice(random_source=random.Random(42)))
    )
    selector = window.findChild(QComboBox, "playerCount")
    assert selector is not None
    selector.setCurrentIndex(selector.findData(2))
    QTest.mouseClick(
        _button(window, "newGameButton"), Qt.MouseButton.LeftButton
    )
    played_colors = set()
    for _ in range(2000):
        assert _button(window).isEnabled()
        color = window.controller.state.active_player.color
        played_colors.add(color)
        _roll(window)
        legal = window.controller.legal_moves
        if legal:
            assert not _button(window).isEnabled()
            pawn_id = max(
                legal,
                key=lambda item: (
                    window.controller.state.active_player.pawns[item].progress
                ),
            )
            _click_pawn(window, color, pawn_id)
        assert window.board_widget.state is window.controller.state
        if window.controller.state.winner is not None:
            break
    else:
        pytest.fail(
            "The seeded two-player GUI game did not finish in 2000 rolls."
        )
    assert played_colors == {PlayerColor.RED, PlayerColor.BLUE}
    assert window.controller.state.active_player.has_won
    assert not _button(window).isEnabled()
    dialog = window.findChild(QMessageBox, "victoryDialog")
    assert dialog is not None
    assert dialog.isVisible()
