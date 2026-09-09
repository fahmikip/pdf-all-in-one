"""Crisp, theme-friendly vector icons for the application shell."""
from __future__ import annotations

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

PATHS = {
    "home": '<path d="M3 10.5 12 3l9 7.5V21h-6v-7H9v7H3Z"/>',
    "compress": '<path d="M8 3v5H3M16 3v5h5M8 21v-5H3M16 21v-5h5"/><path d="M3 8l6-6M21 8l-6-6M3 16l6 6M21 16l-6 6"/>',
    "merge": '<path d="M5 3h9l4 4v14H5Z"/><path d="M14 3v5h5M9 12h6M12 9v6"/>',
    "split": '<circle cx="6" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><path d="m8.5 7.5 10 6.5M8.5 16.5l10-6.5"/>',
    "organize": '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
    "convert": '<path d="M4 7h14M15 4l3 3-3 3M20 17H6M9 14l-3 3 3 3"/>',
    "edit": '<path d="M4 20h4L19 9l-4-4L4 16Z"/><path d="m13.5 6.5 4 4"/>',
    "security": '<rect x="4" y="10" width="16" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3M12 14v3"/>',
    "ocr": '<path d="M3 8V3h5M16 3h5v5M21 16v5h-5M8 21H3v-5"/><path d="M7 12h10M7 16h7"/>',
    "batch": '<rect x="4" y="4" width="16" height="4" rx="1"/><rect x="4" y="10" width="16" height="4" rx="1"/><rect x="4" y="16" width="16" height="4" rx="1"/>',
    "history": '<circle cx="12" cy="12" r="9"/><path d="M12 7v6l4 2M3 5v5h5"/>',
    "settings": '<circle cx="12" cy="12" r="3"/><path d="M19 12a7 7 0 0 0-.1-1l2-1.5-2-3.4-2.4 1a8 8 0 0 0-1.7-1L14.5 3h-5L9 6.1a8 8 0 0 0-1.7 1L5 6.1 3 9.5 5.1 11a7 7 0 0 0 0 2L3 14.5l2 3.4 2.3-1a8 8 0 0 0 1.7 1l.5 3.1h5l.5-3.1a8 8 0 0 0 1.7-1l2.3 1 2-3.4-2.1-1.5a7 7 0 0 0 .1-1Z"/>',
    "about": '<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7h.01"/>',
    "privacy": '<path d="M12 22s8-4 8-11V5l-8-3-8 3v6c0 7 8 11 8 11Z"/><path d="m9 12 2 2 4-4"/>',
    "download": '<path d="M12 3v12M7 10l5 5 5-5M4 21h16"/>',
    "extract": '<path d="M12 3v10M8 9l4 4 4-4M4 15v6h16v-6"/><path d="M8 18h8"/>',
    "app": '<path d="M6 2h9l5 5v15H6Z"/><path d="M15 2v6h6M9 13h8M9 17h6"/>',
    "forms": '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M7 8h5M7 12h10M7 16h7"/><path d="M16.5 15.5v-4M14.5 13.5h4"/>',
}


def _pixmap(name: str, color: str, size: int) -> QPixmap:
    body = PATHS.get(name, PATHS["app"])
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">{body}</svg>'
    pixmap = QPixmap(size, size); pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap); painter.setRenderHint(QPainter.RenderHint.Antialiasing); QSvgRenderer(QByteArray(svg.encode())).render(painter); painter.end()
    return pixmap


def icon(name: str, size: int = 18) -> QIcon:
    result = QIcon()
    result.addPixmap(_pixmap(name, "#64748B", size), QIcon.Mode.Normal, QIcon.State.Off)
    result.addPixmap(_pixmap(name, "#FFFFFF", size), QIcon.Mode.Normal, QIcon.State.On)
    result.addPixmap(_pixmap(name, "#4F46E5", size), QIcon.Mode.Active, QIcon.State.Off)
    result.addPixmap(_pixmap(name, "#CBD5E1", size), QIcon.Mode.Disabled, QIcon.State.Off)
    return result


def colored_icon(name: str, color: str, size: int = 18) -> QIcon:
    """Create a single-color icon for cards and contextual actions."""
    return QIcon(_pixmap(name, color, size))
