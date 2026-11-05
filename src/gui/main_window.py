"""Main desktop window and layout."""

from PySide6.QtWidgets import QLabel, QMainWindow, QVBoxLayout, QWidget

from src.config import APP_CONFIG
from src.gui.board_widget import BoardWidget


class MainWindow(QMainWindow):
    """Application shell with a dedicated, expanding board area."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_CONFIG.title)
        self.resize(APP_CONFIG.width, APP_CONFIG.height)
        self.setMinimumSize(
            APP_CONFIG.minimum_width, APP_CONFIG.minimum_height
        )

        central_area = QWidget(self)
        central_area.setObjectName("centralArea")
        layout = QVBoxLayout(central_area)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(8)

        title = QLabel("Ludo Game", central_area)
        title.setObjectName("title")
        layout.addWidget(title)

        subtitle = QLabel("The classic board game", central_area)
        subtitle.setObjectName("subtitle")
        layout.addWidget(subtitle)
        layout.addSpacing(16)

        self.board_widget = BoardWidget(central_area)
        layout.addWidget(self.board_widget, stretch=1)
        self.setCentralWidget(central_area)

        self.statusBar().showMessage("Ready")
