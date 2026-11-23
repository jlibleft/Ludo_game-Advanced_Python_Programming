"""Load Qt only for GUI tests; domain tests need no PySide6 imports."""

import os
from collections.abc import Iterator
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def application() -> Iterator["QApplication"]:
    """Share one offscreen QApplication and clean up after GUI tests.

    Yields:
        The QApplication used by GUI tests for the current test
        session.
    """
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from Ludo.application import create_application

    app = create_application(["ludo-tests"])
    yield app
    app.closeAllWindows()
    app.processEvents()
