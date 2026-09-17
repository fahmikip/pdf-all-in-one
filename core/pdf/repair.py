"""Recover damaged PDF files and produce web-friendly (linearized) copies."""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

import pikepdf
import pymupdf

from core.utils.file_utils import atomic_output, ensure_distinct_paths
from core.utils.validation import ValidationError, validate_pdf

Progress = Callable[[int, str], None]


def linearize_pdf(source: str | Path, destination: str | Path, *, progress: Progress | None = None) -> Path:
    """Save a new copy optimized for fast downloading via qpdf/pikepdf (Fast Web View)."""
    info = validate_pdf(source)
    output = Path(destination).expanduser().resolve()
    ensure_distinct_paths(info.path, output)
    if output.suffix.lower() != ".pdf":
        raise ValueError("Linearized output must use .pdf.")
    if progress:
        progress(30, "Rewriting object stream…")
    with pikepdf.open(info.path) as pdf, atomic_output(output) as temporary:
        pdf.save(
            str(temporary),
            linearize=True,
            recompress_flate=True,
            object_stream_mode=pikepdf.ObjectStreamMode.generate,
        )
    if progress:
        progress(100, output.name)
    return output


def repair_pdf(source: str | Path, destination: str | Path, *, progress: Progress | None = None) -> Path:
    """Attempt to rebuild a damaged PDF using qpdf, pikepdf, then PyMuPDF in order."""
    source = Path(source).expanduser().resolve()
    output = Path(destination).expanduser().resolve()
    if not source.exists() or not source.is_file():
        raise ValidationError("The selected PDF does not exist.")
    if source.suffix.lower() != ".pdf":
        raise ValidationError("Please select a PDF file.")
    ensure_distinct_paths(source, output)
    if progress:
        progress(15, "Repairing document…")
    executable = shutil.which("qpdf")
    if executable is not None:
        with atomic_output(output) as temporary:
            result = subprocess.run(
                [executable, str(source), str(temporary)],
                capture_output=True,
                text=True,
                timeout=600,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            if result.returncode != 0:
                raise RuntimeError(
                    "qpdf could not repair this file. "
                    + (result.stderr.strip()[-300:] if result.stderr.strip() else "")
                )
        return _completed(output, progress)
    try:
        with pikepdf.open(source, attempt_recovery=True) as pdf, atomic_output(output) as temporary:
            pdf.save(str(temporary), recompress_flate=True)
        return _completed(output, progress)
    except pikepdf.PdfError:
        pass
    with pymupdf.open(source) as document, atomic_output(output) as temporary:
        document.save(temporary, garbage=3, deflate=True)
    return _completed(output, progress)


def _completed(output: Path, progress: Progress | None) -> Path:
    if progress:
        progress(100, output.name)
    return output
