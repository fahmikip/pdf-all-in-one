"""Privacy-conscious rotating application logging."""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from app.config import local_data_dir


def configure_logging() -> None:
    log_dir = local_data_dir() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(log_dir / "pdfmaster.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s"))
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    if not any(isinstance(item, RotatingFileHandler) for item in root.handlers):
        root.addHandler(handler)
    logging.getLogger(__name__).info("PDF Master started")
