"""Modern light/dark Qt stylesheets with colorful, semantic controls."""

from __future__ import annotations

from PySide6.QtGui import QGuiApplication


def _system_is_dark() -> bool:
    app = QGuiApplication.instance()
    return bool(app and app.styleHints().colorScheme().value == 2)


def stylesheet_for(theme: str) -> str:
    dark = theme == "dark" or (theme == "system" and _system_is_dark())
    if dark:
        bg, surface, card, text, muted, border, hover = (
            "#0B0F19",
            "#111827",
            "#182235",
            "#F8FAFC",
            "#94A3B8",
            "#263449",
            "#22304A",
        )
    else:
        bg, surface, card, text, muted, border, hover = (
            "#F5F7FB",
            "#FFFFFF",
            "#FFFFFF",
            "#172033",
            "#64748B",
            "#E2E8F0",
            "#EEF2FF",
        )

    brand = "#6366F1"
    accent_box = {
        "indigo": ("#EEF2FF", "#4F46E5"),
        "emerald": ("#ECFDF5", "#059669"),
        "amber": ("#FFFBEB", "#D97706"),
        "cyan": ("#ECFEFF", "#0891B2"),
        "violet": ("#F5F3FF", "#6D28D9"),
        "rose": ("#FFF1F2", "#E11D48"),
        "teal": ("#F0FDFA", "#0D9488"),
    }
    if dark:
        accent_box = {
            "indigo": ("#171A3A", "#818CF8"),
            "emerald": ("#0F2E2A", "#34D399"),
            "amber": ("#332515", "#FBBF24"),
            "cyan": ("#102D36", "#22D3EE"),
            "violet": ("#25183C", "#A78BFA"),
            "rose": ("#351725", "#FB7185"),
            "teal": ("#0C2A2E", "#2DD4BF"),
        }

    card_rules = "\n".join(
        f'QFrame#quickCard[accent="{name}"], QFrame#statCard[accent="{name}"] {{ background: {colors[0]}; border: 1px solid {colors[1]}; }}'
        f'QFrame#quickCard[accent="{name}"] QPushButton#cardAction {{ background: {colors[1]}; color: #FFFFFF; }}'
        f'QFrame#quickCard[accent="{name}"] QPushButton#cardAction:hover {{ background: {colors[1]}; }}'
        for name, colors in accent_box.items()
    )

    drop_gradient = (
        "stop:0 #102D36, stop:0.5 #182235, stop:1 #0F2E2A"
        if dark
        else "stop:0 #EEF2FF, stop:0.5 #FFFFFF, stop:1 #F0FDFA"
    )
    drop_text_color = "#94A3B8" if dark else "#4F46E5"

    return f"""
    QWidget {{ color: {text}; font-family: 'Segoe UI'; font-size: 14px; }}
    QMainWindow, QStackedWidget {{ background: {bg}; }}
    QMainWindow > QWidget, QStackedWidget > QWidget {{ background: {bg}; }}
    QLabel {{ background: transparent; border: none; }}
    QToolTip {{ background: {surface}; color: {text}; border: 1px solid {border}; padding: 5px; border-radius: 4px; }}

    #sidebar {{ background: {surface}; border-right: 1px solid {border}; }}
    #brand {{ font-size: 21px; font-weight: 700; color: {brand}; }}
    #subtitle, #muted {{ color: {muted}; }}

    QPushButton {{ border: none; border-radius: 8px; padding: 9px 12px; text-align: left; background: transparent; color: {text}; }}
    QPushButton:hover {{ background: {hover}; }}
    QPushButton:pressed {{ background: {border}; }}
    QPushButton:checked {{ background: {brand}; color: white; font-weight: 600; }}
    QPushButton:disabled {{ color: {muted}; background: transparent; }}

    QScrollArea#sidebarScroll QPushButton {{ margin-left: 4px; margin-right: 4px; border-radius: 8px; }}
    QScrollArea#sidebarScroll QPushButton:hover:!checked {{ background: {hover}; color: {brand}; }}

    QPushButton#primary {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #818CF8, stop:1 #4F46E5);
        color: white; text-align: center; font-weight: 600; padding: 11px 18px; border-radius: 9px;
    }}
    QPushButton#primary:hover {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #6366F1, stop:1 #4338CA); }}
    QPushButton#primary:pressed {{ background: #4338CA; }}
    QPushButton#primary:disabled {{ background: #A5B4FC; color: white; }}

    QPushButton#success {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #34D399, stop:1 #059669);
        color: white; text-align: center; font-weight: 600; padding: 11px 18px; border-radius: 9px;
    }}
    QPushButton#success:hover {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #10B981, stop:1 #047857); }}
    QPushButton#success:pressed {{ background: #047857; }}
    QPushButton#success:disabled {{ background: #6EE7B7; color: white; }}

    QPushButton#warning {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #FBBF24, stop:1 #D97706);
        color: white; text-align: center; font-weight: 600; padding: 11px 18px; border-radius: 9px;
    }}
    QPushButton#warning:hover {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #F59E0B, stop:1 #B45309); }}
    QPushButton#warning:pressed {{ background: #B45309; }}

    QPushButton#danger {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #FB7185, stop:1 #E11D48);
        color: white; text-align: center; font-weight: 600; padding: 11px 18px; border-radius: 9px;
    }}
    QPushButton#danger:hover {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #F43F5E, stop:1 #BE123C); }}
    QPushButton#danger:pressed {{ background: #BE123C; }}
    QPushButton#danger:disabled {{ background: #FDA4AF; color: white; }}

    QPushButton#info {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #38BDF8, stop:1 #0284C7);
        color: white; text-align: center; font-weight: 600; padding: 11px 18px; border-radius: 9px;
    }}
    QPushButton#info:hover {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0EA5E9, stop:1 #0369A1); }}
    QPushButton#info:pressed {{ background: #0369A1; }}
    QPushButton#info:disabled {{ background: #7DD3FC; color: white; }}

    QPushButton#ghost {{
        background: {surface}; border: 1px solid {border}; color: {text};
        text-align: center; font-weight: 500; padding: 9px 14px; border-radius: 8px;
    }}
    QPushButton#ghost:hover {{ background: {hover}; border-color: {brand}; color: {brand}; }}
    QPushButton#ghost:pressed {{ background: {border}; }}
    QPushButton#ghost:disabled {{ color: {muted}; border-color: {border}; }}

    QFrame#card {{ background: {card}; border: 1px solid {border}; border-radius: 14px; }}
    QFrame#quickCard, QFrame#statCard {{ border-radius: 14px; }}
    QFrame#quickCard:hover {{ border-width: 2px; }}
    {card_rules}
    QFrame#dropZone {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1, {drop_gradient});
        border: 2px dashed #6366F1; border-radius: 16px;
    }}
    QFrame#dropZone:hover {{ border-color: #4F46E5; border-width: 2.5px; }}
    QFrame#dropZone QLabel#section {{ color: {drop_text_color}; }}

    QLabel#title {{ font-size: 28px; font-weight: 700; }}
    QLabel#section {{ font-size: 17px; font-weight: 650; }}

    QStatusBar {{ background: {surface}; border-top: 1px solid {border}; color: {muted}; }}
    QScrollArea {{ border: none; }}
    QScrollArea#sidebarScroll, QScrollArea#sidebarScroll > QWidget > QWidget, QWidget#sidebarNavigation {{ background: {surface}; }}
    QScrollBar:vertical {{ background: transparent; width: 7px; margin: 0; }}
    QScrollBar::handle:vertical {{ background: {border}; border-radius: 3px; min-height: 28px; }}
    QScrollBar::handle:vertical:hover {{ background: #A5B4FC; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    QScrollArea > QWidget > QWidget {{ background: {bg}; }}

    QFormLayout QLabel {{ padding-top: 4px; padding-bottom: 4px; }}

    QComboBox, QLineEdit, QSpinBox, QFontComboBox {{
        background: {card}; border: 1px solid {border}; border-radius: 7px; padding: 7px 10px; min-height: 20px;
    }}
    QComboBox:hover, QLineEdit:hover, QSpinBox:hover, QFontComboBox:hover {{ border-color: #818CF8; }}
    QComboBox:focus, QLineEdit:focus, QSpinBox:focus, QFontComboBox:focus {{ border: 2px solid {brand}; }}
    QComboBox::drop-down {{ border: none; width: 24px; }}
    QComboBox::down-arrow {{ image: none; border-left: 5px solid transparent; border-right: 5px solid transparent; border-top: 6px solid {muted}; margin-right: 8px; }}
    QComboBox QAbstractItemView {{
        background: {card}; border: 1px solid {border}; border-radius: 8px;
        selection-background-color: {brand}; selection-color: white; padding: 4px;
    }}
    QCheckBox {{ spacing: 7px; }}
    QCheckBox::indicator {{ width: 17px; height: 17px; border: 1px solid {border}; border-radius: 4px; background: {card}; }}
    QCheckBox::indicator:hover {{ border-color: {brand}; }}
    QCheckBox::indicator:checked {{ background: {brand}; border-color: {brand}; }}

    QListWidget {{ background: {card}; border: 1px solid {border}; border-radius: 10px; padding: 6px; outline: none; }}
    QListWidget::item {{ border-radius: 7px; padding: 7px; }}
    QListWidget::item:selected {{ background: {brand}; color: white; }}
    QListWidget::item:hover:!selected {{ background: {hover}; }}

    QTableWidget, QTableView {{
        background: {card}; border: 1px solid {border}; border-radius: 10px;
        gridline-color: {border}; selection-background-color: #EEF2FF; selection-color: {text};
    }}
    QTableWidget::item {{ padding: 4px; }}
    QTableWidget::item:selected {{ background: #EEF2FF; color: {text}; border-left: 3px solid {brand}; }}
    QHeaderView::section {{
        background: {surface}; border: none; border-bottom: 1px solid {border};
        padding: 8px 10px; font-weight: 600; color: {muted};
    }}

    QTabWidget::pane {{ border: 1px solid {border}; border-radius: 12px; background: {card}; top: -1px; }}
    QTabBar::tab {{
        background: transparent; padding: 9px 18px; margin-right: 3px; border-radius: 8px 8px 0 0; color: {muted};
    }}
    QTabBar::tab:selected {{ background: {brand}; color: white; font-weight: 600; }}
    QTabBar::tab:hover:!selected {{ background: {hover}; color: {text}; }}

    QProgressBar {{ background: {border}; border: none; border-radius: 5px; height: 10px; text-align: center; color: transparent; }}
    QProgressBar::chunk {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #818CF8, stop:1 #10B981);
        border-radius: 5px;
    }}
    QGraphicsView {{ border: 1px solid {border}; border-radius: 12px; }}
    """


def accent_styles() -> dict[str, str]:
    """Return objectName -> stylesheet fragment for accent-colored widgets."""
    return {
        "success": "QPushButton#success { background: #059669; color: white; text-align: center; font-weight: 600; padding: 11px 18px; border-radius: 9px; } QPushButton#success:hover { background: #047857; }",
        "warning": "QPushButton#warning { background: #D97706; color: white; text-align: center; font-weight: 600; padding: 11px 18px; border-radius: 9px; } QPushButton#warning:hover { background: #B45309; }",
        "danger": "QPushButton#danger { background: #E11D48; color: white; text-align: center; font-weight: 600; padding: 11px 18px; border-radius: 9px; } QPushButton#danger:hover { background: #BE123C; }",
        "info": "QPushButton#info { background: #0284C7; color: white; text-align: center; font-weight: 600; padding: 11px 18px; border-radius: 9px; } QPushButton#info:hover { background: #0369A1; }",
        "ghost": "QPushButton#ghost { background: transparent; border: 1px solid #A5B4FC; color: #4F46E5; text-align: center; font-weight: 500; padding: 9px 14px; border-radius: 8px; } QPushButton#ghost:hover { background: #EEF2FF; }",
    }
