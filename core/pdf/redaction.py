"""Permanent text redaction helpers."""

from __future__ import annotations

from pathlib import Path

import pymupdf

from core.utils.file_utils import atomic_output, ensure_distinct_paths
from core.utils.validation import validate_pdf


def find_text(source: str | Path, query: str) -> list[dict]:
    """Return page and rectangle matches for exact text fragments."""
    info = validate_pdf(source)
    query = query.strip()
    if not query:
        raise ValueError("Masukkan teks yang ingin dicari.")
    matches = []
    with pymupdf.open(info.path) as document:
        for page_index, page in enumerate(document):
            for rect in page.search_for(query, quads=False):
                matches.append({"page": page_index, "rect": tuple(rect), "text": query})
    return matches


def redact_text(source: str | Path, destination: str | Path, query: str) -> Path:
    """Permanently remove matching text and overlapping pixels into a new PDF."""
    info = validate_pdf(source)
    output = Path(destination).expanduser().resolve()
    ensure_distinct_paths(info.path, output)
    matches = find_text(info.path, query)
    if not matches:
        raise ValueError("Teks tidak ditemukan di PDF.")
    with pymupdf.open(info.path) as document, atomic_output(output) as temporary:
        for match in matches:
            page = document[match["page"]]
            page.add_redact_annot(pymupdf.Rect(match["rect"]), fill=(0, 0, 0), cross_out=False)
        for page in document:
            if page.first_annot:
                page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_PIXELS)
        document.set_metadata({})
        document.save(temporary, garbage=4, deflate=True, clean=True)
    return output


def replace_text(source: str | Path, destination: str | Path, query: str, replacement: str) -> Path:
    """Replace exact matches in a new PDF by redacting then inserting replacement text."""
    info = validate_pdf(source)
    output = Path(destination).expanduser().resolve()
    ensure_distinct_paths(info.path, output)
    query = query.strip()
    if not query:
        raise ValueError("Masukkan teks yang ingin diganti.")
    matches = find_text(info.path, query)
    if not matches:
        raise ValueError("Teks tidak ditemukan di PDF.")
    with pymupdf.open(info.path) as document, atomic_output(output) as temporary:
        for match in matches:
            page = document[match["page"]]
            rect = pymupdf.Rect(match["rect"])
            page.add_redact_annot(rect, fill=(1, 1, 1), cross_out=False)
        for page in document:
            if page.first_annot:
                page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_PIXELS)
        if replacement:
            for match in matches:
                page = document[match["page"]]
                rect = pymupdf.Rect(match["rect"])
                page.insert_text(
                    pymupdf.Point(rect.x0, rect.y1 - max(1, rect.height * 0.18)),
                    replacement,
                    fontsize=max(5, min(18, rect.height * 0.8)),
                    fontname="helv",
                    color=(0, 0, 0),
                )
        document.set_metadata({})
        document.save(temporary, garbage=4, deflate=True, clean=True)
    return output
