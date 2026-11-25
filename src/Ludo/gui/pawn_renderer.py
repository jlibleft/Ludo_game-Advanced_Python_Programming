"""QPainter token artwork, separate from placement and Ludo rules."""

from collections.abc import Sequence

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QRadialGradient

from Ludo.core.player import PlayerColor
from Ludo.gui.board_geometry import PawnPlacement
from Ludo.gui.styles import PLAYER_COLORS

__all__ = ("PawnRenderer",)


class PawnRenderer:
    """Draw colored, numbered tokens at already-computed pixel positions."""

    def paint(
        self,
        painter: QPainter,
        placements: Sequence[PawnPlacement],
        *,
        movable_color: PlayerColor | None = None,
        movable_pawns: frozenset[int] = frozenset(),
        selected_pawn: tuple[PlayerColor, int] | None = None,
    ) -> None:
        """Draw each token without changing the game state.

        Args:
            painter: The active painter for the board widget.
            placements: Pawn identities, centers, and radii in widget pixels.
            movable_color: The active color whose legal pawns are highlighted.
            movable_pawns: Legal active-player pawn IDs.
            selected_pawn: The last accepted pawn identity, or None.
        """
        painter.save()
        for placement in placements:
            selected = (placement.color, placement.pawn_id) == selected_pawn
            movable = (
                placement.color == movable_color
                and placement.pawn_id in movable_pawns
            )
            if movable or selected:
                self._paint_highlight(painter, placement, selected)
            self._paint_pawn(painter, placement)
        painter.restore()

    def _paint_highlight(
        self, painter: QPainter, placement: PawnPlacement, selected: bool
    ) -> None:
        """Draw an available-move halo or a last-selection outline.

        Args:
            painter: The board's active painter.
            placement: The pawn circle to emphasize.
            selected: True for the last accepted selection, otherwise a move.
        """
        radius = placement.radius * 1.23
        painter.setBrush(QColor("#edf1f8") if selected else QColor("#fff0b5"))
        painter.setPen(
            QPen(
                QColor("#24334b") if selected else QColor("#ac7b16"),
                max(1.1, placement.radius * 0.12),
            )
        )
        painter.drawEllipse(
            QPointF(placement.center_x, placement.center_y), radius, radius
        )

    def _paint_pawn(self, painter: QPainter, placement: PawnPlacement) -> None:
        """Paint a token with a soft shadow, colored dome, and pawn number.

        Args:
            painter: The board's active painter.
            placement: The visible circle and identity of this pawn.
        """
        radius = placement.radius
        center = QPointF(placement.center_x, placement.center_y)
        circle = QRectF(
            center.x() - radius, center.y() - radius, 2 * radius, 2 * radius
        )
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(25, 40, 65, 28))
        painter.drawEllipse(circle.translated(0, radius * 0.2))

        color = QColor(PLAYER_COLORS[placement.color])
        gradient = QRadialGradient(
            center - QPointF(radius * 0.25, radius * 0.3), radius * 1.8
        )
        gradient.setColorAt(0, color.lighter(125))
        gradient.setColorAt(1, color.darker(115))
        painter.setBrush(gradient)
        painter.setPen(QPen(QColor("#ffffff"), max(0.7, radius * 0.13)))
        painter.drawEllipse(circle)

        if radius >= 4.5:
            font = QFont(painter.font())
            font.setPixelSize(max(6, round(radius * 1.05)))
            font.setWeight(QFont.Weight.Bold)
            painter.setFont(font)
            label_color = (
                "#594219"
                if placement.color == PlayerColor.YELLOW
                else "#ffffff"
            )
            painter.setPen(QColor(label_color))
            painter.drawText(
                circle,
                Qt.AlignmentFlag.AlignCenter,
                str(placement.pawn_id + 1),
            )
