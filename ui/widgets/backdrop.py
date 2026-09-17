"""Vivid translucent backdrop behind the frosted-glass UI."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QRadialGradient
from PySide6.QtWidgets import QWidget

from ui.themes.palette import rgba


@dataclass(frozen=True)
class _Orb:
    x: float
    y: float
    radius: float
    color: str
    alpha: float


_LIGHT = (
    QColor("#EEF2FF"),
    QColor("#E0E7FF"),
    QColor("#EDE9FE"),
    QColor("#DDF6FF"),
)

_DARK = (
    QColor("#0B0F19"),
    QColor("#121A3A"),
    QColor("#1E1B4B"),
    QColor("#0F1B2D"),
)

_ORBS_LIGHT = (
    _Orb(0.06, 0.05, 340, "#6366F1", 0.28),
    _Orb(0.92, 0.12, 300, "#22D3EE", 0.22),
    _Orb(0.82, 0.78, 360, "#A78BFA", 0.24),
    _Orb(0.10, 0.85, 260, "#34D399", 0.14),
)

_ORBS_DARK = (
    _Orb(0.06, 0.05, 360, "#6366F1", 0.32),
    _Orb(0.92, 0.12, 320, "#22D3EE", 0.20),
    _Orb(0.82, 0.78, 380, "#A78BFA", 0.26),
    _Orb(0.10, 0.85, 280, "#2DD4BF", 0.16),
)


class Backdrop(QWidget):
    """Paints a tinted gradient with soft colored orbs behind the glass panels."""

    def __init__(self, dark: bool = False) -> None:
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._dark = dark
        colors = _DARK if dark else _LIGHT
        self._gradient = (colors[0], colors[1], colors[2], colors[3])
        self._orbs = _ORBS_DARK if dark else _ORBS_LIGHT

    def set_dark(self, dark: bool) -> None:
        self._dark = dark
        colors = _DARK if dark else _LIGHT
        self._gradient = (colors[0], colors[1], colors[2], colors[3])
        self._orbs = _ORBS_DARK if dark else _ORBS_LIGHT
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect())
        gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
        for stop, color in zip((0.0, 0.35, 0.72, 1.0), self._gradient, strict=True):
            gradient.setColorAt(stop, color)
        painter.fillRect(rect, gradient)
        width, height = rect.width(), rect.height()
        for orb in self._orbs:
            center = (orb.x * width, orb.y * height)
            radius = orb.radius * min(width, height) / 800
            glow = QRadialGradient(center[0], center[1], radius)
            glow.setColorAt(0.0, QColor(rgba(orb.color, orb.alpha)))
            glow.setColorAt(0.7, QColor(rgba(orb.color, orb.alpha * 0.45)))
            glow.setColorAt(1.0, QColor(rgba(orb.color, 0.0)))
            painter.fillRect(rect, glow)