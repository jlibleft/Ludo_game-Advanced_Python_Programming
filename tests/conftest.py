"""Load Qt only for GUI tests; domain tests need no PySide6 imports."""

import os
from collections.abc import Iterator
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def application() -> Iterator["QApplication"]:
    """Share the single QApplication required by all widget tests."""
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from src.application import create_application

    app = create_application(["ludo-tests"])
    yield app
    app.closeAllWindows()
    app.processEvents()
