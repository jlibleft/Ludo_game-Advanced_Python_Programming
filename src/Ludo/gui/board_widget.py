"""QPainter surface reserved for future board rendering."""

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget


class BoardWidget(QWidget):
    """Draw a responsive placeholder without board geometry or game rules."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the expanding, accessible board drawing surface.

        Args:
            parent: The owning Qt widget, or None for a standalone widget.
        """
        super().__init__(parent)
        self.setObjectName("boardArea")
        self.setAccessibleName("Ludo game board area")
        self.setAccessibleDescription("Reserved for the Ludo game board.")
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

    def sizeHint(self) -> QSize:
        """Suggest a square size to the parent layout.

        Returns:
            A QSize of 640 by 640 pixels; the layout can choose another
            size.
        """
        return QSize(640, 640)

    def paintEvent(self, event: QPaintEvent) -> None:
        """Paint a centered square placeholder and its labels.

        Args:
            event: The Qt paint event requesting a redraw. The entire
                placeholder is repainted regardless of the event region.
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        side = max(0.0, min(self.width(), self.height()) - 8.0)
        board_rect = QRectF(
            (self.width() - side) / 2,
            (self.height() - side) / 2,
            side,
            side,
        )
        painter.setPen(QPen(QColor("#dfe5ee"), 1.0))
        painter.setBrush(QColor("#ffffff"))
        painter.drawRoundedRect(board_rect, 24, 24)

        center = board_rect.center()
        painter.setPen(Qt.PenStyle.NoPen)
        for index, color in enumerate(
            ("#e76b72", "#e5b84f", "#56ab8a", "#628bdd")
        ):
            painter.setBrush(QColor(color))
            painter.drawEllipse(
                QRectF(center.x() - 47 + index * 26, center.y() - 44, 16, 16)
            )

        font = QFont(self.font())
        font.setPointSize(18)
        font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(font)
        painter.setPen(QColor("#24334b"))
        painter.drawText(
            QRectF(board_rect.left(), center.y() - 8, side, 40),
            Qt.AlignmentFlag.AlignCenter,
            "A place to play",
        )
        font.setPointSize(11)
        font.setWeight(QFont.Weight.Normal)
        painter.setFont(font)
        painter.setPen(QColor("#66758a"))
        painter.drawText(
            QRectF(board_rect.left(), center.y() + 32, side, 32),
            Qt.AlignmentFlag.AlignCenter,
            "The Ludo board will appear here.",
        )
        painter.end()
