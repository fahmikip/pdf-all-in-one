"""Main responsive application shell."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QProcess, QThreadPool, QTimer, QUrl
from PySide6.QtGui import QAction, QDesktopServices, QKeySequence
from PySide6.QtWidgets import QHBoxLayout, QMainWindow, QMessageBox, QProgressDialog, QStackedWidget, QWidget

from app.config import APP_NAME, ConfigStore, Settings, VERSION, local_data_dir
from ui.footer import Footer
from ui.pages.about import AboutPage
from ui.pages.home import HomePage
from ui.pages.pdf_tools import CompressPage, MergePage, SplitPage
from ui.pages.organizer import OrganizerPage
from ui.pages.converter import ConverterPage
from ui.pages.edit import EditPage
from ui.pages.forms import FormsPage
from ui.pages.security import SecurityPage
from ui.pages.history import HistoryPage
from ui.pages.settings import SettingsPage
from ui.pages.ocr import OcrPage
from ui.pages.extract import ExtractPage
from ui.pages.batch import BatchPage
from ui.pages.placeholder import PlaceholderPage
from ui.sidebar import Sidebar
from core.jobs.worker import FunctionWorker
from core.utils.updater import UpdateInfo, check_for_update, download_release_asset


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
            "merge": MergePage(), "split": SplitPage(), "organize": OrganizerPage(), "convert": ConverterPage(), "edit": EditPage(), "forms": FormsPage(), "security": SecurityPage(),
            "history": HistoryPage(), "settings": SettingsPage(settings, config_store, self.check_updates_manual),
            "ocr": OcrPage(),
            "extract": ExtractPage(),
            "batch": BatchPage(settings.default_compression),
        }
        labels = {}
        for key, title in labels.items(): self.pages[key] = PlaceholderPage(title)
        for page in self.pages.values(): self.stack.addWidget(page)
        self.setCentralWidget(shell); self.setStatusBar(Footer())
        self.sidebar.page_requested.connect(self.navigate)
        home = self.pages["home"]
        if isinstance(home, HomePage): home.tool_requested.connect(self.navigate)
        self._create_shortcuts(); self.navigate("home")
        self.update_worker = None
        if settings.check_updates:
            QTimer.singleShot(3500, self.check_updates_silently)

    def _create_shortcuts(self) -> None:
        shortcuts = (("Ctrl+Q", self.close), ("Ctrl+M", lambda: self.navigate("merge")), ("Ctrl+O", lambda: self.navigate("home")))
        for sequence, callback in shortcuts:
            action = QAction(self); action.setShortcut(QKeySequence(sequence)); action.triggered.connect(callback); self.addAction(action)

    def navigate(self, page: str) -> None:
        target = self.pages.get(page)
        if target is not None:
            self.stack.setCurrentWidget(target)
            if page in self.sidebar.buttons: self.sidebar.select(page) if not self.sidebar.buttons[page].isChecked() else None

    def check_updates_silently(self) -> None:
        if self.update_worker is not None: return
        worker = FunctionWorker(check_for_update, VERSION); self.update_worker = worker
        worker.signals.result.connect(self._show_update)
        worker.signals.finished.connect(lambda: setattr(self, "update_worker", None))
        QThreadPool.globalInstance().start(worker)

    def check_updates_manual(self) -> None:
        if self.update_worker is not None: return
        worker = FunctionWorker(check_for_update, VERSION); self.update_worker = worker
        worker.signals.result.connect(lambda result: self._show_update(result, manual=True))
        worker.signals.finished.connect(lambda: setattr(self, "update_worker", None))
        QThreadPool.globalInstance().start(worker)

    def _show_update(self, result: object, *, manual: bool = False) -> None:
        if not isinstance(result, UpdateInfo):
            if manual: QMessageBox.information(self, "PDF Master is up to date", "You are using the latest available version.")
            return
        if result.version == self.settings.skipped_version: return
        dialog = QMessageBox(self); dialog.setIcon(QMessageBox.Icon.Information); dialog.setWindowTitle("PDF Master update available")
        dialog.setText(f"PDF Master {result.version} is available")
        if result.installer is not None:
            dialog.setInformativeText("You are using version " + VERSION + ". The installer can be downloaded now and run with your permission.")
            download = dialog.addButton("Download & Install", QMessageBox.ButtonRole.AcceptRole); dialog.setDefaultButton(download)
        else:
            dialog.setInformativeText("You are using version " + VERSION + ". Updates are never downloaded or installed without your permission.")
        visit = dialog.addButton("View Release", QMessageBox.ButtonRole.ActionRole); skip = dialog.addButton("Skip This Version", QMessageBox.ButtonRole.DestructiveRole); dialog.addButton("Later", QMessageBox.ButtonRole.RejectRole)
        dialog.exec()
        clicked = dialog.clickedButton()
        if result.installer is not None and clicked is download: self._download_update(result)
        elif clicked is visit: QDesktopServices.openUrl(QUrl(result.release_url))
        elif clicked is skip:
            self.settings.skipped_version = result.version; self.config_store.save(self.settings)

    def _download_update(self, update: UpdateInfo) -> None:
        if self.update_worker is not None or update.installer is None: return
        folder = local_data_dir() / "updates"; folder.mkdir(parents=True, exist_ok=True)
        target = folder / (update.installer.name)
        worker = FunctionWorker(download_release_asset, update.installer, str(target), with_progress=True)
        self.update_worker = worker
        worker.signals.progress.connect(self._update_progress)
        worker.signals.result.connect(self._install_downloaded)
        worker.signals.error.connect(self._update_failed)
        worker.signals.finished.connect(lambda: setattr(self, "update_worker", None))
        QThreadPool.globalInstance().start(worker)
        self._ensure_progress().setLabelText("Preparing download…"); self._ensure_progress().setValue(0)

    def _ensure_progress(self) -> QProgressDialog:
        if getattr(self, "update_progress", None) is None:
            dialog = QProgressDialog("Updater", None, 0, 100, self)
            dialog.setWindowTitle("Downloading update"); dialog.setWindowModality(Qt.WindowModality.WindowModal); dialog.setCancelButton(None); dialog.setMinimumDuration(0)
            self.update_progress = dialog
        return self.update_progress

    def _update_progress(self, value: int, message: str) -> None:
        self._ensure_progress().setLabelText(message); self._ensure_progress().setValue(value)
        if value >= 100:
            self._ensure_progress().close(); self.update_progress = None

    def _install_downloaded(self, path: object) -> None:
        if not isinstance(path, Path) or not path.exists(): return
        if getattr(self, "update_progress", None) is not None: self.update_progress.close(); self.update_progress = None
        dialog = QMessageBox(self); dialog.setIcon(QMessageBox.Icon.Question); dialog.setWindowTitle("Run the updater?")
        dialog.setText("PDF Master update ready")
        dialog.setInformativeText("The installer has been downloaded. Run it now to complete the update? PDF Master will close while the installer runs.")
        install_now = dialog.addButton("Install Now", QMessageBox.ButtonRole.AcceptRole); dialog.addButton("Later", QMessageBox.ButtonRole.RejectRole); dialog.setDefaultButton(install_now)
        dialog.exec()
        if dialog.clickedButton() is install_now:
            QProcess.startDetached(str(path), [])
            QTimer.singleShot(600, self.close)

    def _update_failed(self, message: str, _trace: str) -> None:
        if getattr(self, "update_progress", None) is not None: self.update_progress.close(); self.update_progress = None
        QMessageBox.warning(self, "Update failed", message)
