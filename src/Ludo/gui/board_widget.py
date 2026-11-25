"""Responsive QPainter board driven by immutable Ludo state snapshots."""

from math import cos, pi, sin

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QMouseEvent,
    QPainter,
    QPaintEvent,
    QPen,
    QPolygonF,
)
from PySide6.QtWidgets import QSizePolicy, QWidget

from Ludo.core.game import GameEngine
from Ludo.core.player import PlayerColor
from Ludo.core.state import GameState
from Ludo.gui.board_geometry import BoardGeometry, GridCell, PawnPlacement
from Ludo.gui.pawn_renderer import PawnRenderer
from Ludo.gui.styles import PLAYER_COLORS, PLAYER_TINTS

__all__ = ("BoardWidget",)


def _grid_rect(
    geometry: BoardGeometry,
    column: float,
    row: float,
    width: float,
    height: float,
) -> QRectF:
    """Convert a rectangle measured in grid units into widget pixels.

    Args:
        geometry: The current viewport transform.
        column: Left edge in grid units.
        row: Top edge in grid units.
        width: Rectangle width in grid units.
        height: Rectangle height in grid units.

    Returns:
        The scaled rectangle in widget coordinates.
    """
    return QRectF(
        *geometry.point(column, row),
        width * geometry.cell_size,
        height * geometry.cell_size,
    )


def _star(center: QPointF, radius: float) -> QPolygonF:
    """Construct the five-point marker used on safe starting squares.

    Args:
        center: Pixel center of the marker.
        radius: Outer marker radius in pixels.

    Returns:
        The ten alternating outer and inner vertices of the star.
    """
    vertices = []
    for point_index in range(10):
        angle = -pi / 2 + point_index * pi / 5
        point_radius = radius if point_index % 2 == 0 else radius * 0.45
        direction = QPointF(cos(angle), sin(angle))
        vertices.append(center + direction * point_radius)
    return QPolygonF(vertices)


class BoardWidget(QWidget):
    """Display the board and state without making game-rule decisions."""

    pawn_clicked = Signal(str, int)

    def __init__(
        self, parent: QWidget | None = None, *, state: GameState | None = None
    ) -> None:
        """Initialize the board surface and its initial snapshot.

        Args:
            parent: The owning Qt widget, or None for a standalone widget.
            state: The snapshot to render; defaults to a new four-player game.
        """
        super().__init__(parent)
        self.setObjectName("boardArea")
        self.setAccessibleName("Ludo game board")
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self._pawn_renderer = PawnRenderer()
        self._movable_pawn_ids: frozenset[int] = frozenset()
        self._selected_pawn: tuple[PlayerColor, int] | None = None
        self.setMouseTracking(True)
        self.set_state(state if state is not None else GameEngine().state)

    @property
    def state(self) -> GameState:
        """Expose the snapshot currently displayed by the board.

        Returns:
            The immutable GameState used for rendering.
        """
        return self._state

    @property
    def board_geometry(self) -> BoardGeometry:
        """Build the transform for the widget's current dimensions.

        Returns:
            The centered square viewport and logical coordinate mapping.
        """
        return BoardGeometry(self.width(), self.height())

    @property
    def pawn_placements(self) -> tuple[PawnPlacement, ...]:
        """Expose visible pawn circles for inspection and mouse hit testing.

        Returns:
            All rendered pawn identities, centers, and radii in pixels.
        """
        return self.board_geometry.pawn_placements(self._state)

    @property
    def movable_pawn_ids(self) -> tuple[int, ...]:
        """Read the active player's currently highlighted pawn IDs.

        Returns:
            A sorted tuple of pawn IDs supplied by the controller.
        """
        return tuple(sorted(self._movable_pawn_ids))

    @property
    def selected_pawn(self) -> tuple[PlayerColor, int] | None:
        """Read the pawn marked as the most recently accepted selection.

        Returns:
            The selected owning color and pawn ID, or None.
        """
        return self._selected_pawn

    def set_state(self, state: GameState) -> None:
        """Display a validated snapshot and request a repaint.

        Args:
            state: The immutable GameState to display.
        """
        if not isinstance(state, GameState):
            raise TypeError("The board requires a GameState snapshot.")
        self._state = state
        self._movable_pawn_ids = frozenset()
        self._selected_pawn = None
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.setToolTip("")
        description = "; ".join(
            f"{player.color.value.title()}: "
            f"{sum(pawn.in_base for pawn in player.pawns)} in base, "
            f"{sum(pawn.finished for pawn in player.pawns)} finished"
            for player in state.players
        )
        self.setAccessibleDescription(f"Ludo board. {description}.")
        self.update()

    def set_available_moves(self, pawn_ids: tuple[int, ...]) -> None:
        """Highlight controller-supplied legal choices for the active player.

        Args:
            pawn_ids: The legal pawn IDs returned by the game engine.
        """
        self._movable_pawn_ids = frozenset(pawn_ids)
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.setToolTip("")
        self.update()

    def set_selected_pawn(self, pawn: tuple[PlayerColor, int] | None) -> None:
        """Mark the most recently accepted pawn selection after its move.

        Args:
            pawn: The owning color and pawn ID, or None to clear selection.
        """
        self._selected_pawn = pawn
        self.update()

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt override.
        """Emit a selection only for a left-clicked highlighted pawn.

        Args:
            event: The Qt mouse event in logical widget coordinates.
        """
        if event.button() == Qt.MouseButton.LeftButton:
            pawn = self._movable_pawn_at(
                event.position().x(), event.position().y()
            )
            if pawn is not None:
                self.pawn_clicked.emit(pawn.color.value, pawn.pawn_id)
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt override.
        """Show a pointer and identifying tooltip over legal pawn choices.

        Args:
            event: The Qt mouse movement event.
        """
        pawn = self._movable_pawn_at(
            event.position().x(), event.position().y()
        )
        self.setCursor(
            Qt.CursorShape.PointingHandCursor
            if pawn
            else Qt.CursorShape.ArrowCursor
        )
        self.setToolTip(
            f"Move {pawn.color.value} pawn {pawn.pawn_id + 1}." if pawn else ""
        )
        super().mouseMoveEvent(event)

    def _movable_pawn_at(
        self, position_x: float, position_y: float
    ) -> PawnPlacement | None:
        """Hit-test the current viewport against active legal pawns only.

        Args:
            position_x: Horizontal logical widget coordinate.
            position_y: Vertical logical widget coordinate.

        Returns:
            The eligible pawn under the point, or None.
        """
        for pawn in reversed(self.pawn_placements):
            if (
                pawn.color == self._state.active_player.color
                and pawn.pawn_id in self._movable_pawn_ids
                and pawn.contains(position_x, position_y)
            ):
                return pawn
        return None

    def sizeHint(self) -> QSize:  # noqa: N802 - Qt override name.
        """Suggest a square size to the parent layout.

        Returns:
            A preferred board area of 640 by 640 pixels.
        """
        return QSize(640, 640)

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802 - Qt override.
        """Render the complete board using the current viewport and snapshot.

        Args:
            event: The Qt paint request; the entire board is redrawn.
        """
        geometry = self.board_geometry
        if not geometry.side:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        try:
            self._paint_surface(painter, geometry)
            for color in PlayerColor:
                self._paint_base(painter, geometry, color)
            self._paint_routes(painter, geometry)
            self._paint_finish(painter, geometry)
            self._pawn_renderer.paint(
                painter,
                geometry.pawn_placements(self._state),
                movable_color=self._state.active_player.color,
                movable_pawns=self._movable_pawn_ids,
                selected_pawn=self._selected_pawn,
            )
        finally:
            painter.end()

    def _paint_surface(
        self, painter: QPainter, geometry: BoardGeometry
    ) -> None:
        """Draw the board card with a soft shadow and a clean outer border.

        Args:
            painter: The widget's active painter.
            geometry: The current board transform.
        """
        surface = _grid_rect(
            geometry, 0, 0, geometry.GRID_SIZE, geometry.GRID_SIZE
        )
        radius = geometry.cell_size * 0.4
        painter.setPen(Qt.PenStyle.NoPen)
        for expansion, opacity in ((5.0, 5), (3.0, 8), (1.0, 12)):
            painter.setBrush(QColor(30, 45, 70, opacity))
            shadow = surface.adjusted(
                -expansion, -expansion, expansion, expansion
            )
            painter.drawRoundedRect(shadow.translated(0, 4), radius, radius)
        painter.setBrush(QColor("#ffffff"))
        painter.setPen(QPen(QColor("#dce3ed"), 1))
        painter.drawRoundedRect(surface, radius, radius)

    def _paint_base(
        self, painter: QPainter, geometry: BoardGeometry, color: PlayerColor
    ) -> None:
        """Draw a colored home base and four empty pawn stations.

        Args:
            painter: The active painter.
            geometry: The board transform and base coordinates.
            color: The color identifying this home base.
        """
        row, column = geometry.BASE_ORIGINS[color]
        scale = geometry.cell_size
        base_color = QColor(PLAYER_COLORS[color])
        frame = _grid_rect(geometry, column + 0.16, row + 0.16, 5.68, 5.68)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(base_color)
        painter.drawRoundedRect(frame, scale * 0.38, scale * 0.38)
        painter.setBrush(QColor(PLAYER_TINTS[color]))
        inset = _grid_rect(geometry, column + 0.85, row + 1.3, 4.3, 4.05)
        painter.drawRoundedRect(inset, scale * 0.3, scale * 0.3)

        font = QFont(self.font())
        font.setPixelSize(max(7, round(scale * 0.36)))
        font.setWeight(QFont.Weight.Bold)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, scale * 0.045)
        painter.setFont(font)
        painter.setPen(
            QColor("#594219" if color == PlayerColor.YELLOW else "#ffffff")
        )
        painter.drawText(
            _grid_rect(geometry, column + 0.5, row + 0.3, 5, 0.8),
            Qt.AlignmentFlag.AlignCenter,
            color.value.upper(),
        )
        painter.setBrush(QColor("#ffffff"))
        station_border = QColor(base_color)
        station_border.setAlpha(90)
        painter.setPen(QPen(station_border, max(0.8, scale * 0.035)))
        for station_column, station_row in geometry.BASE_SLOTS:
            center = QPointF(
                *geometry.point(column + station_column, row + station_row)
            )
            painter.drawEllipse(center, scale * 0.64, scale * 0.64)

    def _paint_routes(
        self, painter: QPainter, geometry: BoardGeometry
    ) -> None:
        """Draw all shared cells, safe starts, and private home stretches.

        Args:
            painter: The active painter.
            geometry: The centralized route coordinates and transform.
        """
        scale = geometry.cell_size
        for square, cell in enumerate(geometry.SHARED_TRACK):
            color = geometry.START_COLORS.get(square)
            fill = QColor(PLAYER_COLORS[color]) if color else QColor("#ffffff")
            self._paint_cell(painter, geometry, cell, fill, QColor("#dce3ed"))
            if color is not None:
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor("#ffffff"))
                painter.drawPolygon(
                    _star(QPointF(*geometry.cell_center(cell)), scale * 0.28)
                )
        for color, cells in geometry.HOME_STRETCHES.items():
            shade = QColor(PLAYER_COLORS[color])
            direction_x, direction_y = geometry.HOME_DIRECTIONS[color]
            for cell in cells:
                self._paint_cell(
                    painter,
                    geometry,
                    cell,
                    QColor(PLAYER_TINTS[color]),
                    QColor(PLAYER_TINTS[color]).darker(105),
                )
                center = QPointF(*geometry.cell_center(cell))
                direction = QPointF(direction_x, direction_y)
                normal = QPointF(-direction_y, direction_x)
                tip = center + direction * (scale * 0.12)
                tail = center - direction * (scale * 0.08)
                painter.setPen(
                    QPen(shade.lighter(115), max(0.8, scale * 0.035))
                )
                painter.drawPolyline(
                    QPolygonF(
                        [
                            tail + normal * (scale * 0.1),
                            tip,
                            tail - normal * (scale * 0.1),
                        ]
                    )
                )

    def _paint_cell(
        self,
        painter: QPainter,
        geometry: BoardGeometry,
        cell: GridCell,
        fill: QColor,
        border: QColor,
    ) -> None:
        """Draw a single scaled route square with a subtle rounded border.

        Args:
            painter: The active painter.
            geometry: The current board transform.
            cell: The (row, column) cell to draw.
            fill: The cell's fill color.
            border: The cell's outline color.
        """
        row, column = cell
        rectangle = _grid_rect(
            geometry, column + 0.035, row + 0.035, 0.93, 0.93
        )
        painter.setBrush(fill)
        painter.setPen(QPen(border, max(0.6, geometry.cell_size * 0.02)))
        radius = geometry.cell_size * 0.07
        painter.drawRoundedRect(rectangle, radius, radius)

    def _paint_finish(
        self, painter: QPainter, geometry: BoardGeometry
    ) -> None:
        """Draw the four central finish triangles and their shared badge.

        Args:
            painter: The active painter.
            geometry: The finish polygons and current board transform.
        """
        scale = geometry.cell_size
        painter.setPen(QPen(QColor("#ffffff"), max(0.8, scale * 0.035)))
        for color, points in geometry.FINISH_POLYGONS.items():
            shade = QColor(PLAYER_COLORS[color])
            shade.setAlpha(190)
            painter.setBrush(shade)
            painter.drawPolygon(
                QPolygonF(
                    [QPointF(*geometry.point(*point)) for point in points]
                )
            )
        badge = _grid_rect(geometry, 6.85, 7.22, 1.3, 0.56)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#ffffff"))
        painter.drawRoundedRect(badge, scale * 0.15, scale * 0.15)
        font = QFont(self.font())
        font.setPixelSize(max(5, round(scale * 0.24)))
        font.setWeight(QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(QColor("#24334b"))
        painter.drawText(badge, Qt.AlignmentFlag.AlignCenter, "FINISH")
