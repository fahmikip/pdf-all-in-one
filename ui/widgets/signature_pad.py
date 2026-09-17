"""Freehand signature capture widget that exports strokes as a transparent PNG."""

from __future__ import annotations

import tempfile
import uuid
from pathlib import Path

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

INK = QColor(16, 40, 160)
PAPER = QColor(248, 250, 252)
BASELINE = QColor(203, 213, 225)

SignatureStroke = list[QPointF]


def render_signature_image(
    strokes: list[SignatureStroke],
    width: int,
    height: int,
    *,
    ink: QColor | None = None,
    background: QColor | None = None,
    scale: float = 1.0,
) -> QImage:
    """Render signature strokes into a raster image with transparent background."""
    image = QImage(width, height, QImage.Format.Format_ARGB32)
    fill = background if background is not None else Qt.GlobalColor.transparent
    image.fill(fill)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(ink or INK)
    pen.setWidthF(max(2.0, height / 60.0))
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    for points in strokes:
        path = QPainterPath()
        scaled: list[QPointF] = [QPointF(point.x() * scale, point.y() * scale) for point in points]
        if not scaled:
            continue
        path.moveTo(scaled[0])
        for point in scaled[1:]:
            path.lineTo(point)
        painter.drawPath(path)
    painter.end()
    return image


def signature_png_path(
    strokes: list[SignatureStroke],
    *,
    pad_width: int = 320,
    pad_height: int = 120,
    scale: float = 3.0,
) -> Path:
    """Write the strokes to a temporary transparent PNG and return its path."""
    image = render_signature_image(
        strokes,
        round(pad_width * scale),
        round(pad_height * scale),
        scale=scale,
    )
    target = Path(tempfile.gettempdir()) / f"pdfmaster-signature-{uuid.uuid4().hex}.png"
    image.save(str(target), "PNG")
    return target


class SignaturePad(QWidget):
    """A small drawing surface for handwritten signatures."""

    changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.strokes: list[SignatureStroke] = []
        self.current: SignatureStroke = []
        self.setMinimumSize(320, 120)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(120)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setObjectName("signaturePad")

    def is_empty(self) -> bool:
        return not self.strokes

    def clear(self) -> None:
        self.strokes = []
        self.current = []
        self.update()
        self.changed.emit()

    def has_changes(self) -> bool:
        return bool(self.strokes)

    def image(self) -> QImage:
        return render_signature_image(self.strokes, self.width(), self.height())

    def png_path(self) -> Path:
        return signature_png_path(self.strokes, pad_width=self.width(), pad_height=self.height())

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.current = [QPointF(event.position())]
            self.strokes.append(self.current)
            self.update()
            self.changed.emit()

    def mouseMoveEvent(self, event) -> None:
        if event.buttons() & Qt.MouseButton.LeftButton and self.current:
            point = QPointF(event.position())
            if self.current and (point - self.current[-1]).manhattanLength() < 3:
                return
            self.current.append(point)
            self.update()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.current = []
            self.changed.emit()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(PAPER)
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 10, 10)
        baseline = QPen(BASELINE)
        baseline.setStyle(Qt.PenStyle.DashLine)
        baseline.setWidthF(max(1.0, self.height() / 120.0))
        painter.setPen(baseline)
        baseline_y = self.height() * 0.72
        painter.drawLine(18, int(baseline_y), self.width() - 18, int(baseline_y))
        pen = QPen(INK)
        pen.setWidthF(max(2.0, self.height() / 60.0))
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        for points in self.strokes:
            path = QPainterPath()
            path.moveTo(points[0])
            for point in points[1:]:
                path.lineTo(point)
            painter.drawPath(path)
        painter.end()
