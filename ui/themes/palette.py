"""Modern light/dark Qt stylesheets."""
from __future__ import annotations

from PySide6.QtGui import QGuiApplication


def _system_is_dark() -> bool:
    app = QGuiApplication.instance()
    return bool(app and app.styleHints().colorScheme().value == 2)


def stylesheet_for(theme: str) -> str:
    dark = theme == "dark" or (theme == "system" and _system_is_dark())
    if dark:
        bg, surface, card, text, muted, border, hover = "#0B0F19", "#111827", "#182235", "#F8FAFC", "#94A3B8", "#263449", "#22304A"
    else:
        bg, surface, card, text, muted, border, hover = "#F5F7FB", "#FFFFFF", "#FFFFFF", "#172033", "#64748B", "#E2E8F0", "#EEF2FF"
    return f"""
    QWidget {{ color: {text}; font-family: 'Segoe UI'; font-size: 14px; }}
    QMainWindow, QStackedWidget {{ background: {bg}; }}
    QMainWindow > QWidget, QStackedWidget > QWidget {{ background: {bg}; }}
    QLabel {{ background: transparent; border: none; }}
    #sidebar {{ background: {surface}; border-right: 1px solid {border}; }}
    #brand {{ font-size: 21px; font-weight: 700; color: #6366F1; }}
    #subtitle, #muted {{ color: {muted}; }}
    QPushButton {{ border: none; border-radius: 8px; padding: 9px 12px; text-align: left; background: transparent; }}
    QPushButton:hover {{ background: {hover}; }}
    QPushButton:checked {{ background: #6366F1; color: white; font-weight: 600; }}
    QPushButton#primary {{ background: #6366F1; color: white; text-align: center; font-weight: 600; padding: 11px 18px; }}
    QPushButton#primary:hover {{ background: #5558E8; }}
    QFrame#card {{ background: {card}; border: 1px solid {border}; border-radius: 14px; }}
    QFrame#dropZone {{ background: {card}; border: 2px dashed #A5B4FC; border-radius: 16px; }}
    QLabel#title {{ font-size: 28px; font-weight: 700; }}
    QLabel#section {{ font-size: 17px; font-weight: 650; }}
    QStatusBar {{ background: {surface}; border-top: 1px solid {border}; color: {muted}; }}
    QScrollArea {{ border: none; }}
    QScrollArea > QWidget > QWidget {{ background: {bg}; }}
    QComboBox, QLineEdit, QSpinBox {{ background: {card}; border: 1px solid {border}; border-radius: 7px; padding: 7px 10px; min-height: 20px; }}
    QComboBox:hover, QLineEdit:hover, QSpinBox:hover {{ border-color: #A5B4FC; }}
    QComboBox:focus, QLineEdit:focus, QSpinBox:focus {{ border: 2px solid #6366F1; }}
    QListWidget {{ background: {card}; border: 1px solid {border}; border-radius: 10px; padding: 6px; outline: none; }}
    QListWidget::item {{ border-radius: 7px; padding: 7px; }}
    QListWidget::item:selected {{ background: #6366F1; color: white; }}
    QListWidget::item:hover:!selected {{ background: {hover}; }}
    QProgressBar {{ background: {border}; border: none; border-radius: 5px; height: 10px; text-align: center; color: transparent; }}
    QProgressBar::chunk {{ background: #6366F1; border-radius: 5px; }}
    QToolTip {{ background: {surface}; color: {text}; border: 1px solid {border}; padding: 5px; }}
    """
