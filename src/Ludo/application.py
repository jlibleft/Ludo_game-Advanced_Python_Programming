"""Qt initialization shared by desktop entry points."""

from collections.abc import Sequence

from PySide6.QtWidgets import QApplication

from Ludo.config import APP_CONFIG
from Ludo.gui.styles import APPLICATION_STYLE

__all__ = ("create_application",)


def create_application(argv: Sequence[str]) -> QApplication:
    """Create and configure the process's single QApplication.

    Args:
        argv: Command-line arguments passed to Qt, including the
            program name.

    Returns:
        The configured QApplication, ready for widget construction.
    """
    application = QApplication(list(argv))
    application.setApplicationName(APP_CONFIG.title)
    application.setOrganizationName("Ludo Desktop")
    application.setStyle("Fusion")
    application.setStyleSheet(APPLICATION_STYLE)
    application.setQuitOnLastWindowClosed(True)
    return application
