"""Reliable streaming-style PDF merge operation."""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Sequence

import fitz

from core.utils.file_utils import atomic_output
from core.utils.validation import validate_pdf

Progress = Callable[[int, str], None]


def merge_pdfs(sources: Sequence[str | Path], destination: str | Path, progress: Progress | None = None) -> Path:
    if len(sources) < 2:
        raise ValueError("Select at least two PDF files to merge.")
    infos = [validate_pdf(path) for path in sources]
    output = Path(destination).expanduser().resolve()
    if output.suffix.lower() != ".pdf":
        raise ValueError("Merge output must use the .pdf extension.")
    if output in {info.path for info in infos}:
        raise ValueError("Output must not replace an input PDF.")
    merged = fitz.open()
    try:
        for index, info in enumerate(infos, start=1):
            with fitz.open(info.path) as document:
                merged.insert_pdf(document)
            if progress:
                progress(round(index / len(infos) * 90), info.path.name)
        with atomic_output(output) as temporary:
            merged.save(temporary, garbage=3, deflate=True)
        if progress:
            progress(100, output.name)
    finally:
        merged.close()
    return output
