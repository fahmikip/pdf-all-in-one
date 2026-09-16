"""Bootstrap and application-shell coverage."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

import pytest
from app.bootstrap import create_application, install_exception_handler
from app.config import APP_NAME, VERSION, Settings
from core.utils.logger import configure_logging


def test_configure_logging_is_idempotent(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("core.utils.logger.local_data_dir", lambda: tmp_path)
    configure_logging()
    configure_logging()
    handlers = [item for item in logging.getLogger().handlers if isinstance(item, RotatingFileHandler)]
    assert len(handlers) == 1
    assert tmp_path.joinpath("logs", "pdfmaster.log").exists()
    assert logging.getLogger().level == logging.INFO


def test_install_exception_handler_logs_and_shows_dialog(monkeypatch) -> None:
    import sys as sys_module

    captured: dict[str, object] = {}

    class FakeMessageBox:
        Icon = type("I", (), {"Critical": 3})

        def __init__(self, icon, title, text) -> None:
            captured["icon"] = icon
            captured["title"] = title
            captured["text"] = text

        def setInformativeText(self, value: str) -> None:
            captured["informative"] = value

        def setDetailedText(self, value: str) -> None:
            captured["details"] = value

        def exec(self) -> None:
            captured["executed"] = True

    monkeypatch.setattr("app.bootstrap.QMessageBox", FakeMessageBox)
    install_exception_handler()
    assert callable(sys_module.excepthook)

    def boom() -> None:
        raise ValueError("kaboom")

    try:
        boom()
    except ValueError as exc:
        sys_module.excepthook(type(exc), exc, exc.__traceback__)
    assert captured["executed"] is True
    assert "kaboom" in str(captured["details"])
    assert captured["informative"]


def test_create_application_shell(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "appdata"))
    app, window = create_application([])
    assert app.applicationName() == APP_NAME
    assert app.applicationVersion() == VERSION
    assert window.windowTitle().startswith(APP_NAME)
    window.close()


@pytest.mark.parametrize("theme", ["light", "dark", "system"])
def test_create_application_with_each_theme(tmp_path: Path, monkeypatch, theme: str) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / f"data-{theme}"))

    class FakeStore:
        def __init__(self) -> None:
            pass

        def load(self):
            return Settings(theme=theme, check_updates=False)

    monkeypatch.setattr("app.bootstrap.ConfigStore", FakeStore)
    app, window = create_application([])
    assert app.styleSheet()
    window.close()
