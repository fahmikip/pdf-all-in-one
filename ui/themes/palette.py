"""Glassmorphism application themes (frosted translucent panels over a vivid backdrop)."""

from __future__ import annotations

from PySide6.QtGui import QGuiApplication


def dark_mode(theme: str) -> bool:
    """Return True when the effective theme is dark."""
    return theme == "dark" or (theme == "system" and _system_is_dark())


def _system_is_dark() -> bool:
    app = QGuiApplication.instance()
    return bool(app and app.styleHints().colorScheme().value == 2)


def _hex_to_rgb(color: str) -> tuple[int, int, int]:
    value = color.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def rgba(color: str, alpha: float) -> str:
    r, g, b = _hex_to_rgb(color)
    return f"rgba({r}, {g}, {b}, {alpha})"


def stylesheet_for(theme: str) -> str:
    dark = dark_mode(theme)
    if dark:
        palette = {
            "bg": "#0B0F19",
            "text": "#F1F5F9",
            "muted": "#9AA7BC",
            "glass": "rgba(30, 41, 59, 0.45)",
            "glass_hi": "rgba(51, 65, 85, 0.55)",
            "border": "rgba(148, 163, 184, 0.20)",
            "border_hi": "rgba(148, 163, 184, 0.45)",
            "field": "rgba(15, 23, 42, 0.55)",
            "hover": "rgba(51, 65, 85, 0.45)",
            "brand": "#818CF8",
            "brand_deep": "#6366F1",
            "white": "#FFFFFF",
        }
    else:
        palette = {
            "bg": "#EEF2FF",
            "text": "#1E1B4B",
            "muted": "#64748B",
            "glass": "rgba(255, 255, 255, 0.55)",
            "glass_hi": "rgba(255, 255, 255, 0.78)",
            "border": "rgba(100, 116, 139, 0.28)",
            "border_hi": "rgba(99, 102, 241, 0.45)",
            "field": "rgba(255, 255, 255, 0.60)",
            "hover": "rgba(255, 255, 255, 0.72)",
            "brand": "#4F46E5",
            "brand_deep": "#6366F1",
            "white": "#FFFFFF",
        }

    text = palette["text"]
    muted = palette["muted"]
    glass = palette["glass"]
    glass_hi = palette["glass_hi"]
    border = palette["border"]
    border_hi = palette["border_hi"]
    field = palette["field"]
    hover = palette["hover"]
    brand = palette["brand"]
    brand_deep = palette["brand_deep"]

    accent = {
        "indigo": ("#6366F1", "#4F46E5"),
        "emerald": ("#34D399", "#059669"),
        "amber": ("#FBBF24", "#D97706"),
        "cyan": ("#22D3EE", "#0891B2"),
        "violet": ("#A78BFA", "#7C3AED"),
        "rose": ("#FB7185", "#E11D48"),
        "teal": ("#2DD4BF", "#0D9488"),
    }
    if not dark:
        accent = {
            "indigo": ("#6366F1", "#4F46E5"),
            "emerald": ("#10B981", "#059669"),
            "amber": ("#F59E0B", "#D97706"),
            "cyan": ("#06B6D4", "#0891B2"),
            "violet": ("#8B5CF6", "#7C3AED"),
            "rose": ("#F43F5E", "#E11D48"),
            "teal": ("#14B8A6", "#0D9488"),
        }

    def glass_card(acc: str, tint: tuple[str, str]) -> str:
        light = tint[0]
        return (
            f"QFrame#quickCard[accent=\"{acc}\"], QFrame#statCard[accent=\"{acc}\"] {{ "
            f"background: {rgba(light, 0.16)}; border: 1px solid {rgba(light, 0.45)}; }}"
            f"QFrame#quickCard[accent=\"{acc}\"] QPushButton#cardAction {{ "
            f"background: {rgba(light, 0.85)}; color: #FFFFFF; border: none; }}"
            f"QFrame#quickCard[accent=\"{acc}\"] QPushButton#cardAction:hover {{ "
            f"background: {light}; }}"
        )

    card_rules = "\n".join(glass_card(name, colors) for name, colors in accent.items())

    return f"""
    QWidget {{ color: {text}; font-family: 'Segoe UI'; font-size: 14px; }}
    QMainWindow {{ background: transparent; }}
    QMainWindow, QStackedWidget, QScrollArea, QScrollArea > QWidget > QWidget {{ background: transparent; }}

    QLabel {{ background: transparent; border: none; }}
    QToolTip {{ background: {glass_hi}; color: {text}; border: 1px solid {border_hi}; padding: 6px; border-radius: 6px; }}

    /* ---- Sidebar (frosted pane) ---- */
    #sidebar {{
        background: {glass}; border: none; border-right: 1px solid {border};
        border-radius: 0px 22px 22px 0px;
    }}
    #sidebarScroll, #sidebarScroll > QWidget > QWidget, QWidget#sidebarNavigation {{ background: transparent; }}
    #brand {{ font-size: 21px; font-weight: 700; color: {brand}; }}
    #subtitle, #muted {{ color: {muted}; }}
    #sidebar QPushButton {{ padding-left: 10px; }}

    /* ---- Generic buttons ---- */
    QPushButton {{ border: none; border-radius: 9px; padding: 9px 12px; text-align: left; background: transparent; color: {text}; }}
    QPushButton:hover {{ background: {hover}; }}
    QPushButton:pressed {{ background: {border_hi}; }}
    QPushButton:checked {{ background: {rgba(brand, 0.85)}; color: white; font-weight: 600; }}
    QPushButton:disabled {{ color: {muted}; background: transparent; }}

    QScrollArea#sidebarScroll QPushButton {{ margin-left: 4px; margin-right: 4px; border-radius: 9px; }}
    QScrollArea#sidebarScroll QPushButton:hover:!checked {{ background: {hover}; color: {brand}; }}

    QPushButton#primary {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {rgba("#818CF8", 0.95)}, stop:1 {rgba(brand_deep, 0.95)});
        color: white; text-align: center; font-weight: 600; padding: 11px 18px; border-radius: 10px;
    }}
    QPushButton#primary:hover {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {rgba("#6366F1", 0.95)}, stop:1 {rgba("#4338CA", 0.95)}); }}
    QPushButton#primary:pressed {{ background: {rgba("#4338CA", 0.95)}; }}
    QPushButton#primary:disabled {{ background: {rgba("#A5B4FC", 0.5)}; color: white; }}

    QPushButton#success {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {rgba("#34D399", 0.95)}, stop:1 {rgba("#059669", 0.95)});
        color: white; text-align: center; font-weight: 600; padding: 11px 18px; border-radius: 10px;
    }}
    QPushButton#success:hover {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {rgba("#10B981", 0.95)}, stop:1 {rgba("#047857", 0.95)}); }}
    QPushButton#success:pressed {{ background: {rgba("#047857", 0.95)}; }}
    QPushButton#success:disabled {{ background: {rgba("#6EE7B7", 0.5)}; color: white; }}

    QPushButton#warning {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {rgba("#FBBF24", 0.95)}, stop:1 {rgba("#D97706", 0.95)});
        color: white; text-align: center; font-weight: 600; padding: 11px 18px; border-radius: 10px;
    }}
    QPushButton#warning:hover {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {rgba("#F59E0B", 0.95)}, stop:1 {rgba("#B45309", 0.95)}); }}
    QPushButton#warning:pressed {{ background: {rgba("#B45309", 0.95)}; }}

    QPushButton#danger {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {rgba("#FB7185", 0.95)}, stop:1 {rgba("#E11D48", 0.95)});
        color: white; text-align: center; font-weight: 600; padding: 11px 18px; border-radius: 10px;
    }}
    QPushButton#danger:hover {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {rgba("#F43F5E", 0.95)}, stop:1 {rgba("#BE123C", 0.95)}); }}
    QPushButton#danger:pressed {{ background: {rgba("#BE123C", 0.95)}; }}
    QPushButton#danger:disabled {{ background: {rgba("#FDA4AF", 0.5)}; color: white; }}

    QPushButton#info {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {rgba("#38BDF8", 0.95)}, stop:1 {rgba("#0284C7", 0.95)});
        color: white; text-align: center; font-weight: 600; padding: 11px 18px; border-radius: 10px;
    }}
    QPushButton#info:hover {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {rgba("#0EA5E9", 0.95)}, stop:1 {rgba("#0369A1", 0.95)}); }}
    QPushButton#info:pressed {{ background: {rgba("#0369A1", 0.95)}; }}
    QPushButton#info:disabled {{ background: {rgba("#7DD3FC", 0.5)}; color: white; }}

    QPushButton#ghost {{
        background: {glass}; border: 1px solid {border_hi}; color: {text};
        text-align: center; font-weight: 500; padding: 9px 14px; border-radius: 9px;
    }}
    QPushButton#ghost:hover {{ background: {glass_hi}; border-color: {brand}; color: {brand}; }}
    QPushButton#ghost:pressed {{ background: {hover}; }}
    QPushButton#ghost:disabled {{ color: {muted}; border-color: {border}; }}

    /* ---- Frosted panels ---- */
    QFrame#card {{
        background: {glass}; border: 1px solid {border}; border-radius: 16px;
    }}
    QFrame#quickCard, QFrame#statCard {{ border-radius: 16px; }}
    QFrame#quickCard:hover {{ border-width: 2px; }}
    {card_rules}
    QFrame#dropZone {{
        background: {rgba("#FFFFFF", 0.30) if not dark else rgba("#1E293B", 0.25)};
        border: 2px dashed {rgba(brand, 0.65)}; border-radius: 18px;
    }}
    QFrame#dropZone:hover {{ border-color: {brand}; border-width: 2px; }}
    QFrame#dropZone QLabel#section {{ color: {brand}; }}

    /* ---- Typography ---- */
    QLabel#title {{ font-size: 28px; font-weight: 700; letter-spacing: 0.2px; }}
    QLabel#section {{ font-size: 17px; font-weight: 650; }}
    QLabel#subtitle {{ font-size: 14px; }}

    /* ---- Status bar (frosted) ---- */
    QStatusBar {{
        background: {glass}; border-top: 1px solid {border}; color: {muted}; padding: 2px 10px;
    }}
    QProgressBar {{ background: {border}; border: none; border-radius: 5px; height: 10px; text-align: center; color: transparent; }}
    QProgressBar::chunk {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {brand}, stop:1 #10B981);
        border-radius: 5px;
    }}

    /* ---- Scrollbars ---- */
    QScrollArea {{ border: none; }}
    QScrollBar:vertical {{ background: transparent; width: 9px; margin: 2px; }}
    QScrollBar::handle:vertical {{ background: {border}; border-radius: 4px; min-height: 28px; }}
    QScrollBar::handle:vertical:hover {{ background: {rgba(brand, 0.7)}; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    QScrollBar:horizontal {{ background: transparent; height: 9px; margin: 2px; }}
    QScrollBar::handle:horizontal {{ background: {border}; border-radius: 4px; min-width: 28px; }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

    QFormLayout QLabel {{ padding-top: 4px; padding-bottom: 4px; }}

    /* ---- Inputs ---- */
    QComboBox, QLineEdit, QSpinBox, QFontComboBox {{
        background: {field}; border: 1px solid {border}; border-radius: 9px; padding: 7px 10px; min-height: 20px;
    }}
    QComboBox:hover, QLineEdit:hover, QSpinBox:hover, QFontComboBox:hover {{ border-color: {brand}; }}
    QComboBox:focus, QLineEdit:focus, QSpinBox:focus, QFontComboBox:focus {{ border: 2px solid {brand}; }}
    QComboBox::drop-down {{ border: none; width: 26px; }}
    QComboBox::down-arrow {{
        image: none; border-left: 5px solid transparent; border-right: 5px solid transparent;
        border-top: 6px solid {muted}; margin-right: 8px;
    }}
    QComboBox QAbstractItemView {{
        background: {glass_hi if dark else "rgba(255,255,255,0.95)"};
        border: 1px solid {border_hi}; border-radius: 10px;
        selection-background-color: {brand}; selection-color: white; padding: 4px;
    }}

    /* ---- Checkboxes & radios ---- */
    QCheckBox {{ spacing: 8px; }}
    QCheckBox::indicator {{ width: 18px; height: 18px; border: 1px solid {border_hi}; border-radius: 5px; background: {field}; }}
    QCheckBox::indicator:hover {{ border-color: {brand}; }}
    QCheckBox::indicator:checked {{ background: {brand}; border-color: {brand}; }}
    QRadioButton::indicator {{ width: 18px; height: 18px; border: 1px solid {border_hi}; border-radius: 9px; background: {field}; }}
    QRadioButton::indicator:hover {{ border-color: {brand}; }}
    QRadioButton::indicator:checked {{ background: {brand}; border: 5px solid {brand}; }}

    /* ---- Lists ---- */
    QListWidget {{
        background: {field}; border: 1px solid {border}; border-radius: 12px; padding: 6px; outline: none;
    }}
    QListWidget::item {{ border-radius: 8px; padding: 7px; }}
    QListWidget::item:selected {{ background: {rgba(brand, 0.8)}; color: white; }}
    QListWidget::item:hover:!selected {{ background: {hover}; }}

    /* ---- Tables ---- */
    QTableWidget, QTableView {{
        background: {field}; border: 1px solid {border}; border-radius: 12px;
        gridline-color: {border}; selection-background-color: transparent; selection-color: {text};
    }}
    QTableWidget::item {{ padding: 5px; }}
    QTableWidget::item:selected {{ background: {rgba(brand, 0.18)}; color: {text}; border-left: 3px solid {brand}; }}
    QHeaderView::section {{
        background: {glass}; border: none; border-bottom: 1px solid {border};
        padding: 8px 10px; font-weight: 600; color: {muted};
    }}

    /* ---- Tabs ---- */
    QTabWidget::pane {{ border: 1px solid {border}; border-radius: 13px; background: {glass}; top: -1px; }}
    QTabBar::tab {{
        background: transparent; padding: 9px 18px; margin-right: 3px; border-radius: 9px 9px 0 0; color: {muted};
    }}
    QTabBar::tab:selected {{ background: {rgba(brand, 0.85)}; color: white; font-weight: 600; }}
    QTabBar::tab:hover:!selected {{ background: {hover}; color: {text}; }}

    QGraphicsView {{ border: 1px solid {border}; border-radius: 13px; background: {field}; }}
    QSplitter::handle {{ background: {border}; }}
    """


def accent_styles() -> dict[str, str]:
    """Return objectName -> stylesheet fragment for accent-colored buttons."""
    return {
        "success": "QPushButton#success { background: " + rgba("#059669", 0.95) + "; color: white; text-align: center; font-weight: 600; padding: 11px 18px; border-radius: 10px; } QPushButton#success:hover { background: " + rgba("#047857", 0.95) + "; }",
        "warning": "QPushButton#warning { background: " + rgba("#D97706", 0.95) + "; color: white; text-align: center; font-weight: 600; padding: 11px 18px; border-radius: 10px; } QPushButton#warning:hover { background: " + rgba("#B45309", 0.95) + "; }",
        "danger": "QPushButton#danger { background: " + rgba("#E11D48", 0.95) + "; color: white; text-align: center; font-weight: 600; padding: 11px 18px; border-radius: 10px; } QPushButton#danger:hover { background: " + rgba("#BE123C", 0.95) + "; }",
        "info": "QPushButton#info { background: " + rgba("#0284C7", 0.95) + "; color: white; text-align: center; font-weight: 600; padding: 11px 18px; border-radius: 10px; } QPushButton#info:hover { background: " + rgba("#0369A1", 0.95) + "; }",
        "ghost": "QPushButton#ghost { background: transparent; border: 1px solid " + rgba("#818CF8", 0.6) + "; color: #4F46E5; text-align: center; font-weight: 500; padding: 9px 14px; border-radius: 9px; } QPushButton#ghost:hover { background: " + rgba("#EEF2FF", 0.8) + "; }",
    }