"""Qt initialization shared by desktop entry points."""

from collections.abc import Sequence

from PySide6.QtWidgets import QApplication

from src.config import APP_CONFIG
from src.gui.styles import APPLICATION_STYLE


def create_application(argv: Sequence[str]) -> QApplication:
    """Create and configure the process's single QApplication instance."""
    application = QApplication(list(argv))
    application.setApplicationName(APP_CONFIG.title)
    application.setOrganizationName("Ludo Desktop")
    application.setStyle("Fusion")
    application.setStyleSheet(APPLICATION_STYLE)
    application.setQuitOnLastWindowClosed(True)
    return application
