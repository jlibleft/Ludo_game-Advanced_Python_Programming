"""Shared visual styling for the desktop interface."""

from collections.abc import Mapping
from types import MappingProxyType

from Ludo.core.player import PlayerColor

__all__ = ("APPLICATION_STYLE", "PLAYER_COLORS", "PLAYER_TINTS")

PLAYER_COLORS: Mapping[PlayerColor, str] = MappingProxyType(
    {
        PlayerColor.RED: "#dc626b",
        PlayerColor.BLUE: "#5288ce",
        PlayerColor.GREEN: "#329c84",
        PlayerColor.YELLOW: "#e7b547",
    }
)

PLAYER_TINTS: Mapping[PlayerColor, str] = MappingProxyType(
    {
        PlayerColor.RED: "#fbe9ec",
        PlayerColor.BLUE: "#e8f0fc",
        PlayerColor.GREEN: "#e3f3ee",
        PlayerColor.YELLOW: "#fff4d8",
    }
)

APPLICATION_STYLE = """
QWidget {
    color: #24334b;
    font-family: "Segoe UI", "DejaVu Sans", sans-serif;
    font-size: 14px;
}
QMainWindow, QWidget#centralArea {
    background-color: #f4f6fa;
}
QLabel#title {
    font-size: 30px;
    font-weight: 700;
}
QLabel#subtitle {
    color: #66758a;
    font-size: 14px;
}
QLabel#rosterSummary {
    background-color: #e9eef6;
    border-radius: 12px;
    color: #5b6b82;
    padding: 8px 14px;
    font-size: 12px;
}
QLabel[role="legend"] {
    font-size: 12px;
    font-weight: 600;
}
QLabel#safeLegend {
    color: #718096;
    font-size: 12px;
}
QStatusBar {
    background-color: #ffffff;
    border-top: 1px solid #e2e7ef;
    color: #66758a;
}
QFrame#gameSidebar {
    background-color: #ffffff;
    border: 1px solid #dfe6ef;
    border-radius: 18px;
}
QScrollArea#sidebarScroll {
    background-color: transparent;
    border: none;
}
QLabel[role="sectionHeading"] {
    color: #718096;
    font-size: 11px;
    font-weight: 700;
}
QLabel[role="muted"] {
    color: #718096;
    font-size: 12px;
}
QLabel#activePlayer {
    font-size: 24px;
    font-weight: 700;
}
QLabel#diceResult {
    background-color: #f8faff;
    border: 1px solid #dfe6ef;
    border-radius: 14px;
    font-size: 44px;
    font-weight: 700;
    min-height: 80px;
}
QLabel#gameStatus {
    color: #51627a;
    font-size: 13px;
}
QPushButton {
    border-radius: 10px;
    padding: 10px;
    font-weight: 600;
}
QPushButton#rollDiceButton {
    background-color: #243b5c;
    border: 1px solid #243b5c;
    color: #ffffff;
}
QPushButton#rollDiceButton:hover {
    background-color: #35547b;
}
QPushButton#rollDiceButton:pressed {
    background-color: #172943;
}
QPushButton#rollDiceButton:disabled {
    background-color: #e3e8f0;
    border-color: #e3e8f0;
    color: #7d8aa0;
}
QPushButton#newGameButton {
    background-color: #ffffff;
    border: 1px solid #cbd6e5;
}
QPushButton#newGameButton:hover {
    background-color: #eef3fa;
}
QComboBox {
    background-color: #f8faff;
    border: 1px solid #d7e0ec;
    border-radius: 8px;
    padding: 7px;
}
QScrollBar:vertical {
    background: transparent;
    width: 8px;
    margin: 2px;
}
QScrollBar::handle:vertical {
    background: #c3cedd;
    border-radius: 3px;
    min-height: 20px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
"""

APPLICATION_STYLE += "\n".join(
    f'QLabel[playerColor="{color.value}"] {{ color: {value}; }}'
    for color, value in PLAYER_COLORS.items()
)
