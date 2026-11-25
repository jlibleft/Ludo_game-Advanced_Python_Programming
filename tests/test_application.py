"""Check the desktop shell and real entry-point lifecycle."""

import os
import subprocess
import sys
from pathlib import Path

import pytest
from PySide6.QtCore import QSize
from PySide6.QtWidgets import QApplication, QSizePolicy

from Ludo.config import APP_CONFIG
from Ludo.gui.main_window import MainWindow


def test_window_defaults_and_close(application: QApplication) -> None:
    """Verify configured window defaults, visibility, and closing.

    Args:
        application: The shared QApplication fixture used to process
            GUI events.
    """
    window = MainWindow()
    try:
        assert window.windowTitle() == APP_CONFIG.title == "Ludo - Chińczyk"
        assert window.size() == QSize(1100, 800)
        assert window.minimumSize().width() < window.maximumSize().width()
        assert window.minimumSize().height() < window.maximumSize().height()
        assert window.centralWidget().isAncestorOf(window.board_widget)
        assert application.quitOnLastWindowClosed()
        window.show()
        application.processEvents()
        assert window.isVisible()
    finally:
        window.close()
        application.processEvents()
    assert not window.isVisible()


def test_board_resizes_and_paints(application: QApplication) -> None:
    """Verify that resizing expands the board and preserves its painting.

    Args:
        application: The shared QApplication fixture used to process
            GUI events.
    """
    window = MainWindow()
    try:
        window.show()
        application.processEvents()
        board = window.board_widget
        initial_size = board.size()
        window.resize(1300, 900)
        application.processEvents()
        assert board.width() > initial_size.width()
        assert board.height() > initial_size.height()
        assert board.sizePolicy().horizontalPolicy() == (
            QSizePolicy.Policy.Expanding
        )
        for size in (QSize(1300, 900), window.minimumSize()):
            window.resize(size)
            application.processEvents()
            image = board.grab().toImage()
            assert not image.isNull()
            assert len(board.pawn_placements) == 16
            assert board.board_geometry.side <= min(
                board.width(), board.height()
            )
    finally:
        window.close()


@pytest.mark.parametrize("entry_point", ["console", "module"])
def test_entry_point_runs_event_loop_and_exits(entry_point: str) -> None:
    """Verify startup and clean shutdown in a fresh Qt process.

    Args:
        entry_point: The parametrized launch mode: console or module.
    """
    runner = f"""
import runpy
from importlib.metadata import distribution
from PySide6.QtCore import QTimer
import Ludo.application

create_application = Ludo.application.create_application

def create_with_shutdown(argv):
    '''Create a Qt application with a timed window shutdown.

    Args:
        argv: Command-line arguments passed to the application factory.

    Returns:
        The QApplication scheduled to close its windows after 100 ms.
    '''
    app = create_application(argv)
    QTimer.singleShot(100, app.closeAllWindows)
    return app

Ludo.application.create_application = create_with_shutdown
if {entry_point!r} == 'console':
    command = next(
        item for item in distribution('ludo-desktop').entry_points
        if item.group == 'console_scripts' and item.name == 'ludo'
    )
    raise SystemExit(command.load()())
else:
    runpy.run_module('Ludo.main', run_name='__main__')
"""
    result = subprocess.run(
        [sys.executable, "-c", runner],
        cwd=Path(__file__).resolve().parents[1],
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Traceback" not in result.stderr
