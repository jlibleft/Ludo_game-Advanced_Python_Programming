"""Check real QPainter output, state updates, and resizable board integration."""

import random
from dataclasses import replace

import pytest
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication

from Ludo.core.dice import Dice
from Ludo.core.game import GameEngine
from Ludo.core.pawn import Pawn
from Ludo.core.player import Player, PlayerColor
from Ludo.core.state import GameState
from Ludo.gui.board_geometry import Point
from Ludo.gui.board_widget import BoardWidget
from Ludo.gui.main_window import MainWindow
from Ludo.gui.styles import PLAYER_COLORS, PLAYER_TINTS


def _pixel_color(image: QImage, point: Point) -> QColor:
    """Sample a logical widget coordinate from a possibly high-DPI image.

    Args:
        image: The widget's captured image, preserving its pixel ratio.
        point: The logical (horizontal, vertical) widget coordinate.

    Returns:
        The color of the corresponding physical image pixel.
    """
    ratio = image.devicePixelRatio()
    return image.pixelColor(round(point[0] * ratio), round(point[1] * ratio))


@pytest.mark.parametrize(
    ("width", "height"),
    [
        (800, 800),
        (1200, 500),
        (400, 900),
        (300, 300),
    ],
)
def test_every_route_cell_and_base_is_painted_at_each_viewport_size(
    application: QApplication, width: int, height: int
) -> None:
    """Verify actual pixels across all shared cells, home lanes, and bases.

    Args:
        application: The shared offscreen QApplication fixture.
        width: The parametrized board widget width.
        height: The parametrized board widget height.
    """
    board = BoardWidget()
    try:
        board.resize(width, height)
        board.show()
        application.processEvents()
        image = board.grab().toImage()
        assert not image.isNull()
        geometry = board.board_geometry
        assert len(board.pawn_placements) == 16
        for square, (row, column) in enumerate(geometry.SHARED_TRACK):
            color = geometry.START_COLORS.get(square)
            expected = PLAYER_COLORS[color] if color else "#ffffff"
            point = geometry.point(column + 0.2, row + 0.2)
            assert _pixel_color(image, point) == QColor(expected)
        for color, cells in geometry.HOME_STRETCHES.items():
            for row, column in cells:
                point = geometry.point(column + 0.2, row + 0.2)
                assert _pixel_color(image, point) == QColor(
                    PLAYER_TINTS[color]
                )
            row, column = geometry.BASE_ORIGINS[color]
            point = geometry.point(column + 0.65, row + 0.65)
            assert _pixel_color(image, point) == QColor(PLAYER_COLORS[color])
    finally:
        board.close()


def test_engine_moves_update_the_painted_pawn_without_changing_old_snapshots(
    application: QApplication,
) -> None:
    """Verify that a real engine move changes token placement and pixels.

    Args:
        application: The shared offscreen QApplication fixture.
    """
    engine = GameEngine(dice=Dice(random_source=random.Random(42)))
    board = BoardWidget(state=engine.state)
    try:
        board.resize(800, 800)
        board.show()
        application.processEvents()
        original = board.state
        original_pawn = next(
            pawn
            for pawn in board.pawn_placements
            if pawn.color == PlayerColor.RED and pawn.pawn_id == 0
        )
        sample = (
            round(original_pawn.center_x + original_pawn.radius * 0.65),
            round(original_pawn.center_y + original_pawn.radius * 0.2),
        )
        before = _pixel_color(board.grab().toImage(), sample)
        assert before.red() > before.green() + 30
        assert engine.roll_dice() == 6
        engine.move_pawn(0)
        board.set_state(engine.state)
        application.processEvents()
        moved_pawn = next(
            pawn
            for pawn in board.pawn_placements
            if pawn.color == PlayerColor.RED and pawn.pawn_id == 0
        )
        assert (moved_pawn.center_x, moved_pawn.center_y) == (
            board.board_geometry.cell_center(
                board.board_geometry.SHARED_TRACK[0]
            )
        )
        assert _pixel_color(board.grab().toImage(), sample) == QColor(
            "#ffffff"
        )
        assert original.players[0].pawns[0].in_base
        assert board.state is engine.state
    finally:
        board.close()


def test_board_displays_base_track_home_and_finish_from_one_snapshot(
    application: QApplication,
) -> None:
    """Verify mapping of every logical pawn region in a valid two-player game.

    Args:
        application: The shared offscreen QApplication fixture.
    """
    red = Player(
        PlayerColor.RED,
        (
            Pawn(0, 0),
            Pawn(1, 52),
            Pawn(2, 57),
            Pawn(3),
        ),
    )
    state = GameState((red, Player(PlayerColor.BLUE)))
    window = MainWindow(state)
    try:
        window.show()
        application.processEvents()
        board = window.board_widget
        assert board.state is state
        assert len(board.pawn_placements) == 8
        for pawn in red.pawns:
            placement = next(
                item
                for item in board.pawn_placements
                if item.color == red.color and item.pawn_id == pawn.id
            )
            assert (placement.center_x, placement.center_y) == (
                board.board_geometry.pawn_center(red, pawn)
            )
        assert not board.grab().isNull()
        assert "1 in base, 1 finished" in board.accessibleDescription()
    finally:
        window.close()


def test_set_state_rejects_invalid_data_without_losing_the_snapshot(
    application: QApplication,
) -> None:
    """Verify atomic state replacement and a repaint after a valid update.

    Args:
        application: The shared offscreen QApplication fixture.
    """
    board = BoardWidget()
    original = board.state
    with pytest.raises(TypeError, match="GameState"):
        board.set_state(None)
    assert board.state is original
    blue_turn = replace(original, active_player_index=1)
    board.set_state(blue_turn)
    application.processEvents()
    assert board.state is blue_turn
    board.close()
