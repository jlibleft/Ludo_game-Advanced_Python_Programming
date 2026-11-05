"""Run GUI checks without a desktop display or third-party Qt test plugin."""

import os
from collections.abc import Iterator

import pytest

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication  # noqa: E402

from src.application import create_application  # noqa: E402


@pytest.fixture(scope="session")
def application() -> Iterator[QApplication]:
    """Share the single QApplication required by all widget tests."""
    app = create_application(["ludo-tests"])
    yield app
    app.closeAllWindows()
    app.processEvents()
