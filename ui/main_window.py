"""Main responsive application shell."""
from __future__ import annotations

from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QHBoxLayout, QMainWindow, QStackedWidget, QWidget

from app.config import APP_NAME, ConfigStore, Settings, VERSION
from ui.footer import Footer
from ui.pages.about import AboutPage
from ui.pages.home import HomePage
from ui.pages.pdf_tools import CompressPage, MergePage, SplitPage
from ui.pages.organizer import OrganizerPage
from ui.pages.converter import ConverterPage
from ui.pages.edit import EditPage
from ui.pages.security import SecurityPage
from ui.pages.placeholder import PlaceholderPage
from ui.sidebar import Sidebar


class MainWindow(QMainWindow):
    def __init__(self, settings: Settings, config_store: ConfigStore) -> None:
        super().__init__()
        self.settings = settings
        self.config_store = config_store
        self.setWindowTitle(f"{APP_NAME} {VERSION}")
        self.setMinimumSize(1024, 700)
        self.resize(1280, 800)
        shell = QWidget(); layout = QHBoxLayout(shell); layout.setContentsMargins(0, 0, 0, 0); layout.setSpacing(0)
        self.sidebar = Sidebar(); layout.addWidget(self.sidebar)
        self.stack = QStackedWidget(); layout.addWidget(self.stack, 1)
        self.pages: dict[str, QWidget] = {
            "home": HomePage(), "about": AboutPage(), "compress": CompressPage(),
            "merge": MergePage(), "split": SplitPage(), "organize": OrganizerPage(), "convert": ConverterPage(), "edit": EditPage(), "security": SecurityPage(),
        }
        labels = {"ocr": "OCR PDF", "history": "History", "settings": "Settings"}
        for key, title in labels.items(): self.pages[key] = PlaceholderPage(title)
        for page in self.pages.values(): self.stack.addWidget(page)
        self.setCentralWidget(shell); self.setStatusBar(Footer())
        self.sidebar.page_requested.connect(self.navigate)
        home = self.pages["home"]
        if isinstance(home, HomePage): home.tool_requested.connect(self.navigate)
        self._create_shortcuts(); self.navigate("home")

    def _create_shortcuts(self) -> None:
        shortcuts = (("Ctrl+Q", self.close), ("Ctrl+M", lambda: self.navigate("merge")), ("Ctrl+O", lambda: self.navigate("home")))
        for sequence, callback in shortcuts:
            action = QAction(self); action.setShortcut(QKeySequence(sequence)); action.triggered.connect(callback); self.addAction(action)

    def navigate(self, page: str) -> None:
        target = self.pages.get(page)
        if target is not None:
            self.stack.setCurrentWidget(target)
            if page in self.sidebar.buttons: self.sidebar.select(page) if not self.sidebar.buttons[page].isChecked() else None
