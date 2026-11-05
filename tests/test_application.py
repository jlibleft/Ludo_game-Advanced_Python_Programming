"""Check the desktop shell and real entry-point lifecycle."""

import os
from pathlib import Path
import subprocess
import sys

from PySide6.QtCore import QSize
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication, QSizePolicy
import pytest

from src.config import APP_CONFIG
from src.gui.main_window import MainWindow


def test_window_defaults_and_close(application: QApplication) -> None:
    window = MainWindow()
    try:
        assert window.windowTitle() == APP_CONFIG.title
        assert window.size() == QSize(1100, 800)
        assert window.minimumSize().width() < window.maximumSize().width()
        assert window.minimumSize().height() < window.maximumSize().height()
        layout = window.centralWidget().layout()
        assert layout.indexOf(window.board_widget) >= 0
        assert application.quitOnLastWindowClosed()
        window.show()
        application.processEvents()
        assert window.isVisible()
    finally:
        window.close()
        application.processEvents()
    assert not window.isVisible()


def test_board_resizes_and_paints(application: QApplication) -> None:
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
            # The white board surface and colored markers exercise QPainter.
            x = image.width() // 2
            y = image.height() // 2
            assert image.pixelColor(x, y - 80) == QColor("#ffffff")
            assert image.pixelColor(x - 39, y - 36) == QColor("#e76b72")
    finally:
        window.close()


@pytest.mark.parametrize("entry_point", ["script", "module"])
def test_entry_point_runs_event_loop_and_exits(entry_point: str) -> None:
    """Launch each documented entry point in a fresh Qt process."""
    runner = f"""
import runpy
from PySide6.QtCore import QTimer
import src.application

create_application = src.application.create_application

def create_with_shutdown(argv):
    app = create_application(argv)
    QTimer.singleShot(100, app.closeAllWindows)
    return app

src.application.create_application = create_with_shutdown
if {entry_point!r} == 'script':
    runpy.run_path('main.py', run_name='__main__')
else:
    runpy.run_module('src.main', run_name='__main__')
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
