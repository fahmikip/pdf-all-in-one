"""Executable entry point for PDF Master."""
from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.bootstrap import run

if __name__ == "__main__":
    raise SystemExit(run())
