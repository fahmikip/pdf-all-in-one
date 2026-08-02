"""Thread-pool worker for long-running document operations."""
from __future__ import annotations

import traceback
import logging
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, QRunnable, Signal, Slot


class WorkerSignals(QObject):
    progress = Signal(int, str)
    result = Signal(object)
    error = Signal(str, str)
    finished = Signal()


class FunctionWorker(QRunnable):
    """Run a callable outside the GUI thread.

    Callables opting into progress should accept a ``progress`` keyword callback.
    """

    def __init__(self, function: Callable[..., Any], *args: Any, with_progress: bool = False, **kwargs: Any) -> None:
        super().__init__()
        self.function = function
        self.args = args
        self.kwargs = kwargs
        self.with_progress = with_progress
        self.signals = WorkerSignals()
        self.setAutoDelete(True)

    @Slot()
    def run(self) -> None:
        try:
            if self.with_progress:
                self.kwargs["progress"] = self.signals.progress.emit
            result = self.function(*self.args, **self.kwargs)
        except Exception as exc:  # exception is transported to the GUI thread
            logging.getLogger(__name__).exception("Background operation failed: %s", type(exc).__name__)
            self.signals.error.emit(str(exc), traceback.format_exc())
        else:
            self.signals.result.emit(result)
        finally:
            self.signals.finished.emit()
