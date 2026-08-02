"""Application bootstrap and global error handling."""
from __future__ import annotations

import logging
import sys
import traceback
from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMessageBox

from app.config import APP_NAME, ConfigStore, Settings, VERSION
from core.utils.logger import configure_logging
from ui.main_window import MainWindow
from ui.icons import icon
from ui.themes.palette import stylesheet_for


def install_exception_handler() -> None:
    def handle(exc_type: type[BaseException], exc: BaseException, tb: object) -> None:
        details = "".join(traceback.format_exception(exc_type, exc, tb))
        logging.getLogger(__name__).critical("Unhandled exception", exc_info=(exc_type, exc, tb))
        dialog = QMessageBox(QMessageBox.Icon.Critical, "Something went wrong", str(exc))
        dialog.setInformativeText("PDF Master encountered an unexpected problem. Your original files were not changed.")
        dialog.setDetailedText(details)
        dialog.exec()
    sys.excepthook = handle


def create_application(argv: list[str] | None = None) -> tuple[QApplication, MainWindow]:
    configure_logging()
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(argv or sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(VERSION)
    app.setOrganizationName("Fahmikip")
    app.setWindowIcon(icon("app", 32))
    app.setStyle("Fusion")
    store = ConfigStore()
    settings = store.load()
    app.setStyleSheet(stylesheet_for(settings.theme))
    install_exception_handler()
    window = MainWindow(settings=settings, config_store=store)
    return app, window


def run() -> int:
    app, window = create_application()
    window.show()
    return app.exec()
